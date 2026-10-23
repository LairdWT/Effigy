# Add a direct protected seam-heal workflow

Spoke: S02
Outcome: Connect combined previews to protected full-context seam healing
Depends-on: S01
Decisions: D1, D2, D3, D4
Constraints: C1, C2, C3, C4
Skills: python:python-core, web:typescript-core, art:texture-painting-core
Read-set: docs/plans/painting-completion/INDEX.md, docs/plans/painting-completion/01-plan-reconciliation.md#result, steps/paint.py, steps/_paint_mask.py, ui/src/SurfacePaint.tsx, ui/src/PaintSelection.tsx
Write-set: steps/paint.py, steps/_paint_mask.py, steps/_paint_seams.py, ui/src/SurfacePaint.tsx, ui/src/PaintSelection.tsx, ui/src/MultiViewPaint.tsx, tools/stage_multi_view_trial.py, server/library.py
State: done

## Context

The assembled mesh must supply context across a join before the next masked edit. Whole-sheet regeneration can reproduce inconsistent features. This unit connects existing capture/edit/apply operations and supplies an advisory seam mask. Expected turns20.

## Evidence

steps/paint.py:163 owns single-view capture/apply. steps/_paint_mask.py:96 resolves capture-bound paint permission. ui/src/SurfacePaint.tsx:147 submits full-frame masked image-to-image. ui/src/MultiViewPaint.tsx:395 owns combined preview review. The repaired multi-view sampler is steps/_paint_projection.py:15.

The trial's SurfacePaint copy had FIBO-only labels, disabled four-step controls and FIBO conditioning attached to every model. The canonical component now provides model-specific settings, four-step FIBO controls, Genesis defaults and MOSS wording, with FIBO-only reference/conditioning fields. The trial stages that reusable component instead of retaining a divergent copy. The existing local description action is also allowed in the trial's run route. Empty edited masks now disable Generate after actual canvas coverage is empty.

## Steps

Add a heal capture from the currently reviewed mesh and camera. Persist full image, camera, suggested mask and appearance snapshot in ordinary capture output. Project the prior camera ownership atlas into the current view and identify visible ownership changes with color disagreement, excluding background and back faces. Dilate only inside visible support. Label the result advisory.

Support a capture-bound suggested-mask preset plus existing additive/erasing strokes and face selection. Show exactly the same starting mask in the editor and worker. Empty/missing presets fail clearly. Preserve the whole image as model context and limit denoising/writeback to the reviewed mask. Reuse the repaired ownership-aware residual sampler for single-view apply. Add a direct Heal seams from this view action from the combined preview, preserving camera and shared appearance. Keep source geometry references and history dependency protection.

## Files to touch

- steps/paint.py
- steps/_paint_mask.py
- steps/_paint_seams.py
- ui/src/SurfacePaint.tsx
- ui/src/PaintSelection.tsx
- ui/src/MultiViewPaint.tsx
- tools/stage_multi_view_trial.py
- server/library.py

## Verification

1. Scoped Ruff and offline trial UI build. Expected: pass with no new dependencies.
2. Normal heal capture and editing. Expected: full view retained, green means paint here, brush/face changes match worker permission and source binding.
3. Source identity and protected apply. Expected: no geometry/UV/alpha/map changes and zero writes outside the approved mask/gutters.

## Risks

Ownership boundaries may coincide with legitimate material edges. Suggestions require visible review and edits. Residual transfer may retain old features when generated features move. Repair must be judged on baked views, not the edited image alone.

## RESULT

Implemented and staged on8380: full-context Heal seams capture, editable capture-bound suggestion preset, brush/lasso/face composition, empty-mask disabling, model-specific single-view controls, appearance snapshots and repaired single-view residual projection. UI capture251 from249 suggested279552 pixels; reviewed erasure/addition narrowed the anchor to46556 image pixels. Genesis job8a0655d24d41 and projection93ec831b9d9b produced252/253. Output changed12417 surface texels with zero outside/alpha changes. Actual GLB accessor arrays, UVs, other maps and1024 RGBA16 were compared and equal. Artistic drift failed S03 review; no acceptance claimed. Ruff and offline trial build pass. Primary behavior remains gated by EFFIGY_MULTI_VIEW and PID49908 remains unchanged. Runtime source and UI are uncommitted.
