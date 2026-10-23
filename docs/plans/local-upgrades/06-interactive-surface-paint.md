# Add interactive surface painting

Spoke: S06
Outcome: Expose captured-view image editing and masked texture projection for imported meshes.
Depends-on: S05
Decisions: D12, D13, D15, D16, D17
Constraints: C1, C2, C3, C4, C5
Skills: python:python-core, web:typescript-core
Read-set: INDEX.md, 05-guided-brush-hut.md#result, CODE.md, steps/_views.py, steps/_glb.py, steps/reference.py, ui/src/ReferenceModels.tsx
Write-set: steps/, server/jobs.py, server/reference_models.py, ui/src/, docs/plans/local-upgrades/, docs/LOCAL-SETUP.md, scratch/legaia/, N:/generated/Effigy/
State: done

## Context

Expected 55 turns, 256-turn breaker, 2250000-token ceiling. Deliver the approved surface-paint loop and map broader integration. No new video provider, shared runtime changes or canonical Legaia edits.

The hut remains 409 triangles with its current unique UV atlas and one 1024 albedo. Its density is 432.322 texels per Effigy asset unit, unchanged from S05; no metre conversion is asserted. Version 104 is a source candidate, not an accepted final appearance. The owner rejected its degree of style change. Vahn remains held.

## Evidence

Later closure (2026-10-21): the historical restart block below was resolved. Surface-paint-ux/S05 and multi-view-paint/S11 record subsequent UI generation, projection, camera retention, restart/resume and Apply. The original failure remains historical evidence; seam quality continues under painting-completion/S03.

- Starting state: ui/src/ReferenceModels.tsx:93 hid denoise and hardcoded 2048 transfer; imported meshes lacked texture controls.
- reference.py supplies the local FLUX worker. Under D17 its recipe is Ghibli 0.7 only, with mandatory LoRA coverage checks. _views.py owns camera coordinates; _glb.py preserves binary geometry.
- Prompt-core separates FLUX scene prose from Qwen instructions. Blender guidance separates source/candidate/acceptance and requires visible-triangle permission. Effigy owns this adapter; Legaia sessions stay read-only.

### Implementation and observed samples - 2026-10-20

- Added capture/apply, bounded masks, 16-bit atlas preservation, saved drafts, model-specific prompts, denoise/seed controls and enlarged mask editing. Existing refinement is exposed on imports; legacy transfer now defaults explicitly to 1024.
- API capture 107 (759d6fa8c2d8), browser capture 108 (22c08ae3c32a) and rear capture 109 (7d59542a6690) passed. Captures retain the input mesh; 109 confirms 409 triangles, 1024 and 16-bit CPU decoding.
- Browser drawing, erasing, keyboard marks, draft save/reload, generation and Apply were exercised. Original generation masks remain intact; projection variants add separate vent/crown protection.
- Ruff, UI build and plan structure passed. Broader AEP type/lint findings remain advisory under the accepted deviation, not a strict audit pass.
- D16 released Ollama's 27.1 GiB allocation. Its app/server reappeared once without a model; those instances were quit too. Other workloads remained protected.

| Output / job | Observed result |
|---|---|
| 110_reference / d6b23be6694c | All 640 Arcane keys ignored; roof decorations invented. Historical combined-model label is inaccurate. |
| 111_reference / 3a6001e4866d | Ghibli-only: 912 keys, 304 applied modules, zero unmatched; 16.95 GiB CUDA peak. Continuous painted thatch. |
| 112_reference / 2fc959859a26 | Denoise 0.45 comparison; agent prefers 0.60 for this roof pass. |
| 113_paint / f8112e059905 | Binary geometry/UV data and alpha retained; small white edge leak identified. |
| 114_paint / 0cc48db261c9 | Background exclusion fixes leak; 63572 changed texels, zero outside-mask/alpha changes. |
| 115_sprites / 3296a6b916c4 | Eight views inspected. One roof-view pass; remaining style coverage and transitions need art work. |
| 116_paint / 4c49b63cc09a | Close roof capture for localized refinement. |
| 117_refine / fed9334b6beb | One view, strength 0.3, 1K output; 9.46 GiB CUDA peak. Visual comparison inspected; optional 8-bit variant. |
| 119_paint / d4ec80d889d4 | Same pixels as 114, now propagating actual model provenance. Preferred 16-bit review source. |
| 120_export / 7a507771cf56 | Godot GLB exported from 119. Reopened as rim_elm_hut_surface_paint_reopened/002_import_model (37e473ff98d4): 409 triangles, 1K uint16, matching geometry/UVs, no missing textures. |
| 121_paint / 8b0d6b9a2e08 | Browser Apply: 409 triangles, 1K/16-bit, zero outside-mask/alpha changes. Comparison inspected; vent retained, roof style transitions remain. |

