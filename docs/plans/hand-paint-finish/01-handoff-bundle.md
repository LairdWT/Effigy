# Export the hand-paint bundle and heal-zone helpers

Spoke: S01
Outcome: Export the hand-paint bundle and heal-zone helpers
Depends-on: none
Decisions: D1, D2, D3
Constraints: C1, C2, C3, C4
Skills: python:python-core
Read-set: docs/plans/hand-paint-finish/INDEX.md, steps/uv_context.py, steps/_paint_set.py, steps/_uv_transfer.py, steps/_paint_seams.py, steps/paint.py, server/authoring_contracts.py
Write-set: steps/_paint_handoff.py, steps/uv_context.py, tools/stage_multi_view_trial.py
State: done

## Context

The hand-painting doctrine works over fixed guide renders, face IDs and a UV layout, then returns strokes as a registered donor. `uv_context` already reconstructs donor RGB inside a permission mask. This spoke adds the export side and the CPU helpers both other spokes use.

## Evidence

Line numbers are before this change.

- steps/_paint_set.py:259-268 renders fixed unlit captures and face IDs; steps/_paint_set.py:501-517 sets the review pitch (-25 degrees) and yaws.
- steps/uv_context.py:57-58 measures texels per asset unit and reports physical scale as unknown.
- steps/uv_context.py:279-317 is the guarded RGB-only reconstruction.
- server/authoring_contracts.py:36-48 requires metres per unit for a declared density; :69-81 holds UV profile, atlas size and gutter.

## Steps

1. Add steps/_paint_handoff.py with `guide_cameras`, `write_guides`, `contact_sheet`, `uv_layout_image`, `seam_zone`, `zone_overlays`, `comparison_sheet` and `handoff_record`. CPU only; Surface renders and rasters.
2. `seam_zone` modes: `writers` (adjacent covered texels with different nonzero writer labels inside one shell, widened by max(3, round(size x 0.012)) pixels and kept in the boundary's shell) and `shells` (shell-border texels, `fallback: true`). An empty boundary or missing history fails without writing.
3. `handoff_record` keeps density null unless declared, `physical_scale` declared or unknown, `texels_per_metre_p50` only with metres per unit.
4. uv_context: op `handoff` (guide/, faces/, cameras.json, uv-layout.png, basecolor.png, permission.png, handoff.json, contact-sheet.png; mesh by reference) and op `heal_mask` (mask.png, overlays/, manifest.json). Reconstruct adds comparison.png, `source_render_comparison` and `mask_version`; any mask with the source's geometry revision is accepted.
5. Add the module to the BACKEND staging tuple.

## Files to touch

- steps/_paint_handoff.py
- steps/uv_context.py
- tools/stage_multi_view_trial.py

## Verification

1. `.venv/Scripts/ruff.exe check .`
   Expected: exit 0.
2. `.venv-ml/Scripts/python.exe -c "import steps.uv_context, steps._paint_handoff, steps._paint_seams"`
   Expected: exit 0.
3. Gated: after staging and restarting the trial, POST action `handoff` for a frozen fixture session.
   Expected: a new uv_context version whose handoff.json shows `declared_density_pixels_per_metre: null` and `physical_scale: unknown`.

## Risks

Guide renders at 1024 pixels run on the CPU and take longer than review renders. Writer labels from older history can mark joins that are not visible seams; the zone is advisory permission, not proof of a defect.

## RESULT

Implemented as specified. steps/_paint_handoff.py holds the eight helpers; uv_context gains `handoff` and `heal_mask` ops and the reconstruct comparison sheet; BACKEND lists the module. Deviation: the bundle also writes basecolor.png so a painter has the clean atlas. Ruff exit 0; import smoke exit 0. Item 3 gated, not run (trial :8380 not freed).
