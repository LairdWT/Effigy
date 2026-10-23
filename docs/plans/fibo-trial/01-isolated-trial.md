# Run one isolated FIBO mesh-painting candidate

Spoke: S01
Outcome: Run one isolated FIBO mesh-painting candidate.
Depends-on: none
Decisions: D1, D2, D3, D4
Constraints: C1, C2, C3, C4
Skills: python:python-core, powershell:powershell-core, planning:prototypes-and-spikes
Read-set: INDEX.md, CODE.md, docs/adr/db506b9a-reuse-the-configured-native-engine-for-reference-workflows.md, server/runtime_policy.py, server/jobs.py, server/reference_models.py, steps/paint.py
Write-set: tools/provision_fibo_trial.py, tools/fibo_trial_worker.py, tools/run_fibo_trial.ps1, ui/src/SurfacePaint.tsx, docs/plans/fibo-trial/01-isolated-trial.md, scratch/lanes/fibo2
State: done

## Context

Decision owner: Laird. Question: does FIBO Edit Turbo improve localized painted
materials while preserving surrounding work after mesh projection? Inspect one
candidate against its captured source; this establishes initial compatibility
and visible behavior, not statistical superiority over Genesis.

## Evidence

- `server/runtime_policy.py:45` fixes primary port 8370. Adapt only the private
  source copy to 8380, with a separate NAS library under `_trials/fibo2`.
- `server/jobs.py:143` already routes reference workers separately. Trial uses
  an isolated package overlay, pinned native source and one-shot model workers.
- `steps/paint.py:224` retains geometry-bound selection and independent UV guards.
- Native source pin: kijai/ComfyUI e3699a745d513941f17ecbc9a3c58d00fc7768cb
  from the open FIBO integration PR 17240. Shared Comfy source is b1693ecb.
- Model pin: Comfy-Org/Fibo-2.0 41e6a0331eff43d5a323107197056e377288c642;
  transformer published size 8408562474 bytes. Shared Python packages remain
  read-only; only comfy-kitchen 0.2.39, comfy-aimdo 0.5.6 and av 17.0.0 are installed in
  the trial overlay. Existing native versions are 0.2.26 and 0.4.11 respectively.
- Initial job 8917ea5c6602 failed before inference: the newer native API imports
  ColorPrimaries, absent from the borrowed AV version. The pinned source requires
  av >=17; install av 17.0.0 into the trial overlay, preserving the shared package.
- Capacity before provisioning: D 243777519616 bytes free, N 4258874056704 free.
  No storage migration or retirement is part of the task.

### Setup observations

The 8408562474-byte transformer is installed in the dedicated NAS subtree.
The native source, AV/kitchen/aimdo overlay, cache and settings are under
scratch/lanes/fibo2. Shared Torch 2.10.0+cu130 and other packages are borrowed
read-only; the primary runtime files and model bindings were not changed.
TextEncodeFibo2 imports successfully after the AV correction. This is import
readiness, not model execution or compatibility acceptance.

Loopback 8380 is served by PID 79544 (launcher 45392). Primary 8370 remains
PID 49908. Both health endpoints passed. Trial runtime reports offline=true and
zero CSP violations. The trial library is N:/generated/Effigy/_trials/fibo2.
Normal upload/import copied source 141 into rim_elm_hut_fibo_trial/002_import_model
(job 5ffa965d6637), retaining 409 triangles, one material and one texture, no
rotation or dropped meshes. Capture 711e5f0b42ba -> 003_paint rendered the
expected hut. Appearance was copied into this asset with FIBO/four-step settings.

Private UI build and Ruff passed; launcher PowerShell syntax passed. Browser
control remains disabled in Work settings, so live UI interaction is not claimed.
The normal app open tool queued the separate lane. Capacity afterward: D
243046830080 bytes free, N 4246832648192 free; no added audit report was created.

The initial inference attempt failed before rendering due to AV's missing
ColorPrimaries. After correcting that concrete dependency, automatic approval
review rejected the resubmission command with only "blocked by policy". No
alternative submission mechanism was attempted. At that stop there was no completed FIBO
preview, projection, timing measurement, quantization execution proof or quality
comparison. Source 141 and all primary library versions remain untouched.

### Completed end-to-end trial

The owner subsequently ran 004_reference (job e4c3b4983be8) with a whole-surface
mask. Its detailed thatch also relocated/replaced openings, so it was retained as
an unprojected comparison. Whole-surface masking blanks the building in FIBO's
conditioning; it does not provide the same preservation as a local repair.

After the owner explicitly requested the full process, job c8d8c88afeb8 produced
005_reference from capture 003. Seed 24026, four steps, brush centre (0.61, 0.45),
radius 0.09 and inward blend 8 were held fixed. Inference took 153.55s, including
89.27s sampling; CUDA peak allocated memory was 14.41 GiB. Runtime was native
0.42.0 with Torch 2.10.0+cu130 and 215 int8_tensorwise layers. This confirms the
selected borrowed encoder/VAE can execute with the pinned transformer; it does
not establish a particular INT8 hardware kernel or comparative performance win.

