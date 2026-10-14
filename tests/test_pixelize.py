"""M51 pixelize (research 15 §5.3): the grid of a picture drawn large, one palette over frames, dither, the
outline, palette files, the sheet round trip and the step end to end. CPU, no model."""

import json

import numpy as np
import pytest
from PIL import Image

from steps import _pixel, _sheet, pixelize
from steps._common import StepError

PAL = np.array(
    [[200, 30, 30], [30, 200, 30], [30, 30, 200], [240, 240, 20], [20, 240, 240]], np.uint8
)


def sprite(seed=0, w=12, h=10):
    rng = np.random.default_rng(seed)
    a = np.full((h, w, 4), 255, np.uint8)
    a[..., :3] = PAL[rng.integers(0, len(PAL), (h, w))]
    a[:2] = 0  # a transparent band: an alpha edge on the grid too
    return a


def blow_up(a, k, pad=(3, 2)):
    """The sprite drawn k times larger, off the grid by `pad` pixels, with a ragged transparent border."""
    return np.pad(a.repeat(k, 0).repeat(k, 1), ((pad[1], 5), (pad[0], 7), (0, 0)))


def test_grid_and_dominant_downscale_recover_the_picture():
    big = blow_up(sprite(), 6, (3, 2))
    period, offset = _pixel.grid([big])
    assert (period, offset) == (6, (3, 2))
    small = _pixel.downscale(big, period, offset)
    assert np.array_equal(small[1:11, 1:13], sprite()) and small[0].max() == 0
    assert np.array_equal(_pixel.downscale(big, period, offset, "median")[1:11, 1:13], sprite())


def test_a_sharp_picture_has_no_grid():
    rng = np.random.default_rng(1)
    noise = rng.integers(0, 256, (64, 64, 4), dtype=np.uint8)
    ramp = np.broadcast_to(np.linspace(0, 255, 64, dtype=np.uint8)[None, :, None], (64, 64, 4))
    assert _pixel.grid([noise])[0] == 1 and _pixel.grid([ramp])[0] == 1
    assert np.array_equal(_pixel.downscale(noise, 1), noise)
    # only anti-correlated peaks (a dark sprite sheet, 2026-10-14): 0.8 × a negative best let none pass, min() of nothing
    profile = np.array("3 1 8 3 3 9 8 1 2 4 4 8 9 10 2 0 5 2 5 3 8 1".split(), float) / 10  # noqa: SIM905
    assert _pixel._period(profile) == (1, 0.0)


def test_one_palette_over_frames_and_binary_alpha():
    frames = [_pixel.cut_alpha(sprite(s).astype(np.uint8)) for s in range(3)]
    pal = _pixel.make_palette(frames, 4)
    assert 1 <= len(pal) <= 4
    out = [_pixel.apply_palette(f, pal) for f in frames]
    seen = {tuple(px) for f in out for px in f[f[..., 3] > 0][:, :3]}
    assert seen <= {tuple(c) for c in pal} and all(
        set(np.unique(f[..., 3])) <= {0, 255} for f in out
    )


def test_ordered_dither_is_still_and_changes_a_gradient():
    g = np.zeros((8, 64, 4), np.uint8)
    g[..., :3], g[..., 3] = np.linspace(0, 255, 64, dtype=np.uint8)[None, :, None], 255
    pal = np.array([[0, 0, 0], [85, 85, 85], [170, 170, 170], [255, 255, 255]], np.uint8)
    flat, dithered = _pixel.apply_palette(g, pal), _pixel.apply_palette(g, pal, "bayer4")
    assert not np.array_equal(flat, dithered)
    assert np.array_equal(dithered, _pixel.apply_palette(g, pal, "bayer4"))


