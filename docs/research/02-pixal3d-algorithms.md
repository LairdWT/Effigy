# Research 02: Pixal3D (pixel-aligned TRELLIS.2), algorithms to adopt

> Status: research notes, 2026-10-03. Source: `TencentARC/Pixal3D` (main @ `f7cf384`, 2026-09-01,
> MIT, SIGGRAPH 2026, arXiv 2605.10922), the HF weights `TencentARC/Pixal3D`, and the parameter
> surface of the `Pixal3DImageTo3D` ComfyUI node (https://comfy.icu/node/Pixal3DImageTo3D).
> **We take the algorithms and weights, not ComfyUI.** Pixal3D runs on the same stack as TRELLIS.2
> (O-Voxel, CuMesh, FlexGEMM, identical latent spaces), so it fits into our `trellis2` engine as a
> second "generator profile".

## 1. Why it matters for us

Stock TRELLIS.2 injects the image only through **global cross-attention** on DINOv3 tokens. The
model has to work out where each pixel belongs in 3D, so the front view tends to look
"inspired by" the input rather than matching it. Pixal3D adds an explicit **pixel → voxel
back-projection**:

- Each sparse token gets the image features from where it projects in the input view. The paper
  claims near-reconstruction-level fidelity, which matters most for faces, logos and costume
  details on characters.
- There's a released **multi-view variant** (Sep 2026). Front, side and back views from a
  character turnaround sheet are fused in the *same* 3D grid. This is the "multi-image to 3D" mode
  we need for characters.
- Same cascade and same O-Voxel output as TRELLIS.2, so our cleanup, remesh, bake, rig and export
  stages work unchanged.

## 2. Algorithm 1: view-aligned projection conditioning

Code: `pixal3d/trainers/flow_matching/mixins/image_conditioned_proj.py`
(`ProjGrid`, `DinoV3ProjFeatureExtractor`) and `pixal3d/modules/sparse/attention/proj_attention.py`.

1. **Feature map.** DINOv3 ViT-L/16 encodes the preprocessed image (512 or 1024 px) into a
   patch-token grid. For the shape and texture stages, **NAF** (valeoai, Apache-2.0) also
   upsamples those patch features to 512 or 1024 px using the RGB image as guidance. The projected
   feature is then `concat(lowres, highres)` with 2048 channels.
2. **Projection grid.** Each stage has a fixed dense 3D grid in `[-1,1]³`: **16³** for sparse
   structure, **32³** for shape-512, **64³** for shape-1024 and tex-1024. It's rotated into
   Blender convention, scaled by `1/(2·mesh_scale)`, and projected with a pinhole camera at
   `(0, -distance, 0)` looking at the origin (FOV `camera_angle_x`). Features are bilinearly
   sampled at the projected pixel. There's **no visibility test**: occluded voxels get the
   feature of the surface in front of them, and the denoiser learns to cope.
3. **Sparse gather.** For the sparse stages, the dense grid features are gathered at the active
   voxel coordinates, so each token carries its own pixel feature.
4. **Injection.** In every transformer block, `SparseProjectAttention` runs the normal global
   cross-attention and **adds** `proj_linear(pixel_feature)` to its output. A gated variant fuses
   DINOv3 with FLUX-VAE color features through a zero-initialized linear layer. That variant
   isn't used by the released inference configs (good, because FLUX.1-dev's VAE is
   non-commercial).
5. **View-aligned latents.** Training data is rendered and voxelized in the *camera frame* of the
   condition view, so the output asset is **aligned with the input view**, not canonicalized. For
   characters this is good: a front-facing input gives a front-facing (−Y forward) asset. Our
   cleanup stage still applies the glTF axis convention.

## 3. Algorithm 2: camera fitting

`inference.py::get_camera_params_wild_moge`, `distance_from_fov`:

- **FOV** comes from **MoGe-2 ViT-L** (`Ruicheng/moge-2-vitl`, MIT), which predicts normalized
  intrinsics. `camera_angle_x = 2·atan(W / (2·fx))`.
- **Distance** is solved in closed form so that the grid's horizontal extent (`x = ±1`, scaled by
  `mesh_scale`) lands exactly on the image's left and right edges, `±extend_pixel`. The image is
  first cropped tightly to the object's alpha bounding box and padded to square, so "object fills
  the frame width" holds.
- Overrides: `camera_mode=manual` with `manual_camera_angle_x` (default 0.858 rad ≈ 49°),
  `manual_distance`, `mesh_scale`, and `extend_pixel` (shifts the fitting target; useful when the
  silhouette touches the frame).
- **Implication for concept art and character sheets:** illustrations are usually near-orthographic.
  MoGe on drawn art can return arbitrary FOVs, so our UI should default **drawn/turnaround inputs
  to a narrow manual FOV (≈20°, the same rig the MV example uses)** and photos to MoGe.

## 4. Algorithm 3: multi-view fusion (`inference_mv.py`, `Pixal3DMVImageTo3DPipeline`)

- Input: V views with **camera-to-world matrices** and FOV(s) in Blender/NeRF `transforms.json`
  convention (Z-up, camera looks along −Z). **View 0 must be the canonical front**
  (camera at `(0,-d,0)`).
- For each view i, `calc_mat_i = F · inv(C_0) · C_i`, where `F` is the canonical front matrix. The
  *same* 3D grid is projected through every view (`ProjGridMV`).
