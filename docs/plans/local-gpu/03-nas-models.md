# Bind borrowed and owned NAS models

Spoke: S03
Outcome: One resolver makes shared model assets read-only while keeping Effigy downloads and generated configuration owned.
Depends-on: S02
Decisions: D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13
Constraints: C1, C2, C3, C4, C5, C6, C7, C8
Skills: python:python-core
Read-set: INDEX.md, 02-offline-runtime.md#result, CODE.md, accepted model and Blender ADRs, server/settings.py, server/models.py, server/storage.py, server/machine.py, server/install.py, server/jobs.py, steps/trellis2.py, tools/download_models.py, tools/models_manifest.json
Write-set: server/model_bindings.py, server/settings.py, server/models.py, server/storage.py, server/machine.py, server/install.py, server/jobs.py, steps/trellis2.py, tools/download_models.py, model-bindings.local.json, settings.json, scratch/, N:/generated/3DGen-models/Effigy/, N:/generated/Effigy/, D:/AI/3DGen/Temp/Storage/effigy-before-20261020.json, tools/model_sources.py, tools/model_sources.json, tools/models_manifest.json
State: done

## Context

Expected 18 model turns, implementation ceiling 2250000 tokens, 256 turns, and 14500000 tokens per active hour. Load the owner's 3DGen model-storage skill before storage effects. Use its canonical inventory without moving or retiring existing payloads. This unit owns the first of exactly two authorized storage audit reports.

## Evidence

- steps/trellis2.py:120 and :167 write generated pipeline JSON beside model files.
- server/settings.py selects EFFIGY_MODELS or user settings.
- server/install.py:349 owns repair damage checks and deletion; all borrowed paths need explicit exclusion.
- Existing TRELLIS.2 revision af44b45f2e35a493886929c6d786e563ec68364d and TRELLIS-image-large revision 25e0d31ffbebe4b5a97464dd851910efc3002d96 match recorded metadata and expected sizes (about 15.3 GiB).
- Existing DINOv3 metadata records 3f8a045b38486fd86d899b1194e038b53fa80906, not Effigy's ea8dc2863c51be0a264bab82070e3e8836b02d51.

## Steps

1. Run the canonical before-installation storage audit once; keep its authorized report under the existing 3DGen Temp/Storage directory.
2. Configure owned downloads and HF cache under N:/generated/3DGen-models/Effigy, library under N:/generated/Effigy, and scratch under the local Effigy root. Keep machine bindings ignored by Git.
3. Introduce one typed resolution boundary distinguishing [[borrowed model]] from [[owned model]]. Route loading, readiness, repair, remove, and relocate through it.
4. Reuse the two existing TRELLIS repositories by path without copies, mutation, or new hashes. Bind existing DINOv3 read-only using complete matching published file objects and both revisions, as recorded in adr:resolve-pinned-runtime-objects-from-equivalent-local-and-public-sources.
5. Write generated TRELLIS configuration to owned scratch, resolving checkpoint paths explicitly. Never junction a borrowed directory into a writable destination.
6. Guard canonical and resolved paths so links cannot grant write authority over borrowed assets. Preserve all existing storage and GPU work.

## Files to touch

- server/model_bindings.py
- server/settings.py
- server/models.py
- server/storage.py
- server/machine.py
- server/install.py
- server/jobs.py
- steps/trellis2.py
- tools/download_models.py
- model-bindings.local.json
- settings.json
- scratch/
- N:/generated/3DGen-models/Effigy/
- N:/generated/Effigy/
- D:/AI/3DGen/Temp/Storage/effigy-before-20261020.json
- tools/model_sources.py
- tools/model_sources.json
- tools/models_manifest.json


## Verification

1. Required changed-source static checks pass without code tests or hash sweeps.
2. Source tracing covers every loader and management mutation using the binding owner.
3. Configuration names exact approved roots and preserves the pre-install audit for WU04 comparison.
4. Runtime model loading and representative non-destructive refusal observations belong to WU05.


## Risks

Directory aliasing can hide writes and double-count storage. Size/revision metadata is reuse evidence, not newly computed byte identity. Do not delete, migrate, repair, or rehash shared assets to make an installer accept them.

## RESULT

Shared TRELLIS repositories and exact-object DINOv3 are read-only bindings. Owned NAS cache/library and D: runtime scratch configured. Required public Llama mirror retains requested and source revisions plus installation provenance; no shared payload hashes computed. Borrowed model deletion returned 403. Generated Fast pipeline loaded from scratch successfully. Before audit: D:/AI/3DGen/Temp/Storage/effigy-before-20261020.json. Its preexisting C: free-space reserve failure does not describe the selected D:/N: destinations.
