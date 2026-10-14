"""refine (M43b): view planning, the back-projection weights, the weight⁴ paint, the colour match, the face
mask, a whole run with the generator faked (identity), the params; the real model only with
EFFIGY_GPU_TESTS=1, CUDA and the Tile weights installed (it loads ~20 GB and fills the card)."""

import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
trimesh = pytest.importorskip("trimesh")
from PIL import Image

from steps import refine
from steps._bake import heal_seams, rasterize_uv, seams, write_glb
from steps._common import StepError
from steps._views import ortho, render, texel_weights
from tests.test_project import _box

ATLAS = 96


def test_views_are_planned_from_the_texel_density():
    v, f, uv, _, _ = _box()
    v = v * [1, 4, 1] + [0, 1, 0]  # 0.5 × 2 × 0.5 m, standing on the ground
    size = 2048
    # UV cells cover 6 × 0.3 × 0.45 of the atlas; 3D area 4 × (0.5 × 2) + 2 × 0.25 m²
    d = size * math.sqrt(6 * 0.3 * 0.45 / 4.5)
    assert refine.texel_density(v, f, uv, size) == pytest.approx(d, rel=1e-3)
    e = 1024 / (1.25 * d)  # 0.94 m windows
    n = math.ceil((2 - e) / (0.75 * e)) + 1
    views = refine.plan_views(v, f, uv, size)
    assert n == 3 and len(views) == 8 * n + 1
    assert [w["yaw"] for w in views[: n + 1]] == [0] * (n + 1) and views[n]["pitch"] == -60
    assert {w["yaw"] for w in views[-n:]} == {180}  # the back last
    tops = sorted({round(w["center"][1], 3) for w in views if w["pitch"] == 0})
    assert tops == pytest.approx([e / 2, 1.0, 2 - e / 2], abs=1e-3)
    assert all(w["extent"] >= e - 1e-9 for w in views)


def test_a_wide_window_is_widened_to_fit():
    v, f, uv, _, _ = _box()
    v = v * [8, 1, 1]  # 4 m wide, 0.5 m tall: wider than one window at this density
    views = refine.plan_views(v, f, uv, 256)
    front = views[0]
    pix, _ = ortho(0, 0, front["center"], front["extent"])["project"](v)
    assert pix.min() >= 0 and pix.max() <= 1
    assert not any(
        w["pitch"] for w in views
    )  # wider than tall: no view from above onto its flat top


def _cube_texels(dev="cpu"):
    v, f, uv, _, cells = _box()
    ft = torch.tensor(f, dtype=torch.long)
    uvt = torch.tensor(uv, dtype=torch.float32)
    face_id, bary = rasterize_uv(uvt, ft, ATLAS)
    covered = face_id >= 0
    corners, w3 = ft[face_id[covered]], bary[covered][..., None]
    pts = (torch.tensor(v, dtype=torch.float32)[corners] * w3).sum(1).numpy().astype(float)
    return v, f, ft, uvt, covered, corners, w3, pts, cells


def test_back_projection_paints_what_the_view_sees():
    v, f, ft, uvt, covered, corners, w3, pts, cells = _cube_texels()
    cam = ortho(30, 0, [0, 0, 0], 1.2)  # turned 30° towards +X: the front at cos 0.87, +X at 0.5
    base = torch.full((ATLAS, ATLAS, 3), 128.0)
    _, a, _, (_, _, zbuf, _, depth_v) = render(base, uvt, ft, v, cam, 256)
    wt, _ = texel_weights(cam, a, zbuf, depth_v, pts, v, f, corners, w3)
    img = torch.zeros(ATLAS, ATLAS)
    img[covered] = wt

    def at(cell):
        u, w = cells[cell]["centre"]
        return float(img[int(w * ATLAS), int(u * ATLAS)])

    s = (0.5 - 0.25) / 0.35
    assert at((2, 1)) == pytest.approx(1.0)  # the front: full weight
    assert at((0, 1)) == pytest.approx(s * s * (3 - 2 * s), abs=0.02)  # grazing: partly
    assert at((2, -1)) == 0 and at((0, -1)) == 0  # the back and the far side: untouched


def test_the_best_view_wins_and_fades_into_the_original():
    orig = torch.zeros(2, 3)
    acc, wsum, wmax = torch.zeros(2, 3), torch.zeros(2), torch.zeros(2)
    red, blue = torch.tensor([[255.0, 0, 0]] * 2), torch.tensor([[0, 0, 255.0]] * 2)
    out = refine.paint(acc, wsum, wmax, torch.tensor([1.0, 0.5]), red, orig)
    assert out[0].tolist() == [255, 0, 0] and out[1].tolist() == pytest.approx([127.5, 0, 0])
    out = refine.paint(acc, wsum, wmax, torch.tensor([0.5, 1.0]), blue, orig)
    assert out[0, 0] > 15 * out[0, 2]  # the frontal red, a 1/16 trace of blue
    assert out[1, 2] > 15 * out[1, 0]


