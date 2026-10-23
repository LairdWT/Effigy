"""CPU camera capture, shared UV permission and deterministic multi-view projection."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

from server import library
from server.paint_contracts import PERMISSION_PROJECTION, group_layout, joint_group
from steps import _glb
from steps._bake import rasterize_uv
from steps._common import StepError, progress
from steps._paint_mask import mask_image, parse_mask
from steps._paint_projection import sample_owned, sample_replacement, selection_feather
from steps._views import ortho, render, zbuffer
from steps.paint import load_mesh, reject_uv_overlap, version_dir, write_atlas

PANEL = 704


class Surface:
    def __init__(self, source: Path):
        torch.set_num_threads(2)
        _, self.doc, self.blob, self.material, self.mesh, self.base, uv = load_mesh(source)
        self.source = source
        self.original_accessors = tuple(_glb.accessor(self.doc, self.blob, i).copy() for i in range(len(self.doc["accessors"])))
        self.original_materials = material_state(self.doc, self.blob, self.material)
        self.size = len(self.base)
        reject_uv_overlap(uv, self.mesh.faces, self.size)
        self.uv = torch.tensor(uv, dtype=torch.float32)
        self.faces = torch.tensor(np.asarray(self.mesh.faces), dtype=torch.long)
        self.vertices = np.asarray(self.mesh.vertices)
        self.channel_max = np.iinfo(self.base.dtype).max
        self.texture = torch.tensor(self.base.astype(np.float32) * (255 / self.channel_max))
        owner, bary = rasterize_uv(self.uv, self.faces, self.size)
        self.owner = owner.numpy()
        self.covered = self.owner >= 0
        self.ids = self.owner[self.covered]
        self.points = (self.vertices[np.asarray(self.mesh.faces)[self.ids]] * bary.numpy()[self.covered, :, None]).sum(1)
        self.normals = np.asarray(self.mesh.face_normals)[self.ids]

    def render(self, view: dict, texture: torch.Tensor | None = None, size: int = PANEL) -> tuple:
        rgb, alpha, _, raster = render(self.texture if texture is None else texture, self.uv,
                                       self.faces, self.vertices, ortho(**view), size)
        rgba = np.dstack((rgb.numpy(), alpha.numpy()))
        return Image.fromarray((rgba * 255).round().clip(0, 255).astype(np.uint8)), raster[0].numpy()

    def mapping(self, view: dict, face_image: np.ndarray) -> tuple:
        camera = ortho(**view)
        pix, _ = camera["project"](self.points)
        xy = np.floor(pix * face_image.shape[0]).astype(np.int64)
        valid = ((pix >= 0) & (pix < 1)).all(1)
        xy = xy.clip(0, face_image.shape[0] - 1)
        facing = (self.normals * camera["towards"](self.points)).sum(1)
        visible = valid & (face_image[xy[:, 1], xy[:, 0]] == self.ids) & (facing > 0.25)
        border = np.minimum(pix, 1 - pix).min(1).clip(0, 0.5)
        return pix, visible, facing, border

    def raster(self, view: dict, size: int) -> tuple[np.ndarray, np.ndarray]:
        pix, depth = ortho(**view)["project"](self.vertices)
        ids, bary, _ = zbuffer(torch.tensor(pix, dtype=torch.float32),
                              torch.tensor(depth, dtype=torch.float32), self.faces, size)
        return ids.numpy(), bary.numpy()

    def screen_permission(self, view: dict, selected: np.ndarray, size: int) -> np.ndarray:
        ids, bary = self.raster(view, size)
        seen = ids >= 0
        screen = np.zeros_like(seen)
        face_ids = ids[seen]
        uv = (self.uv.numpy()[np.asarray(self.mesh.faces)[face_ids]] * bary[seen, :, None]).sum(1)
        permission = sample_owned(selected[..., None].astype(np.float32), uv, self.owner,
                                  face_ids, self.covered, self.covered)
        facing = np.asarray(self.mesh.face_normals)[face_ids] @ ortho(**view)["towards"](np.zeros((1, 3)))[0]
        screen[seen] = permission.supported & (permission.values[:, 0] == 1) & (facing > 0.25)
        return screen


def material_state(doc: dict, blob: bytearray, painted_material: int) -> list:
    def walk(value: object, key: str, material: int) -> object:
        if isinstance(value, list):
            return [walk(item, "", material) for item in value]
        if not isinstance(value, dict):
            return value
        if key.endswith("Texture") and "index" in value:
            texture = doc["textures"][value["index"]]
            if "source" not in texture:
                raise StepError("missing_input", "Multi-view paint needs embedded image sources for all material maps")
            image = doc["images"][texture["source"]]
            if "bufferView" not in image:
                raise StepError("missing_input", "Embed all material maps before multi-view painting")
            view = doc["bufferViews"][image["bufferView"]]
            start = view.get("byteOffset", 0)
            payload = bytes(blob[start:start + view["byteLength"]])
            if material == painted_material and key == "baseColorTexture":
                payload = b"painted-base-colour"
            sampler = doc.get("samplers", [])[texture["sampler"]] if "sampler" in texture else None
            return {"binding": {k: v for k, v in value.items() if k != "index"}, "image": payload,
                    "sampler": sampler, "texture": {k: v for k, v in texture.items() if k not in ("source", "sampler")}}
        return {k: walk(v, k, material) for k, v in value.items()}
    return [walk(material, "", i) for i, material in enumerate(doc["materials"])]


def save_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def read_manifest(folder: Path) -> dict:
    return json.loads(library.resolve_output(folder, "manifest").read_text(encoding="utf-8"))


def read_faces(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB")).astype(np.int32)
    return rgb[..., 0] + (rgb[..., 1] << 8) + (rgb[..., 2] << 16) - 1


def cameras(surface: Surface, selected: np.ndarray, yaw: float) -> list[dict]:
    points = surface.points[selected[surface.covered]]
    if not len(points):
        raise StepError("bad_params", "Select at least one surface texel")
    center = (points.min(0) + points.max(0)) / 2
    extent = max(float(np.linalg.norm(points - center, axis=1).max()) * 2 * 1.1, 0.01)
    angles = [(a, 0) for a in range(0, 360, 45)]
    angles += [(a, -45 if a % 90 == 0 else -35.2643897) for a in range(0, 360, 45)]
    angles += [(0, -90)]
    angles += [(a, 45 if a % 90 == 0 else 35.2643897) for a in range(0, 360, 45)]
    angles += [(0, 90)]
    return [{"id": f"v{i:02}", "view": {"yaw": (a + yaw) % 360, "pitch": p,
             "center": center.tolist(), "extent": extent}} for i, (a, p) in enumerate(angles)]


def coverage_views(permissions: list[np.ndarray], views: list[dict]) -> list[int]:
    remaining = np.any(permissions, axis=0)
    pending = sorted(range(len(views)), key=lambda i: views[i]["id"])
    chosen = []
    while remaining.any():
        best = max(pending, key=lambda i: int((permissions[i] & remaining).sum()))
        chosen.append(best)
        remaining &= ~permissions[best]
        pending.remove(best)
    for index in reversed(chosen.copy()):
        other = [permissions[i] for i in chosen if i != index]
        if other and not (permissions[index] & ~np.any(other, axis=0)).any():
            chosen.remove(index)
    return sorted(chosen, key=lambda i: views[i]["id"])


def _selection_outputs(surface: Surface, capture: Path, out: Path, views: list[dict],
                       selected: np.ndarray, strategy: str = "pairs", panel_size: int = PANEL,
                       authoring: dict | None = None) -> dict:
    (out / "selections").mkdir()
    (out / "overlays").mkdir()
    mask_texture = torch.tensor(np.dstack([selected * 255.0] * 3 + [np.ones_like(selected) * 255.0]), dtype=torch.float32)
    permissions = []
    result_views = []
    for row in views:
        image_path = capture / "views" / f"{row['id']}.png"
        faces = read_faces(capture / "faces" / f"{row['id']}.png")
        if faces.shape != (panel_size, panel_size):
            faces, _ = surface.raster(row["view"], panel_size)
        pix, visible, _, _ = surface.mapping(row["view"], faces)
        picture, _ = surface.render(row["view"], mask_texture, panel_size)
        values = np.asarray(picture)
        screen = surface.screen_permission(row["view"], selected, panel_size) & (values[..., 3] == 255)
        xy = np.floor(pix * panel_size).astype(int).clip(0, panel_size - 1)
        allowed = visible & selected[surface.covered] & screen[xy[:, 1], xy[:, 0]]
        permissions.append(allowed)
        Image.fromarray(screen.astype(np.uint8) * 255).save(out / "selections" / f"{row['id']}.png")
        with Image.open(image_path) as original:
            overlay = np.asarray(original.convert("RGBA")).copy()
        overlay[screen, :3] = (overlay[screen, :3] * 0.5 + np.array([35, 210, 105]) * 0.5).astype(np.uint8)
        Image.fromarray(overlay).save(out / "overlays" / f"{row['id']}.png")
        result_views.append(row | {"texels": int(allowed.sum())})
    active = [i for i, p in enumerate(permissions) if p.any()]
    pairs = set()
    isolated = []
    directions = [ortho(**row["view"])["towards"](np.zeros((1, 3)))[0] for row in views]
    for i in active:
        neighbours = [j for j in active if j != i and np.any(permissions[i] & permissions[j])]
        if not neighbours:
            isolated.append(views[i]["id"])
            continue
        other = max(neighbours, key=lambda j: (float(directions[i] @ directions[j]),
                                              int((permissions[i] & permissions[j]).sum()), -j))
        pairs.add(tuple(sorted((i, other))))
    groups = [{"id": f"{views[a]['id']}_{views[b]['id']}", "views": [views[a]["id"], views[b]["id"]],
               "overlap_texels": int((permissions[a] & permissions[b]).sum())} for a, b in sorted(pairs)]
    covered = np.any(permissions, axis=0)
    working = coverage_views(permissions, views)
    limitation = None
    if strategy != "pairs":
        keys = [views[i]["id"] for i in (active if strategy == "synchronized" else working)]
        try:
            groups = [joint_group(keys, strategy, panel_size)]
        except ValueError as error:
            groups = []
            limitation = str(error)
    manifest = {"schema": 2 if strategy != "pairs" else 1, "strategy": strategy,
                "permission_projection": PERMISSION_PROJECTION,
                "panel_size": panel_size, "views": result_views, "groups": groups,
                "working_views": [views[i]["id"] for i in working], "limitation": limitation,
                "coverage": {"selected": int(selected.sum()), "visible": int(covered.sum()),
                             "unseen": int((selected[surface.covered] & ~covered).sum()), "unpaired_views": isolated,
                             "working_count": len(working), "eligible_count": len(active)}}
    Image.fromarray(selected.astype(np.uint8) * 255).save(out / "mask.png")
    selection_atlas = (surface.base.astype(np.float64) * (255 / surface.channel_max)).round().clip(0, 255).astype(np.uint8)
    selection_atlas[selected, :3] = (selection_atlas[selected, :3] * 0.5 + np.array([35, 210, 105]) * 0.5).astype(np.uint8)
    Image.fromarray(selection_atlas).save(out / "selection_atlas.png")
    if strategy != "pairs" and groups:
        layout = group_layout(groups[0])
        sheet = Image.new("RGBA", (layout.width, layout.height))
        permission_sheet = Image.new("L", sheet.size)
        for panel in layout.panels:
            with Image.open(capture / "views" / f"{panel.camera_id}.png") as image:
                sheet.paste(image, (panel.x, panel.y))
            with Image.open(out / "selections" / f"{panel.camera_id}.png") as image:
                permission_sheet.paste(image, (panel.x, panel.y))
        sheet.save(out / "sheet.png")
        permission_sheet.save(out / "sheet_mask.png")
    from steps._sampling_plan import measure_sampling
    included = set(manifest["working_views"]) if strategy == "whole_sheet" else {v["id"] for v in views}
    manifest["sampling"] = measure_sampling(surface, capture, [v for v in views if v["id"] in included],
                                             selected, panel_size, authoring, out)
    save_json(out / "manifest.json", manifest)
    return manifest


def capture(surface: Surface, out: Path, params: dict) -> dict:
    profile = params.get("authoring_profile")
    if profile is not None:
        if profile["preparation"]["atlas_size"] != surface.size:
            raise StepError("bad_params", f"Declared atlas size differs from the source's {surface.size} pixels; inspect and correct the profile")
        if any(face >= len(surface.mesh.faces) for material in profile["materials"] for face in (material["faces"] or [])):
            raise StepError("bad_params", "A material region names missing source triangles")
    selected = surface.covered.copy()
    faces = params["initial_faces"]
    if faces is not None:
        if not faces or any(type(i) is not int or i < 0 or i >= len(surface.mesh.faces) for i in faces):
            raise StepError("bad_params", "Select valid geometry face IDs")
        selected &= np.isin(surface.owner, faces)
    strategy = params.get("strategy", "pairs")
    panel_size = PANEL if strategy == "pairs" else params.get("panel_size", 512)
    if strategy != "pairs" and panel_size not in (192, 256, 384, 512):
        raise StepError("bad_params", "Unsupported camera panel size")
    if params.get("selection_source"):
        folder = version_dir(surface.source.parent, params["selection_source"])
        with Image.open(library.resolve_output(folder, "mask")) as picture:
            selected = np.asarray(picture) > 0
        views = [{"id": v["id"], "view": v["view"]} for v in read_manifest(folder)["views"]]
    else:
        views = cameras(surface, selected, params["front_yaw"])
    (out / "views").mkdir()
    (out / "faces").mkdir()
    for i, row in enumerate(views):
        progress(i / 32, f"Capturing fixed camera {i + 1}/26")
        picture, ids = surface.render(row["view"], size=panel_size)
        ids, _ = surface.raster(row["view"], panel_size)
        picture.save(out / "views" / f"{row['id']}.png")
        encoded = ids.astype(np.int64) + 1
        rgb = np.stack([encoded & 255, (encoded >> 8) & 255, (encoded >> 16) & 255], axis=-1).astype(np.uint8)
        Image.fromarray(rgb).save(out / "faces" / f"{row['id']}.png")
    manifest = _selection_outputs(surface, out, out, views, selected, strategy, panel_size, params.get("authoring_profile"))
    outputs = {"views": "views", "face_ids": "faces", "mask": "mask.png",
               "manifest": "manifest.json", "selections": "selections", "overlays": "overlays", "selection_atlas": "selection_atlas.png", "sampling": "sampling.png"}
    if (out / "sheet.png").exists():
        outputs.update(sheet="sheet.png", sheet_mask="sheet_mask.png")
    return {"outputs": outputs, "metrics": {"coverage": manifest["coverage"], "panel_size": panel_size}}


def select(surface: Surface, out: Path, params: dict) -> dict:
    asset = surface.source.parent
    capture_dir = version_dir(asset, params["capture"])
    old_dir = version_dir(asset, params["mask_version"])
    old = read_manifest(old_dir)
    panel_size = old.get("panel_size", PANEL)
    with Image.open(library.resolve_output(old_dir, "mask")) as picture:
        selected = np.asarray(picture) > 0
    mode = params["selection_mode"]
    if mode == "all":
        selected = surface.covered.copy()
    elif mode == "clear":
        selected = np.zeros_like(selected)
    elif mode != "refresh":
        mask = parse_mask(params["selection"])
        if mask.faces is not None and mask.revision != params["geometry_revision"]:
            raise StepError("bad_params", "Face selection belongs to different geometry")
        if mask.faces is not None and any(i >= len(surface.mesh.faces) for i in mask.faces):
            raise StepError("bad_params", "Face selection includes missing triangles")
        if mode == "faces":
            if mask.faces is None:
                raise StepError("bad_params", "Choose faces for the shared selection")
            selected = np.isin(surface.owner, mask.faces)
        else:
            row = next((v for v in old["views"] if v["id"] == params["view_id"]), None)
            if row is None:
                raise StepError("bad_params", "Select a captured camera")
            ids = read_faces(capture_dir / "faces" / f"{row['id']}.png")
            pix, visible, _, _ = surface.mapping(row["view"], ids)
            screen = np.asarray(mask_image(mask, panel_size)) > 0
            xy = (pix * panel_size).astype(int).clip(0, panel_size - 1)
            permission = visible & screen[xy[:, 1], xy[:, 0]]
            if mask.faces is not None:
                permission &= np.isin(surface.ids, mask.faces)
            values = selected[surface.covered]
            values[permission] = mode != "erase"
            selected[surface.covered] = values
    manifest = _selection_outputs(surface, capture_dir, out, old["views"], selected,
                                  params.get("strategy", "pairs"), panel_size, params.get("authoring_profile"))
    changed_views = set()
    for row in manifest["views"]:
        with Image.open(old_dir / "selections" / f"{row['id']}.png") as a, Image.open(out / "selections" / f"{row['id']}.png") as b:
            if not np.array_equal(np.asarray(a), np.asarray(b)):
                changed_views.add(row["id"])
    invalid = [g["id"] for g in old["groups"] if set(g["views"]) & changed_views]
    outputs = {"mask": "mask.png", "manifest": "manifest.json", "selections": "selections", "overlays": "overlays", "selection_atlas": "selection_atlas.png", "sampling": "sampling.png"}
    if (out / "sheet.png").exists():
        outputs.update(sheet="sheet.png", sheet_mask="sheet_mask.png")
    return {"outputs": outputs,
            "metrics": {"invalidated_groups": invalid, "coverage": manifest["coverage"]}}


def _patch_ids(surface: Surface) -> np.ndarray:
    faces = np.asarray(surface.mesh.faces)
    _, vertex_ids = np.unique(np.round(surface.vertices, 7), axis=0, return_inverse=True)
    parent = np.arange(len(faces))
    normals = np.asarray(surface.mesh.face_normals)
    edges: dict[tuple[int, int], int] = {}

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = int(parent[i])
        return i

    for i, triangle in enumerate(vertex_ids[faces]):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((int(triangle[a]), int(triangle[b]))))
            other = edges.get(edge)
            if other is None:
                edges[edge] = i
                continue
            if float(normals[i] @ normals[other]) < 0.99999:
                continue
            parent[root(i)] = root(other)
    return np.unique([root(i) for i in range(len(faces))], return_inverse=True)[1]


def preview(surface: Surface, out: Path, params: dict) -> dict:
    asset = surface.source.parent
    capture_dir = version_dir(asset, params["capture"])
    mask_dir = version_dir(asset, params["mask_version"])
    manifest = read_manifest(mask_dir)
    with Image.open(library.resolve_output(mask_dir, "mask")) as picture:
        mask = np.asarray(picture) > 0
    views = {v["id"]: v for v in manifest["views"]}
    candidates = sorted((panel.camera_id, c["group"]["id"], c["version"], panel)
                        for c in params["candidates"] for panel in group_layout(c["group"]).panels)

    def contribution(candidate: tuple) -> tuple:
        view_id, group_id, version, panel = candidate
        folder = version_dir(asset, version)
        box = (panel.x, panel.y, panel.x + panel.width, panel.y + panel.height)
        with Image.open(capture_dir / "views" / f"{view_id}.png") as image:
            original = np.asarray(image.convert("RGBA")).copy()
        if params.get("diagnostic"):
            rgb = original[..., :3].copy()
            with Image.open(mask_dir / "selections" / f"{view_id}.png") as image:
                permitted = np.asarray(image) > 0
            if params.get("diagnostic_mode", "mask") == "mask":
                rgb[permitted] = [35, 210, 105]
        else:
            with Image.open(library.resolve_output(folder, "image")) as image:
                rgb = np.asarray(image.crop(box).convert("RGB")).copy()
            with Image.open(library.resolve_output(folder, "write_mask")) as image:
                permitted = np.asarray(image.crop(box)) > 0
        ids = read_faces(capture_dir / "faces" / f"{view_id}.png")
        if ids.shape != original.shape[:2]:
            ids, _ = surface.raster(views[view_id]["view"], panel.width)
        pix, visible, facing, border = surface.mapping(views[view_id]["view"], ids)
        xy = (pix * panel.width).astype(int).clip(0, panel.width - 1)
        allowed = visible & mask[surface.covered] & permitted[xy[:, 1], xy[:, 0]]
        from steps._sampling_plan import face_footprints
        footprints = face_footprints(surface, views[view_id]["view"], panel.width)
        samples = sample_replacement(original[..., :3], rgb, pix, ids, surface.ids,
                                     permitted, original[..., 3] == 255,
                                     footprints=footprints[surface.ids], eligible=allowed)
        allowed &= samples.supported
        if params.get("authoring_profile", {}).get("sampling", {}).get("mode") == "detail":
            native_samples = np.linalg.svd(footprints, compute_uv=False)
            allowed &= native_samples[surface.ids, 1] >= params["authoring_profile"]["sampling"]["minimum_samples"]
        source_rgb = surface.base[surface.covered, :3].astype(np.float64) * (255 / surface.channel_max)
        sampled = np.where(samples.changed[:, None], samples.values, source_rgb)
        return sampled.clip(0, 255), allowed, facing, border, view_id, group_id

    progress(0.1, "Resolving visible contributions from recorded camera rectangles")
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(contribution, candidates))
    if not rows:
        raise StepError("bad_params", "No generated groups selected")
    patches = _patch_ids(surface)[surface.ids]
    patch_count = int(patches.max()) + 1
    dominant = np.zeros(patch_count, dtype=int)
    best_facing, best_border = np.full(patch_count, -1.0), np.full(patch_count, -1.0)
    for index, (_, allowed, facing, border, _, _) in enumerate(rows):
        fs = np.bincount(patches, weights=facing * allowed, minlength=patch_count)
        bs = np.bincount(patches, weights=border * allowed, minlength=patch_count)
        better = (fs > best_facing) | ((fs == best_facing) & (bs > best_border))
        dominant[better], best_facing[better], best_border[better] = index, fs[better], bs[better]
    chosen = np.full(len(surface.ids), -1, dtype=np.int16)
    best_facing = np.full(len(chosen), -1.0)
    best_border = np.full(len(chosen), -1.0)
    low = np.full((len(chosen), 3), 255, dtype=np.float64)
    high = np.zeros_like(low)
    for index, (rgb, allowed, facing, border, _, _) in enumerate(rows):
        low[allowed] = np.minimum(low[allowed], rgb[allowed])
        high[allowed] = np.maximum(high[allowed], rgb[allowed])
        better = allowed & ((facing > best_facing) | ((facing == best_facing) & (border > best_border)))
        chosen[better], best_facing[better], best_border[better] = index, facing[better], border[better]
    for index, (_, allowed, _, _, _, _) in enumerate(rows):
        use = allowed & (dominant[patches] == index)
        chosen[use] = index
    permission = np.zeros_like(mask)
    permission[surface.covered] = chosen >= 0
    if not permission.any():
        raise StepError("bad_params", "Selected candidates contain no eligible texture texels")
    amount = selection_feather(mask, surface.covered, params.get("feather", 6))
    colours = surface.base[surface.covered, :3].astype(np.float64)
    for index, (rgb, _, _, _, _, _) in enumerate(rows):
        use = chosen == index
        a = amount[use, None]
        colours[use] = colours[use] * (1 - a) + rgb[use] * (surface.channel_max / 255) * a
    result = surface.base.copy()
    result[surface.covered, :3] = np.rint(colours).clip(0, surface.channel_max).astype(result.dtype)
    wide = (rasterize_uv(surface.uv, surface.faces, surface.size * 2)[0] >= 0).numpy().reshape(surface.size, 2, surface.size, 2).any(3).any(1)
    distances, nearest = distance_transform_edt(~surface.covered, return_indices=True)
    surface_changed = np.any(result != surface.base, axis=2)
    gutter = (~wide) & (distances <= 8) & permission[nearest[0], nearest[1]] & surface_changed[nearest[0], nearest[1]]
    result[gutter, :3] = result[nearest[0][gutter], nearest[1][gutter], :3]
    changed = np.any(result != surface.base, axis=2)
    if np.any(changed & ~(permission | gutter)) or np.any(result[..., 3] != surface.base[..., 3]):
        raise StepError("failed", "Combined projection changed protected pixels")
    write_atlas(out, surface.doc, surface.blob, surface.material, result)
    saved_doc, saved_blob = _glb.read(out / "mesh.glb")
    if len(saved_doc["accessors"]) != len(surface.original_accessors) or any(
            not np.array_equal(value, _glb.accessor(saved_doc, saved_blob, i)) for i, value in enumerate(surface.original_accessors)):
        raise StepError("failed", "Combined bake changed geometry or UV accessors")
    if material_state(saved_doc, saved_blob, surface.material) != surface.original_materials:
        raise StepError("failed", "Combined bake changed another material map or setting")
    Image.fromarray(permission.astype(np.uint8) * 255).save(out / "permission.png")
    owners = np.zeros((*mask.shape, 3), dtype=np.uint8)
    ids = chosen + 1
    owners[surface.covered] = np.stack([(ids * 67) % 256, (ids * 149) % 256, (ids * 223) % 256], -1)
    Image.fromarray(owners).save(out / "owners.png")
    from steps._paint_seams import ownership_map
    try:
        writers, _, _ = ownership_map(surface.source)
    except StepError as error:
        if error.code != "missing_input":
            raise
        writers = np.zeros_like(mask, dtype=np.int64)
    if writers.shape != mask.shape:
        raise StepError("bad_params", "Appearance ownership does not match the prepared atlas")
    marker = int(writers.max()) + 1
    writers[surface.covered & (writers == 0)] = marker
    if marker + len(rows) > 0xFFFFFF:
        raise StepError("bad_params", "Appearance ownership exceeds its 24-bit label capacity")
    written = permission & surface_changed
    new_labels = np.zeros_like(writers)
    new_labels[surface.covered] = marker + chosen.astype(np.int64) + 1
    writers[written] = new_labels[written]
    writers[~surface.covered] = 0
    encoded_writers = np.stack((writers & 255, (writers >> 8) & 255, (writers >> 16) & 255), axis=-1).astype(np.uint8)
    Image.fromarray(encoded_writers).save(out / "writers.png")
    save_json(out / "projection.json", {"views": [
        {"index": i + 1, "view": row[4], "group": row[5], "version": candidates[i][2],
         "colour": [((i + 1) * k) % 256 for k in (67, 149, 223)]} for i, row in enumerate(rows)]})
    disagreement = np.zeros_like(owners)
    disagreement[surface.covered, 0] = np.where(chosen >= 0, (high.astype(int) - low).max(1).clip(0, 255), 0).astype(np.uint8)
    Image.fromarray(disagreement).save(out / "disagreement.png")
    review(surface, result, out)
    return {"outputs": {"mesh": "mesh.glb", "basecolor": "basecolor.png", "permission": "permission.png",
                        "owners": "owners.png", "writers": "writers.png", "projection": "projection.json", "disagreement": "disagreement.png", "image": "review.png", "turntable": "turntable.gif"},
            "metrics": {"written_texels": int(permission.sum()), "changed_texels": int(changed.sum()),
                        "gutter_changed_texels": int((changed & gutter).sum()), "gutter_maximum_pixels": 8,
                        "protected_changed": 0, "alpha_changed": 0, "selected_unwritten": int((mask & ~permission).sum()),
                        "geometry_uv_equal": True, "other_materials_equal": True,
                        "candidate_count": len(rows), "cpu_workers": 2, "diagnostic": bool(params.get("diagnostic")),
                        "diagnostic_mode": params.get("diagnostic_mode", "mask") if params.get("diagnostic") else None,
                        "projection_transfer": "replace_changed_v4", "sampling": "same_face_footprint_grid_v1",
                        "writer_ownership": "accumulated_changed_texels_v1",
                        "feathered_surface_texels": int(((amount < 1) & (chosen >= 0)).sum())}}


def review(surface: Surface, result: np.ndarray, out: Path) -> None:
    texture = torch.tensor(result.astype(np.float32) * (255 / surface.channel_max))
    center = (surface.vertices.min(0) + surface.vertices.max(0)) / 2
    extent = float(np.linalg.norm(surface.vertices - center, axis=1).max()) * 2.2
    sheet = Image.new("RGB", (4 * 384, 2 * 408), (33, 36, 39))
    frames = []
    for i in range(8):
        progress(0.7 + i * 0.03, f"Reviewing combined texture at {i * 45} degrees")
        picture, _ = surface.render({"yaw": i * 45, "pitch": -25, "center": center.tolist(), "extent": extent}, texture, 384)
        background = Image.new("RGBA", picture.size, (33, 36, 39, 255))
        background.alpha_composite(picture)
        frame = background.convert("RGB")
        sheet.paste(frame, ((i % 4) * 384, (i // 4) * 408 + 24))
        ImageDraw.Draw(sheet).text(((i % 4) * 384 + 8, (i // 4) * 408 + 5), f"Yaw {i * 45}", fill="white")
        frames.append(frame)
    sheet.save(out / "review.png")
    frames[0].save(out / "turntable.gif", save_all=True, append_images=frames[1:], duration=350, loop=0)
