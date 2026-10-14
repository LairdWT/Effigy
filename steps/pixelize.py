"""Pixel art from a picture or a set of frames (research 15 §5.3, M51): one pixel grid, one palette and a binary
alpha over every frame; the frames, sheet.png + sheet.json for the engine, palette.gpl, preview.png, report.json.

Input: a version with `image` (a picture, a cut-out), `image_<k>` (an image set), a `frames` folder or a
`sheet` + `data` (sprites, an earlier pixelize: its tags and durations are kept). Params:
  key: one picture of the input (an output key such as "image_2") instead of all of them
  scale: "auto" (default: the grid the picture was drawn on, 1 when there is none) | int >= 1 (output pixel = scale×scale input pixels)
  height_px: int, instead of scale: the subject's height (its alpha) in output pixels (a sprite from a render)
  method: "dominant" (default, the cell's most frequent colour: hard edges) | "median" (renders, photos)
  alpha_cut: 0..1 (default 0.5): the alpha threshold; the output alpha is 0 or 255
  colors: 2..256 (default 16): one palette over all frames; or palette: a bundled name ("pico-8"), a .gpl/.hex/.pal path
    or "input" (the input version's own palette.gpl: a recolour of pixel art with palette_map re-quantises nothing)
  dither: "none" (default) | "bayer2" | "bayer4" (ordered: still across frames)
  outline: "#rrggbb" | "darkest" (the palette's darkest colour): a 1-px outline around the alpha
  palette_map: {"#rrggbb": "#rrggbb"}: exact recolours after everything (an enemy variant), nothing re-quantised
  fps: default 12: the frame duration of frames that carry none
Outputs: frames/<name>.png, sheet.png, sheet.json (Aseprite json-array), palette.gpl, preview.png (whole pixels),
report.json {scale, offset, colors, frames, cell, alpha_fringe}; image.png too for a single picture.
A seamless tile (an input with `tile`, M54) stays one: its pixel size divides the tile's (height_px is then the tile's
size in pixels), its grid starts at the edge (rolled round, never padded), and the output keeps `tile` (= image.png),
a 2 × 2 preview and report.seam_ratio.
op edit (M56, the in-app pixel editor): the frames it changed, as base64 PNGs, over the input sheet's (see _edit); the
same outputs, report {edited_frames, changed_pixels, colors, frames, cell}. A colour outside the palette is refused.
"""

import base64
import binascii
import io
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

from steps import _pixel, _sheet
from steps._common import StepError, main, progress
from steps._image import subject_bbox

PALETTE_ROWS = {"pico-8": "PICO-8 palette"}  # bundled palettes → their licenses.yaml row
METHODS, DITHERS = ("dominant", "median"), ("none", "bayer2", "bayer4")


def _inputs(in_dir: Path, key: str | None = None):
    """[(name, RGBA array)], the tags and the durations (ms, or None) of the input version."""
    meta = json.loads((in_dir / "meta.json").read_text(encoding="utf-8"))
    outs, tags, ms = meta.get("outputs", {}), [], None
    if key is not None:
        if not re.fullmatch(r"image(_\d+)?", key) or key not in outs:
            raise StepError("bad_params", f"key {key!r}: not one of {meta['version']}'s pictures")
        frames = [("image", Image.open(in_dir / outs[key]).convert("RGBA"))]
    elif "sheet" in outs and "data" in outs:
        data = json.loads((in_dir / outs["data"]).read_text(encoding="utf-8"))
        frames = _sheet.unpack(Image.open(in_dir / outs["sheet"]).convert("RGBA"), data)
        tags, ms = data["meta"].get("frameTags", []), [f["duration"] for f in data["frames"]]
    elif "frames" in outs:
        files = sorted((in_dir / outs["frames"]).glob("*.png"))
        frames = [(p.stem, Image.open(p).convert("RGBA")) for p in files]
    else:
        keys = sorted(k for k in outs if re.fullmatch(r"image_\d+", k)) or ["image"] * (
            "image" in outs
        )
        frames = [(k, Image.open(in_dir / outs[k]).convert("RGBA")) for k in keys]
    if not frames:
        raise StepError(
            "missing_input", f"{meta['version']}: no picture, frames or sheet to pixelize"
        )
    return [(n, np.asarray(im)) for n, im in frames], tags, ms


