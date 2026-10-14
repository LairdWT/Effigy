# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [mesh.glb, parts.json]; params: {} → mesh.glb: one object per part, named after it, the unlabelled
rest as "Body" (M31). parts.json: {"labels": [one int per face of the input, 0 = none], "parts": [{"id",
"name"}]}. The input is read without merging vertices so its face order is the one GeoSAM2 labelled
(blender_ops/parts_views wrote it)."""

import json
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, export_glb, import_mesh, job

j = job()
out = Path(j["out_dir"])
parts = json.loads(Path(j["in"][1]).read_text(encoding="utf-8"))
labels = parts["labels"]

src = import_mesh(j["in"][0], merge=False)  # one mesh: parts_views wrote it
assert len(src.data.polygons) == len(labels), (
    f"{len(labels)} labels for {len(src.data.polygons)} faces"
)

bm = bmesh.new()
bm.from_mesh(src.data)
bm.faces.ensure_lookup_table()
names = [(p["id"], p["name"]) for p in parts["parts"]] + [(0, "Body")]
counts = {}
for pid, name in names:
    keep = [i for i, lab in enumerate(labels) if lab == pid]
    if not keep:
        continue
    part = bm.copy()
    part.faces.ensure_lookup_table()
    drop = [f for i, f in enumerate(part.faces) if labels[i] != pid]
    bmesh.ops.delete(part, geom=drop, context="FACES")
    me = src.data.copy()  # the material slots and the UV layers come along
    part.to_mesh(me)
    part.free()
    me.name = name
    obj = bpy.data.objects.new(name, me)
    obj.matrix_world = src.matrix_world
    bpy.context.scene.collection.objects.link(obj)
    counts[name] = len(keep)
bm.free()
bpy.data.objects.remove(src, do_unlink=True)
export_glb(out / "mesh.glb")
done(j, {"parts": counts})
