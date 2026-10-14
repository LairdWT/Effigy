"""The 2D exports' files (research 15 §5.8, M53): a sprite sheet + its Aseprite json-array data → Godot 4's
`SpriteFrames` resource and an `AnimatedSprite2D` scene, Unreal Paper2D's sprite-sheet json, and the 2D checklist.
Text writers only: no engine is called here (the engine checks are in docs/bench/engine-import.md)."""

import json
import re
from collections import Counter

import numpy as np
from PIL import Image


def _tags(data: dict) -> list[tuple[str, int, int, bool]]:
    """(name, first, last, loops) per animation: the sheet's tags, or one "default" over every frame. A tag
    marked to play once (Aseprite's `repeat` "1") does not loop."""
    n = len(data["frames"])
    tags = [t for t in data["meta"].get("frameTags", []) if 0 <= t["from"] <= t["to"] < n]
    if not tags:
        return [("default", 0, n - 1, True)]
    return [(t["name"], t["from"], t["to"], str(t.get("repeat", "0")) != "1") for t in tags]


def feet_row(sheet: Image.Image, data: dict) -> int:
    """The lowest opaque row over every frame, from the cell's top: where the figure stands (a jump's frames are
    higher, never lower)."""
    a = np.asarray(sheet.convert("RGBA"))[..., 3]
    low = 0
    for f in data["frames"]:
        r = f["frame"]
        cell = a[r["y"] : r["y"] + r["h"], r["x"] : r["x"] + r["w"]]
        rows = np.flatnonzero(cell.max(1) > 0)
        if len(rows):
            low = max(low, int(rows[-1]))
    return low


def godot_sprite_frames(data: dict, sheet_file: str) -> str:
    """A Godot 4 `SpriteFrames` .tres: one AtlasTexture per frame on the sheet (a path beside the .tres), one
    animation per tag. Its speed is the most common frame's fps; a longer frame keeps its time as a relative
    `duration` (Aseprite's per-frame milliseconds, as Godot's own Aseprite importers map them)."""
    frames = data["frames"]
    lines = [
        f'[gd_resource type="SpriteFrames" load_steps={len(frames) + 2} format=3]',
        "",
        f'[ext_resource type="Texture2D" path="{sheet_file}" id="1_sheet"]',
        "",
    ]
    for i, f in enumerate(frames):
        r = f["frame"]
        lines += [
            f'[sub_resource type="AtlasTexture" id="AtlasTexture_{i}"]',
            'atlas = ExtResource("1_sheet")',
            f"region = Rect2({r['x']}, {r['y']}, {r['w']}, {r['h']})",
            "",
        ]
    anims = []
    for name, a, b, loops in _tags(data):
        ms = [max(1, int(frames[k]["duration"])) for k in range(a, b + 1)]
        base = Counter(ms).most_common(1)[0][0]
        fps = 1000 / base
        fps = round(fps) if abs(fps - round(fps)) < 0.1 else fps  # 83 ms is 12 fps, not 12.05
        entries = ",\n".join(
            f'{{\n"duration": {ms[k - a] / base:.4g},\n"texture": SubResource("AtlasTexture_{k}")\n}}'
            for k in range(a, b + 1)
        )
        anims.append(
            f'{{\n"frames": [{entries}],\n"loop": {"true" if loops else "false"},\n'
            f'"name": &"{_gd(name)}",\n"speed": {fps:.4g}\n}}'
        )
    lines += ["[resource]", f"animations = [{', '.join(anims)}]", ""]
    return "\n".join(lines)


def godot_scene(node: str, frames_file: str, data: dict, feet: int) -> str:
    """An `AnimatedSprite2D` scene: nearest filtering, the first animation playing, and the figure standing on the
    node's origin (its feet at y 0, its middle at x 0), so placing it in a level puts it on the ground."""
    first = _tags(data)[0][0]
    w = data["frames"][0]["frame"]["w"]
    return "\n".join(
        [
            "[gd_scene load_steps=2 format=3]",
            "",
            f'[ext_resource type="SpriteFrames" path="{frames_file}" id="1_frames"]',
            "",
            f'[node name="{_node(node)}" type="AnimatedSprite2D"]',
            "texture_filter = 1",
            'sprite_frames = ExtResource("1_frames")',
            f'animation = &"{_gd(first)}"',
            f'autoplay = "{_gd(first)}"',
            "centered = false",
            f"offset = Vector2({-(w // 2)}, {-(feet + 1)})",
            "",
        ]
    )


