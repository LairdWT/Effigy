"""Decimate to a face budget (IMPLEMENTATION.md M4): CuMesh simplify, two passes with repairs between.

params: {faces: 20000, topology: "tri"|"quad", symmetry: false|"x", fill: true, close: null} (symmetry: quad
only; mirrors props too: a hammer in one hand became two, so only for symmetric characters). `close` (metres,
2026-10-12): slits up to that width shut before simplifying, the solid's voxel close at half that pitch and
the filled solid's surface taken (a fence of 5 mm boards with hairline slits tore at every budget without it:
0.012 gave one watertight piece with no tunnel in 17 s). At least the model's length / 200: 0.006 on that
fence took 165 s and the simplify left 94 open edges. The close also smooths grooves narrower than it; the
bake's texture and normal map keep them. Without `close`, a generated prop's tri remesh (its chain starts at
a brief for a prop) whose surface comes back over 5 % folded through itself (`self_intersection`, as
validate measures it) is done again with `close` at the model's length / 150, kept when it folds less
(metrics.closed: close_m, self_intersection_before, kept, error); `close: 0` never. metrics.self_intersection:
the result's.
quad (M18): solid_hull (the input's solid, small holes closed) → blender_ops/quadriflow (voxel remesh,
QuadriFlow, Catmull-Clark, shrinkwrap onto the input) → `faces` quads, symmetric across X if asked. glTF
has no quads: mesh.glb holds them as triangle pairs, quads.obj keeps them (for Blender or a DCC); the quad
facts in the report come from Blender before the triangulation.
metrics.hausdorff_pct / p95_pct: distance to the input surface (filled: the filled solid's), % of its
bounding-box diagonal.
A hollow shell with holes (a generated black cat's back: a thin shell with holes up to ~7 cm, its inside open
to the outside; Clean closes it into a thick shell, and the remesh made tunnels where the holes were) is
filled first (`fill_inside`: holes from 4 % to 1/8 of its size), in both topologies: tri simplifies the
filled solid, quad shrinkwraps onto it. metrics.filled_gap_cm: how wide a hole it filled through (0: nothing
filled). `fill: false` keeps a model meant to be open inside (a birdhouse) as is.
"""

import json
import shutil
from pathlib import Path

import numpy as np

from steps._blender import BlenderError, run_blender
from steps._common import StepError, main, progress, root_meta
from steps._mesh import (
    drop_enclosed_parts,
    make_manifold,
    mesh_report,
    orient,
    read_glb,
    self_intersection,
    weld,
    write_glb,
)


def _cumesh_simplify(v, f, target: int, trust: bool = False):
    import cumesh
    import torch

    m = cumesh.CuMesh()
    m.init(torch.tensor(v, dtype=torch.float32).cuda(), torch.tensor(f, dtype=torch.int32).cuda())
    for faces in (
        target * 3,
        target,
    ):  # as upstream to_glb: coarse pass, repair, final pass, repair
        m.simplify(faces)
        m.remove_duplicate_faces()
    diag = float(np.linalg.norm(np.ptp(v, 0)))
    if trust:
        drop_enclosed_parts(m)
    # validate counts on welded topology: 0 edges with > 2 faces. The holes its face drops leave are a
    # few edges around, and at 12k triangles an edge is 2-4 cm: a fixed 3 % of the size left 54 open
    # on the robot; 12 mean edge lengths still leaves a real opening (a barrel's top) alone
    a, b = m.read()
    t = a[b.long()]
    edge = float((t - t.roll(1, 1)).norm(dim=2).mean())
    make_manifold(m, close=max(0.03 * diag, 12 * edge))
    orient(m, trust)  # trust: a rebuilt clean upstream (consistent winding); else ray votes
    v2, f2 = m.read()
    return v2.cpu().numpy(), f2.cpu().numpy()


def _rebuilt(src: Path) -> bool:
    """The nearest clean up the chain rebuilt the surface (steps/clean.py): its winding is consistent."""
    d = src
    while (d / "meta.json").is_file():
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        if meta.get("step") == "clean":
            return bool(meta.get("metrics", {}).get("rebuilt"))
        if not meta.get("parent"):
            return False
        d = d.parent / meta["parent"]
    return False


