# Establish the fork and AEP governance

Spoke: S01
Outcome: The relocated clean upstream checkout has the requested fork, owner rules, accepted ADRs, and bounded plan.
Depends-on: none
Decisions: D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13
Constraints: C1, C2, C3, C4, C5, C6, C7, C8
Skills: aep:aep-core, git:git-core, claude:claude-core, patterns:patterns-core, planning:planning-core
Read-set: CLAUDE.md, pyproject.toml, ui/package.json, .gitignore, generated AEP files, owner-approved plan
Write-set: AGENTS.md, CLAUDE.md, CODE.md, .gitignore, .git/config, .git/hooks/pre-commit, .aep/standards.json, .codex/hooks.json, .claude/settings.json, .claude/aep-lint.json, .claude/aep-skills.json, .claude/rules/, docs/adr/, docs/plans/local-gpu/
State: done

## Context

This unit owns governance only. It must not install dependencies or models, start Effigy, run code tests, or release WU02. Expected 10 model turns; multi-file implementation ceiling 2250000 tokens, 256-turn circuit breaker, and 14500000 tokens per active hour. No wall-clock cap.

## Evidence

Prior stopped attempt, preserved after owner D12 resumed delivery:

NOT ACCEPTED: budget stop. Snapshot 2026-10-19 22:35:25 UTC; elapsed 706.8s from 22:23:39. Input 3533653 (cached 3466624), output 29933, total 3563586; 18150256 tokens/hour. Exceeds 2250000 total and 14500000/hour. No source continuation or next-unit release.

Fork LairdWT/Effigy created; D:/AI/Effigy on codex/local-gpu, origin/upstream set. AEP scaffold, owner rules, eight ADRs, and six plan spokes exist uncommitted. ADR check passed. Plan check failed: Snn IDs/plain filename cells and open-question formatting need correction. Standards/hook final inspection not run. Native analyzers remain unbound. Inherited .mcp.json entries and five Temp/Planning ADR drafts need review/cleanup in fresh bounded work. No dependencies/models/tests/runtime started.

Move-Item partially failed; copy-only recovery restored a clean D: checkout before edits. L: remainder preserved after approval policy blocked move/cleanup. No files deleted by that rejected command.

Current continuation:

- Upstream baseline c62db21 was clean before relocation; origin was SifuInTheShell/Effigy.
- pyproject.toml:4 declares Python >=3.12,<3.13; dependency groups preserve incompatible feature environments.
- The owner approved LairdWT/Effigy, the D: checkout, full feature scope, and no publication of local changes.
- The scaffold's .aep/standards.json contains empty native-provider bindings; installed profiles do not prove analyzer readiness.

## Steps

1. Verify both relocation paths and refuse to overwrite work. Complete the D: checkout from the existing clean source.
2. Create LairdWT/Effigy, retain upstream, set origin, and create codex/local-gpu without committing or pushing.
3. Run the existing AEP scaffold for Python, web, PowerShell, shell, and Git with multi-runtime instructions and no orchestration.
4. Align root instructions and hooks with owner authority. Preserve upstream technical context, remove test nudges and automatic artifact writers, and forbid implicit npm downloads.
5. Mint/populate/accept the scoped ADRs through AEP operations. Supersede the scaffold's wrapper-based verification decision with existing static commands; do not rewrite accepted bodies.
6. Materialize this index and all six spokes. Preserve installation and runtime units as unexecuted; record the analyzer admission gap explicitly.
7. Inspect structural correctness, update only this RESULT and index state, and stop.

## Files to touch

- AGENTS.md
- CLAUDE.md
- CODE.md
- .gitignore
- .git/config
- .git/hooks/pre-commit
- .aep/standards.json
- .codex/hooks.json
- .claude/settings.json
- .claude/aep-lint.json
- .claude/aep-skills.json
- .claude/rules/
- docs/adr/
- docs/plans/local-gpu/


## Verification

1. git remote -v and gh api repos/LairdWT/Effigy: correct fork parent and remotes.
2. git status --short and git diff --check: scoped uncommitted changes, no whitespace errors.
3. agent-code-skills adr check --target .: lifecycle and references pass.
4. agent-code-skills plan check docs/plans/local-gpu: structural plan check passes.
5. Project Ruff and the offline UI build pass. The 696-line AEP standards report remains advisory under owner decision D13; explicitly review semantic obligations.
6. Inspect hook commands: declared baseline checks, no tests, auto-downloads, or automatic handoff files. Hook trust/activation is not claimed.


## Risks

A Windows cross-drive Move-Item partially moved the tree before rejecting hidden Git-directory cleanup. Recovery copied only absent files to D:, whose Git status was clean; residual L: source files remain preserved. Automatic approval blocked a combined move/cleanup command, so no further cleanup is authorized by this result. Native provider binding is a separate discovered prerequisite for WU02.

## RESULT

Fork LairdWT/Effigy and D:/AI/Effigy checkout established on codex/local-gpu; changes remain uncommitted. Eleven ADRs record governance and workstation adaptations. Owner D13 accepted upstream Ruff/UI verification and mechanically superseded earlier strictness decisions. Hooks invoke installed tools without downloads or tests. AEP standards has not passed: existing annotations, unsupported batch profiles, and missing analyzer coverage remain advisory. Prior overrun history remains above.
