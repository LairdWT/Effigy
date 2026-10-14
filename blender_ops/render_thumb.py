# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [mesh.glb]; params: {"size": 512, "samples": 16} → thumb.png (Cycles on CPU: the GPU stays with ML)."""

import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, import_mesh, job

j = job()
p = j["params"]
obj = import_mesh(j["in"][0])
corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
center = sum(corners, Vector()) / 8
radius = max((c - center).length for c in corners) or 1
scene = bpy.context.scene
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
cam.location = center + Vector((1.2, -2.0, 1.0)).normalized() * radius * 3
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.rotation_euler = (0.8, 0.2, 0.6)
scene.collection.objects.link(sun)
scene.world = bpy.data.worlds.new("world")
scene.world.color = (0.25, 0.25, 0.27)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = p.get("samples", 16)
scene.render.resolution_x = scene.render.resolution_y = p.get("size", 512)
scene.render.filepath = str(Path(j["out_dir"]) / "thumb.png")
bpy.ops.render.render(write_still=True)
assert Path(scene.render.filepath).is_file(), "render wrote nothing"
done(j, {"outputs": {"thumb": "thumb.png"}, "device": "CPU"})
