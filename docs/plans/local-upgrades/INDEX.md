# Integrate local models into the asset workflow

## Outcome

Make existing Krea2 and Qwen Edit models usable in Effigy's mesh, texture and animation workflow, then qualify an anime asset through export. Preserve the accepted baseline and record the preliminary image comparison as supporting work.

## Decisions

- D1 (2026-10-20): Owner requested trials of upgrade proposals, including existing Krea2 and NVIDIA accelerated quantization.
- D2 (2026-10-20): Owner selected existing Genesis NVFP4 with no model download.

- D3 (2026-10-20): Owner prioritized the existing anime checkpoint for meshes.
- D4 (2026-10-20): Owner clarified: "im using this tooling for mesh and texture and animation, not just 2d image gen, so we should setup and test the models that workflow not just more image gen".
- D5 (2026-10-20): Try a Legend of Legaia building first, then Vahn's battle model.
- D6 (2026-10-20): Compare texture improvements on preserved geometry with regenerated meshes on separate copies.
- D7 (2026-10-20): Owner already has a better inn; use a Rim Elm hut instead. Stop further inn processing.
- D8 (2026-10-20): Keep Vahn's original battle stance for the regenerated comparison.
- D9 (2026-10-20): Finish and present the hut comparison before any further Vahn work. Its source extraction and import happened prematurely; hold subsequent processing.
- D10 (2026-10-20): The owner's Ghibli-styled retail inn screenshot is the minimum visual quality target: deliberate brushwork, distinct materials, readable architectural edges and coherent colour. A mild cleanup or technically successful export does not meet this target.
- D11 (2026-10-20): Owner confirmed the reference inn used the FLUX Ghibli + Arcane workflow. Reuse its existing local components: FLUX.1-dev Q8, Ghibli LoRA 0.7 and Arcane LoRA 0.35. Keep the source workflow and shared files unchanged; qualify the isolated Effigy adapter through the hut.
- D12 (2026-10-20): Owner rejected the hut's excessive 4096 atlas, wall drift and loss of thatch. Continue on a separate copy using installed Blender, Zen UV and UVPackmaster to repair layout and stretching, reduce repetition, restore retail material identity and target a 1024 atlas. Preserve the source and earlier candidates; Vahn stays held.
- D13 (2026-10-20): Owner considers the 1K hut a decent improvement, edited its geometry in Blender, and requested a fresh unwrap/UVPackmaster pack followed by texture iteration in Effigy. Owner confirmed the hut was saved. The edited visible mesh is authoritative; the hidden 277-face material reference must not replace it.
- D14 (2026-10-20): Owner requested a more hand-painted iteration of the new mesh using texture-painting-core and Legaia guidance, with art-review, Python and PowerShell guidance. Use explicit Blender brush strokes for this pass; keep the 409-triangle geometry, current UVs and 1K atlas.
- D15 (2026-10-20): Owner found the brush result too subtle and approved an interactive FLUX Ghibli + Arcane image-to-image, masked projection and refinement workflow for imported meshes. Expose denoise and preserve texture size. Consider the established prompt, video, painting, realtime art, Legaia and Blender skills as one suite; broader integrations remain staged separately.
- D16 (2026-10-20): Owner explicitly instructed quitting Ollama to release GPU memory and resume this work. This authorizes stopping Ollama only; other workloads remain protected.
- D17 (2026-10-20): Runtime found all 640 configured Arcane keys ignored by FLUX. Owner selected "Continue with Ghibli for this hut". Remove the incompatible Arcane component from this recipe, name it accurately, and reject unmatched LoRA keys before generation.

## Constraints