def _prop(src: Path) -> bool:
    """The chain starts at a brief for a prop (steps/brief.py's category): a generated prop, not a figure, whose
    fingers or arm by its side a close would join."""
    root = root_meta(src)
    return root.get("step") == "brief" and root.get("params", {}).get("category", "prop") == "prop"


def surface_distance(v_a, f_a, v_b, f_b, n: int = 40_000) -> tuple[float, float]:
    """(max, 95th percentile) of the two-way distance between surface samples, % of a's bbox diagonal."""
    import trimesh
    from scipy.spatial import cKDTree

    a, b = trimesh.Trimesh(v_a, f_a, process=False), trimesh.Trimesh(v_b, f_b, process=False)
    pa = trimesh.sample.sample_surface(a, n, seed=0)[0]
    pb = trimesh.sample.sample_surface(b, n, seed=1)[0]
    d = np.r_[
        cKDTree(pb).query(pa)[0], cKDTree(pa).query(pb)[0]
    ]  # ponytail: sample-to-sample, not exact
    diag = float(np.linalg.norm(a.bounds[1] - a.bounds[0]))
    return round(100 * d.max() / diag, 3), round(100 * float(np.percentile(d, 95)) / diag, 3)


# fill_inside's r (voxels) from which solid_hull fills: smaller holes are the close pass's (quad) or stay open
# edges validate reports (tri), as before; 46 of 66 library models have them. Larger ones made tunnels (the
# cat 6, the dwarf turnaround 7: 52 tunnels). ponytail: any hollow model with an opening up to 1/8 of its size
# is filled, a vase or a helmet too (not told apart from a cat's back): `fill: false` keeps it hollow
HOLE = 3


def fill_inside(occ: np.ndarray, rmax: int = 10) -> tuple[np.ndarray, int]:
    """The inside of a shell given as surface voxels `occ`, even through holes in it: the air the outside
    reaches only through passages narrower than 2r voxels and that lies deep (over r + 1 voxels from the
    skin), for the smallest r that finds an inside at least half the skin's size. A gap between two legs is
    sealed as well but thin, so it stays air. A closed model is found at r = 0 (the plain fill); returns the
    inside and r (-1: none, a thin thing such as a sign or a sword)."""
    from scipy import ndimage

    p = rmax + 2  # air around it deeper than any r: the outside is the corner's piece
    air = ~np.pad(occ, p)
    depth = ndimage.distance_transform_edt(air)
    for r in range(rmax + 1):
        lab, _ = ndimage.label(depth > r if r else air)
        core = lab == lab[0, 0, 0]
        outside = core if not r else (ndimage.distance_transform_edt(~core) <= r) & air
        sealed = air & ~outside
        parts, n = ndimage.label(sealed)
        if not n:
            continue
        deep = np.unique(parts[sealed & (depth > r + 1)])
        inside = np.isin(parts, deep[deep > 0])
        if inside.sum() > 0.5 * occ.sum():
            return inside[p:-p, p:-p, p:-p], r
    return np.zeros_like(occ), -1


