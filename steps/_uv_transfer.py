"""Typed triangle correspondence for appearance-preserving UV round trips."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

from steps._bake import rasterize_uv
from steps._common import StepError
from steps._paint_projection import ProjectedSamples, sample_owned
from steps._paint_set import Surface


@dataclass(frozen=True)
class TriangleUvBinding:
    source_faces: np.ndarray
    source_uv_corners: np.ndarray
    maximum_geometry_error: float


def bind_triangles(source: Surface, target: Surface) -> TriangleUvBinding:
    old_faces, new_faces = np.asarray(source.mesh.faces), np.asarray(target.mesh.faces)
    if len(old_faces) != len(new_faces):
        raise StepError("bad_params", "UV round trip changed the triangle count")

    def key(points: np.ndarray) -> tuple:
        return tuple(sorted(tuple(point) for point in np.round(points, 6)))

    old_points, new_points = source.vertices[old_faces], target.vertices[new_faces]
    lookup = {key(points): index for index, points in enumerate(old_points)}
    if len(lookup) != len(old_faces):
        raise StepError("bad_params", "Coincident source triangles make UV correspondence ambiguous")
    face_map, source_uvs, maximum_error = [], [], 0.0
    for points in new_points:
        original = lookup.get(key(points))
        if original is None:
            raise StepError("bad_params", "UV round trip changed the geometric surface")
        distances = np.linalg.norm(points[:, None] - old_points[original][None, :], axis=2)
        corners = distances.argmin(1)
        error = float(distances[np.arange(3), corners].max())
        if len(set(corners)) != 3 or error > 2e-7:
            raise StepError("bad_params", "UV triangle corners differ beyond float32 precision")
        if tuple(corners) not in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
            raise StepError("bad_params", "UV round trip reversed a triangle")
        maximum_error = max(maximum_error, error)
        face_map.append(original)
        source_uvs.append(source.uv.numpy()[old_faces[original]][corners])
    if len(set(face_map)) != len(old_faces):
        raise StepError("bad_params", "UV round trip duplicated or omitted a triangle")
    return TriangleUvBinding(np.asarray(face_map), np.asarray(source_uvs), maximum_error)


def source_texels(target: Surface, binding: TriangleUvBinding) -> tuple[np.ndarray, np.ndarray]:
    owner, bary = rasterize_uv(target.uv, target.faces, target.size)
    ids = owner.numpy()[target.covered]
    pixels = (binding.source_uv_corners[ids] * bary.numpy()[target.covered, :, None]).sum(1)
    return pixels, binding.source_faces[ids]


def shell_ids(surface: Surface) -> np.ndarray:
    faces, uv = np.asarray(surface.mesh.faces), surface.uv.numpy()
    parents = list(range(len(faces)))
    edges: dict[tuple, list[int]] = defaultdict(list)

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for face, corners in enumerate(faces):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            key = tuple(sorted(tuple(np.round(surface.vertices[corners[i]], 7)) + tuple(np.round(uv[corners[i]], 7)) for i in (a, b)))
            edges[key].append(face)
    for members in edges.values():
        if len(members) == 2:
            parents[find(members[0])] = find(members[1])
    return np.array([find(i) for i in range(len(faces))])


def sample_atlas(values: np.ndarray, source: Surface, pixels: np.ndarray, faces: np.ndarray,
                 gutter: int = 16) -> ProjectedSamples:
    shells = shell_ids(source)
    distance, nearest = distance_transform_edt(~source.covered, return_indices=True)
    readable = source.covered | (distance <= gutter)
    owners = np.full_like(source.owner, -1)
    owners[readable] = shells[source.owner[nearest[0][readable], nearest[1][readable]]]
    return sample_owned(values, pixels, owners, shells[faces], readable, readable)


def sample_labels(values: np.ndarray, source: Surface, pixels: np.ndarray, faces: np.ndarray) -> np.ndarray:
    xy = np.floor(pixels * source.size).astype(int).clip(0, source.size - 1)
    xx, yy = xy[:, 0], xy[:, 1]
    result = values[yy, xx].copy()
    missing = source.owner[yy, xx] != faces
    for face in np.unique(faces[missing]):
        affected = missing & (faces == face)
        sy, sx = np.nonzero(source.owner == face)
        if not len(sx):
            result[affected] = 0
            continue
        _, nearest = cKDTree(np.column_stack((sx, sy)) + 0.5).query(pixels[affected] * source.size)
        result[affected] = values[sy[nearest], sx[nearest]]
    return result
