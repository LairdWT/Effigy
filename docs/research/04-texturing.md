# Research 04: Texturing and retexturing (local "AI Texturing" / "Retexture")

> Status: research notes, 2026-10-03. Compiled from a delegated literature/repo survey plus our own
> source reading (see [01](01-trellis2-deep-dive.md)). Licenses were checked against LICENSE files and
> model cards. Items marked *(est.)* are estimates.

## 1. Bottom line

- **The MVP needs no extra texturing model.** TRELLIS.2 already produces full PBR
  (base color, metallic, roughness, alpha) as a sparse voxel field. We persist that field and
  **bake it onto whatever mesh comes out of retopology**. For imported meshes or a new reference
  image, `Trellis2TexturingPipeline` (shape-conditioned, MIT) re-textures any mesh.
- **Problems in upstream, and our fixes:**
  - The keep-UVs path is dead code: `preprocess_mesh` drops `visual`. The fix is in upstream
    PR #173/#175, still unmerged; we patch it in our vendored copy.
  - Output stays in the normalized frame. We restore the original transform.
  - Default RMBG-2.0 is non-commercial. We swap to BiRefNet (MIT).
  - nvdiffrast is non-commercial. We use our own PyTorch UV rasterizer.
  - There's no normal or AO map. We bake those from the high-poly.
  - There's no text input. We go text → image → texture.
- **Detail ceiling:** texture information is limited by voxel resolution (≈ 1/1024 of the bbox at
  1024³). A 4K map adds nothing over 2K unless generated at 1536 or refined in 2D. That's the
  reason for a later **2D refinement / projection pass** (§4b).
- **Best open PBR quality is Hunyuan3D-2.1 Paint**, but its license **excludes the EU, UK and South
  Korea** and it re-unwraps UVs. Plugin only, region-gated, never default.

## 2. Candidate matrix (abridged)

| Candidate | Licence (code / weights) | VRAM | Inputs | Outputs | Keeps our UVs? | Verdict |
|---|---|---|---|---|---|---|
| **TRELLIS.2 texturing** (Dec 2025) | MIT / MIT (DINOv3 licence; RMBG-2.0 & nvdiffrast NC, both replaceable) | ~6 GB @512, ~10–16 GB @1024 *(est.)*; FP8/GGUF/int8 community weights exist | mesh + 1 image | BaseColor, Metallic, Roughness, Alpha | after patch | **Primary** |
| TRELLIS.2 voxel re-bake (no diffusion) | MIT | <1 GB, <1 s | MeshWithVoxel + any UV mesh | same PBR | yes | **Primary for generated assets** |
| Pixal3D texture stage | MIT (stale EU flag on HF card) | 1024/12 steps/2K ≈ 14 GB | image(s), **2–4 views with cameras** | PBR | via our bake | **The multi-image retexture path** (TRELLIS.2 upstream never shipped one; its multi-image conditioning is reported worse than single-image) |
| Hunyuan3D-2.1 Paint | Tencent Community (no EU/UK/KR; >1M MAU needs licence) | ~21 GB | mesh + image | albedo + MR, 4K | **no** (xatlas re-unwrap) | Optional plugin, geo-gated |
| Hunyuan3D-2.0 Paint/Delight | Tencent Community (same territory) | ~10–12 GB | mesh + image | RGB | no | Avoid |
| MV-Adapter texture | Apache-2.0 (SDXL OpenRAIL++); deps nvdiffrast (NC), CV-CUDA (no Windows) | 12–16 GB SDXL | mesh + text/image | RGB (PBR only with PBR views) | yes | Reference design, needs dep swaps |
| Material Anything | MIT / Apache-2.0 | n/a | mesh (+text) | albedo, rough, metal, bump | UV refiner | Later: PBR-izing albedo-only meshes |
| MVPainter (+IDArb) | Apache-2.0 / MIT | n/a | mesh + image | RGB → PBR | own | Watch |
| SeqTex (VAST) | MIT (per HF Space; no LICENSE in repo) | A100-class | UV mesh + text | UV texture | native | Research |
| UniTEX, TEXGen, Paint3D, SyncMVD, Step1X-3D Tex | mixed (FLUX-dev base, Tencent code, SD1.5 era) | high | – | – | – | Avoid / dated |
| **UltraTex** (SIGGRAPH Asia 2026, Oct 2026) | MIT code; released LoRAs only for FLUX.1-dev / klein-9B (**NC** bases); klein-4B incompatible | likely > 16 GB | ref image + 6 normal G-buffers | 2K multi-view albedo + metal-rough; beats Hunyuan Paint 2.1 on FID/LPIPS | – | **Watch** for a klein-4B branch |
| MaterialMVP, RomanTex, NaTex (repo 404), LaFiTe, PixTex, Meta TextureGen/AssetGen | no usable code/weights | – | – | – | – | Watch |

