"""Measure final camera sampling against native atlas texels."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from steps._views import ortho

if TYPE_CHECKING:
    from steps._paint_set import Surface


def face_footprints(surface: Surface, view: dict, size: int) -> np.ndarray:
    faces: np.ndarray = np.asarray(surface.mesh.faces)
    uv: np.ndarray = surface.uv.numpy()[faces].astype(np.float64) * surface.size
    uv_edges: np.ndarray = np.stack((uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0]), axis=2)
    valid: np.ndarray = abs(np.linalg.det(uv_edges)) > 1e-12
    inverse: np.ndarray = np.zeros_like(uv_edges)
    inverse[valid] = np.linalg.inv(uv_edges[valid])
    pixels: np.ndarray = ortho(**view)["project"](surface.vertices)[0][faces] * size
    edges: np.ndarray = np.stack((pixels[:, 1] - pixels[:, 0], pixels[:, 2] - pixels[:, 0]), axis=2)
    return edges @ inverse


def face_sampling(surface: Surface, view: dict, size: int) -> np.ndarray:
    return np.linalg.svd(face_footprints(surface, view, size), compute_uv=False)


def measure_sampling(surface: Surface, capture: Path, views: list[dict], selected: np.ndarray,
                     panel_size: int, profile: dict | None, out: Path) -> dict:
    """Use singular values in native pixel coordinates and actual front-face visibility."""
    from steps._paint_set import read_faces

    faces: np.ndarray = np.asarray(surface.mesh.faces)
    uv: np.ndarray = surface.uv.numpy()[faces].astype(np.float64) * surface.size
    uv_edges: np.ndarray = np.stack((uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0]), axis=2)
    invertible: np.ndarray = abs(np.linalg.det(uv_edges)) > 1e-12
    selected_values: np.ndarray = selected[surface.covered]
    best: np.ndarray = np.zeros((len(surface.ids), 2), dtype=np.float64)
    visible_any: np.ndarray = np.zeros(len(surface.ids), dtype=bool)
    cameras: list[dict] = []
    for row in views:
        singular: np.ndarray = face_sampling(surface, row["view"], panel_size)
        ids: np.ndarray = read_faces(capture / "faces" / f"{row['id']}.png")
        if ids.shape != (panel_size, panel_size):
            ids, _ = surface.raster(row["view"], panel_size)
        _, visible, _, border = surface.mapping(row["view"], ids)
        visible &= selected_values & invertible[surface.ids] & (border >= 0.5 / panel_size)
        values: np.ndarray = singular[surface.ids]
        better: np.ndarray = visible & (values[:, 1] > best[:, 1])
        best[better] = values[better]
        visible_any |= visible
        ratios: np.ndarray = values[visible, 1]
        cameras.append({"id": row["id"], "visible_texels": int(visible.sum()),
                        "minimum_axis_p10_p50_p90": np.quantile(ratios, [0.1, 0.5, 0.9]).tolist() if len(ratios) else []})
    policy: dict = profile["sampling"] if profile else {"mode": "study", "minimum_samples": 1.0}
    floor: float = float(policy["minimum_samples"])
    eligible: np.ndarray = selected_values & visible_any
    adequate: np.ndarray = eligible & (best[:, 1] >= floor)
    minimum: np.ndarray = best[eligible, 1]
    materials: list[dict] = []
    for material in profile["materials"] if profile else []:
        region: np.ndarray = selected_values.copy()
        if material["faces"] is not None:
            region &= np.isin(surface.ids, material["faces"])
        reached: np.ndarray = region & visible_any
        values = best[reached, 1]
        materials.append({"id": material["id"], "selected_texels": int(region.sum()),
                          "unreachable_texels": int((region & ~visible_any).sum()),
                          "undersampled_texels": int((reached & ~adequate).sum()),
                          "minimum_axis_p10_p50_p90": np.quantile(values, [0.1, 0.5, 0.9]).tolist() if len(values) else []})
    overlay: np.ndarray = np.zeros((*surface.covered.shape, 4), dtype=np.uint8)
    encoded: np.ndarray = np.zeros((len(surface.ids), 4), dtype=np.uint8)
    encoded[selected_values & ~visible_any] = (170, 75, 210, 255)
    encoded[eligible & ~adequate] = (235, 145, 40, 255)
    encoded[adequate] = (35, 210, 105, 255)
    overlay[surface.covered] = encoded
    Image.fromarray(overlay).save(out / "sampling.png")
    return {"schema": 1, "space": "native_camera_pixels_per_atlas_texel", "panel_size": panel_size,
            "minimum_samples": floor, "mode": policy["mode"], "selected_texels": int(selected_values.sum()),
            "reachable_texels": int(eligible.sum()), "unreachable_texels": int((selected_values & ~visible_any).sum()),
            "undersampled_texels": int((eligible & ~adequate).sum()), "adequate_texels": int(adequate.sum()),
            "minimum_axis_p10_p50_p90": np.quantile(minimum, [0.1, 0.5, 0.9]).tolist() if len(minimum) else [],
            "detail_admitted": bool(eligible.any() and np.all(adequate[eligible])),
            "unreachable_policy": "preserve_source", "materials": materials, "cameras": cameras}
