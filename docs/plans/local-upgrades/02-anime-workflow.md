# Qualify the anime mesh and animation workflow

Spoke: S02
Outcome: Make the selected models available in Effigy and qualify an anime asset through mesh, texture, rigging, animation and export.
Depends-on: S01
Decisions: D1, D2, D3, D4
Constraints: C1, C2, C3, C4
Skills: python:python-core, web:typescript-core, aep:aep-core
Read-set: INDEX.md, 01-compare-models.md#result, CODE.md, server/jobs.py, server/model_bindings.py, server/presets.py, steps/_common.py, steps/trellis2.py, ui/src/main.tsx, configured native inference source
Write-set: server/__init__.py, server/reference_models.py, server/jobs.py, server/presets.py, server/app.py, steps/reference.py, steps/project.py, tools/native_reference_entry.py, ui/src/api.ts, ui/src/main.tsx, ui/src/ReferenceModels.tsx, ui/src/workflow.ts, model-bindings.local.json, CODE.md, docs/adr/, docs/LOCAL-SETUP.md, docs/plans/local-upgrades/, N:/generated/Effigy/, scratch/
State: done

## Context

Expected 20 turns, implementation ceiling 2250000 tokens, 256-turn breaker and 14500000 tokens per active hour. Owner wants actual mesh, texture and animation use. Krea/Qwen checkpoints supply references and edits; TRELLIS still owns geometry and texture transfer, and existing rig/motion stages own animation. Model availability or a standalone image cannot close this unit.

## Evidence

- server/jobs.py:191 launches isolated step workers and :443 cancels owned process trees.
- steps/_common.py owns offline activation, GPU budgets, scratch staging and result publication.
- steps/trellis2.py:482 selects a prep version in the same asset for retexturing; :504 preserves mesh vertices, faces and UVs while replacing textures.
- ui/src/main.tsx returns the resulting version from each normal step chain; ui/src/ReferenceModels.tsx composes reference edit, preparation and mesh retexturing.
- Anime checkpoint: 13.51 GiB, 224 MXFP8 layers. Job 7b1c547e3b87 -> anime_workflow_local_checkpoint/002_reference: 181.61 seconds, 15.68 GiB peak Torch allocation. A-pose and separated limbs inspected. Duplicate quantization-metadata warning was nonfatal.
- Native bootstrap fixes: regular server package prevents a ComfyUI import collision; runpy alter_sys=True enables the existing buffered protocol. Failed/cancelled attempts remain in jobs.log.
- Existing native engine is ComfyUI 0.30.0, Python 3.12 and Torch 2.10.0+cu130. Reuse it as a configured external worker, without importing its dependency pins into Effigy environments.
- Faithful a9fcf83c8621 -> 004_trellis2: 17490 triangles, 203.5 seconds (183.5 loading), 9.2 GiB peak. Front/oblique views retained silhouette and clothing. UI Prepare -> 005_clean through 009_validate: 15418 triangles, zero hard failures; warnings for 374 boundary edges, two parts and 2.78 percent self-intersection samples.
- UI Qwen edit 980e6e218a7d -> 010_reference: 369.85 seconds, 17.48 GiB peak. Crimson jacket and close pose/framing, but unwanted patterned background. Exact edit locality is not accepted.
- UI chain -> 011_prep and texture f72f11772a79 -> 012_trellis2: clean background removal, damaged face/hand texture detail. Projection now resolves the original geometry camera across texture volumes and preserves transforms. Its UI retains the edited reference. Head projection 36c2eb6e5f7c -> 013_project and front projection 3f55dc89a209 -> 014_project achieved 0.952 silhouette overlap and clearer front detail. Peripheral defects remain.
- Rig fit 048ad3c13b61 -> 015_rig_fit: all 52 joints inside, both hands detected, no low-confidence joints. Skin 3b2d7a5acc07 -> 016_rig_skin: Auto chose Blender; zero hard failures/unweighted vertices, four influences, 2.079 maximum stretch. Alternate SkinTokens output retained, 3.39 GiB peak.
- Both skinning reports meet the hard QA limits for this sample; SkinTokens' maximum stretch was 2.582. Walk job 53c63a2c7c4a -> 017_anim was played and inspected from the side. Kimodo job f3478ee27814 -> 018_motion generated a three-second right-hand wave in 114.4 seconds with the text encoder on CPU. Retarget 33949a53902f -> 019_anim contains Walk and the generated wave.
- Sprites c9f9b105edf0 -> 020_sprites rendered 111 frames from front, side and back. Export 5874721dccdf -> 021_export produced the animated Godot GLB. Normal upload/import job 262749f381f7 reopened that exact file as anime_workflow_reopened_glb/002_import_model: 15418 triangles, one material, two textures, no missing textures, Mixamo52 skeleton and both clips. The imported wave was played and inspected at frame 36 after restarting the backend.
- Functional acceptance passes; ears/neck, fingers and peripheral textures need cleanup. Qwen is not accepted for unattended texture upgrades. Original blue material: 008_bake. Genesis NVFP4 arithmetic remains unqualified; stored metadata requests higher precision.
- Observed backend peers were loopback; native workers had no TCP peers; browser CSP had zero violations. This is application behavior, not OS containment. Restart on 127.0.0.1:8370 passed; shared weights, engines and other workloads were preserved.

