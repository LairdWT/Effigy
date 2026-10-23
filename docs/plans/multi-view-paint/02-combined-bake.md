# Compose all eligible views into one protected texture preview

Spoke: S02
Outcome: Compose all eligible views into one protected texture preview
Depends-on: S01
Decisions: D1, D2, D3, D4, D5, D6
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, art:texture-painting-core
Read-set: CODE.md, docs/plans/multi-view-paint/INDEX.md, steps/_paint_set.py, steps/paint_set.py, server/paint_sessions.py
Write-set: steps/_paint_set.py, steps/paint_set.py, server/paint_sessions.py
State: stale

## Context

The owner requested a complete workflow after sequential views produced mismatched materials. Joint paired editing is a hypothesis to qualify, not guaranteed shared3D structure. The original small foundation stones must be restored; the larger wrap is rejected. The single-view workflow remains available. Keep code ownership in the Effigy checkout and activate only the isolated trial. New file names in Read-set are implementation destinations and are read only after creation.

## Evidence

- steps/paint.py:163 dispatches single capture/application; lines247-318 own visibility and protected texture writes.
- server/library.py:304 resolves immutable output aliases; lines338-363 own dependencies and geometry lineage.
- server/jobs.py:144 chooses worker interpreters; runtime publication belongs to the backend.
- tools/fibo_trial_worker.py:40 constrains FIBO to one fixed capture today.
- steps/reference.py:204 owns Genesis differential masking.
- ui/src/SurfacePaint.tsx:62 is the existing single-view entrypoint.
- docs/plans/surface-paint-ux/00-genesis-edit.md:55 records full-precision matrix multiplication for borrowed NVFP4 weights.

## Steps

1. Compute at most two CPU view contributions concurrently. Admit only selected, generated, front-most visible texels with positive facing above 0.25.
2. Assign connected coplanar patches a dominant view ranked by facing then frame distance, using stable view IDs for ties. Fill occlusion gaps from eligible alternatives; never average conflicting mortar lines.
3. Preserve unselected and unseen texels, alpha, geometry, UVs and other maps. Feather only inside the global mask boundary and refresh only permitted empty gutters.
4. Write one combined preview mesh and review renders with ownership/disagreement overlays. Apply aliases the reviewed outputs without another GLB copy, and rejects stale or incomplete inputs.

## Files to touch

- steps/_paint_set.py
- steps/paint_set.py
- server/paint_sessions.py

## Verification

1. Run the installed Ruff check against changed Python files from the project root; expected: zero findings. Do not autoformat unrelated files.
2. For UI changes run npm --offline --prefix scratch/lanes/fibo2/ui run build; expected: successful TypeScript compilation and bundling.
3. Run agent-code-skills plan check docs/plans/multi-view-paint after plan changes; expected: no structural findings. This does not prove visual quality.
4. Use ordinary application job identities and output references for behavior. Expected: the actual mesh retains409 triangles, original UVs, one1024 RGBA16 atlas and exact alpha, with protected texels unchanged. No code tests or hashes are authorized.


## Risks

- Shared sheets can lose detail, invent geometry in pixels or move panel content: reject the baked candidate and hold the adapter if one diagnosed correction also fails.
- Concurrent owner work or stale revisions: reject writes rather than silently rebasing or modifying another job.
- Runtime or browser access may be unavailable: complete independent work and state the exact remaining acceptance surface.
- NAS or GPU capacity failure: preserve completed work and report; never replace storage or stop foreign processes.

## RESULT

Combined previews `178_paint_set`, `179_paint_set`, `184_paint_set` and `185_paint_set` ran through normal jobs. Each composed two camera contributions into 40,811 permitted texels with two CPU workers; 51,444 selected texels remain unseen by this anchor pair. Guards passed: 409 triangles, exact geometry/UV arrays, 1024 RGBA16, exact alpha, unchanged other maps and zero changes outside permitted texels/gutters. Total changed texels include refreshed gutters.

Browser inspection exercised ownership and disagreement overlays on the baked mesh. Eight-angle reviews and turntables are ordinary preview outputs. FIBO correction job `1b5283b53708` produced `184_paint_set`; Genesis job `c2b40c3fb977` produced `185_paint_set`.

Art qualification failed in S03. Neither preview was applied. Reference-only Apply and full-wrap acceptance remain incomplete. Scoped Ruff passed; source remains uncommitted.

