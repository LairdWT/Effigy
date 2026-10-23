# Repack the owner's edited hut

Spoke: S04
Outcome: Unwrap the owner's edited hut, repack at 1024 and create a separate texture iteration in Effigy.
Depends-on: S03
Decisions: D12, D13
Constraints: C1, C2, C3, C5
Skills: planning:planning-core, python:python-core, aep:aep-core
Read-set: INDEX.md, 03-legaia-assets.md#result, CODE.md, scratch/legaia/hut_uv_workflow.py, steps/refine.py, N:/generated/Effigy/legaia_rim_elm_hut_effigy_comparison/086_export/authoring/hut-1k.blend
Write-set: docs/plans/local-upgrades/, scratch/legaia/, N:/generated/Effigy/
State: done

## Context

Expected 35 turns; 256-turn breaker and 2250000-token ceiling. The owner saved the edited hut after source confirmation. Work from a private snapshot, preserve the live Blender session and owner file, keep the 1024 texture budget, and hold Vahn. Texture changes remain separately reviewable.

## Evidence

- scratch/legaia/hut_uv_workflow.py:124 owns the prior native UV adapter use. Existing Blender, Zen UV and UVPackmaster are reused without installation or preference changes.
- The saved visible `Rim Elm hut - UV revision` has added geometry. Its hidden `Editable material source - hidden` still has 277 polygons and is a reference only. The visible mesh retains one baked albedo and RetailUV, AtlasUV and MaterialUV.
- The hut editing process is separate from the unrelated Rim Elm MCP listener on 9877. No operation targets that listener.
- steps/refine.py:1 accepts a textured UV-mapped GLB, retains its geometry/UVs, and supports texture_size `keep`.
- Confirmed snapshot: scratch/legaia/hut-owner-edit-01/owner-source.blend, copied from the owner's saved 086_export/authoring/hut-1k.blend (35033179 bytes; modified 2026-10-20 15:55:58 local). The visible mesh has 216 vertices and 409 triangles; the hidden reference remains 277 triangles. Source file and live session were not overwritten.
- scratch/legaia/reunwrap_hut_edit.py implements this iteration using the prior provider adapter. Zen UV unwrapped 409 faces; seven additional hard/boundary seams were marked. UVPackmaster packed a new AtlasUV_Edit01 at 1024 with requested 16-pixel gutters. All three pre-existing UV layers and triangle positions were preserved. Median/p95/max stretch: 1.000/1.053/1.131. The prior AtlasUV had 64 zero-area faces; the new layer has zero, no flipped triangles and no overlapping pixel centres at 1024.
- The initial appearance transfer preserved invalid inherited colouring on added stair/trim surfaces. A bounded material repair assigned consistent stone to 54 foundation/riser faces and wood to 56 collapsed window/vent faces. RepairMaterialUV is separate; no owner geometry moved. The saved blend includes a hidden 409-face `Owner geometry - editable texture source`; the old object is explicitly named `Previous 277-triangle material reference`.
- Ordinary application versions in legaia_rim_elm_hut_effigy_comparison: owner-before import d50db2e8f3f1 -> 088_import_model and sprites 1264d1166448 -> 089_sprites; initial transfer 8a61abd5afea -> 091_import_model and 1f6f2aaa23e7 -> 092_sprites; repaired baseline b95fb2629341 -> 094_import_model and aa0300108645 -> 095_sprites. All eight repaired views were inspected.
- Texture trial 7a07934e4cae -> 096_refine used the local Z-Image/full Tile model, strength 0.4, scale 1.0, four views and texture_size keep. Runtime reported 290.4 seconds including 273.3 seconds loading, 12.05 GiB peak VRAM, 1024 output and seam delta 26.579 -> 7.817. These metrics do not establish visual preference. Sprites 3ac504754150 -> 098_sprites were inspected from eight directions; the result is a restrained, somewhat softer comparison with material boundaries retained.
- Baseline export 7aa50b42ea4d -> 097_export; reopen 027947d55025 -> rim_elm_hut_owner_edit_repack_reopen/002_import_model. Trial export 35a6a2775939 -> 099_export; reopen 57cf554b403b -> rim_elm_hut_owner_texture_trial_reop/002_import_model. Both retain 409 triangles and 1024 albedo; their geometry and UV assignments match the repaired baseline at five decimals. Reopened trial has one material, two texture images and no missing textures.
- Native authoring reopen found all images packed and the new editable source at 409 faces. Authoring blends are stored in each export's authoring/ folder. Changed-file Ruff passed. Runtime policy remained offline with zero browser violations; one connection observation during refinement found no non-loopback connections owned by the observed Effigy Python processes. No tests, hashes, downloads, commits or shared-installation changes occurred.

## Steps

1. Snapshot the confirmed saved file; inspect the edited mesh and export its current appearance.
2. Retain existing UV layers. Add a new layer, establish seams for new geometry, unwrap with Zen UV and pack with UVPackmaster at 1024.
3. Re-bake existing appearance onto the new UVs and save a separate editable blend and GLB.
4. Import into Effigy; inspect rendered directions and preserve this baseline.
5. Run one bounded local texture refinement on a separate version; retain 1024, geometry and UVs. Reject visible material/architectural drift.
6. Export/reopen the chosen result and record ordinary application identities here.

## Files to touch

- scratch/legaia/
- docs/plans/local-upgrades/
- N:/generated/Effigy/

## Verification

1. Blender/native provider operations. Expected: edited geometry and protected UVs unchanged; valid new UVs and successful packing.
2. Texture bake and rendered samples. Expected: 1024 atlas, no blank added surfaces or destructive appearance transfer.
3. Export/reopen. Expected: geometry matches the owner's snapshot, textures present, inspectable authoring file.
4. Changed-file Ruff and plan check. Expected: pass; no code tests, hashes or additional evidence packs.

## Risks

New faces may carry collapsed source UVs. Their transferred colour may need local repainting even after fresh UVs are valid. A texture model can alter thatch, mortar or openings; reject such drift rather than selecting it because the job completed.

## RESULT

Completed the requested round-trip on a private snapshot of the owner's saved edit. All 409 triangles retained. Zen UV + UVPackmaster produced a new 1024 atlas; 64 collapsed source-UV faces -> zero, with no sampled overlaps. Added stair/window/vent surfaces received bounded texture-coordinate repairs.

Repaired baseline: 094_import_model; eight views 095_sprites; GLB and editable blend under 097_export. Separate texture trial: 096_refine; eight views 098_sprites; GLB and editable blend under 099_export. Both exports reopened without missing textures and with matching geometry/UVs.

Texture trial is available for owner comparison, not claimed as visually approved. Original saved file and live Blender session remain intact. Vahn remains held. Ruff and plan checks passed; changes remain uncommitted.
