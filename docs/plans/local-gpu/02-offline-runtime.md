# Separate provisioning from offline runtime

Spoke: S02
Outcome: Normal startup and every worker operate locally without provisioning or external service calls.
Depends-on: S01
Decisions: D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13
Constraints: C1, C2, C3, C4, C5, C6, C7, C8
Skills: aep:aep-core, python:python-core, powershell:powershell-core, web:typescript-core
Read-set: INDEX.md, 01-fork-aep.md#result, CODE.md, .aep/standards.json, server/__main__.py, server/jobs.py, server/hf.py, server/app.py, server/install.py, run.bat, run.sh, ui/src/api.ts, ui/src/main.tsx, affected model loaders
Write-set: server/runtime_policy.py, steps/_common.py, provision.bat, .mcp.json, server/__main__.py, server/app.py, server/jobs.py, server/hf.py, server/install.py, steps/concepts.py, steps/_birefnet.py, steps/canon.py, steps/refine.py, steps/layers.py, steps/motion.py, run.bat, run.sh, tools/provision.py, ui/src/api.ts, ui/src/main.tsx, docs/LOCAL-SETUP.md, server/blender_client.py, tools/blender_session.py, blender_ops/session_bridge.py, steps/_blender.py, steps/mocap.py, steps/import_motion.py
State: done

## Context

Owner-issued source unit; expected 20 model turns, implementation ceiling 2250000 tokens, 256 turns, and 14500000 tokens per active hour. Prior admission gap, resumed under D12: required Python/UI native analyzers are unbound, while provisioning was scheduled for WU04. D12 authorized frozen-environment bootstrap and continuous delivery here. No additional dependency names are introduced.

## Evidence

- server/__main__.py binds 127.0.0.1; 8370 was free during planning and must be checked at launch.
- server/jobs.py:154 owns worker environment composition.
- server/hf.py:23 embeds online whoami/auth_check operations; Setup invokes its status endpoint.
- steps/concepts.py:82 loads by Hugging Face ID; steps/canon.py:58 loads a local pipeline.
- run.bat combines environment synchronization, supporting-tool downloads, UI build, and runtime launch.

## Steps

1. Bind available project analyzers under D12; retain offline and no-tests constraints.
2. Add one runtime-policy owner and separate provisioning/runtime entrypoints. Normal startup launches installed code without uv sync, npm install, or download helpers.
3. Bind 127.0.0.1:8370; an occupied port is an actionable error, never a silent fallback or LAN bind.
4. Propagate HF_HUB_OFFLINE, TRANSFORMERS_OFFLINE, telemetry-disable settings, and offline package-tool settings to workers. Resolve every model locally; no hosted fallback.
5. Guard online install/repair and Hugging Face account calls in normal runtime. Setup displays local readiness and directs missing components to explicit provisioning.
6. Keep existing API operations, library, generation, and export contracts. Document local launch/stop and the separate provisioning command. Do not register MCP with a hosted client.

## Files to touch

- server/runtime_policy.py
- steps/_common.py
- provision.bat
- .mcp.json
- server/__main__.py
- server/app.py
- server/jobs.py
- server/hf.py
- server/install.py
- steps/concepts.py
- steps/_birefnet.py
- steps/canon.py
- steps/refine.py
- steps/layers.py
- steps/motion.py
- run.bat
- run.sh
- tools/provision.py
- ui/src/api.ts
- ui/src/main.tsx
- docs/LOCAL-SETUP.md
- server/blender_client.py
- tools/blender_session.py
- blender_ops/session_bridge.py
- steps/_blender.py
- steps/mocap.py
- steps/import_motion.py


## Verification

1. Inspect complete changed files and run project-bound required static analyzers without installing anything from a check.
2. Missing local dependencies produce explicit failure; startup and UI sources contain no implicit provisioning path.
3. Actual offline operation is accepted only by WU05 runtime samples and connection observation, not this source inspection.
4. No code tests, model execution, download, firewall mutation, or model hashes in this unit.


## Risks

Offline SDK flags alone do not cover arbitrary HTTP calls. Trace backend, worker, browser, and vendored loader entrypoints. Preserve existing typed API error behavior and avoid disguising an unavailable component as ready. Owner D13 selects upstream Ruff and UI build checks; broader AEP findings remain advisory.

## RESULT

Separate provisioning and direct run.bat startup implemented at 127.0.0.1:8370. Offline worker flags, Python socket guard, local loaders, disabled install/account actions, and same-origin browser policy are active. Final policy allows local GLB blobs; browser violations remained zero after restart, animated export and playback. Install and borrowed-delete refusals returned 403 earlier. Isolated Blender bridge uses 8371. Ruff/UI build pass. Broader standards findings remain advisory under D13; connection observation is not OS containment.
