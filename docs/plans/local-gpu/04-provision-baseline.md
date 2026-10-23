# Provision the complete supported baseline

Spoke: S04
Outcome: Every requested feature has its frozen environment and local model dependencies installed or an explicit unresolved access failure.
Depends-on: S03
Decisions: D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13
Constraints: C1, C2, C3, C4, C5, C6, C7, C8
Skills: python:python-core
Read-set: INDEX.md, 03-nas-models.md#result, CODE.md, provisioning entrypoint and local settings, pyproject.toml, uv.lock, ui/package-lock.json, tools/download_models.py, tools/models_manifest.json, before-installation audit
Write-set: .python-version, .venv*/, python/, cache/, ui/node_modules/, ui/dist/, gltfpack/, settings.json, N:/generated/3DGen-models/Effigy/, D:/AI/3DGen/Temp/Storage/effigy-after-20261020.json
State: done

## Context

Expected 12 model turns, implementation ceiling 2250000 tokens, 256 turns, and 14500000 tokens per active hour. Public provisioning is authorized; private data stays outside it. The manifest totals about 145 GiB before borrowed reuse. This unit creates the second and final authorized storage audit report.

## Evidence

- pyproject.toml pins Python 3.12 and separate ml, skin, kimodo, parts, gemx, and moge groups.
- server/install.py:27 maps feature groups to dedicated environments; its everything preset covers all model groups.
- tools/download_models.py owns pinned repositories, filters, and supporting files.
- server/blender_install.py accepts EFFIGY_BLENDER; owner configuration resolves existing Blender 5.2.0.
- UI build is declared in ui/package.json and includes TypeScript checking.

## Steps

1. Use the separate provisioning entrypoint with explicit app/model/library roots. Create backend, ML, skin, Kimodo, parts, GEM-X, and MoGe environments with frozen upstream constraints and bundled CUDA wheels.
2. Build UI locally and obtain required supporting tools. Resolve and reuse configured Blender; do not invoke its download path.
3. Provision every group in everything: Fast, Faithful, multiview, texturing, full refinement, styles, pose, skin, clips, parts, text/video motion, and parallax depth.
4. Use borrowed TRELLIS paths without copying or hashing them. New downloads retain required installation integrity checks. No extra sweeps of existing payloads.
5. Use normal local Hugging Face authentication without printing or copying tokens. For inaccessible pins, identify the exact missing repository and capability; no substitute hosted route.
6. Run the canonical after-installation audit once and compare placement/capacity with the preserved first report. Report provisioning independently from runtime readiness.

## Files to touch

- .python-version
- .venv*/
- python/
- cache/
- ui/node_modules/
- ui/dist/
- gltfpack/
- settings.json
- N:/generated/3DGen-models/Effigy/
- D:/AI/3DGen/Temp/Storage/effigy-after-20261020.json


## Verification

1. Installed versions, local paths, manifest availability, environment routing, and built UI are directly inspectable.
2. Every feature is either locally provisioned or explicitly incomplete; missing gated dependencies prevent full-baseline acceptance.
3. Exactly two canonical audit reports exist for this installation, and no shared model was mutated.
4. No code tests, benchmark campaigns, private prompts, runtime generation, or third-party environment changes.


## Risks

Frozen upstream packages or remote pins may become unavailable; do not silently upgrade. A model installed successfully is not a GPU or quality result. Capacity and available GPU memory are rechecked before later runtime use.

## RESULT

All seven frozen Python environments, UI build, gltfpack, and 48/48 local model entries installed. Exact-object DINOv3 reuse and the pinned public Llama source resolved initial access failures without new credentials. Both canonical audits exist: effigy-before-20261020.json and effigy-after-20261020.json in D:/AI/3DGen/Temp/Storage. After audit: 52268 files, 30 links, zero warnings; its one failure is the preexisting C: HF-cache reserve (78.73 GiB free versus 100 GiB policy). Selected destinations have 246.62 GiB free on D: and 3.88 TiB on NAS. Model files remain NAS-backed; environments/caches/scratch use D:. No additional audit reports or hash sweeps.
