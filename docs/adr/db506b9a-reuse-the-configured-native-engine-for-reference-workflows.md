---
id: db506b9a-ddcb-4f25-b4f0-e56ad1a100b4
slug: adr:reuse-the-configured-native-engine-for-reference-workflows
title: Reuse the configured native engine for reference workflows
status: accepted
supersedes: []
supersededBy: null
deciders: ["Laird"]
proposedAt: 2026-10-20
decidedAt: 2026-10-20
tags: []
---

## Context
The owner requested that existing Krea2, anime and Qwen checkpoints be set up for Effigy's mesh, texture and animation workflow, and selected existing files with no model downloads. Those files use Comfy-compatible quantized layouts and separate encoders. The configured workstation already has a working native engine, while Effigy's frozen baseline environments must retain their own dependencies.

## Decision
Reuse the configured native engine as an isolated Effigy reference worker. Resolve its interpreter and source through the owner-selected tools.config.json, and resolve every model, encoder and VAE through Effigy's read-only model-binding owner. Run it under the existing job lock, cancellation, offline policy, GPU budget and scratch/publication protocol. Add normal reference generation and Qwen reference-edit-to-retexture controls. TRELLIS continues to own mesh generation and texture transfer; existing rig and animation stages remain responsible for motion. Keep baseline choices available. Install no packages and change no shared engine files or model payloads.

## Consequences
The optional model workflows depend on the configured external engine being present. Local Setup reports availability; missing tools or weights fail with actionable local errors. The worker records the actual native versions and model identities. This introduces a maintained adapter boundary, whose runtime compatibility requires application samples. No hosted calls, model downloads, tests, hashes, commits or pushes are introduced.

## Alternatives
- Convert all checkpoints and encoders to Diffusers layouts: additional adapter work and potentially model/package provisioning, contrary to the selected reuse boundary.
- Treat standalone images as completion: rejected by the owner's workflow correction.
- Merge the native engine's pins into the baseline environments: rejected because it risks the accepted stack.
