# Complete the approved painting workflow and repairs

## Outcome

Complete painting on8380; preserve outputs and qualify baked repairs. Track cleanup and owner acceptance.

## Decisions

- D1 (2026-10-21): Owner authorizes autonomous goal execution without per-unit handoffs.
- D2: Closed comparison budgets stay closed. S03 allowed three preserve-context attempts plus one diagnosed FIBO blank-region sample on the same mask (four total). Later inference remains targeted repair, never a new whole-house comparison.
- D3: Genesis masked editing:1024 context/atlas,409 triangles. Preserve227; repairs start249.
- D4: Suggestions stay editable. Numeric retention is not owner art acceptance; no automatic full repaint.
- D5: Prior exclusions persist: no MOSSArt/KV-cache/nativeFP4 upgrades or downloads; Vahn held until hut review.
- D6 (2026-10-22): Owner rejects268 ghosts; S07/S08 fix projection/finishing and preserve268/227.
- D7 (2026-10-22): S08 and Sol6 Moirai authorized when blocked; cleanup independent, other delegation excluded.
- D8 (2026-10-22): Rejection282 reopens targetedS09 repairs; closed comparisons and cleanup stay separate.
- D9 (2026-10-22): ZenUV/UV Squares/UVPackmaster on a separate copy; align shells and pack with90-degree rotations.

- D10 (2026-10-22): Owner rejects312 blur, seams and uneven detail. Diagnose the base before further generation.

## Constraints

- C1: Offline runtime,8380 activation only, primary8370 and unrelated work preserved. No subagents except D7's Sol6 Moirai roles; no tests, hashes, commits, pushes, CI, broad cleanup or extra evidence packs.
- C2: Borrowed models read-only. Use existing environments and source-owned staging. No engine/dependency changes.
- C3: Preserve geometry, UVs, alpha, other maps, unselected texels and history. Source-only projection must remain an exact identity operation. NAS failure must stop publication.
- C4: Preserve results and usage history, the256-turn breaker and standing ceilings. Spokes own expected turns and runtime records; use ordinary application outputs.

## Requirements

| Requirement | Implementation | Acceptance |
|---|---|---|
| Reconcile stale plan blockers and remaining obligations | S01 | S04 |
| Direct combined-preview to masked-heal workflow | S02 | S03 |
| Full-context mask suggestions and precise add/erase controls | S02 | S03 |
| Baked seam repair with preserved good areas | S02 | S03 |
| UI lifecycle and observed offline behavior | S04 | S04 |
| Shared UV permission without false triangle-edge holes | S06 | S06 |
| Replace generated detail without residual ghosts or repeated edge blends | S07 | S07 |
| Bounded automatic seam finishing with one final review | S08 | S08 |
| Visibly coherent repairs with preserved surrounding paint | S09 | S09 |

## Terms

- Heal capture: immutable full-frame capture of the assembled texture with an optional editable seam suggestion.
- Seam suggestion: advisory mask at camera-owner and colour discontinuities.

## Spokes

