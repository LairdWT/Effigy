"""engine/pixal3d/patches.py on the CPU: vendored Pixal3D imports, na2d matches NATTEN's neighbourhoods, and
the proj extractor runs DINOv3 (transformers 5) + NAF (vendored, local weights) on the shim."""

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
from engine.pixal3d import patches

pixal3d = patches.prepare("/tmp")


def natten_start(i, n, k, d):
    """NATTEN's get_window_start, transcribed from its CUDA source."""
    ns = k // 2
    if d <= 1:
        return max(i - ns, 0) + (i + ns >= n) * (n - i - ns - 1)
    if i - ns * d < 0:
        return i % d
    if i + ns * d >= n:
        a = n // d * d
        b = n - a
        return n - b + i % d - 2 * ns * d if i % d < b else a + i % d - k * d
    return i - ns * d


@pytest.mark.parametrize("hw,k,d", [((7, 9), (3, 5), (1, 1)), ((12, 13), (3, 3), (2, 3))])
def test_na2d_matches_brute_force(hw, k, d):
    torch.manual_seed(0)
    (H, W), (kh, kw), (dh, dw) = hw, k, d
    q, key, v = torch.randn(1, H, W, 2, 8), torch.randn(1, H, W, 2, 8), torch.randn(1, H, W, 2, 4)
    want = torch.empty(1, H, W, 2, 4)
    for i in range(H):
        for j in range(W):
            si, sj = natten_start(i, H, kh, dh), natten_start(j, W, kw, dw)
            ri, rj = range(si, si + kh * dh, dh), range(sj, sj + kw * dw, dw)
            kk = key[0][list(ri)][:, list(rj)].reshape(-1, 2, 8)  # [kh·kw, heads, D]
            vv = v[0][list(ri)][:, list(rj)].reshape(-1, 2, 4)
            w = torch.einsum("nd,knd->nk", q[0, i, j], kk).mul(8**-0.5).softmax(-1)
            want[0, i, j] = torch.einsum("nk,knc->nc", w, vv)
    got = patches.na2d(q, key, v, kernel_size=k, dilation=d, stride=1, backend="cutlass-fna")
    torch.testing.assert_close(got, want)


@pytest.fixture
def tiny_dino(tmp_path, monkeypatch):
    """A 2-layer DINOv3 on disk and random NAF weights behind the patched loader: (path, config)."""
    from pixal3d.trainers.flow_matching.mixins import image_conditioned_proj as proj
    from src.model.naf import NAF
    from transformers import DINOv3ViTConfig, DINOv3ViTModel

    torch.manual_seed(1)
    cfg = DINOv3ViTConfig(
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=2,
        patch_size=16,
        num_register_tokens=4,  # as the real model; 0 saves a zero-size tensor Windows can't load
    )
    DINOv3ViTModel(cfg).save_pretrained(tmp_path / "dino")
    torch.save(NAF().state_dict(), tmp_path / "naf.pth")
    monkeypatch.setattr(
        proj.DinoV3ProjFeatureExtractor, "_load_naf", patches._naf_loader(tmp_path / "naf.pth")
    )
    return tmp_path / "dino", cfg


def test_proj_extractor_runs_dinov3_and_naf(tiny_dino):
    from pixal3d.trainers.flow_matching.mixins import image_conditioned_proj as proj

    dino, cfg = tiny_dino

    def extractor():
        return proj.DinoV3ProjFeatureExtractor(
            str(dino),
            image_size=160,
            grid_resolution=4,
            use_naf_upsample=True,
            naf_target_size=160,
        )

    a, b = extractor(), extractor()
    assert a.model is b.model  # one DINOv3 for every stage
    z_global, z_proj = a(
        torch.rand(1, 3, 160, 160),
        camera_angle_x=torch.tensor([0.2]),
        distance=torch.tensor([0.5 / torch.tan(torch.tensor(0.1))]),
        mesh_scale=torch.tensor([1.0]),
    )
    assert z_global.shape == (1, 1 + cfg.num_register_tokens, 32)
    assert z_proj.shape == (1, 4**3, 64)  # low-res DINOv3 + NAF-upsampled features
    assert torch.isfinite(z_proj).all()


