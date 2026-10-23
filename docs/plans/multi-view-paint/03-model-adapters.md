# Qualify paired editing with both existing local models

Spoke: S03
Outcome: Qualify paired editing with both existing local models
Depends-on: S01, S02
Decisions: D1, D2, D3, D4, D5, D6
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, powershell:powershell-core
Read-set: CODE.md, docs/plans/multi-view-paint/INDEX.md, steps/paint_generate.py, tools/fibo_trial_worker.py, tools/native_reference_entry.py, steps/reference.py, server/reference_models.py, server/jobs.py, server/presets.py, server/paint_sessions.py, tools/stage_multi_view_trial.py
Write-set: steps/paint_generate.py, tools/fibo_trial_worker.py, tools/native_reference_entry.py, steps/reference.py, server/reference_models.py, server/jobs.py, server/presets.py, server/paint_sessions.py, tools/stage_multi_view_trial.py
State: stale

## Context

Also follow the owner-supplied project skill3dgen-prompt-core for model-specific prompt channels; its canonical name has no bundle-qualified alias.

The owner requested a complete workflow after sequential views produced mismatched materials. Joint paired editing is a hypothesis to qualify, not guaranteed shared3D structure. The original small foundation stones must be restored; the larger wrap is rejected. The single-view workflow remains available. Keep code ownership in the Effigy checkout and activate only the isolated trial. New file names in Read-set are implementation destinations and are read only after creation.

## Evidence

- steps/paint.py:163 dispatches single capture/application; lines247-318 own visibility and protected texture writes.
- server/library.py:304 resolves immutable output aliases; lines338-363 own dependencies and geometry lineage.
- server/jobs.py:144 chooses worker interpreters; runtime publication belongs to the backend.
- tools/fibo_trial_worker.py:40 constrains FIBO to one fixed capture today.
- steps/reference.py:204 owns Genesis differential masking.
- ui/src/SurfacePaint.tsx:62 is the existing single-view entrypoint.
- docs/plans/surface-paint-ux/00-genesis-edit.md:55 records full-precision matrix multiplication for borrowed NVFP4 weights.

## Steps

1. Route FIBO through the isolated runtime and Genesis through its configured native runtime. Borrow existing models read-only; do not change shared engines or claim native NVFP4 compute.
2. Adapt both to two704-square panels at1408x704. FIBO uses four steps and structure-preserving conditioning by default. Genesis uses eight steps, denoise0.35 and existing remaining settings.
3. Retain complete sheet context, apply exact selection compositing and preserve panel coordinates. Snapshot model-specific prompts, cameras, seed, settings and permission.
4. Keep one model loaded per submitted batch, process groups serially and release afterward. Persist completed groups across interruption, resume only missing work and preserve foreign GPU processes.
5. Restore foundation texels from143 into164 on one new candidate. Qualify one pair for each model before wrap propagation; allow one diagnosed correction per model, then hold a failing adapter incomplete.

## Files to touch

- steps/paint_generate.py
- tools/fibo_trial_worker.py
- tools/native_reference_entry.py
- steps/reference.py
- server/reference_models.py
- server/jobs.py
- server/presets.py
- server/paint_sessions.py
- tools/stage_multi_view_trial.py

## Verification

1. Run the installed Ruff check against changed Python files from the project root; expected: zero findings. Do not autoformat unrelated files.
2. For UI changes run npm --offline --prefix scratch/lanes/fibo2/ui run build; expected: successful TypeScript compilation and bundling.
3. Run agent-code-skills plan check docs/plans/multi-view-paint after plan changes; expected: no structural findings. This does not prove visual quality.
4. Use ordinary application job identities and output references for behavior. Expected: the actual mesh retains409 triangles, original UVs, one1024 RGBA16 atlas and exact alpha, with protected texels unchanged. No code tests or hashes are authorized.


## Risks

- Shared sheets can lose detail, invent geometry in pixels or move panel content: reject the baked candidate and hold the adapter if one diagnosed correction also fails.
- Concurrent owner work or stale revisions: reject writes rather than silently rebasing or modifying another job.
- Runtime or browser access may be unavailable: complete independent work and state the exact remaining acceptance surface.
- NAS or GPU capacity failure: preserve completed work and report; never replace storage or stop foreign processes.

## RESULT

Both GPU adapters ran on the RTX 5090. FIBO job `fb66b6e7163d` -> `174_paint_group` peaked at 14.906 GiB; Genesis `3df5c4dbc61f` -> `176_paint_group` peaked at 13.439 GiB. Exact protected pixels/alpha passed. Both initial anchors failed smaller-stone/style qualification.

The one allowed correction per model is exhausted. FIBO `8378a699eccf` -> `180_paint_group` used explicit fine courses and blank-region repair; its bake `184_paint_set` still has coarse blocks and wooden-looking risers. Genesis `c6e8980cd154` -> `182_paint_group` used finer-course appearance wording and denoise 0.55; bake `185_paint_set` retains oversized blocks and invents wooden strips. Panel mortar disagreement remains visible.

Both adapters are incomplete at the visual gate. No wrap propagation, Apply, substitution or further reroll occurred. Rejected candidates are labelled in the library. Further qualification needs an owner-approved plan change; Ruff passed.

