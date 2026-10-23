"""Held local model worker with durable patch checkpoints and one final draft mesh."""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageOps
from scipy.ndimage import distance_transform_edt

from server import library, reference_models
from server.finish_contracts import FINISH_ENGINE, FinishCheckpoint, FinishPatch, FinishPlan
from steps import _glb
from steps._bake import rasterize_uv
from steps._common import StepError, main, progress
from steps._finish_cut import hard_cut, image_regression
from steps._finish_plan import patch_masks, project_patch, registered_targets
from steps._paint_seams import ownership_map
from steps._paint_set import Surface, material_state, review, save_json
from steps.paint import version_dir, write_atlas
from steps.paint_generate import SheetEngine
from tools.fibo_trial_worker import primary_worker_present


def _file(folder: Path, name: str) -> Path:
    path = (folder / name).resolve()
    if not path.is_relative_to(folder.resolve()):
        raise StepError("bad_params", "Finishing checkpoint path escapes its version")
    return path


def _save_image(image: Image.Image, path: Path) -> None:
    temporary = path.with_suffix(".tmp.png")
    image.save(temporary)
    temporary.replace(path)


def _texture(surface: Surface, value: np.ndarray) -> torch.Tensor:
    return torch.tensor(value.astype(np.float32) * (255 / surface.channel_max))


def _seam_error(texture: np.ndarray, pairs: np.ndarray, scale: float) -> float:
    values = texture[..., :3].reshape(-1, 3).astype(np.float64) * scale
    return float(np.abs(values[pairs[:, 0]] - values[pairs[:, 1]]).sum(1).mean())


