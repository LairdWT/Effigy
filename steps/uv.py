"""UV-unwrap (IMPLEMENTATION.md M4): CuMesh charts (cone angle) + xatlas packing → mesh.glb with UVs.

params: {cone_deg: 90, refine: 0, global_iterations: 1, smooth: 1}
"""

import json
from pathlib import Path

import numpy as np

from steps._common import StepError, main, progress
from steps._mesh import read_glb, uv_report, weld, write_glb


def _cumesh_unwrap(v, f, p: dict):
    import cumesh
    import torch

    m = cumesh.CuMesh()
    m.init(torch.tensor(v, dtype=torch.float32).cuda(), torch.tensor(f, dtype=torch.int32).cuda())
    v2, f2, uv, _ = m.uv_unwrap(
        compute_charts_kwargs={
            "threshold_cone_half_angle_rad": float(np.radians(p.get("cone_deg", 90))),
            "refine_iterations": int(p.get("refine", 0)),
            "global_iterations": int(p.get("global_iterations", 1)),
            "smooth_strength": float(p.get("smooth", 1)),
        },
        return_vmaps=True,
    )
    return v2.cpu().numpy(), f2.cpu().numpy(), uv.cpu().numpy()


def run(op, in_dir, out_dir, params):
    if not in_dir:
        raise StepError("missing_input", "uv needs a parent version with a mesh")
    meta = json.loads((Path(in_dir) / "meta.json").read_text(encoding="utf-8"))
    glb = next((f for f in meta["outputs"].values() if f.endswith(".glb")), None)
    if not glb:
        raise StepError("missing_input", f"{meta['version']} has no .glb")
    v, f = weld(*read_glb(Path(in_dir) / glb)[:2])
    progress(0.2, f"unwrapping {len(f)} faces")
    v, f, uv = _cumesh_unwrap(v, f, params)
    write_glb(Path(out_dir) / "mesh.glb", v, f, uv)
    rep = uv_report(uv, f, v)
    (Path(out_dir) / "uv_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    if not rep["in_0_1"]:
        raise StepError("failed", "unwrap produced UVs outside [0, 1]")
    return {
        "outputs": {"mesh": "mesh.glb", "uv_report": "uv_report.json"},
        "metrics": {"islands": rep["islands"]},
    }


if __name__ == "__main__":
    main(run)