**Tools and reference designs**
- **StableProjectorz**: AGPL-3.0 (verified), Unity 6/C#. It has a loopback JSON-over-TCP "Agent
  Bridge" and a separate MIT MCP server (`spz-mcp`). Integrate only as a **companion process**
  through its protocol; never embed its code.
- **StableGen**: GPL-3.0 Blender add-on. It's a good *design* reference for projection retexturing
  (multi-camera projection, sequential inpainting, Marigold/StableDelight PBR split).
- **ComfyUI-Trellis2** (MIT, very active): "Mesh Texturing", "Projection MultiView Texturing" and
  "Projection HighPoly to LowPoly" nodes, plus Windows wheels and FP8. A good MIT reference
  implementation.
- **ComfyUI core** (GPL-3.0) has a native TRELLIS.2/Pixal3D port with no compiled CUDA extensions
  and a normal/AO bake. Use it as a reference only; don't copy code.
- **trellis.cpp / trellis2cpp** (MIT, GGUF): C++ ports that have already replaced nvdiffrast. They
  could become a lightweight runtime backend later.

## 3. Supporting components (licence-clean choices)

| Need | Choice | Licence | Avoid |
|---|---|---|---|
| Background removal | `ZhengPeng7/BiRefNet` (+ `_HR`, `-matting`), BEN2 base | MIT | RMBG-2.0 (CC BY-NC), RMBG-1.4 (Bria agreement) |
| Delighting / PBR split for 2D images | StableDelight (`yoso-delight-v0-4`), Marigold-IID v1.1 | Apache-2.0, OpenRAIL++ | Hunyuan Delight (territory), UniTEX delight LoRA (FLUX-dev) |
| Upscale | Real-ESRGAN via spandrel; SeedVR2-3B | BSD-3/MIT; Apache-2.0 | Running SR over a whole UV atlas (bleeds across seams). Upscale views or per-chart with padding |
| Inpainting | TRELLIS.2 voxel texels as fill; LaMa | MIT; Apache-2.0 | |
| Text→image / edit / ControlNet | Qwen-Image, Qwen-Image-Edit-2511, InstantX Qwen ControlNet-Union, Z-Image-Turbo, FLUX.2-klein-4B, SDXL+ControlNet | Apache-2.0 (SDXL: OpenRAIL++) | **FLUX.1-dev / FLUX.2-dev (non-commercial)** |
| Viewer | three.js (+ debug modes for albedo/rough/metal/normal/AO) | MIT | model-viewer (too limited for editing UIs) |

## 4. Recommended texturing design

### 4a. MVP: "TRELLIS.2 only"
1. **Generated assets**: never re-generate the texture. Persist `attrs/coords/voxel_size/layout`
   as `ovoxel.npz` and **bake onto the retopo mesh's own UVs** (§5).
2. **Imported mesh / new reference image**: our patched `Trellis2TexturingPipeline` keeps the
   UVs, restores the transform, uses BiRefNet and our rasterizer, and defaults to 1024 voxels
   with a 2K map. 8–12 GB cards get 512, or 1024 with FP8 and sequential offload.
3. **Normal + AO** baked from the high-poly (TRELLIS.2 produces neither), packed as glTF
   `normalTexture` plus ORM (R=AO, G=roughness, B=metallic).

### 4b. v1: text-driven and high-detail retexture
> Revisited 2026-10-08 in [11-retexturing-alternatives](11-retexturing-alternatives.md): keep this architecture, but
> synchronise the views in UV latent space (SyncMVD) instead of shared seeds/grids, start from Z-Image-Turbo + its
> Apache ControlNet-Union, and replace the Marigold-IID re-estimation with targeted StableDelight + AO passes.

- **Text → texture, staying inside TRELLIS.2:**
  1. Render the mesh's front depth and normals.
  2. Generate a geometry-aligned reference with an Apache-licensed model plus ControlNet
     (Z-Image-Turbo / FLUX.2-klein / Qwen-Image + ControlNet-Union).
  3. Run BiRefNet, then the TRELLIS.2 texturing pipeline.

  This gives full PBR with no occlusion holes and stays licence-clean.
- **Detail / edit pass (Meshy "Retexture" equivalent):**
  1. Render 4–8 views of the TRELLIS.2-textured mesh.
  2. Refine or edit them with SDXL + ControlNet tile/depth, or Qwen-Image-Edit, using shared seeds
     or grid layout for consistency.
  3. Upscale.
  4. **Back-project into the UVs**, weighted by cos(view angle), with depth-test masks.
  5. **Fall back to TRELLIS.2 texels wherever no view sees the surface**, so no inpainting model
     is needed.
  6. Keep TRELLIS.2 metallic/roughness, or re-estimate with Marigold-IID.

  This is the StableGen/SPZ architecture rebuilt on permissive parts. The Pixal3D-style direct
  projection of a user's hi-res front image ([02 §7](02-pixal3d-algorithms.md)) is the
  zero-model special case.
