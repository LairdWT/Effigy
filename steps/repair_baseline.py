"""Restore a corrected projection baseline without replacing later painted regions."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from server import library
from steps import _glb
from steps._bake import rasterize_uv
from steps._common import StepError, main, progress
from steps._paint_seams import ownership_map
from steps._paint_set import Surface, material_state, review
from steps._uv_transfer import bind_triangles, sample_atlas, sample_labels, source_texels
from steps.paint import version_dir, write_atlas


def _same_layout(first: Surface, second: Surface) -> None:
    if (first.size != second.size or first.base.dtype != second.base.dtype
            or len(first.original_accessors) != len(second.original_accessors)
            or any(not np.array_equal(a, b) for a, b in zip(first.original_accessors, second.original_accessors))
            or first.original_materials != second.original_materials):
        raise StepError("bad_params", "Baseline repair inputs differ in geometry, UVs, atlas format or material properties")


def _later_permissions(start: Path, stop: Path, surface: Surface) -> np.ndarray:
    current = library.resolve_output(start, "mesh").parent
    expected = library.geometry_revision(stop)
    selected = np.zeros_like(surface.covered)
    visited = set()
    while current.name != stop.name:
        if current.name in visited or library.geometry_revision(current) != expected:
            raise StepError("bad_params", "Repair history is cyclic or crosses an unrecorded UV change")
        visited.add(current.name)
        meta = library._read(current / "meta.json")
        if "permission" in meta["outputs"]:
            with Image.open(library.resolve_output(current, "permission")) as image:
                mask = np.asarray(image.convert("L")) > 0
            if mask.shape != selected.shape:
                raise StepError("bad_params", "Historical paint permission has a different atlas size")
            selected |= mask
        parent = meta.get("parent")
        if parent is None:
            raise StepError("bad_params", "Named baseline is not in the retained paint history")
        current = version_dir(start.parent, parent)
    return selected


def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    if os.environ.get("EFFIGY_MULTI_VIEW") != "1" or in_dir is None or op != "restore":
        raise StepError("bad_params", "Baseline reconstruction is available only for a saved trial mesh")
    required = {"legacy", "corrected", "retained", "aligned"}
    if not required <= params.keys() or set(params) - required - {"dependencies"}:
        raise StepError("bad_params", "Name the legacy, corrected, retained and aligned versions explicitly")
    current_path, out = Path(in_dir), Path(out_dir)
    paths = {name: version_dir(current_path.parent, params[name]) for name in required}
    metas = {name: library._read(path / "meta.json") for name, path in paths.items()}
    if (metas["legacy"]["step"] != "paint_set" or metas["corrected"]["step"] != "paint_set"
            or metas["legacy"]["parent"] != metas["corrected"]["parent"]
            or metas["legacy"]["params"] != metas["corrected"]["params"]
            or metas["corrected"]["metrics"].get("projection_transfer") != "replace_changed_v3"):
        raise StepError("bad_params", "Corrected baseline must replay the exact recorded projection request")
    if metas["aligned"]["step"] != "uv_context" or metas["aligned"]["params"].get("source") != paths["retained"].name:
        raise StepError("bad_params", "Aligned reference is not bound to the retained old-UV source")
    surfaces = {name: Surface(path) for name, path in paths.items()}
    legacy, corrected, retained, aligned = (surfaces[name] for name in ("legacy", "corrected", "retained", "aligned"))
    current = Surface(current_path)
    _same_layout(legacy, corrected)
    _same_layout(legacy, retained)
    _same_layout(aligned, current)
    if not np.array_equal(legacy.base[..., 3], corrected.base[..., 3]):
        raise StepError("bad_params", "Corrected baseline changed source alpha")
    legacy_protected = _later_permissions(paths["retained"], paths["legacy"], retained)
    legacy_protected |= np.any(retained.base != legacy.base, axis=2)
    new_protected = _later_permissions(current_path, paths["aligned"], current)
    new_protected |= np.any(current.base != aligned.base, axis=2)
    binding = bind_triangles(retained, current)
    pixels, faces = source_texels(current, binding)
    values = np.concatenate((corrected.base[..., :3].astype(float), legacy_protected[..., None].astype(float),
                             retained.base.astype(float)), axis=2)
    progress(0.2, "Verifying UV transfer and preserving every later repair footprint")
    samples = sample_atlas(values, retained, pixels, faces)
    if not samples.supported.all():
        raise StepError("bad_params", "Baseline reconstruction has source texels without supported UV correspondence")
    reference = samples.values[:, 4:8].round().astype(retained.base.dtype)
    reference_error = int(np.abs(reference.astype(np.int64) - aligned.base[current.covered].astype(np.int64)).max())
    if reference_error:
        raise StepError("bad_params", f"Aligned reference is not the exact recorded appearance transfer: {reference_error} channel units")
    protected = new_protected.copy()
    protected[current.covered] |= samples.values[:, 3] > 1e-8
    base = current.base.copy()
    permission = np.zeros_like(current.covered)
    permission[current.covered] = ~protected[current.covered]
    eligible = permission[current.covered]
    flat = base[current.covered].copy()
    flat[eligible, :3] = samples.values[eligible, :3].round().clip(0, current.channel_max).astype(base.dtype)
    base[current.covered] = flat
    changed_surface = np.any(base != current.base, axis=2) & current.covered
    distance, nearest = distance_transform_edt(~current.covered, return_indices=True)
    protected |= (~current.covered) & (distance <= 16) & protected[nearest[0], nearest[1]]
    wide = (rasterize_uv(current.uv, current.faces, current.size * 2)[0] >= 0).numpy().reshape(current.size, 2, current.size, 2).any(3).any(1)
    gutter = (~wide) & (distance <= 8) & changed_surface[nearest[0], nearest[1]] & ~protected
    base[gutter, :3] = base[nearest[0][gutter], nearest[1][gutter], :3]
    permission |= gutter
    changed = np.any(base != current.base, axis=2)
    if np.any(changed & protected) or np.any(changed & ~permission) or not np.array_equal(base[..., 3], current.base[..., 3]):
        raise StepError("failed", "Baseline reconstruction changed a protected repair or alpha")
    owners, _, _ = ownership_map(current_path)
    old_owners, _, _ = ownership_map(paths["legacy"])
    fixed_owners, _, _ = ownership_map(paths["corrected"])
    original_ids, used = set(np.unique(old_owners)), set(np.unique(owners))
    remap = {}
    for label in sorted(set(np.unique(fixed_owners)) - original_ids):
        if label and label in used:
            replacement = max(used | set(np.unique(fixed_owners))) + 1
            if replacement >= 16_777_216:
                raise StepError("failed", "Projection ownership labels are exhausted")
            remap[int(label)] = int(replacement)
            fixed_owners[fixed_owners == label] = replacement
            used.add(replacement)
    restored = sample_labels(fixed_owners, corrected, pixels, faces)
    flat_owners = owners[current.covered].copy()
    flat_owners[changed_surface[current.covered]] = restored[changed_surface[current.covered]]
    owners[current.covered] = flat_owners
    write_atlas(out, current.doc, current.blob, current.material, base)
    doc, blob = _glb.read(out / "mesh.glb")
    if (len(doc["accessors"]) != len(current.original_accessors)
            or any(not np.array_equal(value, _glb.accessor(doc, blob, i)) for i, value in enumerate(current.original_accessors))
            or material_state(doc, blob, current.material) != current.original_materials):
        raise StepError("failed", "Baseline reconstruction changed geometry, UVs or another material map")
    Image.fromarray(np.stack((owners & 255, owners >> 8 & 255, owners >> 16 & 255), axis=-1).astype(np.uint8)).save(out / "owners.png")
    Image.fromarray(protected.astype(np.uint8) * 255).save(out / "protected.png")
    Image.fromarray(permission.astype(np.uint8) * 255).save(out / "permission.png")
    review(current, base, out)
    return {"outputs": {"mesh": "mesh.glb", "basecolor": "basecolor.png", "owners": "owners.png", "protected": "protected.png",
                        "permission": "permission.png", "image": "review.png", "turntable": "turntable.gif"},
            "licenses": metas["corrected"].get("licenses", []),
            "metrics": {"triangles": len(current.mesh.faces), "texture_size": current.size, "bit_depth": base.dtype.itemsize * 8,
                        "geometry_uv_equal": True, "other_materials_equal": True, "alpha_changed": 0,
                        "protected_changed": 0, "outside_changed": 0, "changed_texels": int(changed.sum()),
                        "surface_changed_texels": int(changed_surface.sum()), "protected_surface_texels": int((protected & current.covered).sum()),
                        "aligned_reference_max_error": reference_error, "source_triangle_max_error": binding.maximum_geometry_error,
                        "restored_owner_remap": remap, "model_runs": 0, "device": "cpu",
                        "projection_transfer": "replace_changed_v3", "art_acceptance": "pending_visual_review"}}


if __name__ == "__main__":
    main(run)
