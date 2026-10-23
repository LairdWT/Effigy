# Register repair targets in the final camera

Spoke: S10
Outcome: Close final-camera repair coverage gaps without weakening occlusion guards
Depends-on: S09
Decisions: D8, D9
Constraints: C1, C2, C3, C4
Skills: python:python-core, art:texture-painting-core
Read-set: docs/plans/painting-completion/INDEX.md, docs/plans/painting-completion/09-source-locked-repairs.md#result, steps/_finish_plan.py, steps/paint_finish_generate.py
Write-set: steps/_finish_plan.py, steps/paint_finish_generate.py, scratch/lanes/fibo2, docs/plans/painting-completion
State: done

## Context

S09 improved the hut and preserved its geometry, but several targeted seam endpoints remained unchanged. Investigate actual projection eligibility before spending another model sample. Expected turns12; existing circuit breakers and usage history remain. This continues approved targeted repairs, with no new model campaign or shared runtime changes.

## Evidence

steps/_finish_plan.py:272 reframes a chosen survey camera, then retains seam membership chosen before reframing. patch_masks silently drops unpaintable seeds. Projecting actual306 masks through recorded305 cameras finds44 unpaintable p00 target texels:21 fail exact visibility and23 fall outside the cut; all44 were visible in the original survey camera. For p02,7 target texels are unpaintable:1 fails visibility,6 fall outside the cut and3 lack eligible samples; all7 were visible before reframing. Categories may overlap. No endpoint fails the positive-facing threshold.

These observations establish a mismatch between planned targets and final-frame permission. They do not prove every remaining visible line has that cause.

## Steps

1. Qualify every proposed target pair using the actual final camera, core mask, opaque pixels and existing same-face projection sampler.
2. Keep only pairs with both endpoints projectable. Leave rejected pairs available to other cameras; do not discard them globally merely because one camera fails.
3. Recompute the mask after membership changes and guard the final registered targets. Retain connected-mask, graph-size and framing checks.
4. Record the registration policy and rejected-pair counts in ordinary plan metrics. Old plans retain their recorded behavior.
5. Before inference and after the hard cut, require full permission for registered targets. Preserve strict front-most ownership, grazing/occlusion rejection, alpha and authoritative UV selection.
6. Run one bounded three-patch Genesis repair from308. Inspect marker coverage before inference and actual baked neighbouring views afterward. Do not widen masks or relax guards to obtain a pass.

## Files to touch

- steps/_finish_plan.py
- steps/paint_finish_generate.py
- scratch/lanes/fibo2
- docs/plans/painting-completion

## Verification

1. Scoped Ruff and AEP plan validation. Expected: pass; no tests or hashes.
2. Normal planning job and actual marker projection. Expected: both endpoints of every retained target pair are permitted in the final camera; omitted pairs remain explicitly unresolved.
3. Normal generation, baked review and reference-only Apply. Expected:409 triangles, unchanged geometry/UVs,1024RGBA16, exact alpha/other maps, zero changes outside permission and improved local continuity.
4. Observe worker completion and primary8370. Expected: clean owned-worker exit and unchanged primary lane.

### Current runtime evidence

Planning job156b2509e1fc published309 for sessionc58498b569a144e7 from308. The final-frame marker has zero outside/alpha changes and210 registered target pairs (105/59/46), with zero unpaintable target pairs in all three cores.26 camera assignments were rejected; those pairs were not globally discarded. The plan records core_owned_endpoints_v1. Generation job4ef4e557ab53 is the bounded actual-work qualification. The same guard runs before loading a model and after the hard cut; no visibility or permission rule was relaxed.

Job4ef4e557ab53 completed310/311 with two retained repairs, one rejected repair and one correction. All four attempts report zero unpaintable registered pairs after the actual cut. Retained seam errors fell46.6071->26.7632 and75.3463->21.6551 RGB8. The rejected region worsened62.695->74.256/73.2554 and remained unchanged. Both the close baked views and complete360 were inspected.

Independent decoded-output comparison of310 against308 confirms409 triangles, identical geometry/UV accessors and other material maps,1024x1024x4 uint16, exact alpha and zero changes outside permission.7363 texels changed, including1379 gutters. UI review and Apply published312 by reference to310. The new result was explicitly opened in a visible in-app browser tab at the owner's request. No new inference was started after that review request. Scoped Ruff and plan validation pass; the unchanged UI retains its prior offline build.

## Risks

Strict registration may find fewer qualified patches. Report that limitation rather than painting occluded or unselected surfaces. Fully registered pairs can still contain incompatible generated features; numeric coverage cannot establish art quality.

## RESULT

Final-camera registration is implemented and exercised. Plan309 admits210 pairs only after exact projected-core qualification;26 rejected camera assignments remain available elsewhere. All four generated attempts cover both endpoints of every recorded target. Draft310 retains two improvements and rejects one regression. Independent output reads confirm409 triangles, unchanged geometry/UVs/maps,1024RGBA16, exact alpha and zero outside changes. UI Apply312 references310 without duplicating its GLB;312 is open for owner review. Ruff/plan checks pass, no tests/hashes/commits. This closes the registration defect for newly recorded targets, not overall artistic acceptance. S09 quality review and the independent S05 cleanup blocker remain open.
