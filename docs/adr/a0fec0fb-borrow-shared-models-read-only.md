---
id: a0fec0fb-9ad7-4105-9d96-a81fe33e39f8
slug: adr:borrow-shared-models-read-only
title: Borrow shared models read only
status: accepted
supersedes: []
supersededBy: null
deciders: ["Laird"]
proposedAt: 2026-10-19
decidedAt: 2026-10-19
tags: []
---

## Context
Canonical checkpoints live on the NAS. TRELLIS revision metadata matches upstream, but the loader writes generated configuration beside weights and model management exposes mutation operations.

## Decision
One resolver distinguishes borrowed shared files from owned Effigy downloads. Borrowed files are read-only across load, status, repair, removal, and relocation, including resolved links. Store generated configuration and scratch outside borrowed directories. Put new downloads under the canonical NAS store. Use existing revision metadata and expected sizes for reuse; do not rehash borrowed weights. Preserve existing DINOv3 and provision the required different revision separately.

## Consequences
Reuse avoids duplicate TRELLIS payloads without granting write authority. Only new installation downloads receive integrity checks. Exactly two canonical storage audits bracket installation; no extra evidence packs are authorized.

## Alternatives
- Link shared folders and retain in-place writes: rejected because canonical assets would become writable by the consumer.
- Duplicate every checkpoint on local disk: rejected because it defeats NAS ownership and reuse.
