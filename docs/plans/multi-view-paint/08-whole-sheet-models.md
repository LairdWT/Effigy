# Run FIBO, Genesis and MOSS whole sheets and MOSS references

Spoke: S08
Outcome: Run FIBO, Genesis and MOSS whole sheets and MOSS references
Depends-on: S06, S07
Decisions: D7, D8, D9, D10, D11, D12
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, planning:planning-core
Read-set: CODE.md, docs/plans/multi-view-paint/INDEX.md
Write-set: steps/paint_generate.py, steps/reference.py, server/reference_models.py, server/jobs.py, server/presets.py, tools/native_reference_entry.py, tools/stage_multi_view_trial.py
State: done

## Context

Owner approved the full-view revision on 2026-10-21. Prior paired-sheet anchors failed stone scale and mortar alignment; preserve their RESULT sections and rejected assets. Activate only trial 8380. Expected turns: 20; preserve usage history and standing circuit breakers. No per-unit handoff stops.

## Evidence

- server/paint_sessions.py:26 owns session creation; steps/_paint_set.py:25 owns surface projection.
- Session owner: server/paint_sessions.py; fixed captures and protected bake: steps/_paint_set.py.
- Prior S01-S05 RESULT sections distinguish implementation from incomplete visual and lifecycle acceptance.
- Source 167_upload and foundation selection 173_paint_set retain 409 triangles and the existing 1024 RGBA16 atlas.
- The earlier coverage calculation found fifteen cameras covering 92238 reachable texels; actual 512-resolution coverage must be recalculated.
- SyncMVD source: https://github.com/LIU-Yuxin/SyncMVD . MOSS v2 Euler recipe: https://huggingface.co/akhaliq/MOSS-Image-SFT-4-steps .

## Steps

Generalize workers to exact recorded panel rectangles. FIBO receives the complete sheet with four-step structure-preserving reference conditioning. Genesis uses eight Euler/simple steps, CFG 1 and differential masking at denoise 0.35. MOSS uses borrowed SFT BF16, Qwen3.5 9B INT8 encoder, Flux2 VAE and moss_image_sft_4step_v2.0 LoRA at strength 1 in the installed private native runtime. Verify loaded LoRA keys and actual precision. References use 1024-square/four steps; experimental painting uses eight Euler steps and denoise 0.35. Composite exact source RGB and alpha outside permission. Persist complete candidates, release workers and require 28 GiB free VRAM for full-sheet qualification.

## Files to touch

- steps/paint_generate.py
- steps/reference.py
- server/reference_models.py
- server/jobs.py
- server/presets.py
- tools/native_reference_entry.py
- tools/stage_multi_view_trial.py

## Verification

1. Run scoped static commands after relevant source changes; expected zero findings. Record runtime acceptance separately below.
Run scoped Ruff after Python changes, the offline trial UI build after UI changes, and AEP plan validation after plan changes. Do not write or run code tests or hash sweeps. Use ordinary application jobs and baked renders for runtime acceptance. Installation and static success do not establish art quality. Preserve completed work across interruption.

## Risks

- Whole sheets may alter framing, stone scale or style despite shared context; inspect baked candidates.
- SyncMVD is a new masked adaptation requiring qualification, not a proven drop-in renderer replacement.
- GPU capacity, local compatibility or NAS failures may block runtime work; report exact errors and preserve completed candidates.
- Rejected art is a valid comparison result, not production qualification. No acceptable winner is permitted as a comparison conclusion; technical blockers remain incomplete.
- Owner visual acceptance and primary promotion remain separate. Network observation does not prove OS containment.

## RESULT

FIBO, Genesis and MOSS each completed three whole-sheet candidates on the RTX5090. FIBO193/207/221, Genesis196/210/224 and MOSS200/214/228 preserve exact permission and alpha. Peak allocated memory:13.416/15.519/13.416GiB respectively. Genesis reports256 NVFP4 layers using full_precision_mm; no native FP4 acceleration claim. MOSS loaded756 Turbo v2 keys into252 modules. Its first painting attempt failed on inference-tensor version handling; using no_grad in the owning worker resolved it without engine changes. Reference187 remains separate and unapplied. Each batch loads one worker and releases it. Sampling91.77-107.10s FIBO,100.41-114.87s Genesis,43.02-47.25s MOSS. All three remain unqualified for the requested coherent small-stone artwork.