def _review_patch(surface: Surface, before: np.ndarray, after: np.ndarray, patch: FinishPatch,
                  path: Path, detail: bool = False) -> tuple[list[dict], tuple[str, ...]]:
    sheet = Image.new("RGB", (3 * 320, 2 * 344), (33, 36, 39))
    resolution = 1024 if detail else 320

    def inspection_view(turn: int) -> dict:
        view = patch.camera.view() | {"yaw": patch.camera.yaw + turn}
        if detail and turn and abs(view["pitch"]) > 70:
            view["pitch"] = -55 if view["pitch"] < 0 else 55
        return view

    frames: list[list[np.ndarray]] = [[], []]
    for row, atlas in enumerate((before, after)):
        texture = _texture(surface, atlas)
        for column, turn in enumerate((-20, 0, 20)):
            view = inspection_view(turn)
            picture, _ = surface.render(view, texture, resolution)
            frames[row].append(np.asarray(picture).copy())
    changed = np.any(before != after, axis=2) & surface.covered
    metrics, reasons = [], []
    for column, turn in enumerate((-20, 0, 20)):
        view = inspection_view(turn)
        mask = surface.screen_permission(view, changed, resolution) & (frames[0][column][..., 3] == 255)
        crop = (0, 0, resolution, resolution)
        if detail and mask.any():
            yy, xx = np.nonzero(mask)
            crop = (max(0, int(xx.min()) - 24), max(0, int(yy.min()) - 24),
                    min(resolution, int(xx.max()) + 25), min(resolution, int(yy.max()) + 25))
        for row in (0, 1):
            picture = Image.fromarray(frames[row][column]).crop(crop)
            frame = Image.new("RGBA", picture.size, (33, 36, 39, 255))
            frame.alpha_composite(picture)
            thumb = ImageOps.contain(frame.convert("RGB"), (320, 320), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (column * 320 + (320 - thumb.width) // 2, row * 344 + 24 + (320 - thumb.height) // 2))
            label = f"{'Before' if row == 0 else 'Draft'}{' detail' if detail else ''} / yaw {view['yaw']:g}"
            ImageDraw.Draw(sheet).text((column * 320 + 8, row * 344 + 5), label, fill="white")
        if int(mask.sum()) < 32:
            metrics.append({"yaw": view["yaw"], "pitch": view["pitch"], "checked": False, "visible_pixels": int(mask.sum()), "render_resolution": resolution})
            continue
        values, failed = image_regression(frames[0][column], frames[1][column], mask)
        metrics.append(values | {"yaw": view["yaw"], "pitch": view["pitch"], "checked": True, "visible_pixels": int(mask.sum()), "render_resolution": resolution})
        reasons.extend(f"view{turn:+}_{reason}" for reason in failed)
    _save_image(sheet, path)
    return metrics, tuple(reasons)


def _runtime_receipt(engine: SheetEngine) -> dict:
    formats: Counter[str] = Counter()
    for module in engine.model.model.modules():
        name = getattr(module, "quant_format", None)
        if name is not None:
            path = "full_precision_mm" if getattr(module, "_full_precision_mm", False) else "quantized_mm_enabled"
            formats[f"{name}:{path}"] += 1
    files = reference_models.paths(engine.choice)
    return {"model": engine.model_id, "file": files.weights.name, "bytes": files.weights.stat().st_size,
            "encoders": [p.name for p in files.encoders], "vae": files.vae.name, "engine_version": engine.engine_version,
            "torch_version": torch.__version__, "cuda_version": torch.version.cuda, "device": torch.cuda.get_device_name(0),
            "weight_dtype": str(engine.model.model.get_dtype()), "inference_dtype": str(engine.model.model.get_dtype_inference()),
            "quantized_layers": dict(formats)}


def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    if os.environ.get("EFFIGY_MULTI_VIEW") != "1" or op != "finish" or in_dir is None:
        raise StepError("bad_params", "Automatic finishing is available only in trial8380")
    replay_only = params.get("replay_only") is True
    if not replay_only and primary_worker_present():
        raise StepError("failed", "Primary Effigy owns a model worker; finishing can resume when it is idle")
    source, out = Path(in_dir), Path(out_dir)
    asset = source.parent.resolve()
    plan_dir = version_dir(asset, params["plan_version"])
    plan = FinishPlan.from_dict(json.loads(library.resolve_output(plan_dir, "plan").read_text(encoding="utf-8")))
    if (source.name != plan.source or library.geometry_revision(source) != plan.geometry_revision
            or params["recipe"] != plan.recipe or params["model"] != plan.recipe["model"]):
        raise StepError("bad_params", "Finishing source, geometry or recipe changed")
    destination = (asset / params["run_version"]).resolve()
    if (destination.parent != asset or not library.VERSION.fullmatch(destination.name)
            or not destination.is_dir() or (destination / "meta.json").exists()):
        raise StepError("bad_params", "Finishing destination is missing, published or outside this asset")
    binding = {"engine": FINISH_ENGINE, "source": plan.source, "geometry_revision": plan.geometry_revision,
               "plan_version": plan_dir.name, "mask_version": plan.mask_version, "recipe": plan.recipe,
               "settings": plan.settings.to_dict(), "mask_policy": plan.mask_policy,
               "generation_policy": plan.generation_policy}
    if any(patch.footprint_filter for patch in plan.patches):
        binding["projection_sampling"] = "same_face_footprint_grid_v1"
    checkpoint_path = destination / "checkpoint.json"
    checkpoint = FinishCheckpoint(binding, [])
    if checkpoint_path.is_file():
        checkpoint = FinishCheckpoint.from_dict(json.loads(checkpoint_path.read_text(encoding="utf-8")),
                                                binding, {p.id for p in plan.patches})
    if ([p["id"] for p in checkpoint.patches] != [p.id for p in plan.patches[:len(checkpoint.patches)]]
            or any(p["decision"] == "pending" for p in checkpoint.patches[:-1])):
        raise StepError("bad_params", "Finishing checkpoint is not a completed sequential prefix")
    if replay_only and (len(checkpoint.patches) != len(plan.patches) or any(p["decision"] == "pending" for p in checkpoint.patches)):
        raise StepError("bad_params", "CPU finalization requires every patch to be completed")
    surface = Surface(source)
    base = surface.base.copy()
    initial = base.copy()
    owners, _, _ = ownership_map(source)
    with Image.open(library.resolve_output(plan_dir, "mask")) as image:
        selected = np.asarray(image.convert("L")) > 0
    if selected.shape != surface.covered.shape or np.any(selected & ~surface.covered):
        raise StepError("bad_params", "Finishing permission is incompatible with source UVs")
    with np.load(library.resolve_output(plan_dir, "seams"), allow_pickle=False) as data:
        pairs = data["pairs"].copy()
    if pairs.ndim != 2 or pairs.shape[1] != 2 or np.any(pairs < 0) or np.any(pairs >= base.shape[0] ** 2):
        raise StepError("bad_params", "Invalid recorded surface seam pairs")
    union_permission = np.zeros_like(selected)
    records = {record["id"]: record for record in checkpoint.patches}
    for patch in plan.patches:
        record = records.get(patch.id)
        if record is None or record["decision"] != "retained":
            continue
        with np.load(_file(destination, record["delta"]), allow_pickle=False) as data:
            indexes, rgb, writer = data["indices"], data["rgb"], data["writer"]
            if (indexes.ndim != 1 or rgb.shape != (len(indexes), 3) or writer.shape != indexes.shape
                    or not np.issubdtype(indexes.dtype, np.integer) or rgb.dtype != base.dtype
                    or len(np.unique(indexes)) != len(indexes) or np.any(writer <= 0) or np.any(writer >= 16_777_216)
                    or np.any(indexes < 0) or np.any(indexes >= base.shape[0] ** 2)
                    or not np.all(selected.ravel()[indexes])):
                raise StepError("bad_params", "Completed patch exceeds its immutable permission")
            base.reshape(-1, 4)[indexes, :3] = rgb
            owners.ravel()[indexes] = writer
            union_permission.ravel()[indexes] = True
    stop = threading.Event()

    def yield_to_primary() -> None:
        while not stop.wait(0.5):
            if primary_worker_present():
                print("Finishing yielded to primary Effigy; completed patches remain resumable.", file=sys.stderr, flush=True)
                os._exit(1)

    if not replay_only:
        threading.Thread(target=yield_to_primary, daemon=True).start()
    engine = None
    loads = 0
    load_seconds = 0.0
    runtime_receipt = None
    try:
        with torch.no_grad():
            for position, patch in enumerate(plan.patches):
                record = records.get(patch.id)
                if record is not None and record["decision"] != "pending":
                    continue
                patch_started = time.perf_counter()
                loads_before = loads
                generation_calls = 0
                if record is None:
                    record = {"id": patch.id, "decision": "pending", "attempts": [], "delta": None,
                              "material_faces": patch.material_faces}
                    checkpoint.patches.append(record)
                    records[patch.id] = record
                surface.texture = _texture(surface, base)
                picture, _ = surface.render(patch.camera.view(), size=plan.size)
                original = np.asarray(picture).copy()
                core, outer, _, ids = patch_masks(surface, selected, patch, pairs, picture,
                                                connected_only=plan.mask_policy != "legacy_v1",
                                                feature_scale=plan.mask_policy in ("feature_connected_v3", "close_context_v4"))
                targeted = pairs[list(patch.pair_indices)]
                registered = plan.coverage.get("camera_registration") == "core_owned_endpoints_v1"
                if registered and not registered_targets(surface, selected, patch, pairs, picture, core, ids).all():
                    raise StepError("bad_params", "The final repair camera no longer covers both seam sides; create a new plan")
                baseline_error = _seam_error(base, targeted, 255 / surface.channel_max)
                if int(core.sum()) < 64 or baseline_error < 12:
                    record.update(decision="skipped", reason="insufficient_core" if int(core.sum()) < 64 else "already_continuous")
                    record["timing_this_worker"] = {"seconds": round(time.perf_counter() - patch_started, 3),
                                                  "scope": "render_to_review", "mode": "skipped", "generation_calls": 0}
                    save_json(checkpoint_path, checkpoint.to_dict())
                    continue
                attempt_index = len(record["attempts"])
                if attempt_index and record["attempts"][-1].get("stage") != "evaluated":
                    attempt_index -= 1
                while True:
                    correction = attempt_index > 0
                    stem = f"{patch.id}-a{attempt_index}"
                    recipe = plan.recipe | {"feather": 0}
                    if correction:
                        recipe["conditioning"] = "preserve_structure"
                        recipe["denoise"] = min(0.35, recipe["denoise"])
                    if plan.recipe["model"] == "fibo2-turbo":
                        prompt = ("Repair the marked join on this existing painted mesh. Continue the exact captured material, colour, "
                                  "feature scale, pattern alignment and brush direction across the join. One continuous surface, with no "
                                  "double edges, ghost strokes, extra openings or changed architecture. Match the surrounding finished paint.")
                    else:
                        prompt = ("A continuous hand-painted game surface matching the captured mesh, with the same material identity, "
                                  "palette, feature scale, pattern alignment, brush direction and existing structure across the repaired join.")
                    if plan.recipe["prompt"].strip():
                        prompt += "\n\n" + plan.recipe["prompt"].strip()
                    if correction:
                        prompt += "\nMatch the existing structure closely; retain sharp small painted features and the surrounding material."
                    literal_prompt = patch.correction_prompt if correction else patch.prompt
                    if literal_prompt is not None:
                        prompt = literal_prompt
                    seed = plan.recipe["seed"] + position
                    if attempt_index == len(record["attempts"]):
                        attempt = {"stem": stem, "stage": "prepared", "seed": seed, "prompt": prompt,
                                   "recipe": recipe, "camera": patch.camera.view(), "correction": correction}
                        record["attempts"].append(attempt)
                        _save_image(picture, destination / f"{stem}-source.png")
                        _save_image(Image.fromarray(core.astype(np.uint8) * 255), destination / f"{stem}-core.png")
                        _save_image(Image.fromarray(outer.astype(np.uint8) * 255), destination / f"{stem}-permission.png")
                    else:
                        attempt = record["attempts"][attempt_index]
                        if attempt["prompt"] != prompt or attempt["seed"] != seed or attempt["recipe"] != recipe:
                            raise StepError("bad_params", "Interrupted patch recipe changed")
                    checkpoint.stage = f"{patch.id}: generation"
                    save_json(checkpoint_path, checkpoint.to_dict())
                    receipt_path = destination / f"{stem}-generation.json"
                    image_path = destination / f"{stem}-image.png"
                    if image_path.is_file() and not receipt_path.is_file():
                        raise StepError("incomplete_generation_receipt", "A generated repair image survived without its completion record. The image is preserved; inspect this attempt before starting another pass.")
                    if receipt_path.is_file():
                        generation = json.loads(receipt_path.read_text(encoding="utf-8"))
                        if generation["seed"] != seed or generation["prompt"] != prompt:
                            raise StepError("bad_params", "Generated patch receipt differs from the immutable request")
                        with Image.open(image_path) as image:
                            generated = image.convert("RGBA").copy()
                    else:
                        if engine is None:
                            progress(0.05, f"Loading {plan.recipe['model']} once for this finishing pass")
                            started = time.perf_counter()
                            engine = SheetEngine(plan.recipe["model"])
                            load_seconds += time.perf_counter() - started
                            loads += 1
                            runtime_receipt = _runtime_receipt(engine)
                            torch.cuda.reset_peak_memory_stats()
                        locked_context = plan.generation_policy == "source_locked_v1" and plan.recipe["model"] == "fibo2-turbo"
                        conditioning_mask = core if plan.recipe["model"] == "fibo2-turbo" and not locked_context else outer
                        generation_calls += 1
                        generated, metrics = engine.edit(picture, Image.fromarray(conditioning_mask.astype(np.uint8) * 255),
                                                         recipe, prompt, seed, None, 0.08 + position * 0.65 / len(plan.patches),
                                                         0.55 / len(plan.patches), composite=False, lock_context=locked_context)
                        _save_image(generated, image_path)
                        generation = {"seed": seed, "prompt": prompt, "recipe": recipe, "metrics": metrics,
                                      "runtime": runtime_receipt, "model_load_number": loads,
                                      "seconds_load_this_worker": round(load_seconds, 2),
                                      "plan_version": plan_dir.name, "run_version": destination.name,
                                      "session_id": params["session_id"],
                                      "work_unit": ("reusable-surface-authoring/S05" if params.get("authoring_profile") else "painting-completion/S10" if registered else "painting-completion/S09"
                                                    if plan.generation_policy == "source_locked_v1" else "painting-completion/S08"),
                                      "generation_policy": plan.generation_policy}
                        save_json(receipt_path, generation)
                    attempt.update(stage="generated", generation=generation["metrics"])
                    save_json(checkpoint_path, checkpoint.to_dict())
                    checkpoint.stage = f"{patch.id}: boundary and baked review"
                    progress(0.15 + (position + 1) * 0.65 / len(plan.patches), f"Evaluating hard boundary for {patch.id}")
                    raw = np.asarray(generated)
                    cut = hard_cut(original, raw, core, outer)
                    candidate, permission = project_patch(surface, base, selected, patch, original, raw, cut.mask, ids)
                    if registered and not permission.ravel()[targeted].all():
                        raise StepError("failed", "The repair cut omitted a registered seam endpoint")
                    changed = np.any(candidate != base, axis=2)
                    if np.any(changed & ~permission) or np.any(candidate[..., 3] != initial[..., 3]):
                        raise StepError("failed", "Finishing projection changed protected texels or alpha")
                    rendered, _ = surface.render(patch.camera.view(), _texture(surface, candidate), plan.size)
                    regression, reasons = image_regression(original, np.asarray(rendered), cut.mask)
                    final_error = _seam_error(candidate, targeted, 255 / surface.channel_max)
                    problems = list(cut.reasons) + list(reasons)
                    if final_error > baseline_error * 0.98:
                        problems.append("seam_not_improved")
                    if not changed.any():
                        problems.append("no_surface_change")
                    _save_image(Image.fromarray(cut.mask.astype(np.uint8) * 255), destination / f"{stem}-cut.png")
                    neighbouring_views, view_failures = _review_patch(surface, base, candidate, patch, destination / f"{stem}-review.png",
                                                                     detail=plan.generation_policy == "source_locked_v1")
                    problems.extend(view_failures)
                    attempt.update(stage="evaluated", reasons=problems,
                                   metrics=cut.metrics | regression | {"seam_before_rgb8": round(baseline_error, 4),
                                       "seam_after_rgb8": round(final_error, 4), "changed_texels": int(changed.sum()),
                                       "outside_changed": 0, "alpha_changed": 0, "baked_views_rendered": 3,
                                       "camera_registration": plan.coverage.get("camera_registration", "legacy_survey"),
                                       "unpaintable_target_pairs": int((~permission.ravel()[targeted].all(1)).sum()),
                                       "baked_views_checked": sum(v["checked"] for v in neighbouring_views),
                                       "neighbouring_views": neighbouring_views})
                    if not problems:
                        indexes = np.flatnonzero(changed)
                        used = {int(i) for i in np.unique(owners)}
                        marker = next(i for i in range(1, 16_777_216) if i not in used)
                        delta = f"{patch.id}-delta.npz"
                        temporary_delta = destination / f"{patch.id}-delta.tmp.npz"
                        np.savez_compressed(temporary_delta, indices=indexes, rgb=candidate.reshape(-1, 4)[indexes, :3],
                                            writer=np.full(len(indexes), marker, dtype=np.int64))
                        temporary_delta.replace(destination / delta)
                        base = candidate
                        owners.ravel()[indexes] = marker
                        union_permission |= permission
                        record.update(decision="retained", delta=delta, acceptance="automatic_regression_only")
                        save_json(checkpoint_path, checkpoint.to_dict())
                        break
                    if correction or checkpoint.corrections >= plan.settings.correction_budget:
                        record.update(decision="rejected", reason=", ".join(problems))
                        save_json(checkpoint_path, checkpoint.to_dict())
                        break
                    checkpoint.corrections += 1
                    attempt_index += 1
                    save_json(checkpoint_path, checkpoint.to_dict())
                record["timing_this_worker"] = {
                    "seconds": round(time.perf_counter() - patch_started, 3), "scope": "render_to_review",
                    "mode": "fresh_engine" if loads > loads_before else "reused_engine" if generation_calls else "receipt_replay",
                    "generation_calls": generation_calls, "model_loads": loads - loads_before,
                }
                save_json(checkpoint_path, checkpoint.to_dict())
        checkpoint.stage = "publishing final draft"
        save_json(checkpoint_path, checkpoint.to_dict())
        wide = (rasterize_uv(surface.uv, surface.faces, surface.size * 2)[0] >= 0).numpy().reshape(surface.size, 2, surface.size, 2).any(3).any(1)
        distance, nearest = distance_transform_edt(~surface.covered, return_indices=True)
        surface_changed = np.any(base != initial, axis=2)
        gutter = (~wide) & (distance <= 8) & surface_changed[nearest[0], nearest[1]]
        base[gutter, :3] = base[nearest[0][gutter], nearest[1][gutter], :3]
        changed = np.any(base != initial, axis=2)
        if np.any(changed & ~(selected | gutter)) or not np.array_equal(base[..., 3], initial[..., 3]):
            raise StepError("failed", "Final finishing draft violated its original permission")
        write_atlas(out, surface.doc, surface.blob, surface.material, base)
        doc, blob = _glb.read(out / "mesh.glb")
        if len(doc["accessors"]) != len(surface.original_accessors) or any(
                not np.array_equal(value, _glb.accessor(doc, blob, i)) for i, value in enumerate(surface.original_accessors)):
            raise StepError("failed", "Finishing changed geometry or UVs")
        if material_state(doc, blob, surface.material) != surface.original_materials:
            raise StepError("failed", "Finishing changed another material map")
        review(surface, base, out)
        owners[~surface.covered] = 0
        owner_rgb = np.stack((owners & 255, (owners >> 8) & 255, (owners >> 16) & 255), axis=-1).astype(np.uint8)
        Image.fromarray(owner_rgb).save(out / "owners.png")
        Image.fromarray((union_permission | gutter).astype(np.uint8) * 255).save(out / "permission.png")
        summary = checkpoint.to_dict()
        unresolved = set()
        for patch in plan.patches:
            record = records[patch.id]
            if record["decision"] == "rejected" or (record["decision"] == "skipped" and record.get("reason") != "already_continuous"):
                unresolved.update(patch.pair_indices)
        summary.update(stage="complete", remaining_plan_pairs=plan.coverage["remaining_pairs"],
                       rejected_or_skipped_pairs=len(unresolved),
                       unaddressed_reachable_pairs=plan.coverage["remaining_pairs"] + len(unresolved),
                       unreachable_pairs=plan.coverage["unreachable_pairs"], model_loads_this_job=loads,
                       seconds_load_this_job=round(load_seconds, 2), art_acceptance="pending_visual_review")
        save_json(out / "finish.json", summary)
        files = ("mesh.glb", "basecolor.png", "review.png", "turntable.gif", "owners.png", "permission.png", "finish.json")
        for name in files:
            target = destination / name
            temporary = target.with_name(target.name + ".tmp")
            shutil.copyfile(out / name, temporary)
            temporary.replace(target)
        identity = reference_models.paths(reference_models.get(plan.recipe["model"]))
        payload = {"outputs": {"mesh": "mesh.glb", "basecolor": "basecolor.png", "image": "review.png", "writers": "owners.png",
                               "turntable": "turntable.gif", "owners": "owners.png", "permission": "permission.png", "finish": "finish.json"},
                   "models": [{"id": plan.recipe["model"], "file": identity.weights.name, "bytes": identity.weights.stat().st_size}],
                   "metrics": {"completed_patches": summary["completed"], "retained_patches": summary["accepted"],
                               "rejected_patches": summary["rejected"], "corrections": summary["corrections"],
                               "model_loads_this_job": loads, "geometry_uv_equal": True, "other_materials_equal": True,
                               "outside_changed": 0, "alpha_changed": 0, "changed_texels": int(changed.sum()),
                               "gutter_texels": int((gutter & changed).sum()), "texture_size": surface.size,
                               "bit_depth": surface.base.dtype.itemsize * 8, "triangles": len(surface.mesh.faces),
                               "geometry_revision": plan.geometry_revision, "device": "cuda:0" if loads else "replayed",
                               "art_acceptance": "pending_visual_review",
                               "projection_transfer": "replace_changed_v4" if any(p.footprint_filter for p in plan.patches) else "replace_changed_v3"}}
        save_json(destination / "finish_result.json", payload)
        checkpoint.stage = "complete"
        save_json(checkpoint_path, checkpoint.to_dict())
        save_json(out / "batch.json", {"run_version": destination.name, "completed_patches": summary["completed"]})
        for name in files:
            (out / name).unlink()
        return {"outputs": {"batch": "batch.json", "mesh": "@mesh.glb"},
                "output_refs": {"mesh": {"version": source.name, "key": "mesh"}},
                "metrics": {"run_version": destination.name, "model_loads": loads, "completed_patches": summary["completed"]}}
    finally:
        stop.set()
        if engine is not None and os.environ.get("EFFIGY_ONE_SHOT_FINISH") != "1":
            engine.management.unload_all_models()


if __name__ == "__main__":
    main(run)
