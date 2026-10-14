# SPDX-License-Identifier: GPL-3.0-or-later
"""Run inside Blender at test time: blender -b --python make_rig52.py -- out.fbx

A box body on the 52-joint template, rigidly weighted, one 12-frame clip ("Armature|Wave": the left arm turns
0.05 rad a frame about Y, the hips rise), written as a centimetre FBX with `mixamorig:` names; the exporter
adds a leaf bone on the head, the toes and the fingertips (13), the way Mixamo's files come.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from steps import _rig

BOX = ((-0.4, -0.1, 0.0), (0.4, 0.1, 1.7))


def positions() -> dict:
    pos = {"Hips": (0, 0, 0.9), "Spine": (0, 0, 1.0), "Spine1": (0, 0, 1.1), "Spine2": (0, 0, 1.2)}
    pos |= {"Neck": (0, 0, 1.4), "Head": (0, 0, 1.5)}
    for s, x in (("Left", 1), ("Right", -1)):
        pos |= {f"{s}Shoulder": (x * 0.1, 0, 1.35), f"{s}Arm": (x * 0.25, 0, 1.35)}
        pos |= {f"{s}ForeArm": (x * 0.5, 0, 1.35), f"{s}Hand": (x * 0.75, 0, 1.35)}
        for i, f in enumerate(_rig.FINGERS):
            for k in (1, 2, 3):
                pos[f"{s}Hand{f}{k}"] = (x * (0.78 + 0.04 * k), 0.03 * (i - 2), 1.35)
        pos |= {f"{s}UpLeg": (x * 0.1, 0, 0.9), f"{s}Leg": (x * 0.1, 0, 0.5)}
        pos |= {f"{s}Foot": (x * 0.1, 0, 0.1), f"{s}ToeBase": (x * 0.1, 0.15, 0.05)}
    return pos


def main(out: str, away: bool = False) -> None:
    import bpy
    from mathutils import Vector

    bpy.ops.wm.read_factory_settings(use_empty=True)
    U = 100  # centimetres
    pos, tmpl = {n: tuple(U * c for c in p) for n, p in positions().items()}, _rig.template()
    arm_data = bpy.data.armatures.new("Armature")
    arm = bpy.data.objects.new("Armature", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    kids = {n: [c for c, p in tmpl if p == n] for n, _ in tmpl}
    for n, parent in tmpl:
        b = arm_data.edit_bones.new(f"mixamorig:{n}")
        b.head = Vector(pos[n])
        b.tail = Vector(pos[kids[n][0]]) if kids[n] else Vector(pos[n]) + Vector((0, 0, 5))
        if b.length < 0.01:
            b.tail = b.head + Vector((0, 0, 5))
        if parent:
            b.parent = arm_data.edit_bones[f"mixamorig:{parent}"]
    bpy.ops.object.mode_set(mode="OBJECT")
    # the body: a box, every vertex on the nearest joint
    bpy.ops.mesh.primitive_cube_add()
    body = bpy.context.active_object
    body.name = "Body"
    for v in body.data.vertices:
        v.co = Vector([U * (BOX[0][i] if v.co[i] < 0 else BOX[1][i]) for i in range(3)])
    for n, _ in tmpl:
        body.vertex_groups.new(name=f"mixamorig:{n}")
    for v in body.data.vertices:
        near = min(pos, key=lambda n: (Vector(pos[n]) - v.co).length)
        body.vertex_groups[f"mixamorig:{near}"].add([v.index], 1.0, "REPLACE")
    body.modifiers.new("Armature", "ARMATURE").object = arm
    body.parent = arm
    # the clip
    bpy.context.scene.render.fps = 24
    bpy.context.view_layer.objects.active = arm
    act = bpy.data.actions.new("Armature|Wave")
    arm.animation_data_create().action = act
    arm.animation_data.action_slot = act.slots.new(id_type="OBJECT", name="Armature")
    bpy.ops.object.mode_set(mode="POSE")
    hip, left = arm.pose.bones["mixamorig:Hips"], arm.pose.bones["mixamorig:LeftArm"]
    left.rotation_mode = "XYZ"
    for f in range(12):
        left.rotation_euler = (0, 0.05 * f, 0)
        hip.location = (0, 0, 1.0 * f)
        left.keyframe_insert("rotation_euler", frame=f + 1)
        hip.keyframe_insert("location", frame=f + 1)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.scene.frame_end = 12
    # centimetres, as Mixamo writes them: the numbers are centimetres, the scene says so
    bpy.context.scene.unit_settings.scale_length = 0.01
    if away:  # facing away: everything turned round about the vertical
        for o in bpy.context.scene.objects:
            if o.parent is None:
                o.rotation_euler.z += math.pi
    bpy.ops.export_scene.fbx(filepath=out)


if __name__ == "__main__":
    main(*sys.argv[sys.argv.index("--") + 1 :][:1], away="away" in sys.argv)
