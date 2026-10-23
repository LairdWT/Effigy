"""Offline masked SyncMVD adaptation for Effigy's immutable GLB/UV contract.

Algorithm attribution and MIT license: licenses/SyncMVD.txt.
"""
from __future__ import annotations

import math
import os
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from diffusers import AutoencoderKL, ControlNetModel, DDPMScheduler, UNet2DConditionModel
from PIL import Image
from transformers import CLIPTextModel, CLIPTokenizer

from server import library, sync_models
from server.paint_contracts import CameraBinding, group_layout
from steps._common import StepError, budget_gb, main, progress
from steps._paint_set import Surface, read_manifest, save_json
from steps._sync_renderer import LatentRenderer
from steps._sync_scheduler import SamplewiseAttention, prediction_batches, texture_step
from steps.paint import version_dir
from tools.fibo_trial_worker import primary_worker_present


def encode_prompt(tokenizer: CLIPTokenizer, encoder: CLIPTextModel, prompt: str,
                  device: torch.device) -> tuple[torch.Tensor, torch.Tensor, int]:
    tokens = tokenizer(prompt, add_special_tokens=False, truncation=False)["input_ids"]
    width = tokenizer.model_max_length - 2
    chunks = max(1, math.ceil(len(tokens) / width))
    positive, negative = [], []
    for i in range(chunks):
        content = tokens[i * width:(i + 1) * width]
        padded = [tokenizer.bos_token_id, *content, tokenizer.eos_token_id]
        padded += [tokenizer.pad_token_id] * (width + 2 - len(padded))
        blank = [tokenizer.bos_token_id, tokenizer.eos_token_id] + [tokenizer.pad_token_id] * width
        positive.append(encoder(torch.tensor([padded], device=device))[0])
        negative.append(encoder(torch.tensor([blank], device=device))[0])
    return torch.cat(positive, 1), torch.cat(negative, 1), chunks


