# Provision pinned isolated SyncMVD runtime and models

Spoke: S07
Outcome: Provision pinned isolated SyncMVD runtime and models
Depends-on: S06
Decisions: D7, D8, D9, D10, D11, D12
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, planning:planning-core
Read-set: CODE.md, docs/plans/multi-view-paint/INDEX.md
Write-set: tools/provision_syncmvd.py, requirements-syncmvd.in, requirements-syncmvd.lock, docs/adr
State: done

## Context

Owner approved the full-view revision on 2026-10-21. Prior paired-sheet anchors failed stone scale and mortar alignment; preserve their RESULT sections and rejected assets. Activate only trial 8380. Expected turns: 12; preserve usage history and standing circuit breakers. No per-unit handoff stops.

## Evidence

- server/paint_sessions.py:26 owns session creation; steps/_paint_set.py:25 owns surface projection.
- Session owner: server/paint_sessions.py; fixed captures and protected bake: steps/_paint_set.py.
- Prior S01-S05 RESULT sections distinguish implementation from incomplete visual and lifecycle acceptance.
- Source 167_upload and foundation selection 173_paint_set retain 409 triangles and the existing 1024 RGBA16 atlas.
- The earlier coverage calculation found fifteen cameras covering 92238 reachable texels; actual 512-resolution coverage must be recalculated.
- SyncMVD source: https://github.com/LIU-Yuxin/SyncMVD . MOSS v2 Euler recipe: https://huggingface.co/akhaliq/MOSS-Image-SFT-4-steps .

## Steps

Record the approved build-versus-buy dependency ADR through AEP tooling. Pin upstream SyncMVD source and preserve attribution. Create one isolated Python 3.12, Torch 2.8/CUDA 12.8 environment with a separate frozen lock. Provision SD1.5 and normal ControlNet plus required components into Effigy-owned NAS storage. D15 replaces the initially gated Benjamin-Paine distribution with stable-diffusion-v1-5/stable-diffusion-v1-5 at451f4fe16113bff5a5d2269ed5ad43b0592e9a14. Do not install PyTorch3D or modify another environment. Runtime resolves pinned local paths; required installation checks do not authorize borrowed-model hash sweeps.

## Files to touch

- tools/provision_syncmvd.py
- requirements-syncmvd.in
- requirements-syncmvd.lock
- docs/adr

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

Provisioned isolated Python3.12.12/Torch2.8.0+cu128 and frozen49-package lock; Diffusers/ControlNet/CLIP imports succeed. SyncMVD source faa95621 and MIT attribution retained. Initial SD1.5 distribution returned401 with no local token. Owner D15 approved ungated mirror451f4fe; accepted ADR62df929a mechanically supersedes c73be29e. Downloaded required SD1.5 components (2134194125 bytes) and normal ControlNet cb7296e (722598642-byte FP16 weights) into owned NAS storage. syncmvd.local.json now records ready=true. Borrowed MOSS files and existing environments unchanged. Scoped Ruff passes. This establishes provisioning, not synchronized runtime or art acceptance.

