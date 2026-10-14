"""Real-ESRGAN x4plus (M24): a 4× upscaler for the conditioning image before it is projected onto the
head. The RRDBNet below is the ESRGAN architecture written out (23 residual-in-residual dense blocks,
64 features, growth 32), loading the published `RealESRGAN_x4plus.pth` (BSD-3-Clause, xinntao/Real-ESRGAN
v0.1.0) by its own key names; no basicsr, no realesrgan package. The network follows BasicSR's `rrdbnet_arch.py`
(Apache-2.0) as Real-ESRGAN (BSD-3-Clause) uses it; written out here, not copied.
"""

import os
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

MODEL = "xinntao/Real-ESRGAN"
WEIGHTS = "RealESRGAN/RealESRGAN_x4plus.pth"
SCALE = 4


class _Dense(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class _RRDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.rdb1, self.rdb2, self.rdb3 = _Dense(nf, gc), _Dense(nf, gc), _Dense(nf, gc)

    def forward(self, x):
        return self.rdb3(self.rdb2(self.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, nf=64, nb=23, gc=32):
        super().__init__()
        self.conv_first = nn.Conv2d(3, nf, 3, 1, 1)
        self.body = nn.Sequential(*[_RRDB(nf, gc) for _ in range(nb)])
        self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(x)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


def weights_path() -> Path:
    return (
        Path(os.environ.get("EFFIGY_MODELS", Path(__file__).resolve().parents[1] / "models"))
        / WEIGHTS
    )


def load(device: str | None = None) -> nn.Module:
    """The upscaler on the GPU (fp16) or the CPU; FileNotFoundError when the weights are not installed."""
    path = weights_path()
    if not path.is_file():  # no path in the message: it ends up in the library's meta.json
        raise FileNotFoundError("the `texture` model group is not installed (Setup → Face detail)")
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    net = RRDBNet()
    state = torch.load(path, map_location="cpu", weights_only=True)
    net.load_state_dict(state.get("params_ema", state), strict=True)
    net = net.eval().to(device)
    return net.half() if device == "cuda" else net


@torch.no_grad()
def upscale(net: nn.Module, rgb: np.ndarray, tile: int = 256, pad: int = 16) -> np.ndarray:
    """4× of an RGB uint8 image, in tiles with overlap (memory stays flat whatever the image size)."""
    dev = next(net.parameters()).device
    dtype = next(net.parameters()).dtype
    h, w = rgb.shape[:2]
    x = torch.from_numpy(rgb).permute(2, 0, 1)[None].to(dev, dtype) / 255
    out = torch.zeros(1, 3, h * SCALE, w * SCALE, device=dev, dtype=torch.float32)
    for y0 in range(0, h, tile):
        for x0 in range(0, w, tile):
            y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
            py0, px0, py1, px1 = (
                max(y0 - pad, 0),
                max(x0 - pad, 0),
                min(y1 + pad, h),
                min(x1 + pad, w),
            )
            sr = net(x[..., py0:py1, px0:px1]).float()
            oy, ox = (y0 - py0) * SCALE, (x0 - px0) * SCALE
            out[..., y0 * SCALE : y1 * SCALE, x0 * SCALE : x1 * SCALE] = sr[
                ..., oy : oy + (y1 - y0) * SCALE, ox : ox + (x1 - x0) * SCALE
            ]
    return (out[0].clamp(0, 1).permute(1, 2, 0) * 255 + 0.5).byte().cpu().numpy()