- **Fusion = per-voxel mean** of projected features across views, and the global tokens are
  averaged too. The tensor shape is the same as single-view, so the architecture is unchanged,
  but there are **dedicated `_mv` checkpoints** for every stage
  (`ss_flow_…_mv`, `slat_flow_img2shape_…_{512,1024}_mv`, `slat_flow_imgshape2tex_…_1024_mv`).
  An `"attention"` fusion mode exists in code (keeps the view dimension) but isn't used by the
  released weights.
- **Views are not cropped or rescaled individually.** Framing must be consistent with the cameras.
  The shipped rig is 4 views at azimuth 0/90/180/270°, elevation 0°, FOV 20°.
- **Implication for our prep stage:** a "character turnaround" input mode must (a) split the sheet
  into views, (b) apply **one shared crop/scale** to all views (common bounding box, centered on
  the same vertical axis), (c) assign the standard 4-view cameras, or the user-specified ones,
  and (d) reject or warn on inconsistent heights between views. Generated turnaround sheets often
  drift in proportions. A quick sanity check: compare silhouette heights across views.

## 5. Practical numbers and parameters

- Cascade: SS (64³) → shape 512 → shape 1024 (and optionally 1536) → texture 1024.
  `pipeline_type ∈ {1024_cascade, 1536_cascade}`, `max_num_tokens=49152`, 12 steps by default,
  guidance 7.5 (structure and shape) and 1.0 (texture).
- Low-VRAM mode loads models on demand and defaults to 1024. **MoGe and the generator are never
  resident together.**
- Reported by the ComfyUI wrapper: **about 5–6 min/asset at 1024_cascade, 20 steps, 4096 texture on
  an RTX 4070 Ti 12 GB.** That's slower than plain TRELLIS.2 because of the extra NAF/projection
  work and the 4K bake.
- Weights size: one extra set of 1.3B DiTs per stage plus the `_mv` set. Budget about 2× the
  TRELLIS.2 disk footprint if both profiles are installed.

## 6. Licenses

| Component | License | Note |
|---|---|---|
| Pixal3D code + weights | MIT (Tencent, with NOTICE) | Ship NOTICE and attribution. **Relicensed to MIT ~late May 2026** (custom restrictive terms before; HF discussion #2). The HF card still sets `extra_gated_eu_disallowed: true`, but the repo is `gated: false`, so the flag is inert (verified 2026-10-03). We treat the MIT LICENSE as governing; Pixal3D is a default-profile candidate ("Faithful" weights), with the note kept visible. |
| MoGe-2 ViT-L weights, MoGe code | MIT | |
| NAF upsampler | Apache-2.0 | Loaded via `torch.hub` from GitHub. **Vendor it** so we don't hit the network at runtime |
| NATTEN (NAF dependency) | MIT; **source-only on PyPI, needs a CUDA build** | No official Windows wheels, so it's a packaging risk (see below) |
| DINOv3 (`camenduru/…` re-upload used by inference.py) | **DINOv3 License** still applies | Use the official gated repo or our licensed mirror with "Built with DINOv3" attribution |
| RMBG-2.0 (default rembg again) | CC BY-NC 4.0 | Swap for `ZhengPeng7/BiRefNet` (MIT), same as for TRELLIS.2 |
| utils3d | MIT | Only used by renderers and data tools, not needed for inference |

**NATTEN on Windows.** NAF imports `natten.na2d`. Options, in order of preference: (1) build and
host our own Windows wheels in CI (the same approach the SPZ fork uses for cumesh/flex_gemm);
(2) a pure-PyTorch neighborhood-attention fallback for NAF (slower but small, since NAF runs once
per stage); (3) run without NAF upsampling (`use_naf_upsample=False`). Option 3 changes the
projected feature width the weights expect, so it's **not viable** without retraining. Only (1)
and (2) are real options.

## 7. What we adopt

0. The **algorithms** (pixel back-projection conditioning, MoGe camera fit, shared-framing
   multi-view ingestion) are MIT code and can be used whatever is decided about the weights. If
   the EU flag rules out Pixal3D weights for a user, the plain TRELLIS.2 multi-view *blending*
   approach from ComfyUI-Trellis2 (per-view conditioning, spatially blended at each sampler step,
   no retraining) is the fallback for multi-image input.
1. **Generator profiles** in the `trellis2` engine: `trellis2` (default, fastest), `pixal3d`
   (high input fidelity, single view) and `pixal3d-mv` (multi-view). All three produce the same
   MeshWithVoxel output, so everything downstream is shared.
2. **Camera-fit step** in image prep: MoGe-2 for photos and a manual narrow FOV for illustrations
   and turnarounds, exposed as "Camera: Auto / Orthographic-like / Manual" in the UI.
3. **Turnaround-sheet ingestion** with shared framing and standard 4-view cameras (§4).
4. The **pixel-projection idea for our own texture re-projection**. When the user gives a
   high-res front image, we can project it directly onto the final low-poly UVs, with a
   visibility test, to sharpen the front-facing albedo after the voxel bake. That's a cheap,
   deterministic "detail transfer" pass that doesn't need another model.
5. The same **VRAM discipline**: sequential model residency, with depth/camera models unloaded
   before the DiTs load.
