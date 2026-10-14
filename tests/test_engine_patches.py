"""engine/trellis2/patches.py on the CPU: the vendored TRELLIS.2 imports, sparse attention runs on our SDPA
stand-in (no xformers / flash-attn), DINOv3 works on transformers 5, RMBG-2.0 is never built."""

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
from engine.trellis2.patches import (
    BlockDiagonalMask,
    memory_efficient_attention,
    prepare,
)

trellis2 = prepare("/tmp")


def reference(q, k, v, lq, lkv):
    """Packed sequences attend only within themselves: one dense SDPA per sequence."""
    out, a, b = [], 0, 0
    for nq, nk in zip(lq, lkv):
        qi, ki, vi = (
            t[None].transpose(1, 2) for t in (q[a : a + nq], k[b : b + nk], v[b : b + nk])
        )
        out.append(torch.nn.functional.scaled_dot_product_attention(qi, ki, vi)[0].transpose(0, 1))
        a, b = a + nq, b + nk
    return torch.cat(out)


def test_varlen_attention_matches_per_sequence_reference():
    torch.manual_seed(0)
    lq, lkv = [5, 7, 5, 1, 7], [3, 8, 3, 2, 8]  # repeated shapes take the batched path
    q, k, v = torch.randn(sum(lq), 4, 16), torch.randn(sum(lkv), 4, 16), torch.randn(sum(lkv), 4, 8)
    got = memory_efficient_attention(
        q[None], k[None], v[None], BlockDiagonalMask.from_seqlens(lq, lkv)
    )[0]
    torch.testing.assert_close(got, reference(q, k, v, lq, lkv))


def test_vendored_sparse_attention_runs_on_the_shim():
    from trellis2.modules.sparse import VarLenTensor, config
    from trellis2.modules.sparse.attention.full_attn import sparse_scaled_dot_product_attention

    assert config.ATTN == "xformers"
    torch.manual_seed(1)
    seq = [6, 9]
    qkv = torch.randn(sum(seq), 3, 2, 8)
    out = sparse_scaled_dot_product_attention(
        VarLenTensor(qkv, VarLenTensor.layout_from_seqlen(seq))
    )
    q, k, v = qkv.unbind(1)
    torch.testing.assert_close(out.feats, reference(q, k, v, seq, seq))


def test_vendored_windowed_attention_runs_on_the_shim():
    from trellis2.modules.sparse import SparseTensor
    from trellis2.modules.sparse.attention.windowed_attn import (
        sparse_windowed_scaled_dot_product_self_attention,
    )

    torch.manual_seed(2)
    xyz = torch.unique(torch.randint(0, 16, (300, 3)), dim=0)
    coords = torch.cat([torch.zeros(len(xyz), 1, dtype=torch.int32), xyz.int()], 1)
    qkv = torch.randn(len(xyz), 3, 2, 8)
    out = sparse_windowed_scaled_dot_product_self_attention(SparseTensor(qkv, coords), 8).feats
    window = (xyz // 8 * torch.tensor([4, 2, 1])).sum(1)  # 2×2×2 windows of 8³
    want = torch.empty_like(out)
    for w in window.unique():
        idx = (window == w).nonzero()[:, 0]
        q, k, v = qkv[idx].unbind(1)
        want[idx] = reference(q, k, v, [len(idx)], [len(idx)])
    torch.testing.assert_close(out, want)


def test_dinov3_features_on_transformers_5():
    from transformers import DINOv3ViTConfig, DINOv3ViTModel
    from trellis2.modules.image_feature_extractor import DinoV3FeatureExtractor

    cfg = DINOv3ViTConfig(
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=2,
        patch_size=16,
    )
    ext = DinoV3FeatureExtractor.__new__(DinoV3FeatureExtractor)  # skip the hub download
    ext.model = DINOv3ViTModel(cfg).eval()
    assert not hasattr(
        ext.model, "layer"
    )  # why upstream's extract_features breaks on transformers 5
    img = torch.randn(1, 3, 64, 64)
    with torch.no_grad():
        feats = ext.extract_features(img)
        hidden = ext.model.embeddings(img, bool_masked_pos=None)
        rope = ext.model.rope_embeddings(img)
        for block in ext.model.model.layer:
            hidden = block(hidden, position_embeddings=rope)
    torch.testing.assert_close(feats, torch.nn.functional.layer_norm(hidden, hidden.shape[-1:]))
    assert feats.shape[-1] == 32


def test_rmbg_is_never_built():
    from trellis2.pipelines import rembg

    stub = rembg.BiRefNet(model_name="briaai/RMBG-2.0")
    assert stub.to("cuda") is stub
    with pytest.raises(RuntimeError, match="steps.prep"):
        stub(None)


def test_no_random_init():
    from engine.trellis2.patches import no_random_init

    kaiming = torch.nn.init.kaiming_uniform_
    w = torch.full((4, 4), 7.0)
    with no_random_init():
        assert torch.nn.init.kaiming_uniform_(w) is w and (w == 7).all()
        torch.nn.Linear(4, 4)  # its reset_parameters goes through the no-ops
    assert torch.nn.init.kaiming_uniform_ is kaiming
    assert trellis2.models.from_pretrained.effigy_patched


def test_single_sequence_mask_matches_the_reference():
    torch.manual_seed(1)
    q, k, v = torch.randn(9, 4, 16), torch.randn(5, 4, 16), torch.randn(5, 4, 8)
    mask = BlockDiagonalMask.from_seqlens([9], [5])  # the direct SDPA path
    got = memory_efficient_attention(q[None], k[None], v[None], mask)[0]
    torch.testing.assert_close(got, reference(q, k, v, [9], [5]))
