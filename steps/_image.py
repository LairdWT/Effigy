"""Pure image logic for concepts/prep (no torch): 3D-readiness gates (research 07 §3) and framing.

rgb: (H, W, 3) uint8; alpha: (H, W) float in 0..1 (BiRefNet matte). Thresholds are starting values:
log picks and outcomes, then calibrate (research 07 §3).
"""

import json
from pathlib import Path

import cv2
import numpy as np

# gate thresholds (calibration knobs)
MIN_LARGEST = 0.97  # largest component's share of the mask
SPECK = 0.001  # components below this share of the frame are ignored
MIN_MARGIN = 0.03  # to every border, as a share of that axis
SIZE_RANGE = (
    0.55,
    0.95,
)  # object's longest side as a share of the frame: a long wall fills the width, the
# margin gate keeps it off the border (0.90 failed every wide prop: the owner's second agent, 2026-10-11)
MIN_RES = 1024  # long side, px
MAX_BG_STD = 8.0  # background detail std (0..255, luma minus a blur) outside the dilated mask; Z-Image greys 3.7–6.8
MIN_FG_STD = 10.0  # soft: some shading on the subject
# prep framing (TRELLIS.2 preprocessing; localmesh measured 4 % padding as better than none)
ALPHA_CUT = 0.8
PADDING = 0.04
OUT_MAX = 1024


def _luma(rgb: np.ndarray) -> np.ndarray:
    return rgb.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)


def gates(rgb: np.ndarray, alpha: np.ndarray) -> dict:
    """{name: {"ok": bool, "value": float, "hard": bool}}; hard gates reject, soft ones rank."""
    h, w = alpha.shape
    mask = (alpha > 0.5).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    areas = [a for a in stats[1:n, cv2.CC_STAT_AREA] if a >= SPECK * h * w]
    largest = max(areas, default=0) / max(sum(areas), 1)
    out = {"one_component": (largest >= MIN_LARGEST, largest, True)}
    if mask.any():
        ys, xs = np.nonzero(mask)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        margin = min(x0 / w, y0 / h, (w - 1 - x1) / w, (h - 1 - y1) / h)
        size = max((x1 - x0 + 1) / w, (y1 - y0 + 1) / h)
    else:
        margin = size = 0.0
    out["margin"] = (margin >= MIN_MARGIN, margin, True)
    out["size"] = (SIZE_RANGE[0] <= size <= SIZE_RANGE[1], size, True)
    out["resolution"] = (max(h, w) >= MIN_RES, max(h, w), True)
    luma = _luma(rgb)
    k = max(3, int(0.02 * max(h, w)) | 1)
    near = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    # detail only: studio gradients and soft floor shadows (raw std 7.4–11.1 on Z-Image greys) aren't clutter
    bg = (luma - cv2.GaussianBlur(luma, (0, 0), max(h, w) / 64))[near == 0]
    bg_std = float(bg.std()) if bg.size else 255.0
    out["uniform_background"] = (bg_std < MAX_BG_STD, bg_std, True)
    fg = luma[mask == 1]
    fg_std = float(fg.std()) if fg.size else 0.0
    out["shading"] = (fg_std >= MIN_FG_STD, fg_std, False)
    semi = float(((alpha > 0.1) & (alpha < 0.9)).sum() / max(mask.sum(), 1))
    out["few_semi_transparent"] = (semi < 0.05, semi, False)
    return {
        k: {"ok": bool(ok), "value": round(float(v), 4), "hard": hard}
        for k, (ok, v, hard) in out.items()
    }


def rank(scored: dict[str, dict]) -> dict[str, dict]:
    """{name: gates} → {name: {"gates", "hard_fails", "rank"}}, rank 1 = best (fewest hard fails, then soft)."""

    def key(name):
        g = scored[name]
        hard_fails = sum(not v["ok"] for v in g.values() if v["hard"])
        soft = g["shading"]["value"] / 255 - g["few_semi_transparent"]["value"]
        return hard_fails, -soft

    order = sorted(scored, key=key)
    return {
        name: {"gates": scored[name], "hard_fails": key(name)[0], "rank": order.index(name) + 1}
        for name in scored
    }