def _params(params: dict) -> dict:
    p = {
        "scale": params.get("scale", "auto"),
        "height_px": params.get("height_px"),
        "method": params.get("method", "dominant"),
        "alpha_cut": float(params.get("alpha_cut", 0.5)),
        "colors": int(params.get("colors", 16)),
        "palette": params.get("palette"),
        "dither": params.get("dither", "none"),
        "outline": params.get("outline"),
        "palette_map": params.get("palette_map") or {},
        "fps": float(params.get("fps", 12)),
        "key": params.get("key"),
    }
    ok = (
        (p["scale"] == "auto" or (isinstance(p["scale"], int) and p["scale"] >= 1))
        and (p["height_px"] is None or (isinstance(p["height_px"], int) and p["height_px"] > 0))
        and p["method"] in METHODS
        and 0 <= p["alpha_cut"] <= 1
        and 2 <= p["colors"] <= 256
        and p["dither"] in DITHERS
        and p["fps"] > 0
        and isinstance(p["palette_map"], dict)
        and (p["key"] is None or isinstance(p["key"], str))
    )
    if not ok:
        raise StepError("bad_params", f"see the pixelize docstring: {params}")
    return p


def _palette(frames: list[np.ndarray], p: dict, in_dir: Path) -> tuple[np.ndarray, list[str]]:
    if not p["palette"]:
        return _pixel.make_palette(frames, p["colors"]), []
    name = str(p["palette"])
    path = _pixel.PALETTES / f"{name}.gpl" if name in PALETTE_ROWS else Path(name)
    if (
        name == "input"
    ):  # a recolour: the colours the input was quantised to, so nothing moves but the swaps
        own = json.loads((in_dir / "meta.json").read_text(encoding="utf-8")).get("outputs", {})
        if "palette" not in own:
            raise StepError("bad_params", "palette 'input': the input version has no palette")
        path = in_dir / own["palette"]
    if not path.is_file():
        raise StepError(
            "bad_params", f"palette {name!r}: not {sorted(PALETTE_ROWS)} or a palette file"
        )
    try:
        return _pixel.read_palette(path), [PALETTE_ROWS[name]] if name in PALETTE_ROWS else []
    except ValueError as e:
        raise StepError("bad_params", str(e)) from None


