# Own persistent sessions and capture shared mesh selections

Spoke: S01
Outcome: Own persistent sessions and capture shared mesh selections
Depends-on: none
Decisions: D1, D2, D3, D4, D5, D6
Constraints: C1, C2, C3, C4, C5, C6
Skills: aep:aep-core, python:python-core, web:typescript-core
Read-set: CODE.md, docs/plans/multi-view-paint/INDEX.md, server/paint_sessions.py, server/paint_routes.py, server/app.py, server/library.py, server/jobs.py, steps/paint_set.py, steps/_paint_set.py
Write-set: server/paint_sessions.py, server/paint_routes.py, server/app.py, server/library.py, server/jobs.py, steps/paint_set.py, steps/_paint_set.py
State: done

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

1. Add revision-checked, atomic session state beneath each asset. Bind immutable source, geometry, appearance and recipe; keep one backend owner and reject writes during active jobs.
2. Add typed create/read/update/action APIs using normal job IDs. Persist completed outputs and resolve restart state without replaying completed generation.
3. Project visible brush/lasso and face edits to one UV permission mask. Green means permission. Derive 26 fixed cameras with shared framing, capture unlit images/face ownership, pair adjacent visible selections into 1408x704 sheets.
4. Extend dependencies and geometry lineage for session and version references. Keep source meshes virtual rather than copying them. Activate only through bounded trial staging.

## Files to touch

- server/paint_sessions.py
- server/paint_routes.py
- server/app.py
- server/library.py
- server/jobs.py
- steps/paint_set.py
- steps/_paint_set.py

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

Implemented shared UV selection, fixed26 cameras,21 paired groups, typed session APIs and library dependencies. Session47ed3bf8e8f74d1a captured168_paint_set through job9913f3e77d08:92238/92255 selected texels visible. UI clear170 and triangle48 selection171 succeeded; restored172 is pixel-identical to the initial foundation mask. Stale revision returned409. Restart retained the session. Genesis session0061dba219e64aef reuses168 without capture copies. Scoped Ruff and plan check pass. Model generation and combined-bake acceptance remain in dependent spokes. No tests, hashes or publication.

