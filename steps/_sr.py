"""Real-ESRGAN x4plus (M24): a 4× upscaler for the conditioning image before it is projected onto the
head. The RRDBNet below is the ESRGAN architecture written out (23 residual-in-residual dense blocks,
64 features, growth 32), loading the published `RealESRGAN_x4plus.pth` (BSD-3-Clause, xinntao/Real-ESRGAN
v0.1.0) by its own key names; no basicsr, no realesrgan package. The network follows BasicSR's `rrdbnet_arch.py`
(Apache-2.0) as Real-ESRGAN (BSD-3-Clause) uses it; written out here, not copied.
"""

import os
from itertools import pairwise
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


def plan(n: int, win: int, ov: int) -> list[int]:
    """Window starts along a length n: windows of `win` overlapping by at least `ov`, evenly spread, the last one
    ending at n (shifted inward, never cut short)."""
    if n <= win:
        return [0]
    k = -(-(n - win) // (win - ov)) + 1
    return [round(i * (n - win) / (k - 1)) for i in range(k)]


def _bump(n: int, ov: int, lo: bool, hi: bool) -> np.ndarray:
    """A window's 1-D weight: 1, with a raised-cosine ramp over `ov` pixels at each side that has a neighbour."""
    w = np.ones(n, np.float32)
    if ov:
        r = (0.5 - 0.5 * np.cos(np.pi * (np.arange(ov) + 0.5) / ov)).astype(np.float32)
        if lo:
            w[:ov] = r
        if hi:
            w[n - ov :] *= r[::-1]
    return w


class Blend:
    """Overlapping windows blended into one CPU float32 picture of any size (the GPU only ever holds one window):
    each patch is weighted by its raised-cosine ramps and the sum divided by the weights' sum, so a constant stays
    constant and windows fade into each other with no cut. Windows are planned in the input's pixels (h, w), the
    patches added at k× them. ponytail: a float32 copy of the whole picture in RAM (3.8 GB at 321 MP)."""

    def __init__(self, h: int, w: int, win: int, ov: int, k: int = 1):
        self.k, self.wh, self.ww = k, min(win, h), min(win, w)
        self.ys, self.xs = plan(h, self.wh, ov), plan(w, self.ww, ov)
        self.acc = np.zeros((h * k, w * k, 3), np.float32)
        self._wy = {
            y: _bump(self.wh * k, ov * k, i > 0, i < len(self.ys) - 1)
            for i, y in enumerate(self.ys)
        }
        self._wx = {
            x: _bump(self.ww * k, ov * k, i > 0, i < len(self.xs) - 1)
            for i, x in enumerate(self.xs)
        }
        self.den_y, self.den_x = np.zeros(h * k, np.float32), np.zeros(w * k, np.float32)
        for y, b in self._wy.items():
            self.den_y[y * k : (y + self.wh) * k] += b
        for x, b in self._wx.items():
            self.den_x[x * k : (x + self.ww) * k] += b

    def windows(self) -> list[tuple[int, int]]:
        """(y, x) of every window, row by row."""
        return [(y, x) for y in self.ys for x in self.xs]

    def lines(self) -> tuple[list[int], list[int]]:
        """The rows and columns (at k×) half way through each overlap: where a seam would show."""
        mid = lambda s, n: [((a + n) + b) * self.k // 2 for a, b in pairwise(s)]
        return mid(self.ys, self.wh), mid(self.xs, self.ww)

    def add(self, y: int, x: int, patch: np.ndarray) -> None:
        k, wy, wx = self.k, self._wy[y], self._wx[x]
        self.acc[y * k : (y + self.wh) * k, x * k : (x + self.ww) * k] += (
            patch * (wy[:, None] * wx)[..., None]
        )

    def result(self) -> np.ndarray:
        """The blend, float32 (in place, in row chunks: no second copy)."""
        for r in range(0, len(self.acc), 256):
            self.acc[r : r + 256] /= (self.den_y[r : r + 256, None] * self.den_x)[..., None]
        return self.acc


def u8(a: np.ndarray) -> np.ndarray:
    """float 0-255 → uint8, in row chunks."""
    out = np.empty(a.shape, np.uint8)
    for r in range(0, len(a), 256):
        out[r : r + 256] = np.clip(a[r : r + 256] + 0.5, 0, 255)
    return out


@torch.no_grad()
def upscale(
    net: nn.Module, rgb: np.ndarray, tile: int = 256, pad: int = 16, tick=None
) -> np.ndarray:
    """4× of an RGB uint8 image, uint8 in RAM: windows of tile + 2·pad overlapping by 2·pad, blended smoothly
    (`Blend`); the GPU holds one window whatever the image size. tick(i, n) after each window."""
    dev, dtype = next(net.parameters()).device, next(net.parameters()).dtype
    blend = Blend(*rgb.shape[:2], tile + 2 * pad, 2 * pad, SCALE)
    wins = blend.windows()
    for i, (y, x) in enumerate(wins):
        x_in = torch.from_numpy(rgb[y : y + blend.wh, x : x + blend.ww]).permute(2, 0, 1)[None]
        sr = net(x_in.to(dev, dtype) / 255).float().clamp(0, 1)[0].permute(1, 2, 0) * 255
        blend.add(y, x, sr.cpu().numpy())
        if tick:
            tick(i, len(wins))
    return u8(blend.result())
