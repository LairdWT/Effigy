"""Capture a static mesh view and project a reviewed image onto its existing atlas."""
import json
import os
import re
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import trimesh
from PIL import Image
from scipy.ndimage import distance_transform_edt

from server import library
from steps import _glb
from steps._bake import rasterize_uv
from steps._common import StepError, asset_directory, main, progress
from steps._paint_mask import capture_mask, mask_image, number, parse_mask
from steps._paint_projection import sample_replacement
from steps._views import ortho, render, zbuffer


def version_dir(asset: Path, name: object) -> Path:
    if not isinstance(name, str) or re.fullmatch(r"\d{3,}_[a-z0-9_]+", name) is None:
        raise StepError("bad_params", "Select a saved version in this asset")
    path = (asset / name).resolve()
    if path.parent != asset.resolve() or not (path / "meta.json").is_file():
        raise StepError("missing_input", f"Saved version {name!r} is unavailable in this asset")
    return path


def metadata(folder: Path) -> dict:
    return json.loads((folder / "meta.json").read_text(encoding="utf-8"))


def local_file(folder: Path, name: object) -> Path:
    if not isinstance(name, str):
        raise StepError("missing_input", "The selected version has no required output")
    path = (folder / name).resolve()
    if not path.is_relative_to(folder.resolve()) or not path.is_file():
        raise StepError("missing_input", "The selected output is missing or outside its version")
    return path


def load_mesh(folder: Path) -> tuple:
    meta = metadata(folder)
    key = next((k for k, f in meta["outputs"].items() if f.endswith(".glb")), None)
    if key is None:
        raise StepError("missing_input", "Select a version with a mesh")
    path = library.resolve_output(folder, key)
    doc, blob = _glb.read(path)
    if len(doc.get("buffers", [])) != 1 or "uri" in doc["buffers"][0]:
        raise StepError("missing_input", "Surface paint needs a self-contained GLB buffer")
    if any("uri" in image for image in doc.get("images", [])):
        raise StepError("missing_input", "Embed the texture images in the GLB before painting")
    primitives = [p for mesh in doc.get("meshes", []) for p in mesh["primitives"]]
    if len(primitives) != 1 or doc.get("skins") or doc.get("animations"):
        raise StepError("missing_input", "Surface paint currently needs one static mesh primitive; use a static baked copy")
    primitive = primitives[0]
    if primitive.get("targets") or primitive.get("mode", 4) != 4:
        raise StepError("missing_input", "Surface paint needs static triangles without morph targets")
    material_id = primitive.get("material")
    if material_id is None:
        raise StepError("missing_input", "Bake a base-colour atlas before surface painting")
    material = doc["materials"][material_id]
    pbr = material.get("pbrMetallicRoughness", {})
    binding = pbr.get("baseColorTexture")
    if binding is None or binding.get("texCoord", 0) != 0 or binding.get("extensions"):
        raise StepError("missing_input", "Surface paint needs a base-colour atlas on UV0 without a texture transform")
    if pbr.get("baseColorFactor", [1, 1, 1, 1]) != [1, 1, 1, 1]:
        raise StepError("missing_input", "Bake the material colour factor into the atlas before painting")
    texture = doc["textures"][binding["index"]]
    if "source" not in texture or texture.get("extensions"):
        raise StepError("missing_input", "Bake the compressed texture into a PNG atlas before painting")
    scene = trimesh.load(path, force="scene", process=False)
    mesh = scene.to_geometry()
    mat = getattr(mesh.visual, "material", None)
    base_image = getattr(mat, "baseColorTexture", None)
    if getattr(mesh.visual, "uv", None) is None or base_image is None:
        raise StepError("missing_input", "Mesh needs UVs and a local base-colour texture")
    if base_image.width != base_image.height or base_image.width > 4096:
        raise StepError("missing_input", "Surface paint supports square atlases up to 4096; keep this asset at 1024")
    image = doc["images"][texture["source"]]
    if "bufferView" not in image:
        raise StepError("missing_input", "Embed the base-colour image before painting")
    image_view = doc["bufferViews"][image["bufferView"]]
    offset = image_view.get("byteOffset", 0)
    encoded = np.frombuffer(blob, dtype=np.uint8, count=image_view["byteLength"], offset=offset)
    decoded = cv2.imdecode(encoded, cv2.IMREAD_UNCHANGED)
    if decoded is None or decoded.dtype not in (np.uint8, np.uint16):
        raise StepError("missing_input", "Base colour must decode as an 8-bit or 16-bit image")
    if decoded.ndim == 2:
        base = cv2.cvtColor(decoded, cv2.COLOR_GRAY2RGBA)
    elif decoded.ndim == 3 and decoded.shape[2] in (3, 4):
        base = cv2.cvtColor(decoded, cv2.COLOR_BGRA2RGBA if decoded.shape[2] == 4 else cv2.COLOR_BGR2RGBA)
    else:
        raise StepError("missing_input", "Unsupported base-colour image channels")
    uv = np.asarray(mesh.visual.uv, dtype=np.float32).copy()
    uv[:, 1] = 1 - uv[:, 1]
    if not np.isfinite(uv).all() or np.any(uv < -1e-5) or np.any(uv > 1.00001):
        raise StepError("missing_input", "Use a unique atlas inside UV 0-1; tiled UVs need baking first")
    return path, doc, blob, material_id, mesh, base, uv


