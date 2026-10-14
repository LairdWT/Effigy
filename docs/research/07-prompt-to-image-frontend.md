# Research 07: Prompt → candidate images → pick (the front end)

> Status: research notes, 2026-10-03. Compiled from a delegated survey. We re-verified the
> following ourselves:
> - HF licences: Z-Image-Turbo, Z-Image-Turbo-Fun-ControlNet-Union, FLUX.2-klein-4B, Qwen3.5-4B,
>   Qwen-Image-Edit-2511, AnyPose and the Multiple-Angles LoRA are all **Apache-2.0**;
>   Qwen-Image-2.1 is **qwen-research (NC)**.
> - `diffusers` main ships `pipeline_z_image{,_controlnet,_img2img,_inpaint}.py` and
>   `pipeline_flux2_klein*.py`.
>
> **All timings below are estimates** for the RTX 5080 Laptop (≈ desktop RTX 5070 class; plan on
> ~14.5 GB usable VRAM).

## 1. Bottom line (ponytail-sized)

| Need | MVP choice | Why | Later / upgrade |
|---|---|---|---|
| Text → image | **Z-Image-Turbo** (Apache-2.0, 6B, 8 steps) via **`diffusers` `ZImagePipeline`** in the existing `.venv-ml`, bf16 + `enable_model_cpu_offload()` | Best anatomy and hands among Apache models; diffusers is already in the venv, so no ComfyUI and no Nunchaku | FP8/NVFP4 weights for speed (Nunchaku FP4 or ComfyUI cu130) once timings are measured; **FLUX.2-klein-4B** (Apache, faster, wider illustrative range, worse hands) as a style option |
| Pose control (characters) | Prompt-only A-pose template first | Might be enough; test it | **Z-Image-Fun-ControlNet-Union 2.1** (Apache; Turbo and Base variants, "lite" low-VRAM versions; pose/depth/canny + inpaint) with a **shipped synthetic A/T-pose skeleton PNG**, strength 0.65–0.8 |
| Prompt enhancement | **Templates per category** (character / prop / creature), filled from the user's text, plus 4 hand-written variant suffixes | Covers most of it with zero models (YAGNI) | **Qwen3.5-4B** (Apache, vision-capable) as a step that writes the brief JSON + 4 prompt variants |
| Candidate scoring | **BiRefNet-mask CV gates** (BiRefNet is already loaded for prep): one component, margin to the border, fill ratio, uniform background | ~0.5 s per image, no extra model | Qwen3.5-4B VQA yes/no checks (same model as the enhancer); **DWPose (Apache, ONNX)** for A/T-pose angles in Phase 2 |
| Edit the chosen image | Z-Image img2img / inpaint (diffusers) | Same model, same venv | **Qwen-Image-Edit-2511** (Apache, 20B, needs Q4/FP4 on 16 GB) + **AnyPose** (re-pose) + **Multiple-Angles LoRA** (side/back views). Bake-off candidate: **HiDream-O1-Image** (MIT, 8B pixel-native; instruction edit + multi-reference + **skeleton conditioning**; FP8 ≈ 10–16 GB; ComfyUI/DiffSynth, no diffusers pipeline yet) |

**Don't ship** (licence):
- FLUX.2-klein-9B, FLUX.2-dev, FLUX.1-dev/Krea-dev (NC)
- **Qwen-Image-2.1** (Sep 2026, qwen-research NC, despite its native RGBA output)
- Ideogram 4 weights (NC)
- Krea 2 (revenue/seat cap + mandatory filter)
- NoobAI-XL (NC incl. outputs)
- Pony V7 (no apps/services)
- Wonder3D/Era3D (AGPL)
- RMBG-2.0 (NC)
- CMU OpenPose models (NC), Ultralytics YOLO-pose (AGPL)

**LoRAs inherit their base model's licence.** Most character-sheet LoRAs target klein-9B (NC).
The clean path is to train our own on Z-Image or klein-4B *base*.

## 2. Text-to-image candidates (16 GB fit)

