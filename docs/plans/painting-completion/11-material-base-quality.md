# Diagnose the rejected material base and recover a sharper reference

Spoke: S11
Outcome: Diagnose blur and compare a sharper source on the aligned mesh
Depends-on: S10
Decisions: D9, D10
Constraints: C1, C2, C3, C4
Skills: python:python-core, art:texture-painting-core
Read-set: docs/plans/painting-completion/INDEX.md, docs/plans/painting-completion/10-final-camera-registration.md#result, steps/uv_context.py, steps/_uv_transfer.py
Write-set: steps/uv_context.py, scratch/lanes/fibo2, docs/plans/painting-completion
State: done

## Context

The owner rejects312 as blurry, visibly seamed and inconsistent in detail. Technical preservation and lower seam-error scores did not establish a coherent material result. Stop further diffusion while diagnosing the base. Expected turns12; preserve prior usage and circuit breakers. No new model campaign, downloads, atlas enlargement or shared engine changes.

## Evidence

steps/_paint_set.py:461 renders the actual texture without lighting. Both the raw310 atlas and the live312 mesh show softness. The whole-house base is MOSS242, captured in26 panels of384 square at denoise0.55, then baked into249/274 and inherited by later branches. Later finishing uses1024 close views with half the world-space extent.

Read-only geometric measurement against the aligned atlas finds optimistic best-angle camera pixels per atlas texel of0.5439/0.5605/0.5716 at weightedp10/p50/p90. All atlas area is below one camera pixel per texel, even ignoring occlusion. Close-up repairs sample5.3346 times more densely. The current atlas occupies49.9818 percent of its1024 square. These are measured ratios, not an invented physical-density target.

Live comparison with retained227 shows sharper walls and wood in227.312 has accumulated a soft whole-house base and locally redrawn detail from different models/scales. UV overlap remains zero; alignment alone cannot correct those image-content differences. The texture-painting texel-budget guidance requires camera-footprint and reference-density checks; it does not prescribe a universal density or make diffusion equivalent to guided brush painting.

## Steps

1. Record312 as rejected quality; preserve all history and227.
2. Extend the existing CPU UV correspondence operation to transfer a named source's base colour onto the current aligned UVs. Use existing same-triangle/same-shell sampling; reject unsupported correspondence, material changes or transparency changes.
3. Preserve target geometry/UV arrays, atlas size/bit depth, alpha and other maps. Refresh only empty gutters; publish one new candidate through the normal backend job owner.
4. Transfer227 onto312's aligned mesh without inference. Retain projection ownership and the remapped foundation selection. Compare actual fixed-camera renders with227 and inspect against312.
5. Treat the result as a sharper working-reference candidate, not final art acceptance. Any further repaint needs consistent sampling density and material scale before generation; do not patch the rejected mixed base indefinitely.

## Files to touch

- steps/uv_context.py
- scratch/lanes/fibo2
- docs/plans/painting-completion

## Verification

1. Scoped Ruff and plan validation. Expected: pass; no tests or hashes.
2. Normal CPU transfer job. Expected:409 triangles, unchanged target geometry/UVs/maps/alpha,1024RGBA16, exact triangle correspondence and no unsupported source samples.
3. Four fixed-camera render comparisons plus live before/after. Expected: source appearance retained within the observed single resampling pass; report measured differences and visible defects separately.
4. Runtime boundary. Expected: zero model loads, primary8370 unchanged, no historical overwrite.

### Source-recovery result

Normal CPU job0491da78bf20 published313_uv_context, transferring227's colour onto312's unchanged aligned geometry/UVs. No model loaded.409 triangles,1024RGBA16, other maps and target alpha remain unchanged; every target texel has a supported same-triangle/same-shell source sample. Maximum triangle-position error0. Fixed-view mean RGB8 differences from227 are1.091/1.029/1.011/1.043 at yaw0/90/180/270; p95 is5/4/4/4 and rendered alpha changes are0.830333 atlas texels changed, including refreshed empty gutters. The retained source appearance survives the UV transfer; this does not accept its existing art defects.

## Risks

227 has its own known seam and style limitations. Restoring its detail does not qualify the full house. Resampling between UV layouts introduces a small filter footprint. The atlas cap stays1024; no sharpening filter or invented microdetail should conceal an inadequate source.

## RESULT

312 is recorded as rejected for blur, seams and uneven detail. Its MOSS384-panel base undersamples every atlas face even at the best angle: median0.5605 camera pixels per texel. Later close repairs sample5.3346 times more densely. Raw-atlas and live comparison confirm source softness and inconsistent detail; zero UV overlap does not resolve them. Added a guarded CPU source-colour transfer and published313 from retained227 on312's aligned geometry/UVs.409 triangles,1024RGBA16, alpha/maps and exact triangle positions remain intact; no model loaded. Four render comparisons average1.01-1.09 RGB8 difference from227.313-versus312 comparison is prepared in the existing browser tab. Ruff and plan checks pass.313 is a sharper reference with known defects, not accepted final art. Further repaint requires consistent capture density and material scale; no new diffusion was run.
