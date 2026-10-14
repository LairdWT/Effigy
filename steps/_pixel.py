"""Pixel-art maths for the pixelize step (research 15 §5.3): the pixel grid of a picture drawn at a larger
size (a model's "pixel art" is 6–8 picture pixels per drawn pixel), a downscale per cell, one palette over
many frames, ordered dither, a 1-px outline, palette files. numpy + Pillow, no model. Frames are (H, W, 4)
uint8 RGBA arrays."""

import math
import re
from pathlib import Path

import numpy as np
from PIL import Image

MAX_PERIOD = 32
# calibration knob: the normalised autocorrelation of the edge profile a real grid shows at its period;
# a sharp render or a photo scores well below (the picture is then taken pixel for pixel)
MIN_PEAK = 0.3
PALETTES = Path(__file__).with_name("palettes")
BAYER = {
    "bayer2": np.array([[0, 2], [3, 1]]) / 4,
    "bayer4": np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16,
}


def _profiles(frames: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Edge presence per column and per row (the energy saturated at its upper quartile: a grid is where
    the edges *are*, their strength varies with the colours), summed over the frames (one grid for all)."""
    px = py = None
    for f in frames:
        g = f.astype(np.float32).mean(-1)
        dx, dy = np.abs(np.diff(g, axis=1)).sum(0), np.abs(np.diff(g, axis=0)).sum(1)
        dx = np.minimum(dx / (np.percentile(dx, 75) + 1e-6), 1.0)
        dy = np.minimum(dy / (np.percentile(dy, 75) + 1e-6), 1.0)
        px = dx if px is None else px[: len(dx)] + dx[: len(px)]
        py = dy if py is None else py[: len(dy)] + dy[: len(py)]
    return px, py


def _period(p: np.ndarray) -> tuple[int, float]:
    """(period, peak) of one edge profile: the smallest lag that is a local maximum of the autocorrelation
    near the best one (the harmonics score about as high as the fundamental)."""
    if len(p) < 8:
        return 1, 0.0
    w = min(MAX_PERIOD, len(p))  # a smooth profile is not a grid: the running mean taken out
    p = p - np.convolve(p, np.ones(w) / w, "same")
    norm = float((p * p).sum()) or 1.0
    top = min(MAX_PERIOD, len(p) // 4)
    ac = {k: float((p[:-k] * p[k:]).sum()) / norm for k in range(1, top + 2)}
    peaks = {k: v for k, v in ac.items() if 2 <= k <= top and v > ac[k - 1] and v > ac[k + 1]}
    # no peak, or only anti-correlated ones (0.8 × a negative best is above it: none would pass; a dark sprite sheet)
    best = max(peaks.values(), default=0.0)
    if best <= 0:
        return 1, 0.0
    k = min(k for k, v in peaks.items() if v >= 0.8 * best)
    return k, peaks[k]


def _offset(p: np.ndarray, k: int) -> int:
    """Where the cells start: the edges sit between the columns `r` and `r + 1`, so a cell starts at `r + 1`."""
    r = int(np.argmax([p[i::k].sum() for i in range(k)]))
    return (r + 1) % k


def grid(frames: list[np.ndarray]) -> tuple[int, tuple[int, int]]:
    """(period, (x, y) offset of the first whole cell) of the pixel grid the frames were drawn on; 1 and (0, 0)
    when there is none (a sharp picture)."""
    px, py = _profiles(frames)
    (kx, sx), (ky, sy) = _period(px), _period(py)
    if max(sx, sy) < MIN_PEAK:
        return 1, (0, 0)
    k = kx if sx >= sy else ky
    return k, (_offset(px, k), _offset(py, k))


def downscale(rgba: np.ndarray, k: int, offset=(0, 0), method: str = "dominant") -> np.ndarray:
    """One pixel per k×k cell, the cells starting at `offset` (the partial cells at the edges are padded with
    transparent pixels): the cell's most frequent colour (`dominant`: hard edges) or its median (renders)."""
    if k == 1:
        return rgba.copy()
    h, w = rgba.shape[:2]
    top, left = (-offset[1]) % k, (-offset[0]) % k
    a = np.pad(rgba, ((top, (-(h + top)) % k), (left, (-(w + left)) % k), (0, 0)))
    rows, cols = a.shape[0] // k, a.shape[1] // k
    cells = a.reshape(rows, k, cols, k, 4).transpose(0, 2, 1, 3, 4).reshape(rows, cols, k * k, 4)
    if method == "median":
        return np.median(cells, axis=2).round().astype(np.uint8)
    keys = cells.astype(np.uint32)
    keys = (keys[..., 0] << 24) | (keys[..., 1] << 16) | (keys[..., 2] << 8) | keys[..., 3]
    out = np.empty((rows, cols), np.uint32)
    for idx in np.ndindex(
        rows, cols
    ):  # ponytail: ~1 s per million cells; vectorise if wallpapers crawl
        vals, counts = np.unique(keys[idx], return_counts=True)
        out[idx] = vals[counts.argmax()]
    return np.stack([(out >> s) & 255 for s in (24, 16, 8, 0)], -1).astype(np.uint8)


def cut_alpha(rgba: np.ndarray, cut: float = 0.5) -> np.ndarray:
    """A binary alpha (at or above `cut` is opaque); transparent pixels black, so sheets compare equal."""
    out = rgba.copy()
    out[..., 3] = np.where(rgba[..., 3] >= cut * 255, 255, 0)
    out[out[..., 3] == 0, :3] = 0
    return out


SEAM_PASS = 1.1  # §3.2: a tile passes when its wrapped edges jump no more than its own lines do (10 % leeway)


def seam_ratio(rgba: np.ndarray) -> float:
    """How hard a tile's wrapped edges jump (M54, research 15 §5.5): the mean grey step across the left/right wrap
    (and the top/bottom one) over the strongest such step between neighbouring columns (rows) inside, the worse of
    the two. A seamless tile's wrap is one more of its own lines (1 or less); a cut-out piece of a picture jumps
    further than any. The strongest line, not a typical one: bricks, planks and cobbles have mortar lines as hard as
    a seam (on the M54 bench a 512 px tile's own lines reach 1.3-1.9 times their 90th percentile).
    ponytail: the ceiling of that choice: a nearly flat tile with one hard line of its own hides a seam up to that
    line's strength; a per-line rank or a structure measure if such tiles come up."""
    g = rgba[..., :3].astype(np.float32).mean(-1)
    ratios = [0.0]
    for a in (g, g.T):  # columns, then rows
        if a.shape[1] < 2:  # one pixel wide: no line inside to compare with
            continue
        inside = np.abs(np.diff(a, axis=1)).mean(0)
        ratios.append(float(np.abs(a[:, 0] - a[:, -1]).mean() / max(inside.max(), 1e-6)))
    return max(ratios)


def make_palette(frames: list[np.ndarray], colors: int) -> np.ndarray:
    """(n, 3) uint8: at most `colors` colours over every opaque pixel of every frame (median cut)."""
    px = [f[f[..., 3] > 0][:, :3] for f in frames]
    px = np.concatenate(px) if px else np.zeros((0, 3), np.uint8)
    if len(px) == 0:
        return np.zeros((1, 3), np.uint8)
    px = px[:: max(1, len(px) // 200_000)]  # a sample is plenty for a palette
    im = Image.fromarray(px.reshape(-1, 1, 3), "RGB").quantize(colors, Image.Quantize.MEDIANCUT)
    pal = np.array(im.getpalette()[: 3 * colors], np.uint8).reshape(-1, 3)
    return np.unique(pal[np.unique(np.asarray(im))], axis=0)


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """(..., 3) sRGB 0–255 → CIELAB, D65."""
    c = np.asarray(rgb, np.float32) / 255
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array(
        [[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]], np.float32
    )
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883], np.float32)
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (841 / 108) * xyz + 4 / 29)
    return np.stack(
        [116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1
    )


def delta_e00(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """CIEDE2000 between broadcastable (..., 3) Lab arrays (Sharma, Wu and Dalal 2005): the hue term keeps
    a blue from mapping onto a purple or a grey of the same RGB distance."""
    L1, a1, b1 = (lab1[..., i] for i in range(3))
    L2, a2, b2 = (lab2[..., i] for i in range(3))
    cm = (np.hypot(a1, b1) + np.hypot(a2, b2)) / 2
    g = 0.5 * (1 - np.sqrt(cm**7 / (cm**7 + 25.0**7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1, c2 = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1, h2 = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    grey = c1 * c2 == 0
    dh = h2 - h1
    dh = np.where(grey, 0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dH = 2 * np.sqrt(c1 * c2) * np.sin(np.radians(dh / 2))
    lm, cmp = (L1 + L2) / 2, (c1 + c2) / 2
    hs = h1 + h2
    hm = np.where(
        grey,
        hs,
        np.where(np.abs(h1 - h2) <= 180, hs / 2, np.where(hs < 360, hs + 360, hs - 360) / 2),
    )
    t = (
        1
        - 0.17 * np.cos(np.radians(hm - 30))
        + 0.24 * np.cos(np.radians(2 * hm))
        + 0.32 * np.cos(np.radians(3 * hm + 6))
        - 0.20 * np.cos(np.radians(4 * hm - 63))
    )
    sl = 1 + 0.015 * (lm - 50) ** 2 / np.sqrt(20 + (lm - 50) ** 2)
    sc, sh = 1 + 0.045 * cmp, 1 + 0.015 * cmp * t
    rt = (
        -np.sin(np.radians(60 * np.exp(-(((hm - 275) / 25) ** 2))))
        * 2
        * np.sqrt(cmp**7 / (cmp**7 + 25.0**7))
    )
    dl, dc = (L2 - L1) / sl, (c2 - c1) / sc
    return np.sqrt(dl**2 + dc**2 + (dH / sh) ** 2 + rt * dc * (dH / sh))


def apply_palette(rgba: np.ndarray, pal: np.ndarray, dither: str = "none") -> np.ndarray:
    """Every opaque pixel to its nearest palette colour by CIEDE2000 (a small palette judged by RGB distance
    turns blues purple and skin grey), after an ordered (Bayer) dither when asked: ordered dither keeps a
    pattern still across the frames of an animation, error diffusion crawls."""
    rgb = rgba[..., :3].astype(np.float32)
    if dither != "none":
        m = BAYER[dither]
        n, (h, w) = len(m), rgb.shape[:2]
        t = np.tile(m, (math.ceil(h / n), math.ceil(w / n)))[:h, :w] - 0.5 + 0.5 / (n * n)
        rgb = rgb + t[..., None] * (255 / len(pal) ** (1 / 3))  # about one palette step
    out, p = rgba.copy(), srgb_to_lab(pal)
    rows = max(
        1, 2_000_000 // (rgb.shape[1] * len(pal))
    )  # by bands: ΔE00's (rows, w, n) temporaries stay in MBs
    for y in range(0, rgb.shape[0], rows):
        d = delta_e00(srgb_to_lab(np.clip(rgb[y : y + rows], 0, 255))[:, :, None, :], p[None, None])
        out[y : y + rows, :, :3] = pal[d.argmin(-1)]
    out[out[..., 3] == 0, :3] = 0
    return out


def outline(rgba: np.ndarray, color) -> np.ndarray:
    """A 1-px outline in `color` around the opaque pixels (4-connected; the sprite grows by one pixel)."""
    a = rgba[..., 3] > 0
    ring = np.zeros_like(a)
    ring[1:] |= a[:-1]
    ring[:-1] |= a[1:]
    ring[:, 1:] |= a[:, :-1]
    ring[:, :-1] |= a[:, 1:]
    ring &= ~a
    out = rgba.copy()
    out[ring, :3], out[ring, 3] = color, 255
    return out


def remap(rgba: np.ndarray, mapping: dict[str, str]) -> np.ndarray:
    """Exact recolours (`{"#rrggbb": "#rrggbb"}`) of the opaque pixels: a palette swap, nothing re-quantised."""
    out = rgba.copy()
    for src, dst in mapping.items():
        m = (rgba[..., :3] == hex_rgb(src)).all(-1) & (rgba[..., 3] > 0)
        out[m, :3] = hex_rgb(dst)
    return out


def hex_rgb(s: str) -> tuple[int, int, int]:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", s.strip())
    if not m:
        raise ValueError(f"not a #rrggbb colour: {s!r}")
    return tuple(int(m[1][i : i + 2], 16) for i in (0, 2, 4))


def read_palette(path: Path) -> np.ndarray:
    """A `.gpl` (GIMP: `R G B name` lines), `.hex` (one RRGGBB per line) or JASC `.pal` palette as (n, 3)."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    if Path(path).suffix.lower() == ".hex":
        found = re.findall(r"^[ \t]*#?([0-9a-fA-F]{6})[ \t]*$", text, re.MULTILINE)
        rows = [hex_rgb(m) for m in found]
    else:  # one colour per line; a header's lone number (JASC's "0100") never pairs across lines
        found = re.findall(r"^[ \t]*(\d+)[ \t]+(\d+)[ \t]+(\d+)\b", text, re.MULTILINE)
        rows = [tuple(map(int, m)) for m in found]
    rows = [r for r in rows if max(r) <= 255]
    if not rows:
        raise ValueError(f"{path}: no colours found")
    return np.unique(np.array(rows, np.uint8), axis=0)


def write_gpl(pal: np.ndarray, path: Path, name: str = "effigy") -> None:
    lines = [f"GIMP Palette\nName: {name}\nColumns: 16\n#"] + [
        f"{r:3d} {g:3d} {b:3d}" for r, g, b in pal
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
