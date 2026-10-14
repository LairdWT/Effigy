"""M39 import_model: the step on hand-made upload versions. With Blender (skipped without, as test_blender_ops):
a still mesh keeps its mesh, the 52-joint template in a centimetre FBX with leaf bones keeps its rig and clip."""

import importlib.util
import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from server import library
from server.blender_install import blender_exe
from steps import _anim, _mesh, anim_edit, import_model
from steps._common import StepError

HERE = Path(__file__).parent / "fixtures"
BLENDER = blender_exe()
needs_blender = pytest.mark.skipif(
    not BLENDER.is_file(), reason="no Blender (EFFIGY_BLENDER / blender_install)"
)


@pytest.fixture
def lib(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path / "lib"))
    monkeypatch.setenv("EFFIGY_BLENDER", str(BLENDER))
    return library.create_asset("thing")["id"]


def upload(asset: str, src: Path) -> Path:
    """What the upload route makes: source/<file> and outputs {"model": …}."""
    d = library.new_version(asset, "upload")
    (d / "source").mkdir()
    shutil.copy(src, d / "source" / src.name)
    library.write_meta(d, None, {"name": src.name}, {"outputs": {"model": f"source/{src.name}"}})
    return d


def run(up: Path, tmp_path: Path, **params):
    out = tmp_path / "out"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    return import_model.run("run", str(up), str(out), params), out


def test_refusals(lib, tmp_path):
    up = upload(lib, HERE / "two_tris.glb")
    for bad in ({"scale": 0}, {"scale": 1001}, {"scale": "2"}, {"rig": 1}, {"turn": 90}):
        with pytest.raises(StepError) as e:
            run(up, tmp_path, **bad)
        assert e.value.code == "bad_params"
    gltf = tmp_path / "a.gltf"
    gltf.write_text(json.dumps({"asset": {"version": "2.0"}, "buffers": [{"uri": "a.bin"}]}))
    with pytest.raises(StepError) as e:
        run(upload(lib, gltf), tmp_path)
    assert e.value.code == "missing_input" and "a.bin" in str(e.value) and ".zip" in str(e.value)


def test_yaw_of_a_turned_template():
    """Joint heads moved by the lean and a quarter turn and stretched on the body's axes give that turn back."""
    heads = {b["name"]: np.array(b["head"]) for b in import_model._templates.bones("fox")}
    a = math.radians(125.3)
    r = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    joints = [
        {"name": n, "position": (r @ (h * [1.0, 1.0, 1.7])).tolist()} for n, h in heads.items()
    ]
    assert abs(import_model._yaw("fox", joints) - 125.3) < 1.0


@needs_blender
def test_unrigged_glb_is_still(lib, tmp_path):
    res, out = run(upload(lib, HERE / "anim.glb"), tmp_path)  # 3 bones: not a known skeleton
    m = res["metrics"]
    assert list(res["outputs"]) == ["mesh"] and (out / "mesh.glb").is_file()
    assert (
        m["skeleton"] is None and m["skeleton_note"].startswith("missing:") and m["triangles"] > 0
    )
    assert m["format"] == "glb" and m["clips"] == []


@needs_blender
def test_rig52_in_centimetres(lib, tmp_path):
    fbx = tmp_path / "rig52.fbx"
    subprocess.run(
        [
            BLENDER,
            "-b",
            "--factory-startup",
            "--python",
            str(HERE / "make_rig52.py"),
            "--",
            str(fbx),
        ],
        capture_output=True,
        check=True,
    )
    up = upload(lib, fbx)
    res, out = run(up, tmp_path)
    m = res["metrics"]
    assert list(res["outputs"]) == ["rigged_anim", "rigged", "skeleton", "clips", "qa"]
    assert m["skeleton"] == "mixamo52" and m["merged_bones"] == 13 and m["engine"] == "import"
    assert abs(m["height_m"] - 1.7) < 0.01 and m["clips"] == ["Wave"]
    # joints at the template's positions, re-centred (x, y centre of the box, its floor) and in glTF's frame
    spec = importlib.util.spec_from_file_location("make_rig52", HERE / "make_rig52.py")
    maker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(maker)
    want = {n: (x, z, -y) for n, (x, y, z) in maker.positions().items()}
    skel = json.loads((out / "skeleton.json").read_text(encoding="utf-8"))
    assert len(skel["joints"]) == 52
    for j in skel["joints"]:
        assert np.abs(np.array(j["position"]) - want[j["name"]]).max() < 1e-3, j["name"]
    clips = json.loads((out / "clips.json").read_text(encoding="utf-8"))
    assert clips["clips"] == [{"name": "Wave", "frames": 11, "seconds": 0.458}]
    doc, blob = _anim.read_glb(out / "rigged_anim.glb")
    s = _anim.sample_clip(doc, blob, "Wave", 24)
    q = next(b[_anim.ROT] for b in s["bones"] if b["name"] == "LeftArm")
    for f in range(12):  # the arm turned 0.05 rad a frame about one axis, whichever the bone's own
        ang = 2 * math.acos(min(1.0, abs(float(q[0] @ q[f]))))
        assert abs(ang - 0.05 * f) < 1e-3, (f, ang)
    # a layer that changes nothing bakes to the same clip
    done = tmp_path / "done"
    shutil.copytree(out, done)
    v = library.new_version(lib, "import_model")
    shutil.copytree(done, v, dirs_exist_ok=True)
    library.write_meta(v, up.name, {}, res)
    edit = tmp_path / "edit"
    edit.mkdir()
    e = anim_edit.run("run", str(v), str(edit), {"clips": {"Wave": {}}})
    assert e["metrics"]["base"] == v.name
    d1, b1 = _anim.read_glb(edit / "rigged_anim.glb")
    t = _anim.sample_clip(d1, b1, "Wave", 24)
    for a, b in zip(s["bones"], t["bones"]):
        assert (
            np.abs(
                a[_anim.ROT] * np.sign((a[_anim.ROT] * b[_anim.ROT]).sum(-1, keepdims=True))
                - b[_anim.ROT]
            ).max()
            < 1e-5
        )