def _tile_grid(arrays: list[np.ndarray], p: dict) -> tuple[list[np.ndarray], int]:
    """A tile's frames rolled so the pixel grid starts at its edge, and a pixel size that divides it: a cell cut
    in two by the wrap, or padded, would be a seam."""
    size = arrays[0].shape[0]
    divisors = [d for d in range(1, size + 1) if size % d == 0]
    sizes = ", ".join(str(size // d) for d in divisors if 8 <= size // d <= 256)
    if p["height_px"] or p["scale"] != "auto":
        cells = p["height_px"] or size // p["scale"]  # the tile's size in output pixels
        if not 8 <= cells <= min(size, 256) or size % cells:
            raise StepError(
                "bad_params", f"a {size} px tile splits into whole pixels as {sizes} px tiles"
            )
        return arrays, size // cells
    k, (x, y) = _pixel.grid(arrays)
    # the offset was found at the drawn period: after the snap it can sit up to a cell off, never across the wrap
    k = min(divisors, key=lambda d: (abs(d - k), d))
    return [np.roll(a, (-y, -x), axis=(0, 1)) for a in arrays], k


def run(op, in_dir, out_dir, params):
    if op == "edit":  # without a parent: a sheet drawn from nothing (M57)
        return _edit(Path(in_dir) if in_dir else None, Path(out_dir), params)
    if op != "run":
        raise StepError(
            "bad_params", f"op {op!r}: run (pixel art) or edit (the pixel editor's frames)"
        )
    if not in_dir:
        raise StepError("missing_input", "pixelize needs a parent version with a picture or frames")
    p = _params(params)
    frames, tags, ms = _inputs(Path(in_dir), p["key"])
    arrays = [a for _, a in frames]
    outs_in = json.loads((Path(in_dir) / "meta.json").read_text(encoding="utf-8"))["outputs"]
    tile = "tile" in outs_in and len(arrays) == 1 and arrays[0].shape[0] == arrays[0].shape[1]
    progress(0.1, "grid")
    if tile:
        arrays, period = _tile_grid(arrays, p)
        offset = (0, 0)
    elif p["height_px"]:
        try:
            _, y0, _, y1 = subject_bbox(arrays[0][..., 3] / 255)
        except ValueError as e:
            raise StepError("failed", str(e)) from None
        period, offset = max(1, round((y1 - y0 + 1) / p["height_px"])), (0, 0)
    elif p["scale"] == "auto":
        period, offset = _pixel.grid(arrays)
    else:
        period, offset = p["scale"], (0, 0)
    small = [_pixel.downscale(a, period, offset, p["method"]) for a in arrays]
    fringe = sum(int(((a[..., 3] > 0) & (a[..., 3] < 255)).sum()) for a in small)
    small = [_pixel.cut_alpha(a, p["alpha_cut"]) for a in small]
    progress(0.5, "palette")
    pal, licenses = _palette(small, p, Path(in_dir))
    small = [_pixel.apply_palette(a, pal, p["dither"]) for a in small]
    if p["outline"]:
        try:
            color = (
                pal[pal.sum(-1).argmin()]
                if p["outline"] == "darkest"
                else _pixel.hex_rgb(p["outline"])
            )
            small = [_pixel.outline(a, color) for a in small]
            small = [_pixel.remap(a, p["palette_map"]) for a in small]
        except ValueError as e:
            raise StepError("bad_params", str(e)) from None
    elif p["palette_map"]:
        try:
            small = [_pixel.remap(a, p["palette_map"]) for a in small]
        except ValueError as e:
            raise StepError("bad_params", str(e)) from None
    progress(0.8, "sheet")
    out = Path(out_dir)
    names = [n for n, _ in frames]
    outputs, data = _write(out, names, small, tags, ms or round(1000 / p["fps"]), pal, tile)
    pixels = sum(a.shape[0] * a.shape[1] for a in small) or 1
    report = {
        "scale": int(period),
        "offset": [int(offset[0]), int(offset[1])],
        "colors": len(pal),
        "frames": len(small),
        "cell": [data["frames"][0]["frame"]["w"], data["frames"][0]["frame"]["h"]],
        "alpha_fringe": round(fringe / pixels, 4),
    } | ({"seam_ratio": round(_pixel.seam_ratio(small[0]), 3)} if tile else {})
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"outputs": outputs, "metrics": report, "licenses": licenses}


def _write(out: Path, names, arrays, tags, ms, pal, tile: bool) -> tuple[dict, dict]:
    """The frames, the sheet and its data, the palette (when there is one), the preview: (outputs, sheet data)."""
    (out / "frames").mkdir(exist_ok=True)
    ims = [(n, Image.fromarray(a, "RGBA")) for n, a in zip(names, arrays)]
    for n, im in ims:
        im.save(out / "frames" / f"{n}.png")
    sheet, data = _sheet.pack(ims, tags, ms)
    sheet.save(out / "sheet.png")
    (out / "sheet.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    _sheet.contact(Image.fromarray(np.tile(arrays[0], (2, 2, 1))) if tile else sheet).save(
        out / "preview.png"
    )
    outputs = {"frames": "frames", "sheet": "sheet.png", "data": "sheet.json"}
    if pal is not None:
        _pixel.write_gpl(pal, out / "palette.gpl", out.parent.name)
        outputs["palette"] = "palette.gpl"
    outputs |= {"preview": "preview.png", "report": "report.json"}
    if len(ims) == 1:
        ims[0][1].save(out / "image.png")
        outputs["image"] = "image.png"
    if tile:
        outputs["tile"] = "image.png"
    return outputs, data


def _colours(a: np.ndarray) -> np.ndarray:
    """The opaque pixels' colours as one int each (0xRRGGBB)."""
    rgb = a[a[..., 3] > 0][:, :3].astype(np.int64)
    return (rgb[:, 0] << 16) | (rgb[:, 1] << 8) | rgb[:, 2]


# a new frame's name is its file's (frames/<name>.png): nothing that leaves frames/, no end Windows strips (a dot or
# a space), no device name (CON, NUL, COM1...)
NAME = re.compile(
    r"(?!(?i:con|prn|aux|nul|com\d|lpt\d)(?:\.|$))[A-Za-z0-9_](?:[A-Za-z0-9_ .-]{0,62}[A-Za-z0-9_-])?"
)


def _edit_palette(
    params: dict, in_dir: Path | None, outs: dict
) -> tuple[np.ndarray | None, list[str]]:
    """The palette an edit keeps to: sent (colours or a bundled name), else the input's, else none (any colour)."""
    sent = params.get("palette")
    try:
        if isinstance(sent, str):
            if sent not in PALETTE_ROWS:
                raise ValueError(f"{sent!r} is not one of {sorted(PALETTE_ROWS)}")
            return _pixel.read_palette(_pixel.PALETTES / f"{sent}.gpl"), [PALETTE_ROWS[sent]]
        if sent is not None:
            if not (isinstance(sent, list) and all(isinstance(c, str) for c in sent)):
                raise ValueError("is a bundled name or a list of #rrggbb")
            return np.array([_pixel.hex_rgb(c) for c in sent], np.uint8).reshape(-1, 3), []
        if in_dir is not None and "palette" in outs:
            return _pixel.read_palette(in_dir / outs["palette"]), []
        return None, []  # sprites: drawn in any colour
    except (ValueError, TypeError) as e:
        raise StepError("bad_params", f"edit: palette {e}") from None


def _edit(in_dir: Path | None, out: Path, params: dict) -> dict:
    """op edit (M56, M57): the in-app editor's sheet. params:
      frames {name: base64 PNG}: the frames that changed or are new, only those (job params land in meta.json)
      order [name, ...]: the sheet's frames in order (default the input's). An input frame keeps its pixels unless
        sent, a new name without pixels is a blank frame, a name left out is deleted.
      durations {name: ms}; tags [{name, from, to, direction, repeat}] with from/to indices into order (default the
        input's, when the order is the input's)
      palette ["#rrggbb", ...] or a bundled name ("pico-8"); default the input's palette.gpl, else any colour (and no
        palette file: a sheet in any colour stays one)
      size [w, h] (4-512): a sheet drawn from nothing, without a parent (then order is needed too)
    Every frame has the cell size. An edited frame's alpha is cut at 0.5 like pixel art's (a sprites sheet is rendered
    without anti-aliasing, so nothing is lost there), and every opaque pixel in it is a palette colour."""
    edits, durations = params.get("frames") or {}, params.get("durations") or {}
    if not isinstance(edits, dict) or not isinstance(durations, dict):
        raise StepError("bad_params", "edit: frames and durations are {name: ...}")
    if in_dir is None:  # drawn from nothing
        size, order = params.get("size"), params.get("order")
        ok = (
            isinstance(size, list)
            and len(size) == 2
            and all(isinstance(x, int) and 4 <= x <= 512 for x in size)
        )
        if not ok:
            raise StepError("bad_params", "edit without a parent: size [w, h] (4-512) and order")
        (w, h), old, was_ms, tags0, outs, default_ms = size, {}, {}, [], {}, 100
    else:
        meta = json.loads((in_dir / "meta.json").read_text(encoding="utf-8"))
        outs = meta["outputs"]
        if not ("sheet" in outs and "data" in outs):
            raise StepError("missing_input", f"{meta['version']}: edit needs a sprite sheet")
        data = json.loads((in_dir / outs["data"]).read_text(encoding="utf-8"))
        frames = _sheet.unpack(Image.open(in_dir / outs["sheet"]).convert("RGBA"), data)
        old = {n: np.asarray(im) for n, im in frames}
        w, h = frames[0][1].size
        was_ms = {n: f["duration"] for (n, _), f in zip(frames, data["frames"])}
        order = params.get("order", [n for n, _ in frames])
        same = order == [n for n, _ in frames]
        tags0, default_ms = (
            data["meta"].get("frameTags", []) if same else [],
            data["frames"][0]["duration"],
        )
    # the input's names are files already; a new one must make a good file name. Distinct ignoring case: a Windows
    # folder holds one of "a" and "A"
    names_ok = (
        isinstance(order, list)
        and 1 <= len(order) <= 256
        and all(isinstance(n, str) and (n in old or NAME.fullmatch(n)) for n in order)
        and len({n.lower() for n in order}) == len(order)
    )
    if not names_ok:
        raise StepError(
            "bad_params",
            "edit: order is 1-256 distinct frame names (a new one: letters, digits, _ . - and spaces, ending in a"
            " letter, digit, _ or -)",
        )
    if not all(isinstance(v, str) for v in edits.values()):
        raise StepError("bad_params", "edit: frames are {name: base64 PNG}")
    if unknown := sorted((set(edits) | set(durations)) - set(order)):
        raise StepError("bad_params", f"edit: frames {unknown} are not in the order")
    pal, licenses = _edit_palette(params, in_dir, outs)
    allowed = None if pal is None else _colours(np.dstack([pal[None], np.full((1, len(pal)), 255)]))
    arrays, changed, edited = [], 0, 0
    for name in order:
        a = old.get(name, np.zeros((h, w, 4), np.uint8))  # a new frame starts blank
        if name in edits:
            try:
                raw = Image.open(io.BytesIO(base64.b64decode(edits[name], validate=True)))
                new = _pixel.cut_alpha(np.asarray(raw.convert("RGBA")), 0.5)
            except (ValueError, OSError, binascii.Error):
                raise StepError("bad_params", f"edit: frame {name} is not a PNG") from None
            if new.shape != a.shape:
                raise StepError(
                    "bad_params",
                    f"edit: frame {name} is {new.shape[1]} x {new.shape[0]}, the cell {w} x {h}",
                )
            if allowed is not None and not np.isin(_colours(new), allowed).all():
                raise StepError("bad_params", f"edit: frame {name} has colours outside the palette")
            gone = (new[..., 3] == 0) & (
                a[..., 3] == 0
            )  # transparent both times: whatever RGB it held
            changed += int(((new != a).any(-1) & ~gone).sum())
            edited += 1
            a = new
        arrays.append(a)
    tags = params.get("tags", tags0)
    ok_tags = isinstance(tags, list) and all(
        isinstance(t, dict)
        and isinstance(t.get("name"), str)
        and t["name"].strip()
        and all(
            isinstance(t.get(k), int) and not isinstance(t.get(k), bool) for k in ("from", "to")
        )
        and 0 <= t["from"] <= t["to"] < len(order)
        for t in tags
    )
    ok_ms = all(
        isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 60_000
        for v in durations.values()
    )
    ok_tags = ok_tags and len({t["name"] for t in tags}) == len(tags)
    if not (ok_tags and ok_ms):
        raise StepError(
            "bad_params",
            "edit: tags [{name, from, to}] inside the order; durations whole ms, 1-60000",
        )
    ms = [int(durations.get(n, was_ms.get(n, default_ms))) for n in order]
    # a tile stays one while it is one frame: more frames make it a sheet (its `tile` is the one picture)
    outputs, data = _write(out, order, arrays, tags, ms, pal, "tile" in outs and len(arrays) == 1)
    report = {
        "edited_frames": edited,
        "changed_pixels": changed,
        "colors": None if pal is None else len(pal),
        "frames": len(arrays),
        "cell": [w, h],
    }
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"outputs": outputs, "metrics": report, "licenses": licenses}


if __name__ == "__main__":
    main(run)
