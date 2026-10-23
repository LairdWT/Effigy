# Paint the complete hut using the inn style reference

Spoke: S02
Outcome: Paint the complete hut using the inn style reference.
Depends-on: S01
Decisions: D1, D2, D3, D5
Constraints: C1, C2, C3, C5
Skills: python:python-core
Read-set: INDEX.md, 01-isolated-trial.md#result, CODE.md, tools/fibo_trial_worker.py, scratch/lanes/fibo2/native-engine/comfy_extras/nodes_fibo2.py, steps/paint.py
Write-set: tools/fibo_trial_worker.py, docs/plans/fibo-trial/02-full-hut.md, scratch/lanes/fibo2
State: done

## Context

The owner wants a visible full-asset improvement comparable to the supplied inn,
following the successful localized roof trial. Start from trial 006_paint, which
retains the owner's 141 geometry and UVs. The inn guides brushwork and value
grouping, not building shape, openings, roof construction or background objects.

## Evidence

- tools/fibo_trial_worker.py:73 blanks the selected input region in the original
  native inpaint route. S01's whole-surface candidate relocated architecture.
- scratch/lanes/fibo2/native-engine/comfy_extras/nodes_fibo2.py:55 supports image
  references named image_1 through image_16 for instruction editing.
- steps/paint.py:240 independently restricts projection to generated pixels,
  visible selected triangles and their owned atlas texels.
- The owner-supplied inn screenshot shows grouped painted planes, muted pigment,
  selective light edges and coherent stone, plaster and wood material marks.

## Steps

1. Add explicit unblanked instruction conditioning with an optional local style
   version. Preserve the existing blank-region repair default and pixel guards.
2. Import the supplied inn screenshot through the local trial API, capture the
   hut, and inspect one substantial front-view edit before projecting it.
3. Continue around the hut with fixed cameras and bounded selections. Preserve
   accepted surfaces, material identity and geometry; inspect baked views.
4. Retain normal application versions and final mesh/texture outputs. Record
   actual coverage, preservation, runtime and any visual limitations here.

## Files to touch

- tools/fibo_trial_worker.py
- docs/plans/fibo-trial/02-full-hut.md
- scratch/lanes/fibo2

## Verification

1. Run Ruff on changed Python and the plan structural check; no code tests.
2. Execute the normal capture, reference and projection jobs on the trial lane.
3. Inspect candidate and baked renders, decoded outside-mask/alpha protection,
   unchanged mesh/UV accessors, 1024 atlas, and cumulative visible UV coverage.
4. Check local runtime policy and sampled worker connections; leave primary
   processes and library unchanged. No hash checks or extra evidence packs.

## Risks

Instruction edits may move painted details even with unblanked context. Reject
misaligned candidates before projection. Successive views may introduce seams
or inconsistent material scale; inspect overlaps and repair bounded defects.
Small occluded and underside areas may not benefit from exterior projections.

## Runtime observations

Upload 008_upload is the owner's inn screenshot. Two-image edit 010_reference
(8e9bf31a73e0) closed the doorway and extended straw onto walls. Its projection
011_paint is a labelled comparison branch, excluded from the delivered ancestry.

A revised single-image instruction pass 013_reference (4982425c6b8e) retained
the open doorway and aligned masonry. Projection f27d857c40b6 -> 014_paint starts
from 006_paint. It covers 224089 of 523762 occupied atlas texels, with 144 of 409
triangles at least 90 percent covered. The roof includes unwanted decorative
grain heads that remain a specific cleanup target. Additional angles select
triangles below 90 percent coverage rather than overwriting completed faces.

The trial UI distinguishes blank-region repair from full-capture restyling and
offers a local style-reference version. Metadata and drafts retain both choices.
Its build passed. Browser automation is disabled; live interaction is unverified.

