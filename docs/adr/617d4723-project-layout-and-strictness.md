---
id: 617d4723-701a-4877-9362-00bc52966fd5
slug: adr:project-layout-and-strictness
title: Project layout and strictness
status: superseded
supersedes: []
supersededBy: adr:preserve-upstream-checks-for-baseline-adaptation
deciders: ["project owner"]
proposedAt: 2026-10-19
decidedAt: 2026-10-19
tags: []
---

## Context
The AEP layer (CLAUDE.md, CODE.md, docs/adr/, .claude/) needs a declared enforcement posture.

## Decision
Strictness is required: whole changed files, native analysis and explicit semantic review; unavailable checks block acceptance. ADRs are uuid-named (never sequential). Agent transients live under Temp/ only.

## Consequences
The posture can be raised by a superseding ADR when concurrency or audit pressure demands it (conventions -> gates -> locks -> services).

## Alternatives
- Day-one service-mediated governance: top-rung machinery without the pressure that justifies it. Rejected.
