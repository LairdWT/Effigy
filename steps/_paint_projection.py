"""Sample projection edits without filtering another face or retaining replaced detail."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ProjectedSamples:
    values: np.ndarray
    supported: np.ndarray


@dataclass(frozen=True)
class ProjectedReplacement:
    values: np.ndarray
    supported: np.ndarray
    changed: np.ndarray


def sample_replacement(original: np.ndarray, edited: np.ndarray, pixels: np.ndarray,
                       face_image: np.ndarray, face_ids: np.ndarray, permitted: np.ndarray,
                       opaque: np.ndarray, *, footprints: np.ndarray | None = None,
                       eligible: np.ndarray | None = None) -> ProjectedReplacement:
    changed = np.any(edited != original, axis=2)
    values = np.concatenate((edited, changed[..., None]), axis=2).astype(np.float64)
    if footprints is None:
        samples = sample_owned(values, pixels, face_image, face_ids, permitted, opaque)
    else:
        samples = sample_footprints(values, pixels, face_image, face_ids, permitted, opaque, footprints, eligible)
    return ProjectedReplacement(samples.values[:, :3], samples.supported, samples.values[:, 3] > 0)


def sample_footprints(values: np.ndarray, pixels: np.ndarray, face_image: np.ndarray,
                      face_ids: np.ndarray, permitted: np.ndarray, opaque: np.ndarray,
                      footprints: np.ndarray, eligible: np.ndarray | None) -> ProjectedSamples:
    """Integrate each atlas texel's camera footprint without mixing view or face owners."""
    if footprints.shape != (len(pixels), 2, 2) or not np.isfinite(footprints).all():
        raise ValueError("Projection footprints must contain finite UV-to-camera transforms")
    active = np.ones(len(pixels), dtype=bool) if eligible is None else eligible
    if active.shape != (len(pixels),) or active.dtype != np.bool_:
        raise ValueError("Projection eligibility must match the target texel list")
    indices = np.flatnonzero(active)
    numerator = np.zeros((len(pixels), values.shape[2]), dtype=np.float64)
    denominator = np.zeros(len(pixels), dtype=np.int64)
    grid = np.maximum(1, np.ceil(np.linalg.norm(footprints[indices], axis=1)))
    maximum_work = 64_000_000
    if np.any(grid > maximum_work):
        raise ValueError("UV distortion makes projection filtering too expensive; inspect the prepared UV layout")
    grid = grid.astype(np.int64)
    work = grid.prod(1)
    if np.any(work > maximum_work) or work.sum() > maximum_work:
        raise ValueError("Projection filtering exceeds 64 million sample sites; inspect UV distortion or select a smaller region")
    height, width = face_image.shape
    scale = np.array([width, height])
    for dimensions in np.unique(grid, axis=0):
        targets = indices[(grid == dimensions).all(1)]
        nu, nv = (int(value) for value in dimensions)
        for start in range(0, nu * nv, 4096):
            sites = np.arange(start, min(start + 4096, nu * nv))
            offsets = np.stack(((sites // nv + 0.5) / nu - 0.5,
                                (sites % nv + 0.5) / nv - 0.5), axis=1)
            batch = max(1, 65536 // len(offsets))
            for first in range(0, len(targets), batch):
                chosen = targets[first:first + batch]
                delta = np.einsum("nij,kj->nki", footprints[chosen], offsets) / scale
                locations = (pixels[chosen, None] + delta).reshape(-1, 2)
                samples = sample_owned(values, locations, face_image, np.repeat(face_ids[chosen], len(offsets)), permitted, opaque)
                supported = samples.supported.reshape(len(chosen), len(offsets))
                colours = samples.values.reshape(len(chosen), len(offsets), values.shape[2])
                numerator[chosen] += (colours * supported[..., None]).sum(1)
                denominator[chosen] += supported.sum(1)
    supported = denominator > 0
    numerator[supported] /= denominator[supported, None]
    return ProjectedSamples(numerator, supported)


def sample_owned(values: np.ndarray, pixels: np.ndarray, face_image: np.ndarray,
                 face_ids: np.ndarray, permitted: np.ndarray, opaque: np.ndarray) -> ProjectedSamples:
    if values.shape[:2] != face_image.shape or permitted.shape != face_image.shape or opaque.shape != face_image.shape:
        raise ValueError("Projection colours, permission, alpha and face ownership must share the same native pixel grid")
    height, width = face_image.shape
    position = pixels * np.array([width, height]) - 0.5
    origin = np.floor(position).astype(np.int64)
    fraction = position - origin
    numerator = np.zeros((len(pixels), values.shape[2]), dtype=np.float64)
    denominator = np.zeros(len(pixels), dtype=np.float64)
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        xy = origin + [dx, dy]
        inside = (xy[:, 0] >= 0) & (xy[:, 0] < width) & (xy[:, 1] >= 0) & (xy[:, 1] < height)
        x, y = xy[:, 0].clip(0, width - 1), xy[:, 1].clip(0, height - 1)
        weight = (fraction[:, 0] if dx else 1 - fraction[:, 0]) * (fraction[:, 1] if dy else 1 - fraction[:, 1])
        eligible = inside & (face_image[y, x] == face_ids) & permitted[y, x] & opaque[y, x]
        weight *= eligible
        numerator += values[y, x] * weight[:, None]
        denominator += weight
    supported = denominator > 1e-8
    numerator[supported] /= denominator[supported, None]
    return ProjectedSamples(numerator, supported)


def selection_feather(mask: np.ndarray, covered: np.ndarray, width: int) -> np.ndarray:
    from scipy.ndimage import distance_transform_edt

    if width <= 0 or not np.any(covered & ~mask):
        return np.ones(int(covered.sum()), dtype=np.float64)
    distance = distance_transform_edt(mask | ~covered)
    return np.minimum(distance[covered] / width, 1)