def subject_bbox(alpha: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(alpha > ALPHA_CUT)
    if xs.size == 0:
        raise ValueError(f"no subject: nothing above alpha {ALPHA_CUT}")
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def frame(rgb: np.ndarray, alpha: np.ndarray, side: int | None = None) -> tuple[np.ndarray, dict]:
    """Square RGBA around the subject: tight box at ALPHA_CUT + PADDING, black/transparent outside.
    side: a fixed crop size (multi-view: one scale for every view), centred on the subject."""
    h, w = alpha.shape
    x0, y0, x1, y1 = subject_bbox(alpha)
    side = side or round(max(x1 - x0 + 1, y1 - y0 + 1) * (1 + 2 * PADDING))
    cx, cy = (x0 + x1 + 1) // 2, (y0 + y1 + 1) // 2
    left, top = cx - side // 2, cy - side // 2
    rgba = np.zeros((side, side, 4), np.uint8)
    sx0, sy0, sx1, sy1 = max(left, 0), max(top, 0), min(left + side, w), min(top + side, h)
    rgba[sy0 - top : sy1 - top, sx0 - left : sx1 - left, :3] = rgb[sy0:sy1, sx0:sx1]
    a8 = (alpha[sy0:sy1, sx0:sx1] * 255 + 0.5).astype(np.uint8)
    rgba[sy0 - top : sy1 - top, sx0 - left : sx1 - left, 3] = a8
    out = min(side, OUT_MAX)
    if out != side:
        rgba = cv2.resize(rgba, (out, out), interpolation=cv2.INTER_AREA)
    info = {
        "source_size": [w, h],
        "subject_bbox": [x0, y0, x1, y1],
        "crop": {"left": left, "top": top, "side": side},
        "out_size": out,
        "alpha_cut": ALPHA_CUT,
        "padding": PADDING,
    }
    return rgba, info


BACKGROUNDS = {"black": 0.0, "grey": 0.5, "white": 1.0}
DARK, DARK_SHARE = 40, 0.15  # a subject with more than 15 % of its pixels under 40/255 is dark


def dark_share(rgba: np.ndarray) -> float:
    """The share of the subject's pixels that are near black (black fur, dark armour)."""
    fg = rgba[..., 3] > 127
    return float((rgba[..., :3][fg].mean(-1) < DARK).mean()) if fg.any() else 0.0


def on_background(rgba: np.ndarray, level: float) -> np.ndarray:
    """The cut-out on a flat grey `level` (0 black … 1 white): what the generator sees."""
    a = rgba[..., 3:] / 255.0
    return (rgba[..., :3].astype(np.float32) * a + 255.0 * level * (1 - a) + 0.5).astype(np.uint8)


def premultiply_black(rgba: np.ndarray) -> np.ndarray:
    """What the generator sees: RGB × alpha on black."""
    return (rgba[..., :3].astype(np.float32) * (rgba[..., 3:] / 255.0) + 0.5).astype(np.uint8)


def asset_prompt(version: Path, full: bool = False) -> str:
    """The asset's brief in the user's words, else its prompt_full, else the asset's name (a version folder in).
    The plain prompt first: prompt_full adds "full body, front view, soft key light", which fights a zoomed back view
    (refine); `full` puts prompt_full first (layers: a background's template carries its look)."""
    try:
        asset = json.loads((Path(version).parent / "asset.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Path(version).parent.name.replace("_", " ")
    brief = asset.get("brief") or {}
    first, second = ("prompt_full", "prompt") if full else ("prompt", "prompt_full")
    return brief.get(first) or brief.get(second) or asset.get("name") or Path(version).parent.name
