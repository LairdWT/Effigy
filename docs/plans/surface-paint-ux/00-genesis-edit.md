# Enable captured-view editing with Krea2 Genesis

Spoke: S00
Outcome: Enable captured-view editing with selected Krea2 Genesis NVFP4.
Depends-on: none
Decisions: D1, D3, D4
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, web:typescript-core
Read-set: INDEX.md, CODE.md, server/reference_models.py, steps/reference.py, ui/src/ReferenceModels.tsx, ui/src/SurfacePaint.tsx
Write-set: server/reference_models.py, steps/reference.py, ui/src/api.ts, ui/src/ReferenceModels.tsx, ui/src/SurfacePaint.tsx, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/00-genesis-edit.md
State: done

## Context

The owner selected Krea2 Genesis NVFP4 for painting. The current adapter supports
generation with that model, while captured-view image editing uses a different
route. Complete the selected model's route before setting it as the painting
default. Historical Ghibli results remain unchanged.

## Evidence

Baseline anchors describe the pre-implementation behavior.

- `server/reference_models.py:56` registers `krea-genesis` as generate-only,
  bound to D4's checkpoint and the existing Krea encoder/VAE configuration.
- `steps/reference.py:80` selects the GGUF loader for edit-mode models, whereas
  line 97 loads Krea safetensors. Changing the mode string alone would choose
  the wrong loader and text encoder.
- `steps/reference.py:160` derives accepted operations from that mode.
  Line 172 rejects denoise outside FLUX.
- `ui/src/SurfacePaint.tsx:172` defaults to `flux-ghibli`; line 203 submits edit
  requests. Existing successful Krea generation therefore does not prove this
  captured-view workflow is supported.
- D4's local checkpoint is present at 7673852176 bytes. Earlier metadata
  inspection identified NVFP4 weights; filename/format alone does not prove
  accelerated execution.

### Runtime observations

Implemented and qualified on 2026-10-20. Genesis supports both image generation
and captured-view editing; architecture now selects the loader independently of
operation. Source images are VAE encoded, denoise is explicit, and no FLUX LoRA
is attached. New work defaults to Genesis at 8 steps and denoise 0.35; historical
recipes retain their identities and parameters.

Runtime: job `01eaabbe44fc` -> `127_reference` (seed 24025, 1024 square,
8 steps, denoise 0.60, 122.09 s, 13.51 GiB Torch peak). Visible result moved
openings/chimney, so it was not applied. Same-input job `886bd9bcc353` ->
`128_reference` at denoise 0.35 retained the composition substantially better.
Job `3c81a8ca131c` -> `129_paint` applied selected roof triangles only:
409 triangles, 1024-square 16-bit atlas, 3076 permitted surface texels,
3086 changed texels including 10 adjacent gutters, zero outside/alpha changes.
These are tool samples, not owner approval of a finished hut.

Actual compute: all 256 NVFP4 layers reported `full_precision_mm`; the checkpoint's
embedded layer config explicitly sets `full_precision_matrix_mult: true`.
CUDA supports NVFP4, but this file executes dequantized full-precision matrix
multiplication. No claim of native FP4 tensor-core acceleration and no override
of the borrowed checkpoint. Source checks and UI build passed.

## Steps

1. Within the approved implementation scope, separate supported operations from
   architecture and checkpoint loading. Preserve existing generation and legacy
   edit routes without treating every editing model as GGUF.
2. Add Krea2 image-to-image preparation using the configured model, encoder and
   VAE: encode the captured image, initialize its latent and expose denoise.
   Use the installed Krea sampling contract; report a missing capability rather
   than substituting FLUX or downloading another checkpoint.
3. Preserve fixed camera/source lineage and the existing application mask. This
   is image-to-image plus masked projection; do not label it native inpainting.
   Do not attach FLUX-only LoRAs to Krea.
4. Make Genesis selectable and the default for new surface-paint work. Preserve
   saved model identities in historical recipes. Expose the effective parameters
   and show actionable local errors for unsupported combinations.
5. Run one ordinary 1K hut capture -> Genesis candidate -> masked application
   sample. Inspect actual compute path, memory and visible output. Compare with
   the source for material/feature drift, preserving geometry and UVs.

## Files to touch

- server/reference_models.py
- steps/reference.py
- ui/src/api.ts
- ui/src/ReferenceModels.tsx
- ui/src/SurfacePaint.tsx
- docs/LOCAL-SETUP.md
- docs/plans/surface-paint-ux/00-genesis-edit.md

## Verification

1. `.venv/Scripts/ruff.exe check server/reference_models.py steps/reference.py`
   and `npm --offline --prefix ui run build`. Expected: pass.
2. Normal hut workflow. Expected: job metadata identifies the selected Genesis
   file, output visibly uses the capture, and denoise is honored.
3. Applied result. Expected: 409 triangles, existing UVs and 1K atlas retained;
   unselected surfaces remain protected. Record actual quantized/dequantized
   execution rather than inferring native FP4 acceleration.

## Risks

Image-to-image support and quantized sampling require runtime qualification.
Style wording may need adjustment for Krea, but model selection is settled.
Capability labels must not advertise an unimplemented editing path.

## RESULT

Implemented and qualified. Genesis loads by architecture and supports captured-view image-to-image without FLUX LoRAs. Jobs 01eaabbe44fc/886bd9bcc353 produced 127/128_reference; denoise 0.35 retained layout better than 0.60. Selected-region application 3c81a8ca131c produced 129_paint with 409 triangles, 1K RGBA16 and zero protected/alpha changes. Runtime reported 13.51 GiB Torch peak. All 256 NVFP4 layers use full-precision matrix multiplication because the borrowed checkpoint explicitly requests it; native FP4 acceleration is not claimed. Ruff/UI build pass. Detailed ordinary output references and limits are under Runtime observations above.
