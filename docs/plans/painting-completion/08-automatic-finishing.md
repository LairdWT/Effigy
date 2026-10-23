# Automate seam finishing on the assembled mesh

Spoke: S08
Outcome: Automate seam planning, bounded repair and one final draft review
Depends-on: S07
Decisions: D1, D3, D4, D5, D6, D7
Constraints: C1, C2, C3, C4
Skills: python:python-core, powershell:powershell-core, web:typescript-core, planning:planning-core, art:texture-painting-core, art:art-3d-realtime-core
Read-set: docs/plans/painting-completion/INDEX.md, docs/plans/painting-completion/07-replacement-projection.md#result, steps/_paint_seams.py, steps/_paint_projection.py, server/paint_sessions.py
Write-set: server/finish_contracts.py, server/paint_sessions.py, server/paint_routes.py, server/jobs.py, server/presets.py, server/library.py, steps/_paint_seams.py, steps/_finish_plan.py, steps/_finish_cut.py, steps/paint_finish.py, steps/paint_finish_generate.py, steps/paint_generate.py, tools/native_reference_entry.py, tools/stage_multi_view_trial.py, ui/src/AutomaticFinish.tsx, ui/src/MultiViewPaint.tsx, ui/src/multi-view-api.ts, scratch/lanes/fibo2, docs/plans/painting-completion
State: done

## Context

The owner approved execution after reviewing this plan. The source remains immutable; the user reviews one completed draft. Expected turns24 for implementation and ordinary runtime qualification. Initial qualification bound: three repair patches plus one diagnosed correction for the entire pass; no whole-house model rerolls.

The native goal tool refused a new goal because the thread retains an unfinished blocked goal. That existing objective already covers this work, but its native status cannot be resumed through the available tool. S08 tracks this execution durably; the tool limitation and historical cleanup do not block implementation. No prior goal is falsely marked complete to free the slot.

Later on2026-10-22 the app resumed that existing native goal; the earlier tool refusal is historical.

The caller asset profile is the verified static409-triangle, unique square1024 RGBA16 atlas, retaining current UV allocation and density. This task does not create a new density, unwrap or shader profile. The project-local3dgen-core route supplies front-most ownership, full-context editing and immutable checkpoint boundaries; the Effigy session API remains the actual caller-owned state surface.

## Evidence

steps/_paint_seams.py:42 currently detects camera-owner changes and colour discontinuities only in a manually chosen camera. It does not choose cameras or run repairs. steps/_paint_set.py:350 owns the combined bake. S07 confirms residual detail and duplicate feathering as compositor defects, but its saved-image rebakes retain mismatched mortar, scale and some invented features originating in model outputs. A coverage map or low colour error alone cannot establish coherent artwork.

The observed model roles differ. Genesis NVFP4 produced the owner's preferred foundation227; FIBO INT8 blank-region editing produced the retained local repairs; MOSS Turbo was faster in sampling but its whole-house result retained larger continuity defects. MOSS sampling times exclude substantial loading time. The current268 branch mixes all three models and cannot serve as a clean comparison of a single model variation.

Moirai decision,2026-10-22: independent Clotho and Lachesis packets followed by Atropos used owner-selected gpt-6-sol/max, overriding the skill's older gpt-5.6-sol pin. No role wrote artifacts or changed source. Selected: A, bounded integer-CSR s-t mincut with fixed generated core and protected source exterior, real surface adjacency across split UVs, connected boundary and baked review. Conditional: B, finite hard inward contours only under the same checks; no averaging fallback. Already-covered: C, camera-owner reassignment as a supplement rather than the finisher. Atropos confidence7/10; peer tallies7/9 and6/8 verified each cap confidence at7. Cut quality and neighbouring-view continuity remain runtime qualification items.

## Steps

