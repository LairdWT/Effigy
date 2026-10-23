# Expose the complete multi-view painting workflow

Spoke: S04
Outcome: Expose the complete multi-view painting workflow
Depends-on: S03
Decisions: D1, D2, D3, D4, D5, D6
Constraints: C1, C2, C3, C4, C5, C6
Skills: web:typescript-core, web:css-core
Read-set: CODE.md, docs/plans/multi-view-paint/INDEX.md, ui/src/MultiViewPaint.tsx, ui/src/multi-view-paint.css, ui/src/multi-view-api.ts, ui/src/main.tsx, ui/src/viewer/Viewer.ts, server/paint_routes.py, server/paint_sessions.py, tools/stage_multi_view_trial.py
Write-set: ui/src/MultiViewPaint.tsx, ui/src/multi-view-paint.css, ui/src/multi-view-api.ts, ui/src/main.tsx, ui/src/viewer/Viewer.ts, server/paint_routes.py, server/paint_sessions.py, tools/stage_multi_view_trial.py
State: stale

## Context

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

1. Add Multi-view paint beside single-view mode, with shared appearance, model-specific controls and a persistent session picker.
2. Expose shared face/brush/lasso selection, Capture view set, Generate selected groups, Build combined preview and Apply texture. Explain every disabled action.
3. Show fixed capture cameras, pair candidates, status and coverage. Support exclusion, targeted regeneration, before/after review and selecting seams for another round.
4. Preserve viewer camera across interactions and job updates. Resume sessions after reload and restart, without generating copies of completed images or GLBs.

## Files to touch

- ui/src/MultiViewPaint.tsx
- ui/src/multi-view-paint.css
- ui/src/multi-view-api.ts
- ui/src/main.tsx
- ui/src/viewer/Viewer.ts
- server/paint_routes.py
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

Trial UI includes saved sessions, shared appearance/mask, model controls, fixed cameras, generation/retry, pair instructions, exclusion, combined preview, projection overlays and Apply. Unsaved descriptions disable generation/publication with an explanation.

Browser operations passed: session/pair selection, clear (`170_paint_set`), triangle 48 (`171_paint_set`), exact foundation restoration (`172_paint_set`), shared overlay (`173_paint_set`), reload without camera reset, combined preview launch and ownership/disagreement overlays on `184_paint_set`. Before-capture mesh picking added then removed roof triangle 257 without creating a session or moving the camera.

Offline UI build passed. Primary UI/backend unchanged. Presentation: trial asset `presentations/multi-view-anchor-review.png`. Apply and active-batch cancellation/resume remain unqualified because both model anchors failed S03. No rejected texture was applied.

