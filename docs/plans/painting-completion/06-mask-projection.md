# Preserve selected triangle edges in camera masks

Spoke: S06
Outcome: Remove UV rounding holes and refresh saved masks explicitly
Depends-on: S04
Decisions: D1, D3, D4
Constraints: C1, C2, C3, C4
Skills: python:python-core, web:typescript-core, art:texture-painting-core
Read-set: docs/plans/painting-completion/INDEX.md, docs/plans/painting-completion/04-workflow-acceptance.md#result, steps/_paint_set.py, steps/_paint_projection.py
Write-set: steps/_paint_set.py, server/paint_contracts.py, server/paint_routes.py, server/paint_sessions.py, ui/src/MultiViewPaint.tsx, ui/src/multi-view-api.ts, scratch/lanes/fibo2, docs/plans/painting-completion, docs/plans/fibo-trial
State: done

## Context

The continuation audit found a remaining mask projection defect. Nearest UV rounding can select an adjacent triangle or empty atlas texel even when the front-most screen pixel belongs to fully selected geometry. This creates false protected holes before inference. Expected turns12. This unit needs no additional model generation and does not reopen comparison budgets.

## Evidence

steps/_paint_set.py:68 projects UV permission using a single rounded atlas sample and exact face equality. Actual capture241 on source227 selects the complete covered atlas. Cameras v00, v08 and v16 lose601,885 and718 positive-facing pixels respectively that have valid same-face bilinear support. A same-face sampler restores these pixels without losing any previously allowed pixels. Another18,9 and5 pixels respectively have no same-face UV texel support and must remain excluded.

Selection job8f65b2b7c227 produced269 using the existing241 captures without copying geometry. Reachable whole-house coverage increased from518588 to519324 of523762 selected texels;4438 remain inaccessible at384 pixels per camera. Source diagnostic1a29c1507204 produced270 with zero changed texels. Foundation selection7cdcc508e96a produced271 from the exact173 face selection and reused186 captures. Coverage increased from92123 to92145 of92255 texels;110 remain unseen. Green diagnostic50a767ff1080 produced272; its eight-angle review shows the foundation and risers selected with wooden treads, walls and roof preserved.

Actual decoded270/272 outputs retain409 triangles, identical geometry/UV accessors,1024x1024 RGBA16, exact alpha and other maps. Source270 changes zero texels. Green272 changes137663 texels including permitted empty gutters, with zero protected changes. A read-only projection of the actual268 partial foundation permission found1076 kernels crossing its selected/unselected boundary; none were admitted and no other face was admitted. The feather-count metric now counts contributed texels only, excluding untouched areas.

After an idle8380 restart, the actual UI showed the old-mask explanation and disabled generation. A normal generate request against historical sessiona3c63ca038d1443b returned409 mask_projection_update before worker allocation. Its existing241 mask and249 preview remain recorded. The UI created an independent capture-reuse session5de7828cf63e424f and submitted Refresh camera masks as jobcee5e960762f; this operation uses the saved UV selection without changing camera images.

UI refresh completed as273. Its decoded UV mask exactly matches241; its capture reference remains241 and its geometry reference remains227, with no owned GLB. Foundation271 likewise exactly matches173's UV mask and reuses186 images. Original sessiona3c63ca038d1443b still retains241,249 and valid candidate242. The UI removes the stale-mask notice and re-enables generation after completion. No model was loaded for these diagnostics. Historical fibo-trial/S04 is now marked stale with explicit links to the replacement multi-view and repair work; its earlier observations remain intact.

## Steps

Use the existing ownership-aware sampler for UV permission. Require every participating same-face texel to be selected; retain the positive-facing threshold and front-most face raster. Record the projection method with new manifests. Keep historical capture masks immutable. Stage only the changed worker into8380. Exercise new all-surface and foundation selections from existing captures, then ordinary green/source diagnostic bakes. Compare geometry, UVs, alpha, other maps and permitted changes; inspect the actual baked outputs.

Expose an explicit Refresh camera masks action for saved sessions using the previous sampler. Refresh retains the exact UV mask and camera images, creates a new selection version and invalidates candidates for further generation without deleting historical outputs. The UI explains this effect. Generation rejects stale sampler masks before allocating a worker. Existing previews and Apply remain readable against their recorded masks.

## Files to touch

- steps/_paint_set.py
- server/paint_contracts.py
- server/paint_routes.py
- server/paint_sessions.py
- ui/src/MultiViewPaint.tsx
- ui/src/multi-view-api.ts
- scratch/lanes/fibo2
- docs/plans/painting-completion
- docs/plans/fibo-trial

## Verification

1. Scoped Ruff, offline trial UI build and plan validation after edits. Expected: pass.
2. Actual saved capture permission counts and new normal selection actions. Expected: full selection recovers supported edge pixels; partial selection admits no mixed selected/unselected same-face kernels.
3. Ordinary source and green diagnostic bakes. Expected: source is pixel-identical; green changes only permitted texels/gutters, retaining geometry, UVs, alpha and other maps.
4. Refresh through the UI after an idle trial restart. Expected: the UV mask and captures remain identical, new projection method is recorded, and old generated outputs are retained.

## Risks

Triangles without atlas support remain inaccessible. This correction does not make independently generated mortar lines agree or remove existing painted seams. Existing candidates retain their original masks and are not silently reinterpreted.

## RESULT

Fixed false UV-edge holes with same-face sampling that requires all contributing texels selected. Whole-house reachable coverage rose518588->519324; foundation92123->92145. Actual partial-mask analysis admitted zero of1076 mixed kernels. Source diagnostic270 changes zero texels. Green272 retains409 triangles,1024 RGBA16, UVs, alpha, other maps and protected areas; its orbit preserves treads/walls/roof. UI Refresh camera masks produced273 with an identical UV mask and reused captures/geometry; no GLB copy. Stale masks reject generation before worker allocation. Original241/242/249 and repaired268 remain intact. Scoped Ruff, offline trial build and plan checks pass. Only8380 was restarted. Existing generated material seams still need art review; this fix does not regenerate historical paint or claim universal continuity.
