# Establish an AEP-governed local-only Effigy setup

## Outcome

Run every supported Effigy feature on the RTX 5090 using separate online provisioning, offline runtime, NAS models, and runtime sample acceptance. Implementation and provisioning are complete. Every requested feature family has runtime samples. SkinTokens-only stretch quality remains unaccepted; the automatic skinning path selected Blender weights with zero QA failures. Observed offline behavior passed after the documented browser-policy correction; this is not OS containment.

## Decisions

Owner-confirmed on 2026-10-19; preserve these decisions verbatim.

- D1: Everything, including 2D and video-to-motion.
- D2: Separate online provisioning; offline runtime.
- D3: Establish the supported baseline first; evaluate model upgrades afterward.
- D4: Create LairdWT/Effigy on GitHub from the outset and configure it as an AEP project.
- D5: Use D:/AI/Effigy for source, environments, caches, and scratch.
- D6: Keep models under N:/generated/3DGen-models; generated asset library under N:/generated/Effigy.
- D7: Permit required integrity checks for newly installed downloads; no additional hash sweeps or runtime model hashing.
- D8: Acceptance uses runtime samples only. Do not write or run code tests.
- D9: Enforce offline behavior through application controls and connection observation; do not change Windows firewall rules.
- D10: Permit exactly two canonical storage audit reports, before and after installation. No additional evidence packs.
- D11: Create the GitHub fork, but leave implementation changes uncommitted until explicitly authorized.

- D12 (2026-10-20): Owner instructed "Complete the work" after the saved-progress stop. Continue the authorized delivery in this chat, bootstrap frozen tool environments before source checks, and do not require per-unit handoff/release messages. Preserve previous overrun history.
- D13 (2026-10-20): Owner selected upstream checks for this baseline. Ruff, the UI build, and ADR/plan checks govern source acceptance; broader AEP standards findings remain advisory under adr:preserve-upstream-checks-for-baseline-adaptation.

## Constraints

- C1: Preserve shared models, other application environments, configured Blender, and foreign GPU work.
- C2: Preserve upstream Python 3.12 dependency groups and CUDA ABI boundaries. New dependency names require owner approval and a build-versus-buy ADR.
- C3: Resolve portable Blender through 3DGen tools.config.json; qualify 5.2.0 against upstream's 5.2.2 expectations. No replacement installation.
- C4: No hosted inference, uploads, telemetry, automatic runtime downloads, hosted MCP registration, or firewall changes.
- C5: No subagents, Astra, automatic upstream updates, commits, pushes, CI runs, code tests, or extra evidence packs.
- C6: D12 authorizes continuous execution here. Keep bounded scopes, dependency proof, and previous usage history; do not stop at administrative handoff boundaries.
- C7: Each unit uses its expected turns, 256-turn breaker, class token ceiling, and 14500000 tokens per active hour. No wall-clock cap. Stop for budget exhaustion or material mismatch.
- C8: Source, installation, GPU behavior, output quality, hook activation, and publication are separate claims. D13 defines source acceptance; unresolved advisory standards findings remain recorded.

## Requirements

| ID | Requirement | Implementation | Acceptance |
|---|---|---|---|
| R1 | Full supported feature coverage | S04 | S05 |
| R2 | Offline runtime and separate provisioning | S02 | S05 |
| R3 | Safe NAS reuse and model ownership | S03 | S04, S05 |
| R4 | AEP project and maintainable fork | S01 | Structural inspection |
| R5 | Usable GPU launch and persistent library | S02, S03, S04 | S05 |
| R6 | Decision-ready upgrade shortlist | S06 | Owner selection before integration |

## Terms

Spokes S01-S06 retain WU01-WU06 scopes and usage history.

- borrowed model: an existing shared checkpoint that Effigy may read but may not mutate, repair, move, delete, or rehash.
- owned model: a checkpoint explicitly provisioned into Effigy's dedicated NAS subtree.
- baseline: upstream-supported models and features with only changes required for local operation, storage ownership, and this workstation.