def test_outline_and_palette_swap():
    a = np.zeros((8, 8, 4), np.uint8)
    a[2:6, 2:6] = (200, 30, 30, 255)
    lined = _pixel.outline(a, (0, 0, 0))
    assert (lined[..., 3] > 0).sum() == 16 + 16 and tuple(lined[1, 3]) == (0, 0, 0, 255)
    swapped = _pixel.remap(lined, {"#c81e1e": "#1e1ec8"})
    assert tuple(swapped[3, 3]) == (30, 30, 200, 255) and tuple(swapped[1, 3]) == (0, 0, 0, 255)
    with pytest.raises(ValueError):
        _pixel.hex_rgb("red")


def test_palette_files(tmp_path):
    _pixel.write_gpl(PAL, tmp_path / "p.gpl", "five")
    assert np.array_equal(_pixel.read_palette(tmp_path / "p.gpl"), np.unique(PAL, axis=0))
    (tmp_path / "p.hex").write_text("c81e1e\n#1ec81e\n")
    assert _pixel.read_palette(tmp_path / "p.hex").tolist() == [[30, 200, 30], [200, 30, 30]]
    (tmp_path / "p.pal").write_text("JASC-PAL\n0100\n2\n255 0 0\n0 0 255\n")
    assert _pixel.read_palette(tmp_path / "p.pal").tolist() == [[0, 0, 255], [255, 0, 0]]
    pico = _pixel.read_palette(_pixel.PALETTES / "pico-8.gpl")
    assert len(pico) == 16 and [255, 0, 77] in pico.tolist()


def test_sheet_round_trip():
    ims = [
        Image.fromarray(sprite(s, w, h), "RGBA")
        for s, (w, h) in enumerate([(4, 6), (5, 6), (4, 5)])
    ]
    frames = [(f"f{i}", im) for i, im in enumerate(ims)]
    tag = {"name": "walk", "from": 0, "to": 2, "direction": "forward"}
    sheet, data = _sheet.pack(frames, [tag], [50, 60, 70])
    assert sheet.size == (10, 12) and data["frames"][2]["frame"] == {"x": 0, "y": 6, "w": 5, "h": 6}
    assert data["meta"]["frameTags"] == [tag] and [f["duration"] for f in data["frames"]] == [
        50,
        60,
        70,
    ]
    back = _sheet.unpack(sheet, data)
    assert [n for n, _ in back] == ["f0", "f1", "f2"] and all(im.size == (5, 6) for _, im in back)
    assert np.array_equal(
        np.asarray(back[0][1])[:, :4], np.asarray(ims[0])
    )  # bottom-centred, same pixels
    assert np.array_equal(np.asarray(back[2][1])[1:, :4], np.asarray(ims[2]))
    assert _sheet.contact(sheet, 100).size == (80, 96)


def _version(root, name, outputs, pictures):
    d = root / name
    d.mkdir(parents=True)
    for rel, arr in pictures.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(arr, "RGBA").save(d / rel)
    (d / "meta.json").write_text(json.dumps({"version": name, "outputs": outputs}))
    return d