def camera_params(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != {"yaw", "pitch", "center", "extent"}:
        raise StepError("bad_params", "Capture needs the viewer's yaw, pitch, center and extent")
    center = value["center"]
    if not isinstance(center, list) or len(center) != 3:
        raise StepError("bad_params", "Camera center needs three coordinates")
    return {
        "yaw": number(value["yaw"], -360, 360, "Yaw"),
        "pitch": number(value["pitch"], -90, 90, "Pitch"),
        "center": [number(x, -1e6, 1e6, "Camera center") for x in center],
        "extent": number(value["extent"], 0.0001, 1e6, "View extent"),
    }


def reject_uv_overlap(uv: np.ndarray, faces: np.ndarray, size: int) -> None:
    """Reject overlapping triangle interiors at atlas texel centres, excluding shared edges."""
    occupied = np.zeros((size, size), dtype=bool)
    for triangle in uv[faces] * size:
        a, b, c = triangle
        lo = np.maximum(np.ceil(triangle.min(0) - 0.5).astype(int), 0)
        hi = np.minimum(np.floor(triangle.max(0) - 0.5).astype(int), size - 1)
        if np.any(hi < lo):
            continue
        ab, ac = b - a, c - a
        determinant = ab[0] * ac[1] - ab[1] * ac[0]
        if abs(determinant) < 1e-8:
            continue
        yy, xx = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        x, y = xx + 0.5 - a[0], yy + 0.5 - a[1]
        u = (x * ac[1] - y * ac[0]) / determinant
        v = (ab[0] * y - ab[1] * x) / determinant
        inside = (u > 1e-5) & (v > 1e-5) & (u + v < 0.99999)
        region = occupied[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        if np.any(region & inside):
            raise StepError("missing_input", "Atlas UV interiors overlap; unwrap and repack a copy before painting")
        region |= inside


def write_atlas(out: Path, doc: dict, blob: bytearray, material_id: int, rgba: np.ndarray) -> None:
    success, encoded = cv2.imencode(".png", cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
    if not success:
        raise StepError("failed", "Could not encode the painted atlas")
    png = encoded.tobytes()
    blob.extend(b"\0" * (-len(blob) % 4))
    views = doc.setdefault("bufferViews", [])
    views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(png)})
    blob.extend(png)
    doc["buffers"][0]["byteLength"] = len(blob)
    images = doc.setdefault("images", [])
    images.append({"bufferView": len(views) - 1, "mimeType": "image/png"})
    binding = doc["materials"][material_id]["pbrMetallicRoughness"]["baseColorTexture"]
    textures = doc["textures"]
    textures.append({**textures[binding["index"]], "source": len(images) - 1})
    binding["index"] = len(textures) - 1
    blob = _glb.compact_images(doc, blob)
    _glb.write(out / "mesh.glb", doc, blob)
    (out / "basecolor.png").write_bytes(png)


def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    if in_dir is None:
        raise StepError("missing_input", "Select a textured mesh before painting")
    if op not in ("capture", "apply"):
        raise StepError("bad_params", "Paint operation must be capture or apply")
    trial = os.environ.get("EFFIGY_MULTI_VIEW") == "1"
    allowed = ({"view", "size", "heal", "appearance"} if trial else {"view", "size"}) if op == "capture" else {"image", "mask", "strength", "feather", "texture_size"}
    if set(params) - allowed:
        raise StepError("bad_params", f"Unknown paint parameters: {sorted(set(params) - allowed)}")
    src, out = Path(in_dir), Path(out_dir)
    _path, doc, blob, material_id, mesh, base, uv_np = load_mesh(src)
    size = base.shape[0]
    reject_uv_overlap(uv_np, mesh.faces, size)
    device = "cpu"
    uv = torch.tensor(uv_np, device=device)
    faces = torch.tensor(np.asarray(mesh.faces), dtype=torch.long, device=device)
    vertices = np.asarray(mesh.vertices, dtype=float)
    channel_max = np.iinfo(base.dtype).max
    base_t = torch.tensor(base.astype(np.float32) * (255.0 / channel_max), device=device)
    if op == "capture":
        view = camera_params(params.get("view"))
        resolution = params.get("size", 1024)
        if resolution not in (512, 768, 1024):
            raise StepError("bad_params", "Capture size must be 512, 768 or 1024")
        progress(0.2, "capturing the mesh's base colour and fixed camera")
        rgb, alpha, _, raster = render(base_t, uv, faces, vertices, ortho(**view), resolution)
        rgba = torch.cat([rgb, alpha[..., None]], dim=-1).cpu().numpy()
        Image.fromarray((rgba * 255).round().astype(np.uint8)).save(out / "image.png")
        ids = raster[0].cpu().numpy().astype(np.int64) + 1
        encoded_ids = np.stack([ids & 255, (ids >> 8) & 255, (ids >> 16) & 255], axis=-1).astype(np.uint8)
        Image.fromarray(encoded_ids).save(out / "faces.png")
        extras, seam = {}, None
        if params.get("heal") is not None and type(params["heal"]) is not bool:
            raise StepError("bad_params", "Heal capture must be true or false")
        if params.get("heal"):
            from steps._paint_seams import suggest_seams

            guide, seam = suggest_seams(src, view, uv, faces, vertices, (rgba * 255).round().astype(np.uint8))
            guide.save(out / "seam-mask.png")
            extras["seam_mask"] = "seam-mask.png"
        appearance = metadata(src).get("metrics", {}).get("appearance")
        asset_data = json.loads((src.parent / "asset.json").read_text(encoding="utf-8"))
        appearance = asset_data.get("appearance", appearance)
        if "appearance" in params:
            supplied = params["appearance"]
            if not isinstance(supplied, dict) or set(supplied) != {"revision", "materials", "style", "preserve", "model", "denoise", "steps"}:
                raise StepError("bad_params", "Capture appearance needs the complete appearance record")
            if any(not isinstance(supplied[key], str) or len(supplied[key]) > 20000 for key in ("materials", "style", "preserve", "model")):
                raise StepError("bad_params", "Capture appearance text is invalid")
            number(supplied["denoise"], 0.01, 1, "Appearance denoise")
            number(supplied["steps"], 1, 50, "Appearance steps")
            appearance = supplied
        return {"outputs": {"mesh": "@mesh.glb", "image": "image.png", "face_ids": "faces.png", **extras},
                "output_refs": {"mesh": {"version": src.name, "key": next(k for k, f in metadata(src)["outputs"].items() if f.endswith(".glb"))}},
                "metrics": {"source": src.name, "view": view, "size": resolution,
                            "appearance": appearance, "seam_suggestion": seam,
                            "geometry_revision": library.geometry_revision(src),
                            "texture_size": size, "bit_depth": base.dtype.itemsize * 8,
                            "triangles": len(mesh.faces), "device": device}}

    if params.get("texture_size", "keep") != "keep":
        raise StepError("bad_params", "Surface painting keeps the source atlas size")
    strength = number(params.get("strength", 1), 0.01, 1, "Apply strength")
    feather = number(params.get("feather", 8), 0, 32, "Inward mask edge blend")
    asset = asset_directory(src)
    candidate = version_dir(asset, params.get("image"))
    candidate_meta = metadata(candidate)
    if candidate_meta["step"] != "reference" or candidate_meta["params"].get("op") != "edit":
        raise StepError("bad_params", "Select an edited image made from a captured paint view")
    captured = version_dir(asset, candidate_meta["parent"])
    capture_meta = metadata(captured)
    if capture_meta["step"] != "paint" or capture_meta["params"].get("op") != "capture":
        raise StepError("bad_params", "The image must descend directly from a captured paint view")
    if capture_meta["parent"] != src.name:
        raise StepError("bad_params", "This image belongs to a different source mesh version; capture the current version")
    view = camera_params(capture_meta["metrics"]["view"])
    resolution = int(capture_meta["metrics"]["size"])
    picture = Image.open(local_file(candidate, candidate_meta["outputs"].get("image"))).convert("RGB")
    if picture.size != (resolution, resolution):
        raise StepError("bad_params", "Edited image dimensions differ from the captured view; regenerate at the capture size")
    mask = parse_mask(params.get("mask", candidate_meta["params"].get("paint_mask")))
    if mask.faces is not None:
        if mask.revision != library.geometry_revision(src):
            raise StepError("bad_params", "Face selection belongs to different geometry; select faces again")
        if not mask.faces or max(mask.faces) >= len(mesh.faces):
            raise StepError("bad_params", "Face selection is empty or includes missing triangles")
    selection = capture_mask(captured, mask) if trial else mask_image(mask, resolution)
    generation_mask = None
    generation_faces = None
    requested_feather = feather
    preview_feather = 0
    if candidate_meta["params"].get("paint_mode") == "masked":
        preview_feather = number(candidate_meta["params"].get("mask_feather", 8), 0, 32, "Preview edge blend")
        if trial and preview_feather > 0:
            feather = 0
        with Image.open(local_file(candidate, candidate_meta["outputs"].get("write_mask"))) as generated_mask:
            if generated_mask.size != (resolution, resolution):
                raise StepError("bad_params", "Candidate mask does not match the captured view")
            generation_mask = np.asarray(generated_mask.convert("L")) > 0
        requested = np.asarray(capture_mask(captured, mask)) > 0
        if np.any(requested & ~generation_mask):
            raise StepError("bad_params", "Selection extends beyond this preview's generated area. Generate a new preview for the wider selection.")
        generation_faces = parse_mask(candidate_meta["params"]["paint_mask"]).faces
    if selection.getbbox() is None:
        raise StepError("bad_params", "Selection is empty; paint a region or choose the whole visible surface")
    selection.save(out / "selection.png")
    cam = ortho(**view)
    progress(0.15, "resolving selected front-visible UV texels")
    before, alpha, _, raster = render(base_t, uv, faces, vertices, cam, resolution)
    face_img, _, _, _, _ = raster
    owner, bary = rasterize_uv(uv, faces, size)
    covered = owner >= 0
    triangle_ids = owner[covered]
    points = (torch.tensor(vertices, dtype=torch.float32, device=device)[faces[triangle_ids]]
              * bary[covered][..., None]).sum(1).cpu().numpy()
    pixels, _ = cam["project"](points)
    pix = torch.tensor(pixels, dtype=torch.float32, device=device)
    in_view = (pix >= 0).all(1) & (pix < 1).all(1)
    pxy = (pix * face_img.shape[0]).long()
    x = pxy[:, 0].clamp(0, face_img.shape[1] - 1)
    y = pxy[:, 1].clamp(0, face_img.shape[0] - 1)
    visible = face_img[y, x] == triangle_ids
    normal = np.asarray(mesh.face_normals)[triangle_ids.cpu().numpy()]
    facing = (normal * cam["towards"](points)).sum(1)
    grid = (pix * 2 - 1).view(1, 1, -1, 2)
    selection_values = np.asarray(selection).copy().astype(np.float32) / 255
    if generation_mask is not None:
        selection_values *= generation_mask
    if mask.faces is not None:
        screen_faces = cv2.resize(face_img.cpu().numpy().astype(np.float32),
                                  (resolution, resolution), interpolation=cv2.INTER_NEAREST).astype(np.int64)
        selection_values *= np.isin(screen_faces, mask.faces)
        Image.fromarray((selection_values * 255).astype(np.uint8)).save(out / "selection.png")
    if feather > 0 and (not mask.whole or mask.faces is not None or mask.strokes):
        selection_values *= np.minimum(distance_transform_edt(selection_values > 0) / feather, 1)
    selected = torch.tensor(selection_values, device=device, dtype=torch.float32)[None, None]
    silhouette = -F.max_pool2d(-(alpha > 0.99).float()[None, None], 5, 1, 2)
    weights = F.grid_sample(selected * silhouette, grid, mode="nearest", align_corners=False)[0, 0, 0]
    background_rejected = 0
    if candidate_meta["params"].get("model") == "flux-ghibli":
        white = (np.asarray(picture).min(axis=2) >= 245).astype(np.uint8)
        _, components = cv2.connectedComponents(white, connectivity=4)
        boundary = np.unique(np.concatenate((components[0], components[-1], components[:, 0], components[:, -1])))
        boundary = boundary[boundary != 0]
        foreground = (~np.isin(components, boundary)).astype(np.uint8)
        foreground = cv2.erode(foreground, np.ones((3, 3), dtype=np.uint8))
        foreground_t = torch.tensor(foreground, dtype=torch.float32, device=device)[None, None]
        image_permission = F.grid_sample(foreground_t, grid, mode="nearest", align_corners=False)[0, 0, 0]
        background_rejected = int(((weights > 0) & (image_permission == 0)).sum())
        weights *= image_permission
    permission = weights > 0
    permission &= visible & in_view & torch.tensor(facing > 0.25, device=device)
    if mask.faces is not None:
        permission &= torch.isin(triangle_ids, torch.tensor(mask.faces, dtype=torch.long, device=device))
    if generation_faces is not None:
        permission &= torch.isin(triangle_ids, torch.tensor(generation_faces, dtype=torch.long, device=device))
    source_rgb = base[covered.cpu().numpy(), :3].astype(np.float32)
    if trial:
        with Image.open(library.resolve_output(captured, "image")) as captured_picture:
            original_capture = np.asarray(captured_picture.convert("RGBA")).copy()
        projected_vertices, projected_depth = cam["project"](vertices)
        sample_faces, _, _ = zbuffer(torch.tensor(projected_vertices, dtype=torch.float32),
                                      torch.tensor(projected_depth, dtype=torch.float32), faces, resolution)
        samples = sample_replacement(original_capture[..., :3], np.asarray(picture), pixels,
                                     sample_faces.numpy(), triangle_ids.numpy(),
                                     selection_values > 0, original_capture[..., 3] == 255)
        permission &= torch.tensor(samples.supported)
        new_rgb = np.where(samples.changed[:, None], samples.values * (channel_max / 255.0), source_rgb)
    else:
        rgb = torch.tensor(np.asarray(picture).copy(), device=device, dtype=torch.float32).permute(2, 0, 1)[None]
        sampled = F.grid_sample(rgb, grid, mode="bilinear", padding_mode="border", align_corners=False)[0, :, 0].T
        new_rgb = sampled.cpu().numpy() * (channel_max / 255.0)
    result = base.copy()
    permitted = np.zeros((size, size), dtype=bool)
    permitted[covered.cpu().numpy()] = permission.cpu().numpy()
    if not permitted.any():
        raise StepError("bad_params", "Selection contains no front-visible non-grazing surface; reframe or widen it")
    amount = weights.cpu().numpy()[:, None] * strength
    blended = np.rint(source_rgb * (1 - amount) + new_rgb * amount).clip(0, channel_max).astype(base.dtype)
    result[permitted, :3] = blended[permission.cpu().numpy()]
    cov = covered.cpu().numpy()
    wide = (rasterize_uv(uv, faces, size * 2)[0] >= 0).view(size, 2, size, 2).any(3).any(1).cpu().numpy()
    distances, nearest = distance_transform_edt(~cov, return_indices=True)
    surface_changed = np.any(result != base, axis=2)
    gutter = (~wide) & (distances <= 8) & permitted[nearest[0], nearest[1]]
    if trial:
        gutter &= surface_changed[nearest[0], nearest[1]]
    result[gutter, :3] = result[nearest[0][gutter], nearest[1][gutter], :3]
    changed = np.any(result != base, axis=2)
    if np.any(changed & ~(permitted | gutter)) or np.any(result[..., 3] != base[..., 3]):
        raise StepError("failed", "Projection changed protected pixels; candidate was not published")
    progress(0.8, "saving a new texture version with the original geometry")
    write_atlas(out, doc, blob, material_id, result)
    Image.fromarray(permitted.astype(np.uint8) * 255).save(out / "permission.png")
    after_t = torch.tensor(result.astype(np.float32) * (255.0 / channel_max), device=device)
    after, _, _, _ = render(after_t, uv, faces, vertices, cam, resolution)
    comparison = torch.cat([before, after], dim=1).cpu().numpy()
    Image.fromarray((comparison * 255).round().clip(0, 255).astype(np.uint8)).save(out / "comparison.png")
    review_outputs = {}
    if trial:
        from steps._paint_set import Surface, review

        review(Surface(src), result, out)
        review_outputs = {"review": "review.png", "turntable": "turntable.gif"}
    continued = {}
    if trial:
        appearance = candidate_meta["params"].get("appearance", capture_meta["metrics"].get("appearance"))
        paint_settings = {key: candidate_meta["params"][key] for key in
                          ("model", "steps", "denoise", "paint_mode", "mask_feather", "conditioning", "prompt_scope") if key in candidate_meta["params"]}
        paint_settings["appearance"] = appearance
        continued = {"appearance": appearance, "paint_settings": paint_settings}
    return {"outputs": {"mesh": "mesh.glb", "basecolor": "basecolor.png",
                        "comparison": "comparison.png", "selection": "selection.png", "permission": "permission.png", **review_outputs},
            "models": candidate_meta.get("models", []),
            "licenses": candidate_meta.get("licenses", []),
            "metrics": {"source": src.name, "capture": captured.name, "image": candidate.name,
                        **continued,
                        "geometry_revision": library.geometry_revision(src),
                        "texture_size": size, "bit_depth": base.dtype.itemsize * 8,
                        "triangles": len(mesh.faces), "device": device,
                        "surface_texels": int(permitted.sum()), "changed_texels": int(changed.sum()),
                        "feather": feather,
                        "requested_feather": requested_feather, "preview_feather": preview_feather,
                        "projection_transfer": "replace_changed_v3" if trial else "direct_v1",
                        "background_rejected_texels": background_rejected,
                        "gutter_texels": int((changed & gutter).sum()), "outside_changed": 0, "alpha_changed": 0,
                        "geometry": "original GLB accessors and binary bytes preserved"}}


if __name__ == "__main__":
    main(run)