Views at yaw 25, 115, 205 and 295 were edited from the progressively updated
mesh. The four projections through 023_paint cover 459604 occupied atlas texels
(87.75 percent). Capture 024 used yaw 180, pitch -70 to inspect the roof. Its
edit 025_reference made usable plain thatch but invented vent/ledge details.
Projection 026 crossed onto the stone ledge and was rejected. Corrected
projection 029 selects 84 original brown roof triangles, excludes the vent
region and leaves stone untouched. The original texture's per-face colour and
geometry identify material regions; no model payload hashes are involved.

Localized repair 031_reference -> 032_paint reduces grain motifs around the
vent. Broad ledge repair 034_reference invented windows and was rejected.
Instead, 035_reference -> 036_paint repairs two small defects with the adjacent
stone retained as context. The final vent-area repair uses original roof face
selection to protect the black wooden slats precisely. Rejected versions are
labelled in the application and excluded from the chosen mesh's ancestry.

Observed inference so far spans 99.97-144.90 seconds per image, with peak Torch
CUDA allocation 11.28-14.18 GiB. All previews report zero changed pixels outside
their write mask and unchanged alpha. Source checks and the private UI build
pass. No model downloads, tests, hashes, primary restart or publication occurred.

### Delivered candidate and inspection

Final projection d4b27eb62255 produced 039_paint from preview 038_reference
(524b3442e6e5). Accepted projection ancestry is 006 -> 014 -> 017 -> 020 -> 023
-> 029 -> 032 -> 036 -> 039. Final ordinary captures 040-043 inspect yaw
25, 115, 205 and 295 respectively. The asset labels 039 as the starred full
exterior review candidate. Appearance revision 2 retains the selected materials
and style without the ambiguous wheat wording that caused decorative grain.

Independent decoded inspection confirms all four geometry/UV accessors equal
006, 409 triangles, one embedded 1024-square RGBA16 texture, zero alpha changes,
and zero changes to occupied atlas texels outside accumulated projection
permissions. Ten generated previews also have zero protected-pixel or alpha
changes. The final GLB is 3988112 bytes; its separate atlas is 3966286 bytes.

Accumulated projection permissions cover 460425 of 523762 occupied texels
(87.91 percent). Rendering that coverage through the four final cameras measures
99.07, 99.15, 98.72 and 98.65 percent of opaque visible pixels respectively.
Unreached/occluded surfaces and narrow rejected border texels retain their prior
texture. This is a full exterior treatment, not a claim that every atlas texel
was regenerated. No model-content hash or code-test suite was run.

The final review shows stronger masonry, timber and straw detail; major grain
motifs and invented ledge openings were removed. Fibre scale and painted
shading still vary around the vent and some roof joins. The result is more
finely hatched than the inn's broad brushwork, so matching or exceeding the
inn's artistic quality is not established. The candidate is ready for owner
review, not automatically promoted to the primary workspace.

Both backend PIDs remain unchanged (primary 49908, trial 53432). Final primary
health passes; trial reports offline=true and browser_violations=0. No FIBO
worker remains. Sampled worker connections during inference showed no TCP
connections; this observation is not OS-level network containment.

## RESULT

- Done: full exterior FIBO candidate 039_paint, job d4b27eb62255; review captures
  040-043. Four sides, roof and localized repairs are projected onto the mesh.
- Exact geometry/UV accessors retained: 409 triangles, one 1024 RGBA16 atlas.
  Independent preview and atlas checks found no protected-pixel/alpha changes.
- 460425 occupied texels covered; 98.65-99.15 percent visible coverage in the
  four review cameras. Occluded surfaces retain prior texture.
- Final GLB 3988112 bytes. Ten previews ran locally in 99.97-144.90s each,
  peak Torch CUDA allocation 11.28-14.18 GiB. No worker remains; primary untouched.
- Ruff, private UI build and plan structure passed. No tests, hashes, downloads,
  commits or pushes. Roof/vent stroke variation remains; artistic equivalence
  to the inn and primary promotion are not claimed.
