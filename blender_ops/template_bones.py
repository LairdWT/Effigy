# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [rig.glb] → bones.json: every bone's name, parent, head and tail in the glTF frame (Y up, metres).

For the creature templates (IMPLEMENTATION.md M36, tools/templates.py): a glTF skeleton has joints, not
bones; Blender's importer turns each joint's authored orientation back into a bone with a tail, which is
what the skinning needs to point a creature's bones (a hip towards the spine, not towards a leg).
"""

import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, job

j = job()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=j["in"][0])
arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")


def gltf(v):  # Blender (x, y, z) → glTF (x, z, -y)
    w = arm.matrix_world @ v
    return [round(w.x, 5), round(w.z, 5), round(-w.y, 5)]


bones = [
    {
        "name": b.name,
        "parent": b.parent.name if b.parent else None,
        "head": gltf(b.head_local),
        "tail": gltf(b.tail_local),
    }
    for b in arm.data.bones
]
Path(j["out_dir"], "bones.json").write_text(json.dumps(bones, indent=1), encoding="utf-8")
done(j, {"bones": len(bones)})