- C1: Offline inference, read-only existing model weights, no model downloads, no shared environment changes, tests, hashes, commits, pushes or subagents.
- C2: Preserve other GPU work. Use CUDA 0 only within currently available memory; never terminate or unload foreign workloads.
- C3: Keep results in ordinary images/application assets and this plan. The two baseline storage audits remain the only audit reports; this trial installs or moves no models.
- C4: Existing native inference modules run in an isolated Effigy worker using the configured installed interpreter. Do not modify the shared engine, pins, workflows, or services. Keep baseline models available and route native model paths through the read-only resolver.
- C5: Legaia sources and accepted artwork stay read-only. This trial does not rebuild or publish game scenes, alter overlays, or replace the owner's Vahn work.

## Terms

- Baseline: accepted Effigy installation and its existing synthetic samples.
- Candidate: an optional local model whose workflow suitability requires runtime qualification.

## Spokes

| ID | File | Outcome | Depends on | Skills | Write set | State | Commit | Result |
|---|---|---|---|---|---|---|---|---|
| S01 | 01-compare-models.md | Compare existing Krea2 and Qwen Edit candidates through local image samples while preserving the accepted Effigy baseline. | none | planning:prototypes-and-spikes, python:python-core | scratch/upgrades/, N:/generated/Effigy/, docs/plans/local-upgrades/ | done | - | 01-compare-models.md#result |

| S02 | 02-anime-workflow.md | Make the selected models available in Effigy and qualify an anime asset through mesh, texture, rigging, animation and export. | S01 | python:python-core, web:typescript-core, aep:aep-core | server/__init__.py, server/reference_models.py, server/jobs.py, server/presets.py, server/app.py, steps/reference.py, steps/project.py, tools/native_reference_entry.py, ui/src/api.ts, ui/src/main.tsx, ui/src/ReferenceModels.tsx, ui/src/workflow.ts, model-bindings.local.json, CODE.md, docs/adr/, docs/LOCAL-SETUP.md, docs/plans/local-upgrades/, N:/generated/Effigy/, scratch/ | done | - | 02-anime-workflow.md#result |

| S03 | 03-legaia-assets.md | Compare preserved-geometry texture refinement and regenerated meshes for one Legaia building, then Vahn's battle model. | S02 | planning:planning-core, python:python-core, aep:aep-core | docs/plans/local-upgrades/, steps/reference.py, server/reference_models.py, server/presets.py, model-bindings.local.json, scratch/legaia/, N:/generated/Effigy/ | active | - | 03-legaia-assets.md#result |

| S04 | 04-owner-hut-iteration.md | Unwrap the owner's edited hut, repack at 1024 and create a separate texture iteration in Effigy. | S03 | planning:planning-core, python:python-core, aep:aep-core | docs/plans/local-upgrades/, scratch/legaia/, N:/generated/Effigy/ | done | - | 04-owner-hut-iteration.md#result |

| S05 | 05-guided-brush-hut.md | Produce and review an explicit brush-painted hut candidate in Effigy. | S04 | art:texture-painting-core, python:python-core, powershell:powershell-core, aep:aep-core | docs/plans/local-upgrades/, scratch/legaia/, N:/generated/Effigy/ | done | - | 05-guided-brush-hut.md#result |

| S06 | 06-interactive-surface-paint.md | Expose captured-view image editing and masked texture projection for imported meshes. | S05 | python:python-core, web:typescript-core | steps/, server/jobs.py, server/reference_models.py, ui/src/, docs/plans/local-upgrades/, docs/LOCAL-SETUP.md, scratch/legaia/, N:/generated/Effigy/ | done | - | 06-interactive-surface-paint.md#result |

## Reading rule

Read this index and the owning spoke; baseline results are in ../local-gpu/05-runtime-acceptance.md#result. Expected 20 turns, 256-turn breaker, 2250000-token implementation ceiling and 14500000 tokens per active hour; no wall-clock cap.

## Non-goals

Model conversion/training, new packages or model downloads, replacing baseline choices, benchmark campaigns, private reference inputs, and changes to 3DGen.

## Open questions

- Deferred: native FP4 arithmetic remains experimental until a workflow sample verifies output and hardware behavior. Resume that optional path after the anime workflow is operational.
