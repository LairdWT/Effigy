# Research 01: TRELLIS.2 and the StableProjectorz fork, code deep dive

> Status: research notes, 2026-10-03. Based on reading the source of
> `IgorAherne/TRELLIS.2-stableprojectorz` (release `latest` = **v22**, Windows zip
> uploaded 2026-04-28, 736 MB) and upstream `microsoft/TRELLIS.2` (HEAD `75fbf01`, 2026-06-05).
> Paths below refer to those repositories, not to this one.

## 1. What TRELLIS.2 is

- 4B-parameter image-to-3D model (MIT, paper arXiv 2512.14692). It uses a sparse voxel structure
  called **O-Voxel**. It holds geometry *and* PBR attributes (base color, metallic, roughness,
  alpha), and it handles open surfaces, non-manifold geometry and internal structures.
- It runs in three flow-matching stages, each a 1.3B DiT:
  1. **Sparse structure** (64³ occupancy, `ss_flow_img_dit_1_3B_64_bf16`). Its decoder is reused from TRELLIS v1.
  2. **Shape SLAT** at 512 or 1024 (`slat_flow_img2shape_dit_1_3B_{512,1024}_bf16`). The `*_cascade`
     modes generate at 512 and then upsample to 1024 or 1536.
  3. **Texture SLAT** (`slat_flow_imgshape2tex_dit_1_3B_{512,1024}_bf16`). It is **conditioned on
     image + shape**, which is what makes "texture an arbitrary mesh" possible (see §4).
- Conditioning: **DINOv3 ViT-L/16** (`facebook/dinov3-vitl16-pretrain-lvd1689m`). It takes one image.
  The official pipeline has no multi-image input.
- Background removal: `BiRefNet` wrapper loading **`briaai/RMBG-2.0`** by default.
- Upstream timing (H100): 512³ about 3 s, 1024³ about 17 s, 1536³ about 60 s. Upstream says it needs 24 GB or more and Linux.
- Pipeline types: `512`, `1024`, `1024_cascade` (default), `1536_cascade`; `max_num_tokens=49152`.
  Both pipelines expose a `low_vram` flag that moves each sub-model to the GPU only while it runs.

## 2. What the StableProjectorz fork adds

| Area | Fork behaviour |
|---|---|
| Packaging | One-click Windows zip with portable Python 3.11, Torch 2.8.0, CUDA 12.8, prebuilt wheels in `whl/` (`cumesh`, `flex_gemm`, `o_voxel`, `nvdiffrast`, `nvdiffrec_render`, `Pillow_SIMD`). No Visual Studio or CUDA toolkit needed (except GTX 10xx). |
| VRAM | Tuned to fit **8 GB** GPUs even at 1024³: aggressive CPU offload of `attrs`/`coords`, `torch.cuda.empty_cache()` between stages, dual-contouring remesh grid capped at 512 (`o_voxel/postprocess.py`), pre-simplify to 2M faces before BVH. |
| Windows fixes | `flex_gemm` forced to `Algorithm.EXPLICIT_GEMM` plus a pure-Torch fallback for missing Triton kernels (`api_spz/core/state_manage.py::_apply_patches`); `triton-windows==3.4.0.post21`; xformers for pre-Ampere GPUs. |
| Quality fix | "Vertical lines" artefact bug fixed (credited to visualbruno). |
| Process model | `pipeline_worker.py` runs the pipeline in a **separate process** so it doesn't contend for the GIL with Gradio. |
| API server | FastAPI on `127.0.0.1:7960` (`api_spz/`), see §3. |
| Models | Re-hosts `dinov3` and `RMBG-2.0` zips on GitHub/SourceForge (`install.py::download_models`). **This is a licensing concern for us, see §6.** |

## 3. Fork API (StableProjectorz protocol), worth staying compatible with

`api_spz/routes/generation.py`:

| Method | Path | Notes |
|---|---|---|
| GET | `/ping`, `/status` | `status ∈ {PROCESSING, PREVIEW_READY, COMPLETE, FAILED}`, `progress`, `busy` |
| POST | `/generate_no_preview` | multipart form: `seed`, `guidance_scale`, `num_inference_steps`, `resolution` (snapped to 512/1024_cascade/1536_cascade), `mesh_simplify` (×1000 faces, 10–1000), `apply_texture`, `texture_size`, `tex_rescale_t`, `tex_guidance_strength`, `output_format` |
| POST | `/generate_multi_no_preview` | accepts several images but **only uses the first** |
| POST | `/generate` | JSON variant used by the SPZ UI |
| POST | `/interrupt` | cancels by injecting an exception into the worker thread |
| GET | `/download/model` | returns `temp/current_generation/model.glb` |
| GET | `/info/supported_operations`, `/download/spz-ui-layout/generation-3d-panel` | SPZ UI integration |

