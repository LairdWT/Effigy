# SPDX-License-Identifier: GPL-3.0-or-later
# blender_ops/ runs inside Blender (bpy) and is GPL; the MIT backend only exchanges JSON files with it.
"""Shared helpers for `blender -b --python blender_ops/<op>.py -- <job.json>` (IMPLEMENTATION.md §3.6).

job.json = {"in": [paths], "out_dir": path, "params": {}}; every op ends with done(job, result).
"""

import json
import sys
from pathlib import Path

import bmesh
import bpy
from _maps import SOMA, SOURCES, UE5, kind, source_map  # noqa: F401  (bpy-free: tests import them)


def job() -> dict:
    return json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))


def done(job: dict, result: dict) -> None:
    Path(job["out_dir"], "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


IMPORT = {
    # merge_vertices: glTF splits vertices at UV/normal seams; Blender keeps UVs per corner, so merging
    # is lossless and gives true topology (boundary edges, manifoldness)
    ".glb": lambda p, merge=True: bpy.ops.import_scene.gltf(filepath=p, merge_vertices=merge),
    ".gltf": lambda p, merge=True: bpy.ops.import_scene.gltf(filepath=p, merge_vertices=merge),
    ".fbx": lambda p: bpy.ops.import_scene.fbx(filepath=p),
    ".obj": lambda p: bpy.ops.wm.obj_import(filepath=p),
    ".stl": lambda p: bpy.ops.wm.stl_import(filepath=p),
    ".ply": lambda p: bpy.ops.wm.ply_import(filepath=p),
}
for _e in (".usd", ".usda", ".usdc", ".usdz"):
    IMPORT[_e] = lambda p: bpy.ops.wm.usd_import(
        filepath=p, import_cameras=False, import_lights=False
    )


def load(path: str, merge: bool = True) -> list[bpy.types.Object]:
    """Import into the current scene; the new objects. merge=False (glTF only) keeps the file's vertices."""
    old = set(bpy.context.scene.objects)
    IMPORT[Path(path).suffix.lower()](str(path), *(() if merge else (False,)))
    # a rigged GLB: the importer parks a bone display shape in a "glTF_not_exported" collection, which
    # the glTF exporter skips but the FBX exporter would write as a mesh (M21: an Icosphere per LOD)
    for c in [c for c in bpy.data.collections if c.name.startswith("glTF_not_exported")]:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
    return [o for o in bpy.context.scene.objects if o not in old]


def import_meshes(path: str, new_scene: bool = True, merge: bool = True) -> list[bpy.types.Object]:
    """The file's mesh objects as they are (M31b: a parts version keeps one per part); empties the scene
    first if new_scene. merge=False (GLB only) keeps the file's vertices and its face order (M31:
    GeoSAM2's labels index it)."""
    if new_scene:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    meshes = [o for o in load(path, merge) if o.type == "MESH"]
    assert meshes, f"no mesh in {path}"
    return meshes


def import_mesh(path: str, new_scene: bool = True, merge: bool = True) -> bpy.types.Object:
    """The file's meshes joined into one active, selected object (import_meshes for the arguments)."""
    meshes = import_meshes(path, new_scene, merge)
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def export_glb(path: Path, **kw) -> None:
    """GLB; a rigged input's clips (one NLA track each, blender_ops/retarget) ride along."""
    kw.setdefault("export_animation_mode", "NLA_TRACKS")
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", **kw)


def mesh_report(obj: bpy.types.Object) -> dict:
    """Topology facts the ops assert on and validate_mesh reports."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    rep = {
        "vertices": len(bm.verts),
        "faces": len(bm.faces),
        "triangles": sum(len(f.verts) - 2 for f in bm.faces),
        "quads": sum(len(f.verts) == 4 for f in bm.faces),
        "non_manifold_edges": sum(not e.is_manifold and not e.is_boundary for e in bm.edges),
        "boundary_edges": sum(e.is_boundary for e in bm.edges),
        "zero_area_faces": sum(f.calc_area() < 1e-12 for f in bm.faces),
        "uv_layers": len(obj.data.uv_layers),
        "dimensions": [round(d, 4) for d in obj.dimensions],  # metres, Blender axes (Z up)
    }
    if bm.loops.layers.uv:
        uv = bm.loops.layers.uv.active
        coords = [loop[uv].uv for f in bm.faces for loop in f.loops]
        rep["uv_in_unit_square"] = all(0 <= c.x <= 1 and 0 <= c.y <= 1 for c in coords)
    bm.free()
    return rep
