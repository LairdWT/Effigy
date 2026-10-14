# SPDX-License-Identifier: Apache-2.0
"""GeoSAM2's `utils/mode_ext.cpp` (a per-row mode: the most frequent label, 0 only when nothing else is
there) as torch, so no compiler is needed at import; steps/parts.py registers it as `utils.mode_ext`
before GeoSAM2's utils import it (PATCHES.md). Counts over the distinct labels only: GeoSAM2 feeds it
5 rows per face and labels up to 999, so a dense table would take rows × 1000 × 8 bytes (4 GB at 100k
faces)."""

import torch


def mode_except_negative_one(x: torch.Tensor) -> torch.Tensor:
    n, d = x.shape
    labels, idx = torch.unique(x, return_inverse=True)  # sorted, so ties go to the smaller label
    counts = torch.zeros(n, len(labels), dtype=torch.int32, device=x.device)
    counts.scatter_add_(1, idx.view(n, d), torch.ones(n, d, dtype=torch.int32, device=x.device))
    zero = (labels == 0).nonzero().flatten()
    if len(zero):
        counts[:, zero[0]] = -1  # 0 wins only when nothing else is there
    best = counts.max(1)
    return torch.where(best.values > 0, labels[best.indices], torch.zeros_like(best.indices)).to(
        torch.int32
    )