Takeaway: our backend can expose this protocol as a **compatibility shim**. StableProjectorz
users could then point SPZ at our server and use it for manual AI re-texturing, for free.

## 4. Post-processing internals we will reuse (`o_voxel.postprocess.to_glb`)

The GLB export is a reusable **"bake voxel attributes onto any UV-mapped mesh"** routine:

1. CuMesh cleanup: QEM `simplify`, `remove_duplicate_faces`, `repair_non_manifold_edges`,
   `remove_small_connected_components`, `unify_face_orientations`.
2. Optional **narrow-band dual-contouring remesh** (`cumesh.remeshing.remesh_narrow_band_dc`).
   It rebuilds a clean, closed, uniform triangle shell and projects it back to the surface.
3. UV unwrap with CuMesh's GPU charting plus xatlas packing (`mesh.uv_unwrap`, cone-angle clustering).
4. Rasterize the UV layout with nvdiffrast to get a 3D position per texel. That position is
   **snapped to the original high-res surface via `cuBVH.unsigned_distance`**, then
   **trilinearly sampled from the sparse PBR attribute volume** (`flex_gemm.grid_sample_3d`).
5. `cv2.inpaint` dilation against seams, then a glTF metallic-roughness material
   (B = metallic, G = roughness; alpha kept but `alphaMode=OPAQUE`), and a Z-up → Y-up swap.

**Key architectural consequence:** if we persist the decoded `attr_volume + coords + layout`
(the "MeshWithVoxel"), we can **re-bake PBR textures onto any later mesh**: a retopologized
low-poly, a hand-edited mesh, or a different UV layout. We don't need to re-run diffusion or do
image-space projection. The bake is <1 s of GPU work.

Gaps in `to_glb` that we must add ourselves:
- **No normal-map bake.** Detail lost by decimation or retopo is not transferred.
  `cumesh.cuBVH.ray_trace` (MIT) gives us a GPU ray caster to bake tangent-space normals (and AO
  or height) from the high-poly onto the low-poly.
- No quad output, no edge-flow control, no symmetry. CuMesh is triangle-only.
- `metallicRoughness` packing only. No separate ORM/AO, no emissive.

## 5. Upstream shape-conditioned texturing (`Trellis2TexturingPipeline`)

Released upstream after the fork snapshot (`trellis2/pipelines/trellis2_texturing.py`,
`example_texturing.py`, `app_texturing.py`, config `texturing_pipeline.json`):

```
mesh (any)  -> preprocess_mesh (normalize to unit cube, Z/Y swap)
            -> encode_shape_slat (o_voxel.mesh_to_flexible_dual_grid + shape_slat_encoder)
image       -> DINOv3 cond
            -> tex_slat_flow_model_{512|1024}  (same weights as the image-to-3D texture stage)
            -> tex_slat_decoder -> pbr_voxel
            -> postprocess_mesh: bake pbr_voxel onto the mesh's UVs (or CuMesh-unwrap if none)
```

- It textures **any input mesh** (user meshes, retopologized meshes) with full PBR from one
  reference image. This is the local equivalent of Meshy "AI Texturing" for image prompts.
- **Bug/limitation we must work around:** `preprocess_mesh` returns a new `Trimesh` with no
  visual, so the "keep existing UVs" branch in `postprocess_mesh` is never reached from `run()`.
  The original UVs are discarded and the output is in normalized, axis-swapped space. Our wrapper
  must call `encode_shape_slat → sample_tex_slat → decode_tex_slat` and then run **our own** bake
  on the original mesh, UVs and transform.
- There is no text prompt. Text-driven retexturing needs a text→image step first (concept image
  via a local image model), or a different texturing model (see research 03).

## 6. Licensing facts verified (2026-10-03)

