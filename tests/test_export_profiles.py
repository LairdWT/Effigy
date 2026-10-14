"""M13 export profiles without Blender: print/obj via trimesh, LOD + collision naming per engine, the hull,
credits; M33's print split (its whole export with a real Blender, skipped without one). The gltfpack checks skip without the binary (EFFIGY_GLTFPACK / `python -m server.gltfpack_install`)."""

import io
import json
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pytest
import trimesh
from PIL import Image

from server.blender_install import blender_exe
from server.gltfpack_install import gltfpack_exe
from steps import export
from steps._print import split_solid

GLTFPACK = gltfpack_exe()


def parent_version(tmp_path, **meta) -> Path:
    """A textured 1280-triangle sphere, 1 m tall, base at y = 0 (library frame), as a version folder."""
    s = trimesh.creation.icosphere(subdivisions=3, radius=0.5)
    u = np.arctan2(s.vertices[:, 2], s.vertices[:, 0]) / (2 * np.pi) + 0.5
    s.apply_translation([0, 0.5, 0])
    texture = Image.new("RGB", (2048, 2048), (200, 120, 40))
    s.visual = trimesh.visual.TextureVisuals(
        uv=np.c_[u, s.vertices[:, 1]],
        material=trimesh.visual.material.PBRMaterial(baseColorTexture=texture),
    )
    parent = tmp_path / "020_bake"
    parent.mkdir()
    s.export(parent / "mesh.glb")
    base = {"asset_id": "crate", "version": "020_bake", "outputs": {"mesh": "mesh.glb"}}
    (parent / "meta.json").write_text(json.dumps(base | {"licenses": ["trimesh"]} | meta))
    return parent


def test_print_is_millimetres_z_up(tmp_path):
    res = export.run(
        "run", str(parent_version(tmp_path)), str(tmp_path / "o"), {"profile": "print"}
    )
    assert set(res["outputs"]) == {"crate.stl", "crate.3mf", "CREDITS.txt", "LICENSES.json"}
    for ext in ("stl", "3mf"):
        path = tmp_path / "o" / "print" / f"crate.{ext}"
        m = read_3mf(path) if ext == "3mf" else trimesh.load(path, force="mesh")
        assert len(m.faces) == 1280 and m.is_watertight, ext  # welded at the UV seam
        assert np.allclose(m.bounds[:, 2], [0, 1000], atol=1e-3), (ext, m.bounds)  # 1 m, Z up


