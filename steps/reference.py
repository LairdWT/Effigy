"""Generate and edit local references consumed by mesh and texture steps."""
from __future__ import annotations

import gc
import importlib.util
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from PIL import Image

from server import reference_models
from steps._common import StepError, budget_gb, main, progress


@dataclass(frozen=True, slots=True)
class LoRACoverage:
    file: str
    tensor_keys: int
    applied_modules: int


@dataclass(frozen=True, slots=True)
class LoadedModel:
    key: str
    model: Any
    clip: Any
    vae: Any
    management: Any
    sampling: Any
    engine_version: str
    lora_coverage: tuple[LoRACoverage, ...]


_CACHE: list[LoadedModel] = []


def _load(choice: reference_models.ReferenceModel) -> LoadedModel:
    files: reference_models.ReferenceFiles | None = None
    if os.environ.get("EFFIGY_MULTI_VIEW") == "1":
        try:
            files = reference_models.paths(choice)
        except (FileNotFoundError, PermissionError) as error:
            raise StepError("missing_input", str(error)) from error
    runtime = reference_models.runtime(choice.id)
    if str(runtime.source) not in sys.path:
        sys.path.insert(0, str(runtime.source))
    from comfy.cli_args import args

    args.disable_dynamic_vram = True
    args.disable_all_custom_nodes = True
    args.disable_api_nodes = True
    args.enable_manager = False
    args.base_directory = str(Path(os.environ["EFFIGY_SCRATCH"]) / "native-reference")
    import comfy.model_management as management
    import comfy.sample as sampling
    import comfyui_version
    from comfy import lora as lora_api
    from comfy import lora_convert, sd, utils

    budget: float | None = budget_gb()
    if budget is None or not torch.cuda.is_available() or torch.cuda.current_device() != 0:
        raise StepError("failed", "Reference models require an Effigy CUDA-0 job with a GPU budget")
    total: int = torch.cuda.get_device_properties(0).total_memory
    management.EXTRA_RESERVED_VRAM = max(2 * 2**30, total - budget * 2**30)
    if _CACHE and _CACHE[0].key == choice.id:
        return _CACHE[0]
    if _CACHE:
        management.unload_all_models()
        _CACHE.clear()
        gc.collect()
        torch.cuda.empty_cache()
    if files is None:
        files = reference_models.paths(choice)
    weights: Path = files.weights
    progress(0.03, f"loading {choice.label}")
    if choice.architecture in ("flux", "qwen"):
        plugin_path: Path = runtime.source / "custom_nodes" / "ComfyUI-GGUF" / "__init__.py"
        spec = importlib.util.spec_from_file_location(
            "effigy_reference_gguf", plugin_path, submodule_search_locations=[str(plugin_path.parent)]
        )
        if spec is None or spec.loader is None or not plugin_path.is_file():
            raise StepError("missing_input", "Configured native GGUF loader is missing")
        plugin = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = plugin
        spec.loader.exec_module(plugin)
        import folder_paths

        folder_paths.add_model_folder_path("diffusion_models", str(weights.parent))
        folder_paths.add_model_folder_path("unet", str(weights.parent))
        model = plugin.NODE_CLASS_MAPPINGS["UnetLoaderGGUF"]().load_unet(weights.name)[0]
        clip_type = sd.CLIPType.FLUX if choice.architecture == "flux" else sd.CLIPType.QWEN_IMAGE
    else:
        model = sd.load_diffusion_model(str(weights), disable_dynamic=True)
        clip_type = sd.CLIPType.MOSS_IMAGE if choice.architecture == "moss" else sd.CLIPType.KREA2
    clip = sd.load_clip([str(path) for path in files.encoders], clip_type=clip_type, disable_dynamic=True)
    coverage: list[LoRACoverage] = []
    for lora in files.loras:
        tensors = lora_convert.convert_lora(utils.load_torch_file(str(lora.path)))
        key_map = lora_api.model_lora_keys_unet(model.model, {})
        patches = lora_api.load_lora(tensors, key_map, log_missing=False)
        used: set[str] = set()
        for patch in patches.values():
            used.update(getattr(patch, "loaded_keys", ()))
        missing: set[str] = set(tensors) - used
        if not patches or missing:
            raise StepError(
                "missing_input",
                f"{lora.path.name} is incompatible with {choice.label}: "
                f"{len(missing)}/{len(tensors)} tensor keys unmatched. No generation was run.",
            )
        patched = model.clone()
        applied = set(patched.add_patches(patches, lora.strength))
        if applied != set(patches):
            raise StepError("missing_input", f"{lora.path.name}: some LoRA modules could not be applied")
        model = patched
        coverage.append(LoRACoverage(lora.path.name, len(tensors), len(applied)))
    vae = sd.VAE(sd=utils.load_torch_file(str(files.vae)))
    loaded = LoadedModel(choice.id, model, clip, vae, management, sampling,
                         comfyui_version.__version__, tuple(coverage))
    _CACHE.append(loaded)
    return loaded