def solid_hull(v, f, res: int = 160, close: int = 1, fill: bool = False, info: dict | None = None):
    """Closed boundary of the input's solid at `res` voxels along its longest side, as triangles: surface
    voxels, dilated by `close` (gaps up to ~2·close voxels shut), everything the outside can't reach filled,
    eroded back. Blender's voxel remesh needs a closed input: on a raw Faithful mesh (~12k open edges from
    small holes) it built a hollow sheet 1/90 of the volume, which QuadriFlow tore into holes. `fill`: a shell
    with holes of HOLE voxels or more gets its inside too (`fill_inside`); info gets filled_gap_cm and the
    voxel pitch."""
    import trimesh
    from scipy import ndimage

    v, f = np.asarray(v, float), np.asarray(f)
    lo = v.min(0)
    pitch = float((v.max(0) - lo).max()) / res
    m = trimesh.Trimesh(v, f, process=False)
    pts = np.r_[v, trimesh.sample.sample_surface(m, int(8 * m.area / pitch**2), seed=0)[0]]
    pad = 2 + close
    occ = np.zeros(np.ceil((v.max(0) - lo) / pitch).astype(int) + 2 * pad + 1, bool)
    occ[tuple((np.floor((pts - lo) / pitch).astype(int) + pad).T)] = True
    solid = ndimage.binary_dilation(occ, iterations=close) if close else occ
    solid = ndimage.binary_fill_holes(solid)
    if close:
        solid = ndimage.binary_erosion(solid, iterations=close) | occ
    inside, r = fill_inside(occ) if fill else (None, -1)
    if r >= HOLE:  # a shell with larger holes: its inside too
        solid = ndimage.binary_fill_holes(solid | inside)
    if info is not None:
        info["filled_gap_cm"] = round(2 * r * pitch * 100, 1) if r >= HOLE else 0.0
        info["pitch"] = pitch
    quads = []
    for a in range(3):
        u, w = np.eye(3, dtype=int)[(a + 1) % 3], np.eye(3, dtype=int)[(a + 2) % 3]
        n = solid.shape[a]
        s0, s1 = solid.take(np.arange(n - 1), axis=a), solid.take(np.arange(1, n), axis=a)
        cells = np.argwhere(s0 != s1)
        outward = s0[s0 != s1]  # solid below the face: its normal is +a
        base = cells.copy()
        base[:, a] += 1
        c = np.stack([base, base + u, base + u + w, base + w], 1)  # counter-clockwise seen from +a
        c[~outward] = c[~outward][:, ::-1]
        quads.append(c)
    corners = np.concatenate(quads)
    grid, idx = np.unique(corners.reshape(-1, 3), axis=0, return_inverse=True)
    q = idx.reshape(-1, 4)
    return (grid - pad) * pitch + lo, np.r_[q[:, [0, 1, 2]], q[:, [0, 2, 3]]]


def _filled(hull, pitch: float, out: Path):
    """The filled solid's surface, its voxel steps rounded off (blender_ops/print_parts)."""
    write_glb(out / "_hull.glb", *hull)
    try:
        run_blender("print_parts", [out / "_hull.glb"], out / "_solid", {"voxel": pitch})
    except BlenderError as e:
        raise StepError("failed", str(e)) from e
    v, f = weld(*read_glb(out / "_solid" / "solid.glb")[:2])
    shutil.rmtree(out / "_solid")
    (out / "_hull.glb").unlink()
    return v, f


def _quad(src: Path, out: Path, v, f, hull, target: int, symmetry) -> dict:
    write_glb(out / "_hull.glb", *hull)
    progress(0.3, f"voxel remesh + QuadriFlow to {target} quads")
    try:
        res = run_blender(
            "quadriflow",
            [out / "_hull.glb", src],
            out / "_quad",
            {"target_faces": target, "symmetry": symmetry == "x"},
            timeout=900,
        )
    except BlenderError as e:
        raise StepError("failed", str(e)) from e
    (out / "_quad" / "mesh.glb").replace(out / "mesh.glb")
    (out / "_quad" / "quads.obj").replace(out / "quads.obj")
    (out / "_hull.glb").unlink()
    shutil.rmtree(out / "_quad")
    qv, qf = weld(*read_glb(out / "mesh.glb")[:2])
    progress(0.8, "distance to the input surface")
    hmax, h95 = surface_distance(v, f, qv, qf)
    rep = res["report"] | {"hausdorff_pct": hmax, "p95_pct": h95}
    (out / "report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    keys = (
        "faces",
        "quads",
        "non_manifold_edges",
        "voxels",
        "hausdorff_pct",
        "p95_pct",
        "topology",
    )
    return {
        "outputs": {"mesh": "mesh.glb", "quads": "quads.obj", "report": "report.json"},
        "metrics": {k: rep[k] for k in keys},
    }


