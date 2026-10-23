# Own complete-set layouts, coverage and protected baking

Spoke: S06
Outcome: Own complete-set layouts, coverage, typed sessions and protected baking
Depends-on: S01, S02, S05
Decisions: D7, D8, D9, D10, D11, D12
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, planning:planning-core
Read-set: CODE.md, docs/plans/multi-view-paint/INDEX.md, server/paint_sessions.py, steps/_paint_set.py
Write-set: server/paint_contracts.py, server/paint_sessions.py, server/paint_routes.py, steps/_paint_set.py, steps/paint_set.py
State: done

## Context

The owner approved whole-set painting on 2026-10-21. Prior paired-sheet anchors failed stone scale and mortar alignment; their RESULT sections and rejected assets remain intact. This unit changes the reusable contract and activates only trial 8380. Expected turns: 18. Standing usage history and the 256-turn circuit breaker remain in force; no per-unit handoff stop.

## Evidence

- server/paint_sessions.py:26 owns session creation; steps/_paint_set.py:25 owns surface projection.
- Existing session owner: server/paint_sessions.py. Capture, visibility and protected bake owner: steps/_paint_set.py.
- Source 167_upload and foundation selection 173_paint_set retain 409 triangles and the existing 1024 RGBA16 atlas.
- At the prior capture resolution, fifteen cameras covered 92238 selected texels, with seventeen unseen. Actual 512-resolution coverage must be recalculated.
- Existing pairs use hardcoded 704-square panels. New layouts require recorded rectangles rather than inferred image arrangement.

## Steps

1. Add typed layout and camera bindings, generation strategy and whole-set candidate identity. Preserve legacy paired sessions without silent conversion.
2. Preserve the existing 26 cameras and framing. Render registered 512-square images and masks using exact front-most ownership and facing greater than 0.25.
3. Select a coverage-complete set greedily, remove redundant views and break ties by stable camera ID. D13 expands whole sheets to twenty-five panels after the actual-resolution 21-view result; retain 512-square panels and report larger requirements. SyncMVD can use all eligible cameras.
4. Keep one authoritative UV permission mask. Share captures across methods. Invalidate the entire affected candidate after source, selection, layout or recipe changes.
5. Generalize projection crops to exact panel rectangles. Preserve dominant-view ownership, inward feathering, permitted gutters and exact source geometry, alpha and other maps.

## Files to touch

- server/paint_contracts.py
- server/paint_sessions.py
- server/paint_routes.py
- steps/_paint_set.py
- steps/paint_set.py

## Verification

1. Run scoped static commands after relevant source changes; expected zero findings. Record runtime acceptance separately below.
Run scoped Ruff and AEP plan validation after relevant edits. Use a normal diagnostic projection to verify registered masks and cameras before inference. Confirm actual coverage and protected pixels through ordinary job metadata. No code tests or model hashes. Later S11 owns complete UI lifecycle and four-method visual acceptance.

## Risks

- Resolution changes can expose additional unreachable texels; report them without dropping coverage requirements.
- A joint result is atomic. Mixing panels from separate generations would hide invalid state and is prohibited.
- NAS failure must stop publication. Historical results and source files remain unchanged.

## RESULT

Typed layouts and immutable candidates support whole-sheet and synchronized strategies while retaining historical pairs. Capture186 reuses source167 and mask173; actual512 coverage requires21 working views,92123 reachable texels and132 unseen. Four methods reuse the captures. All12 combined previews preserve409 triangles, geometry/UV arrays, other maps,1024RGBA16 and alpha, with zero protected changes. Whole-candidate exclusion blocks selection for Apply while retaining history. Tiled-UV, multi-primitive, incompatible-selection, stale revision and storage-access refusals were exercised. Scoped Ruff passes. S11 owns visual and browser qualification limits.
