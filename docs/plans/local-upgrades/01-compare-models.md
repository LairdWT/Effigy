# Sample the existing candidate models

Spoke: S01
Outcome: Compare existing Krea2 and Qwen Edit candidates through local image samples while preserving the accepted Effigy baseline.
Depends-on: none
Decisions: D1, D2
Constraints: C1, C2, C3, C4
Skills: planning:prototypes-and-spikes, python:python-core
Read-set: INDEX.md, ../local-gpu/05-runtime-acceptance.md#result, ../local-gpu/06-upgrade-options.md, existing model metadata and configured native inference source
Write-set: scratch/upgrades/, N:/generated/Effigy/, docs/plans/local-upgrades/
State: done

## Context

Owner wants real local trials. Reuse installed native inference modules in a separate process, with explicit local paths and an outbound Python socket guard. No server is launched or existing environment altered. Candidate image suitability is the decision; one first image can reject a broken loader. If successful, use two synthetic inputs and seeds 24/25, at most four images per candidate. Stops: missing dependency, OOM, outbound attempt, or unusable image. No repeated timing campaign.

## Evidence

- Existing krea2-turbo.safetensors is 12.24 GiB FP8; its quantization metadata names float8_e4m3fn and selected full-precision matmuls.
- Existing checkpoints/Krea2_Genesis-Blackwell-Optimized-nvfp4.safetensors is 7.15 GiB; metadata identifies nvfp4 and source See-Krea2-Genesisv2.safetensors. It is not the same checkpoint as Turbo, so output/timing differences cannot be attributed solely to precision.
- Existing qwen3vl_4b_fp8_scaled.safetensors, qwen_2.5_vl_7b_fp8_scaled.safetensors, qwen_image_vae.safetensors and qwen-image-edit-2511-Q8_0.gguf exist. No payload hashes were read/computed.
- D:/AI/3DGen/ComfyUI-Easy-Install/ComfyUI/comfy/ops.py:1178 loads NVFP4 scales; :1651 selects hardware support. supported_models.py:1887 supports Krea2. comfy_extras/nodes_qwen.py:53 provides the installed edit conditioning operation.
- Effigy also contains Krea2Pipeline, but these Comfy-format quantized checkpoints are not direct pipeline replacements. Reusing the existing native engine avoids unapproved package or encoder downloads for this experiment.
- Primary sources checked 2026-10-20: https://huggingface.co/Comfy-Org/Krea-2 lists official Turbo NVFP4, Qwen3-VL 4B encoder and Qwen image VAE; https://github.com/krea-ai/krea-2 recommends Turbo for inference. Official NVFP4 would be 7673668448 bytes at revision 1171f4dc7e325bf3734586942e737872506c73e1; owner declined that download.

### Completed Krea observations

| Candidate | Setup seconds | Warm 768x512 sampling | Warm 1024-square sampling | Peak allocated GiB | Effigy assets |
|---|---:|---:|---:|---:|---|
| Genesis NVFP4, stored defaults | 20.96 | 2.22 s | 5.53-5.65 s | 13.54 | upgrade_krea2_genesis_nvfp4_landscap; upgrade_krea2_genesis_nvfp4_figure |
| Turbo FP8 | 29.53 | 6.24 s | 6.13-6.42 s | 12.77 | upgrade_krea2_turbo_fp8_landscape; upgrade_krea2_turbo_fp8_figure |

Each named asset has seed 24 at 001_upload and seed 25 at 002_upload. Cold first-image time also includes transfers: 103.54 s after setup for Genesis, 150.75 s for FP8. These are observations, not a benchmark: checkpoint weights differ and available memory varied. FP8 entered with 17.06 GiB physically free and offloaded encoder/model sections; its lower observed peak does not mean its weights are smaller. Subsequent trials use nvidia-smi physical free memory because CUDA's Windows free-memory report exceeded physical headroom.

Visual observations: Genesis landscapes have finer foliage/stone detail and stronger spatial depth; Turbo landscapes use broader cartoon shapes. Both produced intact centered mannequin silhouettes and the requested A-pose. This is a two-prompt sample, not a universal quality ranking.

Hardware finding: all 256 Genesis quantization records set full_precision_matrix_mult=true. The extra profiler sample recorded CUDA dequantize_nvfp4 plus comfy_kitchen::dequantize_nvfp4, without an NVFP4 matrix multiply. Thus its stored defaults compress weights but do not demonstrate the requested FP4 matrix acceleration. The in-memory native variant is a separate pending experiment; shared weights are unchanged.

## Steps

1. Resolve existing tools and named weights, verify free CUDA memory, and create a disposable runner in owned scratch.
2. Load Krea2 Genesis NVFP4, then Turbo FP8, using the same encoder, VAE, direct prompts, size, seeds and eight-step Euler/simple sampling. Record cold-load and sample timing separately in PNG metadata and stdout. Metadata inspection found all 256 Genesis NVFP4 layers explicitly request full-precision matrix multiplication. Also try a separate in-memory native-NVFP4 variant (up to four images); leave the checkpoint unchanged and retain the ordinary variant as its control. Profile its first image; exclude profiled timings from speed comparisons.
3. Run Qwen Edit 2511 with existing Q8 loader and encoder on the baseline figure and landscape, using explicit edit instructions and seeds 24/25. CPU offloading is allowed; no other workload is stopped.
4. Inspect actual images, CUDA memory and native quantization behavior. If dispatch counters do not identify the executed NVFP4 backend, allow one additional CUDA-profiler image sample; its instrumented timing is excluded from comparisons. Import successful images through the ordinary Effigy upload API for owner review.
5. Compare composition, prompt adherence and edit preservation against baseline samples. Record failures and confounders; do not claim a pure quantization speedup or automatic model upgrade.

## Files to touch

- scratch/upgrades/
- N:/generated/Effigy/
- docs/plans/local-upgrades/

## Verification

1. Project Ruff on the disposable runner -> source check passes; no code tests.
2. Ordinary generated PNGs and Effigy upload identities -> images open and show the requested synthetic scene/edit.
3. Actual CUDA allocation and socket observation -> CUDA 0 used, no observed outbound connection; no OS-containment claim.
4. AEP plan check -> structural pass; baseline source and model bindings remain unchanged.

## Risks

Genesis and Turbo differ in weights, not just quantization. File size is not peak VRAM. Native backend support alone does not prove the selected matrix kernels execute or that images improve. A cold NAS load is not inference latency. Qwen Q8 may offload substantially under the shared GPU load.

## RESULT

Preliminary trials completed; owner D3/D4 replaced image-only comparison with workflow integration. Four Genesis NVFP4 and four Turbo FP8 images are in Effigy; their timing/quality observations are above. All 256 Genesis NVFP4 layers request full-precision matrix math; profiler confirmed dequantization, not native FP4 matmul. Qwen Edit produced copper-material figures; its lower-resolution landscape edit changed framing and needs the model-default resolution in the integrated worker. No model downloads or shared environment changes. Unstarted controls and native-FP4-only comparison scripts are superseded by S02; no automatic image-only expansion.