@torch.inference_mode()
def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    if os.environ.get("EFFIGY_MULTI_VIEW") != "1" or params.get("strategy") != "synchronized":
        raise StepError("bad_params", "SyncMVD requires an isolated synchronized paint session")
    if op != "generate" or in_dir is None or len(params["allocated"]) != 1:
        raise StepError("bad_params", "SyncMVD needs one complete immutable candidate")
    if primary_worker_present():
        raise StepError("failed", "Primary Effigy owns a worker; leave it unchanged")
    source, out = Path(in_dir), Path(out_dir)
    if source.name != params["source"] or library.geometry_revision(source) != params["geometry_revision"]:
        raise StepError("bad_params", "SyncMVD source geometry changed")
    try:
        binding = sync_models.resolve()
    except (OSError, ValueError, KeyError) as error:
        raise StepError("missing_input", str(error)) from error
    recipe = params["recipe"]
    if recipe["model"] != "syncmvd" or recipe["style_image"] is not None:
        raise StepError("bad_params", "SyncMVD uses its normal-conditioned recipe without style-image references")
    budget = budget_gb()
    if budget is None or not torch.cuda.is_available():
        raise StepError("oom", "SyncMVD requires an admitted CUDA-0 budget")
    torch.cuda.set_device(0)
    torch.cuda.set_per_process_memory_fraction(min(1.0, budget * 2**30 / torch.cuda.get_device_properties(0).total_memory))
    device, dtype = torch.device("cuda:0"), torch.float16
    allocation = params["allocated"][0]
    destination = (source.parent / allocation["version"]).resolve()
    if destination.parent != source.parent.resolve() or not destination.is_dir() or (destination / "meta.json").exists():
        raise StepError("bad_params", "SyncMVD candidate destination is missing or already published")
    group = allocation["params"]["group"]
    layout = group_layout(group)
    capture = version_dir(source.parent, params["capture"])
    mask_dir = version_dir(source.parent, params["mask_version"])
    manifest = read_manifest(mask_dir)
    views = {v["id"]: v for v in manifest["views"]}
    if set(group["views"]) != {key for key, row in views.items() if row["texels"] > 0}:
        raise StepError("bad_params", "Synchronized generation requires the complete eligible capture pool")
    cameras = tuple(CameraBinding(p.camera_id, views[p.camera_id]["view"]["yaw"],
                                  views[p.camera_id]["view"]["pitch"], tuple(views[p.camera_id]["view"]["center"]),
                                  views[p.camera_id]["view"]["extent"]) for p in layout.panels)
    with Image.open(library.resolve_output(mask_dir, "mask")) as image:
        selected = np.asarray(image) > 0
    surface = Surface(source)
    renderer = LatentRenderer(surface, cameras, device, dtype, selected)
    batches = prediction_batches(renderer.neighbours(), 0)
    progress(0.02, "Loading isolated SD1.5 and normal ControlNet from pinned local files")
    started = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    base, control = binding.sd15.path, binding.normal.path
    common = {"local_files_only": True, "torch_dtype": dtype, "variant": "fp16", "use_safetensors": True}
    unet = UNet2DConditionModel.from_pretrained(base, subfolder="unet", **common).to(device)
    controlnet = ControlNetModel.from_pretrained(control, **common).to(device)
    vae = AutoencoderKL.from_pretrained(base, subfolder="vae", **common).to(device)
    encoder = CLIPTextModel.from_pretrained(base, subfolder="text_encoder", **common).to(device)
    tokenizer = CLIPTokenizer.from_pretrained(base, subfolder="tokenizer", local_files_only=True)
    scheduler = DDPMScheduler.from_pretrained(base, subfolder="scheduler", local_files_only=True)
    scheduler.set_timesteps(math.ceil(30 / recipe["denoise"]), device=device)
    timesteps = scheduler.timesteps[-30:]
    if len(timesteps) != 30:
        raise StepError("bad_params", "SyncMVD requires thirty executed synchronized updates")
    prompt = "\n\n".join(recipe[k].strip() for k in ("materials", "style", "prompt") if recipe[k].strip())
    if not prompt:
        raise StepError("bad_params", "Describe the resulting painted material")
    positive, negative, chunks = encode_prompt(tokenizer, encoder, prompt, device)
    encoder.to("cpu")
    source_images, masks, encoded = [], [], []
    sheet = Image.new("RGBA", (layout.width, layout.height))
    sheet_mask = Image.new("L", sheet.size)
    for panel in layout.panels:
        with Image.open(capture / "views" / f"{panel.camera_id}.png") as image:
            rgba = image.convert("RGBA")
        with Image.open(mask_dir / "selections" / f"{panel.camera_id}.png") as image:
            mask = image.convert("L")
        full = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
        pixels = torch.tensor(np.asarray(full).copy(), device=device, dtype=dtype).permute(2, 0, 1)[None] / 127.5 - 1
        encoded.append(vae.encode(pixels).latent_dist.mode() * vae.config.scaling_factor)
        source_images.append(rgba)
        masks.append(torch.tensor(np.asarray(mask).copy(), device=device, dtype=dtype)[None, None] / 255)
        sheet.paste(rgba, (panel.x, panel.y))
        sheet_mask.paste(mask, (panel.x, panel.y))
    source_views = torch.cat(encoded)
    permission = (F.avg_pool2d(torch.cat(masks), 8) >= 0.999).to(dtype)
    source_texture = renderer.bake(source_views, torch.zeros((1, 4, renderer.texture_size, renderer.texture_size), device=device, dtype=dtype))
    generator = torch.Generator(device=device).manual_seed(recipe["seed"])
    texture_noise = torch.randn(source_texture.shape, generator=generator, device=device, dtype=dtype)
    view_noise = torch.randn(source_views.shape, generator=generator, device=device, dtype=dtype)
    texture = scheduler.add_noise(source_texture, texture_noise, timesteps[:1])
    controls = torch.stack(renderer.normals)
    original_processors = dict(unet.attn_processors)
    sampling_started = time.perf_counter()
    for step, timestep in enumerate(timesteps):
        if primary_worker_present():
            raise StepError("failed", "Trial yielded before the next synchronized update because primary Effigy started work")
        context = scheduler.add_noise(source_views, view_noise, timestep.reshape(1))
        sample = torch.where(permission > 0, renderer.render(texture, context), context)
        predictions = torch.zeros_like(sample)
        completed: set[int] = set()
        for batch in batches:
            indices = list(batch.inputs)
            processors = {key: SamplewiseAttention(batch, 1.0 if step < 6 else 0.0) if "attn1" in key else value
                          for key, value in original_processors.items()}
            unet.set_attn_processor(processors)
            inputs = scheduler.scale_model_input(sample[indices], timestep)
            branches = []
            for embedding in (negative, positive):
                embeddings = embedding.expand(len(indices), -1, -1)
                down, mid = controlnet(inputs, timestep, encoder_hidden_states=embeddings,
                                       controlnet_cond=controls[indices], conditioning_scale=0.7 + 0.2 * step / 29,
                                       return_dict=False)
                branches.append(unet(inputs, timestep, encoder_hidden_states=embeddings,
                                     down_block_additional_residuals=down, mid_block_additional_residual=mid,
                                     return_dict=False)[0])
            prediction = branches[0] + 7.5 * (branches[1] - branches[0])
            for target in batch.targets:
                predictions[target] = prediction[indices.index(target)]
                completed.add(target)
            progress(0.1 + 0.78 * (step + len(completed) / len(cameras)) / 30,
                     f"SyncMVD global step {step + 1}/30: predicted {len(completed)}/{len(cameras)} views; texture update waits for all views")
        if len(completed) != len(cameras):
            raise StepError("failed", "Global prediction barrier is incomplete")
        texture = texture_step(scheduler, renderer, predictions, int(timestep), sample, texture, generator)
        previous = scheduler.previous_timestep(timestep)
        protected = scheduler.add_noise(source_texture, texture_noise, previous.reshape(1)) if previous >= 0 else source_texture
        texture = torch.where(renderer.permission > 0, texture, protected)
    torch.cuda.synchronize()
    sample_seconds = time.perf_counter() - sampling_started
    decoded_views = renderer.render(texture, source_views)
    for index, panel in enumerate(layout.panels):
        latent = torch.where(permission[index:index + 1] > 0, decoded_views[index:index + 1], source_views[index:index + 1])
        decoded = vae.decode(latent / vae.config.scaling_factor).sample[0].float().clamp(-1, 1)
        if not torch.isfinite(decoded).all():
            raise StepError("failed", "SyncMVD returned non-finite decoded pixels")
        values = ((decoded.permute(1, 2, 0).cpu().numpy() + 1) * 127.5).round().astype(np.uint8)
        original = source_images[index]
        mask = Image.fromarray((masks[index][0, 0].cpu().numpy() * 255).round().astype(np.uint8))
        result = Image.composite(Image.fromarray(values).convert("RGBA"), original, mask)
        result.putalpha(original.getchannel("A"))
        outside = np.asarray(mask) == 0
        if np.any(np.asarray(result)[outside] != np.asarray(original)[outside]):
            raise StepError("failed", "SyncMVD decode changed protected pixels")
        sheet.paste(result, (panel.x, panel.y))
    sheet.save(destination / "image.png")
    sheet_mask.save(destination / "write_mask.png")
    metrics = {"strategy": "synchronized", "model": "syncmvd", "steps": 30, "executed_updates": 30,
               "synchronization_end": 1.0, "micro_batch_limit": 6, "view_count": len(cameras),
               "layout": layout.to_dict(), "seed": recipe["seed"], "denoise": recipe["denoise"],
               "prompt": prompt, "prompt_chunks": chunks, "cfg": 7.5, "protected_changed": 0, "alpha_changed": 0,
               "seconds_sample": round(sample_seconds, 2), "seconds_total": round(time.perf_counter() - started, 2),
               "peak_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 3),
               "device": torch.cuda.get_device_name(0), "torch_version": torch.__version__, "cuda_version": torch.version.cuda,
               "source_revision": binding.source_revision, "geometry_revision": params["geometry_revision"]}
    payload = {"outputs": {"image": "image.png", "write_mask": "write_mask.png", "mesh": "@mesh.glb"},
               "output_refs": {"mesh": {"version": source.name, "key": "mesh"}}, "metrics": metrics,
               "models": [{"repo": snapshot.repo, "revision": snapshot.revision} for snapshot in (binding.sd15, binding.normal)]}
    save_json(destination / "group_result.json", payload)
    save_json(out / "batch.json", {"groups": [destination.name], "model": "syncmvd"})
    return {"outputs": {"batch": "batch.json", "mesh": "@mesh.glb"},
            "output_refs": {"mesh": {"version": source.name, "key": "mesh"}}, "metrics": metrics}


if __name__ == "__main__":
    main(run)
