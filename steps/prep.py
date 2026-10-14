"""RGBA for the generator (IMPLEMENTATION.md M10): matte → square crop → image.png, image_rgb.png, crop.json.

Input: a `concepts` version with params {"pick": k}, or an `upload` version (image.*). An input that
already has a real alpha channel is used as cut out; otherwise BiRefNet mattes it.

op "views" (M17): a turnaround for Pixal3D-MV. params {"views": ["front", "right", "back", "left"],
"sources": [version, ...]?, "fov": 0.2, "height_tolerance": 0.05}: the parent's image split into
len(views) equal columns (a turnaround sheet), or one upload version per view (resized to the first's
height). "right"/"left": the character's right/left side faces the camera. One crop size for all views
(the cameras share a distance); view_<k>.png (+ _rgb) and cameras.json (Pixal3D transforms.json
convention: c2w in its Blender Z-up frame, view 0 = the main view); image(.png/_rgb) = the front view, so
every single-view step still works. Silhouette heights must agree within height_tolerance: views at
different zooms or of different poses would be fused into one wrong shape.
"""

import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from steps._common import StepError, main, progress
from steps._image import PADDING, frame, premultiply_black, subject_bbox

# camera azimuth about Z: "right" = the character's right side (camera at -X, the profile faces image-right)
VIEWS = {"front": 0, "right": -90, "back": 180, "left": 90}


def _image_of(version_dir: Path) -> np.ndarray:
    meta = json.loads((version_dir / "meta.json").read_text(encoding="utf-8"))
    src = meta["outputs"].get("image")
    if not src:
        raise StepError("missing_input", f"{meta['version']}: no image")
    return np.asarray(Image.open(version_dir / src).convert("RGBA"))


def _alpha(img: np.ndarray, net) -> np.ndarray:
    a = img[..., 3]
    if (a < 255).any():
        return a.astype(np.float32) / 255
    from steps import _birefnet

    return _birefnet.matte(net(), img[..., :3])


