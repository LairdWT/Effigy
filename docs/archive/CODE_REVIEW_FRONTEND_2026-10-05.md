# Frontend and 3D viewer review — 2026-10-05

## Scope and status

Reviewed the frontend workflow, job tracking, asset selection, rigging controls, and 3D viewer. Source baseline: `149d791`. The frontend files were unchanged during this review.

Read `ui/src/main.tsx`, `ui/src/api.ts`, `ui/src/events.ts`, `ui/src/workflow.ts`, `ui/src/viewer/Viewer.ts`, the browser tests and configuration, and the project architecture, implementation, handover, and UI proposal markdowns. Checked relevant installed three.js implementation details and official documentation.

**Seven findings: one high, five medium, one low.** No application fixes were applied. The browser probes used mocked API responses and Blender connectivity. One existing GLB was read for resource-lifecycle testing; no library asset was modified.

## Findings

### 1. HIGH — Marker placement misses the back surface and puts joints on the front surface

**Location:** `ui/src/viewer/Viewer.ts:244–252` (`pick`).

The placement calculation averages the first hit with the next distinct hit, assuming those are the body's entry and exit surfaces. However, raycasting uses the mesh's material sidedness. With the normal front-sided material, the exit surface is culled. The fallback then averages the first hit with itself.

**Reproduction:** Click the center of a closed box spanning −1 to +1 on each axis, viewed from the front. The actual method returns approximately `[0, 0, 1]`; the expected interior midpoint is `[0, 0, 0]`. Repeating with double-sided intersection detection returns the expected midpoint. Existing generated and rigged GLBs inspected during the review explicitly have `doubleSided: false`, so the triggering material configuration occurs in the project.

**Impact:** Manual corrections can move a marker from inside a character onto its visible surface. Saving those positions changes the skeleton inputs and can harm the subsequent skinning result.

**Recommendation:** Gather intersections from both sides for placement while preserving the displayed materials. Pair an entry with the appropriate exit on the same body component, and handle missing or ambiguous exits explicitly.

