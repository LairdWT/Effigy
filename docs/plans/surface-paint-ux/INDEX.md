# Make repeated surface painting easier and smaller

## Outcome

Carry the hut's approved appearance between camera angles, select precise mesh
regions, and retain useful revisions without copying unchanged payloads.
Optional local vision suggestions must reduce typing without replacing owner
direction or starting a persistent GPU service.

S00-S05 are implemented; owning RESULT sections record runtime observations and
limits. S05 includes the owner-requested camera retention and paint-mask default
correction in both UIs. The later trial browser recheck is recorded in
../painting-completion/04-workflow-acceptance.md#result; S09 also verifies
finishing recipe and mask carry-over. Primary-lane scope is unchanged.
Source changes are uncommitted; artistic acceptance remains separate.

## Decisions

- D1 (2026-10-20): Owner requested cleanup of old files and proposed description
  carry-over, face selection, less duplication and local vision assistance.
- D2 (2026-10-20): After reviewing the scoped cleanup, owner chose
  "Permanently delete these 96 versions".
- D3 (standing): Preserve local-only execution, borrowed weights, owner geometry
  and UVs, and the 1024 atlas. No tests, hashes, downloads, shared environment
  changes, subagents, commits or pushes.
- D4 (2026-10-20): Owner reaffirmed Krea2 Genesis as the painting model. Use
  `N:/generated/3DGen-models/checkpoints/Krea2_Genesis-Blackwell-Optimized-nvfp4.safetensors`.
  The earlier Ghibli-only approval covered the completed hut pass; it does not
  replace Genesis as the selected model for this workflow.
- D5 (2026-10-20): Owner selected
  `N:/generated/3DGen-models/image_categorization/Q3.5-9B-OpusGLM-MAX-0731-ablated-GGUF`
  for descriptions, rejecting the larger alternatives. Use its Q8_0 model and
  matching `mmproj-q8_0.gguf`; do not substitute Qwen3.6/3.8, Qwen3-VL or JoyCaption.

- D6 (2026-10-20): Owner requested completion of this plan, including S00-S04.
- D7 (2026-10-20): Owner resolved the restart approval block and authorized restarting
  Effigy when idle. This does not change model ownership or other-workload protection.
- D8 (2026-10-20): Owner requested incremental masked image-to-image projection,
  retaining the full captured image as context and protecting already-good areas.
  Apply the Legaia differential-inpainting route and texture-painting preservation
  guidance. Full access restores execution authority for this correction.

## Cleanup outcome

Normal Effigy cleanup moved 96 superseded hut versions into 38 recoverable
Trash groups (1209649031 bytes). Source, Blender files, owner geometry, required
ancestors and then-current work were retained. Permanent deletion was blocked;
no bytes were reclaimed. D2 remains authorized; do not empty unrelated Trash.
The scoped groups under `N:/generated/Effigy/_trash/` are dated
`20261020T182051` through `20261020T182100` and name this hut's asset ID.

## Constraints

- C1: D3 governs every unit. Reuse existing isolated workers; leave Ollama stopped.
- C2: Treat source/reference, desired appearance, model suggestion and applied
  result as distinct data. Owner text wins; suggestions require an explicit apply.
- C3: Preserve ordinary application metadata and reversible revision history.
  No extra audit reports or evidence packs.
- C4: Runtime samples establish behavior. Source checks do not establish visual
  quality or model compatibility. Keep Vahn held pending hut review.
- C5: Honor automatic approval blocks; this plan does not authorize bypasses.
- C6: D4 and D5 settle model selection. A missing capability or incompatible
  runtime requires a concrete report, not an automatic model substitution.

## Requirements

| Requirement | Implementation and acceptance |
|---|---|
| Use selected Krea2 Genesis for captured-view image editing | S00 |
| Reuse appearance and settings across views/restarts | S01 |
| Reduce duplicated files and present useful history | S02 |
| Select geometry and make fine pixel corrections | S03 |
| Draft descriptions from existing local vision models | S04 |
| Denoise only selected pixels with full-frame context and clear mesh actions | S05 |

