"""M53: a sprite sheet exported for Godot 4 (SpriteFrames + an AnimatedSprite2D scene) and Unreal's Paper2D, and its
2D checklist (steps/_engine2d.py, steps/export.py, steps/validate.py). The engines' own import is in
docs/bench/engine-import.md (Godot 4.7.1 headless)."""

import json
import re

import numpy as np
import pytest
from PIL import Image

from steps import _engine2d, _sheet, export, validate
from steps._common import StepError


def _sheet_version(root, name="010_pixelize", soft=False, speck=False):
    """A 4-frame sheet: Walk (3 frames, looping) and Punch (1 frame held twice as long, played once); a figure
    standing on row 13 of a 16 px cell."""
    frames = []
    for k in range(4):
        a = np.zeros((16, 16, 4), np.uint8)
        a[4:14, 6:10] = (200, 40, 40, 255)  # the body: rows 4-13
        a[4 + k % 2, 10] = (20, 20, 20, 255)  # a fist that moves
        if soft and k == 0:
            a[5, 5] = (200, 40, 40, 128)
        if speck and k == 1:
            a[1, 1] = (20, 20, 20, 255)
        frames.append((f"f{k}", Image.fromarray(a, "RGBA")))
    tags = [
        {"name": "Walk", "from": 0, "to": 2, "direction": "forward", "repeat": "0"},
        {"name": "Punch", "from": 3, "to": 3, "direction": "forward", "repeat": "1"},
    ]
    sheet, data = _sheet.pack(frames, tags, [83, 83, 83, 166])
    d = root / name
    d.mkdir(parents=True)
    sheet.save(d / "sheet.png")
    (d / "sheet.json").write_text(json.dumps(data))
    (d / "meta.json").write_text(
        json.dumps(
            {
                "version": name,
                "asset_id": "hero",
                "licenses": [],
                "outputs": {"sheet": "sheet.png", "data": "sheet.json"},
            }
        )
    )
    return d, sheet, data


def test_godot_sprite_frames_and_scene(tmp_path):
    _, sheet, data = _sheet_version(tmp_path)
    tres = _engine2d.godot_sprite_frames(data, "sheet.png")
    assert tres.startswith('[gd_resource type="SpriteFrames" load_steps=6 format=3]')
    assert tres.count('[sub_resource type="AtlasTexture"') == 4 and 'path="sheet.png"' in tres
    walk, punch = re.findall(r'"loop": (\w+),\n"name": &"(\w+)",\n"speed": ([\d.]+)', tres)
    assert walk == ("true", "Walk", "12") and punch == (
        "false",
        "Punch",
        "6",
    )  # 83 ms is 12 fps; the punch is held
    assert "region = Rect2(16, 0, 16, 16)" in tres
    feet = _engine2d.feet_row(sheet, data)
    assert feet == 13
    scene = _engine2d.godot_scene("my hero!", "hero.tres", data, feet)
    assert '[node name="my_hero" type="AnimatedSprite2D"]' in scene
    assert (
        "offset = Vector2(-8, -14)" in scene
        and 'autoplay = "Walk"' in scene
        and "texture_filter = 1" in scene
    )


def test_paper2d_names_frames_by_animation_with_the_pivot_at_the_feet(tmp_path):
    _, _, data = _sheet_version(tmp_path)
    p = json.loads(_engine2d.paper2d(data, "hero.png"))
    assert list(p["frames"]) == ["Walk_00", "Walk_01", "Walk_02", "Punch_00"]
    assert p["frames"]["Walk_01"]["frame"] == {"x": 16, "y": 0, "w": 16, "h": 16}
    assert (
        p["frames"]["Punch_00"]["pivot"] == {"x": 0.5, "y": 1.0}
        and p["meta"]["image"] == "hero.png"
    )


def test_export_writes_the_2d_profiles_and_refuses_the_wrong_kind(tmp_path):
    src, _, _ = _sheet_version(tmp_path / "a")
    out = tmp_path / "out"
    out.mkdir()
    r = export.run("run", str(src), str(out), {"profile": "godot-2d"})
    assert sorted(r["outputs"]) == sorted(
        [
            "sheet.png",
            "sheet.json",
            "hero.tres",
            "hero.tscn",
            "README.txt",
            "CREDITS.txt",
            "LICENSES.json",
        ]
    )
    assert json.loads((out / "godot-2d" / "sheet.json").read_text())["meta"]["image"] == "sheet.png"
    assert 'scale_mode="integer"' in (out / "godot-2d" / "README.txt").read_text()
    out2 = tmp_path / "out2"
    out2.mkdir()
    r = export.run("run", str(src), str(out2), {"profile": "unreal-2d"})
    assert sorted(r["outputs"]) == sorted(
        ["hero.png", "hero.paper2dsprites", "README.txt", "CREDITS.txt", "LICENSES.json"]
    )
    with pytest.raises(StepError) as e:
        export.run(
            "run", str(src), str(tmp_path / "x"), {"profile": "godot"}
        )  # a 3D profile on a sheet
    assert e.value.code == "missing_input"
    mesh = tmp_path / "b"
    mesh.mkdir()
    (mesh / "meta.json").write_text(
        json.dumps(
            {
                "version": "010_bake",
                "asset_id": "crate",
                "licenses": [],
                "outputs": {"mesh": "mesh.glb"},
            }
        )
    )
    with pytest.raises(StepError) as e:
        export.run("run", str(mesh), str(tmp_path / "y"), {"profile": "godot-2d"})
    assert e.value.code == "missing_input" and "sprite sheet" in str(e.value)


def test_the_2d_checklist(tmp_path):
    clean, _, _ = _sheet_version(tmp_path / "a")
    out = tmp_path / "out"
    out.mkdir()
    r = validate.run("run", str(clean), str(out), {})
    items = json.loads((out / "checklist.json").read_text())["items"]
    assert r["metrics"]["fail"] == 0
    assert {k: v["status"] for k, v in items.items()} == {
        "uniform_cells": "pass",
        "hard_alpha": "pass",
        "palette": "pass",
        "stray_pixels": "pass",
        "sheet_size": "pass",
        "animations": "pass",
    }
    assert items["palette"]["value"] == 2 and items["animations"]["value"] == 2
    rough, _, _ = _sheet_version(tmp_path / "b", soft=True, speck=True)
    out2 = tmp_path / "out2"
    out2.mkdir()
    validate.run("run", str(rough), str(out2), {})
    items = json.loads((out2 / "checklist.json").read_text())["items"]
    assert items["hard_alpha"] == {"status": "warn", "value": 1}
    assert items["stray_pixels"] == {"status": "warn", "value": 1}
