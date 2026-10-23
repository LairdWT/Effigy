# Compare Legaia assets in Effigy

Spoke: S03
Outcome: Compare preserved-geometry texture refinement and regenerated meshes for one Legaia building, then Vahn's battle model.
Depends-on: S02
Decisions: D5, D6, D7, D8, D9, D10, D11, D12
Constraints: C1, C2, C3, C4, C5
Skills: planning:planning-core, python:python-core, aep:aep-core
Read-set: INDEX.md, 02-anime-workflow.md#result, CODE.md, N:/Legaia/WIP/town01/meshes/chain018-obj000/, N:/Legaia/WIP/town01/pages-styled/, N:/Legaia/WIP/style/material-library.json, N:/Legaia/Workflows/3DGen/Legaia_StyleViews_Flux1Ghibli.json, D:/AI/3DGen/Legaia/scripts/style_page_tiles.py, D:/AI/3DGen/Temp/HDTextureReview/battle-vahn/, steps/import_model.py, steps/refine.py, steps/trellis2.py, steps/reference.py, server/reference_models.py
Write-set: docs/plans/local-upgrades/, steps/reference.py, server/reference_models.py, server/presets.py, model-bindings.local.json, scratch/legaia/, N:/generated/Effigy/
State: active

## Context

Expected 40 turns; 256-turn circuit breaker, 2250000-token ceiling and 14500000 tokens per active hour. Owner selected two comparison approaches, building first and Vahn battle model second. Use Effigy's installed workflow and separate reviewable asset versions. A good render does not establish game replacement readiness.

## Evidence

- Source anchors: server/reference_models.py:52 registers local candidates; steps/reference.py:121 runs native image operations. scratch/legaia/hut_uv_workflow.py:124 performs the standalone UV revision through the installed provider adapters; its bake/export stages produce the copied hut. No shared engines, models, add-ons or canonical Legaia files changed.
- Hut source: N:/Legaia/WIP/town01/meshes/chain018-obj000/chain018-obj000.glb, 277 triangles. Import abed693a4b43 -> 002_import_model. The separate door has unestablished placement; this comparison retains the open entrance. The inn trial stopped when the owner selected the hut.
- Owner confirmed the inn's FLUX Ghibli + Arcane recipe: N:/Legaia/Workflows/3DGen/Legaia_StyleViews_Flux1Ghibli.json, FLUX.1-dev Q8, Ghibli 0.7 and Arcane 0.35. Prior assembly reused pages-styled plus window edit 0a876b3e3864 / 041_reference. Material 87 is buff masonry; 93/94 are pale wall/windows; 97 is chimney shaft. Reusing another building's large stone tile for the pale wall and the prior roof tile caused the D12 fidelity failures.
- Earlier 4K chain: 063_import_model (35624f12d602), 064_uv (027b3d998536), 065_bake (cb69d3f5993d), 066_sprites (c3b623c6800b), 067_export (81682fb09983). Reopened as rim_elm_hut_painted_export_reopened/002_import_model (683a4ff7c553). Geometry/export checks passed, but owner rejected excessive resolution, wall drift and loss of thatch.
- Regeneration remains rejected: rim_elm_hut_regenerated_painted_comp/003_trellis2, job 4eeabbe43c3a; 006_bake, 007_sprites, 008_export; reopened rim_elm_hut_regeneration_export_reop/002_import_model. The 18046-triangle result has holes, a jagged base and distorted/invented details. Preserve the original-geometry route.
- D12 UV revision used configured Blender 5.2.0 in a private offline process. Installed Zen UV 4.5.2.14 unwrapped explicit roof gores and wall/foundation panels; UVPackmaster 3.1.1 packed on CPU with 16-pixel requested gutters. Exact-position welding supplied adjacency without moving triangles. Provider operations preserved geometry and RetailUV; AtlasUV median/p95/max stretch is 1.000/1.027/1.048 versus retail 1.529/2.486/4.133. Atlas bounds are inside 0..1; 1024 pixel-centre coverage found zero overlaps and zero flipped triangles. The authoring blend retains RetailUV, AtlasUV, MaterialUV and a hidden editable material source.
- Material attempts 386b0de30a04 -> 069_reference and 3af05b26e581 -> 071_reference remained blurred; 98b2703ce4f3 -> 072_reference and 6832fb4280cd -> 073_reference introduced unsuitable shapes. All ran locally through the existing FLUX adapter and remain history. Final roof and pale wall instead use controlled Blender straw/limewashed masonry materials. Windows, vent, steps and masonry reuse derived prior painted assets; foundation/chimney mapping now uses consistent surface scale. The final roof is procedural, not a claimed successful FLUX edit. Its restrained finish and cleaner wall remain subject to owner art review.
- Final 1K chain in legaia_rim_elm_hut_effigy_comparison: 084_import_model (a988f8223122), 085_sprites (5938e571086c), 086_export (114d672fa77c). Reopen ab9ee142c5a3 -> rim_elm_hut_1k_export_reopened/002_import_model: 277 triangles, one material, one texture, no missing images. All eight rendered directions were inspected. Exported geometry matches retail at six decimals; the standalone blend reopens with no missing image dependencies. Normal runtime remains offline; no tests or model hashes ran.
- Vahn remains held after extraction/import. Source N:/Legaia/artifacts/authoring-current/battle/prot-0863.lbin yielded 17 rigid parts, 1426 triangles, eight pages and 14 raw clips. Scratch display uses action 0/frame 0, original battle stance. Import d7542c32dabe -> legaia_vahn_battle_texture_compariso/002_import_model. No further character processing or canonical scene changes occurred.

