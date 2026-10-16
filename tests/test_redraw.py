"""redraw (M61): the window plan and blend, protect, alpha, params, on the CPU with the models faked (identity)."""

import json
from contextlib import contextmanager
from itertools import pairwise

import numpy as np
import pytest

pytest.importorskip("torch")
from PIL import Image

from steps import _sr, redraw
from steps._common import StepError


def _version(root, name, arr, key="image"):
    d = root / name
    d.mkdir(parents=True)
    Image.fromarray(arr).save(d / "image.png")
    (d / "meta.json").write_text(
        json.dumps({"version": name, "outputs": {key: "image.png"}}), encoding="utf-8"
    )
    return d


@contextmanager
def _identity(p):
    yield (lambda win, seed: win), [{"id": "fake"}]


def _run(monkeypatch, tmp_path, arr, **params):
    monkeypatch.setattr(redraw, "_model", _identity)
    src = _version(tmp_path, "001_upload", arr)
    out = tmp_path / "002_redraw"
    out.mkdir()
    res = redraw.run("redraw", src, out, {"prompt": "a wall", "window": 256, **params})
    return res, np.asarray(Image.open(out / "image.png"))


def test_windows_cover_the_axis_and_overlap():
    for n, win, ov in [(1000, 256, 64), (257, 256, 64), (5000, 1024, 256), (300, 256, 0)]:
        starts = _sr.plan(n, win, ov)
        assert starts[0] == 0 and starts[-1] + win == n
        assert all(b - a <= win - ov for a, b in pairwise(starts))
    assert _sr.plan(100, 256, 64) == [0]


def test_blend_of_the_same_picture_is_that_picture_without_a_seam():
    rng = np.random.default_rng(0)
    img = (rng.random((300, 700, 1, 3)) * 255)[:, :, 0].astype(np.float32)
    b = _sr.Blend(300, 700, 256, 64)
    for y, x in b.windows():
        b.add(y, x, img[y : y + b.wh, x : x + b.ww])
    assert np.abs(b.result() - img).max() < 1e-3
    flat = _sr.Blend(300, 700, 256, 64)
    for y, x in flat.windows():
        flat.add(y, x, np.full((flat.wh, flat.ww, 3), 90.0, np.float32))
    assert np.abs(flat.result() - 90).max() < 1e-3


def test_an_identity_redraw_comes_back_unchanged_with_a_clean_report(monkeypatch, tmp_path):
    arr = np.tile((np.arange(700) * 255 // 700).astype(np.uint8)[None, :, None], (300, 1, 3))
    res, out = _run(monkeypatch, tmp_path, arr)
    assert (out == arr).all()
    m = res["metrics"]
    assert (
        m["windows"] == 8 and m["drift"] == 0 and m["seam_ratio"] <= 1.0 and all(m["pass"].values())
    )
    assert res["outputs"]["preview"] == "preview.png" and next(iter(res["outputs"])) == "preview"
    assert len(json.loads((tmp_path / "002_redraw" / "report.json").read_text())["per_window"]) == 8


def test_a_picture_smaller_than_the_window_is_padded_and_cropped(monkeypatch, tmp_path):
    arr = np.full((90, 130, 3), 40, np.uint8)
    res, out = _run(monkeypatch, tmp_path, arr)
    assert out.shape == (90, 130, 3) and res["metrics"]["windows"] == 1


def test_protect_keeps_the_original_where_the_mask_is_white(monkeypatch, tmp_path):
    arr = np.full((300, 300, 3), 200, np.uint8)
    mask = np.zeros((300, 300), np.uint8)
    mask[:, :150] = 255
    _version(tmp_path, "003_mask", mask)

    @contextmanager
    def black(p):
        yield (lambda win, seed: np.zeros_like(win)), []

    monkeypatch.setattr(redraw, "_model", black)
    src = _version(tmp_path, "001_upload", arr)
    out = tmp_path / "004_redraw"
    out.mkdir()
    redraw.run("redraw", src, out, {"prompt": "x", "window": 256, "protect": "003_mask"})
    got = np.asarray(Image.open(out / "image.png"))
    assert (got[:, :140] == 200).all() and (got[:, 160:] == 0).all()
    with pytest.raises(StepError, match="protect"):
        redraw.run("redraw", src, out, {"prompt": "x", "protect": "999_none"})


def test_alpha_goes_back_after_the_redraw(monkeypatch, tmp_path):
    arr = np.zeros((64, 64, 4), np.uint8)
    arr[..., :3] = 100
    arr[:, 32:, 3] = 255
    arr[10:20, :32, 3] = 128
    _, out = _run(monkeypatch, tmp_path, arr)
    assert out.shape == (64, 64, 4) and (out[..., 3] == arr[..., 3]).all()
    assert (out[:, 32:, :3] == 100).all()


def test_upscale_makes_the_picture_bigger_and_keeps_alpha(monkeypatch, tmp_path):
    net = _sr.RRDBNet(nb=1).eval()
    monkeypatch.setattr(_sr, "load", lambda device=None: net)
    arr = (np.random.default_rng(2).random((40, 56, 4)) * 255).astype(np.uint8)
    src = _version(tmp_path, "001_upload", arr)
    out = tmp_path / "002_redraw"
    out.mkdir()
    res = redraw.run("upscale", src, out, {"factor": 2})
    got = Image.open(out / "image.png")
    assert got.size == (112, 80) and got.mode == "RGBA" and res["metrics"]["size"] == [112, 80]
    assert res["licenses"] == [_sr.MODEL] and "seam_ratio" not in res["metrics"]


def test_params_are_checked():
    for op, bad in [
        ("redraw", {}),
        ("redraw", {"prompt": " "}),
        ("redraw", {"prompt": "x", "strength": 0.1}),
        ("redraw", {"prompt": "x", "window": 1000}),
        ("redraw", {"prompt": "x", "overlap": 0.9}),
        ("redraw", {"prompt": "x", "lora": "nope"}),
        ("redraw", {"prompt": "x", "protect": "../x"}),
        ("upscale", {"factor": 3}),
        ("sharpen", {}),
    ]:
        with pytest.raises(StepError) as e:
            redraw._params(op, bad)
        assert e.value.code == "bad_params"
    assert redraw._params("redraw", {"prompt": "x"})["strength"] == 0.35
