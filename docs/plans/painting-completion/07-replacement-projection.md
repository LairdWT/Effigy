# Replace painted detail instead of adding residual ghosts

Spoke: S07
Outcome: Remove residual detail and duplicate feathering; compare saved-image rebakes
Depends-on: S06
Decisions: D1, D3, D4, D5, D6
Constraints: C1, C2, C3, C4
Skills: python:python-core, web:typescript-core, art:texture-painting-core
Read-set: docs/plans/painting-completion/INDEX.md, docs/plans/painting-completion/06-mask-projection.md#result, steps/_paint_projection.py, steps/_paint_set.py, steps/paint.py, tools/fibo_trial_worker.py
Write-set: steps/_paint_projection.py, steps/_paint_set.py, steps/paint.py, server/paint_routes.py, ui/src/SurfacePaint.tsx, ui/src/MultiViewPaint.tsx, scratch/lanes/fibo2, docs/plans/painting-completion
State: done

## Context

The owner identifies ghosting and feathered overlap on268. The previous preservation checks correctly established protected pixels, but did not establish coherent paint. This unit fixes confirmed composition mechanisms and derives comparable bakes from existing images, without reopening inference budgets. Expected turns18.

## Evidence

steps/_paint_set.py:377 and steps/paint.py:323 previously added the generated-minus-capture residual to the original atlas. Algebraically this retains original atlas detail that the rendered capture filtered out, even where generated mortar or roof strokes moved. Actual241/v00 analysis on source227 measured mean absolute retained detail7.79 RGB8, maximum140.58, and53282 of153292 supported visible texels above8 RGB8. This is a plausible ghosting contributor, not proof that every observed seam has that cause.

tools/fibo_trial_worker.py:121 feathers the edited image before publication. steps/paint.py:293 then feathered the same repair again. Actual259/260 use8 pixels at both stages;264/265 and267/268 use12 at both stages. Combined bake249 used zero surface feathering, so its inherited seams cannot be blamed on that mask-boundary fade alone. Whole-sheet model panels can still disagree geometrically.

Model lineage: preferred foundation227 came from Genesis224 using Krea2_Genesis-Blackwell-Optimized-nvfp4.safetensors, denoise0.75. Whole-house249 uses MOSS242, BF16 plus Turbo v2, eight steps and denoise0.55 at384 pixels/view. Repairs260/265/268 use FIBO2 Edit Turbo INT8, four steps and blank-region conditioning. Thus268 is a mixed pipeline, not a clean single-model comparison.

## Steps

### Runtime observations

Saved-image rebakes: MOSS242 ->274 (jobb3a4d276d578), FIBO267 ->275 (jobc72a96fa7663), and Genesis224 ->277 (jobd8ea09e45904). No new inference occurred. Source diagnostic276 (job47df8cb58649) changes zero texels. All four decoded outputs retain409 triangles, identical geometry/UVs,1024 RGBA16, alpha and other maps, with zero protected changes.

On37856 changed texels owned byv00, mean deviation from the projected generated RGB fell from9.37529 RGB8 in249 to0.00092 in274; maximum deviation fell from140.57977 to0.00195. This confirms removal of the additive old-detail term. Repair275 records preview feather12 and effective projection feather0 despite the historical request of12. The old267 image still contains its original single edge blend.

Visual review of274/275/277: direct replacement removes the extra original-detail overlay, but MOSS paint is softer and panel/material mismatches remain, including roof-direction changes and architecture details. The foundation repair alone does not remove inherited ghosting elsewhere in268. Genesis227 remains the owner's retained preference;277 is a derived comparison, not a replacement. The proposed automatic finishing loop is S08 and remains unimplemented.

1. Project generated RGB directly through the same-face sampler. Preserve original atlas texels where every participating captured pixel is unchanged, retaining exact source-only identity without adding original detail beneath changed paint.
2. Remove the second projection feather when a masked preview already contains an edge blend. Default new UI recipes to zero optional edge blend; preserve explicit saved recipe values. Record effective and requested feather plus transfer version in output metrics.
3. Stage only changed files to8380. Rebuild the UI offline; restart only idle trial if its API schema changes.
4. Rebuild the saved whole-house image and the saved local foundation repair on their exact original parents. Retain originals. Inspect both complete baked orbits and close joins; report softness or remaining disagreement honestly.
5. Confirm source identity,409 triangles, original UVs,1024 RGBA16, alpha, other maps and protected texels. No new inference or model loading.
6. Specify a bounded automatic finishing loop from the assembled mesh, including surface-space seam grouping, full-context cameras, staged repairs, rollback and one final owner review. Do not claim it is implemented by this compositor change.

## Files to touch

- steps/_paint_projection.py
- steps/_paint_set.py
- steps/paint.py
- server/paint_routes.py
- ui/src/SurfacePaint.tsx
- ui/src/MultiViewPaint.tsx
- scratch/lanes/fibo2
- docs/plans/painting-completion

## Verification

1. Scoped Ruff, offline trial UI build and plan validation. Expected: pass without code tests or model hashes.
2. Normal saved-image rebakes and source diagnostic. Expected: exact geometry/UV/alpha/other-map protection; source identity remains exact; no second edge blend on the recorded masked repair.
3. Baked visual comparison. Expected: assess ghosting separately from lower-resolution softness and inconsistent model features. Do not infer universal seam removal from numeric preservation.

## Risks

Direct replacement exposes the actual generated resolution instead of disguising it with original high-frequency texture. It may look softer. Matching view ownership alone cannot align independently invented mortar lines. Historical preview images retain any edge blending already baked into their pixels.

## RESULT

Trial projection now replaces changed RGB instead of adding a residual to original detail. Masked previews receive no second projection feather; new recipes default to zero optional blend. Saved-image rebakes274(MOSS),275(FIBO repair) and277(Genesis) used no inference. Source diagnostic276 changes zero texels. All four retain409 triangles, UVs,1024 RGBA16, alpha, other maps and protected pixels. For37856v00 texels, mean generated-colour deviation fell9.37529->0.00092 RGB8. Repair275 applies preview feather12 once, with projection feather0. Visible panel/material mismatches and MOSS softness remain; no art acceptance is claimed. Ruff, offline trial build and plan checks pass. Trial restarted asPID40760; primaryPID49908 preserved. Original227/268 remain intact. Automatic finishing is specified in S08 and pending implementation.
