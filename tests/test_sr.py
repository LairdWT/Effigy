"""steps/_sr.py (M24): the written-out RRDBNet and the tiled 4× upscale, without the weights."""

import numpy as np
import pytest

torch = pytest.importorskip("torch")
from steps import _sr


def test_rrdbnet_has_the_published_shape_and_upscales_four_times():
    net = _sr.RRDBNet()
    keys = set(net.state_dict())
    assert {
        "conv_first.weight",
        "body.22.rdb3.conv5.bias",
        "conv_up2.weight",
        "conv_last.bias",
    } <= keys
    assert len(keys) == 2 * (
        6 + 23 * 3 * 5
    )  # six plain convs and 23 blocks of three dense blocks of five
    small = _sr.RRDBNet(nb=1).eval()
    with torch.no_grad():
        assert small(torch.zeros(1, 3, 12, 16)).shape == (1, 3, 48, 64)


def test_upscale_tiles_cover_the_image(monkeypatch):
    torch.manual_seed(0)  # an unseeded random net now and then gave a near-flat picture (std <= 1)
    net = _sr.RRDBNet(nb=1).eval()
    rgb = (np.random.default_rng(0).random((40, 56, 3)) * 255).astype(np.uint8)
    out = _sr.upscale(net, rgb, tile=24, pad=4)
    assert out.shape == (160, 224, 3) and out.dtype == np.uint8 and out.std() > 1


def test_load_names_the_model_group_when_the_weights_are_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_MODELS", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="texture"):
        _sr.load("cpu")


def test_tiles_agree_with_the_whole_image_when_the_overlap_covers_the_receptive_field():
    net = _sr.RRDBNet(nb=1).eval()
    rgb = (np.random.default_rng(1).random((40, 56, 3)) * 255).astype(np.uint8)
    tiled, whole = _sr.upscale(net, rgb, tile=24, pad=20), _sr.upscale(net, rgb, tile=4096, pad=0)
    assert np.abs(tiled.astype(int) - whole.astype(int)).max() <= 1


@pytest.mark.skipif(
    not _sr.weights_path().is_file(), reason="the texture model group is not installed"
)
def test_the_published_weights_load_strictly():
    net = _sr.load("cpu")
    assert sum(p.numel() for p in net.parameters()) == 16_697_987
