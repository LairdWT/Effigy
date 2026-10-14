# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [rigged.glb]; params: {"seed": 0} → report: the rig QA of IMPLEMENTATION.md §3.9 for any skinned GLB.

Weight sums, influences per vertex, unweighted vertices, left/right asymmetry (a vertex against its
mirror's weights with Left/Right swapped), and 10 random poses at ±10° per bone: volume change and the
largest stretch of an edge (edges under 0.5 % of the height left out: a raw mesh's micro-edges turn any
motion into a huge ratio). Both skinning engines (blender_ops/skin_proxy, the SkinTokens port) are
judged by this one op, so rig_skin can pick between them.
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Vector, kdtree

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, job

j = job()
p = j["params"]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(j["in"][0]), merge_vertices=True)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
assert meshes and arms, (
    f"need a skinned mesh and an armature, got {[(o.name, o.type) for o in bpy.context.scene.objects]}"
)
obj, arm = meshes[0], arms[0]
if len(meshes) > 1:  # a parts version (M32): judged as one model, the copy here joined
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
height = obj.dimensions.z if obj.dimensions.z > 1e-6 else max(obj.dimensions)

names = {g.index: g.name for g in obj.vertex_groups}
sums, counts = [], []
for v in obj.data.vertices:
    w = [g.weight for g in v.groups if g.weight > 1e-6]
    sums.append(sum(w))
    counts.append(len(w))
unweighted = sum(1 for s in sums if s < 1e-6)
off_sum = sum(1 for s in sums if s > 1e-6 and abs(s - 1) > 1e-3)

tree = kdtree.KDTree(len(obj.data.vertices))
for i, v in enumerate(obj.data.vertices):
    tree.insert(v.co, i)
tree.balance()


def wdict(v):
    return {names[g.group]: g.weight for g in v.groups}


# a creature (M36): its sides by suffix (Ear_L / Ear_R), mirrored across its own middle plane, across the
# template's left-right turned by rig_fit's yaw (glTF +Y is Blender +Z: x at 0°, y at 90°, the cat's 323.5°
# in between); a person across x = 0
sides = p.get("sides")
a = math.radians(float(p.get("yaw", 0))) if sides else 0.0
side = Vector((math.cos(a), math.sin(a), 0))
across = [v.co.dot(side) for v in obj.data.vertices]
mid = (min(across) + max(across)) / 2 if sides else 0.0


def swap(n):
    if sides:
        for a, b in (sides, sides[::-1]):
            if n.endswith(a):
                return n[: -len(a)] + b
        return n
    return (
        "Right" + n[4:] if n.startswith("Left") else "Left" + n[5:] if n.startswith("Right") else n
    )


def mirrored(co):
    return co - 2 * (co.dot(side) - mid) * side


diffs = []
# no paired bones (the snake, M41e): nothing to swap; a body curled in an S mirrors onto other parts of itself
paired = not sides or any(swap(n) != n for n in names.values())
for v in list(obj.data.vertices)[:: max(1, len(obj.data.vertices) // 2000)] if paired else []:
    if v.co.dot(side) - mid <= 0.01 * height:
        continue
    co, i, dist = tree.find(mirrored(v.co))
    if dist > 0.02 * height:
        continue
    a, b = wdict(v), {swap(n): w for n, w in wdict(obj.data.vertices[i]).items()}
    diffs.append(sum(abs(a.get(n, 0) - b.get(n, 0)) for n in set(a) | set(b)) / 2)
asymmetry = sum(diffs) / len(diffs) if diffs else None


def evaluated():
    dg = bpy.context.evaluated_depsgraph_get()
    m = obj.evaluated_get(dg).to_mesh()
    bm = bmesh.new()
    bm.from_mesh(m)
    vol = abs(bm.calc_volume())
    lens = [e.calc_length() for e in bm.edges]  # same order every time: the topology doesn't change
    bm.free()
    obj.evaluated_get(dg).to_mesh_clear()
    return vol, lens


vol0, len0 = evaluated()
rnd = random.Random(p.get("seed", 0))
vol_change, stretch = [], []
for _ in range(10):
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = Euler([rnd.uniform(-0.1745, 0.1745) for _ in range(3)])
    vol, lens = evaluated()
    vol_change.append(abs(vol - vol0) / vol0 * 100 if vol0 else 0)
    stretch.append(max(b / a for a, b in zip(len0, lens) if a > 0.005 * height))
for pb in arm.pose.bones:
    pb.rotation_euler = Euler((0, 0, 0))

report = {
    "vertices": len(sums),
    "bones": len(arm.data.bones),
    "unweighted_vertices": unweighted,
    "weight_sum_off": off_sum,
    "max_influences": max(counts) if counts else 0,
    "lr_asymmetry": round(asymmetry, 4) if asymmetry is not None else None,
    "pose_volume_change_pct_max": round(max(vol_change), 2),
    "pose_edge_stretch_max": round(max(stretch), 3),
}
done(j, {"report": report})
