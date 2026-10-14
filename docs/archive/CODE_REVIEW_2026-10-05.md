# Code review: calculations and inference performance

Date: 2026-10-05  
Reviewed commit: `149d791`  
Environment: RTX 5080 Laptop, 16 GB VRAM, Windows, torch 2.8.0+cu128

## Scope and conclusion

The review started with the project markdowns, including `CLAUDE.md`, the README,
architecture, implementation, handover, workflow, research, benchmark notes, and
the engine patch inventory. It then traced the inference, attention, baking,
mesh-processing, and resident-worker code.

**Inference has measurable optimization opportunities.** Three correctness issues
and four concrete optimization opportunities were identified. No tracked files
were changed during the review; this document records its results.

The measurements below are component benchmarks and experimental probes, not
full-generation speedups. No production fixes have been applied.

## Correctness findings

### HIGH: Cleanup can delete visible geometry

**Location:** [`steps/_mesh.py`](../../steps/_mesh.py), lines 300–301,
`drop_enclosed_parts`.

The function decides whether an entire connected component is enclosed using its
centroid alone. A centroid need not lie within its own component, so another
object containing that point does not establish containment of the component.

**Reproduction:** A torus with major radius 2.0 and minor radius 0.2 surrounded a
sphere of radius 0.5. Cleanup deleted all 2,048 torus faces, retaining only the
sphere's 320 faces. The torus was entirely outside the sphere; its nearest vertex
was 1.8 units from the origin.

**Impact:** Visible parts can disappear when this helper runs during cleanup of
rebuilt meshes or subsequent remeshing.

**Recommendation:** Use conservative containment checks, including bounds
rejection and surface/intersection checks where needed. Preserve components when
containment is uncertain.

### MEDIUM: Failed inference leaves models occupying VRAM

**Locations:**

- [`pixal3d_image_to_3d.py`](../../engine/pixal3d/pixal3d/pipelines/pixal3d_image_to_3d.py),
  lines 372–382, `sample_shape_slat`.
- [`steps/_common.py`](../../steps/_common.py), lines 76–79, `_release_cache`.
- [`steps/trellis2.py`](../../steps/trellis2.py), lines 171–184, resident pipeline cache.

The sampler moves its model back to CPU only after successful sampling. An
exception skips that operation, while the resident pipeline retains the model.
Calling `torch.cuda.empty_cache()` does not release these live model tensors.

**Reproduction:** An injected sampler `torch.cuda.OutOfMemoryError` left the
model's parameters on `cuda:0`. They remained there after `_release_cache()`.
This probe exercised the error path with a small model; it did not deliberately
exhaust the GPU's memory.

**Impact:** Subsequent requests can encounter reduced VRAM headroom or another
OOM, especially when reusing the same cached pipeline.

**Recommendation:** Evict the failed worker or guarantee model offloading on
failure before accepting another request.

### MEDIUM: NAF channel chunking can leave channels unwritten

**Location:** [`engine/pixal3d/patches.py`](../../engine/pixal3d/patches.py),
lines 73–74, `naf_attention_chunked`.

The loop truncates a chunk at a head boundary but advances by the original chunk
size. This can skip output channels in the tensor allocated with `new_empty`.

**Reproduction:** With 24 value channels across four heads, each head has six
channels. At `chunk=4`, channels 6–7 and 18–19 remain unwritten. At `chunk=5`,
additional channels are skipped. The current production dimensions divide evenly
and avoid this particular failure, but other supported configurations fail.

The existing `test_naf_attention_chunked_matches_upstream` passed in the normal
test run. Enabling deterministic uninitialized-memory filling exposed the issue:
the test failed with 576 of 3,456 elements mismatched, including NaNs in channel 6.
Reused allocation contents can hide the missing writes in the normal test.

**Recommendation:** Iterate within each head or advance to the actual chunk
endpoint. Make the regression test detect unwritten output independently of
allocator contents.

Reproduce the stricter test from the repository root in PowerShell:

```powershell
@'
import torch, pytest
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
raise SystemExit(pytest.main([
    'tests/test_pixal3d_patches.py::test_naf_attention_chunked_matches_upstream',
    '-q',
]))
'@ | .\.venv-ml\Scripts\python.exe -u -
```

## Measured optimization opportunities

