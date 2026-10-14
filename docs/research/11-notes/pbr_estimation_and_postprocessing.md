# PBR material estimation and texture post-processing models (state as of 2026-10-08)

Scope: candidates that could improve an already-baked 2K UV atlas (albedo + metallic/roughness from the 1024³ voxel bake, Blender normal bake, Real-ESRGAN 4× face projection) on an RTX 5080 Laptop (16 GB, sm_120, Windows 11, torch 2.8 cu128, SDPA only, no nvdiffrast/xformers/flash-attn). Licence policy as given in the assignment (allowed: MIT, Apache-2.0, BSD, CC0, OpenRAIL/OpenRAIL++, NVIDIA Open Model License, etc.; never: non-commercial, research-only, FLUX-dev/9B family, Hunyuan outside the experimental engine, Adobe research licences).

Method note: GitHub API and `gh` were gated in this session, so "last commit" dates come from Hugging Face `lastModified` fields and README news entries, not from git. Where a README did not state a licence I fetched the LICENSE blob directly; where that 404'd it is listed as a gap.

## Key question 1: Which delighting / PBR-estimation models are commercial-clean and could run in ≤ ~4 GB at 2K on Windows with torch 2.8 (or tile to that)?

### Takeaway
No delighting/PBR-estimation model that is both commercial-clean and documented at ≤ 4 GB for 2K exists; the clean ones are all Stable-Diffusion-2-class UNets (~0.9–1.3 B params) that need roughly 6–12 GB at native 512–768 px and must be tiled to reach 2K. The commercial-clean shortlist is: Marigold-IID v1-1 (OpenRAIL++, already tried, "flat"), Marigold V2 albedo (Apache-2.0, Sept 2026, Qwen-Image-Edit-2509 backbone, 17 GB at 1024² so it exceeds the GPU unless quantised/offloaded), StableDelight (Apache-2.0, specular-only), IntrinsicAnything (weights Apache-2.0 on HF, code under a "Project Registration License" that permits commercial use only after registration), StableMaterials/MatFuse (OpenRAIL / MIT, generators not estimators). RGB↔X, Intrinsic (Careaga), DiffusionRenderer-SVD, UniRelight, albedoLBM, Chord, InvSR, SUPIR and MAT are all non-commercial or research-only and are excluded.

### Cited Findings

Per-candidate fact sheets (delighting / albedo / PBR estimation):

