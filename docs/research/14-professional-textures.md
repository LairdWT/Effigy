# Research 14: professional textures (M43)

> Status: 2026-10-09. The owner: "do the texture refinements next, I need a high quality solution for making
> textures apply on the generated assets to look them professional". A web survey and repo map the same day, then a
> spike on the reference laptop (RTX 5080 Laptop, 16 GB, torch 2.8.0 cu128, diffusers 0.40.0, `.venv-ml` read-only,
> weights in a scratch folder, never in the repo). Builds on [04](04-texturing.md) and [11](11-retexturing-alternatives.md).
> Numbers marked *(est.)* are not measured.

## 1. Bottom line

- **The detail pass works, and it is already inside our dependencies.** Z-Image-Turbo (Apache-2.0, in the app since
  M10) plus Alibaba-PAI's **Fun-ControlNet Tile 2.1 (2601, 8 steps)** (Apache-2.0) runs through diffusers 0.40's own
  `ZImageControlNetPipeline`: no VideoX-Fun vendoring, no new package. A 1024² view of a baked asset gets real
  buttons, buckles, stitching, fabric and hair strands in **10–14 s** (warm) at **11.9 GB** allocated peak.
- **Back-projected onto the asset's own UVs**, with the M24 low-frequency colour match, the detail survives on the
  mesh and the colours stay the bake's (low-frequency drift 1.6/255 after matching vs 8.6 raw).
- **Strength 1.0, not img2img.** Partial denoising (0.5–0.8) of flat cloth filled it with invented ornament
  (vector-art tracery, embossed carpet patterns); the Tile control alone from pure noise kept the layout and drew
  believable materials. Heads with real detail are the exception: 0.5 kept the face and added hair.
- **The 2K atlas is the next ceiling.** The pirate (1 m) holds 11.4 texels/cm at 2K; the spike's torso view had
  32 px/cm, so two thirds of the new detail was thrown away writing it into the atlas. Views must be zoomed to about
  the atlas's own density, and a 4K atlas is the opt-in for close-ups.
- **Cheap wins first**: AO is still R = 255 in every ORM (bake.py writes no AO), the bake takes 1 sample per texel,
  and UV seams are not healed. These need no model.
- **SuperMat** (delighting + PBR, MIT, SD 2.1 base) was downloaded but **not run**: the spike was stopped once the
  detail pass had answered the main question. It stays a gated item (§5).

## 2. What the bake gives today (repo map)

