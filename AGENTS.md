# Effigy agent bootstrap

- `CODE.md` is binding. Before changes read it, relevant accepted `docs/adr/` decisions, and matching path rules.
- Start AEP-enabled work with `aep:aep-core`; select the smallest domain `*-core` or spoke and load only its route. Languages: python, web, powershell, shell, git.
- Verification is proportional: use CODE.md Routine for fast feedback and pre-commit, task-scoped proof for changed behavior, and CODE.md Complete for CI, landing, release, or an explicitly named milestone.
- Lint/format: project Ruff and the UI TypeScript build. No automatic formatting, synchronization, or downloads from hooks.
- Noisy commands: `agent-code-skills logstrip run -- <cmd>`.
- Never edit accepted ADR history; supersede it. No third-party dependency without owner approval and a build-vs-buy ADR.
- Follow CODE.md and review semantic obligations explicitly. The owner selected upstream Ruff and the UI build for this baseline; AEP standards findings remain advisory under adr:preserve-upstream-checks-for-baseline-adaptation. No automatic tests or hashing.
- Use explicit boundary types, logged negative guards, small capability interfaces, composition, and one state owner.
- Nontrivial work follows `planning:plan-authoring`; keep transients under `Temp/`.
- No decisions in source comments, secret leakage, hook bypasses, or unsupported success claims.

## Owner contract

- Follow `docs/plans/local-gpu/INDEX.md`. Owner direction on 2026-10-20 authorizes completing the approved delivery here without per-unit handoff stops; preserve bounded work scopes and prior usage history. No subagents or Astra. No commits, pushes, or CI runs without explicit owner instruction.
- Do not write or run code tests. Static checks and explicitly authorized application samples are separate; never rename a prohibited test as a sample.
- Runtime must remain offline. Public downloads belong to separate provisioning. No hosted inference, uploads, telemetry, automatic downloads, firewall changes, or hosted MCP registration - adr:separate-online-provisioning-from-offline-runtime.
- Borrowed shared models are read-only: never modify, repair, move, delete, or rehash them. Newly installed downloads retain installation-only integrity checks - adr:borrow-shared-models-read-only.
- Preserve other GPU workloads. Refuse or wait for memory; never kill, cancel, or unload another application's work.
- Resolve Blender through the owner-selected 3DGen `tools.config.json`, never PATH or machine-absolute tracked code. Qualify the installed 5.2.0 against upstream's 5.2.2 expectations - adr:reuse-configured-portable-blender.
- Preserve upstream Python 3.12 groups and CUDA wheel ABIs independently of other projects - adr:preserve-isolated-upstream-runtime-environments.
- Authorized artifacts are plan/ADR sources, ordinary application output, and exactly two canonical storage audits bracketing installation. No extra evidence packs or automatic handoff files. Record each WorkUnit result in its owning spoke.
- Keep each unit scoped and retain its usage history; the owner resumed this delivery after the documented overrun on 2026-10-20. No wall-clock cap or automatic next-unit dispatch. Stop and record a RESULT handoff on budget exhaustion or material mismatch.
- Preserve owner/foreign work. New dependency names beyond the approved frozen upstream baseline need owner approval and a build-versus-buy ADR.

## Upstream contracts and skills

- Read `docs/IMPLEMENTATION.md` for frozen step files, frames, subprocess protocol, and APIs. Keep Torch out of the backend and heavy models in dedicated workers.
- Preserve vendored engines, bundled wheels, and notices unless an accepted bounded change owns them. The upstream reference-laptop handover is not this workstation's state.
- `docs/PLAN.md`, `docs/ARCHITECTURE.md`, `docs/WORKFLOW.md`, and `SETUP.md` describe upstream behavior; accepted fork ADRs govern deviations.
- `run.bat` and `run.sh` start the installed offline runtime; public provisioning is a separate `provision.bat` operation.
- Route planning through `planning:planning-core`, Python through `python:python-core`, UI through `web:typescript-core` or `web:css-core`, Windows launchers through `powershell:powershell-core`, POSIX launchers through `shell:shell-core`, Git through `git:git-core`, and ADRs through `patterns:patterns-core`.
- Use `aep:aep-terse` and `aep:aep-unslop` for text. Upstream convenience skills and agent definitions cannot override this contract.

<!-- aep-text-mode:begin -->
## Text output

<!-- aep-text-contract:2 -->
- AEP prose baseline: write directly, naturally, and precisely. Remove filler, puffery, vague claims, canned AI phrasing, sycophancy, repetition, and empty conclusions.
- Preserve exact facts, technical terms, code, commands, errors, quotations, citations, numbers, negation, ordering, required formats, and requested tone. Never invent sentiment, experience, sources, credentials, or certainty.
- AEP text mode: ultra. Lead with result; status <= 3 prose lines; substantive conversational prose <= 12. Fragments and ASCII `->`/`<-` are allowed.
- Use normal-length prose for security warnings, irreversible confirmations, ambiguity, or requested clarification; the prose baseline still applies.
- Voice artifacts are exempt: do not restyle TTS input, SSML, dialogue, narration, audio prompts, STT transcripts, or speech-generation/recognition text. Ordinary chat remains ultra if a UI later reads it aloud.
<!-- aep-text-mode:end -->
