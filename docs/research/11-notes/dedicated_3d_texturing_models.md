# Dedicated open 3D texture-generation models (state as of 2026-10-08)

Scope: candidates for a local "retexture" step (finished game mesh with its own UVs, 5k–20k tris) that could replace or
complement the TRELLIS.2 / Pixal3D image-conditioned texturing. Method notes: GitHub REST/`gh` was blocked in this
session, so "last commit" dates come from README news sections, HF cards and one third-party tracker (gittrend);
exact last-commit timestamps and precise open-issue counts are listed as gaps where not visible. Prior in-repo survey
(`docs/research/04-texturing.md`, 2026-10-03) was used only as a starting list; every claim below was re-verified
against a primary page unless marked.

## Key Question 1: Which candidates are fully commercial-clean (code + weights + base model + no region lock) and could fit 16 GB VRAM with torch 2.8 on Windows without nvdiffrast / flash-attn / xformers (or with a reasonable swap)?

### Takeaway
No dedicated texturing model is simultaneously (a) licence-clean end to end, (b) full PBR on the mesh's own UVs, (c)
2K, and (d) demonstrated inside 16 GB on Windows. The only clean full-PBR candidate is **Material Anything** (MIT code,
Apache-2.0 estimator weights, SD 2.1 backbone, PyTorch3D only, 1024² UV maps, xatlas only when the mesh has no UVs);
the only clean *high-resolution* candidate that keeps UVs is **MV-Adapter texturing** (Apache-2.0, SDXL, 6 × 768 views
→ 4096 UV, RGB only) but it hard-depends on nvdiffrast + CV-CUDA (no Windows wheels, open issue). Every 2026 2K/4K PBR
model (UltraTex, LumiTex, UniTEX) is built on FLUX.1-dev / FLUX.2-klein-9B (FLUX non-commercial) and nothing ships a
FLUX.2-klein-4B (Apache) variant. Hunyuan-family models (Hunyuan3D-Paint 2.1, MaterialMVP "professional" weights,
LumiTex's renderer, Step1X-3D's rasterizer) carry the Tencent licence that excludes the EU.

### Cited Findings

#### Per-candidate fact sheets