The owner authorized an idle Effigy restart. Automatic approval rejected it again,
returning only "blocked by policy". No bypass was attempted. Fresh workers use the
corrected Ghibli recipe, but the running backend's cached menu label awaits restart.

## Steps

1. Add capture/apply operations with immutable source/camera linkage and bounded local inputs.
2. Capture unlit square views on CPU, retaining mesh lineage.
3. Expose prompt, settings, selection, comparison and application controls on imports and captured views.
4. Use the existing GPU worker for FLUX descriptions or Qwen instructions; persist concrete recipes and masks.
5. Project selected, front-visible texels; preserve alpha, atlas precision/size, other maps and binary geometry.
6. Expose existing localized refinement without automatic texture enlargement.
7. Build, exercise ordinary hut samples, inspect real outputs and leave the painting UI available.

## Files to touch

- steps/
- server/jobs.py
- server/reference_models.py
- ui/src/
- docs/plans/local-upgrades/
- docs/LOCAL-SETUP.md
- scratch/legaia/
- N:/generated/Effigy/

## Verification

1. Changed Python Ruff and offline UI build. Expected: pass without tests, downloads or model hashes.
2. AEP plan check. Expected: structurally valid index and spoke.
3. Hut capture, FLUX edit, masked apply and refinement. Expected: completed application jobs and inspectable outputs.
4. Source versus result. Expected: same geometry/UV accessors, 409 triangles, 1024 texture, preserved alpha and pixels outside mask/gutter permissions.
5. Browser. Expected: usable controls, persisted recipe/mask, comparison, apply and continuation.

## Risks

Large denoise can invent architectural details or turn straw into wood. Full-frame image generation is not masked inpainting: the mask limits writeback, not model attention. Camera changes after capture must not change projection. Overlapping UVs and unsupported multi-material/skinned meshes must fail visibly rather than corrupt shared texels. Source/current/candidate versions must never be confused.

## Suite integration map

Prompt-core and Legaia own source roles and material intent; Blender owns mesh/UV
preparation; texture-painting-core owns explicit brush work; realtime art owns
shading/rig conventions. Video prompt guidance remains separate from existing
mocap. Art review and export/reopen retain owner acceptance. S06 implements the
captured-view texture workspace; broader adapters remain proposed.

Cleanup (2026-10-20): 96 superseded versions now reside in recoverable Trash;
historical sample links may point there. Current 119-122 and dependencies remain.
Approved purge was blocked. Scope and UX proposals: ../surface-paint-ux/INDEX.md.

## Historical RESULT before restart closure

Implemented and exercised capture -> Ghibli edit -> masked projection -> localized refinement -> export/reopen. Preferred source: 119_paint, exported in 120_export; UI application also passed as 121_paint. Geometry/UVs and the 1K 16-bit atlas are preserved in the main result. Ghibli coverage is 912 keys/304 modules with none unmatched; incompatible Arcane was removed under D17. This is a roof-view iteration, not owner-approved finished artwork. Ruff, UI build and plan checks passed. Only the live model-menu refresh remains blocked: automatic approval denied the explicitly authorized Effigy restart. Ollama is quit, other workloads preserved, changes uncommitted, Vahn held.

## RESULT

Implemented and exercised capture, local image editing, masked projection, refinement and export/reopen. Original samples119/120/121 preserve geometry, UVs and the1K16-bit atlas. The historical restart blocker is resolved: surface-paint-ux/S05, multi-view-paint/S11 and painting-completion/S02-S04 record subsequent UI generation, projection, restart, persistence and current model controls. Ghibli coverage was912 keys/304 modules; incompatible Arcane was removed under D17. Source checks and UI builds passed. Artistic acceptance and Vahn remain held separately; changes are uncommitted.
