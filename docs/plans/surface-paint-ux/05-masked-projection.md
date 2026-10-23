# Incremental masked projection painting

Spoke: S05
Outcome: Preserve full-frame context while incrementally painting selected mesh surfaces.
Depends-on: S04
Decisions: D3, D4, D7, D8
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, web:typescript-core, art:texture-painting-core
Read-set: INDEX.md, 00-genesis-edit.md#result, 03-face-selection.md#result, CODE.md, steps/reference.py, steps/paint.py, steps/_paint_mask.py, ui/src/SurfacePaint.tsx, ui/src/workflow.ts
Write-set: steps/reference.py, steps/_paint_mask.py, steps/paint.py, ui/src/workflow.ts, ui/src/SurfacePaint.tsx, ui/src/main.tsx, ui/src/surface-paint.css, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/05-masked-projection.md, ui/src/viewer/Viewer.ts, ui/src/PaintSelection.tsx, scratch/lanes/fibo2/ui
State: done

## Context

S03 restricted UV writeback but did not restrict diffusion. The owner wants
incremental painting with the entire fixed view as context, preserving good areas
while adding or healing adjacent surfaces. Current source is owner version 136.

## Evidence

- Native comfy.sample.sample accepts noise_mask. KSamplerX0Inpaint restores
  protected latents during sampling; DifferentialDiffusion schedules soft masks.
- Legaia routes projection healing to full-frame diffusion with separate sampler
  and final UV-write masks. Texture-painting guidance informs preservation and
  edge treatment; its brush workflow is not the diffusion implementation.
- `steps/reference.py:162` previously parsed paint_mask without passing it to the sampler.
- Reference children of captures previously replaced the main mesh with an image.

### Runtime observations

Capture d71b2b214b4b -> 137_paint references owner mesh 136 without copying it.
UI job 597200d61f39 -> 138_reference used Genesis, seed 24026, eight steps,
denoise 0.35 and an eight-pixel inward blend. The full 1024 frame was encoded;
16392 pixels were selected, 15743 changed, zero changed outside the mask.
Projection cdf614c1ad4a -> 139_paint changed 7679 permitted atlas texels.

Final code also retains the capture's RGBA, including transparent background.
Job d3998aeeb635 -> 140_reference intersected the brush with triangle 53 and
an erase dab. Its 4266 selected pixels contained only triangle 53; the erased
point was excluded. Exactly 3499 preview pixels changed, zero outside or alpha
changes. Genesis used 13.51 GiB peak allocated CUDA memory and took 174.84s,
including 60.83s sampling. Its 256 NVFP4 layers retain full-precision matmul.
No model payloads, native engine files or environments were changed.

Projection f5f280611d76 -> 141_paint changed 1911 texels within 1968 permitted
texels, with zero outside, alpha or gutter changes. Independent decoded reads
confirmed 1024 RGBA16, all four geometry/UV accessors identical to 136, and one
embedded image. Baked before/after renders were inspected: localized roof marks
change while windows, chimney, walls and silhouette remain. This demonstrates
tool behavior, not final artistic acceptance. Both projections branch from 136.
Attempt 0585d632ac9d to expand the final candidate to the whole surface failed
with the actionable regenerate-preview message and published no version.

Browser capture workspace displayed the new incremental method and numbered
actions. Brush coordinates, prompt and Generate were exercised there. Browser
control then became disabled in Work settings; final projection used Effigy's
normal local API. Post-build candidate navigation is source/build verified, not
claimed as a later live-browser observation. Backend connections observed were
loopback and the native worker had no TCP connections at the observation; this
does not establish OS-level network containment.

### Camera and mask correction

Owner reported camera resets and inverted-feeling masks after trying the lane.
`ui/src/viewer/Viewer.ts:371` framed every loaded GLB, including captured aliases
and new painted versions. `ui/src/SurfacePaint.tsx:31` selected the whole view for
new masks. Backend white masks already denote writable pixels; they were not
inverted. The UI now starts empty and labels green as paint, clear as preserve.
Triangle selection from an empty mask selects those faces directly; clearing the
paint mask clears the triangle boundary too. Existing saved masks retain meaning.

The viewer now keeps exact camera position/target/up on same-asset mesh reloads,
remembers it across workspace remounts, restores stored capture angles on an
initial capture open, and exposes an explicit Captured angle control. Normal UI
rerenders do not reload the model. Captured yaw/pitch retain five decimal places.
The same changes were applied to the isolated FIBO UI while preserving its model
choices and native mask wording. Both offline TypeScript/Vite builds passed.
Browser control is disabled in Work settings, so live click/orbit requalification
could not be performed. No server restart, model run, stored-mask inversion or
asset/texture mutation was used for this correction.

## Steps

1. Resolve the capture selection using geometry-bound faces, strokes and alpha.
2. Use the complete encoded capture and a graded differential sampler mask.
   Composite the preview independently to preserve exact protected pixels.
3. Constrain projection to the generated footprint and original face selection,
   retaining visibility, UV ownership, alpha, geometry and atlas-size guards.
4. Keep previews beside the mesh and make Generate Preview and Project onto Mesh
   explicit primary actions. Retain explicit legacy full-view editing.
5. Run bounded ordinary capture, masked Genesis preview and projection from 136.
   Inspect the baked result and preserved pixels; record job references here.

## Files to touch

- steps/reference.py
- steps/_paint_mask.py
- steps/paint.py
- ui/src/workflow.ts
- ui/src/SurfacePaint.tsx
- ui/src/main.tsx
- ui/src/surface-paint.css
- docs/LOCAL-SETUP.md
- docs/plans/surface-paint-ux/05-masked-projection.md

- ui/src/viewer/Viewer.ts
- ui/src/PaintSelection.tsx
- scratch/lanes/fibo2/ui

## Verification

1. Targeted Ruff, offline UI build and plan structure: expect no errors.
2. Ordinary application samples and decoded output inspection: expect changed
   selected pixels, zero protected-pixel/alpha changes and identical geometry/UV
   accessors. No tests, hashes or extra reports.

## Risks

Latent masking alone cannot ensure decoded pixel identity; final compositing and
UV guards are independent. Expanding a mask after generation requires a new
preview. Qwen instruction editing retains explicit full-view behavior until its
masked route is separately implemented and qualified. NVFP4 storage does not
establish native FP4 matrix multiplication or artistic acceptance.

## RESULT

Implemented and runtime-qualified with selected Genesis. Final preview 140 and
mesh 141 preserve protected pixels, alpha, 1K RGBA16 and exact geometry/UVs.
Face/brush intersection, erase exclusion and wider-selection rejection worked.
Generate ran through the numbered UI action; projection used the local API after
browser control became unavailable. Candidate mesh navigation has source/build
proof; later live-browser inspection remains unavailable. Ruff, TypeScript/Vite
and plan checks passed. No tests, hashes, downloads, commits or shared-model edits.
Camera/mask correction: same-asset view retention, explicit captured angle and
empty paint masks added to both UIs; both builds pass. Live browser recheck is
unavailable. See Evidence for measurements and limits.