## Steps

1. Import a hut copy; inspect geometry, materials, scale and views.
2. Paint its original geometry; record UV and atlas conversion separately.
3. Reconstruct from the painted hut render; compare both meshes from multiple angles.
4. Hold Vahn after source import until the hut comparison is reviewed.
5. When resumed, compare both Vahn approaches in his original battle stance. Preserve source pose data and accepted artwork; game-rig compatibility remains unqualified.
6. Export and reopen both branches; retain application identities and limitations here.
7. Revise the hut on a standalone Blender copy: retain source UVs, establish semantic seams, unwrap with Zen UV, pack with UVPackmaster, restore thin pale retail wall courses and directional straw, and bake a 1024 atlas. Inspect actual textured views before selecting a candidate. Do not change the canonical scene or installed add-ons.

## Files to touch

- docs/plans/local-upgrades/
- steps/reference.py
- server/reference_models.py
- server/presets.py
- model-bindings.local.json
- scratch/legaia/
- N:/generated/Effigy/

## Verification

1. Normal Effigy jobs. Expected: separate source, preserved-geometry and regenerated versions with inspectable outputs.
2. Runtime turn-arounds. Expected: clear comparison of forms and textures; visual defects remain explicit acceptance failures.
3. Export/import_model. Expected: inspectable files retain mesh and materials without missing textures.
4. Plan check and changed-file Ruff. Expected: no findings or errors. No code tests, model hashes, downloads or additional audit reports.

## Risks

Retail vertex colours, mirrored UVs, several materials and game-specific battle rigs may need explicit conversion. New geometry can lose recognizable proportions or features. Existing scene-rebuild holds and artwork selection are independent of this trial. Missing complete battle inputs must be reported precisely rather than substituted with a field model or isolated head.

## RESULT

D12 review candidate: legaia_rim_elm_hut_effigy_comparison/084_import_model. One 1024 albedo, one material, unchanged 277 triangles. Zen UV unwrap and UVPackmaster packing ran; median/max atlas stretch improved from 1.529/4.133 to 1.000/1.048. Zero sampled overlaps; source UV retained.

Eight views: 085_sprites. GLB: 086_export/godot/legaia_rim_elm_hut_effigy_comparison.glb. Reopened as rim_elm_hut_1k_export_reopened/002_import_model with no missing textures. Editable packed blend: 086_export/authoring/hut-1k.blend.

Roof and pale wall are controlled Blender materials; other painted details are retained/remapped. FLUX material attempts and earlier projections were rejected. This is a UV/material revision for owner review, not final art acceptance. Wall is cleaner than retail; remaining repetition/art direction stays reviewable. Vahn remains held. All changes uncommitted; no tests, hashes, downloads or shared installation changes.