def test_step_on_a_picture_frames_and_a_sheet(tmp_path):
    big = blow_up(sprite(), 6, (3, 2))
    one = _version(tmp_path / "a", "001_upload", {"image": "image.png"}, {"image.png": big})
    out = tmp_path / "a" / "002_pixelize"
    out.mkdir()
    res = pixelize.run("run", str(one), str(out), {"colors": 8, "outline": "darkest"})
    assert res["metrics"]["scale"] == 6 and res["metrics"]["frames"] == 1 and res["licenses"] == []
    assert (
        all((out / rel).exists() for rel in res["outputs"].values()) and "image" in res["outputs"]
    )
    img = np.asarray(Image.open(out / "image.png"))
    assert (
        set(np.unique(img[..., 3])) <= {0, 255}
        and len(json.loads((out / "sheet.json").read_text())["frames"]) == 1
    )
    # frames: one palette (PICO-8, credited), the default fps as durations
    fr = {f"frames/{n}.png": sprite(s) for n, s in (("a", 1), ("b", 2))}
    many = _version(tmp_path / "b", "001_sprites", {"frames": "frames"}, fr)
    out2 = tmp_path / "b" / "002_pixelize"
    out2.mkdir()
    res = pixelize.run("run", str(many), str(out2), {"palette": "pico-8", "dither": "bayer2"})
    data = json.loads((out2 / "sheet.json").read_text())
    assert res["licenses"] == ["PICO-8 palette"] and res["metrics"]["colors"] == 16
    assert [f["duration"] for f in data["frames"]] == [83, 83] and "image" not in res["outputs"]
    # a sheet in: its tags and durations out, a palette swap
    out3 = tmp_path / "b" / "003_pixelize"
    out3.mkdir()
    data["meta"]["frameTags"] = [{"name": "idle", "from": 0, "to": 1}]
    (out2 / "sheet.json").write_text(json.dumps(data))
    (out2 / "meta.json").write_text(
        json.dumps({"version": "002_pixelize", "outputs": res["outputs"]})
    )
    res = pixelize.run(
        "run",
        str(out2),
        str(out3),
        {"scale": 1, "colors": 16, "palette_map": {"#ff004d": "#29adff"}},
    )
    again = json.loads((out3 / "sheet.json").read_text())
    assert again["meta"]["frameTags"] == [{"name": "idle", "from": 0, "to": 1}]
    assert [f["duration"] for f in again["frames"]] == [83, 83]
    px = np.asarray(Image.open(out3 / "sheet.png"))
    assert not ((px[..., :3] == (255, 0, 77)).all(-1) & (px[..., 3] > 0)).any()
    for bad in ({"colors": 1}, {"palette": "nes"}, {"dither": "floyd"}, {"outline": "red"}):
        with pytest.raises(StepError):
            pixelize.run("run", str(one), str(tmp_path / "x"), bad)
    with pytest.raises(StepError):
        pixelize.run("edit", str(one), str(tmp_path / "x"), {})


def test_key_pixelizes_one_picture_of_a_set(tmp_path):
    """M50: a concepts image set (image_<k>): `key` picks the one picture, a key it lacks is refused."""
    a, b = blow_up(sprite(1), 4, (0, 0)), blow_up(sprite(2), 4, (0, 0))
    v = _version(
        tmp_path / "a",
        "002_concepts",
        {"image_0": "image_0.png", "image_1": "image_1.png", "image": "image.png"},
        {"image_0.png": a, "image_1.png": b, "image.png": a},
    )
    out = tmp_path / "out"
    out.mkdir()
    r = pixelize.run("run", str(v), str(out), {"key": "image_1", "scale": 4})
    assert r["metrics"]["frames"] == 1 and "image" in r["outputs"]
    assert np.array_equal(
        np.asarray(Image.open(out / "image.png")), _pixel.downscale(b, 4, (0, 0), "dominant")
    )
    for bad in ("image_7", "preview", "../meta", 5):
        with pytest.raises(StepError) as e:
            pixelize.run("run", str(v), str(out), {"key": bad})
        assert e.value.code == "bad_params"


def test_a_recolour_keeps_every_pixel_and_swaps_only_the_named_colour(tmp_path):
    """M51 UI: palette "input" + palette_map on a pixelize version: nothing re-quantised, one colour swapped."""
    big = blow_up(sprite(3), 5, (0, 0))
    src = _version(tmp_path / "a", "001_upload", {"image": "image.png"}, {"image.png": big})
    first = tmp_path / "002_pixelize"
    first.mkdir()
    r = pixelize.run("run", str(src), str(first), {"scale": 5, "colors": 6})
    (first / "meta.json").write_text(
        json.dumps({"version": "002_pixelize", "outputs": r["outputs"]})
    )
    before = np.asarray(Image.open(first / "image.png"))
    old = "#{:02x}{:02x}{:02x}".format(*before[before[..., 3] > 0][0][:3])
    out = tmp_path / "003_pixelize"
    out.mkdir()
    pixelize.run(
        "run",
        str(first),
        str(out),
        {"scale": 1, "palette": "input", "palette_map": {old: "#00ff00"}},
    )
    after = np.asarray(Image.open(out / "image.png"))
    hit = (before[..., :3] == _pixel.hex_rgb(old)).all(-1) & (before[..., 3] > 0)
    assert hit.any() and (after[hit][:, :3] == [0, 255, 0]).all()
    assert np.array_equal(after[~hit], before[~hit])  # every other pixel as it was
    with pytest.raises(StepError) as e:
        pixelize.run("run", str(src), str(tmp_path), {"palette": "input"})
    assert e.value.code == "bad_params"  # an upload has no palette of its own


