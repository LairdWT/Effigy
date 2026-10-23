---
id: 70792dba-9692-4c45-8f3a-55e73511891f
slug: adr:resolve-pinned-runtime-objects-from-equivalent-local-and-public-sources
title: Resolve pinned runtime objects from equivalent local and public sources
status: accepted
supersedes: []
supersededBy: null
deciders: ["Laird"]
proposedAt: 2026-10-19
decidedAt: 2026-10-19
tags: []
---

## Context
The baseline DINOv3 and Llama repositories require account approval. Provisioning could read their published manifests but could not fetch their payloads. Existing DINOv3 download metadata records a different revision; every required file has the same published object identifier and byte size as Effigy's pinned snapshot. The pinned public NousResearch Llama mirror also exposes the same weights, configuration, tokenizer, and license objects as the requested Meta snapshot.

## Decision
Preserve the baseline runtime objects through explicit source bindings. Borrow the existing DINOv3 read-only, retaining both source and requested revisions plus recorded file object identifiers. Provision Llama from NousResearch/Meta-Llama-3-8B-Instruct revision 53346005fb0ef11d3b6a83b12c895cca40156b6c only after its published object identifiers match tools/model_sources.json. Place it under Effigy's owned canonical cache identity for Meta revision 8afb486c1db24fe5011ec46dfbe5b5dccdb575c2, with installation provenance naming the actual source. Exclude original/params.json, which belongs to the unused original-format loader. Pin refs/main to the selected owned snapshot for loaders that omit a revision.

## Consequences
No login is needed for these two dependencies on this workstation. This changes transport and storage binding, not runtime weights or tokenizer selection. Metadata equivalence is not a newly computed payload hash; shared files remain unmodified and unrehashable. The downloader validates newly installed source metadata. Runtime sample quality and compatibility remain separate acceptance requirements. This implementation follows the owner's baseline-first and read-only-reuse scope.

## Alternatives
- Require new account approval and duplicate DINOv3: unnecessary when the complete runtime file objects match.
- Substitute different weights or tokenizer files: outside baseline scope and rejected.
- Hash all borrowed payloads: prohibited by the owner.
