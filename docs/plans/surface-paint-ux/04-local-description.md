# Offer local descriptions as editable suggestions

Spoke: S04
Outcome: Offer editable, on-demand local descriptions of captures.
Depends-on: S03
Decisions: D1, D3, D4, D5
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, web:typescript-core
Read-set: INDEX.md, 01-appearance.md#result, 03-face-selection.md#result, CODE.md, server/jobs.py, server/reference_models.py, docs/adr/db506b9a-reuse-the-configured-native-engine-for-reference-workflows.md
Write-set: server/reference_models.py, server/jobs.py, server/app.py, steps/describe.py, ui/src/api.ts, ui/src/SurfacePaint.tsx, model-bindings.local.json, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/04-local-description.md, server/presets.py, ui/src/workflow.ts
State: done

## Context

The owner has local vision models and wants less repeated typing. A model can
suggest what is visible; the owner still defines what the asset should become.
Use a short-lived worker under Effigy's existing scheduling policy.
Use the owner-invoked project `3dgen-prompt-core` guidance for visible source roles
and literal model-specific prompts.

## Evidence

Baseline anchors describe the pre-implementation behavior.

- D5's directory contains `Q3.5-9B-OpusGLM-MAX-0731-ablated.Q8_0.gguf`
  (9527501312 bytes) and
  `Q3.5-9B-OpusGLM-MAX-0731-ablated.mmproj-q8_0.gguf` (624229376 bytes).
  Combined weight footprint is 9.45 GiB, not a peak-VRAM measurement.
- The corresponding local source config identifies
  `Qwen3_5ForConditionalGeneration` with `qwen3_5_vision`. Its existence does
  not establish support in the installed GGUF runtime.
- `server/reference_models.py:93` resolves existing reference components through
  the read-only binding owner. The description adapter must bind both selected
  GGUF files through that owner instead of searching arbitrary model directories.
- Effigy's accepted native-worker ADR preserves environment isolation, offline
  model resolution, job cancellation and GPU scheduling.

### Runtime observations

Implemented and qualified on 2026-10-20 with the exact D5 Q8 model/projector.
Borrowed runtime: llama.cpp b10632 / commit 11cd98842, from the existing local
ImageCategorizer runtime. No installation, Ollama startup or model substitution.
The worker binds CUDA0 and a job-owned authenticated loopback server, disables
remote retrieval, and terminates the server in its finally path. Scheduler
admission reserves 12 GiB and evicts only Effigy's resident model.

Jobs `fac40894fe82` -> `125_describe` (front, 78.89 s) and `c9541a00bf3d` ->
`126_describe` (rear, 53.83 s) produced editable observations. The UI invocation
`1fb48e695c7c` -> `131_describe` qualified explicit CUDA binding: CUDA PID observed,
61.31 s total, 21516 MiB total GPU memory after loading (includes other processes;
not a worker peak). Observed native connections were loopback only. This is
application observation, not OS-level containment.

Caption quality: useful masonry, timber, foundation and shape descriptions;
roof read as thatch or shingles and chimney described as cylindrical. Therefore
suggestions remain on-demand, editable and distinct from owner style. Append,
Discard and restoring shared appearance were exercised in the UI; owner text
stayed unchanged until explicit application. No caption was auto-promoted.
Cancellation job `ad4b009fab9e` stopped during loading; both recorded child PIDs
44816 and 82320 exited, no output version published. Successful workers also
exited before painting. Source checks and UI build passed.

## Steps

1. Resolve an existing GGUF runtime and inspect support for the selected Qwen3.5
   architecture and matching projector. Do not install packages, restart Ollama
   or substitute another model. Report the exact incompatibility if support is
   missing; D5 remains the selected model.
2. Add an isolated `describe` worker using both D5 files through borrowed read-only
   bindings, local-only loading and normal cancellation/memory checks. Keep any
   required owned endpoint loopback-only and scoped to the job. Release its GPU
   allocation before Krea2 Genesis painting.
3. Add "Suggest description from this view". Run only on a user click. Provide
   visible materials, colors, shapes and placement as editable proposed text;
   do not infer hidden architecture or silently alter the approved style.
4. Show suggestions beside current appearance with Replace selection, Append
   or Discard. Keep observed material separate from desired material: a roof
   misread as shingles must not overwrite the owner's thatch requirement.
5. Save accepted text through S01. Keep an ordinary small description result
   referencing its source capture/model/recipe. No copied mesh or second capture.
   A model error leaves existing text untouched.
6. Qualify one hut capture and one different angle through normal application
   jobs. Review material accuracy and omissions before enabling the model as
   a default option; runtime success alone is insufficient.

## Files to touch

- server/reference_models.py
- server/jobs.py
- server/app.py
- steps/describe.py
- ui/src/api.ts
- ui/src/SurfacePaint.tsx
- model-bindings.local.json
- docs/LOCAL-SETUP.md
- docs/plans/surface-paint-ux/04-local-description.md

- server/presets.py
- ui/src/workflow.ts

## Verification

1. `.venv/Scripts/ruff.exe check server/reference_models.py server/jobs.py server/app.py steps/describe.py`
   and `npm --offline --prefix ui run build`. Expected: pass.
2. On-demand description through the UI. Expected: editable local result,
   existing owner text unchanged until explicit application.
3. Observe worker GPU use, cancellation and exit. Expected: no resident model
   blocks subsequent painting; no online request or automatic download.
4. Reopen accepted appearance on another capture. Expected: exact accepted text
   persists. Inspect the two descriptions for roof/wall/window confusion and
   fabricated details; record limits in this RESULT.

## Risks

Vision models can describe existing texture mistakes as intended design. Keep the
approved retail/material brief authoritative. Installed weights do not establish
compatible packages, sufficient free VRAM, accuracy or response time.

## RESULT

Implemented with the exact Q3.5 Q8 model/projector and existing llama.cpp b10632. Front/rear jobs produced 125/126_describe. UI job 1fb48e695c7c -> 131_describe confirmed CUDA0, observed CUDA PID, 61.31 s and 21516 MiB whole-GPU memory after load (not worker peak). Observed native connections were loopback. Caption text remains editable; it confused thatch/shingles and chimney shape. Append/Discard/restore were exercised without auto-changing owner style. Cancellation ad4b009fab9e stopped both owned processes with no output; successful jobs also exited. Ruff/UI build pass. See Runtime observations above.