| ID | File | Outcome | Depends on | Skills | Write set | State | Commit | Result |
|---|---|---|---|---|---|---|---|---|
| S01 | 01-plan-reconciliation.md | Reconcile completed features and remaining acceptance obligations | none | planning:planning-core | docs/plans | done | - | 01-plan-reconciliation.md#result |
| S02 | 02-seam-healing-workflow.md | Connect combined previews to protected full-context seam healing | S01 | python:python-core, web:typescript-core, art:texture-painting-core | steps/paint.py, steps/_paint_mask.py, steps/_paint_seams.py, ui/src/SurfacePaint.tsx, ui/src/PaintSelection.tsx, ui/src/MultiViewPaint.tsx, tools/stage_multi_view_trial.py, server/library.py | done | - | 02-seam-healing-workflow.md#result |
| S03 | 03-hut-repair.md | Qualify and apply targeted repairs to the assembled hut | S02 | python:python-core, art:texture-painting-core | docs/plans/painting-completion/03-hut-repair.md, scratch/lanes/fibo2, steps/paint.py, steps/_paint_seams.py, steps/reference.py, tools/fibo_trial_worker.py, tools/stage_multi_view_trial.py, ui/src/SurfacePaint.tsx | done | - | 03-hut-repair.md#result |
| S04 | 04-workflow-acceptance.md | Close browser lifecycle and remaining runtime acceptance | S03 | planning:planning-core, python:python-core, web:typescript-core | docs/plans, scratch/lanes/fibo2, ui/src/LocalRuntimeStatus.tsx, ui/src/events.ts, ui/src/MultiViewPaint.tsx, ui/src/PaintSelection.tsx, tools/stage_multi_view_trial.py | done | - | 04-workflow-acceptance.md#result |
| S05 | 05-authorized-cleanup.md | Remove only the96 previously authorized superseded hut versions | S01 | powershell:powershell-core | N:/generated/Effigy/_trash | blocked | - | 05-authorized-cleanup.md#result |
| S06 | 06-mask-projection.md | Remove UV rounding holes and refresh saved masks explicitly | S04 | python:python-core, web:typescript-core, art:texture-painting-core | steps/_paint_set.py, server/paint_contracts.py, server/paint_routes.py, server/paint_sessions.py, ui/src/MultiViewPaint.tsx, ui/src/multi-view-api.ts, scratch/lanes/fibo2, docs/plans/painting-completion, docs/plans/fibo-trial | done | - | 06-mask-projection.md#result |
| S07 | 07-replacement-projection.md | Remove residual detail and duplicate feathering; compare saved-image rebakes | S06 | python:python-core, web:typescript-core, art:texture-painting-core | steps/_paint_projection.py, steps/_paint_set.py, steps/paint.py, server/paint_routes.py, ui/src/SurfacePaint.tsx, ui/src/MultiViewPaint.tsx, scratch/lanes/fibo2, docs/plans/painting-completion | done | - | 07-replacement-projection.md#result |
| S08 | 08-automatic-finishing.md | Automate seam planning, bounded repair and one final draft review | S07 | python:python-core, powershell:powershell-core, web:typescript-core, planning:planning-core, art:texture-painting-core, art:art-3d-realtime-core | server/finish_contracts.py, server/paint_sessions.py, server/paint_routes.py, server/jobs.py, server/presets.py, server/library.py, steps/_paint_seams.py, steps/_finish_plan.py, steps/_finish_cut.py, steps/paint_finish.py, steps/paint_finish_generate.py, steps/paint_generate.py, tools/native_reference_entry.py, tools/stage_multi_view_trial.py, ui/src/AutomaticFinish.tsx, ui/src/MultiViewPaint.tsx, ui/src/multi-view-api.ts, scratch/lanes/fibo2, docs/plans/painting-completion | done | - | 08-automatic-finishing.md#result |
| S09 | 09-source-locked-repairs.md | Repair remaining visible joins after UV verification | S08 | python:python-core, powershell:powershell-core, art:texture-painting-core, web:typescript-core | server/finish_contracts.py, server/jobs.py, server/library.py, steps/paint_generate.py, steps/_finish_plan.py, steps/paint_finish_generate.py, steps/uv_context.py, steps/_uv_transfer.py, steps/repair_baseline.py, tools/stage_multi_view_trial.py, tools/native_reference_entry.py, ui/src/AutomaticFinish.tsx, ui/src/multi-view-api.ts, scratch/legaia, scratch/lanes/fibo2, docs/plans/painting-completion | active | - | 312 rejected; S11 |

| S10 | 10-final-camera-registration.md | Close final-camera repair coverage gaps without weakening occlusion guards | S09 | python:python-core, art:texture-painting-core | steps/_finish_plan.py, steps/paint_finish_generate.py, scratch/lanes/fibo2, docs/plans/painting-completion | done | - | 312; registered |

| S11 | 11-material-base-quality.md | Diagnose blur and compare a sharper source on the aligned mesh | S10 | python:python-core, art:texture-painting-core | steps/uv_context.py, scratch/lanes/fibo2, docs/plans/painting-completion | done | - | 313; reference |

## Reading rule

S11 owns the rejected312 base diagnosis; S09/S10 retain repair and registration evidence. Judge baked output.

Read this index, the owning spoke and dependency RESULTs. Preserve historical observations.

## Non-goals

Primary promotion, Vahn work before hut acceptance, nativeFP4 optimization, replacing models, training, remeshing, UV changes outside the D9 authoring copy, atlas enlargement and restarting closed model-comparison campaigns.

## Open questions

Deferred: cleanup. Reason: execution review blocks it. Resume trigger: policy change or owner removal; see S05.
