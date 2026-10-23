# Qualify the workflow across three distinct assets

Spoke: S07
Outcome: Qualify three assets and rank model variants
Depends-on: S06
Decisions: D1, D2, D3, D4, D5
Constraints: C1, C2, C3, C4, C5, C6
Skills: planning:planning-core, python:python-core, powershell:powershell-core, art:texture-painting-core
Read-set: docs/plans/reusable-surface-authoring/INDEX.md, docs/plans/reusable-surface-authoring/06-unified-workspace.md#result, docs/plans/reusable-surface-authoring/01-authoring-contract.md#result, docs/plans/multi-view-paint/11-runtime-comparison.md#result, docs/plans/painting-completion/11-material-base-quality.md#result
Write-set: docs/plans/reusable-surface-authoring
State: active

## Context

S07 verifies S01-S06 using ordinary jobs and outputs. The same executor is not an independent reviewer. The hut is one of three qualification fixtures.

Expected turns: 18. Preserve standing budgets and prior results. Source changes remain uncommitted. Ordinary app outputs are runtime artifacts under C4, not extra evidence packs.

## Evidence

- docs/plans/painting-completion/11-material-base-quality.md:56 records the owner-rejected 312 and reference-only recovery 313.
- server/library.py:306 resolves immutable output references; :350 tracks geometry lineage.
- server/paint_sessions.py:473 contributes session dependencies to retention.

### Runtime comparison, 2026-10-22

Matched source313, faces212/213/402/403, capture320, cameras v01/v09,704px panels, seed24033. Sampling4.17, zero undersampled/unreachable selected texels. Masks325/326 share captures. Baked views335-338 share the final camera; wording follows each adapter.

| Model / candidate / bake | Fresh-worker load / sampling seconds | Peak allocated GiB | Baked visual finding |
|---|---:|---:|---|
| Genesis NVFP4 /321 /324 |17.08 /45.75 |13.439 |Cleaner painted planes; stone/mortar locations move and the patch boundary remains visible. |
| FIBO INT8 /327 /331 |14.38 /79.53 |14.906 |Much source layout retained; gritty high-contrast marks and a visible patch boundary. |
| MOSS Turbo v2 /329 /332 |182.64 /13.52 |20.738 |Best layout retention in this trio; still soft, without resolving discontinuity. |

All three original bakes were operator-rejected; no owner acceptance. MOSS sampled fastest but loaded slowest. Genesis:256 NVFP4/full_precision_mm layers; FIBO:215 INT8 layers, quantized MM enabled; MOSS:BF16,756 Turbo v2 keys/252 modules. No native FP4 claim.

Budget exhausted:12/12. First six:581003ec7b58,011b88145fee(cancelled),2dd5d995a6ea,1467a276bb75,04c44e2beb13,c1231a02c2d4. Seventh: isolated missing-component CLI refusal, conservatively counted. Eighth:676cf15cf89a ->350. Final four:2d26d4bdceb5 ->353 (p00 baseline/correction,p01,p02). CPU rebakes and diagnostics used no generation. No more inference under this allowance.

Footprint-filter rebakes339/340/341 reused the three anchor outputs; S03 records identity preservation and reduced FIBO aliasing. Accumulated ownership then exposed previously missed joins. FIBO350 improved one bounded corner in three baked views and is the operator-preferred working draft. Subsequent353 attempts were all rejected; their mortar breaks, softness or incompatible sharp blocks did not establish a better result. See S05 for exact jobs, diagnoses and21.586s/36.777s warm render-to-review timings. Recommendation: FIBO with qualified footprint projection for bounded repair; no universal winner or full-asset acceptance. MOSS remains the fastest sampler of the matched trio, with slow cold loading and soft results.

Independent decoded350 inspection:409 triangles,1024RGBA16;16227 changed surface texels and4229 permitted empty gutters; zero changes outside the saved permission or independently derived face/gutter allowance. Geometry/UV accessors, alpha and other maps are exact. Decoded353 equals350 pixel-for-pixel with the same preservation results. FIBO workers14220/31732 had no established TCP connections when observed; backend95496 used loopback. Browser traffic remains unobserved.

