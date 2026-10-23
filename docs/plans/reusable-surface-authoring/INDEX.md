# Build a reusable Blender and Effigy surface-authoring workflow

## Outcome

Deliverable: reusable-surface-authoring-v1, requested 2026-10-22. Workflow: Source/profile -> Blender preparation -> sampling/selection -> authoring -> baked review -> publication. Effigy owns sessions; Blender provides preparation/manual editing. Qualify three distinct assets, not just the hut. Execution authorized 2026-10-22.

## Decisions

- D1 (2026-10-22): Develop the reusable workflow; the hut is a qualification example.
- D2 (2026-10-22): Include Blender tooling. Preserve the earlier architectural UV preference for alignment and 90-degree packing; qualify each provider operation.
- D3 (2026-10-22): Package workflow skills after the process is established.
- D4 (standing owner decisions): Local offline execution, trial 8380 first, primary 8370 unchanged.
- D5 (2026-10-22): 312 is rejected for blur, seams and uneven detail. 313 is a reference comparison; retained Genesis 227 remains preserved.

## Constraints

- C1: Goals and implementation authorized 2026-10-22. Work inline without subagents/per-unit stops; preserve usage. See GOALS.md.
- C2: No tests, hashes, commits/pushes, CI, engine/add-on upgrades, cleanup, evidence packs or storage audits. Shared models/skill projections stay read-only.
- C3: Preserve histories, WIP, primary lane, Blender scenes and foreign GPU work. Configured tools only; new dependencies/scope need a decision.
- C4: Effigy owns source; activate only in 8380. NAS owns assets/sessions; D: runtime/scratch. NAS failure stops publication. Use ordinary outputs and owning RESULT.
- C5: Keep the hut's 1024 RGBA16 cap. Painting preserves the prepared source's geometry/UVs, alpha and other maps. Preparation creates a new revision; it never overwrites the original.
- C6: Automation retains drafts, never accepts art. Preference, technical proof, acceptance and promotion are separate. No silent model/source/mask/scale fallback.

## Requirements

| ID | Observable outcome | Implementation | Verification | State |
|---|---|---|---|---|
| R1 | Explicit source roles, profiles and supported geometry | S01 | S07, S09 | active |
| R2 | Reversible Blender/UV preparation and safe round trip | S02 | S07, S09 | active |
| R3 | Measured sampling, coverage and exact projection | S03 | S07 | active |
| R4 | Consistent materials across generated, brush and donor methods | S04 | S07 | active |
| R5 | Bounded automatic diagnosis/repair and restart recovery | S05 | S07, S09 | active |
| R6 | Usable unified UI with persistent context and reference publication | S06 | S07, S09 | active |
| R7 | Three-asset qualification and evidence-based model ranking | S04, S06 | S07 | active |
| R8 | Maintained local workflow skill and consumer ownership | S08 | S09 | active |
| R9 | Offline/preservation/storage/lifecycle obligations remain intact | S01-S06 | S07, S09 | active |

Carry forward unmet visual/lifecycle requirements from painting-completion. Its S05 cleanup remains separate. Retain prior comparisons and usage; do not rerun them by default.

## Terms

- Prepared source: immutable geometry/UV/material revision admitted for painting.
- Appearance contract: source roles, material identity, feature scale, palette, marks and preservation intent.
- Sampling floor: declared minimum effective camera samples per atlas texel, measured in both surface directions.
- Working draft: a reversible batch intermediate, distinct from owner acceptance.

## Spokes

| ID | File | Outcome | Depends on | Skills | Write set | State | Commit | Result |
|---|---|---|---|---|---|---|---|---|
| S01 | 01-authoring-contract.md | Define source, profile and method contracts | none | aep:aep-core, planning:planning-core, python:python-core | server/authoring_contracts.py, server/paint_sessions.py, docs/plans/reusable-surface-authoring | done | - | 01-authoring-contract.md#result |
| S02 | 02-blender-preparation.md | Integrate reversible Blender and UV preparation | S01 | python:python-core, powershell:powershell-core | server/blender_client.py, server/app.py, server/library.py, steps/uv_context.py, tools/blender_prepare.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring | done | - | 02-blender-preparation.md#result |
| S03 | 03-sampling-and-projection.md | Enforce sampling and projection admission | S02 | python:python-core, art:texture-painting-core | server/paint_contracts.py, server/paint_sessions.py, steps/_paint_set.py, steps/_paint_projection.py, steps/_finish_plan.py, steps/_sampling_plan.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring | done | - | 03-sampling-and-projection.md#result |
| S04 | 04-material-authoring.md | Unify material intent across authoring methods | S03 | python:python-core, art:texture-painting-core, art:art-3d-realtime-core | server/app.py, server/authoring_contracts.py, server/paint_sessions.py, steps/paint_generate.py, steps/reference.py, steps/paint_finish_generate.py, steps/uv_context.py, tools/blender_prepare.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring | done | - | 04-material-authoring.md#result |
| S05 | 05-bounded-quality-controller.md | Automate bounded diagnosis and draft retention | S04 | python:python-core, art:texture-painting-core | server/finish_contracts.py, server/paint_sessions.py, steps/_finish_plan.py, steps/_finish_cut.py, steps/_paint_seams.py, steps/paint_finish.py, steps/paint_finish_generate.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring | done | - | 05-bounded-quality-controller.md#result |
| S06 | 06-unified-workspace.md | Deliver the unified authoring workspace | S05 | web:typescript-core, web:css-core, python:python-core | ui/src/SurfacePaint.tsx, ui/src/MultiViewPaint.tsx, ui/src/AutomaticFinish.tsx, ui/src/multi-view-api.ts, ui/src/AuthoringWorkspace.tsx, server/app.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring | active | - | - |
| S07 | 07-cross-asset-qualification.md | Qualify three assets and rank model variants | S06 | planning:planning-core, python:python-core, powershell:powershell-core, art:texture-painting-core | docs/plans/reusable-surface-authoring | active | - | - |
| S08 | 08-workflow-skills.md | Package qualified workflow skills | S07 | aep:aep-core, planning:planning-core | .codex/skills/effigy-surface-authoring, docs/SURFACE-AUTHORING.md, docs/plans/reusable-surface-authoring | active | - | - |
| S09 | 09-operator-acceptance.md | Verify documented operation and final status | S08 | planning:planning-core, art:texture-painting-core | docs/plans/reusable-surface-authoring | blocked | - | 09-operator-acceptance.md#result |

## Reading rule

Read index, own spoke and dependency RESULTs, then named sources/skills. One executor updates plan and goal state.

Expected turns appear per spoke. Retain prior usage, 256-turn breaker and token ceilings: implementation 2250000; research 1500000; acceptance 1032000 (target 300000); 14500000/active hour. No wall-clock cap. Preserve valid work on exhaustion.

S01 settles proposed contracts before dependent work; use supported ADR tooling. Run static checks once after relevant changes. S07's proposed twelve-submission budget includes implementation samples; execution is owner-authorized.

## Non-goals

Training, new model/LoRA downloads, native FP4 optimization, generic-library rewrites, primary promotion, automatic deletion, game/scene publication, or another unrestricted model campaign. Multi-material, UDIM, assembled-scene and skinned/deformed painting are future capability extensions; existing mesh/animation features remain available unchanged.

## Open questions

- Best method/model: deferred until S07 produces matched baked candidates; resume on visual comparison.
- UV Squares: deferred until a separately approved compatible provider exists; resume on a successful real operation. Other qualified preparation proceeds.
- Broader geometry/scene support: deferred until a separate scope is approved; resume with its source, preservation and acceptance contract.
