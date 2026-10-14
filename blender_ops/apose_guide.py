# SPDX-License-Identifier: GPL-3.0-or-later
"""The pose guide behind prompts/apose_ref.png (M16): a mannequin from primitives, arms 45° from the body,
rendered head-on. Z-Image can't be prompted into an A-pose (8/8 candidates: arms at 10-18°) and DWPose
can't read this stick figure's arms, so the shipped reference was made in two steps: a Z-Image mannequin
(seed 3100, cand_0; prompt "full body plain smooth light-grey artist mannequin, human proportions, standing
straight facing the camera, both arms held straight out diagonally downwards at 45 degrees ..., front view,
plain light-grey background") re-posed by FLUX.2-klein-4B with this render as image 2 (4 steps, seed 3; the
gate measured arms 43°/42°, elbows straight on all 4 seeds tried). Not a steps op: run by hand.

    blender -b --factory-startup --python blender_ops/apose_guide.py -- guide.png
"""

import math
import sys

import bpy
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]
ARM = math.radians(45)  # from the body: the gate's A-pose band is 30-60°
bpy.ops.wm.read_factory_settings(use_empty=True)
mat = bpy.data.materials.new("grey")
mat.diffuse_color = (0.55, 0.55, 0.55, 1)


def limb(a: Vector, b: Vector, r: float):
    """A capsule from a to b."""
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a + b) / 2, vertices=32)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    for p in (a, b):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=p, segments=32, ring_count=16)
        bpy.context.object.data.materials.append(mat)
    o.data.materials.append(mat)


def ball(c: Vector, r: Vector):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=c, segments=48, ring_count=24)
    o = bpy.context.object
    o.scale = r
    o.data.materials.append(mat)


# a 1.8 m figure, Z up, facing -Y (the camera)
ball(Vector((0, 0, 1.66)), Vector((0.10, 0.11, 0.13)))  # head
limb(Vector((0, 0, 1.47)), Vector((0, 0, 1.54)), 0.05)  # neck
ball(Vector((0, 0, 1.28)), Vector((0.19, 0.11, 0.22)))  # chest
ball(Vector((0, 0, 0.98)), Vector((0.17, 0.10, 0.15)))  # hips
for side in (-1, 1):
    sh = Vector((side * 0.21, 0, 1.42))
    down = Vector((side * math.sin(ARM), 0, -math.cos(ARM)))
    el = sh + down * 0.30
    wr = el + down * 0.27
    limb(sh, el, 0.045)
    limb(el, wr, 0.038)
    ball(wr + down * 0.08, Vector((0.035, 0.05, 0.08)))  # open hand
    hip = Vector((side * 0.10, 0, 0.92))
    knee = Vector((side * 0.14, 0, 0.50))
    ankle = Vector((side * 0.17, 0, 0.08))
    limb(hip, knee, 0.065)
    limb(knee, ankle, 0.05)
    ball(ankle + Vector((0, -0.06, -0.04)), Vector((0.05, 0.11, 0.04)))  # foot

scene = bpy.context.scene
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = 2.1
cam.location = (0, -6, 0.92)
cam.rotation_euler = (math.radians(90), 0, 0)
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.82, 0.82, 0.82)
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
