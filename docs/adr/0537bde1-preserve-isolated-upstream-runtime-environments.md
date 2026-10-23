---
id: 0537bde1-e5ca-450d-a704-a6110395debc
slug: adr:preserve-isolated-upstream-runtime-environments
title: Preserve isolated upstream runtime environments
status: accepted
supersedes: []
supersededBy: null
deciders: ["Laird"]
proposedAt: 2026-10-19
decidedAt: 2026-10-19
tags: []
---

## Context
Effigy has incompatible dependency groups and Python 3.12 CUDA wheels. Other local AI projects use different toolchains.

## Decision
Adopt the existing Effigy stack requested by the owner: preserve its frozen dependency names and versions, isolated backend/ML/skin/Kimodo/parts/GEM-X/MoGe environments, bundled wheels, and vendored engines. This is the build-versus-buy decision for the existing baseline, not approval for new dependency names. Do not import another project's pins or mutate another application's environment.

## Consequences
Provisioning retains upstream ABI boundaries. Required source analyzers need separate project-bound configuration before changed-source acceptance. Missing providers or incompatible frozen dependencies fail closed instead of causing silent upgrades.

## Alternatives
- Rebuild the full generation stack: rejected because the requested outcome is Effigy adoption.
- Unify dependencies with 3DGen: rejected because declared version conflicts and binary ABIs differ.
