"""Project the generated image onto the texture (IMPLEMENTATION.md M23).

Input: a textured, UV-mapped version (bake's mesh.glb). The image: the prep version the mesh was generated
from (params.image names another prep version of this asset). The Faithful generator (Pixal3D) is
pixel-aligned with its conditioning image under a known camera, so where that camera sees the surface the
image can replace the baked colour, which the 1024 volume smears on a face.
params: {"region": "head" | "front", "strength": 1.0, "match": "local" | "mean" | false (true = local),
"image": "040_prep"?}. The image is upscaled 4× first whenever the `texture` model group is installed (M24).
Outputs: mesh.glb, basecolor.png, orm.png, normal.png (the last two copied from the input), overlay.png
(the image with the mesh silhouette's edge in red and the region band in yellow, for the panel).
"""

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from steps import _pose, _sr
from steps._common import StepError, main, progress

IOU_MIN = (
    0.8  # silhouette match below this: not this mesh's image, or the frame moved; change nothing
)
ZBUF = 2048  # the view's z-buffer, pixels
SHOULDERS, NOSE = (5, 6), 0  # COCO-WholeBody indices, as the pose model returns them


def camera(gen_meta: dict, frame: np.ndarray) -> dict | None:
    """How library-frame points land on the image ([0, 1]², u right, v down), the depth to sort them by,
    and the direction towards the camera: Pixal3D's perspective camera on +Z of the source frame (the
    Faithful weights; verified on the bench, IMPLEMENTATION M23). None for any other generator: TRELLIS
    Fast keeps no facing and no camera, and a silhouette cannot tell a face from the back of a head."""
    if gen_meta.get("metrics", {}).get("weights") != "faithful":
        return None
    inv = np.linalg.inv(frame)
    fov = float(gen_meta["metrics"]["fov"])
    t = math.tan(fov / 2)
    d = 0.5 / t  # inference.py's distance_from_fov: the unit cube fills the frame
    eye = frame[:3, :3] @ np.array([0.0, 0.0, d]) + frame[:3, 3]

    def project(p):
        s = p @ inv[:3, :3].T + inv[:3, 3]
        depth = d - s[:, 2]
        return np.c_[0.5 + s[:, 0] / (depth * 2 * t), 0.5 - s[:, 1] / (depth * 2 * t)], depth

    return {"name": "pixal3d", "fov": fov, "project": project, "towards": lambda p: eye - p}


def head_band(img: np.ndarray, alpha: np.ndarray) -> tuple[float, float, str]:
    """The head's band on the image, in pixel rows: full weight above the first value, none below the
    second. From the pose model's shoulders and nose (the chin lies between), else the top of the matte."""
    rows = np.nonzero(alpha.any(1))[0]
    pts, scores = _pose.keypoints_rgba(_pose.load(), img)
    if scores[list(SHOULDERS)].min() >= _pose.MIN_SCORE:
        y_sh = float(pts[list(SHOULDERS), 1].mean())
        y_nose = (
            float(pts[NOSE, 1])
            if scores[NOSE] >= _pose.MIN_SCORE
            else rows[0] + 0.4 * (y_sh - rows[0])
        )
        if (
            rows[0] <= y_nose < y_sh
        ):  # a nose on the figure, above the shoulders: the chin lies between
            return y_nose + 0.55 * (y_sh - y_nose), y_sh, "pose"
    h = rows[-1] - rows[0]
    return rows[0] + 0.12 * h, rows[0] + 0.18 * h, "top"


