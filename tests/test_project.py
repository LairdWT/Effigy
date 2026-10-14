"""project (M23/M24): the generated image onto a textured box in a fake chain; the head band; the colour
match modes; the upscale plumbing; the gates; the z-test; the params."""

import json
import math

import numpy as np
import pytest

torch = pytest.importorskip("torch")
trimesh = pytest.importorskip("trimesh")
from PIL import Image

from steps import project
from steps._bake import rasterize_uv, write_glb
from steps._common import StepError

FOV, HALF, ATLAS, IMG = 0.2, 0.25, 96, 256
GREY, RED = (120, 120, 120), (200, 30, 30)


def _box():
    """A cube of six separate quads, each on its own cell of a 3×2 UV grid (glTF UVs), outward normals.
    Returns vertices, faces, UVs, normals and per face (axis, sign) the UV of the cell's centre and of the
    points at t = -1 and t = +1 along the cell's second axis (for the +Z face: y = -HALF and y = +HALF)."""
    v, f, uv, n, cells = [], [], [], [], {}
    for k, (axis, sign) in enumerate([(2, 1), (2, -1), (0, 1), (0, -1), (1, 1), (1, -1)]):
        a, b = {0: (1, 2), 1: (2, 0), 2: (0, 1)}[axis]
        cu, cv = (k % 3) / 3, (k // 3) / 2
        base = len(v)
        for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = [0.0, 0.0, 0.0]
            p[axis], p[a], p[b] = sign * HALF, s * HALF, t * HALF
            v.append(p)
            uv.append([cu + (0.05 + 0.9 * (s + 1) / 2) / 3, cv + (0.05 + 0.9 * (t + 1) / 2) / 2])
            nn = [0.0, 0.0, 0.0]
            nn[axis] = sign
            n.append(nn)
        tri = [[base, base + 1, base + 2], [base, base + 2, base + 3]]
        f += tri if sign > 0 else [t[::-1] for t in tri]
        cells[(axis, sign)] = {
            "centre": (cu + 1 / 6, cv + 1 / 4),
            "t-": (cu + 1 / 6, cv + (0.05 + 0.08) / 2),
            "t+": (cu + 1 / 6, cv + (0.05 + 0.82) / 2),
        }
    return np.array(v), np.array(f), np.array(uv), np.array(n), cells


def _front_square():
    """Where the +Z face lands on the image under Pixal3D's camera (identity frame): (first, last) pixel."""
    t = math.tan(FOV / 2)
    d = 0.5 / t
    r = HALF / ((d - HALF) * 2 * t)
    return int((0.5 - r) * IMG), int((0.5 + r) * IMG)


def _chain(tmp_path, square, weights="faithful", gradient=False):
    prep, gen, bake = tmp_path / "010_prep", tmp_path / "020_trellis2", tmp_path / "030_bake"
    for d in (prep, gen, bake):
        d.mkdir()
    img = np.zeros((IMG, IMG, 4), np.uint8)
    lo, hi = square
    img[lo:hi, lo:hi] = RED + (255,)
    if gradient:  # red rising left to right: a colour with a mean and a contrast
        img[lo:hi, lo:hi, 0] = np.linspace(100, 255, hi - lo, dtype=np.uint8)[None, :]
    Image.fromarray(img).save(prep / "image.png")
    Image.fromarray(img[..., :3]).save(prep / "image_rgb.png")
    (prep / "meta.json").write_text(
        json.dumps(
            {
                "version": "010_prep",
                "step": "prep",
                "parent": None,
                "outputs": {"image": "image.png"},
            }
        )
    )
    (gen / "meta.json").write_text(
        json.dumps(
            {
                "version": "020_trellis2",
                "step": "trellis2",
                "parent": "010_prep",
                "outputs": {"mesh": "hi.glb", "ovoxel": "ovoxel.npz"},
                "frame": {"to_library_from_source": np.eye(4).tolist()},
                "metrics": {"fov": FOV, "weights": weights},
            }
        )
    )
    v, f, uv, n, cells = _box()
    rgba = np.full((ATLAS, ATLAS, 4), GREY + (255,), np.uint8)
    rng = np.random.default_rng(0)
    orm = rng.integers(0, 255, (ATLAS, ATLAS, 3), dtype=np.uint8)
    normal_map = rng.integers(0, 255, (ATLAS, ATLAS, 3), dtype=np.uint8)
    write_glb(bake / "mesh.glb", v, f, uv, rgba, orm, n, normal_map)
    (bake / "meta.json").write_text(
        json.dumps(
            {
                "version": "030_bake",
                "step": "bake",
                "parent": "020_trellis2",
                "outputs": {"mesh": "mesh.glb"},
            }
        )
    )
    return bake, cells, orm, normal_map


def _texel(path, uv):
    u, v = uv
    return np.asarray(Image.open(path).convert("RGB"))[int(v * ATLAS), int(u * ATLAS)].astype(int)


def _run(tmp_path, bake, params):
    out = tmp_path / "040_project"
    out.mkdir()
    return out, project.run("run", str(bake), str(out), params)


def _missing(dev=None):
    raise FileNotFoundError("texture group")


@pytest.fixture(autouse=True)
def _no_upscaler_weights(monkeypatch):
    """The tests never load Real-ESRGAN: the step takes the not-installed path unless a test fakes it."""
    monkeypatch.setattr(project._sr, "load", _missing)


def test_rasterize_uv_depth_keeps_the_near_triangle():
    uv = torch.tensor([[0.1, 0.1], [0.9, 0.1], [0.1, 0.9]] * 2)
    faces = torch.tensor([[0, 1, 2], [3, 4, 5]])
    for budget in (1 << 23, 50):  # one chunk, and many: the z-test must hold across chunks
        for near, depth in (
            (1, [2.0, 2.0, 2.0, 1.0, 1.0, 1.0]),
            (0, [1.0, 1.0, 1.0, 2.0, 2.0, 2.0]),
        ):
            face_id, _ = rasterize_uv(uv, faces, 32, budget=budget, depth=torch.tensor(depth))
            assert (face_id >= 0).sum() > 300 and (face_id[face_id >= 0] == near).all()


def test_the_front_face_takes_the_image_and_the_back_keeps_the_bake(tmp_path):
    bake, cells, orm, normal_map = _chain(tmp_path, _front_square())
    out, res = _run(tmp_path, bake, {"region": "front", "match": False})
    m = res["metrics"]
    assert (
        m["camera"] == "pixal3d"
        and m["iou"] > 0.9
        and 0.1 < m["changed"] < 0.25
        and "skipped" not in m
    )
    front, back = (
        _texel(out / "basecolor.png", cells[(2, 1)]["centre"]),
        _texel(out / "basecolor.png", cells[(2, -1)]["centre"]),
    )
    assert np.abs(front - RED).max() < 25 and np.abs(back - GREY).max() < 3
    assert (
        set(res["outputs"]) == {"mesh", "basecolor", "orm", "normal", "overlay"}
        and "models" not in res
    )
    # the other maps pass through untouched, in the files and in the GLB
    assert (np.asarray(Image.open(out / "orm.png")) == orm).all() and (
        np.asarray(Image.open(out / "normal.png")) == normal_map
    ).all()
    glb = trimesh.load(out / "mesh.glb", force="mesh", process=False)
    assert (
        len(glb.faces) == 12
        and (np.asarray(glb.visual.material.metallicRoughnessTexture.convert("RGB")) == orm).all()
    )
    assert m["upscaled"] is False and "without the 4× upscale" in res["note"]


def test_the_head_band_limits_the_image_to_the_rows_above_the_shoulders(tmp_path, monkeypatch):
    lo, hi = (
        _front_square()
    )  # the +Z face spans these image rows: y = +HALF at the top (lo), -HALF at the bottom
    bake, cells, *_ = _chain(tmp_path, (lo, hi))
    full, zero = lo + 0.3 * (hi - lo), lo + 0.6 * (hi - lo)
    monkeypatch.setattr(project, "head_band", lambda img, alpha: (full, zero, "pose"))
    out, res = _run(tmp_path, bake, {"match": False})  # region head, the default
    assert res["metrics"]["head_from"] == "pose" and res["metrics"]["band"] == [
        round(full),
        round(zero),
    ]
    assert res["models"] == [{"id": project._pose.MODEL}]
    top, bottom = (
        _texel(out / "basecolor.png", cells[(2, 1)]["t+"]),
        _texel(out / "basecolor.png", cells[(2, 1)]["t-"]),
    )
    assert np.abs(top - RED).max() < 25 and np.abs(bottom - GREY).max() < 3


def test_match_modes_and_strength(tmp_path):
    bake, cells, *_ = _chain(tmp_path, _front_square(), gradient=True)
    c = cells[(2, 1)]["centre"]
    out, res = _run(tmp_path, bake, {"region": "front", "match": "mean"})
    left, right = (
        _texel(out / "basecolor.png", (c[0] - 0.12, c[1])),
        _texel(out / "basecolor.png", (c[0] + 0.12, c[1])),
    )
    assert right[0] - left[0] > 60  # a mean shift keeps the image's gradient
    m = res["metrics"]["match"]
    assert (
        m["mode"] == "mean" and m["offset"][1] > 60 and m["offset"][2] > 60
    )  # green and blue lifted onto the grey bake
    (tmp_path / "l").mkdir()
    out, res = _run(tmp_path / "l", bake, {"region": "front"})  # the default: local
    left, right = (
        _texel(out / "basecolor.png", (c[0] - 0.12, c[1])),
        _texel(out / "basecolor.png", (c[0] + 0.12, c[1])),
    )
    assert right[0] - left[0] < 30  # the large-scale gradient is the bake's (flat) now
    assert (
        res["metrics"]["match"]["mode"] == "local"
        and np.abs(_texel(out / "basecolor.png", c) - GREY).max() < 40
    )
    (tmp_path / "s").mkdir()
    out, res = _run(tmp_path / "s", bake, {"region": "front", "match": False, "strength": 0.3})
    centre = _texel(out / "basecolor.png", c)
    assert (
        0.1 < res["metrics"]["changed"] < 0.25
    )  # what the image lands on does not shrink with the strength
    assert GREY[1] - 50 < centre[1] < GREY[1] - 10  # a 30 % blend towards the image's low green


def test_the_upscaled_image_is_what_gets_projected(tmp_path, monkeypatch):
    bake, cells, *_ = _chain(tmp_path, _front_square())
    monkeypatch.setattr(project._sr, "load", lambda dev=None: "net")
    calls = []

    def fake_upscale(net, rgb, **kw):
        calls.append(rgb.shape)
        return np.repeat(np.repeat(rgb, 4, 0), 4, 1)

    monkeypatch.setattr(project._sr, "upscale", fake_upscale)
    out, res = _run(tmp_path, bake, {"region": "front", "match": False})
    assert calls == [(IMG, IMG, 3)] and res["metrics"]["upscaled"] is True and "note" not in res
    assert {"id": project._sr.MODEL} in res["models"] and project._sr.MODEL in res["licenses"]
    assert np.abs(_texel(out / "basecolor.png", cells[(2, 1)]["centre"]) - RED).max() < 25


def test_a_mismatched_image_changes_nothing(tmp_path):
    bake, cells, *_ = _chain(tmp_path, (0, 90))  # the matte in a corner the mesh never covers
    out, res = _run(tmp_path, bake, {"region": "front"})
    assert res["metrics"]["iou"] < 0.5 and "skipped" in res["metrics"] and "note" in res
    assert np.abs(_texel(out / "basecolor.png", cells[(2, 1)]["centre"]) - GREY).max() < 3
    assert (out / "overlay.png").is_file()


def test_a_fast_model_has_no_aligned_camera_and_is_skipped(tmp_path):
    bake, cells, *_ = _chain(tmp_path, _front_square(), weights="fast")
    out, res = _run(tmp_path, bake, {"region": "front"})
    assert (
        res["metrics"]["camera"] is None
        and "no aligned camera" in res["metrics"]["skipped"]
        and "note" in res
    )
    assert np.abs(_texel(out / "basecolor.png", cells[(2, 1)]["centre"]) - GREY).max() < 3
    assert (out / "overlay.png").is_file()


@pytest.mark.parametrize(
    "params",
    [{"region": "ears"}, {"strength": 0}, {"strength": 1.5}, {"strength": "x"}, {"match": "x"}],
)
def test_bad_params(tmp_path, params):
    bake, *_ = _chain(tmp_path, _front_square())
    out = tmp_path / "040_project"
    out.mkdir()
    with pytest.raises(StepError) as e:
        project.run("run", str(bake), str(out), params)
    assert e.value.code == "bad_params"


def test_shading_offset_is_zero_for_a_matching_bake_and_follows_the_bake_when_it_differs():
    """A ramp texture on a quad seen head-on, and the same ramp as the image: no shift. The image ramp
    doubled: the shift brings it back down. A flipped uv lookup would show a large shift in the first case."""
    import torch.nn.functional as F

    size = 256
    uv = torch.tensor([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    faces = torch.tensor([[0, 1, 2], [0, 2, 3]])
    face_img, bary_img = rasterize_uv(uv, faces, size)  # the whole view is the quad, uv = pixel
    ramp = torch.linspace(0.2, 0.8, size)
    base = torch.zeros(size, size, 4)
    base[..., 1] = ramp[:, None]  # green rises down the atlas (v)
    base[..., 3] = 1
    pre = torch.zeros(1, 4, size, size)
    pre[0, 1] = ramp[:, None]  # the same ramp down the image rows
    pre[0, 3] = 1
    same = project.shading_offset(base * 255, uv, faces, face_img, bary_img, pre, sigma_px=16.0)
    assert same.abs().mean() < 3
    double = project.shading_offset(
        base * 255,
        uv,
        faces,
        face_img,
        bary_img,
        pre * torch.tensor([1, 2, 1, 1]).view(1, 4, 1, 1) / 1.0,
        sigma_px=16.0,
    )
    assert double[0, 1].mean() < -40 and double[0, 0].abs().mean() < 3
    assert F.interpolate(same, size=(8, 8)).shape == (1, 3, 8, 8)
