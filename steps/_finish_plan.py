"""Surface adjacency, seam candidates and fixed-camera finishing plans."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from server import library
from server.finish_contracts import FinishCamera, FinishPatch, FinishPlan, FinishSettings
from steps._common import StepError, progress
from steps._paint_projection import sample_replacement
from steps._paint_seams import ownership_map
from steps._paint_set import Surface, cameras, save_json
from steps.paint import version_dir


def _edge_pairs(surface: Surface, selected: np.ndarray) -> tuple[np.ndarray, dict]:
    faces = np.asarray(surface.mesh.faces)
    uv = surface.uv.numpy()
    _, welded = np.unique(np.round(surface.vertices, 7), axis=0, return_inverse=True)
    edges: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)
    for face, triangle in enumerate(faces):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            first, second = int(triangle[a]), int(triangle[b])
            if welded[first] > welded[second]:
                first, second = second, first
            edges[(int(welded[first]), int(welded[second]))].append((face, first, second))
    medians = np.zeros((len(faces), 3), dtype=float)
    rgb = surface.base[..., :3].astype(float) * (255 / surface.channel_max)
    flat_rgb, owner = rgb[surface.covered], surface.ids
    for face in range(len(faces)):
        values = flat_rgb[owner == face]
        if len(values):
            medians[face] = np.median(values, axis=0)
    pairs = []
    stats = {"open_edges": 0, "ambiguous_edges": 0, "possible_material_edges": 0, "hard_creases": 0}
    for rows in edges.values():
        if len(rows) != 2:
            stats["open_edges" if len(rows) == 1 else "ambiguous_edges"] += 1
            continue
        a, b = rows
        if float(surface.mesh.face_normals[a[0]] @ surface.mesh.face_normals[b[0]]) < -0.15:
            stats["hard_creases"] += 1
            continue
        if np.abs(medians[a[0]] - medians[b[0]]).mean() > 40:
            stats["possible_material_edges"] += 1
            continue
        length = max(np.linalg.norm(uv[r[1]] - uv[r[2]]) * surface.size for r in rows)
        count = max(2, min(4096, int(np.ceil(length))))
        t = (np.arange(count) + 0.5) / count
        sides = []
        for face, first, second in rows:
            edge = uv[first][None] * (1 - t[:, None]) + uv[second][None] * t[:, None]
            center = uv[faces[face]].mean(0)
            toward = center - edge
            distance = np.linalg.norm(toward, axis=1).clip(1e-9) * surface.size
            points = edge + toward * np.minimum(0.2, 1.1 / distance)[:, None]
            xy = np.floor(points * surface.size).astype(int).clip(0, surface.size - 1)
            index = xy[:, 1] * surface.size + xy[:, 0]
            valid = (surface.owner.ravel()[index] == face) & selected.ravel()[index]
            sides.append((index, valid))
        valid = sides[0][1] & sides[1][1]
        pairs.append(np.stack((sides[0][0][valid], sides[1][0][valid]), axis=1))
    return np.concatenate(pairs) if pairs else np.empty((0, 2), dtype=np.int64), stats


def seam_graph(surface: Surface, selected: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    owners, owner_source, healed = ownership_map(surface.source)
    if owners.shape != selected.shape:
        raise StepError("bad_params", "Writer history and texture atlas dimensions differ")
    flat = np.arange(surface.size * surface.size).reshape(selected.shape)
    pairs = []
    for first, second in ((flat[:-1], flat[1:]), (flat[:, :-1], flat[:, 1:])):
        a, b = first.ravel(), second.ravel()
        use = selected.ravel()[a] & selected.ravel()[b] & (surface.owner.ravel()[a] == surface.owner.ravel()[b])
        pairs.append(np.stack((a[use], b[use]), axis=1))
    crossing, stats = _edge_pairs(surface, selected)
    pairs.append(crossing)
    joined = np.unique(np.sort(np.concatenate(pairs), axis=1), axis=0)
    writer = owners.ravel()
    different = (writer[joined[:, 0]] != writer[joined[:, 1]]) & (writer[joined] != 0).all(1)
    joined = joined[different]
    rgb = surface.base[..., :3].astype(np.float64) * (255 / surface.channel_max)
    colour = cv2.GaussianBlur(rgb, (0, 0), 0.75).reshape(-1, 3)
    severity = np.abs(colour[joined[:, 0]] - colour[joined[:, 1]]).sum(1)
    use = severity > 18
    joined, severity = joined[use], severity[use]
    stats.update(ownership_source=owner_source, healed_versions=healed, candidate_pairs=len(joined),
                 cross_uv_pairs=len(crossing), automatic_material_classification=False)
    return joined, severity, owners, stats


def _components(surface: Surface, pairs: np.ndarray) -> np.ndarray:
    if not len(pairs):
        return np.empty(0, dtype=np.int32)
    if len(pairs) > 80_000:
        raise StepError("bad_params", "Seam graph is too large; select a smaller surface region")
    positions = np.zeros((surface.size * surface.size, 3), dtype=float)
    positions[surface.covered.ravel()] = surface.points
    midpoints = positions[pairs].mean(1)
    scale = float(np.linalg.norm(surface.vertices.max(0) - surface.vertices.min(0)))
    links = cKDTree(midpoints).query_pairs(scale * 0.006, output_type="ndarray")
    if len(links) > 2_000_000:
        raise StepError("bad_params", "Seam graph is too dense; choose a smaller surface region")
    if not len(links):
        return np.arange(len(pairs), dtype=np.int32)
    normals = np.zeros((surface.size * surface.size, 3))
    normals[surface.covered.ravel()] = surface.normals
    directions = normals[pairs].mean(1)
    connected = (directions[links[:, 0]] * directions[links[:, 1]]).sum(1) > 0.25
    pair_faces = surface.owner.ravel()[pairs]
    connected &= (pair_faces[links[:, 0], :, None] == pair_faces[links[:, 1], None, :]).any((1, 2))
    links = links[connected]
    matrix = coo_matrix((np.ones(len(links)), (links[:, 0], links[:, 1])), shape=(len(pairs), len(pairs))).tocsr()
    return connected_components(matrix, directed=False)[1]


def patch_masks(surface: Surface, selected: np.ndarray, patch: FinishPatch, pairs: np.ndarray,
                picture: Image.Image, connected_only: bool = False,
                feature_scale: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    size = picture.width
    if patch.material_faces is not None:
        if any(face >= len(surface.mesh.faces) for face in patch.material_faces):
            raise StepError("bad_params", "Repair material permission names missing triangles")
        selected = selected & np.isin(surface.owner, patch.material_faces)
    ids, _ = surface.raster(patch.camera.view(), size)
    pixels, visible, _, _ = surface.mapping(patch.camera.view(), ids)
    flat_indices = np.flatnonzero(surface.covered)
    lookup = np.full(surface.size * surface.size, -1, dtype=int)
    lookup[flat_indices] = np.arange(len(flat_indices))
    targets = pairs[list(patch.pair_indices)]
    indexes = lookup[targets]
    seen = (indexes >= 0).all(1)
    seen &= visible[indexes.clip(0)].all(1)
    points = pixels[indexes[seen]].reshape(-1, 2)
    seeds = np.zeros((size, size), np.uint8)
    xy = np.floor(points * size).astype(int).clip(0, size - 1)
    seeds[xy[:, 1], xy[:, 0]] = 1
    allowed = surface.screen_permission(patch.camera.view(), selected, size) & (np.asarray(picture)[..., 3] == 255)
    allowed = cv2.erode(allowed.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    core_width, outer_width = (49, 97) if feature_scale else (25, 65)
    core_width = round(core_width * patch.context_zoom) | 1
    outer_width = round(outer_width * patch.context_zoom) | 1
    core = (cv2.dilate(seeds, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (core_width, core_width))) > 0) & allowed
    outer = (cv2.dilate(seeds, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (outer_width, outer_width))) > 0) & allowed
    if connected_only:
        _, labels = cv2.connectedComponents(core.astype(np.uint8), connectivity=4)
        supported = np.unique(labels[(seeds > 0) & core])
        core &= np.isin(labels, supported[supported > 0])
        _, labels = cv2.connectedComponents(outer.astype(np.uint8), connectivity=4)
        supported = np.unique(labels[core])
        outer &= np.isin(labels, supported[supported > 0])
    return core, outer, seeds > 0, ids


def project_patch(surface: Surface, base: np.ndarray, selected: np.ndarray, patch: FinishPatch,
                  source: np.ndarray, generated: np.ndarray, cut: np.ndarray, ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pixels, visible, _, _ = surface.mapping(patch.camera.view(), ids)
    xy = np.floor(pixels * len(cut)).astype(int).clip(0, len(cut) - 1)
    allowed = visible & selected[surface.covered] & cut[xy[:, 1], xy[:, 0]]
    from steps._sampling_plan import face_footprints
    footprints = face_footprints(surface, patch.camera.view(), len(cut))[surface.ids] if patch.footprint_filter else None
    sampled = sample_replacement(source[..., :3], generated[..., :3], pixels, ids, surface.ids,
                                 cut, source[..., 3] == 255,
                                 footprints=footprints, eligible=allowed)
    allowed &= sampled.supported
    permission = np.zeros_like(selected)
    permission[surface.covered] = allowed
    result = base.copy()
    rgb = base[surface.covered, :3].astype(np.float64)
    changed = allowed & sampled.changed
    rgb[changed] = np.rint(sampled.values[changed] * (surface.channel_max / 255)).clip(0, surface.channel_max)
    result[surface.covered, :3] = rgb.astype(base.dtype)
    return result, permission


def registered_targets(surface: Surface, selected: np.ndarray, patch: FinishPatch, pairs: np.ndarray,
                       picture: Image.Image, core: np.ndarray, ids: np.ndarray) -> np.ndarray:
    original = np.asarray(picture).copy()
    marker = original.copy()
    marker[core, :3] = [35, 210, 105]
    _, permission = project_patch(surface, surface.base, selected, patch, original, marker, core, ids)
    return permission.ravel()[pairs[list(patch.pair_indices)]].all(1)


def build_plan(surface: Surface, out: Path, params: dict) -> dict:
    settings = FinishSettings.from_dict(params["finish_settings"])
    selected = surface.covered.copy()
    if params.get("mask_version"):
        folder = version_dir(surface.source.parent, params["mask_version"])
        with Image.open(library.resolve_output(folder, "mask")) as image:
            selected = np.asarray(image.convert("L")) > 0
        if selected.shape != surface.covered.shape:
            raise StepError("bad_params", "Finishing selection does not match the atlas")
        selected &= surface.covered
    elif params.get("initial_faces") is not None:
        selected &= np.isin(surface.owner, params["initial_faces"])
    if any(face >= len(surface.mesh.faces) for face in settings.protected_faces):
        raise StepError("bad_params", "Protected face is outside this mesh")
    selected &= ~np.isin(surface.owner, settings.protected_faces)
    if not selected.any():
        raise StepError("bad_params", "Finishing has no permitted surface texels")
    progress(0.05, "Tracing writer boundaries across the surface and split UV edges")
    pairs, severity, _, stats = seam_graph(surface, selected)
    authoring = params.get("authoring_profile")
    material_boundaries = 0
    material_labels = np.zeros(len(surface.mesh.faces), dtype=np.int32)
    if authoring is not None and len(pairs):
        for label, material in enumerate(authoring["materials"], start=1):
            if material["faces"] is not None:
                assigned = np.asarray(material["faces"], dtype=np.int64)
                if np.any(assigned >= len(material_labels)):
                    raise StepError("bad_params", "Material selection names missing triangles")
                material_labels[assigned] = label
        endpoint_labels = material_labels[surface.owner.ravel()[pairs]]
        intentional = endpoint_labels[:, 0] != endpoint_labels[:, 1]
        material_boundaries = int(intentional.sum())
        pairs, severity = pairs[~intentional], severity[~intentional]
    stats["protected_material_boundaries"] = material_boundaries
    components = _components(surface, pairs)
    camera_rows = cameras(surface, surface.covered, params["front_yaw"])
    bindings = tuple(FinishCamera(row["id"], **row["view"]) for row in camera_rows)
    covered_flat = np.flatnonzero(surface.covered)
    lookup = np.full(surface.size * surface.size, -1, dtype=int)
    lookup[covered_flat] = np.arange(len(covered_flat))
    indexes = lookup[pairs]
    choices = []
    reachable = np.zeros(len(pairs), dtype=bool)
    texels_visible = np.zeros(len(surface.ids), dtype=bool)
    for number, camera in enumerate(bindings):
        progress(0.1 + number * 0.5 / len(bindings), f"Checking both seam sides from camera {number + 1}/{len(bindings)}")
        ids, _ = surface.raster(camera.view(), 1024)
        pixels, visible, facing, border = surface.mapping(camera.view(), ids)
        texels_visible |= visible & selected[surface.covered]
        seen = visible[indexes].all(1) & (border[indexes].min(1) > 0.035)
        reachable |= seen
        score = severity * facing[indexes].min(1).clip(0, 1) ** 2 * border[indexes].min(1)
        choices.append((camera, seen, score, pixels[indexes].mean(1)))
    remaining = reachable.copy()
    patches = []
    marker = surface.base.copy()
    marker_permission = np.zeros_like(selected)
    patch_support = []
    rejected_regions = 0
    covered_by_planned_cores = 0
    registration_rejections = 0
    sampling_rejections = 0
    camera_visibility = {camera.id: seen for camera, seen, _, _ in choices}
    for _ in range(settings.max_patches * 4):
        if len(patches) >= settings.max_patches:
            break
        best = None
        best_score = 0.0
        for camera, seen, score, points in choices:
            eligible = seen & remaining
            for component in np.unique(components[eligible]):
                members = np.flatnonzero(eligible & (components == component))
                anchor = members[np.argmax(score[members])]
                members = members[(np.abs(points[members] - points[anchor]).max(1) * 1024) < 112]
                total = float(score[members].sum())
                if len(members) < 8 or total <= best_score:
                    continue
                best, best_score = (camera, members, int(component)), total
        if best is None:
            break
        camera, members, component = best
        material_faces = None
        if authoring is not None:
            region = material_labels[surface.owner.ravel()[pairs[members[0], 0]]]
            members = members[(material_labels[surface.owner.ravel()[pairs[members]]] == region).all(1)]
            material_faces = tuple(int(face) for face in np.flatnonzero(material_labels == region))
        patch = FinishPatch(f"p{len(patches):02}", camera, tuple(int(i) for i in members), component, best_score,
                            material_faces=material_faces, footprint_filter=True)
        picture, _ = surface.render(camera.view(), size=1024)
        core, outer, _, ids = patch_masks(surface, selected, patch, pairs, picture, connected_only=True, feature_scale=True)
        count, labels, regions, _ = cv2.connectedComponentsWithStats(core.astype(np.uint8), connectivity=4)
        if count > 2:
            largest = int(np.argmax(regions[1:, cv2.CC_STAT_AREA])) + 1
            pixel, _, _, _ = surface.mapping(camera.view(), ids)
            endpoints = np.floor(pixel[indexes[members]] * 1024).astype(int).clip(0, 1023)
            keep = (labels[endpoints[..., 1], endpoints[..., 0]] == largest).all(1)
            camera_visibility[camera.id][members[~keep]] = False
            members = members[keep]
            if len(members) < 8:
                rejected_regions += 1
                camera_visibility[camera.id][list(patch.pair_indices)] = False
                continue
            patch = replace(patch, pair_indices=tuple(int(i) for i in members))
            core, outer, _, ids = patch_masks(surface, selected, patch, pairs, picture, connected_only=True, feature_scale=True)
        if outer.any():
            yy, xx = np.nonzero(outer)
            area = (int(xx.max() - xx.min()) + 5) * (int(yy.max() - yy.min()) + 5)
            zoom = max(1.0, min(2.0, float(np.sqrt(130_000 / area))))
            center = tuple(float(v) for v in surface.points[indexes[members]].mean((0, 1)))
            camera = replace(camera, center=center, extent=camera.extent / zoom)
            patch = replace(patch, camera=camera, context_zoom=zoom)
            picture, _ = surface.render(camera.view(), size=1024)
            core, outer, _, ids = patch_masks(surface, selected, patch, pairs, picture,
                                            connected_only=True, feature_scale=True)
        registered = registered_targets(surface, selected, patch, pairs, picture, core, ids)
        registration_rejections += int((~registered).sum())
        camera_visibility[camera.id][members[~registered]] = False
        members = members[registered]
        if len(members) < 8:
            rejected_regions += 1
            camera_visibility[camera.id][list(patch.pair_indices)] = False
            continue
        patch = replace(patch, pair_indices=tuple(int(i) for i in members))
        core, outer, _, ids = patch_masks(surface, selected, patch, pairs, picture,
                                        connected_only=True, feature_scale=True)
        if not registered_targets(surface, selected, patch, pairs, picture, core, ids).all():
            rejected_regions += 1
            camera_visibility[camera.id][members] = False
            continue
        if authoring is not None and authoring["sampling"]["mode"] == "detail":
            from steps._sampling_plan import face_sampling
            ratios = face_sampling(surface, patch.camera.view(), 1024)
            target_faces = surface.owner.ravel()[pairs[list(patch.pair_indices)]]
            if np.any(ratios[target_faces, 1] < authoring["sampling"]["minimum_samples"]):
                sampling_rejections += 1
                camera_visibility[camera.id][members] = False
                continue
        if (int(core.sum()) < 64 or int(outer.sum()) < int(core.sum()) + 128
                or cv2.connectedComponents(core.astype(np.uint8), connectivity=4)[0] != 2):
            rejected_regions += 1
            camera_visibility[camera.id][members] = False
            continue
        yy, xx = np.nonzero(outer)
        graph_pixels = (int(xx.max() - xx.min()) + 3) * (int(yy.max() - yy.min()) + 3)
        if graph_pixels > 160_000 or min(int(xx.min()), int(yy.min()), 1023 - int(xx.max()), 1023 - int(yy.max())) < 24:
            rejected_regions += 1
            camera_visibility[camera.id][members] = False
            continue
        remaining[members] = False
        yy, xx = np.nonzero(core)
        vertical = "upper" if yy.mean() < 1024 / 3 else "lower" if yy.mean() > 2048 / 3 else "middle"
        horizontal = "left" if xx.mean() < 1024 / 3 else "right" if xx.mean() > 2048 / 3 else "central"
        location = f"{vertical} {horizontal} area"
        if params["recipe"]["model"] == "fibo2-turbo":
            prompt = (f"Repair the texture discontinuity in the {location} of this existing painted mesh. "
                      "Continue the exact captured materials, colour, feature scale, pattern alignment and brush direction across the join. "
                      "Match the surrounding finished paint. Keep the architecture, openings, silhouette and camera framing unchanged. "
                      "One continuous painted surface without double edges or ghost strokes.")
        else:
            prompt = (f"A continuous painted surface in the {location}, matching the captured mesh's materials, palette, "
                      "feature scale, aligned patterns, brush direction and existing architecture.")
        if params["recipe"]["prompt"].strip():
            prompt += "\n\n" + params["recipe"]["prompt"].strip()
        if params.get("authoring_prompt"):
            prompt += "\n\n" + params["authoring_prompt"]
        patch = replace(patch, prompt=prompt, correction_prompt=prompt +
                        "\nMatch the existing structure closely; retain sharp small painted features and the surrounding material.")
        patches.append(patch)
        original = np.asarray(picture).copy()
        paint = original.copy()
        paint[outer, :3] = [35, 210, 105]
        _, core_permission = project_patch(surface, surface.base, selected, patch, original, paint, core, ids)
        covered_pairs = core_permission.ravel()[pairs].all(1)
        covered_by_planned_cores += int((remaining & covered_pairs).sum())
        remaining &= ~covered_pairs
        marker, permission = project_patch(surface, marker, selected, patch, original, paint, outer, ids)
        marker_permission |= permission
        patch_support.append({"id": patch.id, "core_pixels": int(core.sum()), "permission_pixels": int(outer.sum()),
                              "projected_texels": int(permission.sum()), "context_zoom": patch.context_zoom,
                              "core_projected_texels": int(core_permission.sum()),
                              "registered_target_pairs": len(patch.pair_indices),
                              "unpaintable_target_pairs": 0,
                              "graph_pixels": graph_pixels,
                              "core_faces": sorted(int(i) for i in np.unique(ids[core]) if i >= 0)})
    marker_changed = np.any(marker != surface.base, axis=2)
    if np.any(marker_changed & ~marker_permission) or np.any(marker[..., 3] != surface.base[..., 3]):
        raise StepError("failed", "Finishing marker bake changed protected texels")
    marker_texture = surface.texture.new_tensor(marker.astype(np.float32) * (255 / surface.channel_max))
    for patch in patches:
        picture, _ = surface.render(patch.camera.view(), marker_texture, 1024)
        picture.save(out / f"{patch.id}-selection.png")
    planned = {i for patch in patches for i in patch.pair_indices}
    stats.update(sampling_rejections=sampling_rejections,
                 diagnosis={"material_boundaries_preserved": material_boundaries,
                            "sampling_rejected_cameras": sampling_rejections,
                            "visual_coherence": "requires_baked_review"},
                 selected_texels=int(selected.sum()), reachable_pairs=int(reachable.sum()),
                 reachable_selected_texels=int(texels_visible.sum()), unseen_selected_texels=int(selected.sum() - texels_visible.sum()),
                 unreachable_pairs=int((~reachable).sum()), remaining_pairs=int(reachable.sum()) - len(planned),
                 planned_patches=len(patches), rejected_regions=rejected_regions,
                 core_coverage_selection="consume_visible_core_pairs_v1",
                 camera_registration="core_owned_endpoints_v1", registration_rejections=registration_rejections,
                 additional_pairs_in_planned_cores=covered_by_planned_cores)
    stats.update(marker_surface_texels=int(marker_permission.sum()), marker_outside_changed=0,
                 marker_alpha_changed=0, patch_support=patch_support)
    plan = FinishPlan(surface.source.name, params["geometry_revision"], params.get("mask_version"),
                      params["recipe"], settings, 1024, bindings, tuple(patches), stats)
    save_json(out / "plan.json", plan.to_dict())
    np.savez_compressed(out / "seams.npz", pairs=pairs, severity=severity, components=components)
    Image.fromarray(selected.astype(np.uint8) * 255).save(out / "mask.png")
    atlas = (surface.base.astype(float) * (255 / surface.channel_max)).round().astype(np.uint8)
    atlas[selected, :3] = (atlas[selected, :3] * 0.5 + [17.5, 105, 52.5]).astype(np.uint8)
    Image.fromarray(atlas).save(out / "selection_atlas.png")
    Image.fromarray((marker.astype(float) * (255 / surface.channel_max)).round().astype(np.uint8)).save(out / "marker_atlas.png")
    sheet = Image.new("RGB", (max(1, len(patches)) * 384, 408), (33, 36, 39))
    for i, patch in enumerate(patches):
        with Image.open(out / f"{patch.id}-selection.png") as image:
            sheet.paste(image.convert("RGB").resize((384, 384)), (i * 384, 24))
        ImageDraw.Draw(sheet).text((i * 384 + 8, 5), f"{patch.id}: {patch.camera.id}", fill="white")
    sheet.save(out / "review.png")
    return {"outputs": {"plan": "plan.json", "seams": "seams.npz", "mask": "mask.png",
                        "selection_atlas": "selection_atlas.png", "marker_atlas": "marker_atlas.png", "image": "review.png", "mesh": "@mesh.glb"},
            "output_refs": {"mesh": {"version": surface.source.name, "key": "mesh"}},
            "metrics": stats | {"geometry_revision": params["geometry_revision"], "triangles": len(surface.mesh.faces),
                                "texture_size": surface.size, "bit_depth": surface.base.dtype.itemsize * 8}}
