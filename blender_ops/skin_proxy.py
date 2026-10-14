# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [mesh.glb, skeleton.json]; params: {"voxels": 120, "seed": 0, "parts": false} → rigged.glb + report.

Skin weights by Blender's bone heat on a proxy, transferred to the real mesh (IMPLEMENTATION.md M20):
bone heat fails on meshes with holes or several parts (most TRELLIS output), so a voxel remesh of the
mesh (closed, one piece) gets ARMATURE_AUTO and its weights move onto the mesh by DATA_TRANSFER
(nearest face, interpolated). Then at most 4 influences per vertex, normalized. The armature is built
from skeleton.json (library frame: glTF, Y up; Blender: x, -z, y): each bone from its joint to its
child (the middle finger for a hand, the neck for Spine2), a leaf continues its parent's direction.
The QA (weight sums, influences, test poses) is blender_ops/rig_qa.py, shared with the other engine.
A parts version (M32: one object per part) is skinned as one mesh, then split back into its parts, each
skinned on the same armature and named like the part.
"""

import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, kdtree

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, export_glb, import_meshes, job

TAIL = {
    "Hips": "Spine",
    "Spine2": "Neck",
    "LeftHand": "LeftHandMiddle1",
    "RightHand": "RightHandMiddle1",
}

j = job()
p = j["params"]
pieces = import_meshes(j["in"][0])
names = [o.name for o in pieces]
# a parts version (rig_skin passes parts.json's presence): the pieces come back out; any other model of
# several objects stays joined, as before M32 (the robot of separate pieces, a Blender pull)
parts = bool(p.get("parts")) and len(pieces) > 1
if parts:  # each face remembers its part through the join
    for i, o in enumerate(pieces):
        o.data.attributes.new("effigy_part", "INT", "FACE").data.foreach_set(
            "value", [i] * len(o.data.polygons)
        )
bpy.ops.object.select_all(action="DESELECT")
for o in pieces:
    o.select_set(True)
bpy.context.view_layer.objects.active = obj = pieces[0]
if len(pieces) > 1:
    bpy.ops.object.join()
    bpy.data.orphans_purge(
        do_recursive=True
    )  # the joined pieces' meshes, so the copies keep the names
skel = json.loads(Path(j["in"][1]).read_text(encoding="utf-8"))
joints = {x["name"]: x for x in skel["joints"]}
pos = {
    n: Vector((x["position"][0], -x["position"][2], x["position"][1])) for n, x in joints.items()
}
children = {}
for x in skel["joints"]:
    children.setdefault(x["parent"], []).append(x["name"])
height = obj.dimensions.z

# --- armature -----------------------------------------------------------------------------------
arm = bpy.data.objects.new("Armature", bpy.data.armatures.new("Armature"))
bpy.context.scene.collection.objects.link(arm)
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
for name, x in joints.items():
    b = eb.new(name)
    b.head = pos[name]
    kids = children.get(name, [])
    to = None if "tail" in x else TAIL.get(name) or (kids[0] if len(kids) == 1 else None)
    if (
        "tail" in x
    ):  # a creature's bone (M36): its template's direction, following the child it points at
        b.tail = (
            pos[x["to"]] if x.get("to") else Vector((x["tail"][0], -x["tail"][2], x["tail"][1]))
        )
    elif to:
        b.tail = pos[to]
    else:  # a leaf (head, finger tips, toes) or a fork: continue the parent's direction
        par = x["parent"]
        d = (pos[name] - pos[par]) if par else Vector((0, 0, 1))
        if name == "Head":
            d = Vector((0, 0, 1))
        b.tail = pos[name] + d.normalized() * max(0.03 * height, 0.3 * d.length)
    if (b.tail - b.head).length < 1e-4:
        b.tail = b.head + Vector((0, 0, 0.01 * height))
for name, x in joints.items():
    if x["parent"]:
        eb[name].parent = eb[x["parent"]]
    elif (
        "tail" in x
    ):  # a creature template's root (M36): on the ground, it moves the rest, deforms nothing
        eb[name].use_deform = False
bpy.ops.object.mode_set(mode="OBJECT")

# --- weights on a closed proxy, then onto the mesh ----------------------------------------------
for name in joints:
    if arm.data.bones[name].use_deform:
        obj.vertex_groups.new(name=name)


def heat(voxels):
    """Bone heat (ARMATURE_AUTO) on a closed voxel proxy of the mesh at this resolution, moved onto the
    mesh by DATA_TRANSFER (nearest face, interpolated); how many vertices got any weight."""
    proxy = obj.copy()
    proxy.data = obj.data.copy()
    bpy.context.scene.collection.objects.link(proxy)
    proxy.data.remesh_voxel_size = max(obj.dimensions) / voxels
    bpy.context.view_layer.objects.active = proxy
    bpy.ops.object.select_all(action="DESELECT")
    proxy.select_set(True)
    bpy.ops.object.voxel_remesh()
    proxy.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    dt = obj.modifiers.new("transfer", "DATA_TRANSFER")
    dt.object = proxy
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"
    dt.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=dt.name)
    bpy.data.objects.remove(proxy)
    return sum(1 for v in obj.data.vertices if any(g.weight > 1e-6 for g in v.groups))


# bone heat finds no solution at all on some proxies ("failed to find solution for one or more bones",
# every vertex left empty: 4 of 6 characters at 200 voxels in M20, the chef at 120 in M22, which the
# glTF exporter then wrote without a skin); a coarser proxy is one closed piece with fewer thin parts,
# so the next resolutions are tried before giving up
tried = []
for voxels in dict.fromkeys((int(p.get("voxels", 120)), 90, 60, 40)):
    tried.append((voxels, heat(voxels)))
    if tried[-1][1]:
        break
else:
    raise RuntimeError(
        f"bone heat found no solution at any proxy resolution (voxels, weighted): {tried}"
    )


# ponytail: parts are joined unwelded, so a held prop cut off as its own part never connects to the hand and
# loses the hand's weights (then filled from the nearest weighted vertex); make such a part rigid on the
# hand instead (M32)
# a hand or finger bone keeps weights only on mesh connected to it: from the vertices near its segment, outward along
# edges through vertices carrying its weight; the rest goes (§3.9 "no influence from a disconnected
# island"). Where a limb touches the body the proxy fuses them and bone heat spreads the limb over the
# body: the goblin's pinky over its coat. A held prop (the dwarf's hammer) is connected to the hand and
# keeps its weights. Only hands: for every bone it also cut legitimate weights on a model built from
# separate pieces (the robot's pose volume change 8 -> 54 %).
def seg_dist(q, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (q - a).dot(ab) / (ab.length_squared or 1e-12)))
    return (q - (a + ab * t)).length


bm = bmesh.new()
bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table()
nbr = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
bm.free()
bones = {
    b.name: (arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local)
    for b in arm.data.bones
}
dropped = 0
for g in [
    g for g in obj.vertex_groups if "Hand" in g.name
]:  # hands and fingers: what touches the body
    carry = {}
    for v in obj.data.vertices:
        for x in v.groups:
            if x.group == g.index and x.weight > 1e-4:
                carry[v.index] = v.co
    if not carry:
        continue
    head, tail = bones[g.name]
    near = max(0.6 * (tail - head).length, 0.03 * height)
    seen = [i for i, co in carry.items() if seg_dist(co, head, tail) <= near]
    if not seen:
        continue
    reach, stack = set(seen), list(seen)
    while stack:
        for k in nbr[stack.pop()]:
            if k in carry and k not in reach:
                reach.add(k)
                stack.append(k)
    off = [i for i in carry if i not in reach]
    if off:
        g.remove(off)
        dropped += len(off)
# arm and leg bones off the torso: a vertex more than twice as close to the spine as to the limb bone
# loses the limb's weight (the robot's chest centre was weighted fully to its left arm: 10x stretch)
# a creature (M36) names its torso and limbs in params (steps/_templates.py)
TORSO = [bones[n] for n in p.get("torso") or ("Hips", "Spine", "Spine1", "Spine2", "Neck")]
LIMBS = {
    obj.vertex_groups[n].index: bones[n]
    for n in bones
    if (
        n in p["limbs"]
        if "limbs" in p
        else any(n.endswith(x) for x in ("Arm", "ForeArm", "UpLeg", "Leg"))
    )
}
for v in obj.data.vertices:
    mine = [g for g in v.groups if g.group in LIMBS and g.weight > 1e-4]
    if not mine:
        continue
    torso = min(seg_dist(v.co, a, b) for a, b in TORSO)
    for g in mine:
        if seg_dist(v.co, *LIMBS[g.group]) > 2 * torso:
            obj.vertex_groups[g.group].remove([v.index])
            dropped += 1
bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
# vertices the proxy gave nothing (a piece whose proxy shell bone heat couldn't solve): the weights of
# the nearest weighted vertex
weighted = [v for v in obj.data.vertices if any(g.weight > 1e-6 for g in v.groups)]
filled = 0
if weighted and len(weighted) < len(obj.data.vertices):
    near = kdtree.KDTree(len(weighted))
    for i, v in enumerate(weighted):
        near.insert(v.co, i)
    near.balance()
    for v in obj.data.vertices:
        if not any(g.weight > 1e-6 for g in v.groups):
            src = weighted[near.find(v.co)[1]]
            for g in src.groups:
                obj.vertex_groups[g.group].add([v.index], g.weight, "REPLACE")
            filled += 1
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
obj.parent = arm
mod = obj.modifiers.new("Armature", "ARMATURE")
mod.object = arm

out = [obj]
if parts:  # the parts again: copies of the skinned mesh, each without the other parts' faces
    part = [0] * len(obj.data.polygons)
    obj.data.attributes["effigy_part"].data.foreach_get("value", part)
    obj.name = obj.data.name = "_joined"  # frees the first part's names for its copy
    out = []
    for i, name in enumerate(names):
        o = obj.copy()  # the parent, the Armature modifier and the vertex groups come along
        o.data = obj.data.copy()
        bm = bmesh.new()
        bm.from_mesh(o.data)  # the weights (deform layer), UVs and materials too
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if part[f.index] != i], context="FACES")
        bm.to_mesh(o.data)
        bm.free()
        o.data.attributes.remove(o.data.attributes["effigy_part"])
        o.name = o.data.name = name
        bpy.context.scene.collection.objects.link(o)
        out.append(o)
    bpy.data.objects.remove(obj)

bpy.ops.object.select_all(action="DESELECT")
for o in out:
    o.select_set(True)
arm.select_set(True)
export_glb(
    Path(j["out_dir"]) / "rigged.glb",
    use_selection=True,
    export_skins=True,
    export_animations=False,
)
report = {
    "engine": "blender_proxy",
    "vertices": sum(len(o.data.vertices) for o in out),
    "parts": len(out) if parts else 0,
    "bones": len(joints),
    "filled_from_nearest": filled,
    "proxy_voxels": tried[-1][0],
    "disconnected_weights_dropped": dropped,
}
done(j, {"outputs": {"rigged": "rigged.glb"}, "report": report})
