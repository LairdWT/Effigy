---
id: cb12259a-354d-4d3a-a206-120c522e1527
slug: adr:reuse-configured-portable-blender
title: Reuse configured portable Blender
status: accepted
supersedes: []
supersededBy: null
deciders: ["Laird"]
proposedAt: 2026-10-19
decidedAt: 2026-10-19
tags: []
---

## Context
Upstream pins Blender 5.2.2. The owner selected the existing portable 5.2.0 resolved through 3DGen's tools configuration, with runtime qualification.

## Decision
Resolve Blender through the configured tools file and pass the existing Effigy executable override. Never use PATH Blender, embed a workstation-absolute executable path in tracked code, replace the shared installation, or silently download upstream Blender. Qualify 5.2.0 through the approved asset, export, and live-link samples.

## Consequences
Executable discovery does not prove compatibility. A failed Blender-dependent capability remains incomplete until the owner decides a remediation.

## Alternatives
- Automatically install 5.2.2: rejected because the owner selected reuse.
- Assume patch-version parity: rejected because no runtime sample has established it.
