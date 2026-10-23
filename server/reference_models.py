"""Local reference-model choices and their read-only workstation bindings."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from server import model_bindings, settings


@dataclass(frozen=True, slots=True)
class StyleLoRA:
    file: str
    strength: float


@dataclass(frozen=True, slots=True)
class BoundLoRA:
    path: Path
    strength: float


@dataclass(frozen=True, slots=True)
class ReferenceFiles:
    weights: Path
    encoders: tuple[Path, ...]
    vae: Path
    loras: tuple[BoundLoRA, ...]


@dataclass(frozen=True, slots=True)
class ReferenceModel:
    id: str
    label: str
    mode: Literal["generate", "edit"]
    weights: str
    encoder: str
    steps: int
    architecture: Literal["krea", "qwen", "flux", "moss"] = "krea"
    vae: str = "shared-vaes/qwen_image_vae.safetensors"
    encoder_aux: str | None = None
    loras: tuple[StyleLoRA, ...] = ()
    operations: tuple[str, ...] = ("image",)


@dataclass(frozen=True, slots=True)
class NativeRuntime:
    python: Path
    source: Path


MODELS: tuple[ReferenceModel, ...] = (
    ReferenceModel("moss-turbo", "MOSS Turbo v2 (experimental painting)", "generate",
                   "shared-diffusion-models/moss_image_sft_bf16.safetensors",
                   "shared-text-encoders/qwen3.5_9b_int8_convrot.safetensors", 4,
                   architecture="moss", vae="shared-vaes/flux2-vae.safetensors",
                   loras=(StyleLoRA("shared-loras/moss_image_sft_4step_v2.0.safetensors", 1.0),)),
    ReferenceModel("krea-anime", "Krea2 Anime Genesis (MXFP8)", "generate",
                   "shared-checkpoints/Krea2_Anime_Genesis_mxfp8.safetensors",
                   "shared-text-encoders/qwen3vl_4b_fp8_scaled.safetensors", 8),
    ReferenceModel("krea-genesis", "Krea2 Genesis (NVFP4 weights)", "generate",
                   "shared-checkpoints/Krea2_Genesis-Blackwell-Optimized-nvfp4.safetensors",
                   "shared-text-encoders/qwen3vl_4b_fp8_scaled.safetensors", 8,
                   operations=("image", "edit")),
    ReferenceModel("krea-turbo", "Krea2 Turbo (FP8)", "generate",
                   "shared-diffusion-models/krea2-turbo.safetensors",
                   "shared-text-encoders/qwen3vl_4b_fp8_scaled.safetensors", 8),
    ReferenceModel("qwen-edit", "Qwen Image Edit 2511 (Q8)", "edit",
                   "shared-diffusion-models/qwen-image-edit-2511-Q8_0.gguf",
                   "shared-text-encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors", 20,
                   architecture="qwen", operations=("edit",)),
    ReferenceModel("flux-ghibli", "FLUX Ghibli paint (Q8)", "edit",
                   "shared-diffusion-models/flux1-dev-Q8_0.gguf",
                   "shared-text-encoders/t5xxl_fp8_e4m3fn.safetensors", 30,
                   architecture="flux", vae="shared-vaes/flux1-ae.safetensors",
                   encoder_aux="shared-text-encoders/clip_l.safetensors",
                   loras=(StyleLoRA("shared-loras/Flux-Ghibli-Art-LoRA.safetensors", 0.7),),
                   operations=("edit",)),
)


if os.environ.get("EFFIGY_MULTI_VIEW") != "1":
    MODELS = tuple(model for model in MODELS if model.id != "moss-turbo")


def runtime(model_id: str | None = None) -> NativeRuntime:
    selected = model_id or os.environ.get("EFFIGY_REFERENCE_MODEL")
    if selected in ("fibo2-turbo", "krea-genesis", "moss-turbo"):
        return runtime_for_model(selected)
    config: Path = Path(settings.read()["tools_config"])
    data = json.loads(config.read_text(encoding="utf-8-sig"))["comfyUi"]
    python: Path = (config.parent / data["embeddedPython"]).resolve()
    source: Path = (config.parent / data["inputDirectory"]).resolve().parent
    if not python.is_file() or not (source / "comfy" / "sd.py").is_file():
        raise RuntimeError("Configured native reference engine is missing; repair the local tools configuration")
    return NativeRuntime(python, source)


def runtime_for_model(model_id: str | None) -> NativeRuntime:
    local = settings.read()
    if model_id in ("fibo2-turbo", "moss-turbo"):
        python_value, source_value = local.get("trial_native_python"), local.get("trial_native_source")
        if not python_value or not source_value:
            raise RuntimeError("FIBO is available only in the configured isolated trial")
        python, source = Path(python_value), Path(source_value)
    elif model_id == "krea-genesis":
        config = Path(local["tools_config"])
        data = json.loads(config.read_text(encoding="utf-8-sig"))["comfyUi"]
        python = (config.parent / data["embeddedPython"]).resolve()
        source = (config.parent / data["inputDirectory"]).resolve().parent
    else:
        raise RuntimeError("Native painting supports FIBO, Genesis and MOSS Turbo")
    if not python.is_file() or not (source / "comfy" / "sd.py").is_file():
        raise RuntimeError("The selected model's configured local runtime is unavailable")
    return NativeRuntime(python, source)


def get(model_id: str) -> ReferenceModel:
    for model in MODELS:
        if model.id == model_id:
            return model
    raise ValueError(f"Unknown local reference model: {model_id}")


def _component(relative: str) -> Path:
    binding = model_bindings.resolve(relative)
    if binding.owned:
        raise PermissionError("Reference candidates require explicit read-only shared bindings")
    if not binding.path.is_file():
        raise FileNotFoundError(f"Local reference component missing: {relative}; check the shared model binding")
    return binding.path


def paths(model: ReferenceModel) -> ReferenceFiles:
    encoders: tuple[Path, ...] = (_component(model.encoder),)
    if model.encoder_aux is not None:
        encoders += (_component(model.encoder_aux),)
    return ReferenceFiles(
        _component(model.weights), encoders, _component(model.vae),
        tuple(BoundLoRA(_component(lora.file), lora.strength) for lora in model.loras),
    )


def description_paths() -> tuple[Path, Path, Path]:
    return (
        _component("shared-description-runtime/llama-server.exe"),
        _component("shared-description/Q3.5-9B-OpusGLM-MAX-0731-ablated.Q8_0.gguf"),
        _component("shared-description/Q3.5-9B-OpusGLM-MAX-0731-ablated.mmproj-q8_0.gguf"),
    )


def status() -> list[dict]:
    result: list[dict] = []
    for model in MODELS:
        problem: str = ""
        try:
            runtime(model.id)
            paths(model)
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            problem = str(exc)
        result.append({"id": model.id, "label": model.label, "mode": model.mode,
                       "operations": list(model.operations),
                       "available": not problem, "detail": problem})
    return result
