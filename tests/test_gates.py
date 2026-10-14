"""M10: 3D-readiness gates and prep framing on synthetic fixture images."""

import numpy as np
import pytest

from steps._image import frame, gates, premultiply_black, rank

N = 1024


def scene(discs, bg=180, noise=0.0, size=N):
    """Grey background with shaded discs [(cx, cy, r)] → (rgb, alpha)."""
    yy, xx = np.mgrid[:size, :size]
    alpha = np.zeros((size, size), np.float32)
    rgb = np.full((size, size, 3), bg, np.float32)
    for cx, cy, r in discs:
        inside = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
        alpha[inside] = 1
        rgb[inside] = (60 + 120 * (xx[inside] - cx + r) / (2 * r))[:, None]  # a shading gradient
    rgb += np.random.default_rng(0).normal(0, noise, rgb.shape)
    return np.clip(rgb, 0, 255).astype(np.uint8), alpha


def hard_fails(g):
    return {k for k, v in g.items() if v["hard"] and not v["ok"]}


def test_clean_subject_passes():
    assert hard_fails(gates(*scene([(512, 512, 330)]))) == set()


def test_cropped_two_components_noisy_small_fail():
    assert "margin" in hard_fails(gates(*scene([(900, 512, 330)])))  # cut by the right border
    assert "one_component" in hard_fails(gates(*scene([(300, 512, 200), (724, 512, 200)])))
    assert "uniform_background" in hard_fails(gates(*scene([(512, 512, 330)], noise=20)))
    assert hard_fails(gates(*scene([(256, 256, 165)], size=512))) == {"resolution"}
    assert "size" in hard_fails(gates(*scene([(512, 512, 120)])))  # too small in frame
    # a long object fills the width (0.93) and still passes: the margin gate guards the border
    wide = gates(*scene([(280, 512, 245), (744, 512, 245)]))
    assert not {"size", "margin"} & hard_fails(wide) and wide["size"]["value"] > 0.9


def test_specks_are_ignored_and_ranking():
    speck = gates(*scene([(512, 512, 330), (60, 60, 10)]))  # 0.03 % of the frame
    assert speck["one_component"]["ok"]
    ranked = rank(
        {"a.png": gates(*scene([(900, 512, 330)])), "b.png": gates(*scene([(512, 512, 330)]))}
    )
    assert ranked["b.png"]["rank"] == 1 and ranked["a.png"]["hard_fails"] >= 1


def test_frame_is_square_padded_and_keeps_alpha():
    rgb, alpha = scene([(700, 400, 100)])
    rgba, info = frame(rgb, alpha)
    side = info["crop"]["side"]
    assert rgba.shape == (side, side, 4) and side == round(201 * 1.08)
    assert info["subject_bbox"] == [600, 300, 800, 500]
    # subject centred, corners empty
    assert rgba[side // 2, side // 2, 3] == 255 and rgba[0, 0, 3] == 0
    assert premultiply_black(rgba)[0, 0].tolist() == [0, 0, 0]
    # the padded box overhangs the frame: black fill, then downscaled to 1024
    big, info = frame(*scene([(1024, 1024, 1000)], size=2048))
    assert big.shape == (1024, 1024, 4) and info["crop"]["left"] < 0
    with pytest.raises(ValueError):
        frame(rgb, np.zeros_like(alpha))


def test_prep_uses_an_existing_cutout(tmp_path):
    import json

    from PIL import Image

    from steps import prep

    rgb, alpha = scene([(400, 600, 150)])
    rgba = np.dstack([rgb, (alpha * 255).astype(np.uint8)])
    up, out = tmp_path / "010_upload", tmp_path / "020_prep"
    up.mkdir()
    out.mkdir()
    Image.fromarray(rgba, "RGBA").save(up / "image.png")
    (up / "meta.json").write_text(
        json.dumps({"version": "010_upload", "outputs": {"image": "image.png"}})
    )
    res = prep.run("run", str(up), str(out), {})
    assert res["licenses"] == [] and res["metrics"]["size"] == round(
        301 * 1.08
    )  # no matting model used
    im = Image.open(out / "image.png")
    assert im.mode == "RGBA" and im.size[0] == im.size[1]
    assert json.loads((out / "crop.json").read_text())["subject_bbox"] == [250, 450, 550, 750]
