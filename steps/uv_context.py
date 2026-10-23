"""Carry projection ownership and selection through a verified UV-only round trip."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

from server import library, settings
from steps import _glb
from steps._bake import rasterize_uv
from steps._common import StepError, main, progress
from steps._paint_handoff import (
    GUIDE_SIZE,
    comparison_sheet,
    contact_sheet,
    guide_cameras,
    handoff_record,
    seam_zone,
    uv_layout_image,
    write_guides,
    zone_overlays,
)
from steps._paint_projection import sample_owned
from steps._paint_seams import ownership_map
from steps._paint_set import Surface, material_state, review
from steps._uv_transfer import bind_triangles, sample_atlas, shell_ids, source_texels
from steps.paint import version_dir, write_atlas


def inspect_surface(surface: Surface) -> dict:
    faces = np.asarray(surface.mesh.faces)
    triangles = surface.uv.numpy()[faces]
    determinant = np.linalg.det(np.stack((triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=2))
    shells = shell_ids(surface)
    labels = np.full_like(surface.owner, -1)
    labels[surface.covered] = shells[surface.ids]
    nearest_distance, nearest = distance_transform_edt(~surface.covered, return_indices=True)
    nearest_label = labels[nearest[0], nearest[1]]
    gaps = []
    for axis in (0, 1):
        left = [slice(None), slice(None)]
        right = [slice(None), slice(None)]
        left[axis], right[axis] = slice(None, -1), slice(1, None)
        a, b = tuple(left), tuple(right)
        boundary = (nearest_label[a] != nearest_label[b]) & (nearest_label[a] >= 0) & (nearest_label[b] >= 0)
        if boundary.any():
            gaps.append(float((nearest_distance[a] + nearest_distance[b])[boundary].min()))
    positions = surface.vertices[faces]
    world_area = np.linalg.norm(np.cross(positions[:, 1] - positions[:, 0], positions[:, 2] - positions[:, 0]), axis=1) / 2
    valid = world_area > 1e-12
    density = np.sqrt(np.abs(determinant[valid]) * 0.5 * surface.size**2 / world_area[valid])
    return {"triangles": len(faces), "vertices": len(surface.vertices), "atlas_size": surface.size,
            "bit_depth": surface.base.dtype.itemsize * 8, "uv_shells": len(np.unique(shells)),
            "degenerate_uv_faces": int((abs(determinant) < 1e-12).sum()),
            "occupancy": float(surface.covered.mean()), "overlap_check": "no_overlap_at_native_texel_centres",
            "minimum_raster_gutter_pixels": min(gaps) if gaps else None,
            "gutter_measurement": "native raster estimate; exact geometric clearance remains a separate check",
            "texels_per_asset_unit_p10_p50_p90": np.quantile(density, [0.1, 0.5, 0.9]).tolist() if len(density) else [],
            "physical_scale": "unknown", "uv_squares": "runtime_incompatible: BMLoopUV.select"}


def exact_clearance(surface: Surface, gap: int) -> dict:
    config_path = Path(settings.read()["tools_config"])
    config = json.loads(config_path.read_text(encoding="utf-8"))
    scripts = Path(config["blenderMcp"]["libraryRoot"]) / "Skills/blender-asset-workflows/scripts"
    if not scripts.is_dir():
        raise StepError("missing_input", "Configured generic UV measurement library is unavailable")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(scripts))
    from blender_workflows.contracts import SceneRevision
    from blender_workflows.coverage import TileOrigin
    from blender_workflows.measurement_identity import MeasurementUvLayer
    from blender_workflows.measurements import TriangleId, UvPoint
    from blender_workflows.pack_margins import GutterRequirements
    from blender_workflows.profiles import TextureSize
    from blender_workflows.uv_clearance import (
        UvClearanceIsland,
        UvClearanceLimits,
        UvClearanceRequest,
        UvClearanceTriangle,
        measure_uv_clearance,
    )
    shells = shell_ids(surface)
    if len(np.unique(shells)) < 2:
        return {"outcome": "single_island", "inter_island_gap": None}
    faces = np.asarray(surface.mesh.faces)
    uv = surface.uv.numpy()[faces]
    islands = tuple(UvClearanceIsland(str(int(shell)), tuple(
        UvClearanceTriangle(TriangleId("mesh", int(i), 0), tuple(UvPoint(float(p[0]), float(p[1])) for p in uv[i]))
        for i in np.flatnonzero(shells == shell))) for shell in np.unique(shells))
    request = UvClearanceRequest(SceneRevision(surface.source.name, 0), "base_colour",
                                 TextureSize(surface.size, surface.size), TileOrigin(0, 0),
                                 MeasurementUvLayer("mesh", "TEXCOORD_0"), islands,
                                 GutterRequirements(max(1, gap), 0), UvClearanceLimits(max_triangles=20000))
    report = measure_uv_clearance(request)
    return {"outcome": report.outcome, "disposition": report.disposition,
            "minimum_island_pixels": report.minimum_island_distance_squared.approximate_pixels() if report.minimum_island_distance_squared else None,
            "minimum_border_pixels": report.minimum_border_distance_squared.approximate_pixels() if report.minimum_border_distance_squared else None,
            "meets_requested_gap": report.meets_island_gap, "reason": report.reason,
            "overlapping_island_pairs": sum(p.state == "overlapping" for p in report.island_pairs)}


def prepare_surface(source: Path, out: Path, params: dict) -> dict:
    import cv2

    surface = Surface(source)
    operation = params.get("operation", "inspect")
    if type(params.get("gutter_pixels", 4)) is not int or not 1 <= params.get("gutter_pixels", 4) <= 64:
        raise StepError("bad_params", "Preparation gutter must be an integer from 1 to 64 pixels")
    uv_scale = params.get("uv_scale", 1.0)
    if type(uv_scale) not in (float, int) or not 0.5 <= uv_scale <= 1.0:
        raise StepError("bad_params", "Choose an explicit UV scale between 0.5 and 1; it is never reduced automatically")
    inspection = inspect_surface(surface)
    if operation == "inspect":
        progress(0.2, "Measuring exact UV island clearance")
        inspection["exact_clearance"] = exact_clearance(surface, int(params.get("gutter_pixels", 4)))
        (out / "preparation.json").write_text(json.dumps(inspection, indent=2), encoding="utf-8")
        return {"outputs": {"mesh": "@mesh.glb", "preparation": "preparation.json"},
                "output_refs": {"mesh": {"version": source.name, "key": "mesh"}}, "metrics": inspection}
    if operation not in ("pack", "unwrap"):
        raise StepError("bad_params", "Choose Inspect, ZenUV unwrap or UVPackmaster pack")
    if not np.all(surface.base[surface.covered, 3] == surface.channel_max):
        raise StepError("unsupported_alpha", "UV preparation currently requires an opaque atlas; use a private Blender copy for transparency")
    scratch = settings.ROOT / "scratch" / "preparation" / f"{out.name}-{uuid.uuid4().hex[:8]}"
    scratch.mkdir(parents=True, exist_ok=False)
    atlas = scratch / "source.png"
    cv2.imwrite(str(atlas), cv2.cvtColor(surface.base, cv2.COLOR_RGBA2BGRA))
    workfile = scratch / "authoring.blend"
    result_path = scratch / "result.json"
    spec = scratch / "job.json"
    tools_config = Path(settings.read()["tools_config"]).resolve()
    job = {"source": source.name, "geometry_revision": library.geometry_revision(source),
           "tools_config": str(tools_config), "runtime_root": str(scratch),
           "vertices": surface.vertices.tolist(), "faces": np.asarray(surface.mesh.faces).tolist(),
           "uv": surface.uv.numpy().tolist(), "base_image": str(atlas), "workfile": str(workfile),
           "result": str(result_path), "operation": operation,
           "provider": "uvpackmaster3" if operation == "pack" else "zen_uv",
           "atlas_size": surface.size, "gutter_pixels": int(params.get("gutter_pixels", 4)), "uv_scale": uv_scale}
    spec.write_text(json.dumps(job), encoding="utf-8")
    command = [os.environ["EFFIGY_BLENDER"], "--factory-startup", "--offline-mode", "--python-exit-code", "1",
               "--python", str(settings.ROOT / "tools/blender_prepare.py"), "--", str(spec)]
    startup = None
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
    env = os.environ | {"PYTHONDONTWRITEBYTECODE": "1", "BLENDER_USER_CONFIG": str(scratch / "config"),
                        "BLENDER_USER_SCRIPTS": str(scratch / "scripts"), "BLENDER_USER_EXTENSIONS": str(scratch / "extensions")}
    progress(0.1, f"Running isolated Blender {operation}")
    with (scratch / "blender.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, startupinfo=startup)
        try:
            code = process.wait(timeout=240)
        except subprocess.TimeoutExpired as error:
            from server.jobs import _kill_tree
            _kill_tree(process)
            process.wait()
            raise StepError("preparation_timeout", "Private Blender preparation timed out; source was preserved") from error
    if code or not result_path.is_file():
        raise StepError("preparation_failed", f"Private Blender exited {code}; inspect its owned preparation log")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if not result["ok"]:
        raise StepError("provider_unavailable", result["error"])
    corners = np.asarray(result["result"]["corners"], dtype=np.float32)
    faces = np.asarray(surface.mesh.faces)
    if corners.shape != (len(faces), 3, 2) or not np.isfinite(corners).all():
        raise StepError("invalid_uv", "Provider did not return finite UVs for every source triangle")
    new_uv = corners.reshape(-1, 2)
    new_faces = np.arange(len(new_uv), dtype=np.uint32).reshape(-1, 3)
    from steps.paint import reject_uv_overlap
    reject_uv_overlap(new_uv, new_faces, surface.size)
    primitive = surface.doc["meshes"][0]["primitives"][0]
    texture_index = surface.doc["materials"][surface.material]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    base_image_index = surface.doc["textures"][texture_index]["source"]
    for image_index, image in enumerate(surface.doc.get("images", [])):
        if image_index == base_image_index:
            continue
        view = surface.doc["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        decoded = cv2.imdecode(np.frombuffer(surface.blob[start:start + view["byteLength"]], dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if decoded is None or np.any(decoded != decoded[0, 0]):
            raise StepError("uv_other_map_bake_required", "UV changes need a qualified bake for nonconstant secondary maps. Use the private Blender workfile; the source is unchanged.")
    owner, bary = rasterize_uv(torch.tensor(new_uv), torch.tensor(new_faces.astype(np.int64)), surface.size)
    target_owner = owner.numpy()
    covered = target_owner >= 0
    face_ids = target_owner[covered]
    source_uv = (surface.uv.numpy()[faces[face_ids]] * bary.numpy()[covered, :, None]).sum(1)
    sampled = sample_atlas(surface.base.astype(float), surface, source_uv, face_ids)
    if not sampled.supported.all():
        raise StepError("uv_transfer_gap", "The prepared UV layout contains source samples without exact face support")
    transferred = surface.base.copy()
    transferred[..., 3] = 0
    transferred[covered, 3] = surface.channel_max
    transferred[covered, :3] = sampled.values[:, :3].round().clip(0, surface.channel_max).astype(surface.base.dtype)
    distance, nearest = distance_transform_edt(~covered, return_indices=True)
    gutter = (~covered) & (distance <= job["gutter_pixels"])
    transferred[gutter, :3] = transferred[nearest[0][gutter], nearest[1][gutter], :3]
    def append_accessor(values: np.ndarray, component: int, shape: str) -> int:
        surface.blob.extend(b"\0" * (-len(surface.blob) % 4))
        offset = len(surface.blob)
        surface.blob.extend(np.ascontiguousarray(values).tobytes())
        view_index = len(surface.doc["bufferViews"])
        surface.doc["bufferViews"].append({"buffer": 0, "byteOffset": offset, "byteLength": values.nbytes})
        index = len(surface.doc["accessors"])
        surface.doc["accessors"].append({"bufferView": view_index, "componentType": component,
                                         "count": len(values), "type": shape,
                                         "min": values.min(axis=0).reshape(-1).tolist(),
                                         "max": values.max(axis=0).reshape(-1).tolist()})
        return index

    for semantic, accessor in list(primitive["attributes"].items()):
        description = surface.doc["accessors"][accessor]
        values = new_uv if semantic == "TEXCOORD_0" else _glb.accessor(surface.doc, surface.blob, accessor)[faces.ravel()]
        new_accessor = append_accessor(values, description["componentType"], description["type"])
        if description.get("normalized"):
            surface.doc["accessors"][new_accessor]["normalized"] = True
        primitive["attributes"][semantic] = new_accessor
    primitive["indices"] = append_accessor(new_faces.ravel()[:, None], 5125, "SCALAR")
    surface.doc["buffers"][0]["byteLength"] = len(surface.blob)
    write_atlas(out, surface.doc, surface.blob, surface.material, transferred)
    shutil.copy2(workfile, out / "authoring.blend")
    inspection.update(provider=result["result"]["provider"], uv_changed=True,
                      requested_uv_scale=uv_scale,
                      appearance_transfer="same_triangle_once", prepared_geometry_revision=out.name,
                      surface_alpha_opaque=True, alpha_layout="remapped_with_prepared_uvs",
                      vertex_layout="explicit_triangle_corners", triangle_positions_preserved=True,
                      secondary_maps="constant_maps_unchanged", occupancy=float(covered.mean()))
    (out / "preparation.json").write_text(json.dumps(inspection, indent=2), encoding="utf-8")
    return {"outputs": {"mesh": "mesh.glb", "blend": "authoring.blend", "preparation": "preparation.json"},
            "metrics": inspection}


def transfer_base(source: Surface, target: Surface, pixels: np.ndarray, faces: np.ndarray,
                  out: Path) -> tuple[np.ndarray, dict]:
    samples = sample_atlas(source.base.astype(float), source, pixels, faces)
    if not samples.supported.all():
        raise StepError("bad_params", "Source paint does not cover every corresponding target texel")
    values = samples.values.round().clip(0, target.channel_max).astype(target.base.dtype)
    if not np.array_equal(values[:, 3], target.base[target.covered, 3]):
        raise StepError("bad_params", "Source paint would change target surface transparency")
    result = target.base.copy()
    result[target.covered, :3] = values[:, :3]
    distance, nearest = distance_transform_edt(~target.covered, return_indices=True)
    wide = (rasterize_uv(target.uv, target.faces, target.size * 2)[0] >= 0).numpy().reshape(target.size, 2, target.size, 2).any(3).any(1)
    gutter = (~wide) & (distance <= 16)
    result[gutter, :3] = result[nearest[0][gutter], nearest[1][gutter], :3]
    permission = target.covered | gutter
    changed = np.any(result != target.base, axis=2)
    if np.any(changed & ~permission) or not np.array_equal(result[..., 3], target.base[..., 3]):
        raise StepError("failed", "Source transfer changed protected atlas pixels or alpha")
    write_atlas(out, target.doc, target.blob, target.material, result)
    doc, blob = _glb.read(out / "mesh.glb")
    if (len(doc["accessors"]) != len(target.original_accessors)
            or any(not np.array_equal(value, _glb.accessor(doc, blob, i)) for i, value in enumerate(target.original_accessors))
            or material_state(doc, blob, target.material) != target.original_materials):
        raise StepError("failed", "Source transfer changed target geometry, UVs or other material maps")
    Image.fromarray(permission.astype(np.uint8) * 255).save(out / "permission.png")
    texture = target.texture.new_tensor(result.astype(np.float32) * (255 / target.channel_max))
    center = (target.vertices.min(0) + target.vertices.max(0)) / 2
    extent = float(np.linalg.norm(target.vertices - center, axis=1).max()) * 2.2
    views = []
    for yaw in (0, 90, 180, 270):
        progress(0.35 + yaw / 1800, f"Comparing transferred source paint at {yaw} degrees")
        view = {"yaw": yaw, "pitch": -25, "center": center.tolist(), "extent": extent}
        original, _ = source.render(view, size=512)
        transferred, _ = target.render(view, texture, 512)
        a, b = np.asarray(original), np.asarray(transferred)
        opaque = (a[..., 3] == 255) & (b[..., 3] == 255)
        difference = np.abs(a[..., :3].astype(np.int16) - b[..., :3].astype(np.int16))[opaque]
        views.append({"yaw": yaw, "mean_rgb8": float(difference.mean()),
                      "p95_rgb8": float(np.percentile(difference, 95)),
                      "render_alpha_changed": int(np.count_nonzero(a[..., 3] != b[..., 3]))})
    return result, {"source_render_comparison": views, "geometry_uv_equal": True,
                    "alpha_changed": 0, "outside_changed": 0, "changed_texels": int(changed.sum()),
                    "unsupported_source_texels": 0, "model_loads": 0,
                    "source_texel_transfer": "same_triangle_barycentric_with_same_shell_filtering"}


def reconstruct(source_path: Path, out: Path, params: dict) -> dict:
    target = Surface(source_path)
    donor_path = version_dir(source_path.parent, params["donor"])
    donor = Surface(donor_path)
    binding = bind_triangles(donor, target)
    mask_path = version_dir(source_path.parent, params["mask_version"])
    if library.geometry_revision(mask_path) != library.geometry_revision(source_path):
        raise StepError("bad_params", "Paint permission belongs to a different geometry revision")
    with Image.open(library.resolve_output(mask_path, "mask")) as image:
        selected = np.asarray(image.convert("L")) > 0
    if selected.shape != target.covered.shape or np.any(selected & ~target.covered):
        raise StepError("bad_params", "Reconstruction permission does not match the prepared source")
    if not selected.any():
        raise StepError("bad_params", "Select a surface region before reconstruction")
    pixels, faces = source_texels(target, binding)
    values = sample_atlas(donor.base.astype(float) / donor.channel_max, donor, pixels, faces)
    permission = selected[target.covered]
    if not values.supported[permission].all():
        raise StepError("missing_donor_samples", "The registered donor does not cover the complete permitted surface")
    result = target.base.copy()
    proposed = (values.values[:, :3] * target.channel_max).round().clip(0, target.channel_max).astype(target.base.dtype)
    result[selected, :3] = proposed[permission]
    changed = np.any(result != target.base, axis=2)
    if np.any(changed & ~selected) or not np.array_equal(result[..., 3], target.base[..., 3]):
        raise StepError("failed", "Reconstruction changed protected pixels or alpha")
    write_atlas(out, target.doc, target.blob, target.material, result)
    doc, blob = _glb.read(out / "mesh.glb")
    if (len(doc["accessors"]) != len(target.original_accessors)
            or any(not np.array_equal(value, _glb.accessor(doc, blob, i)) for i, value in enumerate(target.original_accessors))
            or material_state(doc, blob, target.material) != target.original_materials):
        raise StepError("failed", "Reconstruction changed geometry, UVs or another map")
    Image.fromarray(selected.astype(np.uint8) * 255).save(out / "permission.png")
    review(target, result, out)
    comparison: list[dict] = comparison_sheet(target, result, out)
    return {"outputs": {"mesh": "mesh.glb", "permission": "permission.png", "image": "review.png", "turntable": "turntable.gif",
                        "comparison": "comparison.png"},
            "metrics": {"method": params["method"], "donor": donor_path.name, "model_loads": 0,
                        "mask_version": mask_path.name, "source_render_comparison": comparison,
                        "changed_texels": int(changed.sum()), "outside_permission_changes": 0, "alpha_changed": 0,
                        "geometry_uv_equal": True, "other_maps_equal": True,
                        "maximum_triangle_error": binding.maximum_geometry_error,
                        "texture_size": target.size, "bit_depth": target.base.dtype.itemsize * 8}}


def _guide_inputs(params: dict) -> tuple[float, list[dict] | None]:
    front_yaw: object = params.get("front_yaw", 0)
    if type(front_yaw) not in (float, int):
        raise StepError("bad_params", "Hand-paint guides need a numeric front yaw")
    views: object = params.get("views")
    if views is not None and not isinstance(views, list):
        raise StepError("bad_params", "Guide framing views must be a list of captured camera rows")
    return float(front_yaw), views or None


def handoff(source_path: Path, out: Path, params: dict) -> dict:
    profile: object = params.get("authoring_profile")
    if not isinstance(profile, dict):
        raise StepError("bad_params", "Hand-paint handoff requires the saved authoring profile")
    front_yaw: float
    views: list[dict] | None
    front_yaw, views = _guide_inputs(params)
    surface: Surface = Surface(source_path)
    geometry: str = library.geometry_revision(source_path)
    permission: np.ndarray = surface.covered.copy()
    permission_source: str = "all_covered_texels"
    if params.get("mask_version") is not None:
        mask_path: Path = version_dir(source_path.parent, params["mask_version"])
        if library.geometry_revision(mask_path) != geometry:
            raise StepError("bad_params", "Paint permission belongs to a different geometry revision")
        with Image.open(library.resolve_output(mask_path, "mask")) as image:
            permission = np.asarray(image.convert("L")) > 0
        if permission.shape != surface.covered.shape or np.any(permission & ~surface.covered):
            raise StepError("bad_params", "Handoff permission does not match the prepared source")
        permission_source = mask_path.name
    progress(0.05, "Measuring texels per asset unit")
    measured: list[float] = inspect_surface(surface)["texels_per_asset_unit_p10_p50_p90"]
    rows: list[dict] = write_guides(surface, out, guide_cameras(surface, front_yaw, views), GUIDE_SIZE)
    (out / "cameras.json").write_text(json.dumps({"projection": "orthographic", "frame": "library",
                                                  "angles": "degrees", "front_yaw": front_yaw,
                                                  "cameras": rows}, indent=2), encoding="utf-8")
    progress(0.65, "Writing UV layout and permission")
    uv_layout_image(surface).save(out / "uv-layout.png")
    Image.fromarray(permission.astype(np.uint8) * 255).save(out / "permission.png")
    import cv2
    cv2.imwrite(str(out / "basecolor.png"), cv2.cvtColor(surface.base, cv2.COLOR_RGBA2BGRA))
    authoring_revision: object = params.get("authoring_revision")
    record: dict = handoff_record(surface, profile, source_path.name, geometry,
                                  authoring_revision if type(authoring_revision) is int else None,
                                  measured, rows, permission_source)
    (out / "handoff.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    contact_sheet(out, rows)
    return {"outputs": {"mesh": "@mesh.glb", "image": "contact-sheet.png", "handoff": "handoff.json",
                        "guides": "guide", "face_ids": "faces", "cameras": "cameras.json",
                        "uv_layout": "uv-layout.png", "permission": "permission.png", "basecolor": "basecolor.png"},
            "output_refs": {"mesh": {"version": source_path.name, "key": "mesh"}},
            "metrics": {"source": source_path.name, "geometry_revision": geometry, "guides": len(rows),
                        "guide_size": GUIDE_SIZE, "permission_source": permission_source,
                        "permitted_texels": int(permission.sum()),
                        "declared_density_pixels_per_metre": record["declared_density_pixels_per_metre"],
                        "physical_scale": record["physical_scale"], "model_loads": 0, "device": "cpu",
                        "duplicate_mesh_bytes": 0, "art_acceptance": "pending_visual_review"}}


def heal_mask(source_path: Path, out: Path, params: dict) -> dict:
    mode: object = params.get("mode")
    if mode not in ("writers", "shells"):
        raise StepError("bad_params", "Choose the writers or shells seam-heal mode")
    front_yaw: float
    views: list[dict] | None
    front_yaw, views = _guide_inputs(params)
    surface: Surface = Surface(source_path)
    progress(0.1, f"Marking seam-heal zone from {mode}")
    zone: np.ndarray
    record: dict
    zone, record = seam_zone(surface, str(mode))
    Image.fromarray(zone.astype(np.uint8) * 255).save(out / "mask.png")
    overlays: list[str] = zone_overlays(surface, zone, out, guide_cameras(surface, front_yaw, views))
    manifest: dict = record | {"source": source_path.name,
                               "geometry_revision": library.geometry_revision(source_path),
                               "overlays": [f"overlays/{name}.png" for name in overlays]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"outputs": {"mesh": "@mesh.glb", "mask": "mask.png", "overlays": "overlays", "manifest": "manifest.json"},
            "output_refs": {"mesh": {"version": source_path.name, "key": "mesh"}},
            "metrics": {key: value for key, value in manifest.items() if key != "overlays"}
            | {"model_loads": 0, "device": "cpu", "atlas_changed": False}}


def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    if os.environ.get("EFFIGY_MULTI_VIEW") != "1" or in_dir is None or op not in ("restore", "transfer", "prepare", "reconstruct", "publish", "handoff", "heal_mask"):
        raise StepError("bad_params", "UV context restoration requires a saved trial mesh")
    if op == "reconstruct":
        return reconstruct(Path(in_dir), Path(out_dir), params)
    if op == "handoff":
        return handoff(Path(in_dir), Path(out_dir), params)
    if op == "heal_mask":
        return heal_mask(Path(in_dir), Path(out_dir), params)
    if op == "publish":
        candidate = version_dir(Path(in_dir).parent, params["candidate"])
        meta = library._read(candidate / "meta.json")
        if (meta.get("parent") != Path(in_dir).name or meta.get("params", {}).get("op") != "reconstruct"
                or meta["params"].get("mask_version") != params["mask_version"]):
            raise StepError("bad_params", "Publish requires the reviewed reconstruction for this exact source and mask")
        return {"outputs": {key: "@" + value for key, value in meta["outputs"].items()},
                "output_refs": {key: {"version": candidate.name, "key": key} for key in meta["outputs"]},
                "metrics": meta["metrics"] | {"duplicate_mesh_bytes": 0, "published_candidate": candidate.name}}
    if op == "prepare":
        if set(params) - {"operation", "gutter_pixels", "uv_scale"}:
            raise StepError("bad_params", "Unknown preparation parameters")
        return prepare_surface(Path(in_dir), Path(out_dir), params)
    if set(params) - {"source", "selection_source", "dependencies"}:
        raise StepError("bad_params", "Unknown UV context parameters")
    target_path, out = Path(in_dir), Path(out_dir)
    source_path = version_dir(target_path.parent, params.get("source"))
    if source_path == target_path:
        raise StepError("bad_params", "Choose the painted source preceding the new UV layout")
    source, target = Surface(source_path), Surface(target_path)
    if source.size != target.size or source.base.dtype != target.base.dtype:
        raise StepError("bad_params", "UV round trip changed atlas size or bit depth")
    if source.original_materials != target.original_materials:
        raise StepError("bad_params", "UV round trip changed another material property")
    old_faces, new_faces = np.asarray(source.mesh.faces), np.asarray(target.mesh.faces)
    binding = bind_triangles(source, target)
    progress(0.2, "Transferring paint ownership through matching triangles")
    old_uv, old_ids = source_texels(target, binding)
    pixels = np.floor(old_uv * source.size).astype(int).clip(0, source.size - 1)
    xx, yy = pixels[:, 0], pixels[:, 1]
    source_writers, _, _ = ownership_map(source_path)
    writers = np.zeros_like(target.owner, dtype=np.int64)
    values = source_writers[yy, xx].copy()
    missing = source.owner[yy, xx] != old_ids
    for face in np.unique(old_ids[missing]):
        affected = missing & (old_ids == face)
        sy, sx = np.nonzero(source.owner == face)
        if not len(sx):
            values[affected] = 0
            continue
        _, nearest = cKDTree(np.column_stack((sx, sy)) + 0.5).query(old_uv[affected] * source.size)
        values[affected] = source_writers[sy[nearest], sx[nearest]]
    writers[target.covered] = values
    rgb = np.stack((writers & 255, (writers >> 8) & 255, (writers >> 16) & 255), axis=-1).astype(np.uint8)
    Image.fromarray(rgb).save(out / "owners.png")
    selected = np.zeros_like(target.covered)
    if params.get("selection_source") is not None:
        selection_path = version_dir(target_path.parent, params["selection_source"])
        if library.geometry_revision(selection_path) != library.geometry_revision(source_path):
            raise StepError("bad_params", "Selection differs from the old UV geometry")
        with Image.open(library.resolve_output(selection_path, "mask")) as image:
            selection = np.asarray(image.convert("L")) > 0
        if selection.shape != source.covered.shape or np.any(selection & ~source.covered):
            raise StepError("bad_params", "Old selection does not fit its source atlas")
        counts = np.bincount(source.ids, minlength=len(old_faces))
        chosen = np.bincount(source.owner[selection & source.covered], minlength=len(old_faces))
        complete_faces = (counts > 0) & (counts == chosen)
        samples = sample_owned(selection[..., None].astype(float), old_uv, source.owner,
                               old_ids, source.covered, source.covered)
        selected[target.covered] = complete_faces[old_ids] | (samples.supported & (samples.values[:, 0] >= 1 - 1e-7))
    Image.fromarray(selected.astype(np.uint8) * 255).save(out / "mask.png")
    base, extra_metrics = target.base, {}
    outputs = {"mesh": "@mesh.glb", "owners": "owners.png", "mask": "mask.png", "image": "review.png",
               "turntable": "turntable.gif", "uv_layout": "uv-layout.png"}
    references = {"mesh": {"version": target_path.name, "key": "mesh"}}
    if op == "transfer":
        base, extra_metrics = transfer_base(source, target, old_uv, old_ids, out)
        outputs.update(mesh="mesh.glb", basecolor="basecolor.png", permission="permission.png")
        references = {}
    review(target, base, out)
    image = Image.fromarray((base.astype(float) * (255 / target.channel_max)).round().astype(np.uint8)).convert("RGB")
    draw = ImageDraw.Draw(image)
    for triangle in target.uv.numpy()[new_faces]:
        points = [tuple(point * target.size) for point in triangle]
        draw.line(points + points[:1], fill=(60, 220, 245), width=1)
    image.save(out / "uv-layout.png")
    return {"outputs": outputs, "output_refs": references,
            "metrics": {"source": source_path.name, "uv_layout_source": target_path.name,
                        "geometry_position_max_error": binding.maximum_geometry_error, "triangles": len(new_faces),
                        "texture_size": target.size, "bit_depth": target.base.dtype.itemsize * 8,
                        "geometry_revision": library.geometry_revision(target_path),
                        "other_materials_equal": True, "selected_texels": int(selected.sum()),
                        "ownership_transfer": "nearest_same_triangle",
                        "atlas_changed": op == "transfer", "duplicate_mesh_bytes": 0, "device": "cpu",
                        "art_acceptance": "pending_visual_review"} | extra_metrics}


if __name__ == "__main__":
    main(run)
