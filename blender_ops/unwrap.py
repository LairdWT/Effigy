# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [mesh.glb]; params: {"angle_limit": 66, "margin": 0.002} → mesh.glb with one packed UV layer.

Smart Project for islands → seams → Minimum Stretch (SLIM) inside them → equal texel scale → pack.
"""

import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, export_glb, import_mesh, job, mesh_report

j = job()
p = j["params"]
obj = import_mesh(j["in"][0])
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(p.get("angle_limit", 66)), island_margin=0)
bpy.ops.uv.seams_from_islands()
bpy.ops.uv.unwrap(method="MINIMUM_STRETCH", margin=0)
bpy.ops.uv.average_islands_scale()
bpy.ops.uv.pack_islands(shape_method="CONCAVE", rotate_method="ANY", margin=p.get("margin", 0.002))
bpy.ops.object.mode_set(mode="OBJECT")
rep = mesh_report(obj)
assert rep["uv_layers"] >= 1 and rep["uv_in_unit_square"], f"unwrap failed: {rep}"
export_glb(Path(j["out_dir"]) / "mesh.glb")
done(j, {"outputs": {"mesh": "mesh.glb"}, "report": rep})