def shading_offset(base_t, uv, f, face_img, bary_img, pre, sigma_px: float):
    """Per z-buffer pixel: blur(the bake as the camera sees it) − blur(the image), colours in 0–255, zero
    where either is not there. Added to the projected image, it moves the image's large-scale shading onto
    the bake's flat albedo and leaves the image's detail in place. Blurred at 1/8 resolution with a
    Gaussian of `sigma_px`, masks carried along (normalised convolution)."""
    import torch
    import torch.nn.functional as F

    from steps._views import blur_premul

    seen = face_img >= 0
    size = face_img.shape[0]
    uvp = (uv[f[face_img[seen]]] * bary_img[seen][..., None]).sum(
        1
    )  # glTF uv of the seen surface point
    tex = base_t.permute(2, 0, 1)[None, :3] / 255
    col = F.grid_sample(
        tex,
        (uvp * 2 - 1).view(1, 1, -1, 2),
        mode="bilinear",
        padding_mode="border",
        align_corners=False,
    )
    view = torch.zeros(1, 4, size, size, device=base_t.device)
    view[0, :3][:, seen] = col[0, :, 0]
    view[0, 3][seen] = 1
    img_v = F.interpolate(pre, size=(size, size), mode="bilinear", align_corners=False)

    lv, li = blur_premul(view, sigma_px), blur_premul(img_v, sigma_px)
    both = (lv[:, 3:] > 0.05) & (li[:, 3:] > 0.05)
    shift = lv[:, :3] / lv[:, 3:].clamp(min=1e-3) - li[:, :3] / li[:, 3:].clamp(min=1e-3)
    return torch.where(both, shift, torch.zeros_like(shift)) * 255


def _erode(m: np.ndarray) -> np.ndarray:
    out = m.copy()
    out[1:-1, 1:-1] = m[1:-1, 1:-1] & m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:]
    return out


def overlay(img: np.ndarray, seen: np.ndarray, band, path: Path):
    """The image on grey, the mesh silhouette's edge in red, the region band's two rows in yellow."""
    size = img.shape[0]
    bg = Image.new("RGBA", (size, size), (64, 64, 64, 255))
    bg.alpha_composite(Image.fromarray(img))
    s = (
        np.asarray(Image.fromarray(seen.astype(np.uint8) * 255).resize((size, size), Image.NEAREST))
        > 0
    )
    rgb = np.asarray(bg.convert("RGB")).copy()
    rgb[s & ~_erode(_erode(s))] = (255, 40, 40)
    im = Image.fromarray(rgb)
    if band:
        draw = ImageDraw.Draw(im)
        for y in band:
            draw.line([(0, y), (size, y)], fill=(255, 220, 0), width=2)
    im.save(path)


