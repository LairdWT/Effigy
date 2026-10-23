# Evaluate the whole hut with the installed MOSS Turbo recipe

Spoke: S02
Outcome: Evaluate a separate whole-house draft and bounded detail correction
Depends-on: S01
Decisions: D1, D2, D3, D4, D5, D6
Constraints: C1, C2, C3, C4
Skills: planning:planning-core, python:python-core, powershell:powershell-core
Read-set: docs/plans/whole-house-moss/INDEX.md, docs/plans/whole-house-moss/01-small-view-controls.md#result, docs/plans/multi-view-paint/11-runtime-comparison.md#result
Write-set: docs/plans/whole-house-moss/02-whole-house-trial.md, scratch/lanes/fibo2
State: done

## Context

The owner observed more consistent form in the whole-sheet comparison, accepted the existing Genesis version as worth keeping, and requested another trial over the complete house. The source is Genesis227, not a replacement of it. Expected turns12; no subagents or per-unit handoff stop.

## Evidence

steps/_paint_set.py:228 owns fixed captures. The prior comparison kept409 triangles, one1024RGBA16 atlas, exact geometry/UVs/alpha and other maps. All methods still had art defects. MOSS used the installed Turbo v2 LoRA successfully; its initial inference-mode integration issue was corrected in the Effigy worker. The publisher's recipe documents four Euler/simple steps near1024-square and six to eight for larger sheets: https://huggingface.co/akhaliq/MOSS-Image-SFT-4-steps . Published timing conditions differ from this workstation's full-sheet jobs.

### Runtime comparison

Genesis227 remains starred and unchanged. The new sessions use that source, its geometry lineage167, the complete523762-texel surface selection, front yaw25 and seed24031. Capture236 registers26 cameras at192 pixels; capture241 uses the same transforms and selection at384 pixels. The first mask diagnostic237 was reviewed around all eight sides before inference. The384 permission sheet was inspected before its generation.

| Candidate | Session | Generation job / image | Preview job / mesh | Sampling + decode | Loading | Peak allocated |
|---|---|---|---|---:|---:|---:|
| 192px, four steps, denoise0.55 | 1c223e7539774a62 | c34b5c097bdc /238_paint_group | 833322e37ab4 /240_paint_set |12.84s |146.62s |20.973GiB |
| 384px, eight steps, denoise0.55 | a3c63ca038d1443b | 7db7c2eabfde /242_paint_group | 8868413b455e /244_paint_set |29.96s |184.52s |14.552GiB |
| 384px, eight steps, denoise0.70 | a3c63ca038d1443b | 961a67075eef /245_paint_group | c84a0be9e253 /247_paint_set |31.37s |206.47s |14.322GiB |

The192 draft retains material identity but loses detail and has conspicuous doorway/eave defects; it is rejected as a final texture. The384 comparison keeps masonry and openings more clearly, but does not resolve the roof's muddy appearance or continuity. One final diagnosed correction uses the same384 captures and seed with denoise0.70 and stronger broad-gouache/ochre-straw wording (job961a67075eef). No fourth candidate is authorized by this follow-up.

The final correction247 has warmer, clearer straw brushwork but invents window frames and openings, including on the rear wall. Its eight-angle baked review fails architectural preservation. It is retained as a rejected candidate, not applied. Candidate244 is the best MOSS comparison for preserving the source, but is not a seam-free or owner-accepted replacement. All three authorized candidates are complete; no further reroll occurred. The existing Genesis227 remains the retained preferred asset.

Both completed bakes prove409 triangles, unchanged geometry/UV accessors,1024-square16-bit texture, exact alpha, unchanged other maps and zero changes outside permission/gutters. Reachable coverage is514986/523762 at192 and518588/523762 at384; unseen texels remain unchanged. Actual mismatched192-to384 capture reuse was rejected with incompatible_resolution, rather than silently resizing or rebasing captures. The first generation and preview were launched through the UI; later detail actions use the same normal APIs and are displayed in the UI.