def test_palette_mapping_is_ciede2000():
    """2d-lab-palette: ΔE00 on Sharma's published pairs; pure blue goes to the purple of its hue, not to the navy
    that is nearer in RGB."""
    lab = lambda *x: np.array(x, np.float32)
    assert (
        abs(_pixel.delta_e00(lab(50.0, 2.6772, -79.7751), lab(50.0, 0.0, -82.7485)) - 2.0425) < 1e-3
    )
    assert (
        abs(_pixel.delta_e00(lab(50.0, 3.1571, -77.2803), lab(50.0, 0.0, -82.7485)) - 2.8615) < 1e-3
    )
    assert _pixel.delta_e00(lab(50.0, 0.0, 0.0), lab(50.0, 0.0, 0.0)) == 0
    pal = np.array([[0, 0, 128], [128, 0, 255]], np.uint8)  # navy 127 away in RGB, purple 128
    blue = np.zeros((1, 1, 4), np.uint8)
    blue[0, 0] = (0, 0, 255, 255)
    assert _pixel.apply_palette(blue, pal)[0, 0, :3].tolist() == [128, 0, 255]


def _png64(a):
    import base64
    import io

    buf = io.BytesIO()
    Image.fromarray(a, "RGBA").save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def test_edit_puts_the_editors_frames_over_the_sheet(tmp_path):
    """M56: the pixel editor saves the frames it changed; the rest, the tags and the palette stay the input's."""
    frames = {f"f{k}.png": blow_up(sprite(k), 4) for k in range(3)}
    src = _version(
        tmp_path / "a",
        "001_upload",
        {"frames": "frames"},
        {f"frames/{n}": a for n, a in frames.items()},
    )
    px = tmp_path / "a" / "002_pixelize"
    px.mkdir()
    pixelize.run("run", str(src), str(px), {"colors": 5})
    meta = json.loads((src / "meta.json").read_text()) | {"version": "002_pixelize"}
    meta["outputs"] = {
        "frames": "frames",
        "sheet": "sheet.png",
        "data": "sheet.json",
        "palette": "palette.gpl",
    }
    (px / "meta.json").write_text(json.dumps(meta))
    data = json.loads((px / "sheet.json").read_text())
    cells = _sheet.unpack(Image.open(px / "sheet.png").convert("RGBA"), data)
    name, cell = cells[1][0], np.asarray(cells[1][1]).copy()
    pal = _pixel.read_palette(px / "palette.gpl")
    y, x = np.argwhere(cell[..., 3] > 0)[0]
    other = next(c for c in pal if tuple(c) != tuple(cell[y, x, :3]))
    cell[y, x, :3] = other  # one pixel, another colour of the palette
    out = tmp_path / "a" / "003_pixelize"
    out.mkdir()
    res = pixelize.run(
        "edit", str(px), str(out), {"frames": {name: _png64(cell)}, "durations": {name: 250}}
    )
    assert res["metrics"]["edited_frames"] == 1 and res["metrics"]["changed_pixels"] == 1
    new = _sheet.unpack(
        Image.open(out / "sheet.png").convert("RGBA"), json.loads((out / "sheet.json").read_text())
    )
    assert np.array_equal(np.asarray(new[1][1]), cell)
    assert np.array_equal(np.asarray(new[0][1]), np.asarray(cells[0][1]))  # the others untouched
    assert [f["duration"] for f in json.loads((out / "sheet.json").read_text())["frames"]][1] == 250
    assert np.array_equal(_pixel.read_palette(out / "palette.gpl"), pal)
    off = cell.copy()
    off[y, x, :3] = (1, 2, 3)  # not in the palette
    wide = np.zeros((cell.shape[0], cell.shape[1] + 1, 4), np.uint8)
    for bad in (
        {"frames": {name: _png64(off)}},
        {"frames": {name: _png64(wide)}},
        {"frames": {"nope": _png64(cell)}},
        {"frames": {name: "not a png"}},
    ):
        with pytest.raises(StepError) as e:
            pixelize.run("edit", str(px), str(tmp_path / "x"), bad)
        assert e.value.code == "bad_params", list(bad["frames"])
    for bad in (
        {"frames": {name: _png64(cell)}, "durations": {name: "fast"}},
        {"tags": [{"name": "x", "from": 0, "to": 9}]},
        {"tags": [{"name": "x", "from": 0, "to": 0}, {"name": "x", "from": 1, "to": 1}]},
    ):
        with pytest.raises(StepError) as e:
            pixelize.run("edit", str(px), str(tmp_path / "x"), bad)
        assert e.value.code == "bad_params", bad


