# Trial smaller MOSS view sheets on the whole hut

## Outcome

Preserve the owner's Genesis foundation result and create a separate MOSS Turbo painting session covering the whole hut. Expose smaller registered camera panels and explicit MOSS step counts, then inspect the combined texture on the unchanged mesh.

## Decisions

- D1 (2026-10-21): Owner likes the existing Genesis result and requests a separate whole-house trial. Use Genesis227_paint_set as the immutable source; retain and star it. No previous versions are overwritten.
- D2: Owner permits considering panels smaller than512. First implementation trial uses192-square panels and four MOSS Turbo steps; compare384-square/eight-step output if the draft establishes useful material/layout behavior. Maximum three new painting candidates in this follow-up; the previous twelve-candidate comparison remains closed.
- D3: Reuse the installed MOSS SFT BF16 model, INT8 encoder, VAE and Turbo v2 LoRA. No new checkpoint, GGUF conversion, download or engine change in this trial.
- D4: Smaller-panel MOSS jobs use the existing model-specific18GiB admission requirement and per-worker memory cap. Historical512 qualification keeps its28GiB gate. Workers are released after each submitted batch.
- D5: The final atlas remains1024RGBA16, with unchanged geometry, UVs, alpha and other maps. Smaller panels change generation detail and reachable coverage; upsampling is not accepted as evidence of repaired continuity.
- D6: Full-house capture requires all26 cameras. Small-panel MOSS supports this complete pool in a fixed six-column/five-row layout:1152x960 at192 pixels. Existing512 layouts and their25-view limit remain unchanged.
- D7 (2026-10-21): Owner rejected visible seams. Diagnose and repair projection defects on8380, reusing existing generated images. Preserve original and historical outputs. No new inference or model changes in this repair.

## Constraints

- C1: Activate only8380. Preserve8370, other GPU work, borrowed models and unrelated WIP. No subagents, tests, hashes, commits, pushes, CI, engine upgrades or hosted processing.
- C2: Keep historical sessions readable at their original704/512 sizes. New panel size is immutable within a session. Recompute coverage at the actual size; never omit necessary cameras silently.
- C3: Use ordinary application versions and owning RESULT sections. No additional evidence packs, audits or broad cleanup. Source remains in Effigy; stage explicit files into the trial overlay.
- C4: Preserve prior usage history and the256-turn circuit breaker; implementation ceiling2250000, acceptance ceiling1032000 targeting300000, rate14500000 tokens per active hour. No automatic per-unit handoff stops.

## Terms

- Draft: a smaller complete view sheet used to judge material identity, framing and broad continuity before finer detail.
- Retained Genesis: version227_paint_set and its existing lineage; owner preference is recorded without claiming the known seam is fixed.

## Requirements

| Requirement | Implementation | Acceptance |
|---|---|---|
| Immutable panel sizes and model-specific step controls | S01 | S02 |
| Complete whole-house MOSS painting | S01 | S02 |
| Preserve source and atlas contracts | S01 | S02 |
| Separate measured generation, loading and art quality | S02 | S02 |
| Projection does not introduce island-edge fades or resample unchanged source detail | S03 | S03 |

## Spokes

| ID | File | Outcome | Depends on | Skills | Write set | State | Commit | Result |
|---|---|---|---|---|---|---|---|---|
| S01 | 01-small-view-controls.md | Add immutable small-panel MOSS sessions and step controls | none | python:python-core, web:typescript-core | server/paint_contracts.py, server/paint_sessions.py, server/paint_routes.py, server/jobs.py, steps/_paint_set.py, steps/paint_generate.py, ui/src/MultiViewPaint.tsx, ui/src/multi-view-api.ts, tools/stage_multi_view_trial.py | done | - | 01-small-view-controls.md#result |
| S02 | 02-whole-house-trial.md | Evaluate a separate whole-house draft and bounded detail correction | S01 | planning:planning-core, python:python-core, powershell:powershell-core | docs/plans/whole-house-moss/02-whole-house-trial.md, scratch/lanes/fibo2 | done | - | 02-whole-house-trial.md#result |
| S03 | 03-projection-seams.md | Repair projection sampling and distinguish remaining generated-view seams | S02 | python:python-core, planning:planning-core, art:texture-painting-core | steps/_paint_projection.py, steps/_paint_set.py, server/paint_routes.py, server/paint_sessions.py, tools/stage_multi_view_trial.py | done | - | 03-projection-seams.md#result |

## Reading rule

Read this index, the owning spoke and named dependency RESULT. Prior comparison evidence remains in docs/plans/multi-view-paint/11-runtime-comparison.md. Do not rerun its closed candidate budget or unchanged checks.

## Non-goals

Quantization replacement, additional model downloads, resident GPU services, primary promotion, changing SyncMVD resolution, automatic UV/geometry repair, atlas enlargement and claiming a1.4-second end-to-end runtime.

## Open questions

(none for this bounded trial)
