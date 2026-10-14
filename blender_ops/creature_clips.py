# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [rigged.glb, <template>-animations.glb]; params: {"clips": ["Walk", …], "yaw": degrees} →
rigged_anim.glb (one NLA track per clip) + report, like retarget.py's.

A creature (IMPLEMENTATION.md M36): its skeleton is its template's (Mesh2Motion's fox, horse, bird, dragon, shark, kaiju, spider, snake), moved
onto the mesh, so the template's own clips play on it bone for bone. A bone's local axes differ from the
template's (the skinning points each bone at its child, with Blender's roll), so a clip moves our bone by
the template bone's turn from its rest pose in the world, not by its local rotation numbers. The root and
the hips also carry the clip's travel, scaled by the hips' height. Keys on every frame.
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, job

j = job()
p = j["params"]
wanted = list(p["clips"])
bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    if arm.animation_data:
        arm.animation_data.action = None
        for t in arm.animation_data.nla_tracks:
            t.mute = True
    return arm, new


ours, ours_objs = import_glb(j["in"][0])
src, src_objs = import_glb(j["in"][1])
for o in [o for o in src_objs if o.type == "MESH"]:  # the template's sample mesh
    bpy.data.objects.remove(o, do_unlink=True)
src_names = [o.name for o in bpy.data.objects if o.name not in {x.name for x in ours_objs}]
names = [b.name for b in ours.data.bones if b.name in src.data.bones]


def depth(b):
    return 0 if not b.parent else 1 + depth(b.parent)


order = sorted(names, key=lambda n: depth(ours.data.bones[n]))  # parents before children
travels = {
    b.name for b in ours.data.bones if not b.parent or not b.parent.parent
}  # the root and its child


def world_rest(arm, n):
    return arm.matrix_world @ arm.data.bones[n].matrix_local


hips = next(n for n in order if ours.data.bones[n].parent and not ours.data.bones[n].parent.parent)
# the hips' height above the skeleton's lowest joint (a floating shark's hips are high over its root)
low = lambda arm: min(world_rest(arm, b.name).translation.z for b in arm.data.bones)
body = lambda arm: max(world_rest(arm, b.name).translation.z for b in arm.data.bones) - low(arm)
# a flat creature (a snake on the floor) has its hips at its lowest joint: at least a quarter of its body's height
ours_h = max(world_rest(ours, hips).translation.z - low(ours), 0.25 * body(ours))
scale = ours_h / max(world_rest(src, hips).translation.z - low(src), 1e-6)
rest_src = {n: world_rest(src, n) for n in names}
rest_ours = {n: world_rest(ours, n) for n in names}
inv_world = ours.matrix_world.inverted()


# our creature faces its template's way turned by rig_fit's yaw (skeleton.json "yaw", degrees about glTF +Y,
# +Z towards +X; in Blender the same turn about +Z, the template's -Y front towards +X): the template's
# turns and travel are turned into our frame (not from the bones: an upright bird's hips-to-head is vertical)
align = Quaternion((0, 0, 1), math.radians(float(p.get("yaw", 0))))


def heading(
    arm, n
):  # a bone's direction seen from above, radians; a vertical bone has none: its parent's
    y = world_rest(arm, n).to_3x3().col[1]
    if math.hypot(y.x, y.y) < 0.1 * y.length and arm.data.bones[n].parent:
        return heading(arm, arm.data.bones[n].parent.name)
    return math.atan2(y.y, y.x)


# with "headings" (a snake lying curved, M41e) each bone by its own heading's difference from the template bone's: a
# lift turns about the bone's own sideways axis, not the head's (a lift far down a curved body went sideways)
aligns = {
    n: Quaternion((0, 0, 1), heading(ours, n) - heading(src, n)) if p.get("headings") else align
    for n in names
}


def transfer(frame):
    """Our pose at `frame`: each bone turned in the world as the template's bone turns from its rest."""
    bpy.context.scene.frame_set(frame)
    want = {}  # armature-space pose matrices of ours
    for n in order:
        cur = src.matrix_world @ src.pose.bones[n].matrix
        a = aligns[n]
        turn = a @ (cur.to_quaternion() @ rest_src[n].to_quaternion().inverted()) @ a.inverted()
        rot = turn @ rest_ours[n].to_quaternion()
        loc = rest_ours[n].translation.copy()
        if n in travels:
            loc += align @ ((cur.translation - rest_src[n].translation) * scale)
        else:  # the head stays where its parent's pose carries it
            par = ours.data.bones[n].parent.name
            rel = rest_ours[par].inverted() @ rest_ours[n]
            loc = (inv_world.inverted() @ want[par] @ rel).translation
        want[n] = inv_world @ Matrix.LocRotScale(loc, rot, None)
    for n in order:
        b = ours.data.bones[n]
        pb = ours.pose.bones[n]
        rest = b.matrix_local
        if b.parent:
            parent_pose = want[b.parent.name] @ b.parent.matrix_local.inverted()
            basis = (parent_pose @ rest).inverted() @ want[n]
        else:
            basis = rest.inverted() @ want[n]
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis = basis
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        if n in travels:
            pb.keyframe_insert("location", frame=frame)


if not any(bpy.data.actions.get(n) for n in wanted):
    raise SystemExit(f"none of {wanted} found in the template's clips")
src.animation_data_create()
baked, missing = [], list(wanted)
for name in wanted:
    act = bpy.data.actions.get(name)
    if not act:
        continue
    src.animation_data.action = act
    if act.slots:
        src.animation_data.action_slot = act.slots[0]
    f0, f1 = (int(x) for x in act.frame_range)
    new_act = bpy.data.actions.new(name)
    slot = new_act.slots.new(id_type="OBJECT", name=name)
    ours.animation_data_create()
    ours.animation_data.action = new_act
    ours.animation_data.action_slot = slot
    for f in range(f0, f1 + 1):
        transfer(f)
    ours.animation_data.action = None
    new_act.use_fake_user = True
    baked.append((name, new_act, f1 - f0))
    missing.remove(name)
src.animation_data.action = None
for n in src_names:
    if n in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)

for pb in ours.pose.bones:
    pb.matrix_basis = Matrix()
fps = bpy.context.scene.render.fps
for name, act, _ in baked:
    track = ours.animation_data.nla_tracks.new()
    track.name = name
    track.strips.new(name, int(act.frame_range[0]), act)
bpy.ops.object.select_all(action="DESELECT")
for o in ours_objs:
    o.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=str(Path(j["out_dir"]) / "rigged_anim.glb"),
    export_format="GLB",
    use_selection=True,
    export_animations=True,
    export_animation_mode="NLA_TRACKS",
    export_skins=True,
)
report = {
    "clips": [{"name": n, "frames": f, "seconds": round(f / fps, 3)} for n, _, f in baked],
    "fps": fps,
    "missing": missing,
    "height_scale": round(scale, 3),
}
done(j, {"outputs": {"rigged_anim": "rigged_anim.glb"}, "report": report})