def test_the_colour_match_removes_a_constant_offset():
    yy, xx = torch.meshgrid(torch.linspace(0, 1, 128), torch.linspace(0, 1, 128), indexing="ij")
    rgb = torch.stack([xx * 0.5, yy * 0.5, xx * 0], -1) + 0.2
    rgb = rgb + 0.1 * ((xx * 40).sin() * (yy * 40).sin())[..., None]  # detail
    a = torch.ones(128, 128)
    out = refine.colour_match(rgb, a, rgb + 0.15, 3.0)[0].permute(1, 2, 0)
    assert (out - rgb)[8:-8, 8:-8].abs().max() < 0.02


def _version(root: Path, name: str, step: str, parent, rgb, outputs=None):
    d = root / name
    d.mkdir(parents=True)
    Image.fromarray(np.asarray(rgb, np.uint8)).save(d / "basecolor.png")
    meta = {
        "version": name,
        "step": step,
        "parent": parent,
        "outputs": outputs or {"basecolor": "basecolor.png"},
    }
    (d / "meta.json").write_text(json.dumps(meta))
    return d


def test_the_face_mask_is_what_project_changed(tmp_path):
    grey = np.full((32, 32, 3), 120)
    face = grey.copy()
    face[4:10, 20:28] = (200, 150, 130)
    face[20, 5] = (125, 120, 120)  # a 5-level wobble is not face
    bake = _version(tmp_path, "030_bake", "bake", None, grey)
    proj = _version(tmp_path, "040_project", "project", "030_bake", face)
    ref = _version(tmp_path, "050_refine", "refine", "040_project", grey)
    for src in (proj, ref):
        m = refine.face_mask(src, 32)
        assert m.sum() == 6 * 8 and m[4:10, 20:28].all()
    assert refine.face_mask(proj, 64).sum() == 4 * 6 * 8  # an upsized atlas
    assert refine.face_mask(bake, 32) is None


class _Identity:
    models = ()

    def encode(self, prompts):
        self.prompts = prompts
        return {p: None for p in prompts}

    def __call__(self, ctrl, emb, strength, scale, seed):
        self.calls = getattr(self, "calls", []) + [strength]
        return ctrl


def _bake(tmp_path):
    v, f, uv, n, _ = _box()
    bake = tmp_path / "asset" / "030_bake"
    bake.mkdir(parents=True)
    yy, xx = np.mgrid[0:ATLAS, 0:ATLAS]
    rgba = np.stack([xx * 2, yy * 2, np.full_like(xx, 90), np.full_like(xx, 255)], -1).astype(
        np.uint8
    )
    rng = np.random.default_rng(0)
    orm = rng.integers(0, 255, (ATLAS, ATLAS, 3), dtype=np.uint8)
    normal_map = rng.integers(0, 255, (ATLAS, ATLAS, 3), dtype=np.uint8)
    write_glb(bake / "mesh.glb", v, f, uv, rgba, orm, n, normal_map)
    meta = {"version": "030_bake", "step": "bake", "parent": None, "outputs": {"mesh": "mesh.glb"}}
    (bake / "meta.json").write_text(json.dumps(meta))
    brief = {"name": "box", "brief": {"prompt_full": "a wooden box"}}
    (tmp_path / "asset" / "asset.json").write_text(json.dumps(brief))
    return bake, rgba, orm, normal_map


def test_a_run_with_an_identity_generator_keeps_the_texture(tmp_path, monkeypatch):
    bake, rgba, orm, normal_map = _bake(tmp_path)
    gen = _Identity()
    monkeypatch.setattr(refine, "VIEW", 256)
    monkeypatch.setattr(refine, "_generator", lambda tile: gen)
    out = tmp_path / "asset" / "040_refine"
    out.mkdir()
    res = refine.run("run", str(bake), str(out), {"seed": 3})
    assert set(res["outputs"]) == {"mesh", "basecolor", "orm", "normal", "views"}
    assert all((out / x).is_file() for x in res["outputs"].values())
    m = res["metrics"]
    assert m["views"] == 9 and m["face_views"] == 0 and gen.calls == [1.0] * 9
    assert m["detail_metric"] == "coherence"
    assert (
        m["drift"] < 1.5 and m["refined"] > 0.5 and 0.5 < m["detail"] < 1.5
    )  # a smooth gradient: little band energy
    assert all(p.startswith("a wooden box, even flat lighting") for p in gen.prompts)
    assert not any(w in p for p in gen.prompts for w in ("front view", "back view", "side view"))
    got = np.asarray(Image.open(out / "basecolor.png"), int)
    # identity in, the texture out: the input with its UV seams levelled (the step's last pass, M43a's)
    v, f, uv, _, _ = _box()
    cov = (
        rasterize_uv(torch.tensor(uv, dtype=torch.float32), torch.tensor(f), ATLAS)[0].numpy() >= 0
    )
    want = heal_seams(rgba[..., :3], cov, seams(v, f, uv, ATLAS)).astype(int)
    assert np.abs(got[..., :3] - want)[cov].mean() < 3
    assert (np.asarray(Image.open(out / "orm.png")) == orm).all()
    assert (np.asarray(Image.open(out / "normal.png")) == normal_map).all()
    glb = trimesh.load(out / "mesh.glb", force="mesh", process=False)
    assert len(glb.faces) == 12