The final247 bake passed the same preservation guards:409 triangles,1024 RGBA16, unchanged geometry/UVs and other maps, zero protected or alpha changes,518588 writable texels and5174 selected texels left unchanged. This technical preservation does not prevent new painted architectural features inside the selected region. The final preview was built and reopened using the UI. Generation workers released their memory after completion; no foreign process was stopped for these trials. Source checks and trial build remain passing from S01; no source changed afterward.

Observed generation workers had no established TCP connections; the trial backend's observed connections were loopback. Browser-specific attribution remains unproven as recorded in the prior comparison. Primary8370 still uses PID49908. MOSS uses the installed BF16 model and INT8 encoder; all756 Turbo LoRA keys applied to252 modules. No model download, custom-node addition, GGUF swap, nativeFP4 claim, test, hash, commit or push occurred.

## Steps

Star and retain Genesis227. Create a separate MOSS whole-house session using that source and all surface texels, with the existing front orientation. Capture every eligible camera at192 pixels, calculate coverage and inspect the registered permission sheet before inference. Use four steps, CFG1, Euler/simple, Turbo LoRA1 and denoise0.55 for the first draft. Describe hand-painted pale masonry, small grey-green foundation stones, dark timber and visibly stylized straw thatch; preserve openings, roof silhouette and material identity.

Build and visually inspect the combined bake around the full circumference and from above, including eaves, roof break, chimney and step risers. Record loading and sampling separately. If composition/materials are useful, create a384-pixel/eight-step detail comparison from the same retained source. Permit one diagnosed correction, at most three new candidates overall. Preserve every candidate and report rejection explicitly. Do not reroll after the bound.

## Files to touch

- docs/plans/whole-house-moss/02-whole-house-trial.md
- scratch/lanes/fibo2

## Verification

1. Use normal application operations and the existing independent projection guards. Expected:409 triangles, unchanged geometry/UVs,1024RGBA16, exact alpha and unchanged other maps. Compare real panels and baked views; clean technical metrics do not establish good art. Observe CUDA memory and report actual coverage loss at each size. Reopen the retained Genesis source and the candidate through the UI. Primary8370 remains untouched. Browser-specific offline qualification from the prior plan remains held; no broader containment claim.

## Risks

Whole-house editing may invent material boundaries or inconsistently interpret the thatch. Small panels can lose mortar detail and inaccessible texels stay unchanged. The existing Kromoss GGUF is not the same qualified baseline and is outside this trial. Model loading may dominate latency even when smaller-sheet sampling becomes faster.

The owner supplied two additional research candidates. [MOSSArt](https://huggingface.co/bunnycore/MOSSArt) is an art/anime/webtoon style LoRA for MOSS SFT; its author recommends0.2-0.4 strength. Repository revision7b308c21755a2f10e528be2c0c79cc4046c9b0b2 was inspected through public metadata and README. Turbo compatibility is not established. [MOSS KV-cache correction](https://huggingface.co/p1atdev/MOSS-Image-SFT-KV-Cache-LoRA) uses a custom attention node, a different eight-step DMD adapter at0.7 strength and a separate correction LoRA. Its published long-prompt improvement excludes model loading and text encoding, and its short-prompt example is slower. It is not an established acceleration for this four-step Turbo v2 recipe. Neither candidate was downloaded or activated; preserve this baseline before a separate compatibility trial.
## RESULT

Completed three separate whole-house MOSS candidates; Genesis227 remains starred and unchanged.192px/four-step draft240 lost detail.384px/eight-step mild244 is the best MOSS comparison, but seams remain. Stronger247 improved straw colour while inventing windows; rejected and unapplied. Ordinary jobs, timing and visual findings are recorded in Evidence above.

All three bakes retained409 triangles, geometry/UV arrays,1024 RGBA16, exact alpha and other maps, with zero changes outside permission/gutters.384px coverage reached518588 of523762 selected texels. UI generation, preview and reopen succeeded; incompatible resolution reuse failed explicitly. Workers released; primary8370 unchanged. Scoped Ruff and trial UI build passed. No tests, hashes, downloads or commits. Owner visual acceptance and browser-specific network attribution remain open. MOSSArt and KV-cache were researched only.
