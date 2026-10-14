"""M54 seamless tiles (research 15 §5.5): the seam measure, `concepts` op tile on a stand-in pipeline (the roll, the
mended cross, the report), pixelize keeping a tile seamless, validate's item, and the Godot TileSet / Paper2D export.
CPU only; the real pipeline's run is in docs/bench/m54.md."""

import json
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from steps import _pixel, export, pixelize, validate
from steps._common import StepError


def periodic(size=256, seed=0):
    """A seamless texture: smooth noise made of whole-period waves."""
    rng = np.random.default_rng(seed)
    f = rng.normal(size=(size, size)) + 1j * rng.normal(size=(size, size))
    k = np.fft.fftfreq(size)[:, None] ** 2 + np.fft.fftfreq(size)[None, :] ** 2
    g = np.real(np.fft.ifft2(f / (k + 1e-3)))
    g = ((g - g.min()) / np.ptp(g) * 255).astype(np.uint8)
    return np.dstack([g, g // 2, 255 - g, np.full_like(g, 255)])


def blocky(cells=32, k=8, shift=(3, 5), seed=2):
    """(the tile, the tile drawn k times larger with its grid shifted round the edge by `shift` x, y): pixel art as a
    model's pixel style draws it, seamless."""
    small = np.full((cells, cells, 4), 255, np.uint8)
    small[..., :3] = np.random.default_rng(seed).integers(0, 4, (cells, cells, 1)) * 60
    big = small.repeat(k, 0).repeat(k, 1)
    return small, np.roll(big, (shift[1], shift[0]), axis=(0, 1))


def version(root, name, outputs, pictures):
    d = root / name
    d.mkdir(parents=True)
    for file, a in pictures.items():
        Image.fromarray(a).save(d / file)
    meta = {"version": name, "asset_id": "bricks", "licenses": [], "outputs": outputs}
    (d / "meta.json").write_text(json.dumps(meta))
    return d


def test_the_seam_measure_takes_any_tile():
    assert _pixel.seam_ratio(np.zeros((1, 1, 4), np.uint8)) == 0.0  # one pixel: nothing to compare
    assert _pixel.seam_ratio(np.zeros((8, 8, 4), np.uint8)) == 0.0  # flat: no step anywhere


def test_the_seam_measure_tells_a_tile_from_a_cut_piece():
    tile = periodic()
    assert _pixel.seam_ratio(tile) <= _pixel.SEAM_PASS
    assert _pixel.seam_ratio(np.roll(tile, (37, 91), axis=(0, 1))) <= _pixel.SEAM_PASS
    assert (
        _pixel.seam_ratio(periodic(512, 1)[:256, :256]) > 2
    )  # a quarter of a texture: edges that don't meet


def test_pixelize_keeps_a_tile_seamless(tmp_path):
    small, big = blocky()
    src = version(
        tmp_path, "003_concepts", {"tile": "tile.png", "image": "tile.png"}, {"tile.png": big}
    )
    out = tmp_path / "004_pixelize"
    out.mkdir()
    res = pixelize.run("run", str(src), str(out), {"colors": 4})
    got = np.asarray(Image.open(out / res["outputs"]["tile"]).convert("RGBA"))
    assert (
        np.array_equal(got, small) and res["metrics"]["scale"] == 8
    )  # the grid rolled round, not padded
    assert res["metrics"]["seam_ratio"] == round(_pixel.seam_ratio(small), 3)
    assert Image.open(out / "preview.png").size[0] % 64 == 0  # 2 × 2 tiles at a whole zoom
    out = tmp_path / "005_pixelize"
    out.mkdir()
    res = pixelize.run("run", str(src), str(out), {"height_px": 64, "colors": 4})
    assert res["metrics"]["cell"] == [64, 64] and res["metrics"]["scale"] == 4
    for bad in (
        {"height_px": 30},
        {"height_px": 512},
        {"height_px": 1},
        {"scale": 3},
        {"scale": 256},
    ):
        with pytest.raises(StepError) as e:
            pixelize.run("run", str(src), str(tmp_path / "x"), bad)
        assert e.value.code == "bad_params" and "32" in str(e.value), bad


def test_validate_checks_a_tiles_seams(tmp_path):
    good = version(tmp_path, "003_concepts", {"tile": "tile.png"}, {"tile.png": periodic()})
    cut = version(
        tmp_path, "004_concepts", {"tile": "tile.png"}, {"tile.png": periodic(512, 1)[:256, :256]}
    )
    for src, status in ((good, "pass"), (cut, "warn")):
        out = tmp_path / f"v{status}"
        out.mkdir()
        validate.run("run", str(src), str(out), {})
        items = json.loads((out / "checklist.json").read_text())["items"]
        assert items["seamless"]["status"] == status and list(items) == ["seamless"]


def test_a_tile_exports_as_a_godot_tileset_and_a_paper2d_texture(tmp_path):
    small, _ = blocky()
    src = version(
        tmp_path, "004_pixelize", {"tile": "image.png", "image": "image.png"}, {"image.png": small}
    )
    out = tmp_path / "out"
    out.mkdir()
    r = export.run("run", str(src), str(out), {"profile": "godot-2d"})
    assert sorted(r["outputs"]) == sorted(
        ["bricks.png", "bricks.tres", "README.txt", "CREDITS.txt", "LICENSES.json"]
    )
    tres = (out / "godot-2d" / "bricks.tres").read_text()
    assert '[gd_resource type="TileSet"' in tres and 'path="bricks.png"' in tres
    assert (
        "texture_region_size = Vector2i(32, 32)" in tres and "tile_size = Vector2i(32, 32)" in tres
    )
    assert "0:0/0 = 0" in tres and 'sources/0 = SubResource("TileSetAtlasSource_0")' in tres
    readme = (out / "godot-2d" / "README.txt").read_text()
    assert (
        "TileMapLayer" in readme and "scale_mode" not in readme
    )  # a smooth tile: no pixel-art settings
    pixel = version(
        tmp_path,
        "005_pixelize",
        {"tile": "image.png", "sheet": "image.png", "data": "x"},
        {"image.png": small},
    )
    export.run("run", str(pixel), str(tmp_path / "out3"), {"profile": "godot-2d"})
    assert 'scale_mode="integer"' in (tmp_path / "out3" / "godot-2d" / "README.txt").read_text()
    out2 = tmp_path / "out2"
    out2.mkdir()
    r = export.run("run", str(src), str(out2), {"profile": "unreal-2d"})
    assert sorted(r["outputs"]) == sorted(
        ["bricks.png", "README.txt", "CREDITS.txt", "LICENSES.json"]
    )
    assert "Create Tile Set" in (out2 / "unreal-2d" / "README.txt").read_text()


def test_concepts_tile_mends_the_cross_and_reports(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    diffusers = pytest.importorskip("diffusers")
    from steps import concepts

    class Part:
        def to(self, *_):
            return self

    class Pipe:
        transformer, text_encoder, vae = Part(), Part(), Part()

        @property
        def components(self):
            return {"transformer": self.transformer}

        def encode_prompt(self, texts, device, do_classifier_free_guidance):
            return [object()], None

        def __call__(
            self, prompt_embeds, height, width, num_inference_steps, guidance_scale, generator
        ):
            ramp = np.linspace(0, 255, width, dtype=np.uint8)  # a picture whose edges don't meet
            return SimpleNamespace(
                images=[Image.fromarray(np.dstack([np.tile(ramp, (height, 1))] * 3))]
            )

    seen = {}

    def inpaint(image, mask_image, prompt_embeds, height, width, strength, **kw):
        seen.update(mask=np.asarray(mask_image), strength=strength, size=image.size)
        return SimpleNamespace(images=[Image.new("RGB", (width, height), (128, 128, 128))])

    monkeypatch.setattr(concepts, "_pipeline", Pipe)
    monkeypatch.setattr(concepts, "progress", lambda *a, **k: None)
    built = []  # the inpaint pipeline gets the resident modules as they are (no from_pipe: it casts to float32)
    monkeypatch.setattr(
        diffusers, "ZImageInpaintPipeline", lambda **parts: built.append(parts) or inpaint
    )
    for bad in (
        {"prompt": "b", "size": 1000},
        {"prompt": "b", "size": 2048},
        {"prompt": "b", "mend": 0.1},
    ):
        with pytest.raises(StepError) as e:
            concepts.run("tile", None, str(tmp_path), bad)
        assert e.value.code == "bad_params"
    res = concepts.run(
        "tile", None, str(tmp_path), {"prompt": "red bricks", "size": 256, "seed": 3}
    )
    assert list(built[0]) == ["transformer"]
    mask = seen["mask"]  # the cross through the middle, an eighth of the size wide
    assert seen["size"] == (256, 256) and seen["strength"] == concepts.MEND
    assert mask[128, 0] == mask[0, 128] == 255 and mask[0, 0] == mask[100, 100] == 0
    assert mask[:, 100].sum() == 255 * 32
    rep = json.loads((tmp_path / "report.json").read_text())
    assert rep["pass"] and rep["seam_ratio"] < 1 < rep["seam_ratio_before"] and rep["band"] == 32
    assert res["outputs"]["tile"] == res["outputs"]["image"] == "tile.png"
    assert Image.open(tmp_path / "preview.png").size == (512, 512)