def read_3mf(path) -> trimesh.Trimesh:
    """Our 3MF, read back with the stdlib: the package parts a slicer looks for, then the mesh."""
    z = zipfile.ZipFile(path)
    assert {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"} <= set(z.namelist())
    model = ET.fromstring(z.read("3D/3dmodel.model"))
    assert model.get("unit") == "millimeter"
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    v = [[float(e.get(k)) for k in "xyz"] for e in model.iterfind(".//m:vertex", ns)]
    f = [[int(e.get(k)) for k in ("v1", "v2", "v3")] for e in model.iterfind(".//m:triangle", ns)]
    return trimesh.Trimesh(v, f, process=False)


def test_obj_keeps_texture(tmp_path):
    export.run("run", str(parent_version(tmp_path)), str(tmp_path / "o"), {"profile": "obj"})
    out = tmp_path / "o" / "obj"
    assert "Kd 1.0" in (out / "crate.mtl").read_text()  # no grey tint over the texture
    m = trimesh.load(out / "crate.obj", force="mesh")
    assert m.visual.uv is not None and m.visual.material.image.size == (2048, 2048)


def test_engine_naming_and_hull(tmp_path, monkeypatch):
    """What each engine profile hands Blender: LODs as <name>_LOD<n>, the convex hull by convention."""
    parent, seen, last = parent_version(tmp_path), {}, {}

    def fake_blender(op, inputs, out, job):
        seen[out.name] = job["objects"]
        last[out.name] = trimesh.load(inputs[-1], force="mesh")  # the hull, where there is one
        return {"files": []}

    monkeypatch.setattr(export, "run_blender", fake_blender)
    monkeypatch.setattr(export, "gltfpack", lambda src, dst, *args: Path(shutil.copy(src, dst)))
    for profile in ("unity", "unreal", "godot", "web"):
        export.run("run", str(parent), str(tmp_path / profile), {"profile": profile})
    lods = [f"crate_LOD{i}" for i in range(4)]
    assert seen == {
        "unity": lods,  # Unity: a Mesh Collider (Convex) hulls the mesh itself
        "unreal": [*lods, "UCX_crate_00"],
        "godot": ["crate", "crate-convcolonly"],
        "web": ["crate"],
    }
    mesh = trimesh.load(parent / "mesh.glb", force="mesh")
    for hull in (last["unreal"], last["godot"]):
        assert hull.is_convex and hull.is_watertight
        # every mesh vertex on the inner side of every hull face
        d = mesh.vertices[:, None] - hull.triangles[:, 0]
        assert np.einsum("vfk,fk->vf", d, hull.face_normals).max() < 1e-6

    export.run("run", str(parent), str(tmp_path / "x"), {"profile": "unreal", "lods": False})
    assert seen["unreal"] == ["crate", "UCX_crate_00"]
    # a rigged model ships no hull: engines give characters their own physics, and Unreal 5.8 imported the
    # UCX_ hull beside a skeletal mesh as a stray static mesh (engine check 2026-10-11)
    (parent / "skeleton.json").write_text("{}", encoding="utf-8")
    for profile in ("unreal", "godot"):
        export.run(
            "run",
            str(parent),
            str(tmp_path / f"rigged_{profile}"),
            {"profile": profile, "lods": False},
        )
    assert seen["unreal"] == ["crate"] and seen["godot"] == ["crate"]  # keyed by the profile folder
    # unless asked: the export panel's tick (M32) ships it
    export.run(
        "run",
        str(parent),
        str(tmp_path / "asked"),
        {"profile": "unreal", "lods": False, "collision": True},
    )
    assert seen["unreal"] == ["crate", "UCX_crate_00"]

    flat = tmp_path / "flat"  # a sign or a plane: no volume, so no hull, but the export still ships
    flat.mkdir()
    trimesh.creation.box(extents=[1, 1, 0]).export(flat / "mesh.glb")
    (flat / "meta.json").write_text((parent / "meta.json").read_text())
    export.run("run", str(flat), str(tmp_path / "f"), {"profile": "godot"})
    assert seen["godot"] == ["crate"]


def parts_version(tmp_path, names=("Iron Helmet", "Body")) -> Path:
    """A parts version (M31): two named nodes, an "Iron Helmet" (a space in the name) and a Body, parts.json."""
    parent = tmp_path / "030_parts"
    parent.mkdir()
    scene = trimesh.Scene()
    for name, x in zip(names, (2.0, -2.0)):
        ball = trimesh.creation.icosphere(subdivisions=3, radius=0.5)
        ball.apply_translation([x, 0.5, 0])
        scene.add_geometry(ball, geom_name=name, node_name=name)
    scene.export(parent / "mesh.glb")
    (parent / "parts.json").write_text("{}")
    meta = {"asset_id": "crate", "version": "030_parts", "outputs": {"mesh": "mesh.glb"}}
    (parent / "meta.json").write_text(json.dumps(meta | {"licenses": ["trimesh"]}))
    return parent


def test_parts_keep_their_names_lods_and_hulls(tmp_path, monkeypatch):
    """M31b: each part of a parts version is its own object, with its own LODs and hull (print: M33, below)."""
    parent, seen, args = parts_version(tmp_path), {}, []

    def fake_blender(op, inputs, out, job):
        seen[out.name] = job["objects"]
        return {"files": []}

    def fake_gltfpack(src, dst, *a):
        args.append(a)
        return Path(shutil.copy(src, dst))

    monkeypatch.setattr(export, "run_blender", fake_blender)
    monkeypatch.setattr(export, "gltfpack", fake_gltfpack)
    for profile in ("unity", "unreal", "godot", "web"):
        export.run("run", str(parent), str(tmp_path / profile), {"profile": profile})
    lods = [f"{{}}_LOD{i}" for i in range(4)]
    assert {k: sorted(v) for k, v in seen.items()} == {  # the hulls in trimesh's node order
        "unity": lods,
        "unreal": ["UCX_Body_00", "UCX_Iron Helmet_00", *lods],
        "godot": ["Body-convcolonly", "Iron Helmet-convcolonly", "{}"],
        "web": ["{}"],
    }
    assert args and all("-kn" in a for a in args)  # gltfpack keeps the part nodes

    export.run("run", str(parent), str(tmp_path / "o"), {"profile": "obj"})
    obj = (tmp_path / "o" / "obj" / "crate.obj").read_text()
    assert "o Iron Helmet" in obj and "o Body" in obj


def test_credits_and_restricted(tmp_path):
    parent = parent_version(
        tmp_path, licenses=["three", "facebook/dinov3-vitl16-pretrain-lvd1689m"]
    )
    export.run("run", str(parent), str(tmp_path / "030_export"), {"profile": "print"})
    out = tmp_path / "030_export" / "print"
    assert (out / "CREDITS.txt").read_text() == "Built with DINOv3\n"
    assert len(json.loads((out / "LICENSES.json").read_text())["components"]) == 2
    meta = json.loads((parent / "meta.json").read_text())
    (parent / "meta.json").write_text(json.dumps(meta | {"restricted": True}))
    with pytest.raises(Exception, match="restricted"):
        export.run("run", str(parent), str(tmp_path / "040_export"), {"profile": "print"})


@pytest.mark.skipif(not GLTFPACK.is_file(), reason="no gltfpack")
def test_gltfpack_lods_and_web(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_GLTFPACK", str(GLTFPACK))
    src = parent_version(tmp_path) / "mesh.glb"
    faces = [1280]
    for lod in export.make_lods(src, tmp_path):
        m = trimesh.load(lod, force="mesh")
        faces.append(len(m.faces))
        assert m.visual.uv is not None and m.visual.material.baseColorTexture.size == (2048, 2048)
    assert faces == sorted(faces, reverse=True) and faces[-1] <= 0.15 * faces[0], faces

    glb = export.gltfpack(src, tmp_path / "web.glb", *export.WEB).read_bytes()
    n = int.from_bytes(glb[12:16], "little")
    gltf, blob = json.loads(glb[20 : 20 + n]), glb[28 + n :]
    assert {"EXT_meshopt_compression", "EXT_texture_webp"} <= set(gltf["extensionsRequired"])
    view = gltf["bufferViews"][gltf["images"][0]["bufferView"]]
    start = view.get("byteOffset", 0)
    image = Image.open(io.BytesIO(blob[start : start + view["byteLength"]]))
    assert image.format == "WEBP" and max(image.size) == 1024


BLENDER = blender_exe()


def halves() -> dict[str, trimesh.Trimesh]:
    """A 1 m box's skin cut in two open halves, left and right: neither is a solid on its own."""
    box = trimesh.creation.box(extents=[1, 1, 1]).subdivide().subdivide()
    left = box.triangles_center[:, 0] < 0
    return {"Left": box.submesh([left], append=True), "Right": box.submesh([~left], append=True)}


def test_the_volume_is_shared_between_the_parts():
    parts = halves()
    assert not any(m.is_watertight for m in parts.values())
    solids, hollow = split_solid(parts, 0.02)
    assert not hollow
    assert set(solids) == {"Left", "Right"}
    for name, m in solids.items():
        _, uses = np.unique(m.edges_sorted, axis=0, return_counts=True)
        assert (uses % 2 == 0).all(), name  # closed: every edge between an even number of faces
        # half the box each; the skin's voxels count in: half a voxel more on every side (4 % here)
        assert m.volume == pytest.approx(0.5, rel=0.15), name
        side = m.bounds[:, 0]
        assert (side[1] <= 0.05) if name == "Left" else (side[0] >= -0.05), (name, side)


def test_a_tiny_part_keeps_its_largest_piece_and_a_big_hole_is_reported():
    parts = halves()
    parts["Button"] = trimesh.creation.icosphere(radius=0.015).apply_translation([0, 0, 0.51])
    solids, _ = split_solid(parts, 0.02)
    assert "Button" in solids  # a few voxels, but its part
    box = trimesh.creation.box(extents=[1, 1, 1]).subdivide().subdivide()
    open_top = box.submesh([box.triangles_center[:, 1] < 0.49], append=True)  # a 1 m hole on top
    _, hollow = split_solid({"Box": open_top}, 0.02)
    assert hollow  # nothing to fill: the parts would be shells, and the export says so


def test_print_detail_is_bounded(tmp_path):
    parent = parts_version(tmp_path)
    with pytest.raises(Exception, match="print_detail"):
        export.run(
            "run", str(parent), str(tmp_path / "o"), {"profile": "print", "print_detail": 5000}
        )


@pytest.mark.skipif(not BLENDER.is_file(), reason="no Blender (EFFIGY_BLENDER / blender_install)")
def test_print_writes_a_solid_per_part(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_BLENDER", str(BLENDER))
    long = "Body with a very long name that Blender would cut at sixty-three bytes"
    parent = parts_version(tmp_path, ("Iron Helmet", long))
    res = export.run(
        "run", str(parent), str(tmp_path / "o"), {"profile": "print", "print_detail": 120}
    )
    out = tmp_path / "o" / "print"
    safe = "crate_Body_with_a_very_long_name_that_Blender_would_cut_at_sixty-three_bytes.stl"
    assert {"crate.stl", "crate.3mf", "crate_Iron_Helmet.stl", safe} <= set(res["outputs"])
    assert "note" not in res  # filled: no hollow shells
    ball = 4 / 3 * np.pi * 500**3  # mm³
    for f in ("crate_Iron_Helmet.stl", safe):
        m = trimesh.load(out / f, force="mesh")
        assert m.is_watertight and m.volume == pytest.approx(ball, rel=0.1), f
        assert m.bounds[0, 2] == pytest.approx(
            0, abs=15
        )  # millimetres, Z up, standing on the plate
    model = zipfile.ZipFile(out / "crate.3mf").read("3D/3dmodel.model").decode()
    assert sorted(re.findall(r'<object id="\d+" name="([^"]+)"', model)) == [long, "Iron Helmet"]
    assert model.count("<item ") == 2
