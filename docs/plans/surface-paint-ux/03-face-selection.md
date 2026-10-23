# Combine face selection and fine mask editing

Spoke: S03
Outcome: Combine face selection with precise brush corrections.
Depends-on: S02
Decisions: D1, D3
Constraints: C1, C2, C3, C4, C5
Skills: python:python-core, web:typescript-core
Read-set: INDEX.md, 02-storage-history.md#result, CODE.md, ui/src/viewer/Viewer.ts, steps/paint.py, steps/_paint_mask.py
Write-set: steps/paint.py, steps/_paint_mask.py, ui/src/viewer/Viewer.ts, ui/src/SurfacePaint.tsx, ui/src/surface-paint.css, ui/src/main.tsx, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/03-face-selection.md, ui/src/PaintSelection.tsx, server/library.py
State: done

## Context

Face selection establishes a reliable surface boundary. Brush editing still
matters: one large wall triangle can contain several small defects. Support both
without forcing the owner to trace architectural edges by hand.
Use the owner-invoked project `blender-core` guidance for source geometry and
projection boundaries; this unit does not modify the owner's Blender session.

## Evidence

Baseline anchors describe the pre-implementation behavior.

- `ui/src/SurfacePaint.tsx:64` stores brush strokes; its current editor has no
  geometry selection or image zoom/pan.
- `ui/src/viewer/Viewer.ts:198` already owns a Three.js raycaster;
  line 673 intersects the mesh for marker placement. Add a distinct paint mode
  rather than overloading rig controls.
- `steps/paint.py:231` resolves visible triangle IDs; line 259 intersects
  permission with visibility, framing and normal facing.
- The current GLB contains triangles. Blender's original quad/n-gon identity is
  not retained as an established interface.

### Runtime observations

Implemented and qualified on 2026-10-20. Explicit triangle add/remove and hover
highlight work in the capture and 3D viewport. Capture face maps use the native
frontmost triangle raster; writeback also intersects exact UV-owner IDs, camera
visibility, facing and inward feathering. Native trimesh triangle/vertex ordering
was inspected against the hut's raw GLB accessors and matched exactly. Geometry
identity follows only operations promising unchanged topology/UVs; no hashes.

Named Roof detail selection was saved on front capture 123 and explicitly loaded
on rear capture 124/description 131. Browser-selected roof faces highlighted in
the 3D viewer; add/remove and undo/redo changed the visible counts correctly.
Zoom/scroll pan, brush exclusion, keyboard lasso vertices and draft reload were
exercised. Enlarged and inline editors share undo history. Stored selections
contain geometry-bound IDs; view pixels stay with their capture.

Normal application job 3c81a8ca131c -> 129_paint used IDs 6/53 and a small erase
stroke; 940f4239ca2f -> 132_paint used ID 53 and a saved/reloaded triangular lasso
exclusion. The latter changed 2068 permitted texels, zero outside pixels, zero
alpha, and no gutters; both retained 409 triangles and 1024 RGBA16 textures.
A stale-revision application (1707a8255792) returned bad_params with 'Face selection
belongs to different geometry; select faces again', publishing no version.
Legacy brush-only recipes remain readable, without forced model/style conversion.
These selections protect application, not the diffusion process itself. Source
checks and UI build passed.

## Steps

1. Add an explicit Select faces mode with visible hover/highlight, add/remove,
   clear and undo. Keep orbit and rig editing distinct. Start with individual
   triangles; label them honestly rather than promising original Blender polygons.
2. Bind face IDs to the immutable geometry revision and source primitive ordering.
   Carry them between texture-only revisions and camera angles. A reimport,
   remesh or changed UV/topology invalidates selection with a visible explanation.
   Do not identify geometry through runtime hashes.
3. Rasterize selected faces through the fixed capture camera, retaining existing
   occlusion and facing guards. Hidden faces must not become writable merely
   because they are selected.
4. Add zoom/pan, lasso and smaller brush corrections with undo/redo. Keep pointer
   coordinates normalized to the original capture, independent of zoom.
5. Combine the face boundary and brush/lasso corrections explicitly. Brush edits
   refine the selected surface; painting another face requires adding it first.
   Show the final write mask before generation/application.
6. Expose copyable named surface selections only within the same geometry
   revision. Keep masks out of global appearance text. Preserve old brush-only
   recipes and keyboard-accessible controls.

## Files to touch

- steps/paint.py
- steps/_paint_mask.py
- ui/src/viewer/Viewer.ts
- ui/src/SurfacePaint.tsx
- ui/src/surface-paint.css
- ui/src/main.tsx
- docs/LOCAL-SETUP.md
- docs/plans/surface-paint-ux/03-face-selection.md

- ui/src/PaintSelection.tsx
- server/library.py

## Verification

1. `.venv/Scripts/ruff.exe check steps/paint.py steps/_paint_mask.py` and
   `npm --offline --prefix ui run build`. Expected: pass.
2. Ordinary hut UI: select roof triangles, exclude vent, zoom and correct an edge,
   undo/redo, then capture another angle. Expected: geometry selection remains
   aligned and view-specific pixels do not migrate to the wrong surface.
3. Apply one localized candidate. Expected: selected visible texels change;
   unselected wall/chimney/vent and occluded regions remain unchanged.
4. Reopen a legacy brush recipe and a geometry-changed disposable copy. Expected:
   old recipe works; stale face IDs fail clearly instead of being reassigned.

## Risks

Triangle ordering may differ between the browser loader and worker; prove the
mapping on the real hut before application. Coplanar grouping can cross a feature
boundary, so it is deferred. Better masks do not turn full-frame FLUX generation
into true masked inpainting; retain the current explanation.

## RESULT

Implemented and qualified. Image/3D triangle picking, highlight, add/remove, named selections, zoom/pan, brush/lasso and undo/redo work. Named Roof detail carried between angles. Saved/reloaded lasso job 940f4239ca2f -> 132_paint changed 2068 permitted texels, zero outside/alpha pixels; 409 triangles and 1K RGBA16 remained. Native triangle order matched GLB. Stale geometry job 1707a8255792 failed clearly without publishing. Legacy brush recipes remain readable. Ruff/UI build pass. Runtime observations above hold the detailed ordinary references.
