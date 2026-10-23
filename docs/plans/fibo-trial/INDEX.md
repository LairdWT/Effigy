# Isolated FIBO 2 mesh-painting trial

## Outcome

Trial FIBO 2 Edit Turbo in a separate Effigy lane while the owner continues using
the primary lane. Evaluate a masked roof or wall edit after projection onto a
copy of mesh 141. Completed candidate 005_reference was projected as 006_paint
and inspected from a second angle in 007_paint. This qualifies the local trial,
not automatic model promotion or whole-hut artistic acceptance.

S02 delivers the full exterior texture candidate as 039_paint, with four review
captures 040-043. Geometry and UVs remain exact and the atlas remains 1024.
The inn guides the finish; this is not a claim of equivalent or superior art
quality. Roof stroke scale and the vent transition remain visual limitations.
The owner rejected 039 on 2026-10-21 for disjoint joins and an overly realistic
roof. S03 delivers retry 103_paint with before/after 360 presentations, repaired
masonry and a muted roof combining the earlier painted base with restrained
FIBO detail. Geometry, UVs and the 1024 atlas remain exact; owner visual review
is still distinct from these preservation checks.

## Decisions

- D1 (2026-10-20): Owner approved trying FIBO first in another lane, retaining
  the current painting workspace and naming version 141 as its source.
- D2: Pin the FIBO Comfy integration and INT8 ConvRot weights in an isolated
  runtime. Borrow the existing Qwen3-VL-4B FP8 encoder and FLUX.2 VAE read-only;
  qualification must establish compatibility.
- D3: Keep primary port 8370 running. Trial port 8380 uses separate settings,
  library, scratch, caches and model-worker lifetime. A shared GPU cannot provide
  independent heavy-generation capacity; the trial refuses primary model workers
  and exits its own worker if primary generation starts.

- D4 (2026-10-20): Owner requested running the full process after finding the
  disabled control. Resume one localized masked preview, mesh projection and
  inspection; clarify the disabled-button reason in both UIs.
- D5 (2026-10-21): Owner requested a full hut texture treatment with FIBO,
  matching or improving the supplied inn's painted style. Preserve the edited
  mesh, UVs, thatch and 1024 atlas. Use the inn only as a style reference.

## Constraints

- C1: No subagents, code tests, model hash sweeps, commits, pushes, CI or changes
  to shared native runtimes, models, owner geometry, UVs or the 1024 atlas.
- C2: Provision publicly online, then run offline. No hosted inference or prompt
  enhancer. Existing exactly-two-audit limit stands; capacity reads produce no
  new audit/evidence files. Normal application outputs and this plan own results.
- C3: Preserve primary working files, library and processes. New model assets
  belong under the existing Effigy-owned NAS subtree and are read-only at runtime.
- C4: Native FIBO masking blanks the region in its full-frame context. It is not
  Genesis differential denoising. Exact compositing and independent UV guards
  remain required. Limit the initial trial to one four-step candidate.
- C5: Full-asset editing retains the unblanked capture as structural context.
  An optional second image guides style through the pinned native multi-image
  instruction interface. This is distinct from blank-region native inpainting;
  exact compositing and UV write guards still enforce the selected write area.
- C6: The retry preserves good masonry, uses actual overlap into prior changed
  paint, repaints across joins and holds the painting-camera tilt. Coverage
  metrics do not establish continuity or style acceptance.

## Requirements

| Requirement | Implementation and acceptance |
|---|---|
| Separate usable mesh workspace and unchanged primary lane | S01 |
| Local pinned FIBO editing with protected pixels and atlas | S01 |
| Baked-result inspection, timing, GPU and compatibility observations | S01 |
| Full hut painted treatment with retained architecture and compact atlas | S02 |
| Owner-requested 360 and coherent stylized retry | S03 |

## Terms

- Trial lane: isolated source, settings, worker overlay and asset library on 8380.
- Primary lane: existing owner workspace on 8370.

## Spokes

| ID | File | Outcome | Depends on | Skills | Write set | State | Commit | Result |
|---|---|---|---|---|---|---|---|---|
| S01 | 01-isolated-trial.md | Run one isolated FIBO mesh-painting candidate. | none | python:python-core, powershell:powershell-core, planning:prototypes-and-spikes | tools/provision_fibo_trial.py, tools/fibo_trial_worker.py, tools/run_fibo_trial.ps1, ui/src/SurfacePaint.tsx, docs/plans/fibo-trial/01-isolated-trial.md, scratch/lanes/fibo2 | done | - | 01-isolated-trial.md#result |
| S02 | 02-full-hut.md | Paint the complete hut using the inn style reference. | S01 | python:python-core | tools/fibo_trial_worker.py, docs/plans/fibo-trial/02-full-hut.md, scratch/lanes/fibo2 | done | - | 02-full-hut.md#result |
| S03 | 03-overlap-retry.md | Inspect 360 degrees and repaint continuous stylized surfaces. | S02 | python:python-core, art:texture-painting-core, art:art-3d-realtime-core | tools/fibo_trial_worker.py, docs/plans/fibo-trial/03-overlap-retry.md, scratch/lanes/fibo2 | done | - | 03-overlap-retry.md#result |
| S04 | 04-targeted-healing.md | Heal the owner-marked hut defects. | S03 | python:python-core, art:texture-painting-core | docs/plans/fibo-trial/04-targeted-healing.md, docs/plans/fibo-trial/INDEX.md, scratch/lanes/fibo2 | stale | - | 04-targeted-healing.md#result |

## Reading rule

Read this index, the active spoke, dependency RESULT, CODE.md and the native-reference ADR. S01 expected 32 turns; S02 expects 64 turns;
256-turn breaker and the standing implementation budget apply. No handoff or
agent delegation is authorized or needed for this trial.

## Non-goals

Primary deployment, automatic model replacement, new geometry, Vahn work,
simultaneous heavy GPU throughput guarantees, repeated seed searches, multi-image
native blank-mask conditioning or the unreleased multi-turn FIBO LoRA.

## Open questions

- Deferred: owner preference and any primary-lane promotion. The isolated
  runtime trial is complete. Resume when the owner explicitly selects FIBO
  for primary-lane integration or requests a broader comparison.
