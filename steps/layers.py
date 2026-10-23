"""Parallax layers from one picture (M55, research 15 §5.5): its depth (a `depth` version, MoGe-3) cut into bands far to
near, what the nearer bands hide drawn in by Z-Image's inpaint on the asset's own description, a scroll speed per
layer. GPU (Z-Image, about 8.5 GB), one-shot.

Input: a `depth` version (its depth.npz and image.png). Params:
  count: 2-5 (default 4): the layers; the sky (no depth) always goes to the farthest
  subject: false (default) | true: the picture's main subject (BiRefNet's cut-out) as the nearest layer, over count - 1
    depth bands (a figure in front of a background)
  prompt: what the hidden parts are drawn as (default: the asset's description with its kind's look), seed, steps
    (default 9); strength: 0.3-1 (default 0.8), how far Z-Image redraws the fill (each layer's own colours carried into
    what the nearer bands hide, OpenCV's inpaint): at 1 it draws a scene of its own, in another style
Outputs layer_<k>.png (0 the farthest; RGBA: layer k holds its own band and everything nearer, drawn in, so when the
nearer layers scroll past it shows what was behind them; the farthest is opaque everywhere), layers.json [{file,
scroll_scale, share}], bands.png (each band in a colour over the picture), preview.png (the layers side by side).
scroll_scale: the band's median disparity over the nearest band's, at least 0.05; a camera move of x px moves layer k
by x · scroll_scale.
"""

import json
import random
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from steps._common import StepError, main, progress
from steps._image import asset_prompt

MODEL, REVISION = (
    "Tongyi-MAI/Z-Image-Turbo",
    "f332072aa78be7aecdf3ee76d5c247082da564a6",
)  # = concepts'
SPECK = 0.002  # a piece of a band under this share of the picture joins the band round it
EMPTY = ", empty ground, nothing standing on it"
MARGIN = 0.35  # of the gap between two bands' centres: the zone round a cut that follows the depth's edges
COLOURS = np.array(
    [[40, 40, 140], [50, 140, 210], [90, 190, 90], [230, 180, 60], [220, 60, 60]], np.uint8
)


def kmeans1d(values: np.ndarray, k: int, rounds: int = 30) -> np.ndarray:
    """k sorted centres of 1D values (Lloyd's, started at the quantiles)."""
    centres = np.quantile(values, (np.arange(k) + 0.5) / k)
    for _ in range(rounds):
        side = np.digitize(values, (centres[1:] + centres[:-1]) / 2)
        new = np.array(
            [values[side == i].mean() if (side == i).any() else centres[i] for i in range(k)]
        )
        if np.allclose(new, centres):
            break
        centres = np.sort(new)
    return centres


def bands(disp: np.ndarray, valid: np.ndarray, n: int) -> np.ndarray:
    """(H, W) labels, 0 the farthest to n - 1 the nearest. The cuts fall in the gaps between the picture's planes
    (k-means on the disparity), not through a facade as equal shares would, and follow its edges: a pixel near a cut
    goes to the side a watershed reaches it from along the disparity's gradient, so an object leaning across a cut
    goes whole to one side (a car parked along the street was cut in two, the owner, 2026-10-13); only a surface that
    recedes smoothly (the road) is still cut. No depth (the sky) is the farthest; a speck joins the band round it; a
    band left empty is dropped."""
    sky = (~valid).mean() > 0.01
    k = n - 1 if sky else n
    smooth = ndimage.median_filter(disp, size=5)
    vals = smooth[valid]
    if not len(vals):  # nothing but sky: one band (the step refuses such a picture first)
        return np.zeros(disp.shape, np.int16)
    if len(vals) > 200_000:
        vals = np.random.default_rng(0).choice(vals, 200_000, replace=False)
    centres = kmeans1d(vals, k) if k > 1 else np.array([0.5])
    cuts = (centres[1:] + centres[:-1]) / 2
    labels = np.where(valid, np.digitize(smooth, cuts) + sky, 0)
    near = np.zeros(disp.shape, bool)  # within 35 % of the gap of a cut: the watershed decides
    for i, cut in enumerate(cuts):
        near |= valid & (np.abs(smooth - cut) < MARGIN * (centres[i + 1] - centres[i]))
    if near.any():
        grad = ndimage.gaussian_gradient_magnitude(smooth, 1.0)
        top = max(float(np.percentile(grad, 99.5)), 1e-6)
        grad16 = (np.clip(grad / top, 0, 1) * 65535).astype(np.uint16)
        labels = ndimage.watershed_ift(grad16, np.where(near, 0, labels + 1).astype(np.int16)) - 1
    labels = labels.astype(np.int16)
    for b in range(n):
        # 8-connected: a speck's diagonal neighbours of its own band are part of it, never its ring
        comp, _ = ndimage.label(labels == b, structure=np.ones((3, 3)))
        for i, box in enumerate(ndimage.find_objects(comp), 1):
            region = comp[box] == i
            if region.sum() >= SPECK * labels.size:
                continue
            # the box grown by 2 px: the ring round the speck
            grow = tuple(slice(max(s.start - 2, 0), s.stop + 2) for s in box)
            piece = comp[grow] == i
            ring = ndimage.binary_dilation(piece, iterations=2) & ~piece
            if ring.any():
                labels[grow][piece] = np.bincount(labels[grow][ring]).argmax()
    used = np.unique(labels)
    return np.searchsorted(used, labels).astype(np.int16)  # 0 .. len(used) - 1, the order kept


