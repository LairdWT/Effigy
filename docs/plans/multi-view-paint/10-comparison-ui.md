# Expose complete-set generation, comparison and reviewed Apply

Spoke: S10
Outcome: Expose complete-set generation, comparison and reviewed Apply
Depends-on: S08, S09
Decisions: D7, D8, D9, D10, D11, D12
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, planning:planning-core
Read-set: CODE.md, docs/plans/multi-view-paint/INDEX.md
Write-set: ui/src/MultiViewPaint.tsx, ui/src/multi-view-api.ts, ui/src/multi-view-paint.css, ui/src/Compare.tsx, tools/stage_multi_view_trial.py
State: done

## Context

Owner approved the full-view revision on 2026-10-21. Prior paired-sheet anchors failed stone scale and mortar alignment; preserve their RESULT sections and rejected assets. Activate only trial 8380. Expected turns: 18; preserve usage history and standing circuit breakers. No per-unit handoff stops.

## Evidence

- server/paint_sessions.py:26 owns session creation; steps/_paint_set.py:25 owns surface projection.
- Session owner: server/paint_sessions.py; fixed captures and protected bake: steps/_paint_set.py.
- Prior S01-S05 RESULT sections distinguish implementation from incomplete visual and lifecycle acceptance.
- Source 167_upload and foundation selection 173_paint_set retain 409 triangles and the existing 1024 RGBA16 atlas.
- The earlier coverage calculation found fifteen cameras covering 92238 reachable texels; actual 512-resolution coverage must be recalculated.
- SyncMVD source: https://github.com/LIU-Yuxin/SyncMVD . MOSS v2 Euler recipe: https://huggingface.co/akhaliq/MOSS-Image-SFT-4-steps .

## Steps

Add method/strategy selection and Generate complete view set. Show actual sheet, coverage and missing texels. Present candidate comparison, before/after, ownership/disagreement and 360 inspection. Preserve camera and shared descriptions. Regeneration creates a complete candidate; never silently mix panels from separate generations. Apply aliases the reviewed preview GLB. Add Use as painting reference only for supported adapters; ordinary image generation is not geometry-preserving editing. Stage only bounded changed files and build only the trial UI.

## Files to touch

- ui/src/MultiViewPaint.tsx
- ui/src/multi-view-api.ts
- ui/src/multi-view-paint.css
- ui/src/Compare.tsx
- tools/stage_multi_view_trial.py

## Verification

1. Run scoped static commands after relevant source changes; expected zero findings. Record runtime acceptance separately below.
Run scoped Ruff after Python changes, the offline trial UI build after UI changes, and AEP plan validation after plan changes. Do not write or run code tests or hash sweeps. Use ordinary application jobs and baked renders for runtime acceptance. Installation and static success do not establish art quality. Preserve completed work across interruption.

## Risks

- Whole sheets may alter framing, stone scale or style despite shared context; inspect baked candidates.
- SyncMVD is a new masked adaptation requiring qualification, not a proven drop-in renderer replacement.
- GPU capacity, local compatibility or NAS failures may block runtime work; report exact errors and preserve completed candidates.
- Rejected art is a valid comparison result, not production qualification. No acceptable winner is permitted as a comparison conclusion; technical blockers remain incomplete.
- Owner visual acceptance and primary promotion remain separate. Network observation does not prove OS containment.

## RESULT

Trial UI exposes complete-set methods, saved mask counts, registered sheets, candidate regeneration, excluded-candidate guards, boundary overlays, before/after and reference-only Apply. Added full-size linked 3D comparison using the existing Compare viewer; both meshes orbit together. Browser exercised candidate selection/exclusion, Sync cancellation/restart/resume, shared face removal/addition and Apply226->preview223. Apply stores only3068-byte metadata, no duplicate GLB; reopened mesh renders. Selection5944->3722->5944 restored the original mask exactly. Explicit session labels distinguish full foundation from eight-face diagnostics. Job events refresh externally submitted work without overwriting unsaved recipe edits. Scoped Ruff and offline trial TypeScript/Vite build pass. Primary8370 remains unchanged.
