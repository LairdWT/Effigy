"""Sprite sheets (research 15 §5.3): frames packed as uniform cells into sheet.png + sheet.json in Aseprite's
json-array shape (what Godot's and Unity's importers read), read back, and the preview a browser or an agent
sees (a nearest-neighbour contact sheet). Frames are PIL RGBA images."""

import math

from PIL import Image


def pack(frames: list[tuple[str, Image.Image]], tags=(), durations=100, columns: int = 0):
    """(sheet, data): cells of the largest frame, every frame on its cell's bottom centre (a sprite's feet
    stay put), `columns` per row (default: a near square), `durations` in ms (one, or one per frame)."""
    w, h = max(im.width for _, im in frames), max(im.height for _, im in frames)
    n = len(frames)
    cols = columns or math.ceil(math.sqrt(n))
    ms = list(durations) if isinstance(durations, (list, tuple)) else [int(durations)] * n
    sheet = Image.new("RGBA", (cols * w, math.ceil(n / cols) * h))
    out = []
    for i, (name, im) in enumerate(frames):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(im, (x + (w - im.width) // 2, y + h - im.height))
        out.append(
            {
                "filename": name,
                "frame": {"x": x, "y": y, "w": w, "h": h},
                "rotated": False,
                "trimmed": False,
                "spriteSourceSize": {"x": 0, "y": 0, "w": w, "h": h},
                "sourceSize": {"w": w, "h": h},
                "duration": ms[i],
            }
        )
    meta = {
        "app": "effigy",
        "version": "1",
        "image": "sheet.png",
        "format": "RGBA8888",
        "size": {"w": sheet.width, "h": sheet.height},
        "scale": "1",
        "frameTags": list(tags),
        "layers": [],
        "slices": [],
    }
    return sheet, {"frames": out, "meta": meta}


def unpack(sheet: Image.Image, data: dict) -> list[tuple[str, Image.Image]]:
    out = []
    for f in data["frames"]:
        r = f["frame"]
        out.append((f["filename"], sheet.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))))
    return out


def contact(sheet: Image.Image, size: int = 1024) -> Image.Image:
    """The sheet at the largest whole zoom that fits `size`, nearest neighbour: a 64 px sprite shows as
    64 px squares, never blurred."""
    k = max(1, size // max(sheet.size))
    return sheet.resize((sheet.width * k, sheet.height * k), Image.NEAREST)