## Terms

- Appearance record: owner-approved material/style intent reused across views.
- Capture: a fixed camera, rendered image and reference to a source mesh revision.
- Painting session: one capture and its candidates, grouped in the history UI.
- Face selection: triangle IDs bound to one geometry revision, separate from
  camera-space brush strokes.

## Spokes

| ID | File | Outcome | Depends on | Skills | Write set | State | Commit | Result |
|---|---|---|---|---|---|---|---|---|
| S00 | 00-genesis-edit.md | Enable captured-view editing with selected Krea2 Genesis NVFP4. | none | python:python-core, web:typescript-core | server/reference_models.py, steps/reference.py, ui/src/api.ts, ui/src/ReferenceModels.tsx, ui/src/SurfacePaint.tsx, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/00-genesis-edit.md | done | - | 00-genesis-edit.md#result |
| S01 | 01-appearance.md | Persist reusable appearance separately from view instructions. | S00 | python:python-core, web:typescript-core | server/library.py, server/app.py, ui/src/api.ts, ui/src/SurfacePaint.tsx, steps/paint.py, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/01-appearance.md | done | - | 01-appearance.md#result |
| S02 | 02-storage-history.md | Reference unchanged meshes and remove repeated payloads from new outputs. | S01 | python:python-core, web:typescript-core | server/library.py, server/app.py, server/jobs.py, steps/paint.py, steps/reference.py, steps/_glb.py, ui/src/api.ts, ui/src/workflow.ts, ui/src/main.tsx, ui/src/SurfacePaint.tsx, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/02-storage-history.md, server/blender_client.py, server/look.py, server/thumbs.py, steps/_common.py | done | - | 02-storage-history.md#result |
| S03 | 03-face-selection.md | Combine face selection with precise brush corrections. | S02 | python:python-core, web:typescript-core | steps/paint.py, steps/_paint_mask.py, ui/src/viewer/Viewer.ts, ui/src/SurfacePaint.tsx, ui/src/surface-paint.css, ui/src/main.tsx, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/03-face-selection.md, ui/src/PaintSelection.tsx, server/library.py | done | - | 03-face-selection.md#result |
| S04 | 04-local-description.md | Offer editable, on-demand local descriptions of captures. | S03 | python:python-core, web:typescript-core | server/reference_models.py, server/jobs.py, server/app.py, steps/describe.py, ui/src/api.ts, ui/src/SurfacePaint.tsx, model-bindings.local.json, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/04-local-description.md, server/presets.py, ui/src/workflow.ts | done | - | 04-local-description.md#result |
| S05 | 05-masked-projection.md | Preserve full-frame context while incrementally painting selected mesh surfaces. | S04 | python:python-core, web:typescript-core, art:texture-painting-core | steps/reference.py, steps/_paint_mask.py, steps/paint.py, ui/src/workflow.ts, ui/src/SurfacePaint.tsx, ui/src/main.tsx, ui/src/surface-paint.css, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/05-masked-projection.md, ui/src/viewer/Viewer.ts, ui/src/PaintSelection.tsx, scratch/lanes/fibo2/ui | done | - | 05-masked-projection.md#result |

## Reading rule

Read this index, the executing spoke and named dependency RESULT sections.
Expected turns: S00 16, S01 12, S02 20, S03 20, S04 12, S05 24. Standing 256-turn breaker and
2250000-token implementation ceiling remain; no wall-clock cap. These are scoped
units, not instructions to create chats or delegate.

## Non-goals

Automatic retopology, rebuilding original Blender quads from GLB triangles,
automatic mesh/UV migration, automatic caption replacement, new model downloads,
persistent vision services, content-addressed storage or hash sweeps, and a broad
library migration.

## Open questions

- Deferred: permanent cleanup. Reason: automatic approval blocked the action.
  Resume trigger: the approval block is resolved or the owner deletes the scoped
  Trash entries manually. D2 already authorizes deletion; do not ask again.
