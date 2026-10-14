# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [motion.bvh]; params: {"name": "310_motion", "fps": 30, "scale": 0.01} → clip.glb

A Kimodo BVH (SOMA 77-joint skeleton, centimetres, Y up, 30 fps) becomes a clip GLB like the pack's: an
armature with the SOMA bone names and one animation named `name`, in metres, Y up (the glTF exporter's
conversion from Blender's Z up). The retarget imports it like any pack GLB (M26).
"""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, job

j = job()
p = j["params"]
name = str(p.get("name", "clip"))
fps = int(p.get("fps", 30))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = fps
bpy.ops.import_anim.bvh(
    filepath=j["in"][0],
    global_scale=float(p.get("scale", 0.01)),
    frame_start=1,
    use_fps_scale=False,
    update_scene_fps=False,
    update_scene_duration=True,
    rotate_mode="NATIVE",
    axis_forward="-Z",
    axis_up="Y",
)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
arm.name = arm.data.name = "soma"
action = arm.animation_data.action
action.name = name
frames = int(action.frame_range[1] - action.frame_range[0]) + 1
out = str(Path(j["out_dir"], "clip.glb"))
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(
    filepath=out,
    export_format="GLB",
    use_selection=True,
    export_animations=True,
    export_force_sampling=True,
    export_frame_range=False,
    export_apply=False,
)
done(
    j,
    {
        "bones": len(arm.data.bones),
        "frames": frames,
        "fps": fps,
        "seconds": round(frames / fps, 2),
        "hips_height_m": round((arm.matrix_world @ arm.data.bones["Hips"].head_local).z, 3),
    },
)