GPU measurements used warm-up calls and CUDA synchronization around timed work.
Experimental alternatives ran in isolated scripts without modifying production
source. Ratios describe only the measured operation.

| Opportunity | Current → experimental | Recommendation |
|---|---|---|
| NAF attention | 1.014 → 0.389 s, approximately 2.6× | Compute attention weights once per head and spatial chunk, then reuse them across value-channel chunks. Gather directly from low-resolution values where equivalent. |
| Single-sequence attention | Cross-attention: 0.622 → 0.095 ms; self-attention: 1.219 → 0.763 ms | Add a direct SDPA path when the packed batch contains one sequence, avoiding index construction, gathers, and scattering. |
| Pixal3D projection | Example output allocation: 1,024 → 64 MiB per branch; 3.85 → 2.54 ms | Project active voxel coordinates directly instead of building the dense grid and selecting from it afterward. Apply to single-view and multiview paths. |
| Volume sampling | 3.61 → 0.72 ms, approximately 5× | Use the already-installed FlexGEMM sampler on CUDA and retain the torch implementation for CPU use. Absolute savings in this probe are small. |

### NAF attention

**Location:** [`engine/pixal3d/patches.py`](../../engine/pixal3d/patches.py),
`naf_attention_chunked` and `na2d`.

The current implementation recomputes attention weights for successive
value-channel chunks belonging to the same head. Queries and keys do not change
between those chunks.

The synthetic attention probe used 256×256 output, 16×16 low-resolution keys and
values, four heads, 256 query/key channels, 1,024 value channels, and a 9×9 kernel.
The experimental version reused weights and gathered low-resolution values
directly for this integer scaling case. Maximum absolute output difference was
`8.34e-7`.

