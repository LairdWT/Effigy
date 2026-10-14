"""The print split (IMPLEMENTATION.md M33): a parts version as solids that fit together, for a 3D printer.

A part cut from a generated model is a piece of its skin: holes where the next part was, small loose
islands; a slicer cannot fill that. So the cut is made in the volume instead: the whole model becomes a
voxel solid (its small holes closed), every voxel goes to the part whose surface is nearest, and each part's
voxels become a closed surface (their outer faces). Together the parts make up the whole solid, like a
jigsaw; Blender's voxel remesh then rounds off the voxel steps (blender_ops/print_parts.py). The voxels the
skin passes through count as inside: the solids are about half a voxel larger on every side (1.7 mm on a
1 m model at 300 voxels; scaled down in the slicer, a fraction of a millimetre).
"""

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

# voxels: holes in the skin up to about twice this wide are closed before the inside is filled
CLOSE = 2


def _samples(parts: dict[str, trimesh.Trimesh], pitch: float) -> tuple[np.ndarray, np.ndarray]:
    """Points on every part's surface, closer together than half a voxel, and the part of each."""
    pts, lab = [], []
    for i, m in enumerate(parts.values()):
        n = int(np.ceil(m.area / (pitch * 0.4) ** 2)) + len(m.faces)
        p, _ = trimesh.sample.sample_surface(m, n, seed=0)
        pts += [p, m.vertices]
        lab += [np.full(len(p) + len(m.vertices), i)]
    return np.concatenate(pts), np.concatenate(lab)


def split_solid(
    parts: dict[str, trimesh.Trimesh], pitch: float
) -> tuple[dict[str, trimesh.Trimesh], bool]:
    """Each part as the closed surface of its share of the whole model's voxel solid; and whether the solid
    stayed a hollow shell (a hole in the skin wider than the closing reaches: nothing to fill). Every part
    keeps at least its largest piece. ponytail: a dense grid (a 1 m figure at 300 voxels: ~25 M cells, ~1 s);
    a sparse grid and marching cubes if 600 voxels or wide models get slow."""
    pts, lab = _samples(parts, pitch)
    lo = pts.min(0) - (CLOSE + 2) * pitch
    shape = np.ceil((pts.max(0) + (CLOSE + 2) * pitch - lo) / pitch).astype(int)
    skin = np.zeros(shape, bool)
    skin[tuple(((pts - lo) / pitch).astype(int).T)] = True
    # the skin thickened until its holes are shut, the inside filled, then thinned back to the skin; gaps
    # under about 2 * CLOSE voxels fuse too (fingers, an arm close to the body)
    ball = ndimage.generate_binary_structure(3, 1)
    thick = ndimage.binary_dilation(skin, ball, iterations=CLOSE)
    filled = ndimage.binary_fill_holes(thick)
    # nothing inside to fill: a hole too wide (an open box: 0; the viking: 6.6 % of the thick skin)
    hollow = filled.sum() - thick.sum() < 0.01 * thick.sum()
    solid = ndimage.binary_erosion(filled, ball, iterations=CLOSE) | skin
    cells = np.argwhere(solid)
    _, nearest = cKDTree(pts).query(lo + (cells + 0.5) * pitch, workers=-1)
    owner = np.full(shape, -1, np.int32)
    owner[tuple(cells.T)] = lab[nearest]
    del solid, filled, thick, skin, cells
    out = {}
    for i, name in enumerate(parts):
        mask = owner == i
        pieces, n = ndimage.label(mask)
        if n > 1:  # crumbs where two parts meet go; the largest piece always stays
            sizes = ndimage.sum(mask, pieces, range(1, n + 1))
            keep = sizes >= max(8, 0.01 * sizes.max())
            keep[np.argmax(sizes)] = True
            mask = np.isin(pieces, 1 + np.flatnonzero(keep))
        if mask.any():
            out[name] = _faces(mask, lo, pitch)
    return out, bool(hollow)


def _faces(mask: np.ndarray, lo: np.ndarray, pitch: float) -> trimesh.Trimesh:
    """The outer faces of a voxel set, as triangles on the grid's corners, wound outwards. Closed, but not
    manifold where voxels meet only at an edge or a corner (blender_ops/print_parts.py remeshes that)."""
    m = np.pad(mask, 1)
    dims = np.array(m.shape) + 1  # corners per axis
    quads = []
    corners = np.array([[0, 0, 0], [0, 1, 0], [0, 1, 1], [0, 0, 1]])  # wound for +x (right-handed)
    for axis in range(3):
        d = np.diff(m.astype(np.int8), axis=axis)  # +1: empty -> full, -1: full -> empty
        c = np.roll(corners, axis, axis=1)  # the same square in this axis' plane, wound for +axis
        for sign, cs in ((1, c[::-1]), (-1, c)):  # empty -> full: the face looks back (-axis)
            idx = np.argwhere(d == sign)
            if len(idx):
                idx[:, axis] += 1  # the face lies between cell i and i + 1 of the padded grid
                quads.append(idx[:, None, :] + cs[None])
    q = np.concatenate(quads)  # (n, 4, 3) corner indices
    keys = (q[..., 0] * dims[1] + q[..., 1]) * dims[2] + q[
        ..., 2
    ]  # one int per corner: a light unique
    uniq, inv = np.unique(keys.ravel(), return_inverse=True)
    corner = np.stack(np.unravel_index(uniq, dims), axis=1)
    inv = inv.reshape(-1, 4)
    faces = np.concatenate([inv[:, [0, 1, 2]], inv[:, [0, 2, 3]]])
    mesh = trimesh.Trimesh(lo + (corner - 1) * pitch, faces, process=False)
    assert mesh.volume > 0, "voxel faces wound inwards"
    return mesh
