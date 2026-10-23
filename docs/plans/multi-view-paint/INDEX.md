# Implement full-view painting, synchronized diffusion, and MOSS Turbo

## Outcome

Compare FIBO, Genesis, MOSS whole sheets and synchronized SyncMVD with one protected bake. Activate only8380; preserve8370.

## Decisions

- D1-D6 (2026-10-21): Original paired-view workflow and its results remain in S01-S05. Pair-only qualification is superseded below.
- D7 (2026-10-21): Compare complete-sheet editing against synchronized diffusion; select SyncMVD instead of six-view MV-Adapter.
- D8: Permit explicit online provisioning for isolated Python 3.12/Torch 2.8 CUDA 12.8; generation remains offline.
- D9: Include borrowed MOSS Turbo v2.0 in references and experimental painting using Euler/simple.
- D10: 512 pixels/view; final 1024 RGBA16 atlas unchanged. Initial sixteen-panel bound superseded by D13; SyncMVD supports every eligible camera.
- D11: Baseline plus two diagnosed corrections per method, twelve painting candidates maximum. Repair technical failures before judging art.
- D12: Source 167_upload, foundation mask 173_paint_set. Preserve old rejected results. Require 28 GiB free VRAM for full-sheet qualification.
- D13 (2026-10-21): Approved5x5/2560 sheet for21 required512-pixel views; preserve coverage and atlas.
- D14 (2026-10-21): Approved one FIBO attempt above26GiB without resolution/camera changes; later attempts retain28GiB.
- D15 (2026-10-21): Approved ungated stable-diffusion-v1-5/stable-diffusion-v1-5 mirror at451f4fe16113bff5a5d2269ed5ad43b0592e9a14; normal ControlNet unchanged.
- D16 (2026-10-21): Owner released Blender and authorized GPU-app closure. Idle Anima8290 closed. D14 used by49158919be05; thresholds unchanged.

## Constraints

- C1: No subagents, code tests, hash sweeps, hosted inference, telemetry, commits, pushes, CI, firewall changes, training or engine upgrades. Internet only during explicit provisioning.
- C2: Preserve primary, foreign work, borrowed checkpoints and unrelated WIP. D16 permits closing GPU apps when needed; leave them alone when memory suffices.
- C3: Preserve geometry, UVs, alpha, other maps and atlas dimensions. Reject unsupported UVs; preserve unseen texels.
- C4: Ordinary outputs and owning RESULT only; no extra audits/evidence packs/cleanup. Owned models on NAS; environments/scratch on D:. NAS failure stops publication.
- C5: Serialized generation; two CPU bake workers maximum; SyncMVD micro-batches at most six views including references. No automatic resolution/camera/model fallback.
- C6: Preserve history and 256-turn breaker; implementation ceiling2250000, acceptance1032000 targeting300000, rate14500000 tokens/active hour. S06-S11 expected turns18/12/20/24/18/20. No per-unit handoff stops.

## Requirements

| Requirement | Implementation | Acceptance |
|---|---|---|
| Registered coverage, atomic candidates, protected bake | S06 | S11 |
| Isolated pinned runtime and owned downloads | S07 | S11 |
| Three whole-sheet adapters and MOSS references | S08 | S11 |
| Shared-texture synchronization through thirty updates | S09 | S11 |
| Comparison UI, persistence, resume and alias Apply | S10 | S11 |

Unmet S02-S05 acceptance moved to S11. Rejected art is a valid comparison outcome; technical gaps remain incomplete. Owner art acceptance and primary promotion are separate.

## Terms

- Whole-set candidate: atomic generation bound to source, mask, layout, recipe and seed; no silent mixing of panels from different generations.
- Full sheet: recorded 512-square rectangles, four columns up to sixteen views, five columns up to twenty-five; deterministic greedy coverage followed by redundant-view removal.
- Synchronized diffusion: collect every prediction before each shared texture update; restore protected context at the corresponding noise level.
- Parallel bake: deterministic CPU contributions composed into one atlas with sharp dominant-view ownership.

## Spokes

