# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [an animation file made elsewhere: .fbx, .glb, .gltf, .bvh]; params: {"clip": which of the file's animations
(its name as reported; default the first), "name": the clip's name (default that animation's own), "taken": names in
use in the asset, "suffix": added to a name in use} → clip.glb + a report.

clip.glb is what a motion version holds (M26): the armature with the file's own bone names and that one animation,
renamed `name`, no mesh, so the retarget reads it like a Kimodo or a video clip (steps/import_motion, owner
2026-10-12). The report lists the file's animations (a generic take name such as Mixamo's "mixamo.com" becomes the
file's name), the bone names, and which skeleton they are (_maps.kind: mixamo, ue5, soma or None). A file without
an armature or an animation reports no clips; the step says so.
"""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _lib import IMPORT, done, job
from _maps import kind

j = job()
p = j["params"]
src = Path(j["in"][0])
bpy.ops.wm.read_factory_settings(use_empty=True)
if src.suffix.lower() == ".bvh":  # as bvh_clip: a BVH in centimetres, Y up
    bpy.ops.import_anim.bvh(
        filepath=str(src),
        global_scale=0.01,
        frame_start=1,
        use_fps_scale=False,
        update_scene_fps=True,
        update_scene_duration=True,
        rotate_mode="NATIVE",
        axis_forward="-Z",
        axis_up="Y",
    )
else:
    IMPORT[src.suffix.lower()](str(src))


def pose_slot(act):
    """The slot of `act` that keys pose bones (Blender 5's layered actions), or None (as import_model)."""
    for sl in act.slots:
        for ly in act.layers:
            for st in ly.strips:
                cb = st.channelbag(sl)
                if cb and any(fc.data_path.startswith("pose.bones") for fc in cb.fcurves):
                    return sl


def clip_name(raw: str) -> str:
    """A take's own name, or the file's for a generic one (as import_model)."""
    n = raw.rsplit("|", 1)[-1]
    return src.stem if n in ("", "mixamo.com", "Take 001", "Scene", "Layer0", "BaseLayer") else n


arms = sorted(
    (o for o in bpy.data.objects if o.type == "ARMATURE"), key=lambda o: -len(o.data.bones)
)
acts = [a for a in bpy.data.actions if pose_slot(a)]
names = []
for a in acts:  # one name each
    n, k = clip_name(a.name), 2
    base = n
    while n in names:
        n, k = f"{base} {k}", k + 1
    names.append(n)
want = p.get("clip")
if not arms or not acts:
    done(j, {"clips": [], "bones": [], "skeleton": None})
elif want and want not in names:
    done(j, {"clips": names, "bones": [], "skeleton": None, "missing": want})
else:
    arm = arms[0]
    i = names.index(want) if want else 0
    act = acts[i]
    mw = (
        arm.matrix_world.copy()
    )  # a parent (an FBX's empty) goes with the rest: keep where it put the armature
    arm.parent = None
    arm.matrix_world = mw
    for o in list(bpy.data.objects):
        if o is not arm:
            bpy.data.objects.remove(o, do_unlink=True)
    for a in list(bpy.data.actions):
        if a is not act:
            bpy.data.actions.remove(a)
    ad = arm.animation_data_create()
    for t in list(ad.nla_tracks):  # the glTF importer leaves a track per clip playing
        ad.nla_tracks.remove(t)
    ad.action, ad.action_slot = act, pose_slot(act)
    name = str(p.get("name") or names[i])[:48]
    if name in set(p.get("taken") or []):  # anim picks clips by name: one each in the asset
        name = f"{name} {p.get('suffix', '')}".strip()
    act.name = name
    sc = bpy.context.scene
    fps = sc.render.fps / sc.render.fps_base
    frames = int(act.frame_range[1] - act.frame_range[0]) + 1
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(
        filepath=str(Path(j["out_dir"], "clip.glb")),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_force_sampling=True,
        export_frame_range=False,
        export_apply=False,
    )
    bones = [b.name for b in arm.data.bones]
    done(
        j,
        {
            "clips": names,
            "picked": names[i],
            "name": name,
            "bones": bones,
            "skeleton": kind(bones),
            "frames": frames,
            "fps": round(fps, 3),
            "seconds": round(frames / fps, 2),
        },
    )