| Model | Licence | Fit on 16 GB | Est. 4×1024² on the 5080 Laptop | Notes |
|---|---|---|---|---|
| **Z-Image-Turbo** | Apache-2.0 | bf16 with CPU offload; FP8 ≈ 6 GB DiT; NVFP4 ≈ 4.5 GB | ~16–28 s warm (FP8/NVFP4); bf16+offload slower (measure) | **Low seed diversity**: vary the *prompt* (4 variants) or inject noise into the text embeddings. Turbo ignores negative prompts (no CFG), so phrase constraints positively |
| FLUX.2-klein-4B | Apache-2.0 | FP8/NVFP4 published by BFL | ~6–14 s | text-to-image + edit + multi-reference in one model |
| Qwen-Image-2512 | Apache-2.0 | 20B, only quantized (Nunchaku NVFP4 / GGUF Q4) | ~35–60 s (Lightning 4/8-step) | best adherence + biggest Apache ecosystem; quality tier |
| HiDream-O1-Image, ERNIE-Image, Boogu-Image | MIT / Apache / Apache | FP8 likely | – | watch-list (2026, unverified for 3D refs) |
| Illustrious-XL v2.0 (SDXL) | OpenRAIL++-M | 8 GB | ~6–9 s each | optional anime pack; understands booru tags like `a-pose`, `simple background` |

## 3. What a "3D-ready" image is (drives templates and gates)

These facts about TRELLIS.2's preprocessing set the requirements:
- The alpha cut is at **0.8**, so wispy or semi-transparent parts get dropped.
- It takes a **tight 1.0× bbox crop**, premultiplies onto **black** (dark rims merge into it), and
  caps at 1024 px.
- **Never feed a multi-panel or turnaround sheet to the single-image path.**

Research:
- **Cue3D** (arXiv 2511.22121): shading matters more than texture. Use **soft key light, not flat
  light**. Plausible shapes and standard viewpoints help.
- Hunyuan's need for a delight model shows that baked lighting leaks into textures.
- No study ties image properties to TRELLIS.2 quality, so **log picks and outcomes and calibrate**.

**Prompt templates** (field reference: hec-ovi/text-to-3D-skill, FLUX.2-klein → TRELLIS.2):
- **Character:** "full body, symmetric neutral A-pose, feet side by side, straight arms about 45°
  from the body with a visible gap, empty open hands, nothing over the shoulders, front view, soft
  key light, plain light-grey background, no cast shadow, single character".
- **Prop:** "single complete object centred, three-quarter view, even soft studio light, flat plain
  light-grey background, no cast shadow, product photograph".
- **Background shade:** contrast with the object (mid-grey for white objects).

**Gates:** H = hard (reject or flag), S = soft (ranking). Thresholds are starting values to
calibrate.

| Gate | Check | How |
|---|---|---|
| H | exactly one foreground component (largest ≥ 97% of the mask; specks < 0.1% ignored) | BiRefNet mask |
| H | ≥ 3% margin to every border; object's longest side 55–90% of the frame; ≥ 1024 px long side | mask bbox |
| H | uniform background (σ < ~8/255 outside the dilated mask) | pixels |
| H (later) | no text, watermark or panels | VLM / Florence-2 |
| H (characters, Phase 2) | full body, front-facing, A-pose (arms 30–60°) or T-pose (80–100°), arm–torso gap, feet apart, one person | DWPose |
| S | shading present (fg luminance variance above a floor), no floor shadow, few semi-transparent pixels | pixels |
| S | prompt match | VQAScore with Qwen3.5-4B, later |
| S | aesthetics | ImageReward (Apache), tie-breaker only. Pretty-image scorers punish plain product shots |

## 4. Flow and timing (estimates, 5080 Laptop)