def scroll_scales(disp: np.ndarray, labels: np.ndarray) -> list[float]:
    """Per layer: its median disparity over the nearest one's (parallax goes with disparity), at least 0.05."""
    med = [float(np.median(disp[labels == k])) for k in range(int(labels.max()) + 1)]
    return [round(max(0.05, m / max(med[-1], 1e-6)), 3) for m in med]


def _params(params: dict) -> dict:
    p = {
        "count": params.get("count", 4),
        "subject": params.get("subject", False),
        "prompt": params.get("prompt"),
        "seed": params.get("seed", random.randrange(2**31)),
        "steps": params.get("steps", 9),
        "strength": params.get("strength", 0.8),
    }
    ok = (
        isinstance(p["count"], int)
        and 2 <= p["count"] <= 5
        and isinstance(p["subject"], bool)
        and (p["prompt"] is None or isinstance(p["prompt"], str))
        and isinstance(p["seed"], int)
        and isinstance(p["steps"], int)
        and 1 <= p["steps"] <= 50
        and isinstance(p["strength"], int | float)
        and 0.3 <= p["strength"] <= 1
    )
    if not ok:
        raise StepError(
            "bad_params", "layers: count 2-5; subject true or false; steps 1-50; strength 0.3-1"
        )
    return p


def _pipeline(size: tuple[int, int]):
    """Z-Image's inpaint pipeline as concepts loads it (the DiT stored fp8), the VAE tiled above 1024 px."""
    import torch
    from diffusers import ZImageInpaintPipeline

    try:
        pipe = ZImageInpaintPipeline.from_pretrained(
            MODEL, revision=REVISION, torch_dtype=torch.bfloat16, local_files_only=True
        )
    except OSError:  # the layers group brings MoGe only; Z-Image comes with Concept images
        raise StepError(
            "missing_input", "the picture model is not installed: Setup, Concept images"
        ) from None
    pipe.transformer.enable_layerwise_casting(
        storage_dtype=torch.float8_e4m3fn, compute_dtype=torch.bfloat16
    )
    if max(size) > 1024:
        pipe.vae.enable_tiling()
    return pipe