1. Start from one assembled mesh and one authoritative UV selection. Read camera-writer history and actual geometry adjacency across split UV vertices. Build a surface-space graph of candidate discontinuities, including later repair boundaries. Keep material boundaries, openings, silhouettes and named protected face groups out of the repair core. Unknown boundaries remain flagged rather than silently reclassified by the description model.
2. Group nearby defects on the same surface. Score cameras by front-facing support, visibility of both sides, distance from the frame edge and projected texel density. Use the existing camera pool and common scale. Place the seam inside the view, not at a panel edge. Show coverage and unresolved components honestly; do not count unreachable texels as healed.
3. Render each repair from the latest assembled draft, with the complete view as context. The core covers the conflicting feature, not just a one-pixel dividing line. A wider unchanged context region establishes stone scale, mortar and brush direction. The local9B model may suggest wording or flag obvious discrepancies; it never expands paint permission or decides acceptance alone.
4. Use the selected repair model in one held worker and serialize patches. Proposed default: FIBO2 Edit Turbo INT8, four steps, blank-region core and match-capture wording. Keep Genesis available as an explicit alternative. Use the immutable source recipe and seed per patch; never switch models automatically. Load once, release after the batch, and yield when the protected primary lane needs the GPU.
5. Apply generated colours at full strength in the core. In a permitted outer ring, investigate a hard, content-aware boundary where original and generated structure agree; never crossfade two incompatible mortar patterns. Keep the full-view context even if boundary optimization uses a local pixel window. The algorithm must retain exact front-most face ownership and original alpha. If no acceptable boundary exists inside permission, reject that patch and retain the previous draft.
6. Re-render the affected surface and neighbouring angles after each patch. Require unchanged geometry/UVs/alpha/other maps and zero writes outside permission. Check for increased discontinuity, lost material structure, new openings and excessive blur. These diagnostics rank and reject obvious regressions; they do not replace the final visual review. One diagnosed correction is allowed within the initial bound, then stop that component rather than loop indefinitely.
7. Persist completed patch images, masks, seeds, camera bindings and source references once. Keep working mesh/atlas processing on D:. Reconstruct an interrupted draft from the immutable source and completed patch operations; do not regenerate finished patches. Publish one final GLB and one360 review, with intermediate operations referencing source geometry. No per-patch copied GLBs, automatic historical deletion or NAS fallback.
8. Add **Finish seams automatically** with a visible patch budget, model, protected selection and progress. Cancellation preserves completed patches. End at one before/after draft review with remaining defects identified. **Apply** references that reviewed final output; no automatic replacement of the source.

## Files to touch

- server/finish_contracts.py
- server/paint_sessions.py
- server/paint_routes.py
- server/jobs.py
- server/presets.py
- server/library.py
- steps/_paint_seams.py
- steps/_finish_plan.py
- steps/_finish_cut.py
- steps/paint_finish.py
- steps/paint_finish_generate.py
- steps/paint_generate.py
- tools/native_reference_entry.py
- tools/stage_multi_view_trial.py
- ui/src/AutomaticFinish.tsx
- ui/src/MultiViewPaint.tsx
- ui/src/multi-view-api.ts
- scratch/lanes/fibo2
- docs/plans/painting-completion

## Verification

### Runtime progress

The UI created sessioncbc96d49727e4a81 from268 with the exact271 foundation mask, two patches and one correction. Planning jobs361d71de1790 andbcdf57e48405 produced278 and279. Plan279 includes an actual UV marker bake through the same projection function as finishing:23352 permitted texels, zero outside changes, zero alpha changes. Its cores span15 and12 faces; wooden treads, walls and roof stay outside the selected foundation. The26-camera pool reaches92221 of92255 selected texels and5435 of5469 seam pairs;34 unseen texels and34 unreachable pairs are reported. Planned patches usev12(yaw295,pitch-45) andv06(yaw25,pitch0), one common center/extent.

Refreshing the plan through the API exposed stale state in the new idle UI panel. Its Run action correctly returned409 without allocating inference. An event/reconnect subscription now refreshes the panel's versioned state; the offline build passes. This is a UI lifecycle correction, not a model-quality retry.

Foundation job1e2645a74812 completed as durable draft280 and metadata-only wrapper281. One held FIBO worker made three generations: p00 retained, p01 rejected, and its one correction rejected. First sampling54.15s, warm samples1.59s and1.61s; loading is recorded separately. Runtime: FIBO2 Edit Turbo INT8,215 quantized layers, BF16 compute, engine0.42.0, Torch2.10/CUDA13, peak15.023GiB. Retained p00 reduced measured seam error102.55 to42.51 RGB8, with a connected hard boundary; all three neighbouring baked views passed regression checks. Final draft preserves409 triangles, geometry/UV arrays,1024 RGBA16, alpha and other maps, with zero writes outside permission.16674 changed texels include3832 permitted gutters. These measurements do not establish owner art acceptance.

The rejected p01 exposed a planner defect: dilation added an81-pixel disconnected core island containing no seam seed. Its main7171-pixel core held all397 seeds. The new versioned seed_connected_v2 policy removes unseeded islands before generation and narrows or rejects disconnected proposals. Read-only evaluation of the saved correction with that corrected mask yields one connected boundary, mean4.962 and p9514 RGB8. No new inference or historical result modification occurred. Historical plans retain legacy_v1 semantics. New plans store literal per-patch prompts naming captured materials instead of default stone features. The initial qualification has used three of four permitted generations; one roof patch remains, without another correction.