Curved:004_blender ->005_uv_context(ad6fe33e72d9),38 native painted texels; publication6b18f94dcbc1 ->006 by reference. Its26-view pool exceeds25 panels; none dropped. Crate017/019:270 native painted texels. Its white model sample does not qualify wood painting.

Decoded hut319/324/331/332, crate017/018/019 and curved005 preserve geometry/UV arrays, alpha and other maps; unauthorized changes0. Hut:409 triangles,1024RGBA16; crate362/curved11370,1024RGBA8. Storage lock:503, revision5 preserved. Stale revision409; overlapping regions400; tiled UV jobb304c72abcd8 rejected; empty plan/budget409. Deletion protects017 through019/session. Running Genesis worker95644 had no established TCP connections; observed backend sockets were loopback. Browser traffic unobserved.
- steps/paint_finish_generate.py:353 checks other material maps after finishing.

## Steps

1. Freeze sources, materials, permissions, cameras/display and generation budget. Preserve hut227/312/313 as preferred/rejected/reference examples and the other S01 fixtures. Do not retune thresholds only for the hut.

2. Run registration/preservation diagnostics before inference. Inspect actual geometry/UV arrays, alpha and maps. Keep the hut at409 triangles/1024RGBA16 unless explicitly preparing a new revision; painting preserves its prepared source.

3. Cap qualification at twelve submissions, including failures and repairs. Reuse evidence; compare Genesis NVFP4, FIBO and MOSS Turbo on supported matched anchors. No new model, cache LoRA or engine upgrade.

4. Inspect matched baked views for fidelity, brush marks, feature scale, mortar continuity, occlusion, protected pixels and invented shading/forms. Include roof/eaves, corners and curved surfaces. Separate technical and visual verdicts.

5. Record cold/warm elapsed time, peak VRAM, checkpoint/LoRA/precision, ancestry and baked quality. Recommend per use case or report no winner. Do not credit inherited paint to the last model or substitute publisher speed claims for local timing.

6. Exercise saved Blender edits, mask/source changes, cancellation, idle restart/resume and reference-only Apply through the UI. Use isolated inputs for missing-provider, stale-state, unsupported-UV and storage failures; preserve shared models, NAS and foreign work.

7. Observe owned CUDA/connections, primary8370 and NAS publication. Deterministic methods must not load models. Do not claim OS containment.

8. Record failures and omissions. At budget exhaustion, retain drafts/diagnoses and continue non-generative checks. Only the owner supplies visual acceptance.

## Files to touch

- docs/plans/reusable-surface-authoring

## Verification

1. Inspect three sessions using the same implementation.
   Expected: Three fixtures use the same implementation without hut-specific code.

2. Inspect decoded pixels/accessors, UV correspondence and overlap against each preservation contract.
   Expected: Actual output arrays meet each frozen preservation contract.

3. Bind every model verdict to its recipe, input/output, baked views and limitations.
   Expected: Every model recommendation names comparable inputs, baked results and limitations.

4. Run `agent-code-skills plan check docs/plans/reusable-surface-authoring`; no redundant builds or tests.
   Expected: The plan checker passes without rerunning unchanged static proof.

## Risks

The plan may establish a reliable process without producing an accepted style on every fixture. Record that boundary. Numeric seam reductions, source-resolution recovery and successful round trips are insufficient substitutes for owner-reviewed appearance.

## RESULT

Budget12/12 exhausted. Actual baked arrays preserve geometry/UVs, alpha, other maps and all protected pixels. FIBO350 is the strongest observed bounded repair after correcting projection filtering and ownership history; it remains an operator-preferred draft. All later353 attempts were rejected and its final pixels equal350. Source/native reconstruction and three-asset operations are recorded above. Missing encoder/provider CLI samples failed without outputs or shared-file changes. Cancellation/restart, reference publication and stale/storage/UV/budget guards have backend evidence. UI operation, browser traffic, broader art quality and owner acceptance remain incomplete. The connector still refuses access despite the visible pane and owner enablement; this does not establish disabled settings. Completion and primary promotion remain open.