`steps/bake.py` / `steps/_bake.py`: per texel one sample, the closest point on `hi_trellis.ply` (CuMesh BVH),
trilinear in the 1024³ voxel colour field → `basecolor.png` (the generator's lighting baked in), ORM with
**R = 255 (no AO)**, G/B roughness/metal from the volume, normal from the hi mesh's vertex normals; gutters by
push-pull. No supersampling (research 04 §5 planned 2×), no seam healing. `steps/project.py` (M23/M24) puts the
Faithful image onto the head only (Real-ESRGAN ×4, local colour match, IoU gate). `trellis2` op `texture` (M12)
re-textures at the same 1024 grid. Gaps, ranked: colour detail capped by the 1024³ field; lighting in the albedo;
only the head projected; no AO; low-res rough/metal; no supersampling or seam healing; no texel-density control.

## 3. Survey facts that decided the design (2026-10-09)

- **Z-Image ControlNet is in diffusers**: `ZImageControlNetPipeline` and `ZImageControlNetInpaintPipeline`
  (diffusers PR #12792, release 0.37.0, 2026-03-05); the app pins 0.40.0, both classes import
  ([diffusers releases](https://github.com/huggingface/diffusers/releases)).
- **Fun-ControlNet-Union 2.1** ([card](https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union-2.1),
  Apache-2.0, repo revision `5155fc56d17821007d6f62ac192c09e0f0e72016`): Union (canny, depth, pose, MLSD, HED,
  scribble, gray), inpaint mode, and a **Tile model "trained on high-definition datasets (up to 2048×2048) for
  super-resolution"**; 2601 retrains "reducing bright spots and artifacts"; **lite** builds (3 control blocks,
  2.0 GB) beside the full ones (15 blocks, 6.7 GB). Files: `Z-Image-Turbo-Fun-Controlnet-Tile-2.1-2601-8steps.safetensors`
  (6 712 485 600 B), `…-Tile-2.1-lite-2601-8steps.safetensors` (2 016 627 488 B). **No normal control.**
  Recommended `control_context_scale` 0.65–1.00.
- **SuperMat** ([code](https://github.com/hyj542682306/SuperMat), [weights](https://huggingface.co/oyiya/SuperMat),
  [arXiv 2411.17515](https://arxiv.org/abs/2411.17515)): MIT code and weights (LICENSE checked; 2026 copyright), base
  SD 2.1 (OpenRAIL++, allowed by PLAN §6; `sd2-community/stable-diffusion-2-1` since Stability removed theirs);
  single-image and 6-view models at 512², UV refine nets at 1024² for albedo and rough/metal; ~3 s/object on an A100;
  albedo PSNR 27.68 vs 24.56 in its table; weak on high-frequency detail and very reflective or transparent
  materials. `xformers` is listed in requirements but is only imported at module level in
  `src/models/custom_attention_processor.py`; the MV path already has an SDPA `MVAttnProcessor2_0` (source read).
- Out, rechecked: Qwen-Image-Edit-2511 Q4 (>660 s without one step, 15.8 GB + spill: our m16 bench); Marigold V2
  (~17 GB, Linux); UltraTex (FLUX.1-dev / klein-9B LoRAs); MV-Adapter texturing (nvdiffrast + CV-CUDA); Material
  Anything (PyTorch3D + Blender 3.2.2); Hunyuan family; no-licence repos (TEXGen, TexGaussian, MVPaint, SeqTex,
  LumiTex); SUPIR (NC); InvSR, RGB↔X, IntrinsicAnything (non-commercial / unclear). SyncMVD's synchronisation wins
  colour consistency, not detail (it averages detail away): kept for a later text restyle, not for this pass.
- Commercial baseline: Meshy retexture defaults `enable_original_uv: false`, `remove_lighting: true`, 2K
  ([API](https://docs.meshy.ai/en/api/retexture)): keeping the UVs is ours alone.

## 4. Spike (measured on the laptop, 2026-10-09)

Subject: `bench_faithful_pirate/200_project` (Faithful, 14 320 faces, 2K, face projected by M23; 1 m tall). The
first choice, the dwarf blacksmith `480_bake`, has a near-black concept (a dark silhouette image) and was useless
for judging texture. Views: orthographic, unlit base colour, drawn with the repo's own `rasterize_uv` in z-buffer
mode at 2048² and box-filtered to 1024² (5 views in 1.2–2.6 s, 1 GB). Back-projection: `project.py`'s recipe
(smoothstep of cos from 0.25 over 0.35, z-test against the 3×3 farthest depth + 1 % slop, faces turned to the
camera), then `fill_gutters`.

**Loading**: `ZImageControlNetModel(**config)` + `load_state_dict(safetensors)` (0 missing, 0 unexpected) for both
Tile files. `from_single_file` mis-detects the lite file (its key test looks for `control_layers.14`); the lite
config is VideoX-Fun's `z_image_control_2.1_lite.yaml`: `control_layers_places [0, 10, 20]`,
`control_refiner_layers_places [0, 1]`, `control_in_dim 33`; the full one `[0, 2, …, 28]`. The pipeline ties the
shared modules (`t_embedder`, `noise_refiner` …) to the DiT, so fp8 storage on the control net must hook only
`control_layers` and `control_noise_refiner` (`apply_layerwise_casting` on those two; `enable_layerwise_casting`
on the whole control net fails: "Hook with name layerwise_casting already exists"). DiT as `steps/concepts.py`:
`enable_layerwise_casting(float8_e4m3fn → bf16)`, prompts encoded with the text encoder alone on the card, then off.

| Run (8 steps, guidance 0, scale 0.85, 1024²) | Time (s) | Peak alloc. (GB) |
|---|---|---|
| Load, Tile lite (cold) / full | 38.2 / 56.4 | — |
| Text encoder alone (5 / 4 prompts) | — | 8.52 / 8.32 |
| Lite, first view (warm-up) / next views | 25.8 / 6.4–7.8 | 10.34 |
| Full, first view / next views | 19.3 / 10.1–13.8 | 11.95 (reserved peak 15.12) |
| Lite, one 2048² view | 127.0 | 17.76: spills past 16 GB → **no 2048² views** |
| Back-projection of one 1024² view into 2K | 0.55 | < 1 |

**What the images show** (`14_tile_torso.jpg`: bake, lite 0.6, full 0.8, lite 1.0, full 1.0;
`14_tile_head_front.jpg`: head bake / lite 0.5, front bake / lite 0.6; `14_backproject.jpg`: front before / after,
three-quarter before / after, 70° after):
- **Bake**: the voxel ceiling, plainly: mushy buttons, a blob buckle, shirt and vest smeared, red streaks.
- **Partial denoise (0.6, 0.8)** keeps the layout to the pixel but paints ornament nobody asked for: vector-like
  tracery over the vest and trousers (lite 0.6), embossed carpet patterns on the trousers (full 0.8). Sharpness
  measured as Laplacian variance falls (81 → 61 / 56): the model invents pattern, not detail.
- **Strength 1.0** draws a costume: brass buttons with rims, a cast buckle with its pin, belt holes, linen weave,
  waistcoat seams. The **full** Tile keeps the navy and the garment edges; the **lite** one drifts more (vest to
  charcoal, the sash rerouted diagonally, studio shading under the belt). Low-frequency drift vs the bake 8.6 (full)
  / 11.7 (lite) on 0–255; Laplacian variance 245 / 243. The full model added a faint plaid to the trousers.
- **Head at 0.5** (full and lite): the face stays the same person; hair gets strands, braids and beads become
  objects, the hat leather grain; the projection's white streaks in the hair are painted over. Lite invented a faint
  chest tattoo. **Full body at 0.6**: layout kept, the waistcoat gets brocade, but the face changes (another man).
- **Back-projected** (full 1.0, colour-matched): front: real buttons and buckle on the mesh, shirt weave, colours of
  the bake (drift 1.6 after matching, 1.8 in the matched view); three-quarter: the detail holds on the surfaces the
  view saw (drift 1.3), the transition into the old texture shows on the vest's side where the weight fades out;
  70°: grazing surfaces keep the bake, as designed. One view painted 5.1 % of the atlas's texels; mean change
  in that view 0.025 (0–1).
- **Laplacian variance is the wrong sharpness metric here**: the back-projected front scores 73 against the bake's 81
  although it looks clearly sharper, because the bake's speckle counts as "detail". The bench needs a band-limited
  measure (energy in the 2–8 px band, background excluded) or the owner's eye.
- **Texel density**: 2K holds 11.4 px/cm on this 1 m asset; the torso view had 32 px/cm; fine weave did not
  survive the trip into the atlas, buttons and buckle did.

**SuperMat**: weights (`supermat.pth` 3.5 GB) and the SD 2.1 fp16 base (2.5 GB) downloaded; not run. Unknowns that
remain: SDPA in the single-image path (needs a stub `xformers` module or a one-line import change in our copy),
compatibility with diffusers 0.40, speed and VRAM on sm_120, and whether its albedo beats "bake ÷ AO" on our assets.

## 5. Decisions

1. **A new step `refine`** (texture refinement on the asset's own UVs), not an extension of `bake` or `project`:
   it reads any textured, UV-mapped version and writes the same four files `bake` writes, so everything after it
   (rig, export) is unchanged. `project` stays the face path for Faithful assets; `refine` runs after it.
2. **Cheap wins go into `bake` itself** (M43a): 2× supersampled UV raster (4 samples per texel, box-filtered),
   AO from hemisphere rays on the hi mesh written into ORM R and declared as the glTF `occlusionTexture`, seam
   colour healing (texels along UV seams blended with their 3D neighbours across the seam). Same files.
3. **Detail pass** (M43b): Z-Image-Turbo + **Tile 2.1-2601-8steps, full**, strength 1.0, scale 0.85, 1024² views,
   orthographic, unlit albedo renders zoomed to about 1–1.5× the atlas's texel density; **sequential**: each view is
   rendered from the texture as the previous views left it, so overlaps continue rather than contradict; per-view
   low-frequency colour match (`project.shading_offset`'s method) before back-projection; texel weight cos-smoothstep
   × z-test × eroded silhouette, the best view wins (weight⁴-normalised blend), unseen texels keep the bake. Faces
   from `project` refine at 0.5. No 2048² views (spill measured). Lite Tile is the fallback if the full one's
   reserved peak breaks 14.5 GB on a busy desktop.
4. **Delight / PBR** (M43c): first the model-free "divide out AO" (albedo luminance regressed on the baked AO at low
   frequency, removed with a strength), measured by the AO–luminance correlation; SuperMat only behind a spike gate
   (it runs with SDPA, ≤ 6 GB, and its albedo beats the AO divide on the bench), as a low-frequency correction like
   M24's, keeping the bake's high frequencies; TRELLIS rough/metal stay unless SuperMat's win the owner's A/B.
5. **Not now**: SR on views (the Tile pass replaces it; Real-ESRGAN stays for `project`), LaMa (push-pull suffices
   for gutters), a text restyle with depth control + SyncMVD (a separate milestone if the owner wants restyles),
   4K by default (opt-in), Qwen-Edit masked edits (too slow on 16 GB).

## 6. Risks

- **Hallucination**: plaid, tattoos, pendants appear with no prompt for them; Turbo has no CFG, so no negative
  prompt. Prompts name materials plainly ("plain dark brown wool trousers"); the owner's before/after decides;
  per-view keep/drop is the upgrade if it bites.
- **Face identity** changes at 1.0 and in full-body views: faces stay at 0.5 and in zoomed head views only.
- **Studio shading** drawn into the views (shadows under belts) survives the low-frequency match at mid frequency.
- **Seams between views**: visible where one view's weight fades into the bake (the vest's side); 8 yaws instead of 4
  and sequential rendering are the mitigation; measured by the seam metric.
- **VRAM**: 11.95 GB allocated, 15.12 GB reserved with the full Tile; Windows desktop compositors take 0.8–1.5 GB.
- **Time** *(est.)*: ~16 views × 12 s + 60 s load ≈ 4–5 min per asset.
- Licence drift of the Fun weights (pin the revision); SuperMat's SD 2.1 base sits behind a re-host (sd2-community).

## Sources

github.com/huggingface/diffusers (PR #12792, v0.37.0; `pipelines/z_image/pipeline_z_image_controlnet.py`) ·
huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union-2.1 · github.com/aigc-apps/VideoX-Fun
(`config/z_image/z_image_control_2.1_lite.yaml`, `examples/z_image_fun/predict_i2i_tile_2.1.py`) ·
huggingface.co/Tongyi-MAI/Z-Image-Turbo · github.com/hyj542682306/SuperMat · huggingface.co/oyiya/SuperMat ·
arxiv.org/abs/2411.17515 · huggingface.co/sd2-community/stable-diffusion-2-1 · docs.meshy.ai/en/api/retexture ·
research 04, 11 and their sources.
