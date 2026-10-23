"""Bounded, normalized brush selections shared by reference and projection workers."""
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

from PIL import Image, ImageDraw

from steps._common import StepError


@dataclass(frozen=True)
class Stroke:
    erase: bool
    radius: float
    points: tuple[tuple[float, float], ...]
    polygon: bool = False


@dataclass(frozen=True)
class PaintMask:
    whole: bool
    strokes: tuple[Stroke, ...]
    revision: str | None = None
    faces: tuple[int, ...] | None = None
    preset: str | None = None


def number(value: object, low: float, high: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StepError("bad_params", f"{name} must be a number")
    if not isfinite(value) or not low <= value <= high:
        raise StepError("bad_params", f"{name} must be between {low} and {high}")
    return float(value)


def parse_mask(value: object) -> PaintMask:
    if value is None:
        return PaintMask(True, ())
    if not isinstance(value, dict) or set(value) - {"mode", "strokes", "faces"} or not {"mode", "strokes"} <= set(value):
        raise StepError("bad_params", "Paint mask needs mode and strokes")
    if value["mode"] not in ("all", "brush", "seams"):
        raise StepError("bad_params", "Paint mask mode must be all, brush or seams")
    preset = "seams" if value["mode"] == "seams" else None
    rows = value["strokes"]
    if not isinstance(rows, list) or len(rows) > 256:
        raise StepError("bad_params", "Paint mask supports at most 256 strokes")
    strokes: list[Stroke] = []
    count = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"tool", "radius", "points"}:
            raise StepError("bad_params", "Each mask stroke needs tool, radius and points")
        if row["tool"] not in ("paint", "erase", "lasso", "erase-lasso"):
            raise StepError("bad_params", "Mask tool must be paint, erase, lasso or erase-lasso")
        radius = number(row["radius"], 0.002, 0.25, "Brush radius")
        points = row["points"]
        if not isinstance(points, list) or not 1 <= len(points) <= 4096:
            raise StepError("bad_params", "Each stroke needs 1-4096 points")
        count += len(points)
        if count > 30000:
            raise StepError("bad_params", "Mask exceeds 30000 points; simplify the selection")
        parsed: list[tuple[float, float]] = []
        for point in points:
            if not isinstance(point, list) or len(point) != 2:
                raise StepError("bad_params", "A mask point needs normalized x and y")
            parsed.append((number(point[0], 0, 1, "Mask x"), number(point[1], 0, 1, "Mask y")))
        polygon = row["tool"] in ("lasso", "erase-lasso")
        if polygon and len(parsed) < 3:
            raise StepError("bad_params", "A lasso needs at least three points")
        strokes.append(Stroke(row["tool"] in ("erase", "erase-lasso"), radius, tuple(parsed), polygon))
    face = value.get("faces")
    if face is None:
        return PaintMask(value["mode"] == "all", tuple(strokes), preset=preset)
    if not isinstance(face, dict) or set(face) != {"revision", "ids"}:
        raise StepError("bad_params", "Face selection needs geometry revision and triangle IDs")
    ids, revision = face["ids"], face["revision"]
    if not isinstance(revision, str) or not 1 <= len(revision) <= 100:
        raise StepError("bad_params", "Invalid geometry revision")
    if not isinstance(ids, list) or len(ids) > 100000 or any(type(i) is not int or not 0 <= i < 2**24 - 1 for i in ids):
        raise StepError("bad_params", "Invalid triangle IDs")
    return PaintMask(value["mode"] == "all", tuple(strokes), revision, tuple(sorted(set(ids))), preset)


def mask_image(mask: PaintMask, size: int, preset: Image.Image | None = None) -> Image.Image:
    if mask.preset is not None and preset is None:
        raise StepError("bad_params", "This mask preset belongs to a seam-heal capture")
    if preset is not None and preset.size != (size, size):
        raise StepError("bad_params", "Suggested mask does not match the fixed capture")
    image = preset.convert("L").copy() if mask.preset is not None else Image.new("L", (size, size), 255 if mask.whole else 0)
    draw = ImageDraw.Draw(image)
    for stroke in mask.strokes:
        radius = stroke.radius * size
        points = [(x * size, y * size) for x, y in stroke.points]
        colour = 0 if stroke.erase else 255
        if stroke.polygon:
            draw.polygon(points, fill=colour)
            continue
        draw.line(points, fill=colour, width=max(1, round(radius * 2)))
        for x, y in points:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=colour)
    return image


def capture_mask(folder: Path, mask: PaintMask) -> Image.Image:
    """Resolve a screen selection against the immutable capture's alpha and faces."""
    import json

    import numpy as np

    from server import library

    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    if meta["step"] != "paint" or meta["params"].get("op") != "capture":
        raise StepError("bad_params", "Masked painting requires a fixed mesh capture")
    size = int(meta["metrics"]["size"])
    with Image.open(library.resolve_output(folder, "image")) as picture:
        if picture.size != (size, size):
            raise StepError("bad_params", "Capture dimensions no longer match its camera")
        foreground = np.asarray(picture.convert("RGBA"))[..., 3] == 255
    preset = None
    if mask.preset is not None:
        if "seam_mask" not in meta["outputs"]:
            raise StepError("bad_params", "This capture has no suggested seam mask; capture a heal view first")
        with Image.open(library.resolve_output(folder, "seam_mask")) as image:
            preset = image.convert("L").copy()
    selected = np.asarray(mask_image(mask, size, preset)) > 0
    selected &= foreground
    if mask.faces is not None:
        if mask.revision != meta["metrics"].get("geometry_revision"):
            raise StepError("bad_params", "Face selection belongs to different geometry; select faces again")
        if not mask.faces or max(mask.faces) >= int(meta["metrics"]["triangles"]):
            raise StepError("bad_params", "Face selection is empty or includes missing triangles")
        with Image.open(library.resolve_output(folder, "face_ids")) as picture:
            rgb = np.asarray(picture.convert("RGB")).astype(np.int64)
        ids = rgb[..., 0] + (rgb[..., 1] << 8) + (rgb[..., 2] << 16) - 1
        ys = np.arange(size) * ids.shape[0] // size
        xs = np.arange(size) * ids.shape[1] // size
        selected &= np.isin(ids[ys[:, None], xs[None, :]], mask.faces)
    if not selected.any():
        raise StepError("bad_params", "Selection contains no visible surface; paint a region or select visible faces")
    return Image.fromarray(selected.astype(np.uint8) * 255)
