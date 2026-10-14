# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [voxel parts .glb: one closed object per part, its voxels' outer faces (steps/_print.py)]; params:
{"voxel": the grid's size in metres, "smooth": passes (4)} → solid.glb: the same parts, each one manifold
watertight surface with the voxel steps rounded off.

The print split (IMPLEMENTATION.md M33): a voxel remesh at the grid's own size makes each part manifold
(voxels that meet only at an edge or a corner become one surface) and a light Laplacian smoothing takes the
stairs out; both keep the part closed. The remesh resamples on Blender's own grid (features one voxel thin
can thin out) and the smoothing shrinks a little, each part on its own: neighbours fit to about a voxel.
"""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, export_glb, import_meshes, job


def main() -> None:
    j = job()
    p = j["params"]
    voxel, smooth = float(p["voxel"]), int(p.get("smooth", 4))
    parts = import_meshes(j["in"][0])
    report = {}
    for o in parts:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        rm = o.modifiers.new("manifold", "REMESH")
        rm.mode, rm.voxel_size = "VOXEL", voxel
        sm = o.modifiers.new("steps", "CORRECTIVE_SMOOTH")  # only_smooth: a plain Laplacian smooth
        sm.iterations, sm.smooth_type, sm.use_only_smooth = smooth * 3, "SIMPLE", True
        for m in (rm, sm):
            bpy.ops.object.modifier_apply(modifier=m.name)
        report[o.name] = {"faces": len(o.data.polygons)}
    bpy.ops.object.select_all(action="SELECT")
    export_glb(Path(j["out_dir"]) / "solid.glb", use_selection=True, export_animations=False)
    done(j, {"parts": report})


main()