def test_a_view_takes_its_own_prompt(tmp_path, monkeypatch):
    """The owner's agent, 2026-10-13: one prompt for a hoarding's painted front and its bare plywood back drew blue
    panels on every back view. A view's `prompt` replaces the asset's for that view only."""
    bake, *_ = _bake(tmp_path)
    gen = _Identity()
    monkeypatch.setattr(refine, "VIEW", 256)
    monkeypatch.setattr(refine, "_generator", lambda tile: gen)
    out = tmp_path / "asset" / "040_refine"
    out.mkdir()
    views = [
        {"yaw": 0, "center": [0, 0, 0], "extent": 1.2},
        {"yaw": 180, "center": [0, 0, 0], "extent": 1.2, "prompt": "bare weathered plywood"},
    ]
    refine.run("run", str(bake), str(out), {"views": views})
    assert sorted(p.split(",")[0] for p in gen.prompts) == [
        "a wooden box",
        "bare weathered plywood",
    ]


def test_the_detail_metric_counts_strokes_not_speckle():
    """The structure-weighted band energy: stripes (coherent gradients) count, noise of the same band energy
    (incoherent) nearly not; a flat image is 0."""
    n = 96
    xx = torch.arange(n).expand(n, n)
    mask = torch.ones(n, n, dtype=torch.bool)
    flat = torch.full((n, n, 3), 0.5)
    stripes = flat + 0.2 * torch.sin(xx.float() / 1.2)[..., None]  # 2–8 px scale strokes
    g = torch.Generator().manual_seed(0)
    noise = flat + 0.2 * torch.randn(n, n, 1, generator=g)
    e_flat, e_stripes, e_noise = (refine._band_energy(x, mask) for x in (flat, stripes, noise))
    assert e_flat < 1e-6 and e_stripes > 20 * e_noise > 0


def _shadowed(n=128):
    """An albedo with detail, darkened by a known AO (a crevice down the middle), and that AO."""
    yy, xx = torch.meshgrid(torch.linspace(0, 1, n), torch.linspace(0, 1, n), indexing="ij")
    albedo = torch.stack([0 * xx + 180, 0 * xx + 140, 0 * xx + 90], -1)
    albedo = (
        albedo + 20 * ((xx * 60).sin() * (yy * 60).sin())[..., None]
    )  # detail, unrelated to the AO
    ao = 1 - 0.7 * torch.exp(-(((xx - 0.5) / 0.15) ** 2))
    return albedo, ao, albedo * ao[..., None]


def test_delight_divides_the_baked_shadows_out():
    albedo, ao, rgb = _shadowed()
    cov = torch.ones(ao.shape, dtype=torch.bool)
    cov[:, :4] = False  # a gutter: left alone
    assert refine.ao_luma_corr(rgb, ao, cov) > 0.9
    out = refine.delight(rgb, ao, cov, 1.0)
    inner = (slice(8, -8), slice(8, -8))
    assert (out - albedo)[inner].abs().mean() < 6  # the crevice comes back up to the albedo
    assert abs(refine.ao_luma_corr(out, ao, cov)) < 0.1
    assert (out[:, :4] == rgb[:, :4]).all()
    ratio = out[inner][..., 0] / out[inner][..., 2]  # one factor per texel: the hue stays
    assert (ratio - (rgb[inner][..., 0] / rgb[inner][..., 2])).abs().max() < 1e-3
    half = refine.delight(rgb, ao, cov, 0.5)
    assert ((half - rgb)[inner] >= -1e-3).all() and ((out - half)[inner] >= -1e-3).all()
    assert torch.equal(refine.delight(rgb, ao, cov, 0.0), rgb)
    lit = albedo.clone()  # no shadows in the colour: nothing to take out
    assert (refine.delight(lit, ao, cov, 1.0) - lit)[inner].abs().max() < 1


