---
id: 9bf1bd0d-6244-4dfa-86cb-fbec435d6cf3
slug: adr:use-static-checks-and-runtime-samples
title: Use static checks and runtime samples
status: superseded
supersedes: [adr:proportional-verification]
supersededBy: adr:preserve-upstream-checks-for-baseline-adaptation
deciders: ["Laird"]
proposedAt: 2026-10-19
decidedAt: 2026-10-19
tags: []
---

## Context
The owner selected static checks and normal application runtime samples while prohibiting code tests. Scaffolding initially named a proposed PowerShell wrapper, but existing commands cover verification without another script.

## Decision
Routine is agent-code-skills standards check --changed. Complete uses ADR check, plan check, changed-source standards, the installed project Ruff executable, and the offline npm UI build, as listed in CODE.md. Run Complete only at an authorized milestone with its project tools available. WU01 uses governance structural inspection; WU05 uses application samples. Do not run code tests, install tools from checks, suppress required native analysis, or automatically create handoff files.

## Consequences
Supersede the initial wrapper-command scaffold decision without altering its body. Governance inspection does not qualify native analyzers, hook trust, or runtime behavior. Missing providers block affected source acceptance. Verification does not authorize commits, pushes, or CI.

## Alternatives
- Add a wrapper solely to invoke existing commands: rejected because it adds code and analyzer prerequisites without needed behavior.
- Run upstream code-test suites: rejected because the owner selected runtime samples only.
