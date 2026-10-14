# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [model.glb]; params: {"size": 384, "clip": "", "turn": 0} → look_0..3.png (Workbench, textured where the GLB is).
Without a clip: front, right side, back, front three-quarter. With one: four frames spread over it, three-quarter.
`turn` N > 0 (M42): N cameras round the model at the current frame, from the front: look_0..N-1.png."""

import sys
from math import cos, pi, sin
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, import_meshes, job

j = job()
p = j["params"]
size, clip, turn = p.get("size", 384), p.get("clip", ""), int(p.get("turn", 0))
meshes = import_meshes(j["in"][0], merge=False)
scene = bpy.context.scene
frames = [scene.frame_current] * (turn or 4)
if clip:
    # the glTF importer parks clips in NLA tracks and leaves one action on top: mute them, set ours
    act = next((a for a in bpy.data.actions if a.name == clip or a.name.endswith("|" + clip)), None)
    assert act, f"no action for clip {clip!r} in {[a.name for a in bpy.data.actions]}"
    for o in [o for o in scene.objects if o.animation_data]:
        ad = o.animation_data
        for t in ad.nla_tracks:
            t.mute = True
        ad.action = act
        if act.slots:
            ad.action_slot = act.slots[0]
    f0, f1 = act.frame_range
    frames = [
        round(f0 + (f1 - f0) * i / 4) for i in range(4)
    ]  # 4 of a loop's 5 stops: no repeated start


def bounds():
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    dg = bpy.context.evaluated_depsgraph_get()
    for o in meshes:
        for c in o.evaluated_get(dg).bound_box:
            w = o.matrix_world @ Vector(c)
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    return lo, hi


lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for f in frames[:4]:  # one framing for the whole sheet, over every frame shown
    scene.frame_set(f)
    a, b = bounds()
    lo, hi = Vector(map(min, lo, a)), Vector(map(max, hi, b))
center, ext = (lo + hi) / 2, hi - lo
# Blender's glTF import faces the model to -Y, up +Z; the character's right is -X
dirs = [(0, -1, 0.05), (-1, 0, 0.05), (0, 1, 0.05), (0.8, -1, 0.4)]
views = [dirs[3]] * 4 if clip else dirs
if turn:
    views = [(sin(2 * pi * i / turn), -cos(2 * pi * i / turn), 0.35) for i in range(turn)]

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = max(ext.x**2 + ext.y**2, ext.z**2, 1e-6) ** 0.5 * 1.1
cam.data.clip_end = 1000
scene.collection.objects.link(cam)
scene.camera = cam
scene.world = bpy.data.worlds.new("world")
scene.world.color = (0.16, 0.16, 0.17)
r = scene.render
r.engine = "BLENDER_WORKBENCH"
r.resolution_x = r.resolution_y = size
r.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.display.render_aa = "8"
sh = scene.display.shading
sh.light, sh.color_type = "STUDIO", "TEXTURE"
for i, (d, f) in enumerate(zip(views, frames)):
    scene.frame_set(f)
    v = Vector(d).normalized()
    cam.location = center + v * (ext.length + 1)
    cam.rotation_euler = (-v).to_track_quat("-Z", "Y").to_euler()
    r.filepath = str(Path(j["out_dir"]) / f"look_{i}.png")
    bpy.ops.render.render(write_still=True)
    assert Path(r.filepath).is_file(), "render wrote nothing"
done(j, {"outputs": {"cells": [f"look_{i}.png" for i in range(len(views))]}, "frames": frames})