**IntrinsicAnything (ZJU, 2024)**
- Single-image → albedo generator and specular-shading generator ("weights/albedo", "weights/specular"); multiview inverse rendering listed as "Coming Soon"; HF demo 2024-05-22, single-view code 2024-05-31; default `--ddim 100`, batch 4; optional high-res mode `--ddim 200` using the low-res output as guidance with a 2×2 split and 1 overlap; guidance scale "2 to 5 generally yields good results"; Python 3.10 conda, rembg masks; no nvdiffrast/xformers mentioned; VRAM and base model not stated — [GitHub README](https://github.com/zju3dv/IntrinsicAnything)
- Code licence: "Project Registration License (PRL) v1.0": research/education/personal use free without registration; "Use by a company or other entity in any product, service, or project is allowed free of charge, but only if the use is registered before it begins … regardless of whether the project is commercial or non-commercial"; redistributors "must independently comply with the registration requirements" — [LICENSE on master](https://github.com/zju3dv/IntrinsicAnything/blob/master/LICENSE)
- Weights: HF repo `LittleFrog/IntrinsicAnything` tagged `apache-2.0`, last modified 2025-07-08, README empty — [HF API query, this session]; [HF card](https://huggingface.co/LittleFrog/IntrinsicAnything)

**RGB↔X (Adobe / zheng95z, SIGGRAPH 2024)**
- RGB→X estimates "per-pixel intrinsic channels (albedo, roughness, metallicity)" and lighting; X→RGB synthesises from intrinsic channels; built on Diffusers; "we recommend using a GPU with a minimum of 12GB of memory" — [GitHub README](https://github.com/zheng95z/rgbx)
- Licence: "ADOBE RESEARCH LICENSE" — grant is "for noncommercial research purposes only"; the definition excludes "commercial licensing or distribution, development of commercial products"; derivatives must also be limited to non-commercial research — [LICENSE](https://raw.githubusercontent.com/zheng95z/rgbx/main/LICENSE)
- HF weights `zheng95z/rgb-to-x` and `zheng95z/x-to-rgb` carry no licence tag (None), last modified 2024-10-08 — [HF API query, this session]
- Built on Stable Diffusion v2.1 (per a 2026 comparison paper) — [albedoLBM paper](https://arxiv.org/html/2609.09884)
- ComfyUI wrappers: toyxyz/ComfyUI_rgbx_Wrapper (outputs albedo, normal, roughness, metallic, irradiance; last updated 2025-04-03) and leob03/ComfyUI-rgbx ("GPU with at least 12GB VRAM") — [runcomfy listing](https://www.runcomfy.com/comfyui-nodes/ComfyUI_rgbx_Wrapper); [leob03 repo](https://github.com/leob03/ComfyUI-rgbx)

**NVIDIA DiffusionRenderer, academic SVD version (June 2025)**
- "The source code and model are made available under the Nvidia Source Code License"; base is Stable Video Diffusion; inverse passes listed: basecolor, normal, depth, diffuse_albedo; tested on A100 80 GB; on an RTX 4090 with fp16 and `decode_chunk_size: 8` it still needs "over 22 GB of GPU memory"; examples 512×512, 24 frames, 20 steps; torch 2.1–2.4; code and weights released 2025-06-11 — [GitHub README](https://github.com/nv-tlabs/diffusion-renderer)
- HF card `nexuslrf/diffusion_renderer-inverse-svd`: licence "other"/"Nvidia Source Code License", "This model is accessible for non-commercial use", 1.1 B params, default 512×512 — [HF card](https://huggingface.co/nexuslrf/diffusion_renderer-inverse-svd)

**NVIDIA Cosmos-DiffusionRenderer (June 2025)**
- Code Apache-2.0, models under the "NVIDIA Open Model License" (allowed by policy); 7B inverse/forward models, ~56 GB download, ≥70 GB disk; inverse passes basecolor, normal, depth, roughness, metallic; minimum 16 GB GPU, ≥48 GB recommended, image inference ~16 GB, video peak ~27 GB, offload flags available; dependencies include `transformer-engine[pytorch]==1.12.0` and **nvdiffrast installed from GitHub**; tested only on Ubuntu 20.04 (A100/A6000); released 2025-06-12 — [GitHub README](https://github.com/nv-tlabs/cosmos1-diffusion-renderer)
- HF `nvidia/Diffusion_Renderer_Inverse_Cosmos_7B` licence tag `nvidia-open-model-license`, last modified 2025-08-06 — [HF API query, this session]

**NVIDIA UniRelight (April 2026)**
- "distributed under the Nvidia Source Code License", "ready for non-commercial use"; Cosmos-Predict1 7B; 480×848; relighting + albedo estimation; released 2026-04-06 — [HF card](https://huggingface.co/nvidia/UniRelight)

**Intrinsic Image Diffusion (Kocsis et al., CVPR 2024) — the "IID-Diffusion" baseline**
- Stable Diffusion 2 depth variant (`512-depth-ema.ckpt`); outputs albedo, roughness, metallic (plus depth/normals stage and lighting stage); "Running the model requires at least 10GB of GPU memory"; trained on InteriorVerse (250 epochs, 4×A100, ~7 days); `stable-diffusion-sdkit==2.1.5`, optional xformers; tested only on Ubuntu 22.04/20.04 — [GitHub README](https://github.com/Peter-Kocsis/IntrinsicImageDiffusion)
- The paper describes it as a generative model that "samples multiple possible material explanations represented as albedo, roughness, and metallic maps" — [arXiv 2312.12274](https://arxiv.org/abs/2312.12274v1)

**Intrinsic (Careaga & Aksoy, TOG 2023/2024, "Colorful Diffuse IID in the Wild")**
- "This implementation is provided for academic use only"; methodology "under IP protection", licensing via SFU Technology Licensing Office; outputs albedo (`hr_alb`), diffuse shading, chromatic shading, residual (specular/light sources); high-resolution pipeline — [GitHub README](https://github.com/compphoto/Intrinsic)

**Marigold-IID v1-1 (ETH prs-eth, Oct–Dec 2024; journal paper May 2025)**
- Licence OpenRAIL++ (inherited from SD2); appearance variant outputs albedo (sRGB 0–1), roughness and metallicity (linear 0–1), trained on InteriorVerse; effective resolution ~768 px ("resize the longer side to 768 px"); DDIM 1–50 steps; diffusers `MarigoldIntrinsicsPipeline`; no v1-2 listed; lighting variant `marigold-iid-lighting-v1-1` (albedo, diffuse shading, non-diffuse residual) — [HF card](https://huggingface.co/prs-eth/marigold-iid-appearance-v1-1)
- Journal paper (arXiv 2505.09358, 2025-05-14): appearance trained on InteriorVerse 45K samples at 480×640; lighting on HyperSim 24K; evaluation with 4 denoising steps, no ensembling, "one step is qualitatively sufficient"; InteriorVerse albedo PSNR/SSIM/LPIPS: IID-Diffusion 18.10/0.863/0.198, RGB↔X 13.16/0.774/0.289, Marigold 19.50/0.846/0.190; material: IID-Diffusion 16.09/0.691/0.356, RGB↔X 10.13/0.547/0.636, Marigold 17.63/0.803/0.286; HyperSim albedo: IID-in-the-wild (Careaga) 19.28/0.819/0.260, RGB↔X 17.43/0.795/0.200, Marigold 18.21/0.771/0.218; the paper claims Marigold's predictions "contain less baked-in shading and are more consistent with the ground truth"; no high-res or LCM changes for IID (only depth) — [arXiv HTML](https://arxiv.org/html/2505.09358)
- HF tags: `marigold-iid-appearance-v1-1` openrail++ (created 2024-10-21), `marigold-iid-lighting-v1-1` openrail++ (created 2024-12-16), both last modified 2025-05-20 — [HF API query, this session]
- Independent user characterisation (StableGen Blender add-on v0.3.0): albedo sources "Marigold IID (flat)", "StableDelight (specular-free, configurable strength)", "Marigold IID-Lighting (vibrant)"; StableDelight download ~3.3 GB — [StableGen releases](https://github.com/sakalond/stablegen/releases)

**Marigold V2 (Huawei Bayer Lab, 2026-09-08) — the "changes since" for Marigold**
- "Code and models are released under the Apache License, Version 2.0"; frozen Qwen-Image-Edit-2509 backbone (DiT quantised to 4-bit on first load; 7B text encoder not loaded, precomputed prompt embeddings); outputs depth, camera-space normals, and albedo (linear RGB 0–1); single-step; inference needs ~17 GB at 1024² and ~29 GB at 2048²; native resolution rounded to multiples of 16; Linux, Python 3.10, CUDA 12.8 wheels; SIGGRAPH Asia 2026 / TOG 45(6); Marigold-IID not mentioned — [GitHub README](https://github.com/huawei-bayerlab/marigold-v2)
- Qwen-Image-Edit-2509 is tagged `apache-2.0` on HF (created 2025-09-22) — [HF API query, this session]
- ComfyUI supports it natively: shared int8 base `qwen_image_edit_2509_int8_convrot.safetensors` plus per-task LoRA + VAE + conditioning files for depth, normals, albedo; post-process node converts albedo to sRGB — [ComfyUI docs](https://docs.comfy.org/tutorials/utility/marigold-v2)
- A user reported the ComfyUI albedo output differs from the official demo — [issue #9](https://github.com/huawei-bayerlab/marigold-v2/issues/9); HF weights `huawei-bayerlab/marigold-v2-0`, `Comfy-Org/marigold-v2-0`, `fal/Marigold-v2-Qwen-Image-Edit-2509-NF4` exist — [HF API search, this session]

**StableDelight (Stable-X, Sept 2024)**
- "specular reflection removal from textured surfaces"; Apache-2.0 badge; one-step diffusion prediction building on StableNormal; weights `Stable-X/yoso-delight-v0-4-base`; trained on Hypersim, Lumos and TSHRNet specular-highlight datasets; for 3D it delights source photos and rebuilds the texture with mvs-texturing; Gradio comment mentions Linux and Windows — [GitHub README](https://github.com/Stable-X/StableDelight)
- HF card: `apache-2.0`, removes specular reflections (no mention of diffuse shading/shadows/AO); torch.hub loader `StableDelight_turbo`; weights created 2024-08-24, last modified 2024-09-26 — [HF card](https://huggingface.co/Stable-X/yoso-delight-v0-4-base)
- ComfyUI: kijai/ComfyUI-StableXWrapper — [runcomfy listing](https://www.runcomfy.com/comfyui-nodes/ComfyUI-StableXWrapper)

**Material Anything (3DTopia, Nov 2024 paper; models June 2025)**
- Code MIT; mesh → albedo, roughness, metallic, bump; per-view material estimator + UV-space material refiner; Blender 3.2.2 (Linux instructions); PyTorch3D required; weights licence not stated — [GitHub README](https://github.com/3DTopia/MaterialAnything)
- requirements.txt: diffusers==0.28.2, pytorch-lightning==1.9.1, triton, bpy, objaverse, iopath, no nvdiffrast/xformers/flash-attn/kaolin — [requirements.txt](https://raw.githubusercontent.com/3DTopia/MaterialAnything/main/requirements.txt)

**albedoLBM (CVC, CIC 2026, Sept 2026) — current best-documented single-step albedo model, but NC**
- Code and weights CC BY-NC 4.0 (plus dataset and SDXL terms); SDXL-sized UNets (~2.5 B) with frozen SDXL VAE; single bridge step per model; ~10.5 GB peak bf16 at 768×576 (5.8 GB albedo-only); ~1.1 s per 768×576 on RTX 3090; runs at native size, quality degrades beyond ~2K (trained on 256² crops); trained on InteriorVerse + Hypersim; weights `davidserra9/albedo-lbm` (2×5 GB) — [GitHub README](https://github.com/CVC-Color/albedoLBM)
- Its comparison table (InteriorVerse PSNR/LPIPS, Hypersim PSNR/LPIPS, IIW WHDR 10%/20%): Careaga 17.4/0.20, 13.5/0.34, 24.8/19.2; Kocsis 12.2/0.30, 12.1/0.41, 26.1/20.7; RGB↔X 16.6/0.17, 17.4/0.16, 23.6/21.1; Marigold 19.5/0.19, 18.2/0.22, 16.7/14.8; PRISM 19.9/0.14, 19.3/0.18, 17.2/15.9; DNF-Intrinsic 21.9/0.12, –; Marigold-X 19.8/0.16, 19.0/0.20, 15.2/14.0; PRISM-X 20.7/0.12, 19.9/0.17, 12.9/11.9; albedoLBM 18.3/0.31, 16.7/0.26, 17.9/15.1; notes RGB↔X "featureless estimates in low-light regions" and IntrinsicDiffusion shows an orange/yellow colour shift — [arXiv HTML](https://arxiv.org/html/2609.09884)

**Other 2025–2026 intrinsic papers (no verified open weights)**
- FlowIID (ICASSP 2026): single-step latent flow matching for albedo/shading — [arXiv 2601.12329](https://arxiv.org/pdf/2601.12329)
- ReasonX (CVPR 2026): MLLM-judged GRPO fine-tuning, "9-25% WHDR reduction on IIW albedo", model-agnostic — [arXiv 2512.04222](https://arxiv.org/abs/2512.04222)
- DNF-Intrinsic (ICCV 2025): deterministic flow-matching inverse rendering; arXiv page gives no code link — [arXiv 2507.03924](https://arxiv.org/abs/2507.03924)
- IDArb: multi-view intrinsic decomposition (albedo, roughness, metallic, normal) — [arXiv 2412.12083](https://arxiv.org/pdf/2412.12083)

**Chord (Ubisoft La Forge, SIGGRAPH Asia 2025)**
- Two-stage generate-and-estimate; chained single-step image-conditional diffusion predicts SVBRDF channels; basecolor, normal, roughness, metalness (height via normal integration); tileable generation; claims robustness on in-the-wild photos — [arXiv 2509.09952](https://arxiv.org/abs/2509.09952); [project page](https://ubisoft-laforge.github.io/world/chord/)
- Repo licence "Ubisoft Machine Learning License (Research-Only - Copyleft)"; Python 3.12 via uv, torch cu128 index, Windows activation instructions, HF login required for gated weights — [GitHub README](https://github.com/ubisoft/ubisoft-laforge-chord)

**texture2albedo-v2 (paom, June 2026)**
- LoRA tagged Apache-2.0 but base is `black-forest-labs/FLUX.2-klein-9B` (non-commercial family); prompt "Unlit flat-shaded albedo map. Remove all shadows, reflections, highlights, and specularity…"; inference at 1024², 4 steps, guidance 1.0; created 2026-06-20 — [HF card](https://huggingface.co/paom/texture2albedo-v2); [HF API query, this session]
- A second delight LoRA, `linoyts/Flux2-Klein-Delight-LoRA`, is also on the 9B base and licence "other" (FLUX.2 licence) — [HF card](https://huggingface.co/linoyts/Flux2-Klein-Delight-LoRA)

**Hunyuan3D-Delight / Hunyuan3D-2.1**
- `tencent/Hunyuan3D-2.1` licence tag `tencent-hunyuan-community`; `tencent/Hunyuan3D-Delight-v2-0` not resolvable via the public API (gated or moved) — [HF API query, this session]

**Named candidates that do not exist as released models**
- "DeLight": the only repos found are Unity's De-Lighting Tool (experimental, Unity 5.6/2017.1, works from AO/normal/bent-normal maps, MIT per mirror) and Agisoft De-Lighter (free closed app, 2019, "requires user input in a form of rough brush strokes marking lit and shadowed areas") — [Unity DeLightingTool readme](https://github.com/tfart/DeLightingTool/blob/master/Readme.md); [80.lv on De-Lighter](https://80.lv/articles/agisoft-releases-free-de-lighter)
- "PBR-Boost": closest is "Boosting 3D Object Generation through PBR Materials" (SIGGRAPH Asia 2024): SD fine-tuned on synthetic data for albedo and bump UV maps; roughness/metalness via a "semi-automatic process"; no code/weights link on arXiv — [arXiv 2411.16080](https://arxiv.org/abs/2411.16080)
- "Diffuse2Albedo": no repository found; nearest is texture2albedo-v2 above — [search, this session]

### Inferences
- Nothing clean fits 4 GB at 2K natively. Marigold-IID and StableDelight (SD2-class UNet + VAE, ~1.3 B params) are the only clean estimators that plausibly run on 16 GB at all; 2K must be done by tiling 512–768 px windows with overlap, which is exactly what IntrinsicAnything's 2×2 split mode and Marigold's 768-px guidance imply. A fp16 SD2 UNet plus VAE is ~2–3 GB of weights, so a 768-px tile pass in ~4–6 GB is realistic but unverified for these specific pipelines.
- Marigold V2 albedo is the only post-2025 commercial-clean intrinsic model with a leap in backbone, but at 17 GB for 1024² it will not run on the 16 GB laptop as shipped; the ComfyUI int8 base and the fal NF4 repack suggest quantised runs may fit, but no one has documented VRAM for those on 16 GB. Linux-only in the README; ComfyUI native support implies Windows works via ComfyUI's Qwen-Image-Edit path.
- The IntrinsicAnything PRL registration clause is a commercial-use condition, not a prohibition, but it is an unusual licence that should be reviewed before adoption; the Apache-2.0 tag on the weights conflicts with the code licence.
- Cosmos-DiffusionRenderer has an allowed weights licence but is excluded by the nvdiffrast dependency, 56 GB download, and 16–48 GB VRAM; it is also video-oriented at 1280×704.

### Gaps
- No source gives measured VRAM for Marigold-IID, StableDelight, IntrinsicAnything or Material Anything at any resolution; "≤ 4 GB" cannot be confirmed for any candidate.
- IntrinsicAnything's base model and whether its weights are SD-2.x derived (hence OpenRAIL-encumbered) is not stated.
- Material Anything weights licence: HF repo not resolvable via public API.
- Intrinsic Image Diffusion (Kocsis) LICENSE file content not retrievable (page shows a LICENSE link only).
- "ColorPeel" and "MaterialFusion": no PBR-estimation repo found under these names in any search; both may be misremembered names (left unverified).
- Training-data licences for InteriorVerse, Hypersim, Lumos and the Deschaintre 2018 SVBRDF dataset were not checked.

## Key question 2: Which work on a UV texture atlas (seams, islands, padding) rather than only on a photo, or can be applied on rendered views and back-projected?

### Takeaway
Every intrinsic model surveyed is trained on photographs or rendered scene views; none documents UV-atlas input. The only models that natively touch UV space are mesh-texturing pipelines (Material Anything's UV-space refiner, StableDelight's photo-then-retexture workflow), and the published UV-inpainting work (Maggiordomo 2023, KU Leuven 2024) explicitly states that atlas discontinuities break image models unless you reparametrise per island or per patch.

### Cited Findings
- Material Anything: "The material estimator works per view, and the material refiner works in UV space" — [GitHub README](https://github.com/3DTopia/MaterialAnything)
- StableDelight 3D workflow processes the source images (with `.cam` files) and rebuilds the texture with mvs-texturing's `texrecon`; "The page doesn't say it accepts UV texture maps directly" — [GitHub README](https://github.com/Stable-X/StableDelight)
- Maggiordomo, Cignoni, Tarini (CGF 2023): "The texture image comes as an atlas of texture islands separated by gaps of unused space. Being unaware of the atlas discontinuities and texture distortions, any inpainting method applied to the global texture would produce visible seam artefacts"; their network is trained on "locally reparametrized patches" that avoid "texture seams, unused texture areas, background, depth jumps"; they claim a "reference usable implementation" but no repository surfaced — [EG DigLib](https://diglib.eg.org/handle/10.1111/cgf14735); [CNR open portal PDF](https://openportal.isti.cnr.it/data/2023/479072/2023_479072.published.pdf)
- KU Leuven 2024 (semantic UV mapping): inpaints each UV island separately then repacks the layout — [arXiv 2407.09248](https://arxiv.org/pdf/2407.09248)
- Blender Dynamic Paint adds a one-pixel border around islands averaged across the seam; a 2022 Blender commit extends island borders with connected mesh geometry using a mask; padding guidance "4px for 512, 8px for 1024, 16px for 2048" — [Blender commit mirror](https://miikahweb.com/fi/blender/git-logs/commit/99ca90e80865a99a609cad53f7de435b160549f8); [WANNA seam FAQ](https://wanna.helpjuice.com/faq-new/how-to-fix-seams-on-3d-models)
- MVPaint repairs seams created by its own texture upsampling with a "spatial-aware seam-smoothing algorithm" after super-resolution — [arXiv 2411.02336](https://arxiv.org/pdf/2411.02336)
- ComfyUI-TextureAlchemy offers "Triplanar Projection … Remove UV seams with XYZ projection blending", a "Seamless Tiling Maker" (mirror/blend_edges/offset), a high-pass "Texture Equalizer" that "removes uneven lighting and shadows", and an AO approximator from height — [GitHub README](https://github.com/amtarr/ComfyUI-TextureAlchemy)
- Marigold-IID, RGB↔X, Kocsis IID, albedoLBM, Marigold V2 are all trained on InteriorVerse/Hypersim rendered indoor views — [Marigold journal](https://arxiv.org/html/2505.09358); [albedoLBM README](https://github.com/CVC-Color/albedoLBM); [Kocsis README](https://github.com/Peter-Kocsis/IntrinsicImageDiffusion)

### Inferences
- The practical route for the existing pipeline is "render views → run the 2D model → back-project with the pure-torch UV rasterizer", which is what Material Anything and StableDelight's own pipelines do; this keeps the UVs untouched and sidesteps atlas discontinuities, at the cost of view-coverage and blending logic that already exists in the texturing step.
- Running an intrinsic model directly on the atlas is only defensible per-island with generous padding and the background masked, and then only for lighting-invariant corrections (local shading removal), not for anything that reasons about global scene light.
- No published model is trained on atlases, so quality claims from benchmarks do not transfer to atlas input.

### Gaps
- No code located for the Maggiordomo 2023 UV-aware inpainting network (authors claim an implementation; CNR lab pages do not link one).
- No quantitative evidence on how any intrinsic model behaves on atlas input.

## Key question 3: Which super-resolution models beat Real-ESRGAN on painted/stylised and photo-real textures, and are their licences clean?

### Takeaway
Clean upgrades exist on both axes: deterministic transformers (HAT Apache-2.0, SwinIR Apache-2.0) and GAN (AuraSR-v2 Apache-2.0, 0.6 B) for faithful detail, and SD2-based diffusion SR (SeeSR, OSEDiff, DiffBIR, all Apache-2.0) for hallucinated photo-real detail; InvSR (S-Lab NC) and SUPIR (non-commercial declaration) are excluded. Evidence that any of them beats Real-ESRGAN specifically on textures is vendor/anecdotal; OpenModelDB's "Game Textures" tag is the only texture-specific model pool found.

### Cited Findings
- Real-ESRGAN BSD-3-Clause, HAT MIT (third-party listing; conflicts with HAT's own page), SwinIR Apache-2.0 per a third-party credits file — [AEmotionStudio listing](https://huggingface.co/AEmotionStudio/ai-upscale-models/blob/main/README.md)
- HAT GitHub shows Apache-2.0; HAT 20.8 M params, HAT-S 9.6 M; tile mode for low-VRAM inference (2022-09-25); Real_HAT_GAN_SRx4 (2022-11-24) and a "sharper" perceptual variant (2023-08-01); BasicSR 1.3.4.9; torch ≥1.7 — [GitHub README](https://github.com/XPixelGroup/HAT)
- Replicate's comparison: "SwinIR has much better textures, particularly in the facial hair and skin detail"; "SwinIR takes longer to run, 4s vs Real-ESRGAN's 1.4s"; SwinIR "doesn't handle eyes well" — [Replicate guide](https://replicate.ai/guides/upscaling-images/swinir)
- HST paper found "Real-ESRGAN generates unnatural textures although its degradation process includes JPEG compression" — [arXiv 2208.09885](https://arxiv.org/pdf/2208.09885)
- AuraSR-v2: Apache-2.0, 0.6 B params, GigaGAN-derived, 4×, `upscale_4x_overlapped` — [HF card](https://huggingface.co/fal/AuraSR-v2); v1 tagged "cc" — [HF API query, this session]; fal: v1 "tended to add too much detail", v2 adds ESRGAN-style degradation training, "able to preserve more details of in the wild images than RealESRGAN without artifacts" (vendor claim); "sensitive to compression artifacts … ideal for upscaling AI-generated or high-quality uncompressed images" — [fal blog](https://blog.fal.ai/aurasr-v2); [Replicate wrapper](https://replicate.com/zsxkib/aura-sr)
- SeeSR: "This project and related weights are released under the Apache 2.0 license"; SD-2-base; tiled VAE from multidiffusion-upscaler; repo 2023-11-28, weights 2023-12-25; OSEDiff is "over 30 times faster" — [GitHub README](https://github.com/cswry/SeeSR)
- OSEDiff: Apache-2.0; SD 2.1 base; ~0.1046 s per 512-px iteration on A100; needs RAM and DAPE checkpoints; weights July 2024 — [GitHub README](https://github.com/cswry/OSEDiff)
- DiffBIR: Apache-2.0; SD 2.1 base; tiled sampling for stage-1, VAE and diffusion (example 2396×1596); v2.1 2024-11-27; recommends PyTorch 2.2.2 "for built-in memory-efficient attention", xformers only as a fallback — [GitHub README](https://github.com/XPixelGroup/DiffBIR)
- InvSR: "licensed under NTU S-Lab License 1.0"; SD-Turbo base; `--chopping_size 256` for 1k–4k inputs; pins xformers 0.0.27.post2 and torch 2.4.0; CVPR 2025 — [GitHub README](https://github.com/zsyOAOA/InvSR); HF README copy says "non-commercial purposes" — [HF space README](https://huggingface.co/spaces/OAOA/InvSR/blame/d743d6c55619213a0b1288273ab6734a73aa6db3/README.md)
- SUPIR: "Non-Commercial Use Only Declaration … strictly for non-commercial purposes", commercial use needs written permission from SupPixel; SDXL + LLaVA 13B; low-VRAM mode "12G for Diffusion, 16G for LLaVA" — [GitHub README](https://github.com/Fanghua-Yu/SUPIR); licence conflict discussed in [issue #51](https://github.com/Fanghua-Yu/SUPIR/issues/51)
- spandrel (MIT loader, arch code keeps original licences): loads ESRGAN, Real-ESRGAN Compact, SwinIR, Swin2SR, HAT, OmniSR, DAT, SPAN, ATD, DRCT, PLKSR/RealPLKSR, AuraSR, LaMa, MAT (extra arches, restrictive) and more from .pth/.safetensors — [GitHub README](https://github.com/chaiNNer-org/spandrel)
- OpenModelDB: 671 community models; Subject filters include "Game Textures", "Pixel Art", "CGI"; Purpose filters include "Texture Generation" and "DDS"; "Models carry their own licenses" — [OpenModelDB](https://openmodeldb.info/)

### Inferences
- For the face projection (photo-real, already Real-ESRGAN 4×) the cheapest clean upgrade is a deterministic transformer (Real_HAT_GAN_SRx4 or SwinIR real-world) loaded through spandrel: pure torch, tile mode, no xformers, Windows-trivial. Diffusion SR (OSEDiff/SeeSR/DiffBIR) adds hallucinated pores and fabric weave but is SD2-class and needs 6–10 GB and tiling at 2K; OSEDiff's one-step design makes it the most practical of the three.
- For painted/stylised atlases, GAN/transformer SR models trained on anime/cartoon/game-texture data (OpenModelDB tags) are more appropriate than diffusion SR, which tends to photo-realise strokes; no source quantifies this for stylised textures.
- AuraSR-v2 is tuned for AI-generated, uncompressed inputs, which matches the TRELLIS bake better than JPEG photos.

### Gaps
- No independent side-by-side of AuraSR/HAT/SwinIR/Real-ESRGAN on game textures was found; only vendor and Replicate anecdotes.
- OpenModelDB's filtered "Game Textures" list could not be retrieved (page truncated), so no specific model names or their licences are recorded.
- HAT licence shows as Apache-2.0 on its own page but MIT in a third-party credits file; treat Apache-2.0 as primary.

## Key question 4: State of the art for removing baked lighting from a texture with no lighting information; is a delighting pass still worth it when the generator already approximates albedo?

### Takeaway
The best-measured single-image albedo models in 2026 are non-commercial (albedoLBM, DNF-Intrinsic, PRISM-X/ReasonX-tuned); among clean options Marigold-IID v1-1 still scores best on InteriorVerse albedo (PSNR 19.5) with Marigold V2 as its unbenchmarked (here) successor. Direct evidence that a second delighting pass improves a generator's albedo is absent; the 3D-generation literature instead reports that distilled albedo "suffers from baked-in shading" and that the fix is a dedicated albedo model applied to views, which argues for a targeted specular/shadow pass only where the bake shows baked highlights.

### Cited Findings
- Marigold-IID claims predictions "contain less baked-in shading and are more consistent with the ground truth" and evaluates with 4 steps, no ensemble — [arXiv 2505.09358](https://arxiv.org/html/2505.09358)
- albedoLBM comparison: on InteriorVerse PSNR Marigold 19.5, PRISM-X 20.7, DNF-Intrinsic 21.9; on IIW WHDR Marigold 16.7, PRISM-X 12.9; RGB↔X gives "featureless estimates in low-light regions" — [arXiv 2609.09884](https://arxiv.org/html/2609.09884)
- ReasonX: model-agnostic RL fine-tuning on unlabeled in-the-wild images, "9-25% WHDR reduction on IIW albedo" — [arXiv 2512.04222](https://arxiv.org/abs/2512.04222)
- DreamMat (3D PBR generation) notes "directly distilling the PBR material parameters from 2D diffusion models still suffers from incorrect material decomposition, such as baked-in shading effects in albedo" — [arXiv 2405.17176](https://arxiv.org/html/2405.17176v1)
- "Boosting 3D Object Generation through PBR Materials" fine-tunes Stable Diffusion on synthetic data to produce albedo and bump maps for generated objects (no code) — [arXiv 2411.16080](https://arxiv.org/abs/2411.16080)
- StableDelight is specular-only (trained on specular-highlight datasets), not diffuse-shading or AO removal — [HF card](https://huggingface.co/Stable-X/yoso-delight-v0-4-base)
- QFX PBRGenerator uses Marigold appearance/lighting estimators to "remove baked-in shadows and highlights" for albedo — [comfy.icu](https://comfy.icu/extension/qornflex__ComfyUI-QFX-PBRGenerator)
- Agisoft De-Lighter needs brush strokes marking lit/shadowed areas; Unity's De-Lighting Tool needs AO, normal and bent-normal maps — [80.lv](https://80.lv/articles/agisoft-releases-free-de-lighter); [Unity readme](https://github.com/tfart/DeLightingTool/blob/master/Readme.md)
- Independent user label for Marigold-IID output: "flat"; IID-Lighting: "vibrant" — [StableGen releases](https://github.com/sakalond/stablegen/releases)
- No 2025 neural model for AO or shadow removal in textures surfaced; the only neural delighting hit was Deep Portrait Delighting (ECCV 2022, portraits) — [arXiv 2203.12088](https://arxiv.org/pdf/2203.12088)

### Inferences
- The owner's "too flat" result matches the StableGen label and Marigold-IID's design (appearance model trained on InteriorVerse at 480×640 with lighting-independent targets); the IID-Lighting variant ("vibrant") or a shading-only use of it (divide out the predicted diffuse shading from the current bake rather than replacing the albedo) is a cheaper experiment than a new model.
- Since the bake already approximates albedo, a full intrinsic re-estimation is more likely to lose detail (768-px effective resolution, flat colours) than to help; a targeted pass is defensible only for (a) specular highlights baked into faces/metal (StableDelight, Apache) and (b) obvious AO in crevices, for which the Blender AO bake already exists and can be used to divide out darkening without any ML model.
- The clean frontier (Marigold V2 albedo, Apache) is the only model worth re-testing for "is a delight pass worth it", and only if it fits in 16 GB after quantisation.

### Gaps
- No paper or user report measures "generator albedo + delighting pass" against "generator albedo alone" for 3D-generation outputs.
- No open, clean model for AO/shadow removal in textures was found; the classical tools (De-Lighter, Unity tool) are brush- or map-driven.
- Marigold V2 albedo has no published comparison against Marigold-IID v1-1 on intrinsic benchmarks in the sources retrieved.

## Key question 5: For props, is there a clean "photo of a material → tileable PBR set" model?

### Takeaway
Not as a single estimator. The clean open options are generators conditioned on an image (StableMaterials, OpenRAIL, 512², tileable via feature rolling; MatFuse, MIT, ≥12 GB, no tileability stated) and a per-material LoRA pipeline (Material Palette, MIT, SD1.5 RAIL-M); the true photo-to-tileable-SVBRDF estimators (Chord, MatE, ControlMat/MatGen, Adobe Sampler) are research-only, unreleased, or proprietary, and PBRFusion4 (Apache) only produces normal and depth.

### Cited Findings
- StableMaterials: OpenRAIL; basecolor, normal, height, roughness, metallic; `tileable=True` via "Feature Rolling" in every conv and attention layer; base 512×512, refiner "coming later"; image prompts supported; 0.9 B params; trained on MatSynth + Deschaintre (6,198 materials) + 4,000 SDXL-generated texture-text pairs; paper 2024-06-13 — [HF card](https://huggingface.co/gvecchio/StableMaterials); HF tag `openrail`, last modified 2025-04-05 — [HF API query, this session]; ComfyUI wrapper P5ina/comfyui-stable-materials with LCM mode "~2 seconds (4 steps)" — [comfy.icu](https://comfy.icu/extension/P5ina__comfyui-stable-materials)
- MatFuse: code MIT (HF tag mit, last modified 2026-02-20); outputs diffuse, normal, roughness, specular; conditioning via CLIP image, text, palette (≤5 RGB), sketch; custom multi-encoder VQ-VAE on the CompVis LDM codebase; "at least 12GB of GPU VRAM"; Windows training needs `gloo` backend; training data (Deschaintre 2018 + PolyHaven) not released, MatSynth recommended — [GitHub README](https://github.com/giuvecchio/matfuse-sd); MatFuse Space says tileable maps — [HF Space README](https://huggingface.co/spaces/gvecchio/MatFuse/blob/main/README.md)
- Material Palette: MIT; photo + region masks → albedo, normals, roughness per material; LoRA per region on SD v1-5 (CreativeML Open RAIL-M), then a decomposition network trained on AmbientCG + TexSD; torch 1.13, diffusers 0.19.3; no tileability mentioned — [GitHub README](https://github.com/astra-vision/MaterialPalette)
- MatSynth: "more than 4,000 CC0, ultra-high-resolution PBR materials" (dataset, CVPR 2024) — [Adobe Research](https://research.adobe.com/publication/matsynth-a-modern-pbr-materials-dataset/)
- MatGen is the latent diffusion backbone inside ControlMat (Adobe, 2023; 9 SVBRDF channels, photo ControlNet, "noise rolling" for tileability); no code listed — [arXiv 2309.01700](https://ar5iv.labs.arxiv.org/html/2309.01700); [PwC author page](https://astro.paperswithcode.com/author/giuseppe-vecchio)
- MatE (CVPR 2026, Dec 2025 preprint): single photo under unknown illumination/perspective → tileable albedo, normal, roughness, height via depth prior + dual-branch diffusion; no code mentioned — [arXiv 2512.18312](https://arxiv.org/abs/2512.18312v1)
- Chord: research-only Ubisoft licence (see KQ1) — [GitHub README](https://github.com/ubisoft/ubisoft-laforge-chord)
- PBRFusion4: "Fully open under Apache 2.0"; image-to-image for normal and depth only; "at least 8GB of VRAM"; ComfyUI node Night1099/COMFYUI-PBRFusion4; created 2026-06-02 — [HF card](https://huggingface.co/9I11/PBRFusion4)
- MatForger (gvecchio): HF card returns 401 (gated); a Replicate deployment exposes a `tileable` flag defaulting to true — [Replicate](https://replicate.com/tonyhopkins994/matforger-test/api)
- Adobe Substance 3D Sampler 6 (June 2026) is the proprietary reference for "Image to Material" with shadow removal — [CG Channel](https://www.cgchannel.com/2026/06/adobe-releases-substance-3d-sampler-6/); fal PATINA is a hosted commercial API for PBR from a single image — [fal](https://fal.ai/models/fal-ai/patina)
- Non-ML classics: Materialize (GPL-3.0, Unity project, photo → material maps) — [GitHub](https://github.com/BoundingBoxSoftware/Materialize); pbr_batch derives albedo/height/normal/roughness/AO/metallic/ORM from seamless PNGs with wrap-padding — [GitHub](https://github.com/alexmmx/pbr_batch)

### Inferences
- For props the realistic clean stack is: StableMaterials image-prompted with tileable=True (512², upscale with a clean SR model) when a *style* match is enough, or MatFuse with CLIP image conditioning when roughness/specular control matters; neither reproduces a specific photo pixel-for-pixel.
- A faithful photo → tileable SVBRDF estimator that is commercial-clean does not exist in the open as of Oct 2026; the research direction (MatE, Chord) is clearly there, so this is worth re-checking in 2027.
- MatSynth (CC0) is the cleanest training set if the owner ever fine-tunes a small estimator on their own.

### Gaps
- StableMaterials VRAM and MatForger licence not stated anywhere retrievable.
- Whether MatFuse's released checkpoint supports tileable generation (the Space says yes, the README does not) is unresolved.
- AmbientCG and TexSD licence terms were not verified in this session.

## Key question 6 (objective sub-topic): normal-from-texture tools

### Takeaway
StableNormal/YOSO-normal (Apache-2.0, latest weights Jan 2025), Lotus normals (Apache-2.0), Marigold normals (v1-1 OpenRAIL++, v0-1 Apache) and DeepBump (GPL-3, ONNX, CPU-capable) are all clean; Lotus-2 is excluded by its FLUX.1-dev dependency and 40 GB requirement, NormalCrafter is video-only. All diffusion options predict camera-space normals from a *view*, not tangent-space normals from an atlas, so DeepBump is the only one that applies to the UV albedo directly.

### Cited Findings
- StableNormal: Apache-2.0 code; turbo variant "10 times faster"; released 2024-08-27; StableDelight sibling; no xformers — [GitHub README](https://github.com/Stable-X/StableNormal); HF `Stable-X/stable-normal-v0-1` apache-2.0 (2024-06), `Stable-X/yoso-normal-v1-8-1` apache-2.0 (2025-01-20) — [HF API query, this session]
- Lotus: Apache-2.0; generative and discriminative depth/normal checkpoints; tested on Ubuntu/CUDA 12.3/A800; inference code 2024-10-05, training code 2025-04-03 — [GitHub README](https://github.com/EnVision-Research/Lotus); HF `jingheya/lotus-normal-d-v1-1` / `-g-v1-1` apache-2.0 (2025-01-16) — [HF API query, this session]
- Lotus-2: Apache-2.0 code but "requires access to black-forest-labs/FLUX.1-dev" and "a GPU with at least 40GB memory"; released 2025-11-28 — [GitHub README](https://github.com/EnVision-Research/Lotus-2)
- Marigold normals: `prs-eth/marigold-normals-v1-1` openrail++ (created 2024-10-21), `marigold-normals-v0-1` apache-2.0 — [HF API query, this session]; Marigold V2 normals Apache-2.0, ~17 GB at 1024² — [GitHub README](https://github.com/huawei-bayerlab/marigold-v2)
- NormalCrafter: code MIT, HF weights apache-2.0 (2025-04-06); video input; ~20 GB at 1024×576, ~6 GB at 512×256; ICCV 2025 — [GitHub README](https://github.com/Binyr/NormalCrafter); [HF API query, this session]
- DeepBump: "This repo is under the GPL license" (GPL-3.0); colour→normal, normal→height, normal→curvature, plus an upscale tool; ONNX Runtime; `deepbump256.onnx` — [GitHub README](https://github.com/HugoTini/DeepBump); ComfyUI "Deep Bump (mtb)" node wraps it — [comfy.icu](https://comfy.icu/node/Deep-Bump-mtb)
- PBRFusion4 (Apache-2.0) produces normal + depth from an image, ≥8 GB — [HF card](https://huggingface.co/9I11/PBRFusion4)

### Inferences
- The Blender normal bake already gives geometric normals; the only thing an ML tool can add is *albedo-derived micro-detail* (fabric weave, pores), which is DeepBump's exact job and runs on the atlas in UV space with no GPU; GPL-3 is compatible with the project's GPL `blender_ops/` boundary if it runs as a separate Blender add-on process.
- View-space normal models (StableNormal, Lotus, Marigold) would need render → predict → back-project → convert to tangent space, i.e. the same machinery as the delighting route; they are only worth it if the mesh normals are poor, which a 1024³ voxel field makes unlikely.

### Gaps
- DeepBump model size, 256-px tiling behaviour at 2K and seamless handling are not documented on the page.
- No benchmark comparing StableNormal v1-8-1 vs Lotus vs Marigold V2 normals was retrieved.

## Key question 7 (objective sub-topic): seam healing, UV-space inpainting and tiling

### Takeaway
LaMa (Apache-2.0, big-lama weights Apache-2.0, generalises to ~2K, pure torch via spandrel) is the clean inpainting workhorse; MAT is CC BY-NC 4.0 and excluded; diffusion inpainting on allowed bases exists via ComfyUI for FLUX.2-klein-4B (Apache) and Z-Image-Turbo (Apache, ControlNet-inpaint). Seam-aware inpainting on an atlas has no released code; tileability for generated textures relies on circular-padding conv patches that only touch the VAE for DiT models.

### Cited Findings
- LaMa LICENSE: Apache License 2.0 (copyright line "Copyright [2021] Samsung Research") — [LICENSE](https://github.com/advimman/lama/blob/main/LICENSE); README: big-lama trained on Places2, "generalizes surprisingly well to much higher resolutions" than 256², up to ~2K; torch 1.8-era instructions — [GitHub README](https://github.com/advimman/lama); HF `smartywu/big-lama` apache-2.0 — [HF API query, this session]
- MAT LICENSE: "Creative Commons Attribution-NonCommercial 4.0 International"; README: "for research purposes only"; 512² models, inputs must be multiples of 512 — [LICENSE](https://github.com/fenglinglwb/MAT/blob/main/LICENSE); [GitHub README](https://github.com/fenglinglwb/MAT)
- spandrel loads LaMa (core) and MAT (extra arches, restrictive) — [GitHub README](https://github.com/chaiNNer-org/spandrel)
- FLUX.2-klein-4B: HF apache-2.0 (402K downloads, last modified 2026-02-24) — [HF API query, this session]; one-node wrapper with inpaint/outpaint using ComfyUI-Inpaint-CropAndStitch; "The 4B variant is Apache 2.0 … while the 9B variant uses a non-commercial license" — [sourcepulse](https://www.sourcepulse.org/projects/31925829)
- Z-Image-Turbo: HF apache-2.0 (last modified 2026-01-30) — [HF API query, this session]; inpainting via "Fun ControlNet 2.0/2.1" per a third-party summary; official ComfyUI template "2.2 Creator - Diffusion Guidance" teaches inpainting and controlnet with Z-Image-Turbo — [lilys summary](https://lilys.ai/ms/notes/comfyui-20260119/z-image-turbo-controlnet-inpaint-comfyui-ai-gen); [comfy.org template](https://comfy.org/templates/gsc_creator_2_2)
- Seam-aware inpainting literature: Maggiordomo 2023 (locally reparametrised patches, "reference usable implementation" claimed, no repo found); KU Leuven 2024 per-island inpainting then repack — [EG DigLib](https://diglib.eg.org/handle/10.1111/cgf14735); [arXiv 2407.09248](https://arxiv.org/pdf/2407.09248)
- Tiling nodes: Texturaizer "Seamless Tiling Patch" switches Conv2d padding to circular "within a specified range of steps"; spinagon ComfyUI-seamless-tiling (per-axis X/Y, "Make Circular VAE", "Offset Image" seam check; last updated 2024-05-23); ComfyUI_Seamless_Patten (SeamlessVae/SeamlessApply); tiled_ksampler (tileX/tileY, Circular VAEDecode) — [runcomfy Texturaizer](https://www.runcomfy.com/comfyui-nodes/ComfyUI-Texturaizer/texturaizer-seamless-tiling-patch); [runcomfy seamless-tiling](https://www.runcomfy.com/comfyui-nodes/ComfyUI-seamless-tiling)
- StableMaterials bakes tiling into the model via feature rolling; ControlMat used noise rolling + inpainting — [HF card](https://huggingface.co/gvecchio/StableMaterials); [arXiv 2309.01700](https://ar5iv.labs.arxiv.org/html/2309.01700)
- Classical: Blender island border extension and padding (16 px at 2048); MVPaint seam smoothing after SR; ComfyUI-TextureAlchemy triplanar seam removal and Seamless Tiling Maker — see KQ2 citations
- A US patent (US 8,269,765) covers expanding UV pieces to overlap seams — [Google Patents](https://patents.google.com/patent/US8269765)

### Inferences
- For seam healing on a kept UV layout, the lowest-risk path is deterministic: dilate/pad islands (already in the pure-torch bake), then LaMa-inpaint only the padding gutters and any masked defects per island at 2K; LaMa is CNN/FFC, pure torch, runs in well under 4 GB at 2K, and needs no base-model licence.
- Diffusion inpainting (FLUX.2-klein-4B, Z-Image-Turbo) is for semantic fixes on rendered views, not for atlas gutters; both are already in the pipeline, so no new licence exposure.
- Circular-padding tiling hacks assume a convolutional UNet; for FLUX.2-klein-4B / Z-Image (DiTs) only the VAE part applies, so prop tiling should come from StableMaterials/MatFuse or from post-hoc blending (TextureAlchemy-style) rather than from the main generator.

### Gaps
- No open implementation of UV-aware (reparametrised-patch) inpainting was found.
- Whether any ComfyUI seamless node supports FLUX.2-klein or Z-Image DiTs is unverified (all listings predate them or target SD UNets).
- `stabilityai/stable-diffusion-2-inpainting` and `-2-1-base` were not resolvable via the public HF API (gated/moved), so SD2-inpainting availability was not confirmed.
