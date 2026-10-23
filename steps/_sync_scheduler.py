"""SyncMVD DDPM texture update and samplewise attention, adapted for Effigy.

Derived from LIU-Yuxin/SyncMVD at faa95621d220d7327847a994cd380608c04af5ab,
src/syncmvd/step.py and attention.py. MIT; see licenses/SyncMVD.txt.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import torch
import torch.nn.functional as F
from diffusers import DDPMScheduler
from diffusers.models.attention_processor import Attention


class TextureProjection(Protocol):
    def bake(self, views: torch.Tensor, fallback: torch.Tensor) -> torch.Tensor: ...
    def render(self, texture: torch.Tensor, background: torch.Tensor) -> torch.Tensor: ...


@dataclass(frozen=True)
class PredictionBatch:
    inputs: tuple[int, ...]
    targets: tuple[int, ...]
    neighbours: tuple[tuple[int, ...], ...]
    references: tuple[int, ...]


def prediction_batches(neighbours: list[list[int]], reference: int) -> tuple[PredictionBatch, ...]:
    batches: list[PredictionBatch] = []
    targets: list[int] = []
    inputs: set[int] = set()

    def finish() -> None:
        indices = tuple(sorted(inputs))
        adjacent = tuple(tuple(indices.index(j) for j in neighbours[i] if j in inputs) for i in indices)
        batches.append(PredictionBatch(indices, tuple(targets), adjacent, (indices.index(reference),)))

    for index, adjacent in enumerate(neighbours):
        required = set(adjacent) | {index, reference}
        if len(required) > 6:
            raise ValueError("A target and its attention references exceed the six-view limit")
        if targets and len(inputs | required) > 6:
            finish()
            targets, inputs = [], set()
        targets.append(index)
        inputs |= required
    if targets:
        finish()
    return tuple(batches)


@torch.no_grad()
def texture_step(scheduler: DDPMScheduler, renderer: TextureProjection, predicted_noise: torch.Tensor,
                 timestep: int, sample: torch.Tensor, texture: torch.Tensor,
                 generator: torch.Generator) -> torch.Tensor:
    previous = scheduler.previous_timestep(timestep)
    alpha = scheduler.alphas_cumprod[timestep].to(texture.device)
    alpha_previous = (scheduler.alphas_cumprod[previous] if previous >= 0 else scheduler.one).to(texture.device)
    beta, beta_previous = 1 - alpha, 1 - alpha_previous
    current_alpha = alpha / alpha_previous
    current_beta = 1 - current_alpha
    prediction = scheduler.config.prediction_type
    if prediction == "epsilon":
        original = (sample - beta.sqrt() * predicted_noise) / alpha.sqrt()
    elif prediction == "sample":
        original = predicted_noise
    elif prediction == "v_prediction":
        original = alpha.sqrt() * sample - beta.sqrt() * predicted_noise
    else:
        raise ValueError(f"Unsupported SyncMVD DDPM prediction: {prediction}")
    if scheduler.config.thresholding:
        original = scheduler._threshold_sample(original)
    elif scheduler.config.clip_sample:
        original = original.clamp(-scheduler.config.clip_sample_range, scheduler.config.clip_sample_range)
    clean_texture = renderer.bake(original, texture)
    previous_texture = alpha_previous.sqrt() * current_beta / beta * clean_texture
    previous_texture += current_alpha.sqrt() * beta_previous / beta * texture
    if timestep > 0:
        noise = torch.randn(texture.shape, generator=generator, device=texture.device, dtype=texture.dtype)
        variance = scheduler._get_variance(timestep).to(texture.device)
        if scheduler.variance_type == "fixed_small_log":
            previous_texture += variance * noise
        else:
            previous_texture += variance.sqrt() * noise
    return previous_texture


class SamplewiseAttention:
    """Self attention across adjacent views plus the shared front reference."""

    def __init__(self, batch: PredictionBatch, reference_weight: float):
        self.batch = batch
        self.reference_weight = reference_weight

    def __call__(self, attn: Attention, hidden_states: torch.Tensor,
                 encoder_hidden_states: torch.Tensor | None = None,
                 attention_mask: torch.Tensor | None = None,
                 temb: torch.Tensor | None = None, *args: object, **kwargs: object) -> torch.Tensor:
        if encoder_hidden_states is not None or attention_mask is not None:
            raise ValueError("Synchronized processor supports unmasked self attention only")
        residual = hidden_states
        if attn.spatial_norm is not None:
            hidden_states = attn.spatial_norm(hidden_states, temb)
        shape = hidden_states.shape
        if len(shape) == 4:
            hidden_states = hidden_states.flatten(2).transpose(1, 2)
        count, _, channels = hidden_states.shape
        if count != len(self.batch.inputs):
            raise ValueError("Attention batch does not match recorded camera references")
        if attn.group_norm is not None:
            hidden_states = attn.group_norm(hidden_states.transpose(1, 2)).transpose(1, 2)
        query, key, value = attn.to_q(hidden_states), attn.to_k(hidden_states), attn.to_v(hidden_states)
        head_dim = key.shape[-1] // attn.heads
        query = query.view(count, -1, attn.heads, head_dim).transpose(1, 2)

        def combine(tensor: torch.Tensor, indices: tuple[int, ...]) -> torch.Tensor:
            selected = tensor[list(indices)]
            return selected.view(len(indices), -1, attn.heads, head_dim).permute(2, 0, 1, 3).reshape(1, attn.heads, -1, head_dim)

        result: list[torch.Tensor] = []
        for i, neighbours in enumerate(self.batch.neighbours):
            indices = neighbours or (i,)
            local = F.scaled_dot_product_attention(query[i:i + 1], combine(key, indices), combine(value, indices), dropout_p=0.0)
            if self.reference_weight:
                reference = F.scaled_dot_product_attention(query[i:i + 1], combine(key, self.batch.references),
                                                           combine(value, self.batch.references), dropout_p=0.0)
                local = (local + self.reference_weight * reference) / (1 + self.reference_weight)
            result.append(local)
        output = torch.cat(result).transpose(1, 2).reshape(count, -1, channels).to(query.dtype)
        output = attn.to_out[1](attn.to_out[0](output))
        if len(shape) == 4:
            output = output.transpose(-1, -2).reshape(shape)
        if attn.residual_connection:
            output += residual
        return output / attn.rescale_output_factor
