---
id: 0778b139-f493-4aef-95b0-189667c434aa
slug: adr:language-set-and-toolchain
title: Language set and toolchain
status: accepted
supersedes: []
supersededBy: null
deciders: ["project owner"]
proposedAt: 2026-10-19
decidedAt: 2026-10-19
tags: []
---

## Context
The project needs a declared language set so standards, rules, and tooling bind to something stable.

## Decision
Languages: python, web, powershell, shell, git. Conventions bind by reference through CODE.md pins to the agent-enhanced-project bundles.

## Consequences
Adding a language is a superseding decision plus a CODE.md pin, not an ad hoc drift.

## Alternatives
- Unpinned per-project standards documents: proven to bloat and drift. Rejected.
