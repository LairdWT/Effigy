"""One admitted native worker edits immutable registered view sheets."""
from __future__ import annotations

import os
import sys
import threading
import time
import traceback
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from scipy.ndimage import distance_transform_edt

from server import library, reference_models
from server.paint_contracts import AdapterInput, ViewLayout, group_layout
from steps._common import StepError, budget_gb, main, progress
from steps._paint_set import Surface, read_manifest, save_json
from steps._uv_transfer import bind_triangles
from steps.paint import version_dir
from tools.fibo_trial_worker import primary_worker_present


def _sheet(capture: Path, mask_dir: Path, layout: ViewLayout) -> tuple[Image.Image, Image.Image]:
    picture = Image.new("RGBA", (layout.width, layout.height))
    mask = Image.new("L", picture.size)
    for panel in layout.panels:
        with Image.open(capture / "views" / f"{panel.camera_id}.png") as image:
            if image.size != (panel.width, panel.height):
                raise StepError("bad_params", "Capture panel dimensions changed")
            picture.paste(image.convert("RGBA"), (panel.x, panel.y))
        with Image.open(mask_dir / "selections" / f"{panel.camera_id}.png") as selection:
            if selection.size != (panel.width, panel.height):
                raise StepError("bad_params", "Selection panel dimensions changed")
            mask.paste(selection.convert("L"), (panel.x, panel.y))
    return picture, mask