def run(op, in_dir, out_dir, params):
    target = int(params.get("faces", 20_000))
    if not in_dir or not 100 <= target <= 2_000_000:
        raise StepError("bad_params", "remesh needs a parent version and 100 <= faces <= 2M")
    meta = json.loads((Path(in_dir) / "meta.json").read_text(encoding="utf-8"))
    glb = next((f for f in meta["outputs"].values() if f.endswith(".glb")), None)
    if not glb:
        raise StepError("missing_input", f"{meta['version']} has no .glb")
    src, out = Path(in_dir) / glb, Path(out_dir)
    v, f = weld(*read_glb(src)[:2])
    topology = params.get("topology", "tri")
    if topology not in ("tri", "quad"):
        raise StepError("bad_params", "topology is tri or quad")
    progress(0.05, "closing the solid")
    info: dict = {}
    close = float(params.get("close") or 0)  # metres: slits up to this shut (thin boards)
    length = float(np.ptp(v, 0).max())
    if close:
        res = int(np.ceil(length / (close / 2)))
        # finer: minutes in the voxel solid and a simplify that leaves holes; the range it takes (agent finding 6)
        if not 10 <= res <= 400:
            raise StepError(
                "bad_params",
                f"close {close} m: 10 to 400 voxels over the model's {length:.2f} m, this is {res}: "
                f"use {np.ceil(length / 200 * 1e4) / 1e4} to {np.floor(length / 5 * 1e3) / 1e3}",
            )
        hull = solid_hull(v, f, res=res, close=2, fill=True, info=info)
    else:
        hull = solid_hull(v, f, fill=params.get("fill", True), info=info)
    filled = info["filled_gap_cm"]
    if filled or close:
        progress(0.1, f"filling its inside (holes up to {filled} cm)")
        # from here on its filled solid: tri simplifies it, quad shrinkwraps onto it (onto the input it pinned
        # quads to the hole rims, 75 non-manifold edges on the cat; onto both, the input's noise came through)
        # and measures its distance to it (to the holey input, every filled hole read as an error)
        v, f = _filled(hull, info["pitch"], out)
        src = out / "_filled.glb"
        write_glb(src, v, f)
    if topology == "quad":
        res = _quad(src, out, v, f, hull, target, params.get("symmetry"))
    else:
        progress(0.2, f"{len(f)} → {target} faces")
        if len(f) > target:  # the filled solid comes from Blender's remesh: consistent winding
            v, f = _cumesh_simplify(v, f, target, bool(filled) or _rebuilt(Path(in_dir)))
        write_glb(out / "mesh.glb", v, f)
        rep = mesh_report(v, f) | {"topology": "tri"}
        (out / "report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
        res = {
            "outputs": {"mesh": "mesh.glb", "report": "report.json"},
            "metrics": {"faces": rep["faces"]},
        }
    (out / "_filled.glb").unlink(missing_ok=True)
    res["metrics"]["filled_gap_cm"] = filled
    if topology == "tri":
        folded = self_intersection(*weld(*read_glb(out / "mesh.glb")[:2]))
        res["metrics"]["self_intersection"] = folded and folded["pct"]
        # agent finding 19: a bottle bank's slot and lid rim left 17.5 % folded through each other; slits up to
        # the length / 150 shut took it to 0 (the hoarding, the lamp and the wall needed a close as well). A prop's
        # only: 1.2 cm on a 1.8 m figure joins its fingers, and the library's figures come back 5-11 % folded
        if params.get("close") is None and folded and folded["pct"] > 5 and _prop(Path(in_dir)):
            progress(0.5, f"{folded['pct']} % folded through itself: again with its slits shut")
            closed = {"close_m": round(length / 150, 4), "self_intersection_before": folded["pct"]}
            (out / "_closed").mkdir(exist_ok=True)
            try:  # beside the first, which stands when this one fails or folds no less
                again = run(op, in_dir, str(out / "_closed"), params | {"close": length / 150})
                si = again["metrics"]["self_intersection"]
                closed["kept"] = si is not None and si < folded["pct"]
            except StepError as e:
                again, closed["kept"], closed["error"] = None, False, str(e)
            if closed["kept"]:
                for name in again["outputs"].values():
                    (out / "_closed" / name).replace(out / name)
                res = again
            shutil.rmtree(out / "_closed")
            res["metrics"]["closed"] = closed
    return res


if __name__ == "__main__":
    main(run)