def views(in_dir, out_dir, params):
    names = params.get("views", ["front", "right", "back", "left"])
    fov, tol = float(params.get("fov", 0.2)), float(params.get("height_tolerance", 0.05))
    if not (
        2 <= len(names) <= 4
        and names[0] == "front"
        and len(set(names)) == len(names)
        and set(names) <= set(VIEWS)
        and 0.05 <= fov <= 1.6
    ):
        raise StepError("bad_params", f"views: 2-4 of {list(VIEWS)}, front first; got {params}")
    if not in_dir:
        raise StepError(
            "missing_input", "views needs a parent version (a turnaround sheet or the front view)"
        )
    src = Path(in_dir)
    if params.get("sources"):
        if len(params["sources"]) != len(names):
            raise StepError("bad_params", "one source version per view")
        imgs = [_image_of(src.parent / v) for v in params["sources"]]
        h = imgs[0].shape[0]
        imgs = [
            np.asarray(
                Image.fromarray(i).resize((round(i.shape[1] * h / i.shape[0]), h), Image.LANCZOS)
            )
            for i in imgs
        ]
    else:
        sheet = _image_of(src)
        cols = np.array_split(np.arange(sheet.shape[1]), len(names))
        imgs = [sheet[:, c[0] : c[-1] + 1] for c in cols]
    loaded = []

    def net():
        if not loaded:
            from steps import _birefnet

            progress(0.2, "BiRefNet matte")
            loaded.append(_birefnet.load())
        return loaded[0]

    alphas = [_alpha(i, net) for i in imgs]
    try:
        boxes = [subject_bbox(a) for a in alphas]
    except ValueError as e:
        raise StepError("failed", str(e)) from None
    heights = [y1 - y0 + 1 for _, y0, _, y1 in boxes]
    spread = max(heights) / min(heights) - 1
    if spread > tol:
        raise StepError(
            "failed",
            f"the views disagree on the subject's height by {spread:.0%} (> {tol:.0%}): {dict(zip(names, heights))} px."
            " Use views of one pose at one zoom.",
        )
    side = round(max(max(x1 - x0, y1 - y0) + 1 for x0, y0, x1, y1 in boxes) * (1 + 2 * PADDING))
    out, d, frames = Path(out_dir), 0.5 / math.tan(fov / 2), []
    for k, (name, img, a) in enumerate(zip(names, imgs, alphas)):
        rgba, _ = frame(img[..., :3], a, side)
        Image.fromarray(rgba, "RGBA").save(out / f"view_{k}.png")
        Image.fromarray(premultiply_black(rgba), "RGB").save(out / f"view_{k}_rgb.png")
        t = math.radians(VIEWS[name])
        rz = np.array(
            [
                [math.cos(t), -math.sin(t), 0, 0],
                [math.sin(t), math.cos(t), 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ]
        )
        front = np.array(
            [[1, 0, 0, 0], [0, 0, -1, -d], [0, 1, 0, 0], [0, 0, 0, 1.0]]
        )  # Pixal3D's front c2w
        frames.append(
            {
                "file_path": f"view_{k}_rgb.png",
                "view": name,
                "transform_matrix": (rz @ front).round(9).tolist(),
            }
        )
    shutil.copy(out / "view_0.png", out / "image.png")
    shutil.copy(out / "view_0_rgb.png", out / "image_rgb.png")
    cams = {"camera_angle_x": fov, "camera_distance": d, "frames": frames}
    (out / "cameras.json").write_text(json.dumps(cams, indent=2), encoding="utf-8")
    outputs = {"image": "image.png", "image_rgb": "image_rgb.png", "cameras": "cameras.json"}
    outputs |= {f"view_{k}": f"view_{k}.png" for k in range(len(names))}
    result = {"licenses": [], "models": []}
    if loaded:
        from steps import _birefnet

        result = {
            "licenses": [_birefnet.MODEL],
            "models": [{"id": _birefnet.MODEL, "revision": _birefnet.REVISION}],
        }
    metrics = {"views": names, "size": int(min(side, 1024)), "height_spread": round(spread, 4)}
    return result | {"outputs": outputs, "metrics": metrics}


def run(op, in_dir, out_dir, params):
    if op == "views":
        return views(in_dir, out_dir, params)
    if not in_dir:
        raise StepError("missing_input", "prep needs a parent version (concepts or upload)")
    meta = json.loads((Path(in_dir) / "meta.json").read_text(encoding="utf-8"))
    if "pick" in params:
        src = meta["outputs"].get(f"cand_{params['pick']}")
    else:
        src = meta["outputs"].get("image")
    if not src:
        raise StepError("missing_input", f"{meta['version']}: no image (pick {params.get('pick')})")
    img = np.asarray(Image.open(Path(in_dir) / src).convert("RGBA"))
    rgb, a = img[..., :3], img[..., 3]
    result = {"licenses": [], "models": []}
    if (a < 255).any():
        alpha = a.astype(np.float32) / 255  # the user's own cut-out
    else:
        from steps import _birefnet  # torch: only when we matte

        progress(0.2, "BiRefNet matte")
        alpha = _birefnet.matte(_birefnet.load(), rgb)
        result = {
            "licenses": [_birefnet.MODEL],
            "models": [{"id": _birefnet.MODEL, "revision": _birefnet.REVISION}],
        }
    try:
        rgba, info = frame(rgb, alpha)
    except ValueError as e:
        raise StepError("failed", str(e)) from None
    out = Path(out_dir)
    Image.fromarray(rgba, "RGBA").save(out / "image.png")
    Image.fromarray(premultiply_black(rgba), "RGB").save(out / "image_rgb.png")
    (out / "crop.json").write_text(json.dumps(info | {"source": src}, indent=2), encoding="utf-8")
    outputs = {"image": "image.png", "image_rgb": "image_rgb.png", "crop": "crop.json"}
    return result | {"outputs": outputs, "metrics": {"size": info["out_size"]}}


if __name__ == "__main__":
    main(run)
