"""M62: steps/bake.py on an imported model: the colour comes from the source's own materials (CPU: approximate
closest point; the GPU run uses cuBVH)."""

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")
trimesh = pytest.importorskip("trimesh")
from steps import _mesh, bake
from steps._common import StepError


def grid(x0, n=4):
    """A 1 m quad in the XY plane from x0, n×n cells, UVs spanning the quad (glTF)."""
    g = np.stack(np.meshgrid(np.linspace(0, 1, n + 1), np.linspace(0, 1, n + 1)), -1).reshape(-1, 2)
    idx = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
    a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]
    f = np.concatenate(
        [np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)]
    )
    v = np.c_[g[:, 0] + x0, g[:, 1], np.zeros(len(g))]
    return v, f, g * [1, -1] + [0, 1]  # v up in space = image up = glTF v down


def source_glb(path, textured=True):
    """Two quads: A (x 0..1) an 8×8 texture, left half red, right half green; B (x 1.5..2.5) factor-only linear 0.5."""
    mats = trimesh.visual.material.PBRMaterial
    tex = np.zeros((8, 8, 4), np.uint8)
    tex[:, :4], tex[:, 4:] = [255, 0, 0, 255], [0, 255, 0, 255]
    parts = []
    for x0, mat in (
        (0, mats(baseColorTexture=Image.fromarray(tex))),
        (1.5, mats(baseColorFactor=[0.5, 0.5, 0.5, 1])),
    ):
        v, f, uv = grid(x0)
        m = trimesh.Trimesh(v, f, process=False)
        m.visual = trimesh.visual.TextureVisuals(
            uv=uv * [1, -1] + [0, 1], material=mat
        )  # OpenGL UVs
        parts.append(m)
    scene = trimesh.Scene(
        parts if textured else [trimesh.Trimesh(p.vertices, p.faces, process=False) for p in parts]
    )
    scene.export(path, file_type="glb")


def version(root: Path, name, parent, outputs, **metrics):
    d = root / name
    d.mkdir()
    (d / "meta.json").write_text(
        json.dumps({"version": name, "parent": parent, "outputs": outputs, "metrics": metrics})
    )
    return d


def chain(root, textured=True):
    """010_upload (the source) → 020_transform (turned 90° about Y, ×2) → 030_uv (planar UVs on that mesh)."""
    up = version(root, "010_upload", None, {"mesh": "mesh.glb"})
    source_glb(up / "mesh.glb", textured)
    # what clean/transform record: x' = A x + b with A a quarter turn about Y times 2 (transform.run refuses
    # a source of two meshes, as this one is)
    t = np.eye(4)
    t[:3, :3] = 2 * np.array([[0.0, 0, 1], [0, 1, 0], [-1, 0, 0]])
    version(root, "020_transform", "010_upload", {}, transform=t.tolist())
    v, f, _ = _mesh.read_glb(up / "mesh.glb")
    v = v @ t[:3, :3].T + t[:3, 3]
    lo, hi = v.min(0), v.max(0)
    span = (hi - lo)[[2, 1]]  # planar projection along X (the turned quads face it)
    uv = np.c_[(v[:, 2] - lo[2]) / span[0], 1 - (v[:, 1] - lo[1]) / span[1]]
    uvd = version(root, "030_uv", "020_transform", {"mesh": "mesh.glb"})
    _mesh.write_glb(uvd / "mesh.glb", v, f, uv)
    return uvd, uv


def test_import_bakes_its_own_materials(tmp_path):
    uvd, _ = chain(tmp_path)
    out = tmp_path / "040_bake"
    out.mkdir()
    res = bake.run("run", str(uvd), str(out), {"texture_size": 256, "supersample": 1, "ao": False})
    m = res["metrics"]
    assert (
        m["source_from"] == "010_upload" and m["source_materials"] == 2 and "volume_from" not in m
    )
    assert np.allclose(m["normal_mean"], [127.5, 127.5, 255], atol=1.5)
    glb = trimesh.load(out / "mesh.glb", force="scene")
    assert len(glb.dump()) == 1  # one material in the output
    base = np.asarray(Image.open(out / "basecolor.png"))
    # the atlas is one planar projection: the quad at the lower z (A, red left/green right in its own u) first
    # then the grey one; compare by region instead of by texel: red, green and grey must all be present
    px = base[..., :3].reshape(-1, 3).astype(int)
    near = lambda c: (np.abs(px - c).max(1) <= 8).sum()
    assert near([255, 0, 0]) > 100 and near([0, 255, 0]) > 100 and near([188, 188, 188]) > 100
    assert (base[..., 3] == 255).all()


def test_red_is_on_the_side_it_was_painted(tmp_path):
    """UV orientation: each face of quad A takes red where the source's x < .5 and green where it is above."""
    uvd, uv = chain(tmp_path)
    out = tmp_path / "040_bake"
    out.mkdir()
    bake.run("run", str(uvd), str(out), {"texture_size": 256, "supersample": 1, "ao": False})
    base = np.asarray(Image.open(out / "basecolor.png"))[..., :3].astype(int)
    src_v, src_f, _ = _mesh.read_glb(tmp_path / "010_upload" / "mesh.glb")
    _, f, _ = _mesh.read_glb(uvd / "mesh.glb")
    for face in range(len(f) // 2):  # quad A's faces come first
        sx = src_v[src_f[face]][:, 0].mean()
        u, w = uv[f[face]].mean(0)
        r, g, _ = base[int(w * 256), int(u * 256)]
        assert (r > g) == (sx < 0.5), (face, sx, r, g)


def test_nothing_to_bake_from_and_overlapping_uvs(tmp_path):
    (tmp_path / "a").mkdir()
    uvd, _ = chain(tmp_path / "a", textured=False)
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(StepError) as e:
        bake.run("run", str(uvd), str(out), {"texture_size": 256, "supersample": 1})
    assert e.value.code == "missing_input" and "nothing to bake from" in str(e.value)
    # the input itself carries the textures but its UVs tile: run uv first
    d = tmp_path / "b"
    d.mkdir()
    own = version(d, "010_upload", None, {"mesh": "mesh.glb"})
    v, f, uv = grid(0)
    tiled = trimesh.Trimesh(v, f, process=False)
    tiled.visual = trimesh.visual.TextureVisuals(
        uv=uv * 3 * [1, -1] + [0, 1],
        material=trimesh.visual.material.PBRMaterial(
            baseColorTexture=Image.new("RGB", (8, 8), "red")
        ),
    )
    tiled.export(own / "mesh.glb")
    with pytest.raises(StepError) as e:
        bake.run("run", str(own), str(out), {"texture_size": 256, "supersample": 1})
    assert e.value.code == "missing_input" and "run uv first" in str(e.value)