## Spokes

| ID | File | Outcome | Depends on | Skills | Write set | State | Commit | Result |
|---|---|---|---|---|---|---|---|---|
| S01 | 01-fork-aep.md | The relocated clean upstream checkout has the requested fork, owner rules, accepted ADRs, and bounded plan. | none | aep:aep-core, git:git-core, claude:claude-core, patterns:patterns-core, planning:planning-core | AGENTS.md, CLAUDE.md, CODE.md, .gitignore, .git/config, .git/hooks/pre-commit, .aep/standards.json, .codex/hooks.json, .claude/settings.json, .claude/aep-lint.json, .claude/aep-skills.json, .claude/rules/, docs/adr/, docs/plans/local-gpu/ | done | - | 01-fork-aep.md#result |
| S02 | 02-offline-runtime.md | Normal startup and every worker operate locally without provisioning or external service calls. | S01 | aep:aep-core, python:python-core, powershell:powershell-core, web:typescript-core | server/runtime_policy.py, steps/_common.py, provision.bat, .mcp.json, server/__main__.py, server/app.py, server/jobs.py, server/hf.py, server/install.py, steps/concepts.py, steps/_birefnet.py, steps/canon.py, steps/refine.py, steps/layers.py, steps/motion.py, run.bat, run.sh, tools/provision.py, ui/src/api.ts, ui/src/main.tsx, docs/LOCAL-SETUP.md, server/blender_client.py, tools/blender_session.py, blender_ops/session_bridge.py, steps/_blender.py, steps/mocap.py, steps/import_motion.py | done | - | 02-offline-runtime.md#result |
| S03 | 03-nas-models.md | One resolver makes shared model assets read-only while keeping Effigy downloads and generated configuration owned. | S02 | python:python-core | server/model_bindings.py, server/settings.py, server/models.py, server/storage.py, server/machine.py, server/install.py, server/jobs.py, steps/trellis2.py, tools/download_models.py, model-bindings.local.json, settings.json, scratch/, N:/generated/3DGen-models/Effigy/, N:/generated/Effigy/, D:/AI/3DGen/Temp/Storage/effigy-before-20261020.json, tools/model_sources.py, tools/model_sources.json, tools/models_manifest.json | done | - | 03-nas-models.md#result |
| S04 | 04-provision-baseline.md | Every requested feature has its frozen environment and local model dependencies installed or an explicit unresolved access failure. | S03 | python:python-core | .python-version, .venv*/, python/, cache/, ui/node_modules/, ui/dist/, gltfpack/, settings.json, N:/generated/3DGen-models/Effigy/, D:/AI/3DGen/Temp/Storage/effigy-after-20261020.json | done | - | 04-provision-baseline.md#result |
| S05 | 05-runtime-acceptance.md | Representative normal application operations establish the observed full baseline, with precise incomplete capabilities. | S04 | planning:planning-core | N:/generated/Effigy/, scratch/, docs/plans/local-gpu/05-runtime-acceptance.md, steps/parts.py, engine/geosam2/PATCHES.md, steps/mocap.py, steps/import_motion.py | done | - | 05-runtime-acceptance.md#result |
| S06 | 06-upgrade-options.md | The owner can select a supported upgrade experiment without altering the accepted baseline. | S05 | planning:planning-core, planning:primary-source-research, python:python-core | docs/plans/local-gpu/06-upgrade-options.md | done | - | 06-upgrade-options.md#result |

## Reading rule

Read this index, the assigned spoke, and only dependency RESULT sections. Every spoke owns its result; update index and header state together. Expected turns are planning estimates, not expanded authorization. The parent remains incomplete until its requirements have acceptance.

## Non-goals

Training, LoRA creation, replacing 3DGen/ComfyUI, automatic upgrades, OS network containment, hosted integrations, code tests, benchmark campaigns, and publication of local changes.

## Open questions

- Deferred: select an upgrade proposal only when the owner chooses a candidate; resume integration after that explicit selection. Baseline setup has no remaining installation dependency or credential blocker.
