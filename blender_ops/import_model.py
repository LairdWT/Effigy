# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [model file]; params: {"scale": 1, "rig": true, "templates": {id: [[bone, parent], …]}} → mesh.glb (static)
or rigged.glb [+ rigged_anim.glb] + a report with the skeleton and the clips (IMPLEMENTATION.md M39).

An existing model from any file Blender reads, brought into the library frame (metres, the rest pose's base
centre at the origin). A skeleton the app knows (every bone of one of `templates` by name, `mixamorig:` and UE5
names mapped back, each bone's nearest present ancestor its template parent) is kept with its skin and its
clips: the extra bones' weights go to the nearest kept ancestor and they are deleted; anything else is a
still mesh. Blender trap: applying scale to an armature does not scale its location keys, so each clip is
recorded as world matrices (24 fps, scale and re-centring folded in), the rest pose is baked into metres, and
the clip is keyed again from the recorded matrices, parents first.
"""

import math
import re
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).parent))
from _lib import UE5, done, export_glb, job, load

j = job()
p = j["params"]
src = Path(j["in"][0])
scale, want_rig, templates = float(p.get("scale", 1)), p.get("rig", True), p.get("templates", {})
out = Path(j["out_dir"])
FPS = 24
bpy.ops.wm.read_factory_settings(use_empty=True)
gltf = src.suffix.lower() in (".glb", ".gltf")
new = load(str(src), merge=not gltf)  # a glTF keeps its vertices
bpy.context.view_layer.update()
scene = bpy.context.scene
src_fps = scene.render.fps / scene.render.fps_base

# what our own exports add beside the model: LODs below the first, collision hulls (Unreal UCX_, Godot -convcolonly)
EXTRA = re.compile(r"_LOD[1-9]\d*(\.\d+)?$|-convcolonly(\.\d+)?$|^U(CX|BX|CP|SP)_")
meshes = [o for o in new if o.type == "MESH" and not EXTRA.search(o.name)]
arms = [o for o in new if o.type == "ARMATURE"]
assert meshes, f"no mesh in {src.name}"


def skinned_by(arm):
    return [m for m in meshes if any(x.type == "ARMATURE" and x.object == arm for x in m.modifiers)]


# --- which skeleton -----------------------------------------------------------------------------------
note, tid, arm = "", None, None
deforming = [a for a in arms if skinned_by(a)]
if not want_rig:
    note = "rig: false"
elif not deforming:
    note = "no skeleton"
elif len(deforming) > 1:
    note = f"{len(deforming)} skeletons"
else:
    arm = deforming[0]
    bones = list(arm.data.bones)
    ue5 = (
        {v: k for k, v in UE5.items()} if {"pelvis", "spine_01"} <= {b.name for b in bones} else {}
    )  # not the shark: pelvis, head
    clean = {b.name: ue5.get(b.name.rsplit(":", 1)[-1], b.name.rsplit(":", 1)[-1]) for b in bones}
    by_clean = {c: n for n, c in clean.items()}
    if len(by_clean) < len(bones):
        note = "bone names repeat once cleaned"
    else:
        best = None
        for t, tb in templates.items():
            missing = [n for n, _ in tb if n not in by_clean]
            if best is None or len(missing) < len(best[1]):
                best = (t, missing)
            if not missing:
                keep = {by_clean[n] for n, _ in tb}

                def ancestor(n, keep=keep):
                    b = arm.data.bones[n].parent
                    while b and b.name not in keep:
                        b = b.parent
                    return clean[b.name] if b else None

                bad = next(
                    (
                        (n, ancestor(by_clean[n]), par)
                        for n, par in tb
                        if ancestor(by_clean[n]) != par
                    ),
                    None,
                )
                if bad:
                    note = f"{bad[0]} hangs from {bad[1]}, not {bad[2]}"
                else:
                    tid = t
                    break
        if not tid and not note:
            m = best[1]
            note = f"missing: {', '.join(m[:3])}{', …' if len(m) > 3 else ''} ({len(m)})"
dropped = []
if not tid:
    arm = None
else:  # a rig keeps what its armature deforms: a stray mesh would not move with the body (reported)
    dropped = sorted(o.name for o in meshes if o not in skinned_by(arm))
    meshes = skinned_by(arm)

# --- the world: scale, re-centring ---------------------------------------------------------------------
pts = []
for o in meshes:
    co = np.empty(len(o.data.vertices) * 3)
    o.data.vertices.foreach_get("co", co)
    pts.append(
        co.reshape(-1, 3) @ np.array(o.matrix_world.to_3x3()).T
        + np.array(o.matrix_world.translation)
    )
pts = np.concatenate(pts)
lo, hi = pts.min(0), pts.max(0)
height = float(hi[2] - lo[2]) * scale
# a person faces -Y here (+Z in the glTF): its left leg on the +X side; one facing away is turned round
turn = Matrix.Identity(4)
if tid == "mixamo52":
    legs = {
        clean[b.name]: (arm.matrix_world @ b.head_local).x
        for b in arm.data.bones
        if clean.get(b.name) in ("LeftUpLeg", "RightUpLeg")
    }
    if legs["LeftUpLeg"] < legs["RightUpLeg"]:
        turn = Matrix.Rotation(math.pi, 4, "Z")
W = (
    Matrix.Scale(scale, 4)
    @ turn
    @ Matrix.Translation(-Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])))
)
keep_objs = meshes + ([arm] if arm else [])
mws = {o: o.matrix_world.copy() for o in keep_objs}
for o in keep_objs:  # a dropped parent (an empty) keeps its transform on its children
    o.parent = None
    o.matrix_world = W @ mws[o]
for o in [o for o in bpy.data.objects if o not in keep_objs]:
    bpy.data.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()

# --- clips, recorded ----------------------------------------------------------------------------------------
template = dict(templates.get(tid, [])) if tid else {}
kept = [b.name for b in arm.data.bones if clean[b.name] in template] if tid else []
clips = []


def pose_slot(act):
    for sl in act.slots:
        for ly in act.layers:
            for st in ly.strips:
                cb = st.channelbag(sl)
                if cb and any(fc.data_path.startswith("pose.bones") for fc in cb.fcurves):
                    return sl


def reset_pose():
    for pb in arm.pose.bones:
        pb.location, pb.scale = (0, 0, 0), (1, 1, 1)
        pb.rotation_quaternion, pb.rotation_euler = (1, 0, 0, 0), (0, 0, 0)


def clip_name(raw):
    n = raw.rsplit("|", 1)[-1]
    n = src.stem if n in ("", "mixamo.com", "Take 001", "Scene", "Layer0", "BaseLayer") else n
    return re.sub(r"[^A-Za-z0-9_-]", "_", n)[:48]


if tid:
    ad = arm.animation_data_create()
    acts = [a for a in bpy.data.actions if pose_slot(a)]
    act_names = {a: a.name for a in acts}
    for i, a in enumerate(acts):
        a.use_fake_user, a.name = True, f"source_{i}"  # frees the names for the new actions
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    for m in meshes:
        m.hide_viewport = True  # the pose does not need the skin evaluated
    # recorded in the file's own space, W applied to the matrices: a clip may key the armature object itself (an
    # FBX bakes the object's transform into every take), which would undo W set on the object
    arm.matrix_world = mws[arm]
    used = set()
    for act in acts:
        f0, f1 = act.frame_range
        n = round((f1 - f0) / src_fps * FPS)
        if n < 1:
            continue
        ad.action, ad.action_slot = act, pose_slot(act)
        pos, quat = np.zeros((n + 1, len(kept), 3)), np.zeros((n + 1, len(kept), 4))
        for g in range(n + 1):
            f = f0 + g * src_fps / FPS
            scene.frame_set(math.floor(f), subframe=f - math.floor(f))
            for i, name in enumerate(kept):
                m = W @ arm.matrix_world @ arm.pose.bones[name].matrix
                pos[g, i] = m.translation
                quat[g, i] = m.to_3x3().normalized().to_quaternion()
        name, k = clip_name(act_names[act]), 2
        base = name
        while name in used:
            name, k = f"{base}_{k}", k + 1
        used.add(name)
        clips.append((name, pos, quat))
    # (acts keep their source frames only for the recording above)
    ad.action = None
    for m in meshes:
        m.hide_viewport = False
    reset_pose()
    arm.matrix_world = (
        W @ mws[arm]
    )  # the object's own channels as the last frame left them: the rest again

    # --- extra bones: their weights to the nearest kept ancestor, then deleted ---------------------------
    root = next(c for c, par in template.items() if par is None)
    keepset = set(kept)

    def above(n):  # the nearest kept ancestor
        b = arm.data.bones[n].parent
        while b and b.name not in keepset:
            b = b.parent
        return b.name if b else None

    extra = {
        b.name: above(b.name) or by_clean[root] for b in arm.data.bones if b.name not in keepset
    }
    merged = len(extra)
    for o in meshes:
        idx = {g.index: g.name for g in o.vertex_groups}
        moved = {i: extra[n] for i, n in idx.items() if n in extra}
        adds = {}
        for v in o.data.vertices:
            for g in v.groups:
                if g.group in moved:
                    d = adds.setdefault(moved[g.group], {})
                    d[v.index] = d.get(v.index, 0) + g.weight
        for tgt, d in adds.items():
            vg = o.vertex_groups.get(tgt) or o.vertex_groups.new(name=tgt)
            for vi, w in d.items():
                vg.add([vi], w, "ADD")
        for n in {idx[i] for i in moved}:
            o.vertex_groups.remove(o.vertex_groups[n])
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for b in eb:
        b.use_connect = False
    parents = {n: above(n) for n in kept}  # read before the first change
    for n in kept:
        eb[n].parent = eb[parents[n]] if parents[n] else None
    for n in extra:
        eb.remove(eb[n])
    bpy.ops.object.mode_set(mode="OBJECT")
    for n in kept:
        arm.data.bones[n].name = clean[n]
    for o in meshes:
        for g in o.vertex_groups:
            g.name = clean.get(g.name, g.name)
    # the rest pose in metres: transforms into the bones and the vertices
    arm.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
else:
    for o in meshes:
        o.vertex_groups.clear()
        for x in [x for x in o.modifiers if x.type == "ARMATURE"]:
            o.modifiers.remove(x)
        merged = 0
for o in meshes:
    if o.data.users > 1:
        o.data = o.data.copy()
    o.data.transform(o.matrix_world, shape_keys=True)  # a shaped mesh evaluates from its key blocks
    if o.matrix_world.is_negative:
        o.data.flip_normals()
    o.matrix_world = Matrix.Identity(4)

# --- the clips, keyed again from the world matrices ------------------------------------------------------------
if tid:
    order = sorted(kept, key=lambda n: len(arm.data.bones[clean[n]].parent_recursive))
    col = {n: i for i, n in enumerate(kept)}
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    report_clips, new_acts = [], []
    for name, pos, quat in clips:
        act = bpy.data.actions.new(name)
        slot = act.slots.new(id_type="OBJECT", name=name)
        ad.action, ad.action_slot = act, slot
        G = len(pos)
        loc, rot = {n: np.zeros((G, 3)) for n in order}, {n: np.zeros((G, 4)) for n in order}
        for g in range(G):
            world = {}
            for n in order:
                b, i = arm.data.bones[clean[n]], col[n]
                par = b.parent
                world[b.name] = Matrix.LocRotScale(Vector(pos[g, i]), Quaternion(quat[g, i]), None)
                up = (
                    {"parent_matrix": world[par.name], "parent_matrix_local": par.matrix_local}
                    if par
                    else {}
                )
                basis = b.convert_local_to_pose(world[b.name], b.matrix_local, invert=True, **up)
                q = basis.to_quaternion()
                if g and q.dot(Quaternion(rot[n][g - 1])) < 0:
                    q.negate()
                loc[n][g], rot[n][g] = basis.translation, q
        for n in order:
            pb = arm.pose.bones[clean[n]]
            moves = arm.data.bones[clean[n]].parent is None or np.abs(loc[n]).max() > 1e-5
            for g in range(G):
                pb.rotation_quaternion = tuple(rot[n][g])
                pb.keyframe_insert("rotation_quaternion", frame=g)
                if moves:
                    pb.location = tuple(loc[n][g])
                    pb.keyframe_insert("location", frame=g)
        ad.action = None
        act.use_fake_user = True
        new_acts.append(act)
        report_clips.append({"name": name, "frames": G - 1, "seconds": round((G - 1) / FPS, 3)})
    reset_pose()
    scene.render.fps, scene.render.fps_base = FPS, 1
    for c, act in zip(report_clips, new_acts):
        tr = ad.nla_tracks.new()
        tr.name = c["name"]
        tr.strips.new(c["name"], 0, act)

# --- facts, writes -------------------------------------------------------------------------------------------------
mats = {m for o in meshes for m in o.data.materials if m}
images, missing = {}, []
for m in mats:
    for nd in m.node_tree.nodes if m.node_tree else []:
        if nd.type == "TEX_IMAGE" and nd.image:
            im = nd.image
            images[im.filepath or im.name] = im
for key, im in images.items():
    if im.size[0] == 0 and not im.packed_file:
        missing.append(Path(key).name)


# an image's alpha wired to the material's: the glTF says BLEND, and a viewer draws the inside of a head through its
# face wherever a texel is transparent (our bakes leave some in the seams). Unwired when every pixel is opaque, and for
# an FBX whose materials link no texture as transparency: its importer wires any 32-bit colour image's alpha, whatever
# the file meant (its own note: "images may have alpha but be entirely opaque").
# ponytail: one answer for the whole file; per material when a file mixes cutouts and opaque guesses
def fbx_transparency(path):
    from io_scene_fbx import parse_fbx

    root, _ = parse_fbx.parse(str(path))
    conns = next((e for e in root.elems if e.id == b"Connections"), None)
    links = (
        c.props for c in (conns.elems if conns else []) if len(c.props) > 3 and c.props[0] == b"OP"
    )
    return any(p[3] in (b"TransparentColor", b"TransparencyFactor") for p in links)


guessed = src.suffix.lower() == ".fbx" and not fbx_transparency(src)
opaque = {}  # image name → every pixel opaque (read once: a 4K image is 270 MB of floats)


def is_opaque(im):
    if im.name not in opaque:
        px = np.empty(len(im.pixels), np.float32)
        im.pixels.foreach_get(px)
        opaque[im.name] = bool(px[3::4].min() >= 0.999)
    return opaque[im.name]


for m in mats:
    for lk in list(m.node_tree.links) if m.node_tree else []:
        im = getattr(lk.from_node, "image", None)
        wired = lk.to_node.type == "BSDF_PRINCIPLED" and lk.to_socket.name == "Alpha"
        if wired and im and im.size[0] and (guessed or is_opaque(im)):
            sock = lk.to_socket
            m.node_tree.links.remove(lk)
            sock.default_value = 1.0
tris = sum(len(o.data.loop_triangles) for o in meshes)
report = {
    "format": src.suffix.lower().lstrip("."),
    "height_m": round(height, 4),
    "triangles": tris,
    "meshes": len(meshes),
    "materials": len(mats),
    "textures": len(images) - len(missing),
    "missing_textures": sorted(missing),
    "skeleton": tid,
    "skeleton_note": "" if tid else note,
    "merged_bones": merged if tid else 0,
    "clips": [c["name"] for c in report_clips] if tid else [],
    "dropped_meshes": dropped,
    "turned": turn != Matrix.Identity(4),
}
if not 0.05 <= height <= 50 and height > 0:
    report["scale_hint"] = min(
        (0.001, 0.01, 0.0254, 100, 1000), key=lambda f: abs(math.log(height * f))
    )
if tid:
    report["clip_list"] = report_clips
    report["joints"] = [
        {
            "name": b.name,
            "parent": b.parent.name if b.parent else None,
            "position": [round(x, 5) for x in (b.head_local.x, b.head_local.z, -b.head_local.y)],
            "tail": [round(x, 5) for x in (b.tail_local.x, b.tail_local.z, -b.tail_local.y)],
        }
        for b in arm.data.bones
    ]

bpy.ops.object.select_all(action="DESELECT")
for o in meshes + ([arm] if arm else []):
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if tid:
    outputs = {}
    if clips:
        export_glb(out / "rigged_anim.glb", use_selection=True, export_animations=True)
        outputs["rigged_anim"] = "rigged_anim.glb"
    export_glb(out / "rigged.glb", use_selection=True, export_animations=False)
    outputs["rigged"] = "rigged.glb"
else:
    if len(meshes) > 1:
        bpy.ops.object.join()
    export_glb(out / "mesh.glb", use_selection=True, export_animations=False)
    outputs = {"mesh": "mesh.glb"}
done(j, {"outputs": outputs, "report": report})
