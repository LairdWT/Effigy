---
id: 7bba3f6b-4851-498e-acd1-78f23a8f7523
slug: adr:preserve-upstream-checks-for-baseline-adaptation
title: Preserve upstream checks for baseline adaptation
status: accepted
supersedes: [adr:project-layout-and-strictness, adr:use-static-checks-and-runtime-samples]
supersededBy: null
deciders: ["Laird"]
proposedAt: 2026-10-20
decidedAt: 2026-10-20
tags: []
---

## Context
The owner requested a baseline Effigy adaptation, preserved upstream dependencies and technical guidance, source checks and a UI build, and no code tests. The initial AEP scaffold also accepted whole-file strict migration. Its changed-file check now reports 696 lines of findings, including existing upstream annotations and unavailable ShellCheck/type-aware web lint providers. Project Ruff and the strict upstream TypeScript build pass. Retrofitting every affected upstream file would materially expand the setup scope.

## Decision
Proposed for owner selection: keep AEP instructions, plans, ADRs, ownership boundaries and semantic review, while using the approved upstream verification tools for this baseline adaptation. Routine uses project Ruff on authored changes; Complete adds the UI TypeScript/Vite build and ADR/plan structural checks. Keep AEP standards inspection available as an advisory migration report, and record its unresolved findings explicitly. Do not describe that report as passing. A future owner-issued strict migration can add the missing analyzers and migrate whole files. No tests, model hashes, downloads from verification, commits or pushes are introduced.

## Consequences
The baseline can be accepted against its declared installation/runtime requirements without a broad upstream type refactor or new analyzer dependencies. Verification hooks would invoke the actual project source checker and UI build instead of an unprovisioned strict migration gate. This is a visible policy change requiring owner selection, not a silent suppression. Existing strictness and verification ADRs must be superseded mechanically if selected.

## Alternatives
- Require full AEP migration now: retain the current strict gate, provision approved analyzers and refactor every affected upstream file before source acceptance; significantly broader than setup.
- Silently classify modified files as third-party or report strict checks as passing: rejected.