This is the strongest first performance target: the existing
[M17 profile](../bench/m17.md#where-the-memory-went) also identifies NAF as the
dominant conditioning cost. Validate the alternative at actual 512/1024 stage
sizes, including border behavior and peak memory, before integration.

### Single-sequence attention

**Location:** [`engine/trellis2/patches.py`](../../engine/trellis2/patches.py),
lines 120–130, `memory_efficient_attention`.

The packed attention shim constructs indices and gathers/scatters tensors even
when only one sequence is present. A direct SDPA call can avoid this work while
preserving the existing path for multiple sequences.

The probes used bfloat16, 16 heads, and 64 channels per head:

- Cross-attention: 8,192 query tokens and five key/value tokens.
- Self-attention: 2,048 query/key/value tokens.

Outputs matched exactly in both probes.

### Sparse projection

**Locations:**

- [`pixal3d_image_to_3d.py`](../../engine/pixal3d/pixal3d/pipelines/pixal3d_image_to_3d.py),
  lines 275–280, `get_proj_cond_shape`.
- [`pixal3d_mv_image_to_3d.py`](../../engine/pixal3d/pixal3d/pipelines/pixal3d_mv_image_to_3d.py),
  lines 130–131, the corresponding multiview gather.

Shape and texture conditioning compute dense projected features before retaining
only active voxel coordinates. The probe selected 16,384 coordinates from a 64³
grid with 1,024 float32 channels per branch. Restricting the projected grid points
before feature sampling reduced output allocation from 1,024 MiB to 64 MiB and
matched the dense-then-gather result exactly.

The memory benefit is especially relevant to the 16 GB target. Preserve coordinate
ordering, camera transforms, multiview averaging, and grid-resolution overrides.
This does not remove the separate full-resolution NAF feature-map allocation.

### Native volume sampling

**Location:** [`steps/_bake.py`](../../steps/_bake.py), lines 63–79,
`sample_volume`.

The current implementation sorts voxel keys and performs binary searches for
trilinear neighbors. The installed FlexGEMM dependency already supplies
`flex_gemm.ops.grid_sample.grid_sample_3d`.

The probe used the existing
`library/m17_dwarf_turnaround/050_trellis2/ovoxel.npz`: 1,477,195 voxels at
resolution 1024, with 262,144 query points near occupied voxels. Maximum absolute
output difference was `3.58e-7`.

Keep a CPU fallback and verify missing-neighbor normalization and boundary
semantics before substituting the CUDA implementation.

## Changes not justified by the probes

- **Forcing fused SDPA for NAF:** The current six-dimensional input selected the
  math backend. Reshaping to four dimensions enabled memory-efficient SDPA, but
  the measured 128² neighborhood-attention case became slower: approximately
  9.5–10.3 ms versus 10.9–12.0 ms. Do not recommend this reshape alone as a speedup.
  Backend eligibility and numerical differences depend on input constraints; see
  the [PyTorch 2.8 SDPA documentation](https://docs.pytorch.org/docs/2.8/generated/torch.nn.functional.scaled_dot_product_attention.html).
- **Replacing mesh connected-component labeling:** On the existing 195,923-face
  dwarf mesh, an equivalent SciPy approach reduced approximately 36 ms to 25 ms.
  Labels matched, but this saving does not explain the previously documented
  long mesh-processing hang and is a lower priority than NAF.

## Verification and limits

Executed during the review:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result: **78 passed, 9 skipped, 1 warning in 47.20 s**. The warning was a trimesh
invalid division while calculating center of mass in an export-profile test.

```powershell
.\.venv-ml\Scripts\python.exe -m pytest tests/test_pixal3d_patches.py tests/test_engine_patches.py tests/test_bake_core.py tests/test_trellis2_step.py tests/test_mesh_checks.py -q
```

Result: **31 passed in 46.51 s**. The stricter NAF test above subsequently failed
as described, confirming the missing-write issue despite the normal suite passing.

Additional probes reproduced the geometry deletion and model residency after an
injected sampler OOM, and compared the experimental calculation paths above.

**No full-generation A/B benchmark or final-asset quality comparison was run for
these proposed optimizations.** Do not multiply the component speedups together
or apply them to the full-generation time. Laptop power/thermal conditions were
not controlled as a formal benchmark session. Validate cold and warm runs,
single-view and multiview inputs, peak VRAM, and output quality on the project's
golden set before assigning an overall speedup.

## Recommended order

1. Fix geometry containment, failed-worker cleanup, and NAF chunk boundaries.
2. Optimize NAF weight reuse and add the single-sequence attention fast path.
3. Reduce dense projection allocations; evaluate native volume sampling as a
   smaller follow-up.
4. Run end-to-end A/B benchmarks with fixed inputs and seeds, preserving the
   project's output-quality and 16 GB VRAM constraints.

## Outcome (2026-10-05, same day)

Checked against the code and reproduced where cheap; implemented on branch `review-fixes`.

- **Cleanup deletes visible geometry: confirmed, fixed.** `drop_enclosed_parts` now drops a part only
  when all six of its extreme vertices are inside the rest of the mesh (the mean vertex of a ring sits in
  the part it surrounds). Test: a torus around a sphere keeps every face, a bubble inside a sphere goes.
- **Failed inference leaves models on the GPU: confirmed, fixed.** `steps/trellis2.run` evicts the
  resident pipeline on any failure inside the models (a `StepError` for a bad input keeps it); the next
  request reloads into a clean card. Test with an injected `OutOfMemoryError`.
- **NAF chunk boundary: confirmed, fixed.** The loop advances to the cut, and the regression test runs
  with uninitialised memory filled with NaN (the old loop left channels 6–7 and 18–19 unwritten, as the
  review found; the test could not see it because the allocator handed back the previous buffer).
- **NAF attention: implemented (patch 15 rewritten).** Weights once per head, keys and values gathered
  from the low-resolution maps (`index // factor`). Crate, Faithful, seed 7, same input, one-shot step on a
  free card: **242 → 211 s** total (sampling 198 → 172 s), **peak 9.9 → 9.2 GB**; the mesh differs by
  1–2 % in face and voxel count (bf16 rounding moves the sampler a little), renders show the same object.
  Not yet measured on the multi-view and the 1024 texture stage of a character (the owner's app has to
  restart first).
- **Single-sequence attention: implemented (patch 16),** exact.
- **Sparse projection: not done.** The dense grid is a transient of the conditioning stage; whether it
  sets a run's peak is unmeasured (the crate peaked at 9.2 GB, well under 14.5), and the change means a
  patched copy of two upstream pipeline methods preserving coordinate order, camera transforms, multi-view
  averaging and the grid override. Gate: a phase-level memory profile of a 1024 character run that shows
  conditioning as the peak.
- **Native volume sampling: skipped.** ~3 ms per bake in absolute terms; FlexGEMM's missing-neighbour
  normalisation and border semantics would need verifying for that.
- The two "not justified" items: agreed, nothing changed.