def test_edit_keeps_a_tile_a_tile_and_lets_a_sheet_without_a_palette_take_any_colour(tmp_path):
    """M56: a pixelized tile stays one; a sprites sheet (no palette.gpl) takes any colour and stays without a palette."""
    cell = np.zeros((8, 8, 4), np.uint8)
    cell[2:6, 2:6] = (10, 20, 30, 255)
    sheet, data = _sheet.pack([("f", Image.fromarray(cell, "RGBA"))], [], 100)
    for name, outputs in (
        ("t", {"sheet": "sheet.png", "data": "sheet.json", "tile": "image.png"}),
        ("s", {"sheet": "sheet.png", "data": "sheet.json"}),
    ):
        d = tmp_path / name / "010_x"
        d.mkdir(parents=True)
        sheet.save(d / "sheet.png")
        (d / "sheet.json").write_text(json.dumps(data))
        (d / "meta.json").write_text(json.dumps({"version": "010_x", "outputs": outputs}))
        new = cell.copy()
        new[0, 0] = (200, 100, 50, 255)  # a colour the sheet never had
        out = tmp_path / name / "020_pixelize"
        out.mkdir()
        res = pixelize.run("edit", str(d), str(out), {"frames": {"f": _png64(new)}})
        assert res["metrics"]["changed_pixels"] == 1
        assert ("tile" in res["outputs"]) == (name == "t") and "palette" not in res["outputs"]


