# Reusable surface authoring goals

Owner authorized creation and implementation on 2026-10-22. These are portable local goal contracts, not COSMOS WorkState registrations or additional native app goals. The native create operation refused because this chat's existing goal is unfinished and blocked; no completion or resume was fabricated.

Parent outcome: implement and qualify INDEX.md requirements R1-R9. The native goal remains linked to this chat; the portable contracts below track the authorized work while that API limitation persists.

The owner resumed the native goal on 2026-10-22. These spoke contracts remain linked to its full objective; the native goal tool owns current runtime status.

## goal:effigy-authoring-s01

Goal: Define source, profile and method contracts.
Purpose: implementation
State: done
Depends-on: none
CoversGoals: -
Evidence: [01-authoring-contract.md](01-authoring-contract.md) Verification and RESULT; ordinary application outputs.
Constraints: INDEX.md C1-C6, no tests/hashes, trial 8380 only, preserve historical and foreign work.
Scope: server/authoring_contracts.py, server/paint_sessions.py, docs/plans/reusable-surface-authoring; ordinary application artifacts under C4.
Iteration: Inspect current evidence, perform the next bounded step, record the outcome in the owning RESULT, continue within the approved scope.
Stop: Complete only when the spoke evidence proves its outcome; retain incomplete requirements on exhausted budget, missing capability or failed acceptance. No automatic artistic acceptance.
Result Record: 01-authoring-contract.md#result; source contracts and frozen fixtures complete, scoped Ruff passed.

## goal:effigy-authoring-s02

Goal: Integrate reversible Blender and UV preparation.
Purpose: implementation
State: done
Depends-on: S01
CoversGoals: -
Evidence: [02-blender-preparation.md](02-blender-preparation.md) Verification and RESULT; ordinary application outputs.
Constraints: INDEX.md C1-C6, no tests/hashes, trial 8380 only, preserve historical and foreign work.
Scope: server/blender_client.py, server/app.py, steps/uv_context.py, tools/blender_prepare.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring; ordinary application artifacts under C4.
Iteration: Inspect current evidence, perform the next bounded step, record the outcome in the owning RESULT, continue within the approved scope.
Stop: Complete only when the spoke evidence proves its outcome; retain incomplete requirements on exhausted budget, missing capability or failed acceptance. No automatic artistic acceptance.
Result Record: 02-blender-preparation.md#result; provider operations, transfer and round trip exercised.

## goal:effigy-authoring-s03

Goal: Enforce sampling and projection admission.
Purpose: implementation
State: done
Depends-on: S02
CoversGoals: -
Evidence: [03-sampling-and-projection.md](03-sampling-and-projection.md) Verification and RESULT; ordinary application outputs.
Constraints: INDEX.md C1-C6, no tests/hashes, trial 8380 only, preserve historical and foreign work.
Scope: server/paint_contracts.py, steps/_paint_set.py, steps/_paint_projection.py, steps/_finish_plan.py, steps/_sampling_plan.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring; ordinary application artifacts under C4.
Iteration: Inspect current evidence, perform the next bounded step, record the outcome in the owning RESULT, continue within the approved scope.
Stop: Complete only when the spoke evidence proves its outcome; retain incomplete requirements on exhausted budget, missing capability or failed acceptance. No automatic artistic acceptance.
Result Record: 03-sampling-and-projection.md#result; captures, detail rejection/admission and identity projection exercised.

## goal:effigy-authoring-s04

Goal: Unify material intent across authoring methods.
Purpose: implementation
State: done
Depends-on: S03
CoversGoals: -
Evidence: [04-material-authoring.md](04-material-authoring.md) Verification and RESULT; ordinary application outputs.
Constraints: INDEX.md C1-C6, no tests/hashes, trial 8380 only, preserve historical and foreign work.
Scope: server/authoring_contracts.py, server/paint_sessions.py, steps/paint_generate.py, steps/paint_finish_generate.py, steps/uv_context.py, tools/blender_prepare.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring; ordinary application artifacts under C4.
Iteration: Inspect current evidence, perform the next bounded step, record the outcome in the owning RESULT, continue within the approved scope.
Stop: Complete only when the spoke evidence proves its outcome; retain incomplete requirements on exhausted budget, missing capability or failed acceptance. No automatic artistic acceptance.
Result Record: 04-material-authoring.md#result; three method samples and preservation verified; visual quality remains S07.

## goal:effigy-authoring-s05