class SheetEngine:
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.choice = reference_models.get(model_id)
        runtime = reference_models.runtime_for_model(model_id)
        sys.path.insert(0, str(runtime.source))
        self.lora_coverage = []
        if model_id in ("krea-genesis", "moss-turbo"):
            from steps.reference import _load

            loaded = _load(self.choice)
            self.model, self.clip, self.vae = loaded.model, loaded.clip, loaded.vae
            self.management = loaded.management
            self.sampling = loaded.sampling
            self.engine_version = loaded.engine_version
            self.lora_coverage = [{"file": item.file, "tensor_keys": item.tensor_keys,
                                   "applied_modules": item.applied_modules} for item in loaded.lora_coverage]
        else:
            from comfy.cli_args import args

            args.disable_dynamic_vram = True
            args.disable_all_custom_nodes = True
            args.disable_api_nodes = True
            args.enable_manager = False
            args.base_directory = str(Path(os.environ["EFFIGY_SCRATCH"]) / "native-reference")
            import comfyui_version
            from comfy import model_management, sample, sd, utils

            files = reference_models.paths(self.choice)
            self.model = sd.load_diffusion_model(str(files.weights), disable_dynamic=True)
            self.clip = sd.load_clip([str(p) for p in files.encoders], clip_type=sd.CLIPType.FIBO2, disable_dynamic=True)
            self.vae = sd.VAE(sd=utils.load_torch_file(str(files.vae)))
            self.management, self.sampling = model_management, sample
            self.engine_version = comfyui_version.__version__
        budget = budget_gb()
        if budget is None or not torch.cuda.is_available() or torch.cuda.current_device() != 0:
            raise StepError("failed", "Multi-view generation requires admitted CUDA-0 memory")
        total = torch.cuda.get_device_properties(0).total_memory
        self.management.EXTRA_RESERVED_VRAM = max(2 * 2**30, total - budget * 2**30)

    def edit(self, source: Image.Image, mask: Image.Image, recipe: dict, prompt: str,
             seed: int, style: Image.Image | None, progress_start: float, progress_span: float,
             composite: bool = True, lock_context: bool = False) -> tuple[Image.Image, dict]:
        full = Image.alpha_composite(Image.new("RGBA", source.size, "white"), source).convert("RGB")
        values = np.asarray(mask).astype(np.float32) / 255
        if recipe["feather"]:
            values *= np.minimum(distance_transform_edt(values > 0) / recipe["feather"], 1)
        sampling_model = self.model
        if self.model_id == "fibo2-turbo":
            from comfy_extras.nodes_fibo2 import TextEncodeFibo2

            context = full
            if recipe["conditioning"] == "blank_region":
                context = Image.composite(Image.new("RGB", full.size, (128, 128, 128)), full, mask)
            references = {"image_1": torch.from_numpy(np.asarray(context).astype(np.float32) / 255)[None]}
            if style is not None:
                references["image_2"] = torch.from_numpy(np.asarray(style).astype(np.float32) / 255)[None]
            positive, negative, latent_record = TextEncodeFibo2.execute(
                self.clip, prompt, vae=self.vae, images=references, width=source.width, height=source.height)
            latent, steps, denoise, noise_mask = latent_record["samples"], 4, 1.0, None
            if lock_context:
                pixels = torch.from_numpy(np.asarray(full).astype(np.float32) / 255)[None]
                latent = self.vae.encode(pixels)
                noise_mask = torch.from_numpy(values)[None]
        else:
            from comfy_extras.nodes_differential_diffusion import DifferentialDiffusion

            pixels = torch.from_numpy(np.asarray(full).astype(np.float32) / 255)[None]
            latent = self.vae.encode(pixels)
            positive = self.clip.encode_from_tokens_scheduled(self.clip.tokenize(prompt))
            negative = [[torch.zeros_like(v), {**m, **({"pooled_output": torch.zeros_like(m["pooled_output"])}
                         if m.get("pooled_output") is not None else {})}] for v, m in positive]
            sampling_model = self.model.clone()

            def differential(sigma: object, mask: torch.Tensor, extra_options: dict) -> torch.Tensor:
                return DifferentialDiffusion.forward(sigma, mask, extra_options, strength=1.0) * (mask > 0)

            sampling_model.set_model_denoise_mask_function(differential)
            steps = recipe.get("moss_steps", 8) if self.model_id == "moss-turbo" else 8
            if steps not in (4, 6, 8):
                raise StepError("bad_params", "MOSS sampling requires4,6 or8 steps")
            denoise, noise_mask = recipe["denoise"], torch.from_numpy(values)[None]
        latent = self.sampling.fix_empty_latent_channels(sampling_model, latent)
        protected_source_latent = latent.detach().clone() if lock_context else None
        noise = self.sampling.prepare_noise(latent, seed)
        started = time.perf_counter()

        def sampled(step: int, _clean: torch.Tensor, _noisy: torch.Tensor, total: int) -> None:
            progress(progress_start + progress_span * (step + 1) / total,
                     f"{self.model_id}: complete sheet step {step + 1}/{total}")

        output = self.sampling.sample(sampling_model, noise, steps, 1.0, "euler", "simple", positive,
                                      negative, latent, denoise=denoise, seed=seed, noise_mask=noise_mask,
                                      disable_pbar=True, callback=sampled)
        protected_latent_error = None
        if lock_context:
            protected = torch.nn.functional.adaptive_max_pool2d(noise_mask[:, None], latent.shape[-2:]) == 0
            error = (output - protected_source_latent.to(output)).abs() * protected.to(output)
            protected_latent_error = float(error.max().item())
            if not np.isfinite(protected_latent_error) or protected_latent_error > 1e-4:
                raise StepError("failed", f"Masked denoising changed protected source latents: {protected_latent_error:g}")
        progress(progress_start + progress_span, "Decoding the complete sheet and preserving unselected pixels")
        decoded = self.vae.decode(output)
        if decoded.ndim == 5:
            decoded = decoded.reshape(-1, *decoded.shape[-3:])
        if not torch.isfinite(decoded).all():
            raise StepError("failed", "Model returned non-finite pixels")
        generated = Image.fromarray((decoded[0].clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)).convert("RGBA")
        if generated.size != source.size:
            raise StepError("failed", "Model changed the fixed panel dimensions")
        blend = Image.fromarray((values * 255).round().astype(np.uint8))
        result = Image.composite(generated, source, blend) if composite else generated
        result.putalpha(source.getchannel("A"))
        before, after = np.asarray(source), np.asarray(result)
        outside = int(np.any(after != before, axis=2)[np.asarray(mask) == 0].sum())
        if (composite and outside) or np.any(after[..., 3] != before[..., 3]):
            raise StepError("failed", "Paired editing changed protected pixels")
        torch.cuda.synchronize()
        return result, {"steps": steps, "denoise": denoise, "seconds_sample": round(time.perf_counter() - started, 2),
                        "source_locked_latents": lock_context, "protected_latent_max_error": protected_latent_error,
                        "protected_changed": 0 if composite else None, "raw_candidate": not composite,
                        "outside_candidate_changed": outside, "alpha_changed": 0,
                        "peak_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 3)}


def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    if os.environ.get("EFFIGY_MULTI_VIEW") != "1":
        raise StepError("bad_params", "Multi-view generation is enabled only in the isolated trial")
    if op != "generate" or in_dir is None:
        raise StepError("bad_params", "Paired generation needs a captured paint session")
    if primary_worker_present():
        raise StepError("failed", "Primary Effigy owns a model worker; trial generation leaves it unchanged")
    source, out = Path(in_dir), Path(out_dir)
    if source.name != params["source"] or library.geometry_revision(source) != params["geometry_revision"]:
        raise StepError("bad_params", "Candidate source geometry changed")
    asset = source.parent.resolve()
    capture = version_dir(asset, params["capture"])
    mask_dir = version_dir(asset, params["mask_version"])
    manifest = read_manifest(mask_dir)
    groups = {g["id"]: g for g in manifest["groups"]}
    if params.get("strategy") == "whole_sheet":
        groups = {a["id"]: a["params"]["group"] for a in params["allocated"]}
        expected = set(manifest["working_views"])
        if len(groups) != 1 or set(groups["complete"]["views"]) != expected:
            raise StepError("bad_params", "Whole-sheet candidate must include the complete recorded working set")
        panel_size = manifest.get("panel_size", 512)
        if params.get("panel_size", 512) != panel_size or any(
                p.width != panel_size for p in group_layout(groups["complete"]).panels):
            raise StepError("bad_params", "Candidate camera size differs from its immutable captures")
    recipe = params["recipe"]
    donor = None
    profile = params.get("authoring_profile")
    if profile and profile["operation"] == "restore_source":
        donors = [row["version"] for row in profile["sources"] if row["role"] == "donor"]
        if len(donors) != 1:
            raise StepError("bad_params", "Restore source requires one registered donor")
        donor = Surface(version_dir(asset, donors[0]))
        bind_triangles(donor, Surface(source))
    instruction_edit = recipe["model"] == "fibo2-turbo"
    channels = ("materials", "style", "preserve", "prompt") if instruction_edit else ("materials", "style", "prompt")
    prompt = "\n\n".join(recipe[key].strip() for key in channels if recipe[key].strip())
    if params.get("authoring_prompt"):
        prompt = params["authoring_prompt"] + "\n\n" + prompt
    if not prompt:
        raise StepError("bad_params", "Enter the shared appearance or requested change")
    if recipe["model"] != params["model"]:
        raise StepError("bad_params", "Worker model differs from the session recipe")
    style = None
    if recipe["style_image"] is not None:
        if recipe["model"] != "fibo2-turbo" or recipe["conditioning"] != "preserve_structure":
            raise StepError("bad_params", "A style image requires FIBO structure-preserving mode")
        style_dir = version_dir(asset, recipe["style_image"])
        with Image.open(library.resolve_output(style_dir, "image")) as image:
            style = image.convert("RGB")
    stop = threading.Event()

    def yield_to_primary() -> None:
        while not stop.wait(0.5):
            if not primary_worker_present():
                continue
            print("Trial batch yielding: primary Effigy started a model worker.", file=sys.stderr, flush=True)
            os._exit(1)

    threading.Thread(target=yield_to_primary, daemon=True).start()
    try:
        progress(0.02, f"Loading {recipe['model']} once for the submitted view set")
        loading_started = time.perf_counter()
        engine = SheetEngine(recipe["model"])
        seconds_load = time.perf_counter() - loading_started
        quantized_layers: Counter[str] = Counter()
        for module in engine.model.model.modules():
            quant_format = getattr(module, "quant_format", None)
            if quant_format is None:
                continue
            precision = "full_precision_mm" if getattr(module, "_full_precision_mm", False) else "quantized_mm_enabled"
            quantized_layers[f"{quant_format}:{precision}"] += 1
        files = reference_models.paths(engine.choice)
        model_identity = {"id": recipe["model"], "file": files.weights.name, "bytes": files.weights.stat().st_size,
                          "encoders": [p.name for p in files.encoders], "vae": files.vae.name}
        torch.cuda.reset_peak_memory_stats()
        completed = []
        with torch.no_grad():
            for index, allocation in enumerate(params["allocated"]):
                group = groups.get(allocation["id"])
                if group is None:
                    raise StepError("bad_params", "Group is absent from this fixed mask revision")
                destination = (asset / allocation["version"]).resolve()
                if destination.parent != asset or not destination.is_dir() or (destination / "meta.json").exists():
                    raise StepError("bad_params", "Group destination is missing, published or outside the asset")
                layout = group_layout(group)
                binding = AdapterInput(allocation["params"].get("candidate_id", allocation["version"]),
                                       params.get("strategy", "pairs"), source.name, params["geometry_revision"],
                                       capture.name, mask_dir.name, layout, recipe["seed"])
                picture, mask = _sheet(capture, mask_dir, layout)
                if donor is not None:
                    bindings = {row["id"]: row["view"] for row in manifest["views"]}
                    for panel in layout.panels:
                        source_image, _ = donor.render(bindings[panel.camera_id], size=panel.width)
                        box = (panel.x, panel.y, panel.x + panel.width, panel.y + panel.height)
                        picture.paste(Image.composite(source_image, picture.crop(box), mask.crop(box)), (panel.x, panel.y))
                if mask.getbbox() is None:
                    raise StepError("bad_params", "Pair has no selected pixels")
                if params.get("strategy", "pairs") != "pairs":
                    arrangement = f"A fixed {layout.width // layout.panels[0].width}-column contact sheet containing {len(layout.panels)} orthographic views of one mesh. "
                    if instruction_edit:
                        context = arrangement + "Edit selected surfaces consistently across every panel. Keep exact panel positions, camera framing, silhouette, material boundaries and blank cells unchanged. Match the declared feature scale, material identity and palette throughout."
                    else:
                        context = arrangement + "The same declared material identities, feature scale, palette and painted marks across every view, with unchanged camera framing and surface boundaries."
                elif instruction_edit:
                    context = ("Two fixed orthographic views of the same textured mesh, arranged left and right. "
                               "Keep both panel positions, camera angles, framing, silhouette and material boundaries unchanged. "
                               "Use the same material scale, palette and painted finish in both panels.")
                else:
                    context = ("Two side-by-side orthographic views of the same textured game mesh. "
                               "Matching material scale, palette and painted finish across both panels.")
                group_prompt = context + "\n\n" + prompt
                instruction = allocation["params"].get("instruction", "").strip()
                if instruction:
                    group_prompt += "\n\nFor this pair: " + instruction
                progress(0.08 + index * 0.84 / len(params["allocated"]), f"Editing view set {index + 1}/{len(params['allocated'])}: {group['id']}")
                seed = recipe["seed"] + sorted(groups).index(group["id"])
                result, metrics = engine.edit(picture, mask, recipe, group_prompt, seed, style,
                                              0.08 + index * 0.84 / len(params["allocated"]),
                                              0.75 / len(params["allocated"]))
                result.save(destination / "image.png")
                mask.save(destination / "write_mask.png")
                payload = {"outputs": {"image": "image.png", "write_mask": "write_mask.png", "mesh": "@mesh.glb"},
                           "output_refs": {"mesh": {"version": source.name, "key": "mesh"}},
                           "models": [model_identity],
                           "metrics": metrics | {"prompt": group_prompt, "seed": seed, "views": group["views"],
                                                 "model": recipe["model"], "width": layout.width, "height": layout.height,
                                                 "strategy": binding.strategy, "candidate_id": binding.candidate_id,
                                                 "layout": layout.to_dict(), "lora_coverage": engine.lora_coverage,
                                                 "weight_dtype": str(engine.model.model.get_dtype()),
                                                 "inference_dtype": str(engine.model.model.get_dtype_inference()),
                                                 "admission_free_gib": params.get("admission_free_gib"),
                                                 "admission_floor_gib": params.get("admission_floor_gib"),
                                                 "prompt_kind": "image_edit_instruction" if instruction_edit else "img2img_scene",
                                                 "preservation": recipe["preserve"],
                                                 "seconds_load": round(seconds_load, 2), "quantized_layers": dict(quantized_layers),
                                                 "engine_version": engine.engine_version, "torch_version": torch.__version__,
                                                 "cuda_version": torch.version.cuda, "device": torch.cuda.get_device_name(0),
                                                 "geometry_revision": params["geometry_revision"]}}
                save_json(destination / "group_result.json", payload)
                completed.append(allocation["version"])
        save_json(out / "batch.json", {"groups": completed, "model": recipe["model"]})
        return {"outputs": {"batch": "batch.json", "mesh": "@mesh.glb"},
                "output_refs": {"mesh": {"version": source.name, "key": "mesh"}},
                "metrics": {"completed_groups": completed, "model_loads": 1, "device": "cuda:0"}}
    except Exception:
        traceback.print_exc(file=sys.stderr)
        raise
    finally:
        stop.set()


if __name__ == "__main__":
    main(run)
