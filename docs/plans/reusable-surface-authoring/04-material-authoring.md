# Create material-consistent authoring methods with shared preservation

Spoke: S04
Outcome: Unify material intent across authoring methods
Depends-on: S03
Decisions: D1, D2, D3, D4, D5
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, art:texture-painting-core, art:art-3d-realtime-core
Read-set: docs/plans/reusable-surface-authoring/INDEX.md, docs/plans/reusable-surface-authoring/03-sampling-and-projection.md#result, steps/paint_generate.py, steps/reference.py, steps/paint_finish_generate.py, steps/uv_context.py, server/paint_sessions.py, docs/plans/multi-view-paint/11-runtime-comparison.md#result
Write-set: server/app.py, server/authoring_contracts.py, server/paint_sessions.py, steps/paint_generate.py, steps/reference.py, steps/paint_finish_generate.py, steps/uv_context.py, tools/blender_prepare.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring
State: done

## Context

Load 3dgen-core -> blender-projection-painting -> repeatable-authoring and 3dgen-prompt-core for the named generator. Texture-painting doctrine applies to explicit brush work; generated paint remains labelled generated. Establish material consistency before adding more independent patches.

Expected turns: 20. Preserve standing budgets and prior results. Source changes remain uncommitted. Ordinary app outputs are runtime artifacts under C4, not extra evidence packs.

## Evidence

- server/paint_sessions.py:45 retains recipe/source/selection identity; :244 updates revision-bound state.
- steps/uv_context.py:23 transfers registered source appearance; :69 dispatches the ordinary operation.
- steps/paint_finish_generate.py:225 uses model-specific repair wording; :328 records automatic regression retention.
- docs/plans/painting-completion/11-material-base-quality.md:23 identifies mixed source detail and differing repair scales.

## Steps

1. Introduce a persistent appearance contract: material identity, palette, feature scale in declared asset units or measured reference ratios, mark direction, value range, detail hierarchy and protected motifs. Separate observed source description from requested style. Local vision may draft editable observations using the owner's selected small model; it cannot accept style or change the source.

2. Provide explicit restore-source, refine-current and restyle operations. Each pins context source, permitted surface and appearance source. Restore-source may substitute registered retail/donor RGB only inside its core; accepted/current context remains outside. Never silently use a rejected render as the next baseline.

3. Use one material reference and calibrated capture scale across neighbouring regions. Author low/mid-frequency material organization before optional fine strokes. Enforce that intentional steps, beams and material borders remain distinct. A foundation stone target must express stone size relative to the building, not only the phrase small stones.

4. Keep three method adapters separate: existing local generative edit; registered source reconstruction without inference; explicit native Blender brush strokes/manual Texture Paint. All return candidate pixels plus their source/camera/write bindings to the same projector. Reuse canonical projection/brush interfaces read-only; do not copy Legaia prompts into a generic provider or invent an automatic brush artist.

5. Route installed Genesis, FIBO and MOSS through their actual supported controls. Preserve their runtime separation and exact precision reporting. Whole-sheet context is not synchronized diffusion. Keep existing SyncMVD as an experimental retained capability; no new SD/model substitution or comparison campaign is implicit.

6. Compare only like-for-like material anchors and baked views. Persist model/checkpoint/LoRA/precision/seed/conditioning and source ancestry. Rank visual coherence, useful detail, preservation, cold latency and warm latency separately. Select a method per task class; never declare a universal winning model from one inherited asset.

7. Keep manual or registered-source correction available when generation invents structure. Switching method, source or material scale is a visible recipe revision and invalidates affected candidates. Retained completed work remains inspectable.

## Files to touch

- server/app.py
- server/authoring_contracts.py
- server/paint_sessions.py
- steps/paint_generate.py
- steps/reference.py
- steps/paint_finish_generate.py
- steps/uv_context.py
- tools/blender_prepare.py
- tools/stage_multi_view_trial.py
- docs/plans/reusable-surface-authoring

## Verification

1. Create one bounded example for each method through ordinary application actions: model edit, registered donor transfer and explicit Blender brush stroke. Expect identical permission semantics and no effect outside the declared surface.
   Expected: Each method obeys the same final permission boundary.

2. Inspect material anchors and their baked neighbouring surfaces at equal display scale. Verify grain/stone/stroke size is consistent and lighting has not been baked into base colour by an unintended preview path.
   Expected: Baked material identity and feature scale meet the declared profile, or the candidate is rejected.

3. Confirm a requested unsupported reference or conditioning mode produces an actionable capability message; no silent model/LoRA fallback.
   Expected: Unsupported controls stop with a named capability error and no fallback.

4. Run scoped Ruff. Generation samples count against S07's shared budget, including work performed during this unit.
   Expected: Changed Python passes Ruff and sample usage is recorded against the shared cap.

## Risks

Prompts and shared style images do not force exact cross-view mortar alignment. Deterministic reconstruction or native brush work may be preferable for structured features. Fast warm inference is not end-to-end performance and is not evidence of art quality.

## RESULT

Three adapters now share revisioned material intent and permission guards. Generated crate job581003ec7b58 baked018; its nearly white appearance was operator-rejected, not ranked as painted wood. Registered donor job708e88df3d5b produced hut317 without inference. Native Blender image_paint changed270 pixels; guarded reconstruction89b6e8627c95 produced crate017, publicationf1619e4938f1 aliases it as019 without another GLB. Independent decoded checks found exact geometry/UVs, alpha and other maps; generated018 changed1768 surface and325 permitted empty-gutter texels, zero elsewhere. Fixed historical pair raster/image size mismatch without regenerating its model output. Material face overlap is rejected; empty prompt fields are omitted. Scoped Ruff passes. Trial model preflight now reports missing components before engine loading. Source missing-model CLI qualification is recorded in S07. Art/UI qualification remains S07/S09.