Goal: Automate bounded diagnosis and draft retention.
Purpose: implementation
State: done
Depends-on: S04
CoversGoals: -
Evidence: [05-bounded-quality-controller.md](05-bounded-quality-controller.md) Verification and RESULT; ordinary application outputs.
Constraints: INDEX.md C1-C6, no tests/hashes, trial 8380 only, preserve historical and foreign work.
Scope: server/finish_contracts.py, server/paint_sessions.py, steps/_finish_plan.py, steps/_finish_cut.py, steps/paint_finish_generate.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring; ordinary application artifacts under C4.
Iteration: Inspect current evidence, perform the next bounded step, record the outcome in the owning RESULT, continue within the approved scope.
Stop: Complete only when the spoke evidence proves its outcome; retain incomplete requirements on exhausted budget, missing capability or failed acceptance. No automatic artistic acceptance.
Result Record: 05-bounded-quality-controller.md#result; bounded API repair/recovery and negative guards verified; art was rejected.

## goal:effigy-authoring-s06

Goal: Deliver the unified authoring workspace.
Purpose: implementation
State: active
Depends-on: S05
CoversGoals: -
Evidence: [06-unified-workspace.md](06-unified-workspace.md) Verification and RESULT; ordinary application outputs.
Constraints: INDEX.md C1-C6, no tests/hashes, trial 8380 only, preserve historical and foreign work.
Scope: ui/src/SurfacePaint.tsx, ui/src/MultiViewPaint.tsx, ui/src/AutomaticFinish.tsx, ui/src/multi-view-api.ts, ui/src/AuthoringWorkspace.tsx, server/app.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring; ordinary application artifacts under C4.
Iteration: Inspect current evidence, perform the next bounded step, record the outcome in the owning RESULT, continue within the approved scope.
Stop: Complete only when the spoke evidence proves its outcome; retain incomplete requirements on exhausted budget, missing capability or failed acceptance. No automatic artistic acceptance.
Result Record: -

## goal:effigy-authoring-s07

Goal: Qualify three assets and rank model variants.
Purpose: verification
State: active
Depends-on: S06
CoversGoals: S01, S02, S03, S04, S05, S06
Evidence: [07-cross-asset-qualification.md](07-cross-asset-qualification.md) Verification and RESULT; ordinary application outputs.
Constraints: INDEX.md C1-C6, no tests/hashes, trial 8380 only, preserve historical and foreign work.
Scope: docs/plans/reusable-surface-authoring; ordinary application artifacts under C4.
Iteration: Inspect current evidence, perform the next bounded step, record the outcome in the owning RESULT, continue within the approved scope.
Stop: Complete only when the spoke evidence proves its outcome; retain incomplete requirements on exhausted budget, missing capability or failed acceptance. No automatic artistic acceptance.
Result Record: -

## goal:effigy-authoring-s08

Goal: Package qualified workflow skills.
Purpose: implementation
State: active
Depends-on: S07
CoversGoals: -
Evidence: [08-workflow-skills.md](08-workflow-skills.md) Verification and RESULT; ordinary application outputs.
Constraints: INDEX.md C1-C6, no tests/hashes, trial 8380 only, preserve historical and foreign work.
Scope: .codex/skills/effigy-surface-authoring, docs/SURFACE-AUTHORING.md, docs/plans/reusable-surface-authoring; ordinary application artifacts under C4.
Iteration: Inspect current evidence, perform the next bounded step, record the outcome in the owning RESULT, continue within the approved scope.
Stop: Complete only when the spoke evidence proves its outcome; retain incomplete requirements on exhausted budget, missing capability or failed acceptance. No automatic artistic acceptance.
Result Record: -

## goal:effigy-authoring-s09

Goal: Verify documented operation and final status.
Purpose: verification
State: blocked
Depends-on: S08
CoversGoals: S08
Evidence: [09-operator-acceptance.md](09-operator-acceptance.md) Verification and RESULT; ordinary application outputs.
Constraints: INDEX.md C1-C6, no tests/hashes, trial 8380 only, preserve historical and foreign work.
Scope: docs/plans/reusable-surface-authoring; ordinary application artifacts under C4.
Iteration: Inspect current evidence, perform the next bounded step, record the outcome in the owning RESULT, continue within the approved scope.
Stop: Complete only when the spoke evidence proves its outcome; retain incomplete requirements on exhausted budget, missing capability or failed acceptance. No automatic artistic acceptance.
Result Record: 09-operator-acceptance.md#result; connector unavailable, qualification allowance exhausted, UI and owner acceptance remain incomplete.