## Steps

1. Record the external-worker reuse decision and bind named shared checkpoint/encoder/VAE roots read-only.
2. Add a reference-model registry, local availability endpoint, isolated native step bootstrap and ordinary job routing. Preserve the offline policy and GPU cancellation/budget behavior.
3. Add reference generation/edit controls and a reference-edit-to-texture action for static UV meshes. Preserve normal history and baseline choices.
4. Generate an anime A-pose reference, prepare it, build a Faithful mesh, and run the normal clean/simplify/unwrap/bake/check action. Inspect silhouette, textures and reported defects.
5. Use Qwen to edit the reference material, prepare it, and retexture the same mesh. Inspect the actual textured 3D output.
6. Fit and skin a rig, retarget a bundled walk and a bounded local Kimodo motion sample, inspect motion/sprites, export an animated GLB and reopen it in the app.
7. Record normal job/version identities and any quality failures. Run Ruff, UI build and ADR/plan structural checks only; no code tests or model hashes.

## Files to touch

- server/__init__.py
- server/reference_models.py
- server/jobs.py
- server/presets.py
- server/app.py
- steps/reference.py
- steps/project.py
- tools/native_reference_entry.py
- ui/src/api.ts
- ui/src/main.tsx
- ui/src/ReferenceModels.tsx
- ui/src/workflow.ts
- model-bindings.local.json
- CODE.md
- docs/adr/
- docs/LOCAL-SETUP.md
- docs/plans/local-upgrades/
- N:/generated/Effigy/
- scratch/

## Verification

1. Source checks -> Ruff, UI build, ADR and plan checks pass under the accepted baseline policy.
2. Normal app jobs -> anime reference, textured mesh, rig, animation and export have inspectable outputs and retained history.
3. Runtime observation -> CUDA used within available memory, offline controls active, no shared file/environment mutation or foreign workload cancellation.

## Risks

Anime silhouettes and faces may not reconstruct or rig well. Qwen can alter framing or details; inspect the mesh after texture transfer. Native engine changes can invalidate compatibility. Stop for missing dependencies, memory pressure, or quality failures needing a new owner decision.

## RESULT

Implemented optional local reference models, Qwen edit-to-retexture controls and post-retexture camera-aware projection. Functional path exercised on anime_workflow_local_checkpoint: 002_reference -> 004_trellis2 -> 005-009 preparation -> 010-014 texture edit/projection -> 015-016 rig -> 018_motion/019_anim -> 020_sprites/021_export. Export reopened as anime_workflow_reopened_glb/002_import_model with both clips and textures. Both skin engines passed hard QA; Auto chose Blender. Ruff, UI build and ADR/plan checks passed; no code tests, hashes, downloads or shared-environment changes. Runtime remained offline under observed application controls. Quality limit: Qwen direct retexturing damaged detail; projection improved the front, while ears/neck/fingers still need cleanup. This is a working review sample, not a finished production asset. Baseline defaults retained. Changes remain uncommitted.
