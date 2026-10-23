# Reduce repeated payloads and organize painting history

Spoke: S02
Outcome: Reference unchanged meshes and remove repeated payloads from new outputs.
Depends-on: S01
Decisions: D1, D2, D3
Constraints: C1, C2, C3, C4, C5
Skills: python:python-core, web:typescript-core
Read-set: INDEX.md, 01-appearance.md#result, CODE.md, server/library.py, steps/paint.py, steps/reference.py, ui/src/workflow.ts
Write-set: server/library.py, server/app.py, server/jobs.py, steps/paint.py, steps/reference.py, steps/_glb.py, ui/src/api.ts, ui/src/workflow.ts, ui/src/main.tsx, ui/src/SurfacePaint.tsx, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/02-storage-history.md, server/blender_client.py, server/look.py, server/thumbs.py, steps/_common.py
State: done

## Context

Reduce future storage growth before adding more capture data. Existing versions
remain readable. This unit is not permission to purge Trash through another route.
The cleanup already performed and blocked purge are recorded in the index.

## Evidence

Baseline anchors describe the pre-implementation behavior.

- `steps/paint.py:187` copies the entire source GLB into every capture. Version
  122 duplicates the 5.76 MiB mesh of 119.
- `steps/paint.py:140` appends the new atlas without dropping the previous image.
  Source 104 has one embedded image; 119 has two, with base color using only
  image 1. Another capture then copies both.
- `steps/reference.py:272` saves additional image and preview files. Version 111
  contains three 739213-byte PNGs from the same generation.
- `server/library.py:335` traces deletion through parents only. The applied
  paint also depends on `params.image` (119 references 111), so parent-only
  deletion does not capture every dependency.
- `ui/src/main.tsx:1546` resolves the displayed mesh through `source()`.

### Runtime observations

Earlier cleanup, moved here from the index when S05 was added: the hut held
122 versions / 1402.96 MiB. Normal deletion moved 96 superseded versions into
38 recoverable Trash groups, retaining 26 versions / about 249.35 MiB. Selected
Trash payload: 1209649031 bytes (1153.61 MiB). Required ancestors and image
dependencies were checked before moving. Retained versions were 001, 002, 083,
084, 086, 087, 088, 090, 091, 093, 094, 096, 097, 099, 103, 104, 106, 108, 111,
114, 115, 117, 119, 120, 121 and 122. This preserved retail source, Blender
authoring files, owner geometry, UV milestones, current inputs and exports.
Scratch and other assets were not selected. Automatic approval rejected permanent
deletion with "blocked by policy"; no alternative deletion was attempted and
reclaimed bytes remained zero. The groups remain scoped by the hut ID and dates
20261020T182051 through 20261020T182100; unrelated Trash is excluded.

Implemented and qualified on 2026-10-20. Library-owned output_refs resolve only
same-asset saved versions, reject cycles/escapes/missing inputs, and retain legacy
local outputs. Worker publication validates aliases. File serving, worker input,
Blender lookup, look/turntable and thumbnail mesh lookup use that owner. Captures
store camera/image/face-map metadata, with no GLB copy. Reference image and preview
aliases share image_0.png. New atlas writes compact referenced GLB resources;
unknown extension references fail instead of being guessed.

Jobs a856eab7fff7 -> 123_paint and 8ee3a9ddc974 -> 124_paint contain no GLB;
measured folders were 775873 and 788478 bytes. Both reopen in the UI using the
119 mesh. Candidate 128 contains one PNG plus metadata. Applied immutable
branches 129 (3c81a8ca131c) and 132 (940f4239ca2f) each contain one embedded image;
GLBs are 3120192 and 3120312 bytes versus source 119's 6043088 bytes/two images.
All four geometry/UV accessors in 129 equal source values exactly. The repeated
apply proof uses two branches from the retained source, not an extra GPU reroll.

