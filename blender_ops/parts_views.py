# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [mesh.glb]; params: {"max_faces"?} (more: only result.json with the count) → mesh.glb, color_XXXX.png, normal_XXXX.png (RGBA), depth_XXXX.exr, meta.json

GeoSAM2's twelve views (M31), in its conventions (docs/bench/m31.md): the mesh scaled so its longest
side is 1 and centred at the origin; a 50 mm lens on a 36 mm sensor at 50/36 × the bounding-box diagonal;
elevations 0/25/0/-25 and azimuths every 30° from 180°; colour and world-space normals ((n+1)/2) with a
transparent film; z-depth as a float32 EXR through Cycles at one sample (EEVEE's film is half float and
quantises depth to 1/1024, which GeoSAM2's 1e-3 depth test does not forgive), the background at 1e10;
meta.json with camera_angle_x, the camera-to-world matrices, the scale and the unscaled translation
(GeoSAM2 translates, then scales). The step turns the PNGs into the WEBPs GeoSAM2 reads.
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, export_glb, import_mesh, job

j = job()
out = Path(j["out_dir"])
RES, LENS, SENSOR = 1024, 50.0, 36.0
ELEV = [0, 25, 0, -25, 0, 25, 0, -25, 0, 25, 0, -25]
AZIM = [180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0]

# vertices unmerged, every mesh joined, its parents' transforms kept but the parents gone (the
# normalisation below moves parentless objects), written back out: the mesh.glb whose face order the
# labels follow (GeoSAM2 and blender_ops/parts_split both read this file)
obj = import_mesh(j["in"][0], merge=False)
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
if len(obj.data.polygons) > j["params"].get("max_faces", float("inf")):  # the step says: simplify
    done(j, {"faces": len(obj.data.polygons)})
    sys.exit(0)
for o in [o for o in bpy.data.objects if o != obj]:
    bpy.data.objects.remove(o, do_unlink=True)
export_glb(out / "mesh.glb", use_selection=True)
meshes = [obj]
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
scale = 1.0 / max(hi - lo)
centre = (lo + hi) / 2
root = bpy.data.objects.new("root", None)
bpy.context.scene.collection.objects.link(root)
obj.parent = root
root.scale = (scale, scale, scale)
root.location = -centre * scale
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
size = hi - lo
radius = LENS / SENSOR * math.sqrt(size.x**2 + size.y**2 + size.z**2)

sc = bpy.context.scene
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "PERSP"
cam.data.lens, cam.data.sensor_width = LENS, SENSOR
sc.collection.objects.link(cam)
sc.camera = cam


def override(kind):
    """An emission material for the depth and normal passes (the view layer's material override)."""
    m = bpy.data.materials.new(kind)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    if kind == "depth":
        cd = nt.nodes.new("ShaderNodeCameraData")
        nt.links.new(cd.outputs["View Z Depth"], em.inputs["Color"])
    else:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        mad = nt.nodes.new("ShaderNodeVectorMath")
        mad.operation = "MULTIPLY_ADD"
        mad.inputs[1].default_value = (0.5, 0.5, 0.5)
        mad.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(geo.outputs["Normal"], mad.inputs[0])
        nt.links.new(mad.outputs["Vector"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
    return m


def render(path, fmt, mode, engine, transparent):
    sc.render.engine = engine
    if engine == "CYCLES":
        sc.cycles.samples = 1
        sc.cycles.use_denoising = False
        sc.cycles.max_bounces = 0
        sc.cycles.device = "CPU"
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = fmt
    sc.render.image_settings.color_mode = mode
    sc.render.image_settings.color_depth = "32" if fmt == "OPEN_EXR" else "8"
    if fmt == "OPEN_EXR":
        sc.render.image_settings.exr_codec = "ZIP"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


depth_mat, normal_mat = override("depth"), override("normal")
transforms = []
for i, (e, a) in enumerate(zip(ELEV, AZIM)):
    e, a = math.radians(e), math.radians(a)
    loc = Vector(
        (
            radius * math.cos(e) * math.cos(a),
            radius * math.cos(e) * math.sin(a),
            radius * math.sin(e),
        )
    )
    cam.location = loc
    cam.rotation_euler = (-loc).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    transforms.append([list(r) for r in cam.matrix_world])
    bpy.context.view_layer.material_override = None
    bg.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    render(out / f"color_{i:04d}.png", "PNG", "RGBA", "BLENDER_EEVEE", True)
    bpy.context.view_layer.material_override = depth_mat
    bg.inputs["Color"].default_value = (1e10, 1e10, 1e10, 1.0)
    render(out / f"depth_{i:04d}.exr", "OPEN_EXR", "RGB", "CYCLES", False)
    bpy.context.view_layer.material_override = normal_mat
    bg.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    render(out / f"normal_{i:04d}.png", "PNG", "RGBA", "BLENDER_EEVEE", True)

meta = {
    "camera_angle_x": 2.0 * math.atan(SENSOR / 2 / LENS),
    "camera_lens": LENS,
    "sensor_width": SENSOR,
    "env_texture": "null",
    "bbox_size": list(size),
    "scaling_factor": scale,
    "translation": list(-centre),
    "transforms": transforms,
}
(out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
done(
    j,
    {
        "views": 12,
        "scale": round(scale, 5),
        "radius": round(radius, 4),
        "faces": sum(len(o.data.polygons) for o in meshes),
    },
)
