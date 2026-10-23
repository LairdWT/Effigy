"""Isolated FIBO 2 native masked-edit worker for the optional trial lane."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections import Counter
from pathlib import Path

import numpy as np
import psutil
import torch
from PIL import Image
from scipy.ndimage import distance_transform_edt

from server import reference_models, settings
from steps._common import StepError, budget_gb, progress
from steps._paint_mask import capture_mask, number, parse_mask


def primary_worker_present() -> bool:
    primary = Path(settings.read()["environment_root"]).resolve()
    for process in psutil.process_iter(["pid", "cmdline", "cwd"]):
        if process.pid == os.getpid():
            continue
        try:
            words = process.info["cmdline"] or []
            entry = str(primary / "tools" / "native_reference_entry.py").lower()
            if any(word.lower() == entry for word in words):
                return True
            if (process.info["cwd"] and Path(process.info["cwd"]).resolve() == primary
                    and any(word.startswith("steps.") and word not in ("steps.paint", "steps.import_model") for word in words)):
                return True
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            continue
    return False


def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    if op != "edit" or in_dir is None:
        raise StepError("bad_params", "FIBO trial edits fixed mesh captures only")
    if primary_worker_present():
        raise StepError("failed", "Primary Effigy owns a model worker. Trial leaves it alone; retry when its worker has naturally released the GPU.")
    allowed = {"model", "prompt", "view_prompt", "appearance", "count", "seed", "steps", "width", "height", "paint_mask", "paint_mode", "mask_feather", "denoise", "conditioning", "style_image", "style_mask", "source", "source_mask", "prompt_scope"}
    if set(params) - allowed:
        raise StepError("bad_params", f"Unknown FIBO parameters: {sorted(set(params) - allowed)}")
    if params.get("prompt_scope", "shared_style") not in ("shared_style", "match_capture"):
        raise StepError("bad_params", "Prompt scope must match the capture or use shared style")
    if params.get("count", 1) != 1:
        raise StepError("bad_params", "FIBO trial generates one preview at a time")
    prompt = params.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        raise StepError("bad_params", "FIBO needs an edit instruction")
    seed = params.get("seed", 24026)
    steps = params.get("steps", 4)
    if type(seed) is not int or not 0 <= seed < 2**53 or steps != 4:
        raise StepError("bad_params", "The pinned Edit Turbo trial uses four steps and a nonnegative seed")
    if params.get("paint_mode", "masked") != "masked":
        raise StepError("bad_params", "This trial qualifies masked mesh painting only")
    source = Path(in_dir)
    mask = capture_mask(source, parse_mask(params.get("paint_mask")))
    meta = json.loads((source / "meta.json").read_text(encoding="utf-8"))
    size = int(meta["metrics"]["size"])
    if size != 1024 or params.get("width", size) != size or params.get("height", size) != size:
        raise StepError("bad_params", "FIBO trial keeps the complete 1024-square capture")
    from server.library import resolve_output

    with Image.open(resolve_output(source, "image")) as image:
        original = image.convert("RGBA")
    picture = Image.alpha_composite(Image.new("RGBA", original.size, "white"), original).convert("RGB")
    conditioning: str = params.get("conditioning", "blank_region")
    if conditioning not in ("blank_region", "preserve_structure"):
        raise StepError("bad_params", "FIBO conditioning must be blank_region or preserve_structure")
    source_pixels: int = 0
    if ("source" in params) != ("source_mask" in params):
        raise StepError("bad_params", "A core context source requires its own bounded source_mask")
    if "source" in params:
        if conditioning != "preserve_structure":
            raise StepError("bad_params", "Core source imagery requires full-frame instruction conditioning")
        from steps.reference import _style_image

        basis_path: Path = _style_image(source, params["source"])
        basis_meta: dict = json.loads((basis_path.parent / "meta.json").read_text(encoding="utf-8"))
        if basis_meta["step"] != "paint" or basis_meta["params"].get("op") != "capture":
            raise StepError("bad_params", "Core source must be a fixed mesh capture")
        if any(basis_meta["metrics"].get(key) != meta["metrics"].get(key) for key in ("size", "view", "geometry_revision")):
            raise StepError("bad_params", "Core source camera, dimensions and geometry must match this capture")
        core_mask: Image.Image = capture_mask(source, parse_mask(params["source_mask"]))
        core_values: np.ndarray = np.asarray(core_mask) > 0
        if np.any(core_values & (np.asarray(mask) == 0)):
            raise StepError("bad_params", "Core context replacement extends beyond write permission")
        with Image.open(basis_path) as image:
            basis = image.convert("RGBA")
        basis_rgb = Image.alpha_composite(Image.new("RGBA", basis.size, "white"), basis).convert("RGB")
        picture = Image.composite(basis_rgb, picture, core_mask)
        source_pixels = int(core_values.sum())
    style: Image.Image | None = None
    if "style_mask" in params and "style_image" not in params:
        raise StepError("bad_params", "A projected style mask requires a local style capture")
    if "style_image" in params:
        if conditioning != "preserve_structure":
            raise StepError("bad_params", "A style reference requires unblanked preserve_structure conditioning")
        from steps.reference import _style_image

        style_path: Path = _style_image(source, params["style_image"])
        with Image.open(style_path) as image:
            style = image.convert("RGB")
        if "style_mask" in params:
            style_meta = json.loads((style_path.parent / "meta.json").read_text(encoding="utf-8"))
            if style_meta["step"] != "paint" or style_meta["params"].get("op") != "capture":
                raise StepError("bad_params", "Projected style must use a fixed mesh capture")
            if any(style_meta["metrics"].get(key) != meta["metrics"].get(key) for key in ("size", "view", "geometry_revision")):
                raise StepError("bad_params", "Projected style must use the current camera and geometry")
            style_region = capture_mask(style_path.parent, parse_mask(params["style_mask"]))
            style = Image.composite(style, Image.new("RGB", style.size, "white"), style_region)
    context = picture if conditioning == "preserve_structure" else Image.composite(
        Image.new("RGB", picture.size, (128, 128, 128)), picture, mask
    )
    feather = number(params.get("mask_feather", 8), 0, 32, "Preview edge blend")
    mask_values = np.asarray(mask).astype(np.float32) / 255
    if feather:
        mask_values *= np.minimum(distance_transform_edt(mask_values > 0) / feather, 1)
    blend = Image.fromarray((mask_values * 255).round().astype(np.uint8))
    runtime = reference_models.runtime()
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
    from comfy import sd, utils
    from comfy_extras.nodes_fibo2 import TextEncodeFibo2

    budget = budget_gb()
    if budget is None or not torch.cuda.is_available() or torch.cuda.current_device() != 0:
        raise StepError("failed", "FIBO requires an admitted CUDA-0 job")
    total = torch.cuda.get_device_properties(0).total_memory
    management.EXTRA_RESERVED_VRAM = max(2 * 2**30, total - budget * 2**30)
    stopped = threading.Event()

    def yield_to_primary() -> None:
        while not stopped.wait(0.5):
            if not primary_worker_present():
                continue
            print("FIBO trial exiting: primary Effigy started a model worker; no primary process was changed.", file=sys.stderr, flush=True)
            os._exit(1)

    threading.Thread(target=yield_to_primary, daemon=True).start()
    choice = reference_models.get("fibo2-turbo")
    files = reference_models.paths(choice)
    started = time.perf_counter()
    try:
        progress(0.03, "loading isolated FIBO 2 Edit Turbo on CUDA")
        model = sd.load_diffusion_model(str(files.weights), disable_dynamic=True)
        clip = sd.load_clip([str(path) for path in files.encoders], clip_type=sd.CLIPType.FIBO2, disable_dynamic=True)
        vae = sd.VAE(sd=utils.load_torch_file(str(files.vae)))
        torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            progress(0.15, f"encoding full captured view: {conditioning}")
            pixels = torch.from_numpy(np.asarray(context).astype(np.float32) / 255)[None]
            references: dict[str, torch.Tensor] = {"image_1": pixels}
            if style is not None:
                references["image_2"] = torch.from_numpy(np.asarray(style).astype(np.float32) / 255)[None]
            positive, negative, latent = TextEncodeFibo2.execute(
                clip, prompt, vae=vae, images=references, width=size, height=size
            )
            noise = sampling.prepare_noise(latent["samples"], seed)

            def callback(step: int, _x0: object, _x: object, total_steps: int) -> None:
                progress(0.25 + 0.6 * (step + 1) / total_steps, f"FIBO masked preview: step {step + 1}/{total_steps}")

            sample_start = time.perf_counter()
            output = sampling.sample(model, noise, 4, 1.0, "euler", "simple", positive, negative,
                                     latent["samples"], denoise=1.0, seed=seed, callback=callback, disable_pbar=True)
            torch.cuda.synchronize()
            seconds_sample = time.perf_counter() - sample_start
            decoded = vae.decode(output)
            if not torch.isfinite(decoded).all():
                raise StepError("failed", "FIBO returned non-finite pixels")
            generated = Image.fromarray((decoded[0].clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)).convert("RGBA")
        if generated.size != original.size:
            raise StepError("failed", "FIBO output changed the fixed projection dimensions")
        result = Image.composite(generated, original, blend)
        result.putalpha(original.getchannel("A"))
        outside = np.asarray(mask) == 0
        if np.any(np.asarray(result)[outside] != np.asarray(original)[outside]):
            raise StepError("failed", "FIBO preview changed protected pixels")
        out = Path(out_dir)
        result.save(out / "image_0.png")
        mask.save(out / "write_mask.png")
        quantization = Counter(str(module.quant_format) for module in model.model.modules() if getattr(module, "quant_format", None) is not None)
        return {"outputs": {"image": "image_0.png", "image_0": "image_0.png", "preview": "image_0.png", "write_mask": "write_mask.png"},
                "models": [{"id": "fibo2-turbo", "file": files.weights.name}],
                "metrics": {"model": choice.label, "paint_mode": "masked", "context_policy": "full_frame",
                            "mask_conditioning": "binary grey reference" if conditioning == "blank_region" else "unblanked instruction edit",
                            "conditioning": conditioning, "style_image": params.get("style_image"),
                            "style_reference_mode": "projected_paint" if "style_mask" in params else "whole_reference",
                            "core_context_source": params.get("source"), "core_context_pixels": source_pixels,
                            "write_policy": "protected RGBA composition",
                            "sampler_mask": None, "seed": seed, "steps": 4, "guidance": 1.0,
                            "masked_pixels": int(np.count_nonzero(np.asarray(mask))), "outside_changed": 0,
                            "alpha_changed": 0, "width": size, "height": size,
                            "seconds": round(time.perf_counter() - started, 2), "seconds_sample": round(seconds_sample, 2),
                            "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
                            "quantized_layers": dict(quantization), "engine": comfyui_version.__version__,
                            "native_revision": "e3699a745d513941f17ecbc9a3c58d00fc7768cb",
                            "model_revision": "41e6a0331eff43d5a323107197056e377288c642", "torch": torch.__version__}}
    finally:
        stopped.set()