| Component | License | Implication |
|---|---|---|
| TRELLIS.2 code + weights | MIT | OK to bundle |
| TRELLIS v1 `ss_dec` decoder | MIT | OK |
| CuMesh, FlexGEMM, O-Voxel | MIT | OK |
| nvdiffrast | **NVIDIA Source Code License (1-Way Commercial)**: "may be used … only non-commercially" (except by NVIDIA) | TRELLIS.2 uses it **only** for UV-space rasterization in the bake (plus preview renderers we don't need). Write our own small UV rasterizer (PyTorch/Triton) so the default stack is commercial-clean. |
| nvdiffrec (`nvdiffrec_render`) | NVIDIA Source Code License | Only used for PBR preview videos, which we don't need (the preview is three.js in the UI) |
| DINOv3 ViT-L/16 | **DINOv3 License** (gated on HF). Commercial use allowed; redistribution requires shipping the license text and showing **"Built with DINOv3"**; ITAR/military uses prohibited | Download at install time through HF with the user's acceptance, or bundle with the license plus attribution. Show "Built with DINOv3" in About. |
| `briaai/RMBG-2.0` (default bg remover) | **CC BY-NC 4.0**, gated | **Replace** with `ZhengPeng7/BiRefNet` (MIT), which uses the same `BiRefNet` wrapper class. Don't re-host RMBG-2.0 the way the fork does. |

## 7. Community extensions worth tracking or reusing

- **visualbruno/ComfyUI-Trellis2** (MIT, very active, last update 2026-09-08): multi-view
  sampling for sparse structure, shape and texture (`run_multiview(front, back, left, right)`, with
  per-view conditioning blended spatially during sampling), multi-view texturing, hole filling
  (MeshLib/CuMesh), quad remesh nodes, PyMeshLab smoothing, FP8 weights
  (`visualbruno/TRELLIS.2-4B-FP8`), and ReconViaGen (VGGT-conditioned) support. This is the best
  reference implementation for **multi-image character input** on TRELLIS.2.
- **TencentARC/Pixal3D** (MIT, SIGGRAPH 2026): TRELLIS.2 backbone with pixel-aligned
  back-projection conditioning for higher input fidelity. Has a `--low_vram` mode (1024), and
  **multi-view weights + `inference_mv.py` released Sep 2026** (4 views at 0/90/180/270°, with camera
  `transforms.json`). It's the strongest candidate for a "multi-image to 3D" mode that stays inside
  the TRELLIS.2 model family. Algorithms are analysed in
  [02-pixal3d-algorithms.md](02-pixal3d-algorithms.md).
- **ReconViaGen** (ICLR 2026): TRELLIS plus VGGT for multi-view reconstruction. VGGT's original
  checkpoint is non-commercial; only `VGGT-1B-Commercial` is commercial-OK.
- ComfyUI core now ships native `Trellis2*` nodes, which is an interop path if users want graph workflows.

## 8. Integration decisions derived from this deep dive

> **Review update (2026-10-03):** the SPZ fork is stale (last commit 2026-04-28, cp311 wheels with no
> sm_120 story). We now vendor **upstream** TRELLIS.2 and take patches from **localmesh-engine**
> (Apache-2.0, Sep 2026: pure-torch `uvraster.py`, decoy nvdiffrast, `sdpa_backend.py` for sm_120,
> BiRefNet, staged loading) plus upstream PR #173 (keep UVs) and PR #185 (Windows/Blackwell C++ fixes).
> From the fork we keep only its Apr 21–22 chunked-decode commits and the `EXPLICIT_GEMM` fallback.
> Points 1, 6b/7 below are superseded accordingly; the SPZ API shim (8) is deferred.

1. Use the **fork's Windows wheel set and VRAM patches** as the baseline for the TRELLIS.2 worker
   (8 GB target). Track upstream for the texturing pipeline and fixes.
2. Run TRELLIS.2 in an **isolated worker process** (as the fork does), driven by our job queue.
3. **Persist the O-Voxel attribute volume** for every generation. It drives all later re-bakes.
4. **Normalize the transform contract**: TRELLIS works in a `[-0.5, 0.5]³` Z-up cube. Our asset
   store keeps meters and Y-up (glTF), and conversions happen only at worker boundaries.
5. Replace RMBG-2.0 with MIT BiRefNet. Handle DINOv3 gating and attribution in the installer.
6. Add a **GPU normal/AO bake** built on `cumesh.cuBVH.ray_trace`.
7. Replace nvdiffrast in the bake path with our own UV rasterizer (texel → triangle id + barycentrics),
   so that "commercial-clean" mode has no non-commercial dependencies.
8. Offer an **SPZ-compatible API shim** so StableProjectorz can talk to our server.
