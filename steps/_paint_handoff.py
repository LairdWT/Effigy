"""CPU helpers for the hand-paint handoff bundle, seam-heal zones and source/result sheets."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

from steps._common import StepError, progress
from steps._paint_seams import ownership_map
from steps._paint_set import Surface
from steps._uv_transfer import shell_ids

REVIEW_PITCH: int = -25
GUIDE_TURNS: tuple[tuple[str, int], ...] = (("front", 0), ("right", 90), ("back", 180), ("left", 270))
GUIDE_SIZE: int = 1024
OVERLAY_SIZE: int = 512
SHEET_PANEL: int = 384
DENSITY_UNIT: str = "pixels per metre"
ZONE_COLOUR: np.ndarray = np.array([35, 210, 105])
BACKGROUND: tuple[int, int, int] = (33, 36, 39)


def _framing(surface: Surface, views: list[dict] | None) -> tuple[list[float], float]:
    if not views:
        center: np.ndarray = (surface.vertices.min(0) + surface.vertices.max(0)) / 2
        extent: float = float(np.linalg.norm(surface.vertices - center, axis=1).max()) * 2.2
        return center.tolist(), extent
    first: object = views[0]
    if not isinstance(first, dict) or not isinstance(first.get("view"), dict):
        raise StepError("bad_params", "Guide framing needs a captured camera row with a view")
    view: dict = first["view"]
    if not isinstance(view.get("center"), list) or len(view["center"]) != 3:
        raise StepError("bad_params", "Guide framing needs a three-coordinate camera center")
    if type(view.get("extent")) not in (float, int) or view["extent"] <= 0:
        raise StepError("bad_params", "Guide framing needs a positive camera extent")
    return [float(value) for value in view["center"]], float(view["extent"])


def guide_cameras(surface: Surface, front_yaw: float, views: list[dict] | None = None) -> list[dict]:
    """Front yaw and its quarter turns at the review pitch, framed on the captured region or whole mesh."""
    center: list[float]
    extent: float
    center, extent = _framing(surface, views)
    return [{"id": name, "turn": turn,
             "view": {"yaw": (front_yaw + turn) % 360, "pitch": REVIEW_PITCH, "center": center, "extent": extent}}
            for name, turn in GUIDE_TURNS]


def _encode_faces(ids: np.ndarray) -> Image.Image:
    encoded: np.ndarray = ids.astype(np.int64) + 1
    rgb: np.ndarray = np.stack([encoded & 255, (encoded >> 8) & 255, (encoded >> 16) & 255], axis=-1).astype(np.uint8)
    return Image.fromarray(rgb)


def write_guides(surface: Surface, out: Path, cameras: list[dict], size: int = GUIDE_SIZE) -> list[dict]:
    """Unlit base-colour guide renders plus face ids (id + 1, 24-bit RGB) per camera."""
    (out / "guide").mkdir()
    (out / "faces").mkdir()
    rows: list[dict] = []
    for index, camera in enumerate(cameras):
        progress(0.1 + 0.5 * index / len(cameras), f"Rendering hand-paint guide {camera['id']}")
        picture, _ = surface.render(camera["view"], size=size)
        picture.save(out / "guide" / f"{camera['id']}.png")
        ids, _ = surface.raster(camera["view"], size)
        _encode_faces(ids).save(out / "faces" / f"{camera['id']}.png")
        rows.append(camera | {"guide": f"guide/{camera['id']}.png", "faces": f"faces/{camera['id']}.png",
                              "size": size})
    return rows


def contact_sheet(out: Path, rows: list[dict], panel: int = SHEET_PANEL) -> None:
    sheet: Image.Image = Image.new("RGB", (len(rows) * panel, panel + 24), BACKGROUND)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(sheet)
    for column, row in enumerate(rows):
        picture: Image.Image
        with Image.open(out / row["guide"]) as image:
            picture = image.convert("RGBA").resize((panel, panel), Image.Resampling.LANCZOS)
        background: Image.Image = Image.new("RGBA", picture.size, (*BACKGROUND, 255))
        background.alpha_composite(picture)
        sheet.paste(background.convert("RGB"), (column * panel, 24))
        draw.text((column * panel + 8, 5), f"{row['id']} yaw {row['view']['yaw']:g}", fill="white")
    sheet.save(out / "contact-sheet.png")


def uv_layout_image(surface: Surface) -> Image.Image:
    atlas: np.ndarray = (surface.base.astype(float) * (255 / surface.channel_max)).round().astype(np.uint8)
    image: Image.Image = Image.fromarray(atlas).convert("RGB")
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)
    for triangle in surface.uv.numpy()[np.asarray(surface.mesh.faces)]:
        points: list[tuple] = [tuple(point * surface.size) for point in triangle]
        draw.line(points + points[:1], fill=(60, 220, 245), width=1)
    return image


def _neighbour_slices(axis: int) -> tuple[tuple[slice, slice], tuple[slice, slice]]:
    if axis == 0:
        return (slice(None, -1), slice(None)), (slice(1, None), slice(None))
    return (slice(None), slice(None, -1)), (slice(None), slice(1, None))


def seam_zone(surface: Surface, mode: str, radius: int | None = None) -> tuple[np.ndarray, dict]:
    """UV permission around writer-ownership joins inside one shell, or around shell borders."""
    if mode not in ("writers", "shells"):
        raise StepError("bad_params", "Seam-heal mode must be writers or shells")
    if radius is None:
        radius = max(3, round(surface.size * 0.012))
    if type(radius) is not int or radius < 1:
        raise StepError("bad_params", "Seam-heal radius must be a positive whole number of pixels")
    shells: np.ndarray = np.full_like(surface.owner, -1)
    shells[surface.covered] = shell_ids(surface)[surface.ids]
    boundary: np.ndarray = np.zeros_like(surface.covered)
    record: dict
    first: tuple[slice, slice]
    second: tuple[slice, slice]
    different: np.ndarray
    if mode == "writers":
        labels: np.ndarray
        owner_source: str
        healed: list[str]
        try:
            labels, owner_source, healed = ownership_map(surface.source)
        except StepError as error:
            if error.code != "missing_input":
                raise
            raise StepError("missing_input", "No writer ownership exists in this mesh's history. Mark shell borders explicitly with heal_mask:shells.") from error
        if labels.shape != surface.covered.shape:
            raise StepError("bad_params", "Writer ownership does not match the prepared atlas")
        labels = np.where(surface.covered, labels, 0)
        for axis in (0, 1):
            first, second = _neighbour_slices(axis)
            different = (labels[first] != labels[second]) & (labels[first] != 0) & (labels[second] != 0)
            different &= shells[first] == shells[second]
            boundary[first] |= different
            boundary[second] |= different
        record = {"zone_source": "writer_ownership", "ownership_source": owner_source,
                  "healed_versions": healed, "fallback": False}
    else:
        for axis in (0, 1):
            first, second = _neighbour_slices(axis)
            different = shells[first] != shells[second]
            boundary[first] |= different & surface.covered[first]
            boundary[second] |= different & surface.covered[second]
        record = {"zone_source": "shell_borders", "fallback": True}
    if not boundary.any():
        raise StepError("no_seam_zone", "No seam boundary was found for this mode; the source is unchanged")
    distance: np.ndarray
    nearest: np.ndarray
    distance, nearest = distance_transform_edt(~boundary, return_indices=True)
    zone: np.ndarray = surface.covered & (distance <= radius) & (shells == shells[nearest[0], nearest[1]])
    return zone, record | {"mode": mode, "pixels": int(zone.sum()), "boundary_pixels": int(boundary.sum()),
                           "radius_pixels": radius, "advisory": True}


def zone_overlays(surface: Surface, zone: np.ndarray, out: Path, cameras: list[dict],
                  size: int = OVERLAY_SIZE) -> list[str]:
    tinted: np.ndarray = surface.base.astype(np.float64) * (255 / surface.channel_max)
    tinted[zone, :3] = tinted[zone, :3] * 0.5 + ZONE_COLOUR * 0.5
    texture: torch.Tensor = torch.tensor(tinted.astype(np.float32))
    (out / "overlays").mkdir()
    written: list[str] = []
    for index, camera in enumerate(cameras):
        progress(0.5 + 0.4 * index / len(cameras), f"Rendering seam-heal overlay {camera['id']}")
        picture, _ = surface.render(camera["view"], texture, size)
        picture.save(out / "overlays" / f"{camera['id']}.png")
        written.append(camera["id"])
    return written


def comparison_sheet(surface: Surface, result: np.ndarray, out: Path, panel: int = SHEET_PANEL) -> list[dict]:
    """Source row above result row at the four review yaws; returns per-yaw RGB differences."""
    texture: torch.Tensor = torch.tensor(result.astype(np.float32) * (255 / surface.channel_max))
    center: list[float]
    extent: float
    center, extent = _framing(surface, None)
    sheet: Image.Image = Image.new("RGB", (4 * panel, 2 * (panel + 24)), BACKGROUND)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(sheet)
    rows: list[dict] = []
    for column, yaw in enumerate((0, 90, 180, 270)):
        progress(0.9 + column * 0.02, f"Comparing source and result at {yaw} degrees")
        view: dict = {"yaw": yaw, "pitch": REVIEW_PITCH, "center": center, "extent": extent}
        original, _ = surface.render(view, size=panel)
        changed, _ = surface.render(view, texture, panel)
        source_pixels: np.ndarray = np.asarray(original)
        result_pixels: np.ndarray = np.asarray(changed)
        opaque: np.ndarray = (source_pixels[..., 3] == 255) & (result_pixels[..., 3] == 255)
        difference: np.ndarray = np.abs(source_pixels[..., :3].astype(np.int16)
                                        - result_pixels[..., :3].astype(np.int16))[opaque]
        rows.append({"yaw": yaw, "mean_rgb8": float(difference.mean()) if difference.size else 0.0,
                     "p95_rgb8": float(np.percentile(difference, 95)) if difference.size else 0.0,
                     "render_alpha_changed": int(np.count_nonzero(source_pixels[..., 3] != result_pixels[..., 3]))})
        for row_index, (label, picture) in enumerate((("Source", original), ("Result", changed))):
            background: Image.Image = Image.new("RGBA", picture.size, (*BACKGROUND, 255))
            background.alpha_composite(picture)
            sheet.paste(background.convert("RGB"), (column * panel, row_index * (panel + 24) + 24))
            draw.text((column * panel + 8, row_index * (panel + 24) + 5), f"{label} yaw {yaw}", fill="white")
    sheet.save(out / "comparison.png")
    return rows


def handoff_record(surface: Surface, profile: dict, source: str, geometry_revision: str,
                   authoring_revision: int | None, measured: list[float], cameras: list[dict],
                   permission_source: str) -> dict:
    """Bundle record; density stays null unless the session declares it with a measured scale."""
    preparation: dict = profile["preparation"]
    sampling: dict = profile["sampling"]
    metres_per_unit: float | None = sampling.get("metres_per_unit")
    declared: float | None = sampling.get("density_per_metre")
    if declared is not None and metres_per_unit is None:
        raise StepError("bad_params", "A declared density requires a measured metres-per-unit scale")
    material_keys: tuple[str, ...] = ("id", "identity", "faces", "palette", "feature_scale", "marks", "preserve")
    record: dict = {
        "schema": 1, "source": source, "geometry_revision": geometry_revision,
        "authoring_revision": authoring_revision, "atlas_size": surface.size,
        "bit_depth": surface.base.dtype.itemsize * 8, "uv_profile": preparation["uv_profile"],
        "gutter_pixels": preparation["gutter_pixels"],
        "declared_density_pixels_per_metre": declared, "density_unit": DENSITY_UNIT,
        "density_declaration": "session" if declared is not None else "missing",
        "metres_per_unit": metres_per_unit,
        "texels_per_asset_unit_p10_p50_p90": [float(value) for value in measured],
        "physical_scale": "declared" if metres_per_unit is not None else "unknown",
        "materials": [{key: material.get(key) for key in material_keys} for material in profile["materials"]],
        "cameras": [{"id": row["id"], "turn": row["turn"], **row["view"], "guide": row["guide"],
                     "faces": row["faces"], "size": row["size"]} for row in cameras],
        "permission_source": permission_source,
        "face_id_encoding": "rgb24_face_index_plus_one",
    }
    if metres_per_unit is not None and len(measured) == 3:
        record["texels_per_metre_p50"] = float(measured[1]) / float(metres_per_unit)
    return record
