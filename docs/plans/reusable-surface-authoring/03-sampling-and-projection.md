# Enforce capture sampling and projection correctness before inference

Spoke: S03
Outcome: Enforce sampling and projection admission
Depends-on: S02
Decisions: D1, D2, D3, D4, D5
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, art:texture-painting-core
Read-set: docs/plans/reusable-surface-authoring/INDEX.md, docs/plans/reusable-surface-authoring/02-blender-preparation.md#result, steps/_paint_set.py, steps/_paint_projection.py, steps/_finish_plan.py, server/paint_contracts.py, docs/plans/painting-completion/10-final-camera-registration.md#result
Write-set: server/paint_contracts.py, server/paint_sessions.py, steps/_paint_set.py, steps/_paint_projection.py, steps/_finish_plan.py, steps/_sampling_plan.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring
State: done

## Context

Use texture-painting-core -> texel-budget and multi-view-canvas, plus blender-core -> blender-projection-painting. A view count or overlap percentage is not a quality guarantee. Sampling admission and exact write ownership must use the final camera, final model preprocessing and final atlas.

Expected turns: 20. Preserve standing budgets and prior results. Source changes remain uncommitted. Ordinary app outputs are runtime artifacts under C4, not extra evidence packs.

## Evidence

- steps/_paint_set.py:64 produces camera raster ownership; :70 derives screen permission from selected UV texels.
- steps/_paint_set.py:139 greedily chooses coverage views; :345 combines projected contributions.
- steps/_paint_projection.py:22 samples replacement colour; :31 filters by exact face ownership.
- steps/_finish_plan.py:176 qualifies repair targets against the actual registered camera.

### Projection correction, 2026-10-22

The initial sampling implementation measured both UV-to-camera singular values and exact visible-face ownership, with per-material summaries and an atlas overlay. Detail admission refused undersampled captures before model allocation. Hut315 measured median0.55995 samples/texel; crate010 measured0.55269. The smaller crate011 region passed at3.07697 with no unreachable or undersampled texels. All three fixture captures completed. Hut identity316 preserved every decoded image and geometry/UV array from313; crate marker012 completed.

Subsequent inspection found that adequate capture resolution did not imply adequate bake filtering: the matched hut anchors supplied about4.17 image samples per atlas texel, but the bake read only four bilinear taps. The new bounded midpoint grid integrates each atlas texel's UV-to-camera footprint. Every contributing tap still requires the exact face, permission and opaque source; it never averages competing camera owners. Work exceeding64 million sample sites per view fails explicitly. This is bounded numerical integration, not an exact area integral or a guarantee of sharper art.

CPU rebakes reused unchanged model outputs: FIBO339(ad224c1001a1), MOSS340(fc83dba07760), Genesis341(0c66fa566776); close views342-344 retained the matched camera. FIBO's aliasing reduced; MOSS remained soft and Genesis retained layout drift. Identity345(73951767d4bb) and crate020(fbcd773e4a44) independently decoded to zero pixel changes and identical geometry/UV arrays and other maps. New finishing plans bind the footprint policy; historical plans retain their original projection behavior. Repair350 uses the new filter; its actual protected-pixel proof is recorded in S07.

## Steps

1. Measure the projected UV-to-image footprint per selected texel using the final transform and effective inference dimensions. Record both directional sample ratios, visibility, grazing rejection, camera-boundary margin, useful core and inaccessible texels. Report material-level distributions rather than one whole-asset average.

2. Propose a minimum one native camera sample per atlas texel along both local directions for newly authored cores; calibrate any higher target against the fixtures before claiming sharpness. This is a configurable sampling floor, not a guarantee of generated detail. Keep unknown physical density distinct. Label deliberately low-resolution style studies as previews, not detail-qualified paint.

3. Plan captures against material regions and connected surfaces with one declared world scale. Combine a broad context overview with registered detail views where needed; each edit still receives its complete unchanged camera frame. Use reference images only when the adapter supports them. Never pretend post-generation upscaling restores absent detail.

4. Retain whole-sheet editing where every selected surface meets the sampling policy. If the sheet cannot fit the model budget, report the exact shortfall and offer explicit material/region passes or a preview mode. Do not silently shrink panels, discard cameras, alter the atlas cap or switch models.

5. Build a normal no-inference identity projection and marked ownership diagnostic. Verify camera/mask registration, UV seams, triangle borders, under-eave occlusion and untouched texels. Identity projection must avoid resampling unchanged source content. Keep strict front-most face and facing guards; repair camera planning instead of weakening visibility.

6. Preserve sharp ownership across competing projections. Do not add the old source residual or blur contradictory mortar/strokes together. Separate final write weights, sampler masks, transitions and empty-gutter refresh. For sequential drafts, measure actual changed-predecessor overlap in UV space, including core overlap and fresh surface coverage.

## Files to touch

- server/paint_contracts.py
- server/paint_sessions.py
- steps/_paint_set.py
- steps/_paint_projection.py
- steps/_finish_plan.py
- steps/_sampling_plan.py
- tools/stage_multi_view_trial.py
- docs/plans/reusable-surface-authoring

## Verification

1. Use ordinary capture/preview jobs on the three frozen fixtures. Expect registered masks, explicit unreachable texels and per-material sampling data at the actual generator resolution.
   Expected: Every capture reports registration, sampling and inaccessible selected texels.

2. Replay the retained 384-panel hut sampling parameters without inference. Expect admission to identify the recorded under-resolution problem; a detail plan must meet its declared policy without enlarging the 1024 atlas.
   Expected: The under-resolved configuration is rejected for detail painting; an admitted plan meets its declared floor.

3. Run no-op and marked ownership projection operations; expect exact protected RGB/alpha/maps, no cross-face leakage and no duplicated source detail.
   Expected: Protected values remain exact and marked samples never cross an ineligible face.

4. Run scoped Ruff on changed modules. Structural coverage and preservation results remain separate from artistic acceptance.
   Expected: Changed Python passes Ruff without a visual-acceptance claim.

## Risks

Good geometric sampling cannot make a soft source sharp or constrain a generator's internal feature scale. Transparent surfaces and overlapping UVs remain unsupported by this static unique-atlas contract. Intentional material edges must not be mistaken for projection defects.

## RESULT

Sampling admission and same-face footprint filtering are implemented. Ordinary capture, identity and marked projections preserve the declared geometry/UV and protected-pixel contracts. Dense-anchor rebakes339-341 reused completed generations; identity345 and crate020 had zero decoded changes. FIBO aliasing reduced, while generated softness and layout drift remain model/content limitations. New finishing plans bind the filter without changing historical checkpoints. Prior static checks passed; final scoped validation is recorded with S07. No atlas enlargement, camera substitution or new generation was used for these projection checks. This establishes technical projection behavior, not owner visual acceptance.
