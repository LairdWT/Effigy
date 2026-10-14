# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [mesh.glb, more meshes…]; params: {"name", "objects"?: one name per input,
"formats": [{"kind": fbx|glb|usdz, "preset"?}]} → files.

An input's meshes are joined into one object of its name; a name with "{}" keeps the input's objects
instead, each named by it with its own name (M31b: the parts of a parts version, "{}_LOD1" → Helmet_LOD1).
Objects named <base>_LOD<n> go under an FBX LOD group empty <base> (Unreal and Unity read it) and share
LOD0's materials. Other names are engine conventions chosen by steps/export.py (UCX_…, …-convcolonly).

A rigged input (M21): every LOD file carries its own copy of the skeleton, so the copies are merged into
one armature, and its bones are named for the engine: `mixamorig:` prefix for Unity (its Humanoid
mapper and Mixamo clips know it), UE5 Manny names for Unreal (its Mannequin retarget chains), the plain
Mixamo names for Godot's bone map (steps/_rig template names).
"""

import hashlib
import re
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from _lib import UE5, done, export_glb, import_mesh, import_meshes, job

FBX = {  # research 08 §4
    "unity": {"apply_scale_options": "FBX_SCALE_ALL", "bake_space_transform": True},
    "unreal": {"apply_scale_options": "FBX_SCALE_NONE"},
}
FBX_COMMON = {
    "axis_forward": "-Z",
    "axis_up": "Y",
    "add_leaf_bones": False,
    "use_armature_deform_only": True,
    "use_tspace": True,
    "mesh_smooth_type": "FACE",  # smoothing groups: Unreal warns without them
    "path_mode": "STRIP",  # textures as files next to the FBX: UE 5.8's Interchange can't read embedded ones
    "embed_textures": False,
}


BONES = {"unity": lambda n: f"mixamorig:{n}", "unreal": lambda n: UE5.get(n, n)}


def merge_armatures() -> "bpy.types.Object | None":
    """One skeleton for every skinned object: each imported file brought its own copy (same bones)."""
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if not arms:
        return None
    keep = arms[0]
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            continue
        for m in o.modifiers:
            if m.type == "ARMATURE" and m.object in arms[1:]:
                m.object = keep
        if o.parent in arms[1:]:
            world = o.matrix_world.copy()
            o.parent = keep
            o.matrix_world = world
    for a in arms[1:]:
        bpy.data.objects.remove(a, do_unlink=True)
    keep.name = "Armature"
    return keep


def texture_role(img) -> str:
    """basecolor / normal / orm by the shader input the image feeds (glTF import names them Image_N)."""
    for mat in bpy.data.materials:
        for node in mat.node_tree.nodes if mat.node_tree else []:
            if node.type == "TEX_IMAGE" and node.image == img:
                for link in node.outputs["Color"].links:
                    if link.to_socket.name == "Base Color":
                        return "basecolor"
                    if link.to_node.type == "NORMAL_MAP":
                        return "normal"
                return "orm"
    return bpy.path.clean_name(img.name)


j = job()
p = j["params"]
objs = []
for i, (f, name) in enumerate(zip(j["in"], p.get("objects", [p["name"]]), strict=True)):
    got = import_meshes(f, i == 0) if "{}" in name else [import_mesh(f, i == 0)]
    for o in got:
        want = name.replace("{}", o.name)
        o.name = o.data.name = want
        assert o.name == want, f"name clash: {want} became {o.name}"
    objs += got
armature = merge_armatures()
groups = {}
for o in objs:
    if m := re.fullmatch(r"(.+)_LOD\d+", o.name):
        groups.setdefault(m[1], []).append(o)
for base, lods in groups.items():
    group = bpy.data.objects.new(base, None)
    group["fbx_type"] = "LodGroup"  # the FBX exporter writes this empty as an FbxLODGroup
    bpy.context.scene.collection.objects.link(group)
    shared = lods[0].data.materials  # one material set, not a copy per LOD
    for o in lods:
        world = o.matrix_world.copy()
        o.parent = group
        o.matrix_world = world
        if len(o.data.materials) == len(shared):
            for i, m in enumerate(shared):
                o.data.materials[i] = m

out = Path(j["out_dir"])
files = []
for fmt in p["formats"]:
    kind, preset = fmt["kind"], fmt.get("preset")
    path = out / f"{p['name']}.{kind}"
    # bone renames carry the vertex groups along; a creature (M36, "humanoid": false) keeps its own names:
    # engines take it as a generic rig, with no humanoid mapper to feed
    if kind == "fbx" and armature and preset in BONES and p.get("humanoid", True):
        for b in armature.data.bones:
            b.name = BONES[preset](b.name)
    if kind == "fbx":
        bpy.data.orphans_purge(
            do_recursive=True
        )  # the LODs' own material copies (LOD0's are shared)
        taken, same = (
            {},
            {},
        )  # a second image in the same role (a hat's own base colour) gets its own
        for img in (
            bpy.data.images
        ):  # file: the name alone overwrote the first (audit 2026-10-10, PIPE-002)
            if img.packed_file:  # the GLB's textures are packed: write them next to the FBX
                digest = hashlib.sha1(img.packed_file.data).hexdigest()
                if (
                    digest in same
                ):  # the same picture twice (a bake's ORM, once as metal-rough, once as
                    img.filepath = same[digest]  # occlusion): one file
                    continue
                stem = f"{p['name']}_{texture_role(img)}"
                n = taken[stem] = taken.get(stem, 0) + 1
                tex = out / (f"{stem}.png" if n == 1 else f"{stem}_{n}.png")
                img.save(filepath=str(tex))
                img.filepath = same[digest] = str(tex)
                files.append(tex.name)
        bpy.ops.export_scene.fbx(filepath=str(path), **FBX_COMMON, **FBX[preset])
    elif kind == "glb":
        export_glb(path)
    elif kind == "usdz":
        bpy.ops.wm.usd_export(filepath=str(path))
    else:
        raise ValueError(f"unknown format {fmt}")
    assert path.is_file() and path.stat().st_size > 0, f"export wrote nothing: {path}"
    files.append(path.name)
done(j, {"files": files})