def run(op, in_dir, out_dir, params):
    if op != "run":
        raise StepError("bad_params", f"op {op!r}: only run")
    if not in_dir or not (Path(in_dir) / "depth.npz").is_file():
        raise StepError(
            "missing_input", "layers needs a depth version (the step depth on a picture)"
        )
    p = _params(params)
    import torch

    t0, src, out = time.time(), Path(in_dir), Path(out_dir)
    picture = Image.open(src / "image.png").convert("RGB")
    with np.load(src / "depth.npz") as d:
        disp, valid = d["disparity"].astype(np.float32), d["valid"]
    if disp.shape != (picture.height, picture.width):
        raise StepError("missing_input", f"{src.name}: the depth and the picture differ in size")
    if not valid.any():
        raise StepError(
            "failed", "no depth in this picture (all sky to MoGe): nothing to put in layers"
        )
    progress(0.05, "bands")
    labels = bands(disp, valid, p["count"] - p["subject"])
    if p["subject"]:
        from steps import _birefnet

        matte = _birefnet.matte(_birefnet.load(), np.asarray(picture)) > 0.5
        torch.cuda.empty_cache()
        labels = np.where(matte, labels.max() + 1, labels)
        labels = np.searchsorted(np.unique(labels), labels).astype(
            np.int16
        )  # a band it covered whole: gone
    n = int(labels.max()) + 1
    rgb = np.asarray(picture)
    # what the nearer bands hide is ground and the scenery behind: the description lists its cars and lamps, which the
    # drawing repeated there until it was told the ground is empty (m55.md)
    prompt = (p["prompt"] or asset_prompt(src, full=True)).strip() + EMPTY
    # Z-Image draws on a 64 px grid: the picture goes in at the nearest such size and its drawing comes back
    w64, h64 = (max(256, round(x / 64) * 64) for x in picture.size)
    progress(0.1, "loading Z-Image")
    pipe = _pipeline((w64, h64))
    torch.cuda.reset_peak_memory_stats()
    pipe.transformer.to("cpu")
    pipe.text_encoder.to("cuda")
    with torch.inference_mode():
        embeds, _ = pipe.encode_prompt([prompt], device="cuda", do_classifier_free_guidance=False)
    pipe.text_encoder.to("cpu")
    torch.cuda.empty_cache()
    pipe.transformer.to("cuda")
    pipe.vae.to("cuda")
    grow = max(2, picture.height // 100)  # the nearer bands' fringe goes with them
    layers = []
    for k in range(n):
        alpha = labels >= k  # its own band and everything nearer: the farthest is the whole picture
        colour = rgb
        if k < n - 1:  # what the nearer bands hide, drawn in
            progress(0.15 + 0.75 * k / n, f"layer {k + 1}/{n}: what is behind the nearer ones")
            hidden = ndimage.binary_dilation(labels > k, iterations=grow)
            mask = Image.fromarray((hidden * 255).astype(np.uint8)).resize((w64, h64))
            drawn = pipe(
                image=Image.fromarray(_fill(rgb, hidden)).resize((w64, h64)),
                mask_image=mask,
                prompt_embeds=[embeds[0]],
                height=h64,
                width=w64,
                strength=float(p["strength"]),
                num_inference_steps=p["steps"],
                guidance_scale=0.0,
                generator=torch.Generator("cpu").manual_seed(p["seed"] + k),
            ).images[0]
            drawn = np.asarray(drawn.convert("RGB").resize(picture.size, Image.LANCZOS))
            colour = np.where(hidden[..., None], drawn, rgb)
        a = np.full(alpha.shape, 255, np.uint8) if k == 0 else (alpha * 255).astype(np.uint8)
        Image.fromarray(np.dstack([colour, a])).save(out / f"layer_{k}.png")
        layers.append(f"layer_{k}.png")
    peak = torch.cuda.max_memory_allocated() / 2**30
    pipe.to("cpu")
    del pipe
    torch.cuda.empty_cache()
    scales = scroll_scales(disp, labels)
    shares = [round(float((labels == k).mean()), 3) for k in range(n)]
    data = [{"file": f, "scroll_scale": s, "share": sh} for f, s, sh in zip(layers, scales, shares)]
    (out / "layers.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    Image.fromarray((rgb * 0.45 + COLOURS[labels % len(COLOURS)] * 0.55).astype(np.uint8)).save(
        out / "bands.png"
    )
    _strip([out / f for f in layers]).save(out / "preview.png")
    return {
        "outputs": {f"layer_{k}": f for k, f in enumerate(layers)}
        | {"layers": "layers.json", "bands": "bands.png", "preview": "preview.png"},
        "metrics": {
            "seconds": round(time.time() - t0, 1),
            "peak_vram_gb": round(peak, 2),
            "count": n,
            "scroll_scales": scales,
            "shares": shares,
            "seed": p["seed"],
        },
        "models": [{"id": MODEL, "revision": REVISION}],
        "licenses": [MODEL],
    }


def _fill(rgb: np.ndarray, hidden: np.ndarray, scale: int = 4) -> np.ndarray:
    """The picture with what `hidden` covers filled from the rest's colours (OpenCV's Telea inpaint, at 1/scale for
    speed): the start Z-Image redraws from, so a sky goes on as sky and a far facade in that facade's colours."""
    import cv2

    h, w = hidden.shape
    size = (w // scale, h // scale)
    small = cv2.resize(rgb, size, interpolation=cv2.INTER_AREA)
    mask = cv2.resize(hidden.astype(np.uint8) * 255, size, interpolation=cv2.INTER_NEAREST)
    filled = cv2.inpaint(small, mask, 5, cv2.INPAINT_TELEA)
    filled = cv2.resize(filled, (w, h), interpolation=cv2.INTER_CUBIC)
    return np.where(hidden[..., None], filled, rgb)


def _strip(files: list[Path], height: int = 160) -> Image.Image:
    """The layers side by side on a checkerboard, far to near: the version's thumbnail."""
    ims = [Image.open(f) for f in files]
    w = round(ims[0].width * height / ims[0].height)
    out = Image.new("RGB", (len(ims) * (w + 8) - 8, height), (40, 44, 48))
    cell = 16
    yy, xx = np.mgrid[:height, :w]
    board = np.where(((yy // cell + xx // cell) % 2)[..., None], 200, 150).astype(np.uint8)
    board = Image.fromarray(np.repeat(board, 3, -1), "RGB")
    for i, im in enumerate(ims):
        tile = board.copy()
        tile.paste(im.resize((w, height)), (0, 0), im.resize((w, height)))
        out.paste(tile, (i * (w + 8), 0))
    return out


if __name__ == "__main__":
    main(run)
