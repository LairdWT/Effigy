# Repair remaining material joins on the hut

Spoke: S09
Outcome: Repair remaining visible joins after UV verification
Depends-on: S08
Decisions: D6, D8, D9
Constraints: C1, C2, C3, C4
Skills: python:python-core, powershell:powershell-core, art:texture-painting-core, web:typescript-core
Read-set: docs/plans/painting-completion/INDEX.md, docs/plans/painting-completion/08-automatic-finishing.md#result, steps/paint_generate.py, steps/_finish_plan.py, steps/paint_finish_generate.py
Write-set: server/finish_contracts.py, server/jobs.py, server/library.py, steps/paint_generate.py, steps/_finish_plan.py, steps/paint_finish_generate.py, steps/uv_context.py, steps/_uv_transfer.py, steps/repair_baseline.py, tools/stage_multi_view_trial.py, tools/native_reference_entry.py, ui/src/AutomaticFinish.tsx, ui/src/multi-view-api.ts, scratch/legaia, scratch/lanes/fibo2, docs/plans/painting-completion
State: active

## Context

Owner rejection282 reopens targeted quality work. Preserve227/268 and all history; cleanup is independent. Expected turns18; existing circuit breakers remain.

Preserve409 triangles,1024RGBA16 and shape. D9 permits a separate UV copy; historical layouts remain immutable.

## Evidence

Routes used:3dgen-core, blender-core and projection/UV guidance. At entry, steps/paint_generate.py:80 supplied FIBO an empty latent, then clipped decoded output. Reference context alone did not fix surrounding denoising state. The installed read-only sampler supports source latents and a noise mask. Earlier597-pixel roof cores could not replace a whole conflicting feature; baked views showed colour drift and mismatched stone/roof joins.

## Steps

UV prerequisite D9:282 has zero UV overlaps/degenerates and median/p95/max stretch1.000004/1.053479/1.131092. Its ZenUV/UVPackmaster lineage already uses90-degree packing, disabled pre-rotation and no flips. Qualify UV Squares only in a private process and retain the409 exported triangles. Do not attribute painted ghosts to overlap when measured overlap is zero.

1. Add a versioned finishing generation policy. New FIBO repair plans use the captured source latent and constrain denoising to the repair permission. Preserve native four-step settings and full reference context. Old plans replay under their recorded policy.
2. Increase repair-core support to encompass conflicting features, retaining a wider optimization ring and seeded connected-mask guards. Keep the exact same-face projection and hard binary boundary; no crossfade workaround.
3. Qualify the changed adapter on a bounded foundation join and roof region from282. Inspect actual marker masks first. Start with structure-preserving reference conditioning; use diagnosed changes only after inspecting full-frame output and baked neighbouring angles.
4. Carry retained patches forward through the assembled atlas and repair the remaining conspicuous joins in serial passes. Use at most three patches and one diagnosed correction per pass. Keep intermediate records, reject regressions and change the method when evidence contradicts it; do not count rejection as an art-quality improvement.
5. Re-render the complete circumference and close views. Confirm unchanged geometry, UVs, atlas dimensions, alpha, other maps and protected pixels. Leave one reviewable branch in the UI with specific remaining defects reported honestly.

## Files to touch

- server/finish_contracts.py
- server/jobs.py
- server/library.py
- steps/paint_generate.py
- steps/_finish_plan.py
- steps/paint_finish_generate.py
- steps/uv_context.py
- steps/_uv_transfer.py
- steps/repair_baseline.py
- tools/stage_multi_view_trial.py
- tools/native_reference_entry.py
- ui/src/AutomaticFinish.tsx
- ui/src/multi-view-api.ts
- scratch/legaia
- scratch/lanes/fibo2
- docs/plans/painting-completion

## Verification

### UV prerequisite results

All three local packages load in configured Blender5.2.0. The actual UV Squares1.14.1 grid operator fails at its removed BMLoopUV.select API. It has not been patched or falsely reported as working. Owner-authorized Sol6 Clotho/Lachesis/Atropos decision support selected rigid alignment of the already low-distortion shells before considering an add-on port or grid reshape. Moirai supplied no independent runtime proof; Atropos confidence0. Authoring subsequently supplied runtime proof.

The copy preserves409 triangles andUVMap. UVPackmaster3.1.1 packed65 aligned shells onCPU:90-degree rotation, no pre-rotation/flips,16-pixel requested gutters. The temporary helper had43 quads/323 triangles; coordinates mapped back onto original triangles. Median/p95/max stretch1.000/1.053/1.131; zero overlap/degenerates. All65 reference edges align within0.000034degrees. Two shells have nearly tied slanted/axis edges, so naive longest-edge inspection flags them; no curved shell was forcibly squared.

Current282 paint was transferred through matching triangles with same-shell filtering into another1024 RGBA16 atlas. Maximum triangle-position difference is0; no nearest-colour fallback was needed. Eight fixed512 views show mean RGB8 change0.904-1.032 and p954, with zero rendered alpha differences. This is appearance resampling, not a claim that repacking healed the existing painted joins. The originalUV and newAlignedUV remain in the packed private authoring blend. UV Squares remains runtime-incompatible; no shared add-on or preferences were changed.