| ID | File | Outcome | Depends on | Skills | Write set | State | Commit | Result |
|---|---|---|---|---|---|---|---|---|
| S01 | 01-session-capture.md | Own persistent sessions and capture shared mesh selections | none | aep:aep-core, python:python-core, web:typescript-core | server/paint_sessions.py, server/paint_routes.py, server/app.py, server/library.py, server/jobs.py, steps/paint_set.py, steps/_paint_set.py | done | - | 01-session-capture.md#result |
| S02 | 02-combined-bake.md | Compose all eligible views into one protected texture preview | S01 | python:python-core, art:texture-painting-core | steps/_paint_set.py, steps/paint_set.py, server/paint_sessions.py | stale | - | - |
| S03 | 03-model-adapters.md | Qualify paired editing with both existing local models | S01, S02 | python:python-core, powershell:powershell-core | steps/paint_generate.py, tools/fibo_trial_worker.py, tools/native_reference_entry.py, steps/reference.py, server/reference_models.py, server/jobs.py, server/presets.py, server/paint_sessions.py, tools/stage_multi_view_trial.py | stale | - | - |
| S04 | 04-painting-ui.md | Expose the complete multi-view painting workflow | S03 | web:typescript-core, web:css-core | ui/src/MultiViewPaint.tsx, ui/src/multi-view-paint.css, ui/src/multi-view-api.ts, ui/src/main.tsx, ui/src/viewer/Viewer.ts, server/paint_routes.py, server/paint_sessions.py, tools/stage_multi_view_trial.py | stale | - | - |
| S05 | 05-runtime-acceptance.md | Demonstrate both models, persistence and protected baked results | S04 | planning:planning-core, python:python-core, powershell:powershell-core | docs/plans/multi-view-paint/05-runtime-acceptance.md, scratch/lanes/fibo2 | stale | - | - |
| S06 | 06-full-set-contract.md | Own complete-set layouts, coverage, typed sessions and protected baking | S01, S02, S05 | python:python-core, planning:planning-core | server/paint_contracts.py, server/paint_sessions.py, server/paint_routes.py, steps/_paint_set.py, steps/paint_set.py | done | - | 06-full-set-contract.md#result |
| S07 | 07-isolated-provisioning.md | Provision pinned isolated SyncMVD runtime and models | S06 | python:python-core, planning:planning-core | tools/provision_syncmvd.py, requirements-syncmvd.in, requirements-syncmvd.lock, docs/adr | done | - | 07-isolated-provisioning.md#result |
| S08 | 08-whole-sheet-models.md | Run FIBO, Genesis and MOSS whole sheets and MOSS references | S06, S07 | python:python-core, planning:planning-core | steps/paint_generate.py, steps/reference.py, server/reference_models.py, server/jobs.py, server/presets.py, tools/native_reference_entry.py, tools/stage_multi_view_trial.py | done | - | 08-whole-sheet-models.md#result |
| S09 | 09-synchronized-paint.md | Synchronize view predictions through protected shared texture denoising | S07, S08 | python:python-core, planning:planning-core | steps/sync_paint.py, steps/_sync_renderer.py, steps/_sync_scheduler.py, server/sync_models.py, server/jobs.py, server/presets.py, tools/stage_multi_view_trial.py, licenses/SyncMVD.txt | done | - | 09-synchronized-paint.md#result |
| S10 | 10-comparison-ui.md | Expose complete-set generation, comparison and reviewed Apply | S08, S09 | python:python-core, planning:planning-core | ui/src/MultiViewPaint.tsx, ui/src/multi-view-api.ts, ui/src/multi-view-paint.css, ui/src/Compare.tsx, tools/stage_multi_view_trial.py | done | - | 10-comparison-ui.md#result |
| S11 | 11-runtime-comparison.md | Compare four methods and prove preservation and lifecycle | S10 | python:python-core, planning:planning-core | docs/plans/multi-view-paint/11-runtime-comparison.md, scratch/lanes/fibo2 | done | - | 11-runtime-comparison.md#result |

S11 page acceptance is completed in ../painting-completion/04-workflow-acceptance.md#result; historical results remain intact.

## Reading rule

Read index, own spoke and named dependency RESULTs. Preserve prior RESULTs and usage history. Stage bounded changed files only; never rerun provisioning to refresh the lane.

## Non-goals

Primary promotion, MV-Adapter/Hunyuan/model substitutions, native FP4 optimization, multi-material/skinned meshes, unwrap/remesh, atlas enlargement, training and per-step image archives.

## Open questions

(none)