Independent decoded comparison found 26853 selected preview pixels, 26623 changed
selected pixels, zero outside changes and zero alpha changes. Job c34902a020d5
projected it onto 002_import_model as 006_paint: 12765 changed atlas texels within
12774 permitted texels, zero outside, alpha or gutter changes. The atlas remains
1024 RGBA16, 409 triangles, and all four trial geometry/UV accessors are identical.
Face-corner positions and UVs also match the owner's original 141 exactly.

The baked before/after comparison shows a localized change to flowing straw
marks with surrounding architecture retained. Capture 1e389a782046 -> 007_paint
re-rendered the applied mesh at yaw 55, pitch -22 for a second-angle inspection.
Existing broader texture inconsistencies are not claimed repaired by this small
roof patch. This is a completed operational trial, not final artistic acceptance
or a controlled head-to-head quality ranking against Genesis.

No native FIBO worker remained after completion. Servers stayed at primary PID
49908 and trial PID 53432. Runtime reports offline=true and zero CSP violations;
no worker TCP connections were observed during the sampled check. Browser
controls remain unavailable, so submission and projection used the normal local
API. Both UIs now explain why Generate is disabled, including the empty mask,
missing prompt, loading appearance or invalid values; both offline builds passed.

### Use the lane

Owner-requested restart completed on 2026-10-20. Trial server now runs as PID
53432 (launcher 68256); primary remains PID 49908. Separated its owned runtime
model/cache root into the sibling fibo2-runtime folder because using the borrowed
weight root triggered the ownership guard in model-status requests. Both health
endpoints, trial model status and FIBO availability now respond successfully.
No weight files or primary settings were moved or changed.

Open http://127.0.0.1:8380/#/asset/rim_elm_hut_fibo_trial?version=003_paint.
Choose a brush/lasso/face region, supply the edit instruction, then Generate
projection preview. FIBO is the only trial model and uses four steps. Review the
candidate before Project onto mesh. New versions belong only to the trial library.
For later startup run tools/run_fibo_trial.ps1 from the primary checkout.
The initial sample's exact prompt, seed 24026 and brush mask remain in the
ordinary trial jobs.log under job 8917ea5c6602. Its inference never completed.

## Steps

1. Snapshot current runtime source into ignored trial scratch, preserving primary
   files. Provision the pinned native source and new transformer separately.
2. Adapt only the trial: FIBO model entry, isolated interpreter/cache, native
   mask conditioning, exact RGBA composition, honest UI labels and four steps.
3. Start loopback 8380 and import a copy of 141 into its independent library.
   Keep the source file and primary history untouched.
4. When GPU admission permits, capture one 1024 view and edit one roof/wall mask.
   Project the candidate, inspect baked renders and decoded preservation. Stop
   on incompatibility, unavailable memory, primary activity or owner rejection.
5. Leave the trial workspace available and record ordinary job/output references.

## Files to touch

- tools/provision_fibo_trial.py
- tools/fibo_trial_worker.py
- tools/run_fibo_trial.ps1
- ui/src/SurfacePaint.tsx
- docs/plans/fibo-trial/01-isolated-trial.md
- scratch/lanes/fibo2

## Verification

1. Ruff and private UI build: no errors. PowerShell parse: no syntax errors.
2. Both loopback health endpoints respond; separate asset libraries and primary
   listener identity remain unchanged.
3. Runtime candidate changes selected pixels with zero protected-pixel/alpha
   changes; projected mesh retains exact geometry/UVs and 1024 RGBA16.
4. Record actual engine/weight identities, CUDA peak, elapsed time, unexpected
   connections, errors and visible output. No code tests or extra evidence files.

## Risks

The native integration is pre-merge. Existing encoder/VAE reuse is a candidate
binding until runtime qualification. Four steps do not establish low load latency
over NAS. One GPU is shared; monitoring cannot promise race-free priority over an
unmodified primary server. Trial cancellation frees only the trial's own process.
Native FIBO masks condition an image with a blank region; strict write permission
comes from Effigy's compositing and projection, not a pixel-stability claim.

## RESULT

Completed the isolated masked-paint workflow. c8d8c88afeb8 -> 005_reference;
c34902a020d5 -> 006_paint; second-angle capture 1e389a782046 -> 007_paint.
FIBO took 153.55s with 14.41 GiB peak CUDA allocation. Projection changed 12765
selected texels, zero protected pixels/alpha, retaining 1024 RGBA16 and exact
geometry/UVs relative to owner 141. Inspected baked renders show localized straw
changes. Primary session/assets remain unchanged; the model worker exited.
Both UI builds and plan checks passed; Generate now explains disabled states.
UI interaction itself remains unobserved because browser control is disabled.
Borrowed weights unchanged; no tests, hash sweeps, commits or primary promotion.
Owner artistic acceptance and broader comparison remain separate.