CPU uv_context restores ownership/selection by triangle correspondence and references the uploaded mesh. Geometry, orientation, material and atlas guards remain strict; only the running backend publishes metadata. Upload286 and context jobc74fcc6cba64 establish this lineage.

### Source-locked finishing qualification

Context jobc74fcc6cba64 completed as287_uv_context. Its mesh aliases286 with zero copied GLB bytes; geometry displacement is0 and the remapped foundation selection contains92348 texels. The private editable blend is scratch/legaia/hut-uv-aligned-01/hut-uv-aligned.blend, with originalUVMap, AlignedUV and packed paint.

Initial S09 plans use feature_connected_v3 masks and source_locked_v1 generation. FIBO receives source latents and a noise mask, checked against an independent latent copy. RGB/alpha guards remain separate.49/97-pixel masks retain seeded connectivity and hard mincut boundaries. Historical plans retain their policies.

Foundation session6add79f381e44da5 planned288 and jobe787186f6ed4 produced289. One model load made four samples; protected latent maximum error was4.768e-7 in all four, with15.023GiB peak allocation. Samples took57.77s cold and3.00/2.27/2.25s warm. Two patches were retained; one failed boundary agreement. Retained seam errors fell98.48->54.54 and94.86->24.66 RGB8. Actual metadata reports409 triangles, unchanged geometry/UVs/other maps,1024RGBA16, zero outside/alpha changes and13185 changed texels including2516 gutters. This improves two local joins; it does not close the overall visual-quality requirement.

The next roof session2ab85748769548e8 starts from289 and explicitly selects88 roof triangles. Plan291 reaches132383 of132395 selected texels, reporting12 unseen. Its actual marker bake spans both window-overhang joins and a rear roof join, with zero outside or alpha changes. The new review path renders1024-pixel neighbouring views and shows identical close crops; pole cameras also receive oblique review angles. Full-frame generation context is unchanged. Roof jobcfb8c545809a completed as292, retaining two patches and rejecting one for new dark regions in all three baked views. Its7730 changed texels preserve geometry/UVs, alpha, other maps and all pixels outside permission. Close baked views show more continuous thatch at both window overhangs; the rejected rear proposal remains unchanged.

1. Static verification: scoped Ruff, offline trial UI build and plan validation. Expected: pass.
2. Runtime verification: job receipts, decoded/baked output and markers. Expected: preserved geometry/permission and visible repair. Check geometry, UVs, atlas format, other maps, alpha and protected pixels; inspect local and360 appearance separately. No tests or hashes. Preserve primary8370 and foreign workloads.

### Inherited baseline reconstruction

The retained branch still inherits249's source_residual_v2 projection. The corrected saved-image bake274 uses the exact same request and242 candidate, but its correction was never carried into268/282. Direct inspection finds505789 changed surface texels between249 and274. Later retained paint changed36926 of those source-layout texels, leaving468889 untouched legacy texels with mean6.057 RGB8 difference from the corrected projection. This confirms a propagation gap.

The explicit CPU repair_baseline operation names249,274,282,287 and current292. It verifies source/candidate binding, unchanged geometry/UVs within each layout, exact reconstructed appearance of the aligned reference, and actual triangle correspondence between layouts. It protects every later permission footprint plus all changed pixels, including the new masked repairs. Only unedited baseline regions receive corrected RGB; no residual subtraction/addition or new diffusion is used. Projection labels are carried forward with collision guards, and only permitted gutters refresh. Historical versions remain immutable. Jobd8e9ff36ffec published294_repair_baseline:453498 surface texels corrected,56708 protected surface texels preserved, exact reconstructed aligned RGBA, zero triangle displacement and zero alpha/protected/outside changes. The full360 review is cleaner, but local joins remain.

### Close repair context

New close_context_v4 plans retain the26-camera survey, then record a local frame centered on each selected seam component. Zoom is bounded to2x and mask support scales with it, preserving the physical repair width. The final hard-cut graph remains capped at160000 pixels; clipped or disconnected proposals are rejected before inference. Historical plans keep their original framing. Foundation session18af7aa9ab904417 starts from294 with287's remapped selection. Plan295 records three2x views with actual marker permissions; the step risers are writable and wooden treads remain protected. The worker receives each entire1024 local capture as context.

### Close-view model comparison and worker closeout

FIBO jobd619573523f1 completed296 with three rejected patches and one correction. Its step-riser proposal invented wood on stone; baked-view and boundary guards rejected it. No changed texture was retained. Genesis sessionab477edad2de4be9 uses the identical294 source,287 selection, recorded cameras and seam pairs, with eight-step differential masked editing at denoise0.30. Job039f17bc7d06 saved299 with all three patches retained,18722 changed texels including5065 gutters,409 triangles and unchanged geometry/UVs/other maps/alpha/protected pixels. Close baked reviews show improved risers and foundation joins; this remains a visual candidate, not owner acceptance.