1. Scoped Ruff, offline trial UI build and plan validation. Expected: pass; no code tests, model hashes or downloads.
2. Normal finishing operation on one foundation join and one roof join. Expected: masks span both sides, full context is retained, and generated boundaries are judged on baked re-renders.
3. Draft lifecycle and protection. Expected: one final GLB, no overwritten source, exact409 triangles/UVs/1024 RGBA16/alpha/other maps, and zero outside-permission writes. Cancel/restart resumes completed patches without repeating inference.
4. Rejected and inaccessible components. Expected: specific unresolved status, preserved prior draft, no hidden model or resolution fallback and no endless retries.
5. Final review. Expected: fewer visible discontinuities without duplicated features or blurred mortar; the owner reviews one complete candidate rather than every camera operation.

### Completed runtime qualification
Foundation sessioncbc96d49727e4a81 retained one of two patches, using one diagnosed correction on the rejected patch. Draft280 is applied as282 through the UI;282 contains only meta.json and references280's outputs. No copied GLB. The initial marker plan proves both sides of the selected joins are writable while the wooden treads, walls and roof remain protected. The original268 and preferred Genesis227 remain intact.

Roof session3d00e5782941484c uses282, ten explicitly selected roof faces, seed24061, one patch and no correction. Plan283's marker reaches15819 of15820 selected texels, spans faces6/10/232, changes1125 permitted texels, and changes zero protected texels or alpha. Its one FIBO sample was rejected: boundary disagreement, excessive new detail and colour drift also visible in all three baked neighbour views. No roof repair was retained. All four permitted qualification generations are accounted for; no reroll or model substitution followed. Automatic finishing is qualified as a bounded proposal/rejection workflow, not as universal seam removal.

Lifecycle: UI cancellation of job9d9769c2571c during loading retained the same seed, prompt, masks and pending run284. After an idle restart, UI Resume issued8305b32bd016. A temporary exclusive lock on only its unpublished mesh.glb target caused the intended Windows storage error after the patch decision. No meta.json or final receipt was published. The lock was released and its empty placeholder removed. A second idle restart and UI Resume issueddfeb78964888; CPU finalization published284 with zero model loads and device=replayed. The generation receipt and image retained exactly their original sizes and modification times. One durable GLB exists for the run; wrapper285 references source geometry. No model regeneration, source overwrite or NAS fallback occurred.

Actual output inspection, independently reading decoded mesh arrays and pixels:280 versus268 retains409 triangles, identical geometry/UV arrays and other maps,1024x1024x4 uint16, exact alpha, and zero changes outside permission;16674 texels changed. Roof284 versus282 is an exact zero-texel change with the same guarantees. Its99 reachable seam pairs remain unaddressed and one is unreachable. The UI reports those counts and disables Apply when no repair survived.

Runtime: roof FIBO load16.21s and sample57.68s, peak15.023GiB. Backend and both identified worker processes were observed during loading; backend TCP connections were loopback only and neither worker had TCP connections in that snapshot. Browser observation showed110 page requests, zero external requests, zero blocked requests and only127.0.0.1:8380, with its progress stream connected and offline policy active. This is observed application behavior, not OS network containment. Primary8370 retained PID49908. No borrowed model, engine or foreign workload changed.

Scoped Ruff, offline trial TypeScript/Vite build and AEP plan validation pass. Plan validation required shortening RESULT and moving the same runtime detail into Verification; no additional report was created. Camera position remained fixed across finishing-panel refresh and draft navigation; before/after comparison and saved-pass reopening worked through the UI. The unchanged roof Apply returns409 unchanged_finish before allocating a version. No code tests, model hashes, downloads, commits or pushes. All implementation remains on codex/local-gpu as uncommitted work. The helper lock process is closed;8380 remains available for review with zero active sessions. Primary8370 still owns PID49908.

## Risks
Projection alone cannot make incompatible model images agree. A low-frequency colour fix may hide a tone boundary while leaving duplicated edges. Automatically identifying material boundaries on a single-atlas mesh is uncertain; explicit region selection remains authoritative. Native FP4 acceleration, new model downloads and primary-lane promotion remain outside this unit.

## RESULT

Implemented and runtime-qualified the bounded automatic finishing workflow on8380. Foundation draft280 retained one repair; UI Apply282 references its outputs without copying the GLB. Roof284 rejected colour drift and preserves its source exactly. Cancel/restart and forced publication failure recovered completed work; CPU finalization loaded no model and reused unchanged receipts/images. Actual outputs retain409 triangles, UVs,1024 RGBA16, alpha, other maps and protected pixels. Four permitted generations used. UI shows unresolved regions and prevents unchanged Apply. Scoped Ruff and offline build pass; runtime details and job IDs are in Verification. Owner art acceptance and broader hut quality remain open. Genesis227 remains the preferred foundation; FIBO is the retained repair model. S05 cleanup remains blocked; the native goal resumed for the final audit. Changes are uncommitted.
