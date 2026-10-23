"""Binary source/generated boundaries and conservative image regression signals."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import breadth_first_order, maximum_flow

from steps._common import StepError


@dataclass(frozen=True)
class CutResult:
    mask: np.ndarray
    metrics: dict
    reasons: tuple[str, ...]


def hard_cut(source: np.ndarray, generated: np.ndarray, core: np.ndarray, outer: np.ndarray) -> CutResult:
    if not core.any() or np.any(core & ~outer):
        raise StepError("bad_params", "Finishing core is empty or exceeds permission")
    yy, xx = np.nonzero(outer)
    x0, x1 = max(0, int(xx.min()) - 1), min(source.shape[1], int(xx.max()) + 2)
    y0, y1 = max(0, int(yy.min()) - 1), min(source.shape[0], int(yy.max()) + 2)
    region = np.s_[y0:y1, x0:x1]
    a, b = source[region][..., :3].astype(np.float64), generated[region][..., :3].astype(np.float64)
    inner, allowed = core[region], outer[region]
    height, width = inner.shape
    count = height * width
    if count > 160_000:
        raise StepError("bad_params", "Finishing boundary exceeds its bounded graph; split the region")
    ids = np.arange(count).reshape(height, width)
    difference = np.abs(a - b).mean(2)
    rows, columns, weights = [], [], []
    for first, second in ((np.s_[:-1, :], np.s_[1:, :]), (np.s_[:, :-1], np.s_[:, 1:])):
        edge_error = np.abs((a[first] - a[second]) - (b[first] - b[second])).mean(2)
        cost = np.rint(1 + 4 * (difference[first] + difference[second] + 2 * edge_error)).clip(1, 1024).astype(np.int64).ravel()
        u, v = ids[first].ravel(), ids[second].ravel()
        rows.extend((u, v))
        columns.extend((v, u))
        weights.extend((cost, cost))
    total = sum(int(v.sum()) for v in weights)
    if total >= 2_000_000_000:
        raise StepError("bad_params", "Finishing boundary capacity exceeds the integer solver limit")
    infinity = total + 1
    source_node, sink_node = count, count + 1
    fixed_generated = ids[inner].ravel()
    fixed_original = ids[~allowed].ravel()
    rows.extend((np.full(len(fixed_generated), source_node), fixed_original))
    columns.extend((fixed_generated, np.full(len(fixed_original), sink_node)))
    weights.extend((np.full(len(fixed_generated), infinity), np.full(len(fixed_original), infinity)))
    graph = coo_matrix((np.concatenate(weights), (np.concatenate(rows), np.concatenate(columns))),
                       shape=(count + 2, count + 2), dtype=np.int64).tocsr()
    flow = maximum_flow(graph, source_node, sink_node)
    residual = graph - flow.flow
    residual.data[residual.data <= 0] = 0
    residual.eliminate_zeros()
    reachable = breadth_first_order(residual, source_node, directed=True, return_predecessors=False)
    chosen = np.zeros(count + 2, dtype=bool)
    chosen[reachable] = True
    chosen = chosen[:count].reshape(height, width)
    if np.any(inner & ~chosen) or np.any(chosen & ~allowed):
        raise StepError("failed", "Hard boundary violated its fixed core or protected exterior")
    components, labels = cv2.connectedComponents(chosen.astype(np.uint8), connectivity=4)
    core_components = {int(i) for i in np.unique(labels[inner])}
    reasons = []
    if 0 in core_components or len(core_components) != 1 or components != 2:
        reasons.append("disconnected_boundary")
    boundary = chosen & ~(cv2.erode(chosen.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    boundary_difference = difference[boundary]
    mean = float(boundary_difference.mean()) if len(boundary_difference) else float("inf")
    p95 = float(np.percentile(boundary_difference, 95)) if len(boundary_difference) else float("inf")
    if mean > 24 or p95 > 55:
        reasons.append("boundary_disagreement")
    mask = np.zeros_like(core)
    mask[region] = chosen
    return CutResult(mask, {"boundary_mean_rgb8": round(mean, 3), "boundary_p95_rgb8": round(p95, 3),
                            "graph_pixels": count, "core_pixels": int(core.sum()), "cut_pixels": int(mask.sum()),
                            "connected_regions": components - 1, "boundary_method": "integer_st_mincut"}, tuple(reasons))


def image_regression(source: np.ndarray, result: np.ndarray, mask: np.ndarray) -> tuple[dict, tuple[str, ...]]:
    if not mask.any():
        raise StepError("bad_params", "Regression inspection has an empty repair mask")
    old = cv2.cvtColor(source[..., :3], cv2.COLOR_RGB2GRAY).astype(np.float32)
    new = cv2.cvtColor(result[..., :3], cv2.COLOR_RGB2GRAY).astype(np.float32)
    old_gradient = cv2.magnitude(cv2.Sobel(old, -1, 1, 0), cv2.Sobel(old, -1, 0, 1))
    new_gradient = cv2.magnitude(cv2.Sobel(new, -1, 1, 0), cv2.Sobel(new, -1, 0, 1))
    gradient_ratio = float(new_gradient[mask].mean() / max(1.0, float(old_gradient[mask].mean())))
    dark_increase = float((new[mask] < 35).mean() - (old[mask] < 35).mean())
    colour_shift = float(np.abs(np.median(source[..., :3][mask], axis=0) - np.median(result[..., :3][mask], axis=0)).mean())
    reasons = []
    if gradient_ratio < 0.55:
        reasons.append("detail_loss")
    if gradient_ratio > 2.4:
        reasons.append("excessive_new_detail")
    if dark_increase > 0.06:
        reasons.append("new_dark_region")
    if colour_shift > 32:
        reasons.append("material_colour_drift")
    return {"gradient_ratio": round(gradient_ratio, 4), "dark_fraction_increase": round(dark_increase, 4),
            "median_colour_shift_rgb8": round(colour_shift, 3), "art_acceptance": "pending_visual_review"}, tuple(reasons)