def run(op, in_dir, out_dir, params):
    import torch
    import trimesh

    from steps._bake import fill_gutters, rasterize_uv
    from steps._views import cos_weight, facing_cos, write_textured, zbuffer
    from steps._views import visible as visible_
    from steps.bake import find_volume
    from steps.trellis2 import _image_version

    if not in_dir:
        raise StepError("missing_input", "project needs a textured, UV-mapped version (bake)")
    region = params.get("region", "head")
    match = params.get("match", True)
    match = {True: "local", None: False}.get(match, match)
    try:
        strength = float(params.get("strength", 1.0))
    except (TypeError, ValueError):
        strength = float("nan")
    if (
        region not in ("head", "front")
        or not 0 < strength <= 1
        or match not in (False, "mean", "local")
    ):
        raise StepError("bad_params", f"bad project params: {params}")
    src, out = Path(in_dir), Path(out_dir)
    meta = json.loads((src / "meta.json").read_text(encoding="utf-8"))
    glb = next((f for f in meta["outputs"].values() if f.endswith(".glb")), None)
    if not glb:
        raise StepError("missing_input", f"{meta['version']} has no .glb")
    mesh = trimesh.load(src / glb, force="mesh", process=False)
    mat = getattr(mesh.visual, "material", None)
    if getattr(mesh.visual, "uv", None) is None or getattr(mat, "baseColorTexture", None) is None:
        raise StepError(
            "missing_input", f"{glb} has no UVs or no base colour texture: run uv and bake first"
        )
    gen_dir, frame = find_volume(src)
    gen_meta = json.loads((gen_dir / "meta.json").read_text(encoding="utf-8"))
    prep = _image_version(src, params.get("image"))
    img = np.asarray(Image.open(prep / "image.png").convert("RGBA"))
    if img.shape[0] != img.shape[1]:
        raise StepError("missing_input", f"{prep.name}/image.png is not square")
    alpha = img[..., 3] > 128
    base = np.asarray(mat.baseColorTexture.convert("RGBA")).copy()
    size = base.shape[0]
    if base.shape[1] != size:
        raise StepError("missing_input", f"{glb}: the base colour texture is not square")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    v_np = np.asarray(mesh.vertices, float)
    cam = camera(gen_meta, frame)
    metrics: dict = {
        "region": region,
        "strength": strength,
        "image_from": prep.name,
        "texture_size": size,
    }
    if cam is None:
        weights = gen_meta.get("metrics", {}).get("weights", "?")
        metrics |= {"camera": None, "skipped": f"no aligned camera for weights={weights}"}
        note = f"Only Faithful models are aligned with their image (this one: {weights}): textures kept as they were."
        overlay(img, np.zeros(alpha.shape, bool), None, out / "overlay.png")
        return {
            "outputs": write_textured(out, mesh, mat, base, {"overlay": "overlay.png"}),
            "metrics": metrics,
            "note": note,
        }

    progress(0.1, "the mesh as the camera sees it")
    f = torch.tensor(mesh.faces, dtype=torch.long, device=dev)
    pix_v, depth_v = cam["project"](v_np)
    depth_v = torch.tensor(depth_v, dtype=torch.float32, device=dev)
    face_img, bary_img, zbuf = zbuffer(
        torch.tensor(pix_v, dtype=torch.float32, device=dev), depth_v, f, ZBUF
    )
    seen = face_img >= 0
    matte = Image.fromarray(alpha.astype(np.uint8) * 255).resize((ZBUF, ZBUF), Image.NEAREST)
    matte = torch.from_numpy(np.asarray(matte) > 0).to(dev)
    iou = float((seen & matte).sum() / max(1, int((seen | matte).sum())))
    metrics |= {"camera": cam["name"], "fov": round(cam["fov"], 4), "iou": round(iou, 3)}
    result: dict = {}
    band = None
    if region == "head" and iou >= IOU_MIN:
        progress(0.3, "the head on the image")
        v_full, v_zero, metrics["head_from"] = head_band(img, alpha)
        band = (v_full, v_zero)
        metrics["band"] = [round(v_full), round(v_zero)]
        result |= {"models": [{"id": _pose.MODEL}], "licenses": [_pose.MODEL]}
    overlay(img, seen.cpu().numpy(), band, out / "overlay.png")
    if iou < IOU_MIN:
        metrics["skipped"] = f"silhouette match {iou:.2f} below {IOU_MIN}"
        note = f"The image does not line up with the mesh (silhouette match {iou:.2f}): textures kept as they were."
        return {
            "outputs": write_textured(out, mesh, mat, base, {"overlay": "overlay.png"}),
            "metrics": metrics,
            "note": note,
        } | result

    progress(0.4, f"projecting onto {size}² texels")
    uv = torch.tensor(mesh.visual.uv, dtype=torch.float32, device=dev)
    uv[:, 1] = 1 - uv[:, 1]  # trimesh's OpenGL UVs → glTF UVs (what the file holds)
    face_id, bary = rasterize_uv(uv, f, size)
    covered = face_id >= 0
    corners = f[face_id[covered]]
    w3 = bary[covered][..., None]
    v = torch.tensor(v_np, dtype=torch.float32, device=dev)
    pts = (v[corners] * w3).sum(1).cpu().numpy().astype(float)
    pix, depth = cam["project"](pts)
    cos = facing_cos(v_np, np.asarray(mesh.faces), corners, w3, pts, cam["towards"])
    pix_t = torch.tensor(pix, dtype=torch.float32, device=dev)
    visible = visible_(zbuf, pix_t, torch.tensor(depth, dtype=torch.float32, device=dev), depth_v)
    # the image under each texel: bilinear on premultiplied colour, so the matte's soft edge brings no
    # fringe of the background; 4× upscaled first when the Real-ESRGAN weights are installed (M24)
    pre = torch.tensor(img, dtype=torch.float32, device=dev).permute(2, 0, 1)[None] / 255
    pre = torch.cat([pre[:, :3] * pre[:, 3:], pre[:, 3:]], 1)  # [1, 4, H, W]
    notes: list[str] = []
    metrics["upscaled"] = False
    try:
        net = _sr.load(dev)
    except FileNotFoundError as e:  # the switch is the model group: installed → used
        notes.append(f"The image was projected without the 4× upscale: {e}.")
    else:
        progress(0.5, "upscaling the image")
        rgb8 = (pre[0, :3] * 255 + 0.5).byte().permute(1, 2, 0).cpu().numpy()
        hi = torch.tensor(_sr.upscale(net, rgb8), dtype=torch.float32, device=dev) / 255
        del net
        a_hi = torch.nn.functional.interpolate(
            pre[:, 3:], scale_factor=_sr.SCALE, mode="bilinear", align_corners=False
        )
        pre = torch.cat([hi.permute(2, 0, 1)[None], a_hi], 1)
        metrics["upscaled"] = True
        result.setdefault("models", []).append({"id": _sr.MODEL})
        result.setdefault("licenses", []).append(_sr.MODEL)
    grid = (pix_t * 2 - 1).view(1, 1, -1, 2)
    samp = torch.nn.functional.grid_sample(
        pre, grid, mode="bilinear", padding_mode="zeros", align_corners=False
    )
    samp = samp[0, :, 0].T  # [T, 4]
    a = samp[:, 3:]
    proj = (samp[:, :3] / a.clamp(min=1e-6) * 255).clamp(0, 255)  # the upscaler can ring past white
    weight = torch.tensor(cos_weight(cos), dtype=torch.float32, device=dev)
    weight = weight * visible * a[:, 0]
    if band:
        v_px = pix_t[:, 1] * img.shape[0]
        weight = weight * ((band[1] - v_px) / (band[1] - band[0])).clamp(0, 1)

    progress(0.7, "blending")
    base_t = torch.tensor(base, dtype=torch.float32, device=dev)
    old = base_t[covered][:, :3]
    strong = weight > 0.5  # where the image lands, whatever strength the user dialled
    metrics["match"] = False
    if match and int(strong.sum()) >= 1000:
        if match == "local":
            # the lit image onto the delit albedo: the bake as the camera sees it and the image, both
            # blurred over about a head's height, give per pixel the colour shift that takes the image's
            # (ponytail: large-scale shading only; a sharp shadow edge, under a cap's brim, stays)
            # large-scale shading out and leaves its detail (a mean shift kept the shading; Marigold-IID's
            # albedo lost the detail: docs/bench/m24.md)
            rows = np.nonzero(alpha.any(1))[0]
            sigma = 0.08 * (rows[-1] - rows[0]) * ZBUF / img.shape[0]
            shift = shading_offset(base_t, uv, f, face_img, bary_img, pre, sigma)
            shift = torch.nn.functional.grid_sample(
                shift, grid, mode="bilinear", align_corners=False
            )
            proj = (proj + shift[0, :, 0].T).clamp(0, 255)
            metrics["match"] = {"mode": "local", "sigma_px": round(float(sigma))}
        else:
            c = old[strong].mean(0) - proj[strong].mean(0)
            proj = (proj + c).clamp(0, 255)
            metrics["match"] = {"mode": "mean", "offset": [round(x, 1) for x in c.tolist()]}
    w = (weight * strength)[:, None]
    new = old * (1 - w) + proj * w
    base_t[covered] = torch.cat([new, base_t[covered][:, 3:]], 1)
    rgba = fill_gutters(
        base_t.round().clamp(0, 255).to(torch.uint8).cpu().numpy(), covered.cpu().numpy()
    )
    metrics["changed"] = round(float(strong.float().mean()), 3)
    progress(0.9, "writing the textured mesh")
    out_result = {
        "outputs": write_textured(out, mesh, mat, rgba, {"overlay": "overlay.png"}),
        "metrics": metrics,
    } | result
    if notes:
        out_result["note"] = " ".join(notes)
    return out_result


if __name__ == "__main__":
    main(run)