CUTOUT = """
import math, sys
import bpy
out, wire = sys.argv[-2], sys.argv[-1] == "1"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_plane_add(size=1, rotation=(math.pi / 2, 0, 0))
img = bpy.data.images.new("leaf", 8, 8, alpha=True)
img.pixels.foreach_set([c for i in range(64) for c in (0.2, 0.6, 0.2, float(i % 2))])
img.filepath_raw, img.file_format = out[:-4] + ".png", "PNG"
img.save()
m = bpy.data.materials.new("leaf")
m.use_nodes = True
tex, bsdf = m.node_tree.nodes.new("ShaderNodeTexImage"), m.node_tree.nodes["Principled BSDF"]
tex.image = img
m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
if wire:
    m.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
bpy.context.object.data.materials.append(m)
bpy.ops.export_scene.fbx(filepath=out, path_mode="COPY", embed_textures=True)
"""


@needs_blender
def test_fbx_alpha_kept_only_when_the_file_means_it(lib, tmp_path):
    """Blender's FBX importer wires any 32-bit colour image's alpha; only a texture linked as transparency stays."""
    for wire, mode in ((True, "BLEND"), (False, "OPAQUE")):
        fbx = tmp_path / f"leaf{int(wire)}.fbx"
        subprocess.run(
            [
                BLENDER,
                "-b",
                "--factory-startup",
                "--python-expr",
                CUTOUT,
                "--",
                str(fbx),
                str(int(wire)),
            ],
            check=True,
            capture_output=True,
        )
        _, out = run(upload(lib, fbx), tmp_path)
        doc = json.loads(
            (out / "mesh.glb").read_bytes()[
                20 : 20 + int.from_bytes((out / "mesh.glb").read_bytes()[12:16], "little")
            ]
        )
        assert [m.get("alphaMode", "OPAQUE") for m in doc["materials"]] == [mode], wire


SHAPED = """
import sys
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
o = bpy.context.object
o.scale = (0.5, 0.5, 0.5)  # 1 m in the world, 2 m in its own data
o.shape_key_add(name="Basis")
o.shape_key_add(name="Smile").data[0].co.x += 0.1
bpy.ops.export_scene.gltf(filepath=sys.argv[-1])
"""


@needs_blender
def test_shape_keys_follow_the_scale(lib, tmp_path):
    """A mesh with shape keys evaluates from its key blocks: they take the world transform too."""
    glb = tmp_path / "shaped.glb"
    subprocess.run(
        [BLENDER, "-b", "--factory-startup", "--python-expr", SHAPED, "--", str(glb)],
        check=True,
        capture_output=True,
    )
    res, out = run(upload(lib, glb), tmp_path)
    v = _mesh.read_glb(out / "mesh.glb")[0]
    assert abs(res["metrics"]["height_m"] - 1) < 1e-3 and abs(np.ptp(v[:, 1]) - 1) < 1e-3


@needs_blender
def test_a_person_facing_away_is_turned_round(lib, tmp_path):
    fbx = tmp_path / "away.fbx"
    subprocess.run(
        [
            BLENDER,
            "-b",
            "--factory-startup",
            "--python",
            str(HERE / "make_rig52.py"),
            "--",
            str(fbx),
            "away",
        ],
        capture_output=True,
        check=True,
    )
    res, out = run(upload(lib, fbx), tmp_path)
    assert res["metrics"]["turned"] and res["metrics"]["skeleton"] == "mixamo52"
    j = {
        x["name"]: x["position"] for x in json.loads((out / "skeleton.json").read_text())["joints"]
    }
    assert j["LeftUpLeg"][0] > 0 > j["RightUpLeg"][0]  # its left on +X: facing +Z
    doc, blob = _anim.read_glb(out / "rigged_anim.glb")
    q = next(
        b[_anim.ROT]
        for b in _anim.sample_clip(doc, blob, "Wave", 24)["bones"]
        if b["name"] == "LeftArm"
    )
    assert (
        abs(2 * math.acos(min(1.0, abs(float(q[0] @ q[11])))) - 0.55) < 1e-3
    )  # the clip comes along