1. Prompt → template (MVP) or LLM brief (later, 2–4 s GPU / 15–25 s CPU).
2. Load Z-Image (10–25 s cold) → **4 candidates**, shown as they finish (~16–28 s warm with FP8/NVFP4).
3. BiRefNet gates (< 0.5 s per image) → ranked 2×2 grid with pass/fail badges.
4. "4 more" reuses the loaded model (one `steps.concepts` call can loop until the user picks).
5. Pick → optional img2img / inpaint edit → **RGBA export** (our BiRefNet mask, so TRELLIS.2 skips
   its own background removal).
6. The step process exits (VRAM freed), then `steps.generate` runs.

**RAM (32 GB):** Windows ~6–8 GB + one model's offloaded weights + the LLM if used (~4 GB Q4).
That's fine as long as only one heavy stage is alive, which the subprocess-per-step design
guarantees. Set the NVIDIA "CUDA Sysmem Fallback Policy" to *Prefer No Sysmem Fallback*, so OOMs
fail fast instead of silently spilling into RAM (behaviour on laptops unverified).

## 5. UX patterns worth copying
- **Meshy:** batch grid, Auto-Refine prompt toggle, one-click "Image to 3D", A/T-pose + multi-view toggles.
- **Invoke:** star, "Use prompt / Use seed / Remix", metadata embedded in the PNG.
- **muse-character-sheet-klein:** per-view Confirm / New seed, lock confirmed views.
- **Gradio mapping:** `gr.Gallery` (select event), per-slot reroll button, editable prompt
  `Textbox`, a pose/style `Radio` filled from the template or brief.

## 6. Unverified / risky
- All 5080-Laptop timings.
- Nunchaku: install docs list sm_120 (torch ≥ 2.7, CUDA ≥ 12.8) and Windows wheels exist for v1.2.1; later
  releases are nightlies only, so it's an optional accelerator.
- BFL's official `FLUX.2-klein-4b-nvfp4` runs on an RTX 5080 but needs torch ≥ 2.9.1 + cu130 (we pin cu128),
  so FP8 is the safe first optimization.
- **Z-Image-Edit is still unreleased** (Oct 2026). Qwen-Image-Layered (Apache) can split an image into RGBA
  layers, which is an alternative alpha extractor to BiRefNet if needed.
- AnyPose and Multiple-Angles quality on stylized art.
- ~~Real-ESRGAN / UltraSharp weight licences~~: Real-ESRGAN x4plus checked 2026-10-06 (BSD-3-Clause, the repo LICENSE covers the released weights; `docs/bench/m24.md`); UltraSharp not used.

## Sources
github.com/Tongyi-MAI/Z-Image · huggingface.co/Tongyi-MAI/Z-Image-Turbo · huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union ·
github.com/huggingface/diffusers (pipelines/z_image, pipelines/flux2) · huggingface.co/black-forest-labs/FLUX.2-klein-4B ·
bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence · huggingface.co/Qwen/Qwen-Image-2512 · huggingface.co/Qwen/Qwen-Image-Edit-2511 ·
huggingface.co/Qwen/Qwen-Image-2.1 · huggingface.co/Qwen/Qwen3.5-4B · huggingface.co/lilylilith/AnyPose ·
huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA · github.com/nunchaku-ai/nunchaku (issue #888) ·
blog.comfy.org/p/new-comfyui-optimizations-for-nvidia · huggingface.co/HiDream-ai/HiDream-O1-Image · huggingface.co/baidu/ERNIE-Image ·
github.com/boogu-project/Boogu-Image · huggingface.co/krea/Krea-2-Turbo · github.com/hec-ovi/text-to-3D-skill · arxiv.org/html/2511.22121 (Cue3D) ·
arxiv.org/abs/2410.00890 (Flex3D) · github.com/linzhiqiu/t2v_metrics · github.com/IDEA-Research/DWPose · github.com/THUDM/ImageReward ·
huggingface.co/ZhengPeng7/BiRefNet · docs.meshy.ai/en/api/text-to-image · invoke.ai/features/gallery · github.com/muse-collective-26/muse-character-sheet-klein ·
notebookcheck.net/Nvidia-GeForce-RTX-5080-Laptop-Benchmarks-and-Specs.934946.0.html
