# Synchronize view predictions through protected shared texture denoising

Spoke: S09
Outcome: Synchronize view predictions through protected shared texture denoising
Depends-on: S07, S08
Decisions: D7, D8, D9, D10, D11, D12
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, planning:planning-core
Read-set: CODE.md, docs/plans/multi-view-paint/INDEX.md
Write-set: steps/sync_paint.py, steps/_sync_renderer.py, steps/_sync_scheduler.py, server/sync_models.py, server/jobs.py, server/presets.py, tools/stage_multi_view_trial.py, licenses/SyncMVD.txt
State: done

## Context

Owner approved the full-view revision on 2026-10-21. Prior paired-sheet anchors failed stone scale and mortar alignment; preserve their RESULT sections and rejected assets. Activate only trial 8380. Expected turns: 24; preserve usage history and standing circuit breakers. No per-unit handoff stops.

## Evidence

- server/paint_sessions.py:26 owns session creation; steps/_paint_set.py:25 owns surface projection.
- Session owner: server/paint_sessions.py; fixed captures and protected bake: steps/_paint_set.py.
- Prior S01-S05 RESULT sections distinguish implementation from incomplete visual and lifecycle acceptance.
- Source 167_upload and foundation selection 173_paint_set retain 409 triangles and the existing 1024 RGBA16 atlas.
- The earlier coverage calculation found fifteen cameras covering 92238 reachable texels; actual 512-resolution coverage must be recalculated.
- SyncMVD source: https://github.com/LIU-Yuxin/SyncMVD . MOSS v2 Euler recipe: https://huggingface.co/akhaliq/MOSS-Image-SFT-4-steps .

## Steps

Adapt upstream SyncMVD scheduler/noise equations and samplewise attention with attribution. Replace PyTorch3D with typed Effigy renderer and mask interfaces. Each step renders the shared texture into all cameras, predicts targets in micro-batches of at most six including references, waits for every target prediction, then performs one shared-texture update. Use normal conditioning, thirty executed updates, initial strength 0.35 and synchronization throughout the entire sequence. Restore protected source context at the corresponding noise level after each update; enforce exact final RGB and alpha protection. Report global step and processed-view count without per-step image archives.

## Files to touch

- steps/sync_paint.py
- steps/_sync_renderer.py
- steps/_sync_scheduler.py
- server/sync_models.py
- server/jobs.py
- server/presets.py
- tools/stage_multi_view_trial.py
- licenses/SyncMVD.txt

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

Isolated offline worker completed candidates204/217/231 with25 views, six-view micro-batch cap and30 global texture updates each. Sampling104.24/111.03/123.21s, peak3.194GiB. Renderer inspection found1172 selected latent UV cells, all visible to the capture pool. Baseline5397a3fb80a3 was cancelled through the UI during step7; restart/resume1a40e56890b9 reused source167, mask186 and seed24031. Completed native candidates survived. All three baked results preserve geometry, UVs, alpha, other maps and protected pixels, but produce blurred foundation material. Runtime integration succeeds; the masked adaptation fails art qualification. No model substitution or independent-view fallback.
