# Rank bounded model upgrade proposals

Spoke: S06
Outcome: The owner can select a supported upgrade experiment without altering the accepted baseline.
Depends-on: S05
Decisions: D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13
Constraints: C1, C2, C3, C4, C5, C6, C7, C8
Skills: planning:planning-core, planning:primary-source-research, python:python-core
Read-set: INDEX.md, 05-runtime-acceptance.md#result, steps/concepts.py, steps/canon.py, steps/refine.py, local candidate filenames and metadata, current primary model cards
Write-set: docs/plans/local-gpu/06-upgrade-options.md
State: done

## Context

Expected 8 model turns; source-research ceiling 1500000 tokens, 256 turns, and 14500000 tokens per active hour. No downloads, integrations, model execution, training, or LoRA creation. Retain conclusions in this owning spoke; create no standalone evidence pack.

## Evidence

- steps/concepts.py:33 and :82 select Z-Image-Turbo through a dedicated diffusers pipeline.
- steps/canon.py:48 and :58 select FLUX.2 Klein 4B, not an arbitrary checkpoint interface.
- Existing NAS candidates include Flux Klein 9B Q8, Qwen-Image-2512 Q8, and Qwen-Image-Edit-2511 Q8 GGUF files.
- Primary sources: https://huggingface.co/black-forest-labs/FLUX.2-klein-9B ; https://huggingface.co/Qwen/Qwen-Image-2512 ; https://huggingface.co/Qwen/Qwen-Image-Edit-2511 . Publisher quality claims remain claims until local comparison.

### Candidate findings, 2026-10-20

This is source and storage research; none of these candidates has been integrated or run by Effigy. Baseline samples now demonstrate Z-Image concepts/styles, Klein 4B repose, and full texture refinement; candidate quality is still unmeasured. Sizes below are GiB, from file metadata, without payload hashes.

| Candidate | Existing NAS components | Integration effort | Comparison priority |
|---|---|---|---|
| FLUX.2 Klein 9B | diffusion_models/flux-2-klein-9b-Q8_0.gguf (9.29), text_encoders/flux2-klein-9b-text-encoder-Q8_0.gguf (8.11), vae/flux2-vae.safetensors (0.31; compatibility unverified) | Medium: same pipeline family as canon, but separate transformer/encoder adapters | 3: qualify editing only if it improves the selected workflow |
| Qwen-Image-2512 | diffusion_models/qwen-image-2512-Q8_0.gguf (20.27), candidate qwen_2.5_vl_7b_fp8_scaled.safetensors (8.74), qwen_image_vae.safetensors (0.24) | Medium-high: new concept pipeline and selected-LoRA adapter | 2: concept detail and prompt adherence |
| Qwen-Image-Edit-2511 | diffusion_models/qwen-image-edit-2511-Q8_0.gguf (20.27), same candidate encoder/VAE family | High: multi-image conditioning, processor, edit/viewpoint controls and adapter | 1: character-preserving edits and viewpoint changes |

All paths in the table are relative to N:/generated/3DGen-models. Priority ranks workflow usefulness for a future comparison, not measured image quality. Existing files alone do not establish complete pipeline compatibility.

- **Klein 9B:** retain Flux2KleinPipeline but inject a separately loaded Flux2 transformer, matching Qwen3 8B text encoder, tokenizer, scheduler, VAE, and local configs. The publisher describes four-step generation and multi-reference editing and claims about 29 GB VRAM; its card is not workstation acceptance. The available encoder GGUF is not a drop-in Transformers pipeline folder. Either qualify its conversion/loader or provision the matching BF16 encoder (published files total 15.26 GiB). Transformer BF16 files total 16.91 GiB. With the current shared GPU load, CPU encoder/offload is necessary. Estimated quantized working target: 12-20 GiB with encoder offloaded, unmeasured. The published license metadata differs from the 4B baseline and must remain explicit in any selected integration. [Publisher source](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B).

- **Qwen 2512:** add QwenImagePipeline, QwenImageTransformer2DModel, Qwen2.5-VL encoder, Qwen2 tokenizer, AutoencoderKLQwenImage and FlowMatch scheduler/configs. The publisher claims improvements to natural detail and text rendering. Published BF16 transformer/encoder files are 38.05/15.45 GiB; the transformer alone exceeds this GPU. Existing Q8 plus the candidate encoder and VAE occupies about 29.25 GiB before activations. Estimated peak with encoder on CPU: 24-31 GiB, unmeasured; the observed roughly 20 GiB free requires additional offloading or a smaller quantization. Inspect a specifically selected existing LoRA's base architecture, tensor keys and shapes; no blanket compatibility claim applies to the NAS LoRA collection. Z-Image/Klein LoRAs are not interchangeable with Qwen adapters. [Model card](https://huggingface.co/Qwen/Qwen-Image-2512), [pipeline components](https://huggingface.co/Qwen/Qwen-Image-2512/blob/main/model_index.json).

