"""The transform step (agent finding 11, 2026-10-13): a still model stood up, turned, scaled and placed without
Blender; its UVs, materials and textures as they were, and the 4×4 bake follows recorded."""

import json

import numpy as np
import pytest
import trimesh
from PIL import Image

from steps import _glb, transform
from steps._common import StepError


def _version(d, mesh: trimesh.Trimesh | trimesh.Scene, extra: dict | None = None):
    d.mkdir()
    mesh.export(d / "mesh.glb", include_normals=True)
    Image.new("RGB", (4, 4), (200, 100, 50)).save(d / "basecolor.png")
    outputs = {"mesh": "mesh.glb", "basecolor": "basecolor.png", **(extra or {})}
    (d / "meta.json").write_text(
        json.dumps({"version": d.name, "step": "bake", "parent": None, "outputs": outputs})
    )
    return d


def _textured_box(extents=(0.4, 1.0, 0.2)):
    box = trimesh.creation.box(extents=extents)
    box.apply_translation((0, extents[1] / 2, 0))
    uv = np.random.default_rng(0).random((len(box.vertices), 2))
    box.visual = trimesh.visual.TextureVisuals(uv=uv, image=Image.new("RGB", (4, 4), (10, 20, 30)))
    return box


def _attr(path, key):
    doc, blob = _glb.read(path)
    return _glb.accessor(doc, blob, doc["meshes"][0]["primitives"][0]["attributes"][key]).copy()


def test_a_still_model_is_turned_scaled_and_placed_as_its_transform_says(tmp_path):
    src = _version(tmp_path / "010_bake", _textured_box(), {"ovoxel": "ovoxel.npz"})
    out = tmp_path / "020_transform"
    out.mkdir()
    params = {"rotate_deg": [0, 90, 0], "height_m": 2.0, "translate_m": [1, 0, 0]}
    res = transform.run("run", str(src), str(out), params)
    assert set(res["outputs"]) == {"mesh", "basecolor"}  # the pictures copied, never a volume
    before, after = _attr(src / "mesh.glb", "POSITION"), _attr(out / "mesh.glb", "POSITION")
    t = np.asarray(res["metrics"]["transform"])
    assert np.allclose(
        before @ t[:3, :3].T + t[:3, 3], after, atol=1e-5
    )  # x' = A x + b, as bake composes it
    assert np.allclose(
        np.ptp(after, 0), [0.4, 2.0, 0.8], atol=1e-4
    )  # turned 90° about Y, scaled 2×
    assert np.isclose(after[:, 1].min(), 0) and np.allclose(
        (after.min(0) + after.max(0))[[0, 2]] / 2, [1, 0]
    )
    assert np.allclose(np.linalg.norm(_attr(out / "mesh.glb", "NORMAL"), axis=1), 1, atol=1e-5)
    assert np.array_equal(
        _attr(src / "mesh.glb", "TEXCOORD_0"), _attr(out / "mesh.glb", "TEXCOORD_0")
    )
    assert (out / "basecolor.png").read_bytes() == (src / "basecolor.png").read_bytes()
    assert res["metrics"]["dropped"] == ["ovoxel.npz"]  # left out, named


def test_level_stands_a_tilted_model_upright(tmp_path):
    box = _textured_box()
    box.apply_transform(trimesh.transformations.rotation_matrix(np.radians(12), [1, 0, 0]))
    src = _version(tmp_path / "010_bake", box)
    out = tmp_path / "020_transform"
    out.mkdir()
    res = transform.run("run", str(src), str(out), {"level": True})
    assert res["metrics"]["levelled"] and np.allclose(
        sorted(res["metrics"]["size_m"]), [0.2, 0.4, 1.0], atol=0.01
    )


