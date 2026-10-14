"""Checklist for a version's mesh (IMPLEMENTATION.md §3.9): each item pass|warn|fail with its number.
A sprite sheet (pixelize, sprites; M53) gets the 2D checklist instead (steps/_engine2d.checklist); a seamless tile
(M54: `tile`, raw or pixelized) the item `seamless` (steps/_pixel.seam_ratio, pass <= 1.1).

params: {"max_triangles": 100000, "max_colors": 32 (a sheet)}. ponytail: mesh + UV items only; texel density targets and rig QA join
the list as those steps land. numpy only (steps/_mesh.py): no Blender, no GPU.
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image

from steps import _engine2d, _pixel
from steps._common import StepError, main, progress, root_meta
from steps._mesh import (
    _by_size,
    mesh_report,
    parts_inside,
    read_glb,
    self_intersection,
    uv_report,
    weld,
)
from steps.brief import dims


def checklist(rep: dict, uv: dict | None, max_triangles: int) -> dict:
    items = {
        "manifold": (
            "pass" if rep["non_manifold_edges"] == 0 else "warn",
            rep["non_manifold_edges"],
        ),
        "watertight": ("pass" if rep["boundary_edges"] == 0 else "warn", rep["boundary_edges"]),
        "single_part": ("pass" if rep["components"] == 1 else "warn", rep["components"]),
        "no_tunnels": ("pass" if not rep.get("tunnels") else "warn", rep.get("tunnels") or 0),
        "no_degenerate_faces": (
            "pass" if rep["degenerate_faces"] == 0 else "warn",
            rep["degenerate_faces"],
        ),
        "has_uvs": ("pass" if uv else "fail", bool(uv)),
        "uvs_in_0_1": ("pass" if uv and uv["in_0_1"] else "fail", bool(uv and uv["in_0_1"])),
        "triangle_budget": ("pass" if rep["faces"] <= max_triangles else "warn", rep["faces"]),
        "scale_metres": ("pass" if 0.05 <= rep["height_m"] <= 50 else "fail", rep["height_m"]),
    }
    if uv:  # in percent of the covered texels: refine and bake paint through what overlaps (agent 2026-10-11)
        pct = round(100 * uv["overlap"], 1)
        items["uv_overlap"] = ("pass" if pct < 1 else "warn" if pct < 10 else "fail", pct)
    # geometry the topology cannot see (mesh-gates, 2026-10-12): "skip" when nothing closed could be tested
    si, pi = rep.get("self_intersection"), rep.get("parts_inside")
    items["self_intersection"] = (
        ("skip", None) if si is None else ("pass" if si["pct"] < 1 else "warn", si["pct"])
    )
    items["parts_apart"] = (
        ("skip", None) if pi is None else ("pass" if pi["pct"] < 5 else "warn", pi["pct"])
    )
    size = rep.get("size")
    if size and size["drift_pct"] is not None:  # only when the brief gives a height or a length
        items["size_drift_pct"] = ("pass" if size["drift_pct"] < 10 else "warn", size["drift_pct"])
    return {name: {"status": status, "value": value} for name, (status, value) in items.items()}


def size_drift(v: np.ndarray, want: dict) -> dict:
    """The model's size against the brief's (`brief.dims`): the height and the plan's long side (its smallest-area
    rectangle: the model may face any way), drift_pct the larger miss (None: nothing to judge). The long side only when
    the brief calls a size long or gives two (one "0.5 m wide" on a figure is no length); the thin side is reported,
    not judged: a brief's "0.3 m deep" for a 0.19 m hoarding panel was a room to fit in, not a size."""
    import trimesh
    from scipy.spatial import QhullError

    try:
        plan = trimesh.bounds.oriented_bounds_2D(v[:, [0, 2]])[1]
    except QhullError:  # a plan with no area (a card on edge): its box
        plan = np.ptp(v[:, [0, 2]], 0)
    got = {
        "height": round(float(np.ptp(v[:, 1])), 3),
        "plan": sorted((round(float(x), 3) for x in plan), reverse=True),
    }
    side = want.get("long") or (want["plan"][0] if len(want.get("plan", [])) > 1 else None)
    pairs = [(side, got["plan"][0])] if side else []
    pairs += [(want["height"], got["height"])] if "height" in want else []
    drift = max((abs(g / w - 1) for w, g in pairs), default=None)
    return {
        "brief_m": want,
        "model_m": got,
        "drift_pct": None if drift is None else round(100 * drift, 1),
    }