Export 7c1c8434746a -> 130_export reopened through c2974157e8e1 as
rim_elm_hut_surface_tools_reopened/002_import_model. It retains 409 triangles,
exact 1227 face-corner position/UV tuples, and an identical decoded 1024 RGBA16
atlas. Import merged four duplicate vertices (562 -> 558); this is a new geometry
revision and old triangle selections are not inherited.

UI History groups captures with candidates/descriptions, retaining full expansion
and stars. Deletion previews for 111 and 128 identify their retained paint users;
128 is protected by 129 and 132. Starred versions and active job dependencies are
also guarded. The previews do not delete or claim reclaimed bytes. Earlier 38
Trash groups remain; this unit did not retry the previously blocked purge.
Ruff and UI build passed. The scoped AEP standards report remains advisory:
whole-file typing findings and unavailable TypeScript lint provider remain under
the accepted baseline deviation; it is not reported as passing.

## Steps

1. Add explicit same-asset output/source references owned by the library resolver.
   Keep legacy local-file outputs valid; reject cycles, missing sources and paths
   outside the library. Update viewer and worker callers together.
2. Store capture image, camera and source revision without a copied GLB. Reuse the
   exact source mesh through the resolver. Verify normal preview and continuation.
3. Make reference output aliases point to one full-resolution image. Generate a
   smaller preview only where required, instead of another full-size payload.
4. Write supported painted GLBs with the current atlas and all still-referenced
   data. Remove obsolete atlas payloads only in the new output. Preserve geometry,
   UV and other material bytes; fail clearly for unsupported extension references.
5. Present captures/candidates as an expandable painting session under a checkpoint.
   Keep full history accessible. Pinning and an explicit keep/discard review make
   retention intentional; no automatic expiry or loss of unsaved drafts.
6. Extend cleanup dependency analysis to source references, image inputs, active
   jobs and pinned versions. Show exact affected versions and bytes before any
   cleanup. Distinguish moving to Trash from permanently reclaiming space.

## Files to touch

- server/library.py
- server/app.py
- server/jobs.py
- steps/paint.py
- steps/reference.py
- steps/_glb.py
- ui/src/api.ts
- ui/src/workflow.ts
- ui/src/main.tsx
- ui/src/SurfacePaint.tsx
- docs/LOCAL-SETUP.md
- docs/plans/surface-paint-ux/02-storage-history.md

- server/blender_client.py
- server/look.py
- server/thumbs.py
- steps/_common.py

## Verification

1. `.venv/Scripts/ruff.exe check server/library.py server/app.py server/jobs.py steps/paint.py steps/reference.py steps/_glb.py`
   and `npm --offline --prefix ui run build`. Expected: pass.
2. Two ordinary captures from one hut checkpoint. Expected: independent camera
   metadata/images, no new GLB copies, both views reopen correctly.
3. Apply twice on a disposable hut copy and export/reopen. Expected: 409 triangles,
   unchanged UVs/precision, one current base-color payload rather than accumulated
   old atlases. Inspect file lengths and GLB references without hashing.
4. Cleanup preview against a retained candidate dependency. Expected: identifies
   that dependency and refuses an operation that would break it. No purge is
   performed merely for verification.

## Risks

Hidden aliases can break exports, deletion or older tools. A reference must be
resolved by one owner. Repacking GLB byte ranges requires exact accessor and
extension accounting; unsupported layouts must retain the old safe path.

## RESULT

Implemented and qualified. Captures 123/124 contain no copied GLB; 128_reference has one PNG. Applied branches 129/132 each hold one embedded atlas (3120192/3120312 bytes versus 6043088 before). Export 130 reopened as rim_elm_hut_surface_tools_reopened/002_import_model: 409 triangles, exact face-corner position/UV tuples and decoded RGBA16 pixels. History grouping and dependency-aware deletion preview work; 128 remains protected by 129/132. No old Trash was purged. Ruff/UI build pass; AEP whole-file typing and unavailable web-lint findings remain advisory under the accepted deviation. See Runtime observations above.
