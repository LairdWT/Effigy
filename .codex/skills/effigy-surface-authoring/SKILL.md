---
name: effigy-surface-authoring
description: Prepare, paint, reconstruct and review a static atlas-textured mesh in Effigy's local surface-authoring workspace, including its isolated Blender round trip and bounded repair recovery.
---

# Effigy surface authoring

Use Effigy's paint session as the state owner. Read the repository's CODE.md and the relevant operation below. This local skill does not activate the primary lane or authorize model installation.

## Route

- [Source roles and supported inputs](../../../docs/SURFACE-AUTHORING.md#source-and-profile): start here for a new asset, geometry revision or appearance target.
- [Blender preparation](../../../docs/SURFACE-AUTHORING.md#prepare): inspect, unwrap, pack, open or return a copied mesh. Resolve tools through local settings and tools.config.json.
- [Sampling and selection](../../../docs/SURFACE-AUTHORING.md#select-and-capture): choose detail versus study, capture fixed cameras and diagnose missing coverage.
- [Authoring methods](../../../docs/SURFACE-AUTHORING.md#author): choose model editing, registered-source reconstruction or explicit Blender brush work.
- [Hand-paint handoff and heal](../../../docs/SURFACE-AUTHORING.md#hand-paint-handoff-and-heal): export guide renders and handoff.json for hand painting, mark a seam-heal zone and reconstruct a brush return inside it.
- [Review and publication](../../../docs/SURFACE-AUTHORING.md#review-and-publish): inspect baked surfaces, record preference/rejection and publish by reference.
- [Bounded recovery](../../../docs/SURFACE-AUTHORING.md#recover): resume checkpoints, resolve stale inputs and distinguish technical admission from appearance acceptance.

## Operating contract

The enabled implementation is the trial on localhost:8380. Preserve the source and every historical candidate. Prepared UV geometry is a new source revision; a similar filename does not make an old mask compatible. Green means permission to paint.

Use installed blender-core and 3dgen-core routes for generic Blender operations. Use texture-painting-core for explicit native brush work, art-3d-realtime-core for the selected art profile and 3dgen-prompt-core for a named model's prompt. A generated image is not a native brush-stroke result. Keep shared Blender/3DGen providers read-only. Legaia's source bindings, palette and owner verdict belong to its consumer; do not turn hut-specific prompts into generic defaults.

Do not infer a model winner from inherited paint or a successful job. Compare matched baked views and retain the model/checkpoint/precision/seed record. Numeric retention never sets owner acceptance. A projection may still contain incompatible generated content; repair the responsible stage rather than repeatedly feathering contradictory edges.

Check the bake's footprint-filter policy and accumulated writer ownership when diagnosing aliasing or missed joins. Capture sampling alone does not prove correct atlas filtering. Writer boundaries are advisory; inspect the actual adjacent baked surfaces before spending a repair attempt. Preserve historical policy bindings and stop inference at the recorded batch allowance.

Use existing API actions and job IDs. Read-only diagnostics precede inference; technical sampling/geometry failures do not spend model calls. Reserve a finite batch, retain completed results, and never rerun a completed candidate implicitly. Reconstructing a registered donor or pulling an explicit native stroke requires no model.

## Qualification status

The implementation and API samples are recorded in [the owning plan](../../../docs/plans/reusable-surface-authoring/INDEX.md). UVPackmaster, ZenUV followed by packing, source reconstruction, native Blender strokes and guarded model projection have runtime evidence. UV Squares is incompatible with the current Blender API. UI and fresh-operator acceptance remain incomplete while browser control is unavailable. This skill does not claim a production-qualified or seamless automatic artist.