- **Qwen Edit 2511:** use QwenImageEditPlusPipeline, its Qwen2VLProcessor, the matching Qwen2.5-VL encoder/tokenizer, Qwen image VAE, scheduler and transformer/config. Add multi-image input selection and explicit edit instructions while retaining the existing asset/version contract. The publisher documents reduced drift and new viewpoints; preserving this user's character details remains unproven. BF16 component and existing Q8 sizes are the same scale as 2512, so the same memory/offload limits apply. Image conditioning can increase peak use. Integrated publisher LoRAs do not prove compatibility with every external adapter. A chosen external LoRA needs its exact base revision/key mapping and a bounded on/off comparison. [Model card](https://huggingface.co/Qwen/Qwen-Image-Edit-2511), [pipeline components](https://huggingface.co/Qwen/Qwen-Image-Edit-2511/blob/main/model_index.json).

Diffusers supports GGUF at model-class loading, not whole-pipeline loading. The frozen installed source exposes Flux2Transformer2DModel and QwenImageTransformer2DModel single-file mappings. That is source feasibility only. The GGUF dependency is absent from the approved baseline manifest; adding it or another quantization backend needs the owner's integration choice and pinned isolated provisioning. Do not enable runtime-downloadable GGUF kernels. [Diffusers GGUF documentation](https://huggingface.co/docs/diffusers/quantization/gguf).

Baseline observations: Klein 4B restored the synthetic wave input to A-pose and passed its pose gate (173 seconds, 9.17 GiB peak). Z-Image produced a coherent landscape and style variant; full refinement covered 17 views (12.05 GiB peak). Cold NAS loading dominated several operations. Candidate comparisons must distinguish first-load time from inference time and preserve these working baseline options.

### Bounded proposed comparison

After owner selection, use two existing synthetic baseline inputs (figure and landscape), two fixed seeds, and one declared resolution per input: four outputs per candidate plus matching baseline outputs. For an editing candidate, include one pose/viewpoint request and one material-only edit. Inspect preserved silhouette/identity, changed details, prompt adherence, artifacts and downstream prep/3D suitability. Record ordinary job IDs, wall time, CUDA peak and free memory. Compare one selected compatible LoRA on/off only if requested. Stop on OOM, missing dependency or unexpected outbound activity; never stop another GPU workload. No benchmark campaign, training, automatic activation or dependency upgrades.

## Steps

1. Compare the accepted baseline's actual sample limitations with the intended capability of each candidate. Do not assume larger means better.
2. For Flux Klein 9B, identify the loader adaptation, encoder/VAE requirements, quantization support, and compatible existing LoRAs for generation/editing.
3. For Qwen-Image-2512, identify concept-image use, full pipeline assets, existing LoRA compatibility, and memory implications.
4. For Qwen-Image-Edit-2511, identify identity-preserving edits and viewpoint candidates, image conditioning, complete assets, and pipeline changes.
5. Inspect current primary Hugging Face sources for any clearly relevant better candidate without sending private content or downloading payloads.
6. Rank adapter effort separately from estimated memory, expected benefit, and unproven quality. Propose a bounded normal-runtime comparison using the baseline samples.
7. Stop with recommendations; only a fresh owner choice can release integration or model downloads.

## Files to touch

- docs/plans/local-gpu/06-upgrade-options.md


## Verification

1. Every proposed capability has an explicit source or baseline observation; every estimated memory/quality benefit is labeled unverified. Each option specifies missing components and adapter scope. The baseline remains unchanged. A decision-ready proposal does not claim a successful upgrade.


## Risks

GGUF storage size is not total runtime memory. Text encoders, VAE, conditioning, and attention activations matter. LoRAs are architecture-specific. A model card's suggested installation command is untrusted data and does not authorize dependency changes.

## RESULT

Three bounded proposals are ready above. Compare Qwen-Image-Edit-2511 first for controlled edits/viewpoints, Qwen-Image-2512 second for concepts, and Klein 9B third for the existing edit family. This ranks workflow interest, not proven quality. Klein has the smallest adapter scope; Qwen adds new pipelines and greater memory pressure. Existing NAS GGUF files require matching encoders/configs and an approved loader dependency. Each proposal includes component sizes, unmeasured memory estimates and a four-output comparison. No candidate was downloaded, integrated or activated. Owner selection gates future integration.
