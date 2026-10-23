# Repair the assembled hut through bounded masked edits

Spoke: S03
Outcome: Qualify and apply targeted repairs to the assembled hut
Depends-on: S02
Decisions: D1, D2, D3, D4
Constraints: C1, C2, C3, C4
Skills: python:python-core, art:texture-painting-core
Read-set: docs/plans/painting-completion/INDEX.md, docs/plans/painting-completion/02-seam-healing-workflow.md#result
Write-set: docs/plans/painting-completion/03-hut-repair.md, scratch/lanes/fibo2, steps/paint.py, steps/_paint_seams.py, steps/reference.py, tools/fibo_trial_worker.py, tools/stage_multi_view_trial.py, ui/src/SurfacePaint.tsx
State: done

## Context

The owner rejected seams and requested autonomous completion. Start from249 while preserving227. Expected turns20; qualify one join before applying a recipe around the hut.

Use the project-owned3dgen-prompt-core image-editing and Krea adapters for prompt channels; its unqualified name is not part of the external bundle catalog.

## Evidence

docs/plans/whole-house-moss/03-projection-seams.md:1 records zero-change source projection and persistent disagreement between generated views. Whole-house candidate247 invented windows and is excluded from Apply.

Anchor source249, capture251, seed24041,1024-square context. The suggestion was deliberately erased and replaced with a bounded wall rectangle using the UI, retaining the suggested-mask mode to exercise preset composition. Genesis0.30 produced252/253:57.33s sampling,41.12s load,13.51GiB peak,46556 masked pixels and zero outside changes. It invented stronger tan stone shapes. Correction0.15 produced254/255 and still changed mortar/style. Both are rejected. The final anchor correction uses the already-installed FIBO structure-preserving edit adapter, same capture/seed/mask, four steps and a repair instruction rather than Genesis scene wording (job03f70770f188). This does not reopen the closed full-sheet comparisons or install another model.

FIBO256/257 also changed stone scale. Its preserve_structure input retains the entire original image while the permission mask limits final composition; the model does not receive that permission as an inpainting region. The next bounded diagnostic changes only conditioning to blank_region, exposing the small repair area while retaining the surrounding full view. This uses the already-supported repair mode and the same source, seed and mask. The four-candidate total is recorded in D2; no unbounded rerolls.

Blank-region job051f429e2128 produced259 in106.06s sampling; projection f8effa2b870c produced260. The eight-angle baked review retains architecture and matches surrounding cream stone color substantially better than the three rejected anchors. The local patch is a usable repair candidate, not owner acceptance or a seam-free house. It changed12417 permitted surface texels with zero outside/alpha changes,409 triangles and1024 RGBA16. A subsequent bounded roof-seam capture descends from260, retaining the assembled wall repair as context. Single-view applies now generate ordinary eight-angle review and turntable outputs automatically.

Roof capture261 uses the same full-frame camera. Baseline f8a1519726b2 produced262, preserving outside pixels but introducing bright straw bundles. The shared material text asked for an ochre roof while the local repair requested matching dark brown; this is a prompt-composition defect for repair intent. Added an explicit match_capture prompt scope: repair wording is sent alone, while shared appearance remains stored. Restyle mode retains shared materials/style. FIBO and native adapters validate the scope, and applied meshes retain model/conditioning/scope and appearance for subsequent angles without retaining an old camera-space mask. The canonical FIBO worker now stages explicitly to the existing trial module; no provisioning or engine change.

Roof correction14105f913998 used match_capture and produced264 in70.74s sampling. Bake e49c3f4367e6 produced265:7139 writable surface texels, zero outside/alpha changes and1024 RGBA16. Eight-angle review shows the dark roof appearance continuing through the patch without the rejected bright strip. Side capture266 (job7277355d4ec8, yaw115) descends from265. Seam suggestions now reconstruct later single-view paint footprints through the accepted parent chain;266 records healed_versions260 and265 over the249 ownership atlas, excluding rejected branches.

Foundation job7538292331cc produced267 in55.04s sampling; bake5be13150b8cf produced268. The repair spans the join beneath the side window and keeps the grey-green stone palette.4660 surface texels were writable, with zero outside or alpha changes. Read-only projection inspection measured facing0.8539 and0.932 on the two sides of the join, both above the0.25 admission threshold. Final268 versus retained227 actual accessor arrays, UVs, alpha and other maps compare equal:409 triangles,1024x1024x4 uint16. Local material scale and roof grain remain visible art-review considerations; no claim that every texture join is eliminated.

## Steps

Choose a camera spanning one visible wall/foundation or roof join. Capture the entire model, inspect suggested permission and adjust it to protect good surfaces/openings. Use the installed Genesis model and resulting-appearance wording, an explicit seed and conservative denoise. Compare the baked result across neighboring cameras. Permit baseline plus two diagnosed corrections for the anchor; stop propagation if they fail. After an anchor passes, repair remaining distinct defects sequentially using the accumulated texture as context. Keep every rejected candidate and verify preservation on each apply.

## Files to touch

- docs/plans/painting-completion/03-hut-repair.md
- scratch/lanes/fibo2
- steps/paint.py
- steps/_paint_seams.py
- ui/src/SurfacePaint.tsx
- steps/reference.py
- tools/fibo_trial_worker.py
- tools/stage_multi_view_trial.py

## Verification

1. Baked views and ordinary job metrics. Expected: coherent join without new architectural features, unchanged409 triangles/UVs/1024 RGBA16/alpha/other maps and protected areas.
2. Full circumference review. Expected: defects are either repaired or specifically named; no seam-free claim from coverage alone.

## Risks

Masked inpainting may move mortar or create a repeated feature. Prompt strength and denoise must be diagnosed rather than blindly rerolled. Owner visual acceptance remains separate.

## RESULT

Produced a retained repair branch ending at268: wall260, roof265 and foundation268. Each uses a fixed full-view capture and local write permission; rejected anchors remain separate. Repair-only prompt scope resolved a shared-style conflict. Final268 versus retained227 has equal geometry/UV arrays, alpha and other maps,409 triangles and1024 RGBA16. Local writes affected12417,7139 and4660 surface texels respectively, with zero outside/alpha changes. Eight-angle reviews and turntables accompany applies. This qualifies the targeted workflow and supplies a reviewable candidate, not owner acceptance or a claim that every material-scale variation/seam is gone. Primary lane and Genesis227 remain unchanged. Source checks and trial UI builds pass; no tests, hashes, downloads, commits or borrowed-model modifications.