def test_mv_forward_lean_matches_upstream(tiny_dino):
    """Patch 14: same conditioning as upstream's multi-view forward, for 3 views around the object."""
    import math

    from pixal3d.trainers.flow_matching.mixins import image_conditioned_proj as proj

    torch.manual_seed(2)
    ext = proj.DinoV3ProjMultiViewFeatureExtractor(
        str(tiny_dino[0]),
        image_size=160,
        grid_resolution=4,
        use_naf_upsample=True,
        naf_target_size=160,
    ).eval()
    d = 0.5 / math.tan(0.1)
    front = torch.tensor([[1, 0, 0, 0], [0, 0, -1, -d], [0, 1, 0, 0], [0, 0, 0, 1.0]])

    def rz(deg):
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        return torch.tensor([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])

    args = {
        "camera_angle_x": torch.full((1, 3), 0.2),
        "distance": torch.full((1, 3), d),
        "mesh_scale": torch.tensor([1.0]),
        "transform_matrix": torch.stack([rz(a) @ front for a in (0, -90, 180)])[None],
    }
    image = torch.rand(1, 3, 3, 160, 160)
    got = patches.mv_forward_lean(ext, image, **args)
    want = patches.mv_forward_lean.upstream(ext, image, **args)
    for g, w in zip(got, want):
        torch.testing.assert_close(g, w)


def test_naf_attention_chunked_matches_upstream():
    """Patch 15: chunks smaller than a head, and a chunk that would straddle two heads."""
    from src.layers import attentions

    assert attentions.NATTEN_RECENT  # the na2d path the patch replaces
    torch.manual_seed(3)
    att = attentions.CrossAttention(dim=16, num_heads=4, kernel_size=(3, 3))
    q, k, v = torch.randn(1, 16, 12, 12), torch.randn(1, 16, 6, 6), torch.randn(1, 24, 6, 6)
    want = patches.naf_attention_chunked.upstream(att, q, k, v)
    # uninitialised output memory reads as NaN here: a chunk loop that skips channels can't pass by luck
    # (it did: the allocator handed back the previous run's buffer)
    fill = torch.utils.deterministic.fill_uninitialized_memory
    det = torch.are_deterministic_algorithms_enabled()
    torch.utils.deterministic.fill_uninitialized_memory = True
    torch.use_deterministic_algorithms(True)
    try:
        for chunk in (2, 4, 5):
            torch.testing.assert_close(
                patches.naf_attention_chunked(att, q, k, v, chunk=chunk), want
            )
        # non-square, a different factor per axis (16/4, 12/6), taps shifted inward at the borders
        q2, k2, v2 = torch.randn(2, 16, 16, 12), torch.randn(2, 16, 4, 6), torch.randn(2, 24, 4, 6)
        want2 = patches.naf_attention_chunked.upstream(att, q2, k2, v2)
        torch.testing.assert_close(patches.naf_attention_chunked(att, q2, k2, v2, chunk=5), want2)
        q3, k3 = (
            torch.randn(1, 16, 9, 9),
            torch.randn(1, 16, 6, 6),
        )  # not an integer factor: upstream
        want3 = patches.naf_attention_chunked.upstream(att, q3, k3, v)
        torch.testing.assert_close(patches.naf_attention_chunked(att, q3, k3, v), want3)
    finally:
        torch.utils.deterministic.fill_uninitialized_memory = fill
        torch.use_deterministic_algorithms(det)


def test_rmbg_is_never_built():
    from pixal3d.pipelines import rembg

    with pytest.raises(RuntimeError, match="steps.prep"):
        rembg.BiRefNet(model_name="briaai/RMBG-2.0")(None)


def test_pipeline_imports():
    pytest.importorskip("cumesh")  # the mesh representation needs our CUDA wheels (laptop venv)
    from pixal3d.pipelines import Pixal3DImageTo3DPipeline

    assert "tex_slat_flow_model_1024" in Pixal3DImageTo3DPipeline.model_names_to_load
