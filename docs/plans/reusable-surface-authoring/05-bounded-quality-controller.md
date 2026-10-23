# Automate diagnosis and bounded repairs without automatic art acceptance

Spoke: S05
Outcome: Automate bounded diagnosis and draft retention
Depends-on: S04
Decisions: D1, D2, D3, D4, D5
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, art:texture-painting-core
Read-set: docs/plans/reusable-surface-authoring/INDEX.md, docs/plans/reusable-surface-authoring/04-material-authoring.md#result, server/finish_contracts.py, steps/_finish_plan.py, steps/_finish_cut.py, steps/paint_finish_generate.py
Write-set: server/finish_contracts.py, server/paint_sessions.py, steps/_finish_plan.py, steps/_finish_cut.py, steps/_paint_seams.py, steps/paint_finish.py, steps/paint_finish_generate.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring
State: done

## Context

Reduce oversight through admission, diagnosis and bounded execution. Auto finish may retain drafts; only explicit owner review advances artistic acceptance. Never hide uncontrolled rerolls.

Expected turns: 18. Preserve standing budgets and prior results. Source changes remain uncommitted. Ordinary app outputs are runtime artifacts under C4, not extra evidence packs.

## Evidence

- steps/_finish_plan.py:74 builds a seam graph; :176 enforces final-camera target registration.
- steps/_finish_cut.py:84 calculates image-regression measurements.
- server/finish_contracts.py:136 exposes checkpoint counts, including a legacy accepted count for retained patches.
- ui/src/AutomaticFinish.tsx:181 already states that numeric retention requires visual inspection.

### Runtime corrections, 2026-10-22

Initial plan318 identified45 registered target pairs and28 unreachable pairs. Cancellation011b88145fee and idle restart preserved run319; resume1467a276bb75 completed that run and consumed another reservation. Its appearance was operator-rejected despite numeric retention. Plan333 protected54 declared material-boundary pairs;334 rejected3 undersampled cameras. Both scheduled zero patches. Budget overflow returned409 before allocation. These operations exposed and corrected unpublished-run lookup and material/component-label shadowing.

Later partial-bake inspection found a second cause of missed repairs: current-camera ownership erased the surrounding appearance history. Plan347 found no patch on339. Accumulated writer ownership now preserves unchanged prior surface labels and assigns new labels only to actually changed surface texels. Legacy partial projections reconstruct their labels from immutable parent/current pixels; otherwise unknown source context receives a distinct baseline label, not invented camera provenance. Cyclic/format-incompatible history fails explicitly. New writers are zero in empty gutters. Ordinary rebake349 preserved339's pixels exactly and classified all524097 covered texels. An int16 label-offset overflow in job0b4121c79716 was fixed before successful retry6552cea09972.

Corrected plan348 found2634 candidate pairs,2605 reachable and29 unreachable. FIBO job676cf15cf89a produced350: one numerically retained patch and a visibly cleaner corner in three baked views. Operator preference remains a draft verdict. Plan352's next three patches consumed four calls in job2d26d4bdceb5, including one correction; every attempt was rejected for seam_not_improved. Actual final353 pixels equal350 exactly. Its p00-a1 introduced a mortar break, p01 remained soft, and p02 introduced incompatible sharp blocks at the selected boundary. No source or owner-accepted checkpoint advanced.

Checkpoint timing now distinguishes fresh engine, reused engine and receipt replay. The353 batch recorded214.357s for p00's two attempts including a fresh load, then21.586s and36.777s for the warm p01/p02 attempts. Scope is render-to-review, not whole-asset throughput. Completed and rejected attempts remain reusable evidence and count against S07's exhausted12/12 allowance.

After restart, ordinary finish_apply on rejected353 returned409 unchanged_finish. Session revision stayed6, version count stayed354, source stayed350, and no active job or owner acceptance appeared.

## Steps

1. Classify defects before repair: UV alias/clearance, camera registration/occlusion, insufficient sampling, inconsistent material scale, incompatible view content, filtering/colour mismatch and intentional material edges. A low seam score cannot prove continuity; expose the actual adjoining surface views.

2. Make technical failures deterministic: invalid UVs return to preparation; insufficient samples return to capture; incompatible source ancestry returns to source selection. Do not spend diffusion attempts on those classes. Keep preserved source and best prior draft available.

3. Plan model repairs only for bounded image-content defects. Each footprint crosses the relevant shared surface edge with qualified core samples on both sides, retains full camera context and excludes protected materials. Avoid broad feathering of two unrelated line patterns.

4. Execute a finite owner-authorized batch with one baseline and at most two diagnosed corrections per defect, further bounded by the shared generation budget. Keep a per-material edit count and source lineage. Stop a region after repeated rejection, increasing blur or inconsistent scale; continue independent valid work and report the unresolved region.

5. Rank retained drafts using preservation and calibrated regression measures, then render the baked candidate for visual review. Preserve the least-degraded draft; do not silently publish the last attempt. Metrics never set an owner-accepted flag or invent a visual verdict.

6. Persist submitted job identity, completed patches, actual recipe and rejection cause. Cancel and restart resume only unfinished work. Indeterminate submissions are reconciled rather than automatically repeated. Use reference-only publication once for the reviewed result.

7. Replace ambiguous accepted terminology at the API boundary with technically retained versus owner accepted, preserving old checkpoint readability. Record cause-specific limits instead of claiming a seam-free result from complete coverage.

## Files to touch

- server/finish_contracts.py
- server/paint_sessions.py
- steps/_finish_plan.py
- steps/_finish_cut.py
- steps/_paint_seams.py
- steps/paint_finish.py
- steps/paint_finish_generate.py
- tools/stage_multi_view_trial.py
- docs/plans/reusable-surface-authoring

## Verification

1. Exercise one eligible seam, one intentional material boundary, one sampling failure and one occluded target through normal planning actions. Expect only the eligible image defect to schedule generation.
   Expected: Only eligible image-content defects schedule a model call.

2. Observe a bounded repair batch, cancellation and resume; expect preserved completed work, no duplicate submission and no source/accepted-checkpoint advance.
   Expected: Cancellation/resume preserves completed work and the accepted checkpoint.

3. Inspect before/after baked seams and material-scale views. A numeric improvement with worse visible paint must remain rejectable and must not be labelled accepted.
   Expected: Visible regressions remain rejectable despite lower numeric error.

4. Run scoped Ruff; count all model calls against S07. Do not create a code-test suite or a separate evidence pack.
   Expected: Changed Python passes Ruff; generation accounting stays within the cap.

## Risks

Metrics can misjudge stylization. A finite batch may leave defects; that does not authorize larger repaint regions or an unapproved model change.

## RESULT

Finite, material-bound repairs preserve checkpoints and explicit draft status. Accumulated writer labels fix missed new/old projection boundaries; legacy history remains read-only. FIBO350 improved one inspected corner and remains an operator-preferred draft. The subsequent four-call batch353 rejected every attempt and preserved350 exactly. Warm render-to-review timings were21.586s and36.777s; these are bounded patch observations, not a universal speed claim. Actual350/353 preservation is recorded in S07. All12 qualification submissions are consumed; no further inference is authorized by this batch. Remaining visible defects and UI/owner acceptance stay open. Prior runtime findings and their corrections are preserved above.