def test_what_it_refuses(tmp_path):
    fitted = _version(tmp_path / "005_rig_fit", _textured_box(), {"skeleton": "skeleton.json"})
    with pytest.raises(StepError) as e:  # its joints would no longer fit the moved mesh
        transform.run("run", str(fitted), str(tmp_path), {"rotate_deg": [0, 90, 0]})
    assert e.value.code == "bad_params" and "skeleton" in str(e.value)
    two = trimesh.Scene([_textured_box(), _textured_box((0.1, 0.1, 0.1))])
    src = _version(tmp_path / "010_bake", two)
    out = tmp_path / "020_transform"
    out.mkdir()
    with pytest.raises(StepError) as e:  # not a single still mesh: Blender's job
        transform.run("run", str(src), str(out), {"rotate_deg": [0, 90, 0]})
    assert e.value.code == "bad_params" and "use Blender" in str(e.value)
    for bad in (
        {"rotate_deg": [0, 90]},
        {"scale": -1},
        {"scale": 2, "height_m": 1},
        {"level": "yes"},
    ):
        with pytest.raises(StepError) as e:
            transform.run("run", str(src), str(out), bad)
        assert e.value.code == "bad_params", bad


def test_a_scale_per_axis_fits_a_brief(tmp_path):
    """Agent finding 18: the hoarding needed x × 0.77, the block 0.96 / 0.97 / 1.10: `scale: [x, y, z]` after the
    turn; the normals take the inverse scale and stay unit length."""
    src = _version(tmp_path / "010_bake", _textured_box())
    out = tmp_path / "020_transform"
    out.mkdir()
    res = transform.run("run", str(src), str(out), {"scale": [0.5, 2.0, 1.0]})
    before, after = _attr(src / "mesh.glb", "POSITION"), _attr(out / "mesh.glb", "POSITION")
    t = np.asarray(res["metrics"]["transform"])
    assert np.allclose(before @ t[:3, :3].T + t[:3, 3], after, atol=1e-5)
    assert np.allclose(np.ptp(after, 0), [0.2, 2.0, 0.2], atol=1e-4) and res["metrics"][
        "scale"
    ] == [0.5, 2.0, 1.0]
    n = _attr(out / "mesh.glb", "NORMAL")
    assert np.allclose(np.linalg.norm(n, axis=1), 1, atol=1e-5)


def test_square_and_face_turn_the_front_where_it_is_asked(tmp_path):
    """Agent finding 22: `square` turns the plan square to the axes by the smallest turn (the bench came out 18°
    off), `face` the front (the side the camera saw, +Z) to a named axis (the bench's seat to -Z, the street side)."""
    box = _textured_box((1.2, 0.5, 0.4))  # long on X, its front on +Z; 0.5 deep with the mark
    bump = trimesh.creation.box(extents=(0.2, 0.2, 0.1))
    bump.apply_translation((0, 0.25, 0.25))  # a mark on the front
    model = trimesh.util.concatenate([box, bump])
    model.apply_transform(trimesh.transformations.rotation_matrix(np.radians(20), [0, 1, 0]))
    src = _version(tmp_path / "010_bake", model)
    for face, axis, sign in (("+z", 2, 1), ("-z", 2, -1), ("+x", 0, 1), ("-x", 0, -1)):
        out = tmp_path / f"020_{face}"
        out.mkdir()
        transform.run("run", str(src), str(out), {"square": True, "face": face})
        p = _attr(out / "mesh.glb", "POSITION")
        long_ = 0 if axis == 2 else 2  # the long side lies across the way it faces
        assert np.isclose(np.ptp(p[:, long_]), 1.2, atol=0.01) and np.isclose(
            np.ptp(p[:, axis]), 0.5, atol=0.01
        ), face
        mid = (p[:, long_].min() + p[:, long_].max()) / 2
        mark = p[np.abs(p[:, long_] - mid) < 0.11]  # the bump: the box has corners only at its ends
        assert sign * (mark[:, axis].mean() - (p[:, axis].min() + p[:, axis].max()) / 2) > 0.1, face
    with pytest.raises(StepError):
        transform.run("run", str(src), str(tmp_path), {"face": "up"})