**MV-Adapter (huanngzh/MV-Adapter) — texturing branch**
- Dated news: 2024-12-27 initial release; 2025-03-07 geometry-guided multiview weights; 2025-05-15 "full text-to-texture and image-to-texture pipeline released"; 2025-06-13 SD2.1 geometry adapters "under 10 GB"; 2025-06-26 accepted to ICCV 2025; no 2026 entries; 47 commits shown — [GitHub README](https://github.com/huanngzh/MV-Adapter)
- Inputs: `.glb` mesh + text (`scripts.texture_t2tex`) or image (`scripts.texture_i2tex`, optional `--remove_bg`); output `<name>_shaded.glb`; README does not mention PBR maps; base SDXL by default, `--variant sd21` for <10 GB; licence Apache-2.0; extra checkpoints RealESRGAN_x2plus and big-lama — [GitHub README](https://github.com/huanngzh/MV-Adapter)
- VRAM per README: image-to-multiview ~14 GB; text-geometry-to-multiview SDXL >12 GB / SD2.1 <6 GB; image-geometry-to-multiview SDXL >16 GB / SD2.1 <10 GB; resolution 768 (SDXL), training renders 1024 — [GitHub README](https://github.com/huanngzh/MV-Adapter)
- Texture script: 6 views, `height=width=768` (SDXL) or 512 (SD2.1); `uv_size=4096` (SDXL) or 2048 (SD2.1); flags `uv_unwarp=True`, `preprocess_mesh` — [texture_i2tex.py](https://raw.githubusercontent.com/huanngzh/MV-Adapter/main/scripts/texture_i2tex.py)
- Texture pipeline rasterizer: `self.ctx = NVDiffRastContextWrapper(device=self.device)`; `CameraProjection(pb_backend="torch-cuda")` for back-projection with `aoi_cos_valid_threshold=0.2`, `uv_exp_blend_alpha=3`; `uv_unwarp` default `False` → mesh loaded with existing UVs via `load_mesh`, otherwise `process_raw` writes a `*_unwarp` mesh; UV inpainting via a spandrel-loaded network or padding fallback — [pipeline_texture.py](https://raw.githubusercontent.com/huanngzh/MV-Adapter/main/mvadapter/pipelines/pipeline_texture.py)
- requirements.txt: texturing extras `spandrel==0.4.1`, `open3d`, `pymeshlab`, `cvcuda_cu12`; `git+https://github.com/NVlabs/nvdiffrast.git`; no xformers/flash-attn/kaolin/pytorch3d/triton — [requirements.txt](https://raw.githubusercontent.com/huanngzh/MV-Adapter/main/requirements.txt)
- Windows: issue #55 "Windows support?" (opened 2025-06-18, open), #51 "texture generation, you need to install CV-CUDA!! where is the windows wheels??" (2025-06-06, open), #58 "RuntimeError: Cuda error: 2 … cudaGraphicsGLRegisterBuffer" (2025-07-01, open) — [MV-Adapter issues search](https://github.com/huanngzh/MV-Adapter/issues?q=windows)
- ComfyUI-MVAdapter (Apache-2.0): text/image-to-multiview, LoRA, ControlNet, view selector; **no geometry-conditioned or texture-baking nodes**; "SDXL still needs roughly 13–14 GB"; last update 2025-06-26 — [ComfyUI-MVAdapter](https://github.com/huanngzh/ComfyUI-MVAdapter)
- Training data released as Objaverse-Ortho10View / Objaverse-Rand6View (2025-04-23) — [GitHub README](https://github.com/huanngzh/MV-Adapter)
- Downstream users confirm VRAM: MIDI-3D's textured scene generation installs MV-Adapter and "may require about 30G of VRAM" — [MIDI-3D README](https://github.com/VAST-AI-Research/MIDI-3D)

**TEXGen (cvmi-lab/TEXGen; weights Andyx/TEXGen)**
- Feed-forward 700M-parameter diffusion model "which diffuses albedo texture map directly on the UV domain"; released checkpoint uses Flow Matching ("differs from the paper"); test on a 24 GB GPU, training >40 GB; deps torch 2.1.0 / CUDA 11.8, PyG (pytorch-cluster/scatter/sparse), `lambdalabs/sd-image-variations-diffusers`, `stabilityai/stable-diffusion-2-depth`; only dated news "[2024-12-15] Release the inference code"; 11 commits; no licence stated in README — [GitHub README](https://github.com/cvmi-lab/TEXGen)
- Repo `LICENSE` file does not exist (raw fetch 404) — [raw LICENSE 404](https://raw.githubusercontent.com/cvmi-lab/TEXGen/main/LICENSE)
- HF weights card: `license: apache-2.0`, no gating, pipeline tag Image-to-3D — [Andyx/TEXGen](https://huggingface.co/Andyx/TEXGen)
- Paper: Objaverse → 120,400 cleaned mesh–texture pairs (120K train / 400 eval), Gemini captions; meshes **re-unfolded with xAtlas** to a single atlas and diffuse colour baked onto the new UVs; inputs text + one posed view + mesh; 1024×1024 UV; <10 s on one A100 (30 DDIM steps); Table 1 FID/KID×10⁻⁴/time: TEXTure 48.31/48.00/80 s, Text2Tex 49.85/47.38/344 s, Paint3D 43.55/25.73/95 s, TEXGen 34.53/11.94/10 s; **albedo only**, PBR listed as future work — [arXiv 2411.14740](https://arxiv.org/html/2411.14740)

**SeqTex (VAST-AI-Research/SeqTex; weights VAST-AI/SeqTex-Transformer)**
- "end-to-end 3D texture generation method using video diffusion priors" (SIGGRAPH Asia 2025); credits Wan2.1 for the 3D prior; outputs a UV texture map plus position/normal maps and a multi-view image; text goes through SDXL or FLUX to an image first; multi-part models must be merged to a single mesh with one UV map; tested on one A100 80 GB, training ≥8×80 GB with FSDP; torch 2.6.0 cu118; code release v1.0.0 on 2025-12-12; 2 commits, 1 open issue, 48 stars; no Windows notes; MV-Adapter credited as coding framework — [GitHub README](https://github.com/VAST-AI-Research/SeqTex)
- No LICENSE file (raw and blob fetches both 404) — [raw LICENSE 404](https://raw.githubusercontent.com/VAST-AI-Research/SeqTex/main/LICENSE), [blob 404](https://github.com/VAST-AI-Research/SeqTex/blob/main/LICENSE)
- HF model card: licence "[More Information Needed]", base model "[More Information Needed]", 3B params F32, no gating — [VAST-AI/SeqTex-Transformer](https://huggingface.co/VAST-AI/SeqTex-Transformer)
- HF Space is in "Runtime error" (exit code 128) — [VAST-AI/SeqTex Space](https://huggingface.co/spaces/VAST-AI/SeqTex)

**UniTEX (YixunLiang/UniTEX; weights coolbeam/UniTex)**
- Two-stage: LoRA-adapted DiT multi-view stage + "Large Texturing Model" predicting "Texture Functions" in 3D ("independent of mesh topology", bypasses UV); inputs reference image + mesh; code Apache-2.0; FLUX LoRA checkpoints, TSD-SR (SD3 Medium) super-resolution; deps kaolin, nvdiffrast, slangtorch, torch 2.4.1 cu118; accepted CVPR 2026; **LTM checkpoint release still an open TODO**; 2 commits — [GitHub README](https://github.com/YixunLiang/UniTEX)
- Paper: fine-tunes two **FLUX.1-dev** DiTs; six orthographic 512×512 views; LTM = transformer over triplane (3×32×32) + cube (8×8×8) tokens, RGB only, no PBR; training ablation on A800 at batch 4: 69.2 GB / 38.76 s/it (53.6 GB with drop-training); Table 1 artist meshes UniTEX vs Hunyuan3D-Paint: CMMD 0.826 vs 0.909, FID_CLIP 16.03 vs 20.38, CLIP 0.844 vs 0.824, LPIPS 0.090 vs 0.091; generative meshes user preference 65.91 % vs 21.36 %; MV-Adapter not evaluated — [arXiv 2505.23253](https://arxiv.org/html/2505.23253)
- HF card tagged `apache-2.0`, base model not stated — [coolbeam/UniTex](https://huggingface.co/coolbeam/UniTex)

**MaterialMVP (ZebinHe/MaterialMVP)**
- ICCV 2025; code release 2025-07-02; "Professional Version" weights = **Hunyuan3D-Paint-v2-1 at tencent/Hunyuan3D-2.1**; "Paper Version" weights "coming soon"; inputs `mesh.glb` + `image.png`; 512 (or 768/512 professional), `max_num_view=6`; custom CUDA `custom_rasterizer` + `DifferentiableRenderer`; torch 2.5.1 cu124; Real-ESRGAN x4; licence not stated — [GitHub README](https://github.com/ZebinHe/MaterialMVP)
- No LICENSE file at repo root (raw fetch 404) — [raw LICENSE 404](https://raw.githubusercontent.com/ZebinHe/MaterialMVP/main/LICENSE)
- Third-party tracker snapshot: 199 stars, 15 open issues, last push ~9 months before capture — [gittrend MaterialMVP](https://gittrend.io/repo/ZebinHe/MaterialMVP)
- The Hunyuan3D 2.1 licence that governs those weights: "TENCENT HUNYUAN 3D 2.1 COMMUNITY LICENSE AGREEMENT", Territory = "the worldwide territory, excluding the territory of the European Union, United Kingdom and South Korea"; >1 M MAU requires a separate Tencent licence — [Hunyuan3D-2.1 LICENSE](https://huggingface.co/tencent/Hunyuan3D-2.1/blob/main/LICENSE)

**Paint3D (OpenTexture/Paint3D; weights GeorgeQi/Paint3d_UVPos_Control)**
- Inputs untextured mesh + text or IP-Adapter image; outputs "high-resolution, lighting-less, and diverse 2K UV texture maps" (`albedo.png`); depth-aware SD + ControlNets (depth, UV inpaint, UV-position); code Apache-2.0; deps Kaolin 0.13.0, PyTorch3D, Lightning; tested CentOS 7, torch 1.12.1, CUDA 11.6; code uploaded 2024-04-26; 20 commits — [GitHub README](https://github.com/OpenTexture/Paint3D)
- HF weights `license: apache-2.0` — [GeorgeQi/Paint3d_UVPos_Control](https://huggingface.co/GeorgeQi/Paint3d_UVPos_Control)
- Quality: FID 43.55 (TEXGen table) and 153.20 (Material Anything table, worst in that table) — [TEXGen paper](https://arxiv.org/html/2411.14740), [Material Anything paper](https://arxiv.org/html/2411.15138)

**TexGaussian (ymxbj/TexGaussian; weights ymxbj/TexGaussian)**
- CVPR 2025; code + 5 checkpoints: 4 unconditional RGB (ShapeNet bench/car/chair/table, ~70M) and **TexGaussian-PBR** (text-conditional, Objaverse, ~295M); outputs albedo map + material map (G=roughness, B=metallic); deps torch 2.1.0 cu118, modified `diff-gaussian-rasterization` (compiled CUDA), **nvdiffrast**, ocnn-pytorch; no LICENSE file; 17 commits, 3 open issues — [GitHub README](https://github.com/ymxbj/TexGaussian)
- Project page: bakes "the multi-view rendered images to the UV space of the input 3D model"; single feed-forward pass; website CC BY-SA 4.0, no code/weights licence — [project page](https://3d-aigc.github.io/TexGaussian)
- Paper table: ~21.04 s per object vs 20–48 min for Fantasia3D/FlashTex/DreamMat — [arXiv 2411.19654](https://arxiv.org/abs/2411.19654v1)

**TexPainter (Quantuman134/TexPainter)**
- MIT; mesh + text; depth-conditioned SD (`stable_diffusion_depth.py`), DDIM + colour-fusion optimisation; deps PyTorch3D, torch 2.0.1 cu118, Ubuntu 20.04; "at least … 24 GB" GPU (RTX 3090); `--opt_eps 0` brings generation under 5 min; notes dated 2024-11-04 — [GitHub README](https://github.com/Quantuman134/TexPainter)

**SyncMVD (LIU-Yuxin/SyncMVD)**
- MIT; text + `.obj`/`.mtl` mesh; SD v1.5 + ControlNet v1.1 depth and normalbae; PyTorch3D, XAtlas auto-unwrap fallback; ~40k faces recommended; existing UVs used when the obj/mtl requirement is met; Linux target, WSL suggested for Windows; 53 commits; no VRAM figure — [GitHub README](https://github.com/LIU-Yuxin/SyncMVD)
- Quality: FID 118.46 / CLIP 30.66 in Material Anything's table — [Material Anything paper](https://arxiv.org/html/2411.15138)

**MVPaint (3DTopia/MVPaint)**
- Mesh + prompt file; "multi-view consistent textures with arbitrary UV unwrapping"; MVDream (low-res) + SyncMVD (high-res) environments; pretrained model on Dropbox; "[2025/07/29] Release a preliminary version for testing"; no licence shown; 20 commits — [GitHub README](https://github.com/3DTopia/MVPaint)

**RomanTex (oakshy/RomanTex)**
- Repo contains only `assets/` + README; ICCV 2025 (2025-06-26); 5 commits; no code, weights or licence — [GitHub README](https://github.com/oakshy/RomanTex)

**Material Anything (3DTopia/MaterialAnything; weights xanderhuang/material_estimator)**
- "PBR material generation model for various 3D meshes" (texture-less, albedo-only, generated, scanned); outputs albedo, roughness, metallic, bump, "UV-ready" after a UV-space refiner; MIT; deps PyTorch + PyTorch3D + Blender 3.2.2; news 2024.12 dataset, 2025.06 estimator + refiner on HF; CVPR 2025 Highlight; Linux-style setup — [GitHub README](https://github.com/3DTopia/MaterialAnything)
- Paper: backbone **Stable Diffusion v2.1**; Material3D = ~80K Objaverse objects with complete base-colour/roughness/metallic/bump; training UVs from Blender Smart UV Project; **inference: objects without UVs unwrapped with xatlas** (paper does not say existing UVs are replaced); renders 512², refiner input 768², UV maps 1024²; training 8×A100; all results on one A100, no inference time; Table 1 texture-less FID/CLIP: Text2Tex 116.41/30.33, SyncMVD 118.46/30.66, Paint3D 153.20/28.40, NvDiffRec 103.81/30.14, DreamMat 113.34/30.64, Ours 100.63/31.06 — [arXiv 2411.15138](https://arxiv.org/html/2411.15138)
- HF estimator card: `license: apache-2.0`, StableDiffusionPipeline, 0.9B params F32, empty README — [xanderhuang/material_estimator](https://huggingface.co/xanderhuang/material_estimator)

**PBR-Boost ("Boosting 3D Object Generation through PBR Materials", snowflakewang/PBR_Boost_3DGen)**
- SIGGRAPH Asia 2024; Apache-2.0; modules for albedo/mesh generation, normal boosting, roughness & metalness boosting (semi-automatic, manual `ks_mask`), relighting; weights `SnowflakeWang/MonoIntrinsics` (MonoAlbedo, MonoNormal); torch 1.13.1, Ubuntu 18.04, A100; nvdiffrast acknowledged; 4 commits, 3 open issues, 16 stars — [GitHub README](https://github.com/snowflakewang/PBR_Boost_3DGen)
- Abstract: albedo + bump UV maps from a fine-tuned Stable Diffusion; roughness/metalness via "semi-automatic process" — [arXiv 2411.16080](https://arxiv.org/abs/2411.16080)

**Step1X-3D texture stage (stepfun-ai/Step1X-3D)**
- "SD-XL-based texture synthesis module"; multi-view training uses MV-Adapter code (`step1x3d_ig2mv_sdxl.yaml`); inputs image + untextured `.glb`, mesh cleaned/decimated first; Apache-2.0; deps torch 2.5.1 CUDA 12.4, pytorch3d, kaolin 0.17.0, torch-cluster, **custom CUDA `custom_rasterizer` and `differentiable_renderer` adapted from Hunyuan3D 2.0**; 27 GB VRAM for geometry+texture (29 GB label variant), 152 s for 50 steps; texture weights 2025-05-13; 30K texture assets; 3.5B total — [GitHub README](https://github.com/stepfun-ai/Step1X-3D)
- HF: `license: apache-2.0`, 800K uids dataset released, no gating or geo restriction — [stepfun-ai/Step1X-3D](https://huggingface.co/stepfun-ai/Step1X-3D)

**Hunyuan3D-Paint 2.1 (reference / banned outside experimental engine)**
- "10 GB VRAM for shape generation, 21GB for texture generation and 29GB for shape and texture generation in total"; Paint-v2-1 = 2B; `max_num_view=6, resolution=512`; custom_rasterizer + DifferentiableRenderer; torch 2.5.1 cu124; released 2025-06-13; README says supports macOS/Windows/Linux — [Hunyuan3D-2.1 README](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1)
- Licence excludes EU/UK/South Korea; >1 M MAU clause — [LICENSE](https://huggingface.co/tencent/Hunyuan3D-2.1/blob/main/LICENSE)
- Community: one ComfyUI creator could not run Paint locally ("20 GB+"), recommends ≥20 GB for texturing; kijai's ComfyUI-Hunyuan3DWrapper has Paint-model loader and PBR nodes; an unofficial low-VRAM fork reports 6-view PBR at ~10.5 GB peak on a 20 GB AMD card — [search summary of runcomfy / patreon write-ups](https://www.runcomfy.com/comfyui-nodes/ComfyUI-Hunyuan3DWrapper) (secondary sources)

**UltraTex (yiboz2001/UltraTex; weights on ModelScope Yibo-Zhang/UltraTex)**
- arXiv 2026-09-22; code, training, inference and weights released 2026-10-03; weights for two backbones: **FLUX.1-dev** and **FLUX.2-Klein 9B** (`flux-2-klein-base-9b`), each with albedo and metallic-roughness LoRAs + a Foreground-Aware VAE decoder; **no FLUX.2-Klein 4B weights, "the 9B LoRA won't load into it"**; code MIT, vendored SLA sparse-attention Apache-2.0, **no weights licence statement**; deps Python 3.12, CUDA 12.4, torch 2.5.1, **Triton 3.1.0 sparse-attention kernels compiled on first use**, DeepSpeed configs; no nvdiffrast/xformers/flash-attn/kaolin/pytorch3d; 2048×2048 default; VRAM and inference time not stated; H100 kernel patches; 1 open issue; no Windows notes; outputs albedo by default or MR with `--task mr`; no description of baking to the mesh or UV handling — [GitHub README](https://github.com/yiboz2001/UltraTex)
- Paper: LoRA rank 64 on "the pretrained FLUX model"; inputs reference image + six per-view normal maps (no text); six canonical 2K views reprojected onto the mesh; G-buffer TexVerse ≥268K filtered assets, renders to 4096²; 64 H200 for ~18 days; efficiency measured on one H200; dense/sparse settings OOM at 90–100 % foreground; Table 1 unshaded FID 125.13 / CLIP-FID 15.180 / CMMD 0.810 / CLIP-I 0.929 / LPIPS 0.082 vs Hunyuan3D 2.1 153.48 / 18.995 / 1.150 / 0.908 / 0.136; baselines Step1X-3D, UniTEX, Hunyuan3D 2.1, LumiTex; LumiTex beats it on shaded CMMD (0.351 vs 0.368); held-out 100 TexVerse objects — [arXiv 2609.23169](https://arxiv.org/html/2609.23169)
- Project page: venue SIGGRAPH Asia 2026 ("SA Conference Papers '26"); dataset HF `YiboZhang2001/G-buffer-TexVerse`, 351,847 public BSDF assets; "beyond an 80 % foreground ratio every configuration runs out of memory"; no licence or VRAM — [project page](https://yiboz2001.github.io/UltraTex)
- FLUX.2-klein-9B base: `flux-non-commercial-license`, "fits in ~29GB VRAM"; **the 4B models are Apache-2.0** — [black-forest-labs/FLUX.2-klein-9B](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B)

**LumiTex (LumiTexPBR/LumiTex)**
- ICLR 2026; repo Apache-2.0; base `Jingzhi03/FLUX-MV-Shaded` (FLUX.1-dev acknowledged), LoRA trained on `stepfun-ai/Step1X-3D-obj-data`; uses **Tencent Hunyuan3D-2.1 rendering code** (`Renderer/custom_rasterizer`, `DifferentiableRenderer`); README itself says "the FLUX model and Tencent Hunyuan3D-2.1 rendering code are non-commercial and may restrict commercial use"; inputs `ref.png` + `.obj/.glb`; generates/inpaints basecolor by default; Python 3.11, CUDA 12.8, torch 2.7.0; optional torch.compile / cache-dit / flash-attn3; TODO list (evaluation, pretrained pipeline, data infra) not shown complete; 4 open issues; no VRAM figure — [GitHub README](https://github.com/LumiTexPBR/LumiTex)
- Project page: affiliations CUHK-Shenzhen, HKUST, HKU, PKU, LIGHTSPEED, Lingnan; figures labelled 4K; page CC-BY-NC-SA 4.0 — [lumitex.vercel.app](https://lumitex.vercel.app)
- Paper claims SOTA "surpassing both existing open-source and commercial methods"; arXiv 2025-11-24 — [search summary](https://arxiv.org/html/2511.19437v1)

**NaTex (Zeqiang-Lai/NaTex)**
- CVPR 2026 Highlight; Tencent Hunyuan + MMLab CUHK; texture as colour point cloud, geometry-aware VAE (>80× compression) + DiT; image + geometry conditioned, no text; material (roughness/metallic) "could be readily extended"; qualitative benchmark only, no scores; page links GitHub but states no release status, weights or licence — [project page](https://natex-ldm.github.io/)
- GitHub repo and issues pages returned 404 to this session; tracker snapshot: last push 2026-04-09, 135 stars, 3 open issues — [gittrend NaTex](https://gittrend.io/repo/Zeqiang-Lai/NaTex)
- HF paper page lists no linked models, spaces or code — [HF papers 2511.16317](https://huggingface.co/papers/2511.16317)

**LaFiTe (VAST / Tsinghua / HKU)**
- Sparse latent colour field VAE + rectified flow; albedo base model, second stage roughness + metallic conditioned on albedo latent; ~1M assets from Objaverse, Objaverse-XL and TexVerse; VAE 600K steps on 16 A800, albedo flow 500K steps on 32 A800; ">10 dB PSNR" over TRELLIS at 128³; HF paper page lists no code/models — [HF papers 2512.04786](https://huggingface.co/papers/2512.04786)

**PixTex (VAST, SIGGRAPH 2026)**
- "Consistent 3D Texturing via Pixel-Space Multi-View Diffusion", SIGGRAPH Conference Papers '26 article 57, published 2026-07-19; no code/repo found — [ACM DL](https://dl.acm.org/doi/10.1145/3799902.3811120); VAST research listing — [tripo3d.ai/research](https://www.tripo3d.ai/de/research)

**MV2UV (Huawei Hisilicon / HKUST, CVPR 2026)**
- arXiv 2026-03-16; multi-view images as prompts, a modified SDXL generates the UV map directly (frozen SDXL U-Net copy as "Multiview Reference Network"); no code or project URL on the abstract page — [arXiv 2603.15436](https://arxiv.org/abs/2603.15436)

**MatLat (KAIST, CVPR 2026)** — fine-tunes the pretrained VAE to add material channels (albedo, roughness, metallic); project page matlat-proj.github.io; no code repo found — [search summary](https://arxiv.org/html/2512.17302v1)

**MVPainter (amap-cvlab/MV-Painter; weights shaomq/MVPainter)**
- 250 stars, 37 forks, 22 commits, 8 open issues; inputs GLB + image (meshes from TripoSG/Hunyuan-2/TRELLIS/Hi3DGen with `--geo_rotation`); outputs multi-view images, optional PBR maps (model "improved based on" IDArb), painted models; UNet + ControlNet multi-view model, base not named; news 2025-04-30; acknowledges Hunyuan3D-1 and -2; gradio/training/data code unchecked — [GitHub README](https://github.com/amap-cvlab/MV-Painter)
- LICENSE = Apache License 2.0 — [LICENSE](https://github.com/amap-cvlab/MV-Painter/blob/main/LICENSE)
- Paper: ControlNet-based geometric conditioning, PBR attributes extracted from generated views, full pipeline open-sourced; submitted 2025-05-19 — [arXiv 2505.12635](https://arxiv.org/abs/2505.12635)

**Pandora3D (Tencent/Tencent-XR-3DGen)**
- "all-in-one code release" with training and inference; weights on Google Drive and HF `peterji/Tencent_XR_3DGen`; texture modules `texture_generation`, `multiview_geo2rgb`, `multiview_rgbpbr`, render-bake utilities; uses SAM and RMBG-1.4; code "licensed under the MIT License but with additional restrictions" that prohibit use "within the European Union"; 18 commits, no dates — [GitHub README](https://github.com/Tencent/Tencent-XR-3DGen)
- Paper: Tencent XR Vision Labs + ANU, submitted 2025-02-20; texture = frontal image → extra viewpoints → PBR conversion → high-res refinement with consistency scheduler — [arXiv 2502.14247](https://arxiv.org/html/2502.14247)

**PBR3DGen (XiaokangWei/PBR3DGen, AAAI 2026)** — README + figures only; "We plan to release the checkpoints upon the acceptance of the paper"; based on InstantMesh; Tencent Hunyuan3D affiliation; no licence — [GitHub README](https://github.com/XiaokangWei/PBR3DGen)

**TexFusion (NVIDIA, ICCV 2023)** — SD-backbone, UV-parameterised texture via interlaced multiview sampler; a later paper noted TexFusion's authors "had yet to publish their code", built an approximation instead — [NVIDIA project page](https://research.nvidia.com/labs/toronto-ai/texfusion), [SyncMVD paper](https://arxiv.org/pdf/2311.12891)

**Diffusion Texture Painting (NVIDIA, SIGGRAPH 2024)** — interactive brush-based painting; no code link found — [NVIDIA project page](https://research.nvidia.com/labs/toronto-ai/DiffusionTexturePainting)

**Tex4D (ZqlwMatt/Tex4D)** — zero-shot 4D textures for an untextured mesh *sequence* + text via video diffusion; Apache-2.0; PyTorch3D; inference-code release still a TODO; 7 commits — [GitHub README](https://github.com/ZqlwMatt/Tex4D)

**PrimX / 3DTopia-XL (3DTopia/3DTopia-XL)** — generator (single image or text → PBR mesh), not a retexturer; Apache-2.0 code, weights licence not stated; requires xformers, compiles `simple-knn`; nvdiffrast acknowledged; CVPR 2025, training code 02/2025 — [GitHub README](https://github.com/3DTopia/3DTopia-XL)

**Hi3D (yanghb22-fdu/Hi3D-Official)** — SVD-based multi-view generation from one image (ACM MM 2024); no mesh-retexturing stage; MIT code; tested on 80 GB A100; 6 commits — [GitHub README](https://github.com/yanghb22-fdu/Hi3D-Official)

**MIDI-3D (VAST-AI-Research/MIDI-3D)** — scene generation; textures via MV-Adapter (~30 GB VRAM); Apache-2.0 code; last news 2025-05 — [GitHub README](https://github.com/VAST-AI-Research/MIDI-3D)

**LHM / LHM++ (aigc3d/LHM)** — single-image animatable human avatars driven by SMPL-X parameter files; Apache-2.0 code; LHM++ open-sourced March 2026 (8-view input on 8 GB); no arbitrary-mesh texturing — [GitHub README](https://github.com/aigc3d/LHM)

**Hi3DGen (Stable-X/Hi3DGen)** — geometry only ("via Normal Bridging"), MIT, "dependencies on … kaolin, nvdiffrast, flexicube were removed", requires xformers 0.0.27.post2; WIP — [GitHub README](https://github.com/Stable-X/Hi3DGen)

**TripoSG / TripoSF (VAST)** — TripoSG: image-to-mesh only, MIT code, weights licence not stated, last news 2025-04 — [TripoSG README](https://github.com/VAST-AI-Research/TripoSG); TripoSF: SparseFlex VAE, geometry only, MIT, initial release 2025-03 — [TripoSF README](https://github.com/VAST-AI-Research/TripoSF)

**Meta AssetGen 2.0 / TextureGen** — "consists of two models … one to generate 3D meshes and another to generate textures"; used internally, rollout to Horizon creators; no weights, licence or repo — [Meta developer blog](https://developers.meta.com/horizon/blog/AssetGen2); HF paper page shows no linked model — [HF papers 2407.02445](https://huggingface.co/papers/2407.02445)

**Stability SV3D / SPAR3D**
- SV3D: licence tag `sv3d-nc-community` ("Stability AI Community License"), gated, orbital video (21 frames 576×576) from one image; no mesh texturing — [stabilityai/sv3d](https://huggingface.co/stabilityai/sv3d)
- SPAR3D: single image (+ optional point cloud) → GLB with `--texture-resolution`; gated HF weights; custom CUDA texture baker; ~10.5 GB default, ~7 GB low-VRAM; no retexture of existing meshes; 14 commits — [GitHub README](https://github.com/Stability-AI/stable-point-aware-3d); licence "STABILITY AI COMMUNITY LICENSE AGREEMENT" (registration required, terminates above USD 1 M annual revenue) — [LICENSE.md](https://raw.githubusercontent.com/Stability-AI/stable-point-aware-3d/main/LICENSE.md)

**Seed3D 1.0 / 2.0 (ByteDance)** — API-only (Volcano Engine "Doubao-Seed3D-2.0", 2026-04-23 per third-party wiki); no open weights found — [Seed blog](https://seed.bytedance.com/en/blog/seed3d-1-0-released-generate-high-fidelity-3d-models-from-single-images-featuring-sota-texturing), [aiwiki Seed3D 2.0](https://aiwiki.ai/wiki/seed3d_2)

**TRELLIS.2 / Pixal3D upstream, 2026**
- TRELLIS.2 README has no dated news, is "image-to-3D", no text/style/multi-image conditioning; texturing via `example_texturing.py`/`app_texturing.py`, outputs Base Color, Roughness, Metallic, Opacity, `texture_size=4096`; Releases empty; 11 commits — [microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2)
- Pixal3D news: Apr 2026 SIGGRAPH 2026 accept; May 2026 inference + demo, TRELLIS.2-backbone variant, training code; **Sep 2026 multi-view inference code** (`inference_mv.py`, `transforms.json`, separate MV weights, first view = front, 2 views default in training); no text or style conditioning; MIT; 15 commits — [TencentARC/Pixal3D](https://github.com/TencentARC/Pixal3D)
- A Jan-2026 paper notes TRELLIS.2 "supports only image-to-3D generation" and interpolated image tokens as a workaround — [ATATA, arXiv 2601.11194](https://arxiv.org/pdf/2601.11194)

**2026 survey (Eurographics STAR / CGF 45(2), arXiv 2606.00137, submitted 2026-05-28)**
- Table 1 classifies: PBR-output methods = TANGO, TextureDreamer, DreamMat, MaPa, Paint-it, Fantasia3D, Material Anything, MaterialMVP, CLAY, VideoMat, DreamPBR; UV-space feed-forward = TEXGen (700M), Point-UV Diffusion, SeqTex (Video+UV); synchronized multi-view = SyncMVD, MVPaint, TexPainter, VCD-Texture, GenesisTex/2, FlexiTex, RomanTex, MaterialMVP; everything else RGB; commercial systems Hunyuan3D, Seed3D, CLAY ("2K PBR material maps"), Rodin, Tripo, Meshy "not always fully disclosed" — [survey §4–5](https://arxiv.org/html/2606.00137v1)
- Datasets: TexVerse "over 858K" objects, "over 158K with full PBR maps"; cleaning pipelines "exclude assets tagged with restrictive terms (e.g., 'NoAI') and keep only redistributable Creative Commons licenses"; "PBR data is scarce"; future work calls for "curated, rights-cleared benchmarks" — [survey §5](https://arxiv.org/html/2606.00137v1)
- Survey project page has an empty method table and points to github.com/sairajk/neural-mesh-texturing — [project page](https://sairajk.github.io/neural-mesh-texturing)

### Inferences
- **Licence-clean end to end (code + weights + base, no region lock):** Material Anything (MIT + Apache + SD 2.1), Paint3D (Apache + Apache + SD1.5-era ControlNets), SyncMVD (MIT, SD1.5 + ControlNet 1.1), TexPainter (MIT, SD-depth), MV-Adapter (Apache + Apache + SDXL OpenRAIL++), PBR-Boost (Apache + SD-derived MonoIntrinsics), MVPainter (Apache code; weights licence unstated), Step1X-3D (Apache, but texture stage carries Hunyuan3D-2.0-derived rasterizer code, see KQ5). SD 1.5 / 2.1 are CreativeML OpenRAIL-M family like SDXL's OpenRAIL++, which the owner's policy allows.
- **Not clean:** anything FLUX.1-dev / FLUX.2-klein-9B based (UltraTex, LumiTex, UniTEX multi-view stage), anything with Hunyuan weights or Hunyuan renderer code (Hunyuan3D-Paint 2.1, MaterialMVP, LumiTex), Pandora3D (EU prohibition), SeqTex / TexGaussian / MVPaint / TEXGen-code (no licence file), SPAR3D / SV3D (Stability Community Licence, not on the allowed list).
- **Fits 16 GB + Windows + no nvdiffrast/xformers/flash-attn:** Material Anything (SD 2.1 0.9B UNet, PyTorch3D only) and SyncMVD / Paint3D (SD1.5 + ControlNets, PyTorch3D / Kaolin) are the only clean ones whose dependency lists avoid the banned libraries; none publishes a 16 GB figure and all were tested on A100-class cards; PyTorch3D and Kaolin need Windows builds against torch 2.8 (no official PyTorch3D Windows wheels; this is an inference from general experience, not a cited fact). MV-Adapter texturing needs its `NVDiffRastContextWrapper` and CV-CUDA replaced by the project's pure-torch UV rasterizer; the diffusion part (SDXL + adapter, ~13–14 GB per ComfyUI notes) fits, the SD2.1 variant comfortably so. UltraTex's only hard kernel is Triton (triton-windows exists) and it targets Python 3.12, so it is technically the most Windows-friendly 2K model, but both of its bases are non-commercial and the 9B base needs ~29 GB.
- All 2026 "native 3D" texturing (NaTex, LaFiTe, PixTex, MV2UV, MatLat) is paper-only or unlicensed as of 2026-10-08.

### Gaps
- Exact last-commit dates and open-issue counts for most repos (GitHub API blocked); only README news and tracker snapshots are available.
- No candidate documents a measured VRAM figure on a 16 GB consumer GPU; none documents Windows-native runs (MV-Adapter's Windows issues are open and unanswered on the listing page).
- Licence of the SeqTex weights, TexGaussian code/weights, MVPaint code/weights, MVPainter weights, UltraTex weights, NaTex everything: not stated anywhere I could reach.
- Wan2.1's own licence (SeqTex base) was not fetched in this session; the SeqTex `third_party_license.md` fetch returned 404.
- Hunyuan3D-2.0's licence text (governing the rasterizer code vendored into Step1X-3D and the renderer in LumiTex) was not fetched; only the 2.1 licence (EU/UK/KR exclusion) was verified.

## Key Question 2: Which candidates keep the input mesh's UVs (hard requirement) and output full PBR, not just albedo?

### Takeaway
Only **Material Anything** (albedo + roughness + metallic + bump at 1024², UV-space refiner, xatlas only for meshes without UVs) and **TexGaussian-PBR** (albedo + roughness/metallic baked into the input mesh's UV space) do both; TexGaussian has no licence and needs nvdiffrast plus a CUDA splat rasterizer. MV-Adapter keeps UVs (default `uv_unwarp=False`) but is RGB-only. The strong PBR models (Hunyuan3D-Paint 2.1, UltraTex, LumiTex, MaterialMVP, Pandora3D) are either region-locked or on non-commercial bases, and TEXGen explicitly re-unwraps with xatlas.

### Cited Findings
- Material Anything: outputs albedo, roughness, metallic, bump; UV-space refiner; "UV-ready" — [GitHub README](https://github.com/3DTopia/MaterialAnything); 1024×1024 UV material maps; "objects without UVs are unwrapped with xatlas" — [arXiv 2411.15138](https://arxiv.org/html/2411.15138)
- TexGaussian: "bakes the multi-view rendered images to the UV space of the input 3D model"; albedo, roughness, metallic — [project page](https://3d-aigc.github.io/TexGaussian); material map G=roughness, B=metallic; PBR checkpoint trained on Objaverse — [GitHub README](https://github.com/ymxbj/TexGaussian)
- MV-Adapter: `uv_unwarp` default `False` → existing UVs loaded; output `_shaded.glb`, no PBR maps documented — [pipeline_texture.py](https://raw.githubusercontent.com/huanngzh/MV-Adapter/main/mvadapter/pipelines/pipeline_texture.py), [README](https://github.com/huanngzh/MV-Adapter)
- TEXGen: meshes "re-unfolded with xAtlas"; albedo only — [arXiv 2411.14740](https://arxiv.org/html/2411.14740)
- SyncMVD: existing UVs used for `.obj/.mtl`, xatlas fallback; RGB — [README](https://github.com/LIU-Yuxin/SyncMVD)
- SeqTex: requires single mesh with single UV map; UV texture output; survey classifies it RGB — [README](https://github.com/VAST-AI-Research/SeqTex), [survey Table 1](https://arxiv.org/html/2606.00137v1)
- UniTEX: "bypasses UV mapping", Texture Functions queried by nearest surface point; RGB only; write-back to the input UV layout not described — [arXiv 2505.23253](https://arxiv.org/html/2505.23253)
- UltraTex: albedo + metallic-roughness LoRAs, per-view 2K images "reprojected onto the input mesh"; UV handling not described — [README](https://github.com/yiboz2001/UltraTex), [paper](https://arxiv.org/html/2609.23169)
- LumiTex: basecolor by default, PBR framing; UV handling not stated — [README](https://github.com/LumiTexPBR/LumiTex)
- MVPainter: PBR maps via IDArb-based model; UV handling not stated — [README](https://github.com/amap-cvlab/MV-Painter)
- Paint3D: 2K albedo UV maps, "lighting-less", no PBR — [README](https://github.com/OpenTexture/Paint3D)
- Hunyuan3D-Paint 2.1 / MaterialMVP: PBR (albedo + MR) but UV handling not documented on the pages read; prior in-repo note records an xatlas re-unwrap (unverified here) — [MaterialMVP README](https://github.com/ZebinHe/MaterialMVP), [Hunyuan3D-2.1 README](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1)
- PBR-Boost: produces bump and roughness/metalness UVs for a mesh that already has an albedo UV (semi-automatic RM via manual masks) — [README](https://github.com/snowflakewang/PBR_Boost_3DGen)
- Pandora3D: `multiview_rgbpbr` + `render_bake` modules, UV handling unstated; EU prohibited — [README](https://github.com/Tencent/Tencent-XR-3DGen)

### Inferences
- For "PBR-ize an existing albedo texture on the mesh's own UVs", Material Anything's refiner stage and PBR-Boost's normal/RM boosting are the two licence-clean building blocks; both are SD-1.x/2.x era and 1K.
- Multi-view models (MV-Adapter, UltraTex, LumiTex, MVPainter, Hunyuan Paint) all produce per-view images; keeping UVs is purely a property of the back-projection step, which the project already owns (pure-torch UV rasterizer). The diffusion half of any of them could be swapped in front of the project's own bake, which is what makes MV-Adapter's SDXL adapter the lowest-risk "reference design" and UltraTex's LoRAs the highest-quality-but-blocked one.

### Gaps
- Whether Material Anything replaces existing UVs when present (paper only states the no-UV case).
- Whether MVPainter / Hunyuan Paint / UltraTex preserve or re-unwrap UVs (not documented on the pages read).

## Key Question 3: Which candidates produce texture detail beyond what a 1024³ voxel field gives (fine fabric, text, faces), and what evidence exists?

### Takeaway
Only the 2026 FLUX-based multi-view models document resolution above 1K with quantitative evidence: UltraTex generates six 2048² views trained on 4096² renders and beats Hunyuan3D 2.1 on FID (125.13 vs 153.48) and LPIPS (0.082 vs 0.136); LumiTex shows 4K figures and beats UltraTex on shaded CMMD. Among clean models, MV-Adapter writes a 4096 UV but from 768² views, Paint3D writes 2K from SD1.5-era views, TEXGen/Material Anything are 1K. No source gives evidence specifically about faces, text or fabric weave; the survey notes that fine-detail data is scarce and that models "bake specularities and shadows into albedo".

### Cited Findings
- UltraTex: 2048×2048 per view, six views; G-buffer TexVerse renders to 4096×4096; earlier multi-view methods "constrained to low operating resolutions such as 512 or 768"; 2K joint sequence ">212K tokens"; unshaded FID 125.13 vs 153.48 (Hunyuan3D 2.1), LPIPS 0.082 vs 0.136, CLIP-I 0.929 vs 0.908 — [arXiv 2609.23169](https://arxiv.org/html/2609.23169)
- LumiTex: result figures labelled 4K; claims SOTA over "existing open-source and commercial methods"; shaded CMMD 0.351 vs UltraTex 0.368 — [project page](https://lumitex.vercel.app), [UltraTex Table 1](https://arxiv.org/html/2609.23169)
- UniTEX vs Hunyuan3D-Paint on artist meshes: CMMD 0.826 vs 0.909, FID_CLIP 16.03 vs 20.38; user preference 65.91 % vs 21.36 % — [arXiv 2505.23253](https://arxiv.org/html/2505.23253)
- MV-Adapter: 768² views → `uv_size=4096` (SDXL) — [texture_i2tex.py](https://raw.githubusercontent.com/huanngzh/MV-Adapter/main/scripts/texture_i2tex.py)
- Hunyuan3D-Paint 2.1 default `resolution=512`, 6 views — [README](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1); MaterialMVP 512 or 768/512 — [README](https://github.com/ZebinHe/MaterialMVP)
- Paint3D: "2K UV texture maps" — [README](https://github.com/OpenTexture/Paint3D); TEXGen 1024² UV, FID 34.53 vs Paint3D 43.55 on 400 Objaverse objects — [arXiv 2411.14740](https://arxiv.org/html/2411.14740); Material Anything 1024² UV, FID 100.63 — [arXiv 2411.15138](https://arxiv.org/html/2411.15138)
- LaFiTe: ">10 dB PSNR" reconstruction gain over TRELLIS at 128³ (VAE reconstruction, not generation) — [HF papers 2512.04786](https://huggingface.co/papers/2512.04786)
- TRELLIS.2 exports `texture_size=4096` — [microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2); prior in-repo note: texel information limited to ~1/1024 of bbox at 1024³ — [docs/research/04-texturing.md](../04-texturing.md)
- Survey limitations: projection methods leave holes; models "can bake specularities and shadows into albedo"; high-res UV baking and multi-view sampling "are expensive in time and GPU memory" — [survey §7–8](https://arxiv.org/html/2606.00137v1)
- Meshy marketing: "Meshy 6 is preferred by 63.8% of professional evaluators"; community benchmark Meshy 6 vs Rodin 1014 vs 970 on texture quality; no Hunyuan in that benchmark — [meshy.ai/compare](https://www.meshy.ai/vi/compare) (vendor source)

### Inferences
- Metric tables are not comparable across papers (different test sets: TexVerse hold-out for UltraTex, Objaverse 400 for TEXGen, 20 objects for Material Anything), so the only like-for-like evidence is within each paper: UltraTex > Hunyuan 2.1 > Step1X/UniTEX on TexVerse; UniTEX > Hunyuan Paint on artist meshes.
- Detail above the voxel ceiling comes from view resolution, not UV size: MV-Adapter's 4096 UV from 768² views carries ~768 px of real detail per view; UltraTex's 2048² views are the only open weights that plausibly resolve fabric/text, and they are NC.
- No paper evaluates text legibility or faces explicitly; this remains an owner-side bench item.

### Gaps
- No Reddit/r/StableDiffusion side-by-side of Hunyuan Paint vs Meshy vs open models was found (searches returned vendor pages and ComfyUI write-ups only).
- No independent benchmark covering UltraTex/LumiTex outside their own papers.

## Key Question 4: What is the realistic VRAM/time per asset at 2K on a 16 GB card?

### Takeaway
No candidate publishes a 16 GB / 2K / Windows number. Documented figures are all A100/H100-class: TEXGen <10 s on A100 (24 GB test GPU), Hunyuan3D-Paint 2.1 21 GB, Step1X-3D 27 GB / 152 s, MV-Adapter SDXL image-geometry >16 GB (SD2.1 <10 GB; ComfyUI SDXL 13–14 GB), TexPainter 24 GB / <5 min, TexGaussian ~21 s, FLUX.2-klein-9B base alone ~29 GB, UltraTex measured on H200 and OOMs above 80 % foreground. The realistic 16 GB path is an SDXL- or SD2.1-class multi-view model (MV-Adapter / Material Anything) with the project's own bake; everything 2K-native is above 16 GB today.

### Cited Findings
- MV-Adapter: image-geometry-to-multiview SDXL ">16 GB", SD2.1 "<10 GB"; text-geometry SDXL ">12 GB" — [README](https://github.com/huanngzh/MV-Adapter); ComfyUI SDXL "13–14 GB" with fp16 VAE and VAE slicing — [ComfyUI-MVAdapter](https://github.com/huanngzh/ComfyUI-MVAdapter); with MIDI "about 30G" — [MIDI-3D](https://github.com/VAST-AI-Research/MIDI-3D)
- TEXGen: "<10 seconds on a single A100", 30 DDIM steps; testing works on a 24 GB GPU — [arXiv 2411.14740](https://arxiv.org/html/2411.14740), [README](https://github.com/cvmi-lab/TEXGen)
- Material Anything: all results on one A100; no inference time; estimator 0.9B params — [arXiv 2411.15138](https://arxiv.org/html/2411.15138), [HF card](https://huggingface.co/xanderhuang/material_estimator)
- TexPainter: ≥24 GB; <5 min with `--opt_eps 0` — [README](https://github.com/Quantuman134/TexPainter)
- TexGaussian: ~21.04 s per object (paper table) — [arXiv 2411.19654](https://arxiv.org/abs/2411.19654v1)
- Step1X-3D: 27 GB for geometry+texture, 152 s / 50 steps — [README](https://github.com/stepfun-ai/Step1X-3D)
- Hunyuan3D-Paint 2.1: 21 GB texture, 29 GB total — [README](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1); community "20 GB+", unofficial low-VRAM fork ~10.5 GB peak at 6 views — [runcomfy / patreon summaries](https://www.runcomfy.com/comfyui-nodes/ComfyUI-Hunyuan3DWrapper)
- UltraTex: efficiency on a single H200; OOM beyond 80 % foreground; 22.3×–74.6× inference speed-up vs dense baseline; no VRAM stated — [paper](https://arxiv.org/html/2609.23169), [README](https://github.com/yiboz2001/UltraTex); FLUX.2-klein-9B "fits in ~29GB VRAM" — [HF](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B)
- SeqTex: tested on A100 80 GB; 3B transformer in F32 — [README](https://github.com/VAST-AI-Research/SeqTex), [HF](https://huggingface.co/VAST-AI/SeqTex-Transformer)
- UniTEX training 69.2 GB at batch 4 on A800; no inference figure — [arXiv 2505.23253](https://arxiv.org/html/2505.23253)
- SPAR3D (generator, not retexture): ~10.5 GB default, ~7 GB low-VRAM — [README](https://github.com/Stability-AI/stable-point-aware-3d)
- Pixal3D texture stage in-repo estimate 1024 / 12 steps / 2K ≈ 14 GB — [docs/research/04-texturing.md](../04-texturing.md) (internal estimate)

### Inferences
- With a 16 GB cap, the only documented sub-16 GB diffusion halves are SD2.1-class (MV-Adapter sd21 <10 GB, Material Anything estimator) and SDXL at fp16 with VAE slicing (13–14 GB) — i.e. 512–768 px views, not 2K views; 2K then comes only from upscaling (Real-ESRGAN already in the pipeline) or from the voxel bake.
- FLUX.2-klein-4B (Apache, already in the pipeline) would be the natural 2K-capable base for a LoRA like UltraTex's, but no such LoRA exists and the 9B LoRA is explicitly incompatible.
- Time per asset for an SD-class multi-view pass + bake on a 16 GB card is plausibly tens of seconds to a few minutes (TEXGen 10 s on A100, TexGaussian 21 s, Step1X 152 s on bigger cards), but this is extrapolation; no source measures a 5080-class GPU.

### Gaps
- No measured VRAM/time for any candidate on a 16 GB or Blackwell GPU, on Windows, or at 2K.
- Material Anything's and SyncMVD's peak VRAM are unreported.

## Key Question 5: For each candidate, what is the licence blocker, if any, in one line?

### Takeaway
Blockers fall in four classes: FLUX non-commercial bases (UltraTex, LumiTex, UniTEX), Tencent/Hunyuan weights or code with EU exclusion (Hunyuan3D-Paint 2.1, MaterialMVP, LumiTex renderer, Pandora3D, Step1X-3D's rasterizer, NaTex by affiliation), missing licence files (SeqTex, TexGaussian, MVPaint, TEXGen code, UltraTex weights), and Stability Community Licence (SV3D, SPAR3D). The clean set is MV-Adapter, Material Anything, Paint3D, SyncMVD, TexPainter, PBR-Boost, MVPainter (code), with the caveat that MV-Adapter, TexGaussian, PBR-Boost and UniTEX depend on nvdiffrast (banned by project policy, replaceable).

### Cited Findings
| Candidate | Code licence | Weights licence | Base model (licence) | Blocker (one line) | Source |
|---|---|---|---|---|---|
| MV-Adapter texturing | Apache-2.0 | Apache-2.0 (README) | SDXL (OpenRAIL++) / SD2.1 | None on licence; hard deps nvdiffrast + CV-CUDA (no Windows wheels) must be swapped | [README](https://github.com/huanngzh/MV-Adapter), [requirements](https://raw.githubusercontent.com/huanngzh/MV-Adapter/main/requirements.txt), [issue #51](https://github.com/huanngzh/MV-Adapter/issues?q=windows) |
| TEXGen | no LICENSE file | Apache-2.0 (HF) | own UV diffusion + SD-2-depth / sd-image-variations components | Code licence absent; re-unwraps with xatlas; albedo only | [README](https://github.com/cvmi-lab/TEXGen), [HF](https://huggingface.co/Andyx/TEXGen), [paper](https://arxiv.org/html/2411.14740) |
| SeqTex | no LICENSE file | "More Information Needed" | Wan2.1 (not verified here) | No licence anywhere; 80 GB-class; RGB | [README](https://github.com/VAST-AI-Research/SeqTex), [HF](https://huggingface.co/VAST-AI/SeqTex-Transformer) |
| UniTEX | Apache-2.0 | Apache-2.0 tag on HF, but LoRAs of FLUX.1-dev | FLUX.1-dev (NC) + SD3 Medium upscaler | FLUX.1-dev LoRA → non-commercial; LTM checkpoint unreleased; kaolin + nvdiffrast + slangtorch | [README](https://github.com/YixunLiang/UniTEX), [paper](https://arxiv.org/html/2505.23253), [HF](https://huggingface.co/coolbeam/UniTex) |
| MaterialMVP | not stated (no LICENSE file) | Hunyuan3D-Paint-v2-1 (Tencent Hunyuan 3D 2.1 Community) | Hunyuan | Tencent licence excludes EU/UK/KR; paper-version weights never released | [README](https://github.com/ZebinHe/MaterialMVP), [LICENSE](https://huggingface.co/tencent/Hunyuan3D-2.1/blob/main/LICENSE) |
| Paint3D | Apache-2.0 | Apache-2.0 | SD + ControlNets (OpenRAIL-M era) | None on licence; dated (2024-04), Kaolin 0.13 + PyTorch3D, albedo only | [README](https://github.com/OpenTexture/Paint3D), [HF](https://huggingface.co/GeorgeQi/Paint3d_UVPos_Control) |
| TexGaussian | no LICENSE file | not stated | own (octree 3DGS) | No licence; nvdiffrast + CUDA splat rasterizer | [README](https://github.com/ymxbj/TexGaussian) |
| TexPainter | MIT | n/a (uses SD-depth) | SD-depth (OpenRAIL-M) | None on licence; 24 GB requirement; RGB | [README](https://github.com/Quantuman134/TexPainter) |
| SyncMVD | MIT | n/a | SD1.5 + ControlNet 1.1 (OpenRAIL-M) | None on licence; SD1.5 quality; Linux/WSL | [README](https://github.com/LIU-Yuxin/SyncMVD) |
| MVPaint | none shown | Dropbox, none shown | MVDream + SyncMVD (SD) | No licence; "preliminary" release 2025-07 | [README](https://github.com/3DTopia/MVPaint) |
| RomanTex | none | none | — | No code or weights | [README](https://github.com/oakshy/RomanTex) |
| Material Anything | MIT | Apache-2.0 (estimator) | SD 2.1 (OpenRAIL-M) | None on licence; 1K maps; Objaverse-derived Material3D (licence unstated) | [README](https://github.com/3DTopia/MaterialAnything), [HF](https://huggingface.co/xanderhuang/material_estimator), [paper](https://arxiv.org/html/2411.15138) |
| PBR-Boost | Apache-2.0 | HF MonoIntrinsics (licence not read) | SD fine-tune | None on licence; semi-automatic RM; nvdiffrast ack.; 2024 torch 1.13 | [README](https://github.com/snowflakewang/PBR_Boost_3DGen) |
| Hi3DGen | MIT | not stated | TRELLIS | No texturing stage; needs xformers | [README](https://github.com/Stable-X/Hi3DGen) |
| Step1X-3D texture | Apache-2.0 | Apache-2.0 | SDXL via MV-Adapter code | Custom rasterizer/renderer "adapted from Hunyuan3D 2.0" (Tencent code); 27 GB | [README](https://github.com/stepfun-ai/Step1X-3D), [HF](https://huggingface.co/stepfun-ai/Step1X-3D) |
| TripoSG / TripoSF | MIT | not stated | — | Geometry only, no texturing | [TripoSG](https://github.com/VAST-AI-Research/TripoSG), [TripoSF](https://github.com/VAST-AI-Research/TripoSF) |
| Meta AssetGen 2 / TextureGen | — | not released | — | Not released | [Meta blog](https://developers.meta.com/horizon/blog/AssetGen2) |
| Stability SV3D | Stability Community | gated, `sv3d-nc-community` | SVD | Stability Community Licence not on allowed list; no mesh texturing | [HF](https://huggingface.co/stabilityai/sv3d) |
| Stability SPAR3D | Stability Community (USD 1 M cap) | gated | SF3D | Not on allowed list; generator only | [LICENSE.md](https://raw.githubusercontent.com/Stability-AI/stable-point-aware-3d/main/LICENSE.md) |
| Pandora3D | "MIT … with additional restrictions" | not stated | not stated | Use "within the European Union" prohibited | [README](https://github.com/Tencent/Tencent-XR-3DGen) |
| TexFusion / Diffusion Texture Painting (NVIDIA) | — | — | SD | No code ever released | [TexFusion page](https://research.nvidia.com/labs/toronto-ai/texfusion), [DTP page](https://research.nvidia.com/labs/toronto-ai/DiffusionTexturePainting) |
| Tex4D | Apache-2.0 | — | video diffusion (unnamed) | Mesh *sequences*; inference code still TODO | [README](https://github.com/ZqlwMatt/Tex4D) |
| PrimX / 3DTopia-XL | Apache-2.0 | not stated | own DiT | Generator, not retexture; xformers required | [README](https://github.com/3DTopia/3DTopia-XL) |
| Hi3D | MIT | not stated | SVD | No retexture; 80 GB | [README](https://github.com/yanghb22-fdu/Hi3D-Official) |
| MIDI-3D | Apache-2.0 | not stated | TRELLIS + MV-Adapter | Scene generator; textures = MV-Adapter at ~30 GB | [README](https://github.com/VAST-AI-Research/MIDI-3D) |
| LHM / LHM++ | Apache-2.0 | not stated | SMPL-X driven | SMPL-derived → banned; humans only | [README](https://github.com/aigc3d/LHM) |
| UltraTex | MIT | **not stated** | FLUX.1-dev (NC) / FLUX.2-klein-9B (NC) | Both bases non-commercial; no 4B/Apache variant ("9B LoRA won't load into it") | [README](https://github.com/yiboz2001/UltraTex), [klein-9B HF](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) |
| LumiTex | Apache-2.0 | FLUX-MV-Shaded (FLUX.1-dev derived) | FLUX.1-dev (NC) | README: FLUX and Hunyuan3D-2.1 renderer "non-commercial"; Hunyuan code → EU issue | [README](https://github.com/LumiTexPBR/LumiTex) |
| NaTex | unknown (repo 404 here) | none | own DiT | Tencent Hunyuan affiliation; no licence/weights visible | [project page](https://natex-ldm.github.io/), [gittrend](https://gittrend.io/repo/Zeqiang-Lai/NaTex) |
| LaFiTe / PixTex (VAST) | — | — | own | Paper only, no code | [HF papers](https://huggingface.co/papers/2512.04786), [ACM DL](https://dl.acm.org/doi/10.1145/3799902.3811120) |
| MV2UV / MatLat | — | — | SDXL / SD-VAE fine-tune | Paper only, no code found | [arXiv 2603.15436](https://arxiv.org/abs/2603.15436), [MatLat](https://arxiv.org/html/2512.17302v1) |
| MVPainter | Apache-2.0 | not stated (shaomq/MVPainter) | UNet+ControlNet (base unnamed) | Weights licence unstated; acknowledges Hunyuan3D-1/-2 (possible code reuse) | [README](https://github.com/amap-cvlab/MV-Painter), [LICENSE](https://github.com/amap-cvlab/MV-Painter/blob/main/LICENSE) |
| PBR3DGen | none | not released | InstantMesh-based | Checkpoints withheld; Tencent Hunyuan affiliation | [README](https://github.com/XiaokangWei/PBR3DGen) |
| Seed3D 1.0/2.0 | — | API only | — | Hosted only | [Seed blog](https://seed.bytedance.com/en/blog/seed3d-1-0-released-generate-high-fidelity-3d-models-from-single-images-featuring-sota-texturing) |
| Hunyuan3D-Paint 2.1 | Tencent Hunyuan 3D 2.1 Community | same | Hunyuan | EU/UK/KR excluded; >1 M MAU clause; 21 GB | [LICENSE](https://huggingface.co/tencent/Hunyuan3D-2.1/blob/main/LICENSE), [README](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) |
| TRELLIS.2 / Pixal3D (incumbent) | MIT | MIT | own | No text/style conditioning upstream in 2026; Pixal3D added multi-view inference Sep 2026 | [TRELLIS.2](https://github.com/microsoft/TRELLIS.2), [Pixal3D](https://github.com/TencentARC/Pixal3D) |

- Training-data provenance (all candidates): Objaverse subsets everywhere (TEXGen 120K, Material Anything 80K, TexGaussian-PBR, MV-Adapter Ortho10View/Rand6View, LaFiTe ~1M incl. Objaverse-XL + TexVerse, UltraTex G-buffer TexVerse 268K+); the survey notes some pipelines filter "NoAI"-tagged assets and keep only redistributable CC licences, and calls for rights-cleared benchmarks; no candidate publishes a per-asset licence manifest — [survey §5](https://arxiv.org/html/2606.00137v1), [TEXGen](https://arxiv.org/html/2411.14740), [Material Anything](https://arxiv.org/html/2411.15138), [UltraTex](https://arxiv.org/html/2609.23169), [LaFiTe](https://huggingface.co/papers/2512.04786)
- TexVerse itself: 858K Sketchfab models, 158K with PBR — [survey §5](https://arxiv.org/html/2606.00137v1), [TexVerse arXiv 2508.10868](https://arxiv.org/html/2508.10868v1)

### Inferences
- For the project's policy ("report code, weights and training data separately"), the shortlist with zero licence blockers is: MV-Adapter (after nvdiffrast/CV-CUDA swap), Material Anything, Paint3D, SyncMVD, TexPainter, PBR-Boost. Of these only Material Anything and PBR-Boost give PBR, only MV-Adapter and Paint3D exceed 1K, and none is maintained in 2026 (latest dated activity: MV-Adapter 2025-06, Material Anything 2025-06, Paint3D 2024-04, SyncMVD/TexPainter 2024).
- Step1X-3D and MVPainter are "Apache on paper" but inherit Tencent rasterizer/renderer code; they need the same custom-rasterizer swap the project already made for TRELLIS.2 before they would be clean.
- The practical recommendation that follows from the data: keep TRELLIS.2/Pixal3D as the PBR base, and if a multi-view detail pass is wanted, build it on MV-Adapter's SDXL geometry adapter (or an SDXL/Z-Image/klein-4B ControlNet, already in the stack) in front of the project's own UV bake; watch UltraTex for a klein-4B LoRA and NaTex/LaFiTe/PixTex for code drops.

### Gaps
- Licence text of the HF weights for MV-Adapter (`huanngzh/mv-adapter`), MonoIntrinsics, shaomq/MVPainter and ModelScope UltraTex was not read directly (ModelScope page returned only a title).
- No source states which Objaverse licence subsets (CC-BY vs CC-BY-NC) each model trained on; "ripped game assets" concerns are not addressed by any candidate's documentation.
- Whether the Hunyuan3D-2.0 code licence (governing Step1X-3D's and LumiTex's vendored rasterizer) also carries the EU exclusion was not verified in this session (only 2.1 was).
