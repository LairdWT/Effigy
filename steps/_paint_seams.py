"""Advisory seam masks rendered from accumulated mesh appearance and view ownership."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

from server import library
from steps._common import StepError
from steps._views import ortho, zbuffer


def ownership_source(source: Path) -> Path:
    revision = library.geometry_revision(source)
    current = source
    visited: set[str] = set()
    while current.name not in visited:
        visited.add(current.name)
        meta = json.loads((current / "meta.json").read_text(encoding="utf-8"))
        if ("owners" in meta["outputs"] or "writers" in meta["outputs"]) and library.geometry_revision(current) == revision:
            return current
        parent = meta.get("parent")
        if not isinstance(parent, str) or not library.VERSION.fullmatch(parent):
            break
        current = source.parent / parent
    raise StepError("missing_input", "Seam suggestions need a combined projection preview in this mesh's history. Use a normal capture and brush selection instead.")


def ownership_map(source: Path, seen: frozenset[Path] = frozenset()) -> tuple[np.ndarray, str, list[str]]:
    identity = source.resolve()
    if identity in seen:
        raise StepError("bad_params", "Cyclic appearance ownership history")
    seen = seen | {identity}
    owner_source = ownership_source(source)
    owner_meta = json.loads((owner_source / "meta.json").read_text(encoding="utf-8"))
    key = "writers" if "writers" in owner_meta["outputs"] else "owners"
    with Image.open(library.resolve_output(owner_source, key)) as image:
        atlas = np.asarray(image.convert("RGB")).astype(np.int64)
    atlas_ids = atlas[..., 0] + 256 * atlas[..., 1] + 65536 * atlas[..., 2]
    if key == "owners" and owner_meta["step"] == "paint_set":
        operation = owner_meta["params"].get("op")
        if operation == "apply":
            preview = library.version_dir(source.parent.name, owner_meta["params"]["preview"])
            atlas_ids, _, _ = ownership_map(preview, seen)
        elif operation in ("preview", "diagnostic"):
            parent = library.version_dir(source.parent.name, owner_meta["parent"])
            if library.geometry_revision(parent) != library.geometry_revision(owner_source):
                raise StepError("bad_params", "Projection ownership crossed a geometry revision")
            try:
                inherited, _, _ = ownership_map(parent, seen)
            except StepError as error:
                if error.code != "missing_input":
                    raise
                inherited = np.zeros_like(atlas_ids)
            from steps.paint import load_mesh
            previous = load_mesh(parent)[5]
            current_colour = load_mesh(owner_source)[5]
            if previous.shape != current_colour.shape or previous.dtype != current_colour.dtype or inherited.shape != atlas_ids.shape:
                raise StepError("bad_params", "Projection ancestry changed the atlas format")
            changed = np.any(previous[..., :3] != current_colour[..., :3], axis=2) & (atlas_ids != 0)
            marker = int(inherited.max()) + 1
            inherited[inherited == 0] = marker
            labels = np.unique(atlas_ids[changed])
            if marker + len(labels) > 0xFFFFFF:
                raise StepError("bad_params", "Appearance ownership exceeds its 24-bit label capacity")
            for offset, label in enumerate(labels, start=1):
                inherited[changed & (atlas_ids == label)] = marker + offset
            atlas_ids = inherited
    current = source
    healed: list[Path] = []
    while current != owner_source:
        meta = json.loads((current / "meta.json").read_text(encoding="utf-8"))
        if meta["step"] == "paint" and meta["params"].get("op") == "apply" and "permission" in meta["outputs"]:
            healed.append(current)
        if (meta["step"] == "uv_context" and meta["params"].get("op") in ("reconstruct", "publish")
                and "permission" in meta["outputs"]):
            healed.append(current)
        parent = meta.get("parent")
        if not isinstance(parent, str) or not library.VERSION.fullmatch(parent):
            raise StepError("missing_input", "Projection history changed while preparing seam suggestions")
        current = source.parent / parent
    marker = int(atlas_ids.max()) + 1
    if marker + len(healed) > 0xFFFFFF:
        raise StepError("bad_params", "Appearance ownership exceeds its 24-bit label capacity")
    for folder in reversed(healed):
        with Image.open(library.resolve_output(folder, "permission")) as image:
            permission = np.asarray(image.convert("L")) > 0
        if permission.shape != atlas_ids.shape:
            raise StepError("bad_params", "A previous repair mask does not match the current atlas")
        atlas_ids[permission] = marker
        marker += 1
    return atlas_ids, owner_source.name, [folder.name for folder in reversed(healed)]


def suggest_seams(source: Path, view: dict, uv: torch.Tensor, faces: torch.Tensor,
                  vertices: np.ndarray, rgba: np.ndarray) -> tuple[Image.Image, dict]:
    atlas_ids, owner_source, healed = ownership_map(source)
    size = rgba.shape[0]
    camera = ortho(**view)
    projected, depth = camera["project"](vertices)
    ids_t, bary_t, _ = zbuffer(torch.tensor(projected, dtype=torch.float32),
                               torch.tensor(depth, dtype=torch.float32), faces, size)
    ids, bary = ids_t.numpy(), bary_t.numpy()
    visible = ids >= 0
    points = (uv.numpy()[faces.numpy()[ids[visible]]] * bary[visible, :, None]).sum(1)
    xy = np.floor(points * atlas_ids.shape[0]).astype(int).clip(0, atlas_ids.shape[0] - 1)
    owners = np.zeros((size, size), dtype=np.int64)
    owners[visible] = atlas_ids[xy[:, 1], xy[:, 0]]
    triangles = vertices[faces.numpy()]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True).clip(1e-12)
    facing = normals @ camera["towards"](np.zeros((1, 3)))[0]
    allowed = visible & (rgba[..., 3] == 255) & (owners != 0)
    allowed[visible] &= facing[ids[visible]] > 0.25
    colour = cv2.GaussianBlur(rgba[..., :3].astype(np.float32), (0, 0), 1.0)
    boundary = np.zeros_like(allowed)
    for axis in (0, 1):
        first = (slice(None, -3), slice(None)) if axis == 0 else (slice(None), slice(None, -3))
        second = (slice(3, None), slice(None)) if axis == 0 else (slice(None), slice(3, None))
        different = (owners[first] != owners[second]) & allowed[first] & allowed[second]
        different &= np.abs(colour[first] - colour[second]).sum(2) > 36
        boundary[first] |= different
        boundary[second] |= different
    radius = max(3, round(size * 0.012))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
    selected = (cv2.dilate(boundary.astype(np.uint8), kernel) > 0) & allowed
    return Image.fromarray(selected.astype(np.uint8) * 255), {
        "ownership_source": owner_source, "healed_versions": healed,
        "suggested_pixels": int(selected.sum()),
        "boundary_pixels": int(boundary.sum()), "radius_pixels": radius, "advisory": True,
    }
