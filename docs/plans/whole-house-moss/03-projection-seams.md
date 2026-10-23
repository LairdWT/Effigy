# Repair projection seams in the whole-house bake

Spoke: S03
Outcome: Repair projection sampling and distinguish remaining generated-view seams
Depends-on: S02
Decisions: D1, D5, D7
Constraints: C1, C2, C3, C4
Skills: python:python-core, planning:planning-core, art:texture-painting-core
Read-set: docs/plans/whole-house-moss/INDEX.md, docs/plans/whole-house-moss/02-whole-house-trial.md#result, steps/_paint_set.py, steps/_views.py
Write-set: steps/_paint_projection.py, steps/_paint_set.py, server/paint_routes.py, server/paint_sessions.py, tools/stage_multi_view_trial.py
State: done

## Context

The owner rejected seams in244. Projection maps image pixels onto geometry; it does not itself constrain the model to paint the same stone edges in different panels. Nevertheless, the bake must not add UV-island outlines, resampling losses or samples from another surface. This repair reuses242 and its immutable241 capture; no new inference. Expected turns18; standing256-turn and implementation2250000-token ceilings apply, without a per-unit handoff stop.

## Evidence

The repaired transfer is owned by steps/_paint_set.py:354, with eligible-tap sampling at steps/_paint_projection.py:15 and selection feathering at steps/_paint_projection.py:37.

| Hypothesis | Distinguishing observation | Result |
|---|---|---|
| UV background is treated as unselected surface during feathering | A full-surface mask still has attenuated texels | Confirmed: all523762 surface texels selected, but27511 receive feathering at width2 |
| Bilinear filtering accepts neighbouring faces after checking only the central pixel | Accepted texels have filter taps owned by another face | Confirmed: camera v00 has25556 such footprints among153395 visible texels; all26 cameras contain them |
| Generated panels disagree despite joint context | Different panels invent or move features for the same surface | Confirmed in245 and baked247: extra windows, inconsistent frames and roof strokes; requires a distinct masked cross-view heal, not a claim that projection alone guarantees continuity |

## Steps

Add an owned-face bilinear sampler with normalized eligible taps only. Admit taps only from the same front-most face, generated permission and fully covered captured pixels. Keep the existing positive-facing and central visibility checks. Transfer the edit residual against the exact original capture onto the original atlas, so unchanged images do not repeatedly blur source detail. Preserve sharp dominant-view ownership; do not average contradictory images.

Exclude empty atlas space from selection-boundary feathering. A full-surface selection receives no island-edge fade. Refresh permitted gutters only adjacent to actual changed surface texels. Add a source-only mode to the existing diagnostic action for a normal application round trip; retain the existing green-mask diagnostic default. Publish each rebuilt candidate as a new ordinary version.

## Files to touch

- steps/_paint_projection.py
- steps/_paint_set.py
- server/paint_routes.py
- server/paint_sessions.py
- tools/stage_multi_view_trial.py

## Verification

1. Run scoped Ruff. Expected: no findings. Stage named Python changes only into8380 and restart that lane when idle; primary8370 remains unchanged. No UI changes require a rebuild.
2. Run source diagnostic and a fresh preview of242 through normal session actions. Expected: source diagnostic changes zero pixels; rebuilt preview preserves409 triangles, geometry/UVs,1024 RGBA16, alpha and other maps, with zero changes outside eligible texels/gutters. Report reduced coverage from stricter filtering honestly.
3. Inspect baked eight-angle renders and the UI. Expected: report remaining generated-view disagreements separately; no production acceptance or seam-free claim without visual proof. Do not consume another inference candidate.

## Risks

Residual transfer preserves source detail but can retain source features when a generated feature moves; model agreement still needs visual review. Filtering only eligible samples can leave more texels unchanged. UV-space feathering around partial selections is not a geodesic brush. These repairs cannot reconcile contradictory mortar lines or painted architectural inventions.

## RESULT

Repaired only8380. Source diagnostic job1f734c170e8f produced248 with zero changed texture pixels and zero feathered texels. Reusing242's generated images produced249 through the UI:518588 writable texels,5174 unchanged/unreachable, zero protected/alpha changes, unchanged geometry/UVs/other maps,409 triangles and1024 RGBA16. Full-selection feathering dropped from27511 texels to zero. Mask diagnostic eb548a3d4bf0 produced250; the green-mask UI reference remains separate from source diagnostics.

Eight-angle review shows retained source detail and reduced bake-induced boundary artifacts. Mortar, roof and window/eave disagreements remain in the generated images;249 is not seam-free or accepted art. No inference, model change or source overwrite occurred. Scoped Ruff passed; plan validation passed after structural corrections. No UI source changed. Primary8370 remains PID49908. Repaired preview is open for comparison; asset quality remains unresolved.