def _bake_with_ao(tmp_path):
    v, f, uv, n, _ = _box()
    bake = tmp_path / "asset" / "030_bake"
    bake.mkdir(parents=True)
    xx = np.mgrid[0:ATLAS, 0:ATLAS][1]
    ao = 1 - 0.6 * (xx > ATLAS // 2)  # every cell's right part occluded
    rgba = np.stack([160 * ao, 120 * ao, 80 * ao, np.full_like(ao, 255)], -1).astype(np.uint8)
    orm = np.stack([ao * 255, np.full_like(ao, 200), np.zeros_like(ao)], -1).astype(np.uint8)
    write_glb(bake / "mesh.glb", v, f, uv, rgba, orm, n, None, occlusion=True)
    meta = {"version": "030_bake", "step": "bake", "parent": None, "outputs": {"mesh": "mesh.glb"}}
    (bake / "meta.json").write_text(json.dumps(meta))
    return bake


def test_a_delight_only_run_loads_no_model(tmp_path, monkeypatch):
    bake = _bake_with_ao(tmp_path)
    monkeypatch.setattr(refine, "_generator", lambda tile: pytest.fail("no model without views"))
    out = tmp_path / "asset" / "040_refine"
    out.mkdir()
    res = refine.run("run", str(bake), str(out), {"views": [], "delight": 1.0})
    assert set(res["outputs"]) == {"mesh", "basecolor", "orm"} and res["models"] == []
    m = res["metrics"]
    assert m["views"] == 0 and m["delight"] == 1.0
    assert m["ao_luma_corr_before"] > 0.5 and abs(m["ao_luma_corr"]) < 0.25
    got = trimesh.load(out / "mesh.glb", force="mesh", process=False).visual.material
    assert got.occlusionTexture is not None  # the AO still goes to the engine


def test_delight_needs_the_bakes_ao(tmp_path):
    bake, *_ = _bake(tmp_path)  # no occlusionTexture: a pre-M43a or CPU bake
    with pytest.raises(StepError) as e:
        refine.run("run", str(bake), str(tmp_path / "out"), {"views": [], "delight": 0.5})
    assert e.value.code == "missing_input"


@pytest.mark.parametrize(
    "params",
    [
        {"delight": 1.5},
        {"delight": "yes"},
        {"strength": 0.1},
        {"face_strength": 0},
        {"scale": 2},
        {"zoom": 0.1},
        {"zoom": "big"},
        {"texture_size": 8192},
        {"seed": "x"},
        {"prompt": " "},
        {"views": [{"yaw": 0}]},
        {"views": [{"yaw": 0, "center": [0, 0, 0], "extent": 1, "prompt": " "}]},
        {"views": []},
        {"tile": "huge"},
    ],
)
def test_bad_params(tmp_path, params):
    bake, *_ = _bake(tmp_path)
    with pytest.raises(StepError) as e:
        refine.run("run", str(bake), str(tmp_path / "out"), params)
    assert e.value.code == "bad_params"


@pytest.mark.skipif(
    not (
        os.environ.get("EFFIGY_GPU_TESTS")
        and torch.cuda.is_available()
        and (
            Path(os.environ.get("EFFIGY_MODELS", Path(__file__).resolve().parents[1] / "models"))
            / refine.TILE_DIR
            / refine.TILES["lite"][0]
        ).is_file()
    ),
    reason="the real Tile model: EFFIGY_GPU_TESTS=1, CUDA and the `refine` group installed",
)
def test_the_real_model_draws_one_view(tmp_path):
    bake, *_ = _bake(tmp_path)
    front = {"yaw": 0, "pitch": 0, "center": [0, 0, 0], "extent": 0.7}
    out = tmp_path / "asset" / "040_refine"
    out.mkdir()
    res = refine.run("run", str(bake), str(out), {"views": [front], "seed": 1, "tile": "lite"})
    m = res["metrics"]
    assert m["views"] == 1 and m["peak_reserved_gb"] <= 14.5 and m["drift"] < 8
    assert [x["id"] for x in res["models"]] == ["Tongyi-MAI/Z-Image-Turbo", refine.TILE]


def test_the_full_tile_when_it_is_downloaded_and_fits(tmp_path, monkeypatch):
    """M46c: without a "tile" param refine takes the full Tile when its file is there and the budget holds its
    15.6 GB; asked for one, it loads that one (the pre-flight refuses full where it cannot fit)."""
    from steps import _common

    monkeypatch.setenv("EFFIGY_MODELS", str(tmp_path))
    monkeypatch.setattr(_common, "_budget", 22.6)
    assert refine._tile(None) == "lite"  # not downloaded
    full = tmp_path / refine.TILE_DIR / refine.TILES["full"][0]
    full.parent.mkdir(parents=True)
    full.write_bytes(b"")
    assert refine._tile(None) == "full"
    monkeypatch.setattr(_common, "_budget", 14.66)  # the 16 GB laptop
    assert refine._tile(None) == "lite"
    assert refine._tile("full") == "full" and refine._tile("lite") == "lite"