The default culling behavior is documented in the official [Raycaster reference](https://threejs.org/docs/pages/Raycaster.html).

### 2. MEDIUM — Roughness, metallic, and AO inspection ignore bone movement

**Location:** `ui/src/viewer/Viewer.ts:16–21` (`ORM_SHADER`).

The custom vertex shader directly transforms the original `position` attribute. It does not apply skinning, unlike the standard materials used by the other views.

**Reproduction:** Render a synthetic skinned box into a 128 × 128 render target, then move its controlling bone one unit along X. The material view changes 6,144 RGBA channel values. The roughness view changes **zero**. The shader uploaded to WebGL contains the direct position transform and no skinning transform. Metallic and AO use the same shader.

**Impact:** Switching an animated character to one of these inspection modes shows its undeformed geometry while its skeleton continues moving. That makes inspection misleading.

**Recommendation:** Preserve the standard deformation path when implementing channel views, or include the required skinning shader chunks. Cover an actually posed skinned mesh in the viewer checks.

### 3. MEDIUM — Weight inspection overwrites the mesh's original vertex colors

**Location:** `ui/src/viewer/Viewer.ts:309–326` (`setWeights`).

The heatmap replaces the geometry's `color` attribute. Turning weights off restores the original material, but does not restore the original attribute. A material that uses vertex colors therefore continues reading heatmap colors.

**Reproduction:** Load a skinned box whose original vertex colors are red and whose original material has `vertexColors: true`. Inspect an unused bone, then turn weights off. The original material is restored and still uses vertex colors, but the first vertex's color changes from `[1, 0, 0]` to approximately `[0, 0.04, 1]`.

**Impact:** Imported vertex-colored models display altered colors after inspection until reloaded. The saved GLB is unaffected; this is a mutation of the loaded preview geometry.

**Recommendation:** Preserve and restore the original color attribute. Keep a reusable heatmap buffer separate from it; update that buffer when the selected bone changes instead of allocating a new buffer and a `Color` object per vertex every time.

### 4. MEDIUM — Resuming quad preparation halves the effective validation budget

**Locations:** `ui/src/main.tsx:1408–1419` and `ui/src/main.tsx:1151–1153`.

An uninterrupted quad preparation pass correctly validates against twice the quad count. A resumed pass reads only the ancestor remesh's `params.faces`, losing `params.topology`. The standalone check button makes the same assumption. The remesh step explicitly stores quads as triangle pairs in GLB.

**Reproduction:** Open a checkpoint with `params: { faces: 10000, topology: "quad" }` and click Continue preparation. Captured requests:

```json
[
  { "step": "uv", "parent": "020_remesh", "params": {} },
  { "step": "validate", "parent": "030_uv", "params": { "max_triangles": 10000 } }
]
```

The equivalent uninterrupted pass uses `max_triangles: 20000`.

**Impact:** A model within its chosen quad budget can receive an incorrect triangle-budget warning after resuming or checking a descendant version.

**Recommendation:** Convert the nearest remesh budget to triangles using both `faces` and `topology`, and reuse that conversion for continuation and standalone checks.

### 5. MEDIUM — Rigging controls allow duplicate job submission

**Locations:** `ui/src/main.tsx:939–945`, `ui/src/main.tsx:2094–2095`; related controls at lines 1941, 2114, and 2140.

The rigging submission path directly calls `api.run()` without the `useBusy()` guard used by the guided generation/preparation controls. Fit a skeleton, Skin it, Add animations, and Save markers share this unguarded path.

**Reproduction:** Double-click Fit a skeleton with the endpoint mocked. Two POSTs are submitted, both using parent `010_upload`, and two distinct jobs are tracked.

**Impact:** An ordinary click burst can enqueue duplicate expensive work and create redundant versions. The global backend lock serializes that work but does not remove the duplicate submissions.

**Recommendation:** Apply the existing submission guard to this path and disable the corresponding action while the submission is pending. Extend the existing click-burst browser coverage to rigging controls.

### 6. MEDIUM — Static previews continuously redraw

**Locations:** `ui/src/viewer/Viewer.ts:94` and `ui/src/viewer/Viewer.ts:388–395`.

The viewer starts an unconditional animation loop. Every tick updates controls, clears the renderer, draws the scene, and draws the axis helper, even with no animation or interaction. The canvas also remains mounted beneath reference images and concept overlays.

**Measurement:** A stationary test mesh with zero animation clips generated **70 renderer passes in one idle second**, counting the scene and helper, in headless Chromium using SwiftShader. This establishes redundant rendering; it is not an RTX frame-rate benchmark or an inference speedup measurement.

**Impact:** The UI spends CPU/rendering resources on unchanged frames. This is a useful optimization for an application that also performs expensive model inference, though any resulting inference improvement needs a separate measurement on the actual browser/GPU configuration.

**Recommendation:** Render on changes to the model, view settings, markers, camera, or size. Continue scheduling frames only while animation, camera damping, or a helper transition is active. Stop unnecessary rendering when the viewport is covered or hidden. The official [rendering-on-demand guide](https://threejs.org/manual/pages/rendering-on-demand.html) includes the damping and frame-scheduling considerations.

### 7. LOW — Clearing a skinned model leaves its bone texture allocated

**Location:** `ui/src/viewer/Viewer.ts:270–281` (`free`).

Cleanup disposes geometry, materials, and material textures, but does not dispose the skeleton. A skinned mesh's bone texture belongs to its skeleton, so it is not found by enumerating material properties.

**Reproduction:** Load, render, and clear `library/m17_dwarf_turnaround/110_rig_skin/rigged.glb` three times in the same viewer. After each clear, `renderer.info.memory.textures` reports **8, 9, 10** respectively. One additional texture remains allocated per cycle.

**Impact:** Repeated skinned-model switches accumulate GPU resources. The observed per-skeleton texture is small; this finding does not establish a large VRAM leak or quantify inference impact.

**Recommendation:** Dispose each unique skeleton once its meshes are no longer in use, including superseded loads. Account for skeleton sharing. See the official [object disposal guide](https://threejs.org/manual/pages/how-to-dispose-of-objects.html).

## Verification

Run from `ui/`:

```powershell
npm run build
npx playwright test
```

Results:

- Build passed, including TypeScript checking and Vite bundling.
- Existing browser suite: **6 passed in 24.4 seconds**.
- Additional isolated browser probes established the observations above. The shader check included rendered pixel comparisons, and the quad-budget and duplicate-submission checks captured actual frontend requests.

The probes used a temporary Vite server, mocked API routes, and headless Chromium with software WebGL. Both probe servers and browsers were closed in `finally` blocks. The probe harnesses ran from standard input and were not added to the repository. No live Blender commands, inference jobs, model downloads, or CI runs were triggered.

The existing smoke suite does not cover these rigging, skinned-view, and resource-lifecycle cases. Passing it does not invalidate the additional reproductions.

## Suggested follow-up

1. Fix marker placement and the two inspection correctness issues.
2. Correct quad-budget conversion and guard rigging submissions.
3. Implement rendering on demand and measure its effect under the normal browser/GPU configuration.
4. Complete skeleton resource disposal.

Implementation remains a separate task requiring a request to fix the findings.

## Outcome (2026-10-05, same day)

All seven held against the current code and were implemented (by the `lt2-worker` agent, reviewed by the
lead) on branch `review-fixes`; `npm run build` and the Playwright suite (6/6) pass.

1. `pick` raycasts with every material set to `DoubleSide` for the duration of the cast and restores the
   sides after; entry/exit pairing and the single-hit fallback unchanged.
2. The ORM vertex shader includes three.js's skinning chunks (three 0.186).
3. `setWeights` keeps the geometry's own `color` attribute aside and restores (or deletes) it when
   weights go off; one reusable heatmap buffer per geometry.
4. `triBudget` / `budgetOf` are the single quad-to-triangle conversion, used by the uninterrupted pass,
   the continuation and the standalone check.
5. The rig buttons (Fit a skeleton, Skin it, Save markers, Add animations) go through `useBusy()` and are
   disabled while a submission is pending.
6. Render on demand: a `dirty` flag set by every change to the picture (`OrbitControls` "change" covers
   damping); frames render continuously only while a clip plays or the view helper animates.
7. `free` disposes each unique skeleton once.

Not re-measured: the idle render count and the texture count across clears; no new browser tests for the
rig buttons or the skinned channel views (the review's probes were not added to the repository).