def test_edit_reorders_duplicates_deletes_and_adds_frames(tmp_path):
    """M57: the editor's frame list: the order sent is the sheet's; a new name is blank unless sent, one left out is
    gone; the tags count in the new order (the input's tags are dropped when the order changes and none are sent)."""
    cells = []
    for k in range(3):
        a = np.zeros((8, 8, 4), np.uint8)
        a[k, k] = (255, 0, 77, 255)
        cells.append((f"f{k}", Image.fromarray(a, "RGBA")))
    sheet, data = _sheet.pack(
        cells,
        [{"name": "all", "from": 0, "to": 2, "direction": "forward", "repeat": "0"}],
        [100, 100, 100],
    )
    d = tmp_path / "010_pixelize"
    d.mkdir()
    sheet.save(d / "sheet.png")
    (d / "sheet.json").write_text(json.dumps(data))
    (d / "meta.json").write_text(
        json.dumps(
            {"version": "010_pixelize", "outputs": {"sheet": "sheet.png", "data": "sheet.json"}}
        )
    )
    copy = np.asarray(cells[0][1])
    out = tmp_path / "020_pixelize"
    out.mkdir()
    order = [
        "f2",
        "f0",
        "f0_copy",
        "blank",
    ]  # f1 deleted, f2 first, f0 duplicated, a blank one at the end
    tags = [{"name": "hit", "from": 0, "to": 2, "direction": "forward", "repeat": "1"}]
    res = pixelize.run(
        "edit",
        str(d),
        str(out),
        {
            "order": order,
            "frames": {"f0_copy": _png64(copy)},
            "durations": {"f0": 250},
            "tags": tags,
        },
    )
    new = json.loads((out / "sheet.json").read_text())
    assert [f["filename"] for f in new["frames"]] == order and new["meta"]["frameTags"] == tags
    assert [f["duration"] for f in new["frames"]] == [100, 250, 100, 100]
    got = dict(_sheet.unpack(Image.open(out / "sheet.png").convert("RGBA"), new))
    assert np.array_equal(np.asarray(got["f2"]), np.asarray(cells[2][1])) and np.array_equal(
        np.asarray(got["f0_copy"]), copy
    )
    assert np.asarray(got["blank"])[..., 3].max() == 0 and res["metrics"]["frames"] == 4
    out2 = tmp_path / "030_pixelize"
    out2.mkdir()
    pixelize.run("edit", str(d), str(out2), {"order": ["f1", "f0"]})
    assert (
        json.loads((out2 / "sheet.json").read_text())["meta"]["frameTags"] == []
    )  # the old tags' indices meant other frames
    for bad in (
        {"order": ["../x"]},
        {"order": [["f0"]]},
        {"order": ["f0", "F0"]},
        {"order": ["f0", "con"]},
        {"order": ["f0", "x."]},
        {"frames": {"f0": 5}},
        {"palette": [5]},
        {"order": ["f0", "f0"]},
        {"order": []},
        {"order": ["f0"], "tags": [{"name": "t", "from": 0, "to": 1}]},
        {"frames": {"f1": _png64(copy)}, "order": ["f0"]},
    ):
        with pytest.raises(StepError) as e:
            pixelize.run("edit", str(d), str(tmp_path / "x"), bad)
        assert e.value.code == "bad_params", bad


def test_edit_draws_a_sheet_from_nothing(tmp_path):
    """M57: without a parent: the size and the frames' names (and a palette, or any colour) make a blank sheet."""
    out = tmp_path / "001_pixelize"
    out.mkdir()
    res = pixelize.run(
        "edit",
        None,
        str(out),
        {"size": [16, 24], "order": ["spark_0", "spark_1"], "palette": "pico-8"},
    )
    data = json.loads((out / "sheet.json").read_text())
    assert [f["frame"]["w"] for f in data["frames"]] == [16, 16] and data["frames"][0]["frame"][
        "h"
    ] == 24
    assert len(_pixel.read_palette(out / "palette.gpl")) == 16 and res["licenses"] == [
        "PICO-8 palette"
    ]
    assert np.asarray(Image.open(out / "sheet.png"))[..., 3].max() == 0
    for bad in (
        {"order": ["a"], "palette": "pico-8"},
        {"size": [16, 16], "order": ["a"], "tags": [{"name": " ", "from": 0, "to": 0}]},
        {"size": [2, 16], "order": ["a"], "palette": "pico-8"},
        {"size": [16, 16], "order": ["a"], "palette": "nes"},
    ):
        with pytest.raises(StepError) as e:
            pixelize.run("edit", None, str(tmp_path / "y"), bad)
        assert e.value.code == "bad_params", bad
    out = tmp_path / "002_pixelize"
    out.mkdir()
    res = pixelize.run(
        "edit", None, str(out), {"size": [8, 8], "order": ["a"]}
    )  # any colour: no palette file
    assert "palette" not in res["outputs"] and res["metrics"]["colors"] is None
