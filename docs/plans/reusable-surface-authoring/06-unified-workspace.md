# Expose the complete authoring workflow in one Effigy workspace

Spoke: S06
Outcome: Deliver the unified authoring workspace
Depends-on: S05
Decisions: D1, D2, D3, D4, D5
Constraints: C1, C2, C3, C4, C5, C6
Skills: web:typescript-core, web:css-core, python:python-core
Read-set: docs/plans/reusable-surface-authoring/INDEX.md, docs/plans/reusable-surface-authoring/05-bounded-quality-controller.md#result, ui/src/SurfacePaint.tsx, ui/src/MultiViewPaint.tsx, ui/src/AutomaticFinish.tsx, ui/src/multi-view-api.ts, server/app.py
Write-set: ui/src/SurfacePaint.tsx, ui/src/MultiViewPaint.tsx, ui/src/AutomaticFinish.tsx, ui/src/multi-view-api.ts, ui/src/AuthoringWorkspace.tsx, server/app.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring
State: active

## Context

Effigy is the visible workflow home. Blender is a named preparation/manual-edit tool, not a second hidden session owner. Reuse the current viewer, selection and job infrastructure instead of building a separate asset application.

Expected turns: 20. Preserve standing budgets and prior results. Source changes remain uncommitted. Ordinary app outputs are runtime artifacts under C4, not extra evidence packs.

## Evidence

- ui/src/SurfacePaint.tsx:62 provides single-view painting; ui/src/MultiViewPaint.tsx:16 provides session controls.
- ui/src/MultiViewPaint.tsx:305 restores a recorded projection camera explicitly.
- ui/src/AutomaticFinish.tsx:124 carries the appearance recipe into another pass.
- server/app.py:294 and server/app.py:312 expose the existing Blender round trip.

### Session-state correction, 2026-10-22

Source review found that AuthoringWorkspace retained its inspection/job/review state when the selected paint session changed, because only its profile was reset. The parent also did not know preparation was busy. The workspace is now keyed by asset/session; its local operation state locks painting-session changes until completion or cancellation. A status message explains that lock. The parent does not feed the child's busy flag back into its own activity calculation.

Preparation polling previously set running=false after any request error. It now keeps the same job active and retries, requiring a recognized terminal state before unlocking. Unknown status values also retain the active handle. These are source-proven fixes; browser interaction remains unverified. The offline trial build passes and serves index-DIDuJEFk.js. No model calls, dependencies or primary-lane builds were used.

## Steps

1. Add clear stages: Source and profile -> Prepare/inspect -> Select and capture -> Author -> Review -> Publish. Display original, current draft, preferred reference and owner-accepted checkpoint distinctly. The source mesh remains visible while operating on image candidates.

2. Expose Blender Inspect, Open working copy and Pull saved changes with source/scene identity and resulting invalidation. Show actual provider availability; disable UV Squares with its concrete runtime limitation rather than implying an installed add-on works.

3. Show sampling/coverage on the mesh, intended feature scale and the exact model input sheet/frame. Separate low-resolution preview from detail-qualified capture. Explain why Generate is disabled and which stage resolves it. Green remains paint here.

4. Retain descriptions, material regions, camera, selection and working recipe across angle changes, jobs and restarts. Keep captured projection cameras independent of the user's viewing camera. Face/brush/lasso selection updates the same UV permission.

5. Offer generated edit, registered-source reconstruction and Blender brush painting as clearly labelled methods. Show only applicable controls. An ordinary reference image is never presented as geometry-preserving paint; Use as reference remains a capability-specific action.

6. Provide before/after at matched camera and display scale, full-resolution local inspection, 360, seam/ownership/sampling overlays and candidate provenance. Show per-task model comparisons without a misleading universal best badge. Publish draft and Accept appearance are separate actions.

7. Expose bounded automatic finishing with defect reasons, budget, retained/rejected results and resumable progress. Store source geometry/captures once and reference them from groups. Preserve dependency-aware deletion and historical versions; this plan performs no cleanup.

8. Stage only the explicit changed files and build the trial UI offline. Keep port 8370 source activation and served assets unchanged. Restart only the idle trial backend when authorized execution requires the new API.

## Files to touch

- ui/src/SurfacePaint.tsx
- ui/src/MultiViewPaint.tsx
- ui/src/AutomaticFinish.tsx
- ui/src/multi-view-api.ts
- ui/src/AuthoringWorkspace.tsx
- server/app.py
- tools/stage_multi_view_trial.py
- docs/plans/reusable-surface-authoring

## Verification

1. Use the real browser to complete preparation, selection, capture, authoring, review and reference-only Apply. Confirm camera and descriptions survive each action and explanatory text is visible for disabled controls.
   Expected: The visible workflow completes with stable camera/description state and explained disabled controls.

2. Reopen a saved session and switch between a draft, preferred reference and accepted checkpoint; verify state labels and dependency protection match persisted backend state.
   Expected: UI labels match backend state and retained dependencies remain protected.

3. Run `npm --offline --prefix scratch/lanes/fibo2/ui run build` after relevant UI edits, scoped Ruff for backend changes and the bounded staging check. Never rebuild or redeploy the primary lane.
   Expected: The offline trial build and scoped Ruff pass; primary assets are unchanged.

4. Browser/API unavailability leaves the corresponding UI acceptance item incomplete; API samples cannot substitute for interaction proof.
   Expected: Any unavailable browser interaction remains an incomplete UI requirement.

## Risks

A staged interface can still hide engine-specific limits. Keep those limits visible next to the affected control. Do not create new global viewer state that resets the camera when session polling updates the component.

## RESULT

The shared authoring workspace exposes contracts, preparation, sampling, methods and review. Session changes now reset inspection state; active preparation blocks session switching. Polling failures retain the job until a confirmed terminal state. Region drafts and finite finishing contracts persist; duplicate Apply/Publish resolves existing019,006,226/308 without new jobs or versions. Trial TypeScript/Vite build passes; served bundle index-DIDuJEFk.js. Primary8370 remains unchanged. Browser control still refuses access despite owner enablement, so interactive camera stability, lifecycle and visible control behavior remain incomplete. Source/build proof is not UI acceptance.