def _source_image(src: Path) -> Path:
    meta = json.loads((src / "meta.json").read_text(encoding="utf-8"))
    outputs = meta["outputs"]
    relative: str = outputs.get("image") or outputs.get("image_0") or "image_rgb.png"
    picture: Path = (src / relative).resolve()
    if not picture.is_relative_to(src.resolve()) or not picture.is_file():
        raise StepError("missing_input", "Select a reference image version before editing it")
    return picture


def _style_image(src: Path, version: object) -> Path:
    if not isinstance(version, str) or re.fullmatch(r"\d{3}_[a-z0-9_]+", version) is None:
        raise StepError("bad_params", "style_image must name an image version in this asset")
    asset: Path = src.resolve().parent
    folder: Path = (asset / version).resolve()
    if folder.parent != asset or not (folder / "meta.json").is_file():
        raise StepError("missing_input", f"No local style image version {version!r} in this asset")
    return _source_image(folder)


def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    try:
        choice = reference_models.get(str(params.get("model", "krea-anime")))
    except ValueError as exc:
        raise StepError("bad_params", str(exc)) from exc
    allowed: set[str] = {"model", "prompt", "count", "seed", "steps", "width", "height", "cfg", "style_image", "denoise", "paint_mask", "appearance", "view_prompt", "paint_mode", "mask_feather", "prompt_scope"}
    if set(params) - allowed:
        raise StepError("bad_params", f"Unknown reference parameters: {sorted(set(params) - allowed)}")
    if params.get("prompt_scope", "shared_style") not in ("shared_style", "match_capture"):
        raise StepError("bad_params", "Prompt scope must match the capture or use shared style")
    if "paint_mask" in params:
        from steps._paint_mask import parse_mask

        parse_mask(params["paint_mask"])
    editing: bool = op == "edit"
    if ("image" if op == "run" else op) not in choice.operations:
        raise StepError("bad_params", "Use image for generation or edit for local reference edits")
    prompt: str = str(params.get("prompt", "")).strip()
    if not prompt and not editing and in_dir and (Path(in_dir) / "brief.yaml").is_file():
        brief = yaml.safe_load((Path(in_dir) / "brief.yaml").read_text(encoding="utf-8"))
        prompt = str(brief["prompt_full"]).strip()
    width, height = params.get("width", 1024), params.get("height", 1024)
    count, seed = params.get("count", 1), params.get("seed", random.randrange(2**31))
    flux_style: bool = choice.architecture == "flux"
    steps, cfg = params.get("steps", choice.steps), params.get("cfg", 4.0 if choice.architecture == "qwen" else 1.0)
    image_to_image: bool = editing and choice.architecture in ("flux", "krea")
    paint_mode = params.get("paint_mode", "full_view")
    if paint_mode not in ("full_view", "masked"):
        raise StepError("bad_params", "paint_mode must be masked or full_view")
    masked = paint_mode == "masked"
    if masked and (not image_to_image or not in_dir or "paint_mask" not in params):
        raise StepError("bad_params", "Masked painting needs a mesh capture, a selection and Krea or FLUX image-to-image")
    if "mask_feather" in params and not masked:
        raise StepError("bad_params", "mask_feather requires masked painting")
    denoise = params.get("denoise", 0.55 if image_to_image else 1.0)
    if "denoise" in params and not image_to_image:
        raise StepError("bad_params", "denoise requires FLUX or Krea image-to-image")
    if not isinstance(denoise, (int, float)) or not 0 < denoise <= 1:
        raise StepError("bad_params", "denoise must be greater than 0 and at most 1")
    if not (
        prompt and isinstance(count, int) and 1 <= count <= 4
        and isinstance(seed, int) and 0 <= seed < 2**53
        and isinstance(steps, int) and 1 <= steps <= 50
        and isinstance(cfg, (int, float)) and 1 <= cfg <= 8
        and all(isinstance(v, int) and 256 <= v <= 2048 and v % 64 == 0 for v in (width, height))
    ):
        raise StepError("bad_params", "Reference needs a prompt, count 1-4, valid seed, steps 1-50 and dimensions divisible by 64")
    if editing and not in_dir:
        raise StepError("missing_input", "Reference edits need an input image version")
    style_path: Path | None = None
    if "style_image" in params:
        if choice.architecture != "qwen" or in_dir is None:
            raise StepError("bad_params", "style_image is supported only for Qwen reference edits")
        style_path = _style_image(Path(in_dir), params["style_image"])
    write_mask: Image.Image | None = None
    noise_mask: torch.Tensor | None = None
    sampler_image: Image.Image | None = None
    if masked:
        from scipy.ndimage import distance_transform_edt

        from steps._paint_mask import capture_mask, number, parse_mask

        write_mask = capture_mask(Path(in_dir), parse_mask(params["paint_mask"]))
        if write_mask.size != (width, height):
            raise StepError("bad_params", "Masked painting keeps the complete capture at its original size")
        feather = number(params.get("mask_feather", 8), 0, 32, "Sampler edge blend")
        values = np.asarray(write_mask).astype(np.float32) / 255
        if feather > 0:
            values *= np.minimum(distance_transform_edt(values > 0) / feather, 1)
        sampler_image = Image.fromarray((values * 255).round().astype(np.uint8))
        noise_mask = torch.from_numpy(values)[None]
    t0: float = time.perf_counter()
    engine = _load(choice)
    sampling_model = engine.model
    if masked:
        from comfy_extras.nodes_differential_diffusion import DifferentialDiffusion

        sampling_model = engine.model.clone()

        def differential_mask(sigma: Any, mask: torch.Tensor, extra_options: dict) -> torch.Tensor:
            scheduled = DifferentialDiffusion.forward(sigma, mask, extra_options, strength=1.0)
            return scheduled * (mask > 0).to(mask.dtype)

        sampling_model.set_model_denoise_mask_function(differential_mask)
    load_seconds: float = time.perf_counter() - t0
    torch.cuda.reset_peak_memory_stats()
    progress(0.12, "encoding the reference instructions")
    with torch.inference_mode():
        source_latent: torch.Tensor | None = None
        original: Image.Image | None = None
        if editing:
            picture = Image.open(_source_image(Path(in_dir))).convert("RGBA")
            original = picture.copy()
            if image_to_image:
                picture = Image.alpha_composite(
                    Image.new("RGBA", picture.size, (255, 255, 255, 255)), picture
                )
            picture = picture.convert("RGB")
            ratio: float = picture.width / picture.height
            if not ("width" in params and "height" in params):
                width = round(math.sqrt(1024 * 1024 * ratio) / 32) * 32
                height = round(math.sqrt(1024 * 1024 / ratio) / 32) * 32
            if image_to_image:
                picture = picture.resize((width, height), Image.Resampling.LANCZOS)
                pixels = torch.from_numpy(np.asarray(picture).astype(np.float32) / 255.0)[None]
                source_latent = engine.vae.encode(pixels)
                positive = engine.clip.encode_from_tokens_scheduled(engine.clip.tokenize(prompt))
                if flux_style:
                    positive = [[values, {**metadata, "guidance": 3.0}] for values, metadata in positive]
                    negative = engine.clip.encode_from_tokens_scheduled(engine.clip.tokenize(""))
                else:
                    negative = [[torch.zeros_like(values), {
                        **metadata,
                        **({"pooled_output": torch.zeros_like(metadata["pooled_output"])}
                           if metadata.get("pooled_output") is not None else {}),
                    }] for values, metadata in positive]
            else:
                from comfy_extras.nodes_qwen import TextEncodeQwenImageEditPlus

                pixels = torch.from_numpy(np.asarray(picture).astype(np.float32) / 255.0)[None]
                style_pixels: torch.Tensor | None = None
                if style_path is not None:
                    with Image.open(style_path) as style_picture:
                        style_pixels = torch.from_numpy(
                            np.asarray(style_picture.convert("RGB")).astype(np.float32) / 255.0
                        )[None]
                positive = TextEncodeQwenImageEditPlus.execute(
                    engine.clip, prompt, engine.vae, image1=pixels, image2=style_pixels
                )[0]
                negative = TextEncodeQwenImageEditPlus.execute(
                    engine.clip, "", engine.vae, image1=pixels, image2=style_pixels
                )[0]
        else:
            positive = engine.clip.encode_from_tokens_scheduled(engine.clip.tokenize(prompt))
            negative = []
            for values, metadata in positive:
                zero = metadata.copy()
                if zero.get("pooled_output") is not None:
                    zero["pooled_output"] = torch.zeros_like(zero["pooled_output"])
                negative.append([torch.zeros_like(values), zero])
        out: Path = Path(out_dir)
        progress(0.18, "loading the reference model onto CUDA")
        outputs: dict[str, str] = {}
        if write_mask is not None and sampler_image is not None:
            write_mask.save(out / "write_mask.png")
            sampler_image.save(out / "sampler_mask.png")
            outputs.update(write_mask="write_mask.png", sampler_mask="sampler_mask.png")
        sample_seconds: list[float] = []
        for index in range(count):
            latent = source_latent if source_latent is not None else torch.zeros(
                (1, 16, height // 8, width // 8), device="cpu"
            )
            if choice.architecture == "moss" and source_latent is None:
                from comfy_extras.nodes_flux import EmptyFlux2LatentImage

                latent = EmptyFlux2LatentImage.execute(width, height, 1)[0]["samples"]
            latent = engine.sampling.fix_empty_latent_channels(engine.model, latent)
            noise = engine.sampling.prepare_noise(latent, seed + index)

            def callback(step: int, _x0: Any, _x: Any, total_steps: int, image_index: int = index) -> None:
                progress(0.2 + 0.7 * (image_index + (step + 1) / total_steps) / count,
                         f"{choice.label}: image {image_index + 1}/{count}, step {step + 1}/{total_steps}")

            sample_start: float = time.perf_counter()
            latent = engine.sampling.sample(
                sampling_model, noise, steps, cfg, "euler", "simple", positive, negative,
                latent, denoise=denoise, seed=seed + index, callback=callback, disable_pbar=True,
                noise_mask=noise_mask,
            )
            torch.cuda.synchronize()
            sample_seconds.append(round(time.perf_counter() - sample_start, 2))
            decoded = engine.vae.decode(latent)
            if decoded.ndim == 5:
                decoded = decoded.reshape(-1, *decoded.shape[-3:])
            if not torch.isfinite(decoded).all():
                raise StepError("failed", "Native model produced non-finite pixels")
            image = Image.fromarray((decoded[0].clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8))
            if sampler_image is not None:
                if image.size != picture.size:
                    raise StepError("failed", "Masked decoder changed the full-frame dimensions")
                image = Image.composite(image.convert("RGBA"), original, sampler_image)
                image.putalpha(original.getchannel("A"))
                outside = np.asarray(write_mask) == 0
                if np.any(np.asarray(image)[outside] != np.asarray(original)[outside]):
                    raise StepError("failed", "Masked preview changed protected pixels")
            name: str = f"image_{index}.png"
            image.save(out / name)
            outputs[f"image_{index}"] = name
    outputs.update(image="image_0.png", preview="image_0.png")
    quantized_layers = Counter()
    for module in engine.model.model.modules():
        quant_format = getattr(module, "quant_format", None)
        if quant_format is not None:
            precision = "full_precision_mm" if getattr(module, "_full_precision_mm", False) else "quantized_mm_enabled"
            quantized_layers[f"{quant_format}:{precision}"] += 1
    return {
        "outputs": outputs,
        "models": [{"id": choice.id, "file": Path(choice.weights).name}] + [
            {"id": lora.file, "file": Path(lora.file).name, "strength": lora.strength}
            for lora in choice.loras
        ],
        "metrics": {"model": choice.label, "mode": "edit" if editing else "generate", "seed": seed, "count": count,
                    "width": width, "height": height, "steps": steps, "cfg": cfg,
                    "seconds": round(time.perf_counter() - t0, 2), "seconds_load": round(load_seconds, 2),
                    "seconds_sample": sample_seconds,
                    "style_image": params.get("style_image"),
                    "paint_mode": paint_mode, "context_policy": "full_frame",
                    "sampler_mask": "differential" if masked else None,
                    "masked_pixels": int(np.count_nonzero(np.asarray(write_mask))) if masked else None,
                    "outside_changed": 0 if masked else None,
                    "denoise": denoise, "guidance": 3.0 if flux_style else None,
                    "lora_coverage": [
                        {"file": row.file, "tensor_keys": row.tensor_keys,
                         "applied_modules": row.applied_modules, "unmatched_keys": 0}
                        for row in engine.lora_coverage
                    ],
                    "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
                    "quantized_layers": dict(quantized_layers),
                    "weight_dtype": str(engine.model.model.get_dtype()),
                    "inference_dtype": str(engine.model.model.get_dtype_inference()),
                    "cuda": torch.version.cuda, "device": torch.cuda.get_device_name(0),
                    "nvfp4_compute_supported": engine.management.supports_nvfp4_compute(torch.device("cuda:0")),
                    "engine": f"ComfyUI {engine.engine_version}", "torch": torch.__version__},
    }


if __name__ == "__main__":
    main(run)