- **Optional plugins** (opt-in, licence-flagged):
  - Hunyuan3D-2.1 Paint, patched to skip re-unwrap, geo-gated.
  - MV-Adapter, with its deps swapped.

## 5. Baking TRELLIS.2 PBR onto a retopologized mesh (algorithm)

1. Keep the **pre-decimation high-res mesh + sparse attribute volume** in TRELLIS frame (Z-up,
   `[-0.5,0.5]³`). Map the retopo mesh into the same frame (inverse of the store's transform).
2. Rasterize the low-poly **in UV space** at the target size (2× supersample, then downsample) to
   get position, face id and interpolated normal per texel.
3. Find the high-poly correspondence:
   - **Default:** a **cage ray-cast** along the low-poly normal in both directions
     (`cumesh.cuBVH.ray_trace`), with a max distance.
   - **Fallback:** closest point (`cuBVH.unsigned_distance`, what `to_glb` does). Closest point
     alone misassigns texels on thin or concave parts.
4. Trilinear sample of the attribute volume at the hit point (`flex_gemm.grid_sample_3d`, or a
   pure-torch sparse-hash 8-neighbour lookup for the commercial-clean and Windows-fallback path).
5. **Normal map:** high-poly normal at the hit, expressed in the low-poly **MikkTSpace** tangent
   frame, stored in OpenGL (+Y) convention as glTF expects.
6. **AO:** hemisphere ray-trace against the high-poly, written to ORM.R.
7. Gutter fill: 8–16 px push-pull, which beats Telea for mip-mapping.
8. `alphaMode` is MASK or BLEND only if some alpha < 1, otherwise OPAQUE.

Reference implementations: ComfyUI-Trellis2 "Projection HighPoly to LowPoly" (MIT). Headless
Blender "Selected to Active" with a cage, run as a separate GPL process, is the slow fallback.

## 6. Risks
1. Non-commercial deps hidden in defaults: nvdiffrast and RMBG-2.0 (TRELLIS.2), nvdiffrast
   (MV-Adapter), FLUX-dev bases (UniTEX/SeqTex recipes).
2. Tencent territory clauses (Hunyuan Paint/Delight) and the Pixal3D HF "EU-disallowed" flag.
3. Windows builds of CUDA/Triton extensions. Use community wheels or our CI wheels, with a
   PyTorch-only fallback path.
4. Upstream stagnation: Microsoft hasn't merged feature PRs since Jan 2026. **Vendor and patch.**
5. Voxel-resolution texture ceiling; logos and text drift (not pixel-aligned).
6. Bake artefacts on thin parts; frame/scale mismatches between the TRELLIS frame and the asset frame.
7. Consistency problems in projection edits (seams, Janus, baked lighting). Keep TRELLIS.2 as base
   and fallback.
8. Hunyuan/Step1X silently remesh and re-unwrap. They must be patched before use on retopo meshes.

## Sources
github.com/microsoft/TRELLIS.2 (incl. issues #129, #173, PR #175) · huggingface.co/microsoft/TRELLIS.2-4B ·
github.com/TencentARC/Pixal3D · github.com/visualbruno/ComfyUI-Trellis2 · blog.comfy.org/p/trellis2-and-pixal3d-are-now-native ·
github.com/pwilkin/trellis.cpp · github.com/localai-org/trellis2cpp · github.com/Tencent-Hunyuan/Hunyuan3D-2.1 ·
github.com/huanngzh/MV-Adapter · github.com/3DTopia/MaterialAnything · github.com/amap-cvlab/MV-Painter ·
github.com/VAST-AI-Research/SeqTex · github.com/YixunLiang/UniTEX · github.com/cvmi-lab/TEXGen ·
github.com/IgorAherne/StableProjectorz · github.com/redDwarf03/spz-mcp · github.com/sakalond/StableGen ·
huggingface.co/briaai/RMBG-2.0 · huggingface.co/ZhengPeng7/BiRefNet · huggingface.co/PramaLLC/BEN2 ·
github.com/NVlabs/nvdiffrast/blob/main/LICENSE.txt · huggingface.co/Stable-X/yoso-delight-v0-4-base ·
huggingface.co/prs-eth/marigold-iid-appearance-v1-1 · huggingface.co/Qwen/Qwen-Image-Edit-2511 ·
huggingface.co/Tongyi-MAI/Z-Image-Turbo · huggingface.co/black-forest-labs/FLUX.2-klein-4B ·
huggingface.co/InstantX/Qwen-Image-ControlNet-Union · github.com/xinntao/Real-ESRGAN · github.com/advimman/lama
