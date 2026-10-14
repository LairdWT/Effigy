"""steps/sprites.py (research 15 §5.4, M52): sprite frames of the 3D character, its scale kept per asset.
The Blender part is skipped without Blender (as test_blender_ops)."""

import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from server.blender_install import blender_exe
from steps import sprites
from steps._common import StepError

FIX = Path(__file__).parent / "fixtures"
BLENDER = blender_exe()
needs_blender = pytest.mark.skipif(
    not BLENDER.is_file(), reason="no Blender (EFFIGY_BLENDER / blender_install)"
)


def _version(root: Path, name: str, glb: Path, outputs: dict, clips=None) -> Path:
    d = root / name
    d.mkdir(parents=True)
    shutil.copy(glb, d / outputs.get("rigged_anim", outputs.get("mesh")))
    if clips is not None:
        (d / "clips.json").write_text(
            json.dumps({"clips": [{"name": c} for c in clips], "fps": 24})
        )
    (d / "meta.json").write_text(json.dumps({"version": name, "outputs": outputs}))
    return d


def _anim(root: Path) -> Path:
    return _version(
        root,
        "001_anim",
        FIX / "anim.glb",
        {"rigged_anim": "rigged_anim.glb", "clips": "clips.json"},
        ["Idle", "Walk"],
    )


def test_bad_params_and_an_unknown_clip_are_refused(tmp_path):
    src = _anim(tmp_path / "a")
    for bad in (
        {"yaws": [400]},
        {"yaws": [90, 90]},
        {"yaws": []},
        {"cell": 4},
        {"fps": 0},
        {"pitch_deg": 60},
        {"shading": "toon"},
        {"supersample": 3},
        {"height_px": 2},
        {"clips": "Walk"},
        {"yaws": [True]},  # a bool is not a yaw
    ):
        with pytest.raises(StepError) as e:
            sprites.run("run", str(src), str(tmp_path / "out"), bad)
        assert e.value.code == "bad_params", bad
    with pytest.raises(StepError) as e:
        sprites.run("run", str(src), str(tmp_path / "out"), {"clips": ["Dance"]})
    assert e.value.code == "bad_params" and "Dance" in str(e.value)


@needs_blender
def test_a_clip_becomes_uniform_transparent_frames_and_the_scale_is_kept(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_BLENDER", str(BLENDER))
    asset = tmp_path / "hero"
    src = _anim(asset)
    out = asset / "002_sprites"
    out.mkdir()
    r = sprites.run("run", str(src), str(out), {"clips": ["Walk"], "height_px": 64, "cell": 32})
    data = json.loads((out / "sheet.json").read_text())
    n = r["metrics"]["frames"]
    assert n >= 4 and len(data["frames"]) == n and len(list((out / "frames").glob("*.png"))) == n
    assert [(t["name"], t["from"], t["to"]) for t in data["meta"]["frameTags"]] == [
        ("Walk", 0, n - 1)
    ]
    assert data["meta"]["frameTags"][0]["repeat"] in (
        "0",
        "1",
    )  # loops, or plays once (first pose vs last)
    cell = r["metrics"]["cell"]
    for f in sorted((out / "frames").glob("*.png")):
        a = np.asarray(Image.open(f).convert("RGBA"))
        assert a.shape[:2] == (cell, cell)
        assert set(np.unique(a[..., 3]).tolist()) <= {0, 255}  # no anti-aliasing: a binary alpha
        assert (
            a[0, 0, 3] == a[0, -1, 3] == 0 and (a[..., 3] > 0).any()
        )  # transparent around a figure
    first = json.loads((out / "camera.json").read_text())
    assert first["height_px"] == 64 and abs(first["ppm"] * first["height_m"] - 64) < 0.5

    # a later run on the same asset keeps the scale; a height given sets a new one
    again = asset / "003_sprites"
    again.mkdir()
    r2 = sprites.run("run", str(src), str(again), {"clips": ["Idle"], "yaws": [90, 270]})
    assert r2["metrics"]["scale_from"] == "earlier"
    assert json.loads((again / "camera.json").read_text())["ppm"] == first["ppm"]
    tags = json.loads((again / "sheet.json").read_text())["meta"]["frameTags"]
    assert [t["name"] for t in tags] == ["Idle_090", "Idle_270"]
    half = asset / "004_sprites"
    half.mkdir()
    sprites.run("run", str(src), str(half), {"clips": ["Idle"], "height_px": 32})
    assert abs(json.loads((half / "camera.json").read_text())["ppm"] - first["ppm"] / 2) < 1e-6


@needs_blender
def test_a_still_model_gives_one_frame_per_yaw(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_BLENDER", str(BLENDER))
    src = _version(tmp_path / "prop", "001_upload", FIX / "two_tris.glb", {"mesh": "mesh.glb"})
    out = tmp_path / "prop" / "002_sprites"
    out.mkdir()
    r = sprites.run("run", str(src), str(out), {"yaws": [0, 90], "height_px": 32, "cell": 16})
    assert r["metrics"]["frames"] == 2
    tags = json.loads((out / "sheet.json").read_text())["meta"]["frameTags"]
    assert [t["name"] for t in tags] == ["still_000", "still_090"]


def test_an_oversized_sheet_and_an_unreadable_scale_are_refused_before_rendering(tmp_path):
    """The review of M52: a sheet past 8192 x 8192 px is refused from the clips' lengths; an asset whose last
    camera.json holds no scale says so instead of a traceback."""
    src = _version(
        tmp_path / "a",
        "001_anim",
        FIX / "anim.glb",
        {"rigged_anim": "rigged_anim.glb", "clips": "clips.json"},
        ["Idle"],
    )
    (src / "clips.json").write_text(
        json.dumps({"clips": [{"name": "Idle", "seconds": 600}], "fps": 24})
    )
    with pytest.raises(StepError) as e:
        sprites.run("run", str(src), str(tmp_path / "out"), {"cell": 512})
    assert e.value.code == "bad_params" and "8192" in str(e.value)
    (src / "clips.json").write_text(
        json.dumps({"clips": [{"name": "Idle", "seconds": 1}], "fps": 24})
    )
    old = tmp_path / "a" / "002_sprites"
    old.mkdir()
    (old / "camera.json").write_text("{not json")
    with pytest.raises(StepError) as e:
        sprites.run("run", str(src), str(tmp_path / "out"), {})
    assert e.value.code == "failed" and "height_px" in str(e.value)


def test_a_fighters_moves_play_once_by_name():
    """A pack clip that ends in its start pose still plays once when it is an attack, a hit or a fall: the game waits
    for it to finish (the brawler set's jabs and hits came out looping by the pose rule alone)."""
    loops = [
        "Fighting Idle",
        "Walk",
        "Jog",
        "Defend",
        "Victory",
        "Jump_air",
        "Idle_A",
        "Idle_Sword",
        "Sword_Block",
    ]
    once = [
        "Fighting Left Jab",
        "Punch_Cross",
        "Melee_Hook",
        "Kick_Breach",
        "Jump_Start",
        "Jump_Land",
        "Hit_Head",
        "Hit_Knockback",
        "LayToIdle",
        "Death_A",
        "PickUp_Table",
        "Throw Object",
        "Sword_Regular_A",
        "Spell_Simple_Shoot",
    ]
    assert not [n for n in loops if sprites.ONCE.search(n)]
    assert not [n for n in once if not sprites.ONCE.search(n)]
