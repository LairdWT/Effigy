# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [mesh.glb]; params: {"size": 1024, "view": "front"|"back"} → front.png (RGBA, its textures if any) + camera.json.

Orthographic, looking at the glTF front (+Z) along -Z, Workbench (fast, flat studio light: what a pose
detector needs). camera.json maps pixels back to the glTF frame: x = cx + (u / size - 0.5) * scale,
y = cy - (v / size - 0.5) * scale (u right, v down); "back" looks along +Z from behind, x mirrored
(x = cx - ...).
"""

import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, import_mesh, job

j = job()
p = j["params"]
size = int(p.get("size", 1024))
obj = import_mesh(j["in"][0])
pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
lo = Vector([min(q[i] for q in pts) for i in range(3)])
hi = Vector([max(q[i] for q in pts) for i in range(3)])
center = (lo + hi) / 2
scale = max(hi.x - lo.x, hi.z - lo.z) * 1.1  # Blender Z = glTF Y (up)
sc = bpy.context.scene
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
cam.data.type, cam.data.ortho_scale = "ORTHO", scale
cam.data.clip_end = (hi - lo).length * 4
back = p.get("view") == "back"
reach = (hi - lo).length
# glTF +Z (front) is Blender -Y: look along +Y from the front, or along -Y from behind; up +Z
cam.location = (center.x, hi.y + reach if back else lo.y - reach, center.z)
cam.rotation_euler = (1.5707963, 0, 3.14159265 if back else 0)
sc.camera = cam
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE" if bpy.data.images else "MATERIAL"
sc.render.resolution_x = sc.render.resolution_y = size
sc.render.film_transparent = True
sc.render.image_settings.color_mode = "RGBA"
sc.render.filepath = str(Path(j["out_dir"]) / "front.png")
bpy.ops.render.render(write_still=True)
camera = {"cx": center.x, "cy": center.z, "scale": scale, "size": size, "facing": -1 if back else 1}
done(j, {"outputs": {"front": "front.png"}, "camera": camera})