def paper2d(data: dict, sheet_file: str) -> str:
    """Unreal Paper2D's sprite sheet (TexturePacker's json-hash, `.paper2dsprites`): one sprite per frame, named
    `<animation>_<NN>` so Paper2D's Create Flipbooks groups them, the pivot at the feet (bottom centre)."""
    names = {}
    for name, a, b, _ in _tags(data):
        for k in range(a, b + 1):
            names.setdefault(k, f"{re.sub(r'[^A-Za-z0-9_]+', '_', name)}_{k - a:02d}")
    out = {}
    for k, f in enumerate(data["frames"]):
        r = f["frame"]
        out[names.get(k, f"frame_{k:03d}")] = {
            "frame": {"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]},
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": r["w"], "h": r["h"]},
            "sourceSize": {"w": r["w"], "h": r["h"]},
            "pivot": {"x": 0.5, "y": 1.0},
        }
    meta = data["meta"]
    return json.dumps(
        {
            "frames": out,
            "meta": {
                "app": "https://github.com/SifuInTheShell/Effigy",
                "version": "1.0",
                "image": sheet_file,
                "format": "RGBA8888",
                "size": meta.get("size", {}),
                "scale": "1",
            },
        },
        indent=1,
    )


def godot_tileset(tile_file: str, w: int, h: int) -> str:
    """A Godot 4 `TileSet` .tres holding a seamless tile (M54) as its one atlas tile: a TileMapLayer paints with
    it. ponytail: one tile per TileSet; several tiles in one atlas when a stage needs them."""
    return "\n".join(
        [
            '[gd_resource type="TileSet" load_steps=3 format=3]',
            "",
            f'[ext_resource type="Texture2D" path="{tile_file}" id="1_tile"]',
            "",
            '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_0"]',
            'texture = ExtResource("1_tile")',
            f"texture_region_size = Vector2i({w}, {h})",
            "0:0/0 = 0",
            "",
            "[resource]",
            f"tile_size = Vector2i({w}, {h})",
            'sources/0 = SubResource("TileSetAtlasSource_0")',
            "",
        ]
    )


def godot_parallax(node: str, layers: list[dict]) -> str:
    """A Godot 4.3+ scene of parallax layers (M55): one `Parallax2D` per layer, far to near, each moving at its
    `scroll_scale` of the camera across and with it up and down (a jump never opens a gap under a far layer), holding a
    `Sprite2D` with the layer's picture from its top left."""
    lines = [f"[gd_scene load_steps={len(layers) + 1} format=3]", ""]
    for k, d in enumerate(layers):
        lines.append(f'[ext_resource type="Texture2D" path="{d["file"]}" id="{k + 1}_layer"]')
    lines += ["", f'[node name="{_node(node)}" type="Node2D"]', ""]
    for k, d in enumerate(layers):
        lines += [
            f'[node name="Layer{k}" type="Parallax2D" parent="."]',
            f"scroll_scale = Vector2({d['scroll_scale']:g}, 1)",
            "",
            f'[node name="Sprite2D" type="Sprite2D" parent="Layer{k}"]',
            f'texture = ExtResource("{k + 1}_layer")',
            "centered = false",
            "",
        ]
    return "\n".join(lines)


GODOT_LAYERS_README = """{name}: parallax layers for Godot 4.3+ (Effigy's godot-2d export)

Copy this folder into your project and add parallax.tscn to your level, behind everything else. Each layer is a
Parallax2D that follows the active Camera2D at its own speed, far to near: {speeds}. The pictures are {w} x {h} px:
scale the scene's root to your game's view (a 360 px high view: {fit}).
"""

UNREAL_LAYERS_README = """{name}: parallax layers for Unreal's Paper2D (Effigy's unreal-2d export)

Import the layer pictures, far to near: {files}. Make a sprite of each, place them one behind the other, and move
each with the camera at its speed: {speeds} (1 moves with the camera's view, 0.05 stays nearly still).
"""


PIXEL_SETTINGS = """For crisp pixels, set in Project Settings (or project.godot):

[display]
window/size/viewport_width=640
window/size/viewport_height=360
window/size/window_width_override=1280
window/size/window_height_override=720
window/stretch/mode="viewport"
window/stretch/aspect="keep"
window/stretch/scale_mode="integer"

[rendering]
textures/canvas_textures/default_texture_filter=0
2d/snap/snap_2d_transforms_to_pixel=true
"""

GODOT_README = (
    """{name}: a sprite sheet for Godot 4 (Effigy's godot-2d export)

Copy this folder into your project. {name}.tscn is an AnimatedSprite2D standing on its origin (its feet at y 0):
drop it into a scene, or use {name}.tres (SpriteFrames) on your own AnimatedSprite2D. The animations: {anims}.

"""
    + PIXEL_SETTINGS
    + """
The scene already filters its texture by Nearest; the settings above do it for everything and scale the game by
whole numbers. sheet.json is the same sheet in Aseprite's json-array form, for other tools.
"""
)

GODOT_TILE_README = """{name}: a seamless {w} x {h} tile for Godot 4 (Effigy's godot-2d export)

Copy this folder into your project. Add a TileMapLayer, set its Tile Set to {name}.tres, pick the tile in the
TileMap panel and paint: the tile repeats with no visible edge. {name}.png is the tile on its own.
"""

# a pixel-art tile's README goes on with the pixel-perfect settings; a smooth one's does not need them
GODOT_PIXEL_TILE = (
    "\n"
    + PIXEL_SETTINGS
    + """
They filter every texture by Nearest (the tile's too) and scale the game by whole numbers.
"""
)

UNREAL_TILE_README = """{name}: a seamless {w} x {h} tile for Unreal's Paper2D (Effigy's unreal-2d export)

Enable the Paper2D plugin and import {name}.png. For crisp pixels set its Texture Group to 2D Pixels (unfiltered)
and Compression to UserInterface2D. Right-click it, Sprite Actions, Create Tile Set (tile size {w} x {h}), then
Create Tile Map from the tile set and paint: the tile repeats with no visible edge.
"""

UNREAL_README = """{name}: a sprite sheet for Unreal's Paper2D (Effigy's unreal-2d export)

Enable the Paper2D plugin, then import {name}.paper2dsprites (with {name}.png beside it): Unreal makes a Sprite
Sheet, the texture and one sprite per frame, named <animation>_<frame>, pivot at the feet. Select the sprites of
one animation and choose Create Flipbook. The animations: {anims}; play them at {fps} frames per second.
For crisp pixels set the texture's Texture Group to 2D Pixels (unfiltered) and Compression to UserInterface2D.
"""


def readme(template: str, name: str, data: dict) -> str:
    tags = _tags(data)
    fps = round(1000 / max(1, int(data["frames"][0]["duration"])))
    return template.format(name=name, anims=", ".join(t[0] for t in tags), fps=fps)


def _gd(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _node(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_") or "Sprite"


def checklist(sheet: Image.Image, data: dict, palette_max: int = 32) -> dict:
    """The 2D checklist (§3.2): uniform cells, a hard alpha, the colours, stray pixels, the sheet's size, the
    animations. pass | warn | fail with its number, as the mesh checklist."""
    a = np.asarray(sheet.convert("RGBA"))
    frames = data["frames"]
    sizes = {(f["frame"]["w"], f["frame"]["h"]) for f in frames}
    alpha = a[..., 3]
    soft = int(((alpha > 0) & (alpha < 255)).sum())
    opaque = a[alpha > 0][:, :3]
    colors = len(np.unique(opaque, axis=0)) if len(opaque) else 0
    stray = 0
    for f in frames:  # an opaque pixel with no opaque neighbour (4-connected): a speck
        r = f["frame"]
        m = alpha[r["y"] : r["y"] + r["h"], r["x"] : r["x"] + r["w"]] > 0
        p = np.pad(m, 1)
        alone = m & ~(p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:])
        stray += int(alone.sum())
    h, w = alpha.shape
    bad_tags = [
        t.get("name")
        for t in data["meta"].get("frameTags", [])
        if not 0 <= t["from"] <= t["to"] < len(frames)
    ]
    items = {
        "uniform_cells": ("pass" if len(sizes) == 1 else "fail", len(sizes)),
        "hard_alpha": ("pass" if soft == 0 else "warn", soft),
        "palette": ("pass" if colors <= palette_max else "warn", colors),
        "stray_pixels": ("pass" if stray == 0 else "warn", stray),
        "sheet_size": ("pass" if max(w, h) <= 4096 else "warn", f"{w} × {h}"),
        "animations": ("pass" if not bad_tags else "fail", len(_tags(data))),
    }
    return {name: {"status": s, "value": v} for name, (s, v) in items.items()}