That Genesis worker exited0xc0000005 after saving its complete finish receipt and before returning the outer RESULT. Session reconciliation recovered299 without another model run. The isolated one-shot finishing entry now owns process exit: it flushes the actual CLI result and preserves its exit code, then lets process termination release native resources. The redundant in-process model unload is skipped only for that entry. Errors retain their nonzero codes; resident/reference workers are unchanged. Roof session53484f46e01c4c8d supplies the next actual-work closeout check, from299 with the same88 roof faces and two bounded patches.

Roof jobb38c2a41fa85 completed successfully as wrapper302 with draft301: both repairs retained, no correction,6695 changed texels including99 gutters, unchanged409-triangle geometry/UVs,1024RGBA16, other maps and exact alpha, with zero outside writes. The revised one-shot entry exited0 and released its model worker. Samples took55.39s cold and9.90s warm; peak13.506GiB. Genesis foundation samples took71.93/7.33/7.36s with the same peak; its256 NVFP4 layers still report full_precision_mm, not nativeFP4 acceleration.

UI draft review and Apply published303_paint_finish, labelled Aligned UVs - Genesis foundation and roof repairs. Every output aliases301; there is no duplicate GLB. The editable scratch/legaia/hut-uv-aligned-01/hut-uv-aligned-repaired.blend packs301's atlas and preserves bothUVMap andAlignedUV on409 polygons. Background Blender saved and exited0; unrelated installed HOps reported a headless GPU initialization warning, with no add-on/preference changes. Existing Blender sessions were preserved. Primary8370 remains PID49908; trial8380 is PID91716, with zero remaining model workers. Runtime worker/backend TCP observation saw only backend loopback connections, not OS containment. Ruff and plan checks pass; prior offline UI build remains current because this follow-up changes no UI source. All work is uncommitted.

### Subsequent foundation pass

Session3bd33b5d41b44535 starts from303 with287's foundation permission and the same Genesis recipe, seed24120. Initial plan304 overlaps its first two projected repair cores by690 texels,29.04% of the smaller core. The planner now consumes every seam pair whose endpoints fall inside an earlier patch's actual projected core, while retaining overlapping visual context. This avoids reselection within the batch; it does not declare those seams healed before generation or suppress them in later passes. New plans record additional_pairs_in_planned_cores; historical plans remain replayable. Plan304 stays in history without inference. The updated plan is an ordinary application job,376b622a93c6.

Job5d7aa0cac22b completed306/307 with three retained patches and no correction. Actual texture changes:16030 texels including2995 gutters; geometry/UVs,409 triangles,1024RGBA16, other maps, alpha and outside pixels preserved. Mean targeted seam errors fell107.03->28.27,97.75->22.64 and72.64->29.59 RGB8. Samples57.12/7.98/7.91s, peak13.506GiB. Worker94200 used the configured native interpreter and had no established TCP connections during observation; backend connections were loopback only. The worker exited cleanly.

New pass carries model, appearance, prompt, seed, denoise, conditioning and the prior plan mask, retaining protected-face exclusions. The typed client accepts historical sessions without selection_source. Offline trial build passes as index-hxxHSjNQ.js; live New pass inspection on308 confirms Genesis, denoise0.30, seed24120, the literal foundation prompt and305 mask. No extra job was submitted.

306 read-only inspection: both seam endpoints changed for88/111p00 pairs,82/82p01 and147/157p02. All changes stayed permitted. Some targeted pairs therefore retain a source endpoint; inspect local-camera visibility and mask registration before attributing the remaining thin joins solely to model quality.

## Risks

Masked latent denoising with FIBO is an Effigy adaptation, not a proven native inpainting contract. VAE decoding can change pixels outside a latent mask; final RGB/alpha protection remains mandatory. Larger regions can drift in material identity. Hard boundaries avoid ghosts but cannot make contradictory patterns agree. Existing Genesis masked editing remains available without changing shared engines or checkpoints.

## RESULT

Candidate308 is open for review;303 remains preserved. Separate aligned UVs retain409 triangles, zero overlapping/collapsed faces and1024RGBA16. UVPackmaster used90-degree rotations; UV Squares1.14.1 remains incompatible with Blender5.2 and was not silently substituted. Reconstructed the inherited ghosted baseline, preserving later repairs. Added source-locked FIBO and close-context finishing; Genesis retained three foundation and two roof repairs after the close FIBO pass was rejected. Actual geometry/UV/alpha/map/protected-pixel guards pass. UI Apply303/308 references301/306 without duplicate GLBs. One-shot worker closeout now passes an actual Genesis job. Packed editable Blender copy saved; primary lane and history preserved. Ruff/plan checks pass, no tests/hashes/commits. Overall seamless art quality and owner acceptance remain open; Owner rejects312; S11 owns diagnosis.