def run(op, in_dir, out_dir, params):
    if not in_dir:
        raise StepError("missing_input", "validate needs a parent version")
    meta = json.loads((Path(in_dir) / "meta.json").read_text(encoding="utf-8"))
    outs = meta["outputs"]
    mesh = next((f for f in outs.values() if f.endswith(".glb")), None)
    if not mesh and ("sheet" in outs and "data" in outs or "tile" in outs or "layers" in outs):
        items, report = {}, {}
        if "sheet" in outs and "data" in outs:  # the sheet's checklist
            sheet = Image.open(Path(in_dir) / outs["sheet"])
            data = json.loads((Path(in_dir) / outs["data"]).read_text(encoding="utf-8"))
            items = _engine2d.checklist(sheet, data, int(params.get("max_colors", 32)))
            report = {"frames": len(data["frames"]), "size": list(sheet.size)}
        if "layers" in outs:  # M55: at least two, the farthest covering the whole picture
            data = json.loads((Path(in_dir) / outs["layers"]).read_text(encoding="utf-8"))
            far = np.asarray(Image.open(Path(in_dir) / data[0]["file"]).convert("RGBA"))[..., 3]
            gaps = round(float((far < 255).mean()), 4)
            items["layers"] = {"status": "pass" if len(data) >= 2 else "fail", "value": len(data)}
            items["far_layer_whole"] = {"status": "pass" if gaps == 0 else "warn", "value": gaps}
            report["layers"] = [d["scroll_scale"] for d in data]
        if "tile" in outs:
            tile = np.asarray(Image.open(Path(in_dir) / outs["tile"]).convert("RGBA"))
            ratio = round(_pixel.seam_ratio(tile), 3)
            items["seamless"] = {
                "status": "pass" if ratio <= _pixel.SEAM_PASS else "warn",
                "value": ratio,
            }
            report["tile"] = [tile.shape[1], tile.shape[0]]
        out = {"items": items, "report": report}
        (Path(out_dir) / "checklist.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        fails = sum(i["status"] == "fail" for i in items.values())
        return {"outputs": {"checklist": "checklist.json"}, "metrics": {"fail": fails}}
    if not mesh:
        raise StepError("missing_input", f"{meta['version']} has no .glb output or sprite sheet")
    progress(0.1, "checking the mesh")
    v, f, uv = read_glb(Path(in_dir) / mesh)
    wv, wf = weld(v, f)
    rep = mesh_report(wv, wf)  # topology on welded seams; UVs stay per corner
    progress(0.4, "ray parity: the surface against itself, the parts against each other")
    comps = _by_size(wv, wf, 24)
    rep["self_intersection"] = self_intersection(wv, wf, comps)
    rep["parts_inside"] = parts_inside(wv, wf, comps)
    root = root_meta(Path(in_dir))
    if root.get("step") == "brief" and (want := dims(root.get("params", {}).get("prompt", ""))):
        rep["size"] = size_drift(np.asarray(wv, float), want)
    uvr = uv_report(uv, f, v) if uv is not None else None
    items = checklist(rep, uvr, params.get("max_triangles", 100_000))
    out = {"items": items, "report": rep, "uv": uvr}
    (Path(out_dir) / "checklist.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    fails = sum(i["status"] == "fail" for i in items.values())
    return {"outputs": {"checklist": "checklist.json"}, "metrics": {"fail": fails}}


if __name__ == "__main__":
    main(run)
