---
id: 8111a65d-413b-4186-b6bf-3e7396624b68
slug: adr:proportional-verification
title: Proportional verification
status: superseded
supersedes: []
supersededBy: adr:use-static-checks-and-runtime-samples
deciders: ["project owner"]
proposedAt: 2026-10-19
decidedAt: 2026-10-19
tags: []
---

## Context
A single full-suite command for every edit is disproportionate, while fast checks alone cannot prove changed behavior or whole-repository health.

## Decision
Verification has proportional tiers. Routine feedback is `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1 -Mode Routine` and is the pre-commit tier. Each task also runs proof scoped to the behavior changed and records that command in its plan or WorkUnit. Complete is `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1 -Mode Complete` and runs for CI, landing, release, or an explicitly named milestone.

## Consequences
Evidence identifies which boundary it proves: fast feedback, task behavior, or the complete repository contract.

## Alternatives
- Run Complete after every edit: slow feedback unrelated to the current risk. Rejected.
- Treat Routine as sufficient proof: misses changed behavior and cross-repository regressions. Rejected.
