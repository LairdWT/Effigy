# Research 05: Auto-rigging, skinning and animation

> Status: research notes, 2026-10-03. Compiled from a delegated repo/licence survey. The key
> recommendations were re-verified by us: SkinTokens (MIT, ≥14 GB, `--use_skeleton`), Kimodo
> (Apache-2.0 code, SOMA checkpoints under the NVIDIA Open Model License, <3 GB with the text
> encoder on CPU), and Mesh2Motion (MIT code, CC0 rigs/animations). Star counts are approximate.

> **Owner decision (2026-10-03):** assets ship in a commercial game, so **Make-It-Animatable (v1 and v2)
> is excluded** (Mixamo-trained / Hunyuan-based), as is everything Hunyuan (HY-Motion). See PLAN §6.

## 0. Review update (2026-10-03, verified)

- **SkinTokens skin-only mode (`--use_skeleton`) works only with the 52-joint Mixamo/VRoid template**
  (22 body + 30 finger joints; issue #12, unanswered). Extra chains (twist, scapula, costume) shift or
  drop skin columns. → Our canonical rig is exactly that template; strip extra joints before skinning.
- **GPL provenance:** `src/model/michelangelo` is copied from UniRig, whose subtree LICENSE is GPL-3.0
  (verified; upstream NeuralCarver/Michelangelo is GPL-3). SkinTokens' root LICENSE says MIT; issue #9
  (Aug 2026) asking which files are GPL is unanswered. → **Never import SkinTokens in-process**: own
  venv + subprocess, like Blender.
- **VRAM:** the README's "≥14 GB" is unsupported by the code: weights are 1.62 GB (Qwen3-0.6B + point
  encoder + FSQ-CVAE, bf16); a ComfyUI port states ~4 GB. No low-VRAM flags exist. **Measure** with
  `--num_beams 1` on a 50k-vertex proxy. `--use_skeleton` isn't lighter (same model, same memory).
- **flash-attn is a hard dependency upstream** (no SDPA fallback). The MIT **NoBlender** port makes it
  optional and replaces the `bpy_server.py` HTTP subprocess with trimesh + pygltflib I/O. Use that port.
- **trellis2.c `tokenskin-rig`**: full rig only (no skeleton input), no VRAM/quality data, no user reports.
  Not a skin engine for us. `skintokens-ue` (Apache, GGML, Vulkan) has a `skin` mode but is Linux-only
  pre-alpha; revisit in 2027.
- **UniRig** has the same GPL subtree; PR #70 (Windows + RTX 50, SDPA shim) reports a **3.4 GB** skinning
  peak on a 5060, so it's a viable 8–12 GB fallback if run from that PR, also as a subprocess.
- **Make-It-Animatable v2 is excluded** (Hunyuan3D-2.1 ShapeVAE → EU/UK/KR exclusion). v1 stays opt-in.
- **Retarget extension verified** from the v5.2.0 zip: GPL-3.0-or-later, Blender ≥ 5.0, monthly releases,
  16 presets (Mixamo, Unreal Mannequin, VRoid, Rigify…), operators callable headless
  (`armature.retarget_constrain_to_armature`, `armature.retarget_bake_constrained_actions`,
  `object.retarget_convert_bone_names`, `object.retarget_guess`). Blender 5.2/5.3 still have no native
  retargeting. **BVH-Motion-Retargeter** (MIT, Blender 4.2+) for BVH → Mixamo/UE5 ingestion.
- **Clips:** Quaternius UAL 2 (CC0, 130+, UE5-style 65-joint names → remap), **KayKit** (CC0, 150+),
  Mesh2Motion (CC0, custom names), 100STYLE (CC BY) via `orangeduck/100style-retarget` FBX.
  **Bones-SEED is not permissive** (academia / <$1M startups only). CMU terms to re-verify before bundling.
- **MoCapAnything V2** (SIGGRAPH Asia 2026; MIT code and weights): video + reference skeleton → BVH on any
  rig. Better fit than SAM 3D Body for our Mixamo rig. 3DGenStudio integrated it in Aug 2026.
- **Deformation QA:** no reference-free open scorer. Re-implement (~50 lines): weights sum to 1, ≤ 4
  influences, no influence from disconnected islands, L/R asymmetry, pose-perturbation test (10 poses,
  ±10°: volume change, max per-bone stretch, self-intersections), joints-inside-mesh. Run it on both
  SkinTokens and the Blender bone-heat result and keep the better one.

## 1. Bottom line

- **Template-first for humanoids.** Meshy and Tripo use templates with standard
  (Mixamo-compatible) bone names, so their rigs work with existing animation libraries. We do the
  same: **fit a canonical skeleton** (automatic keypoints plus draggable markers), then compute
  **skin weights** with a learned model or a robust classical fallback.
- **Learned skinning:** **SkinTokens/TokenRig** (VAST, Feb 2026, MIT) on ≥14 GB GPUs. Its
  skin-only mode skins *our* template skeleton. **UniRig** (MIT, ≥8 GB) is the lighter
  fallback for generic objects.
- **Classical fallback that always works:** bone-heat weights on a **watertight voxel proxy**,
  then **Robust Skin Weights Transfer** (MIT) onto the final mesh.
- **Animations:** our own retargeter onto the canonical skeleton. **Bundle only CC0/CC-BY data**
  (Quaternius UAL, Mesh2Motion, 100STYLE). Text-to-motion via **NVIDIA Kimodo** (commercially
  usable SOMA checkpoints).
- **Exclude from the product:** SMPL/SMPL-X/AMASS/HumanML3D-trained models, GVHMR, NVIDIA GEM,
  RigAnything (all non-commercial), Anymate (no licence), and HY-Motion (Tencent territory clause,
  so plugin only if at all).

## 2. Learned riggers

| Model | Licence (code / weights) | VRAM | Scope | Output | Notes |
|---|---|---|---|---|---|
| **SkinTokens / TokenRig** (arXiv 2602.04805, Feb 2026) | MIT / MIT | ≥14 GB | humanoid, quadruped, anime, creatures | GLB skeleton + skin | `--use_skeleton` = skin-only on a given armature. Imports `bpy>=4.2` in-process (GPL); an MIT no-Blender port exists (`ComfyUI-SkinTokens-NoBlender`). Training data includes VRoid Hub and ModelsResource (provenance risk). |
| **UniRig** (SIGGRAPH 2025) | MIT / MIT | ≥8 GB | generic | FBX/GLB, free-form skeleton (no standard names) | Known skin-weight failures (NaN, wrong weights). spconv has no CUDA 12.8 build, which blocks RTX 50. `bpy==4.2` in-process. |
| **Make-It-Animatable** (CVPR 2025) | MIT / Apache-2.0 | small, <1 s | humanoid only | Mixamo 52-bone rig, **pose → rest (T-pose) reset** | **Trained on Mixamo** (Adobe terms ban ML training on Mixamo content). v2 uses the Hunyuan3D-2.1 VAE (territory clause). Opt-in only, licence-flagged. |
| Puppeteer (NeurIPS 2025) | Apache-2.0 | n/a | generic + video-guided animation | skeleton + skin | CUDA 11.8 / torch 2.1 stack, no RTX 50 without porting |
| MagicArticulate (CVPR 2025) | Apache-2.0 | 4.6 GB | generic | skeleton | superseded by Puppeteer |
| AniGen (SIGGRAPH 2026) | MIT | ≥18 GB, Linux | image → rigged mesh (TRELLIS v1 based) | GLB | alternative path, doesn't rig existing TRELLIS.2 meshes |
| RigAnything | Adobe Research (NC) | – | – | – | ✘ |
| Anymate | no LICENSE | – | – | – | ✘ |
| RigNet | GPL-3, 2020 | – | – | – | baseline only |
| Hunyuan3D-Studio rig modules, HumanRig, DRiVE, AnimaX | not released | – | – | – | watch |

**2026 work to watch**
- Rigel3D: joint mesh+rig generation with open-vocabulary joint labels.
- Animator-Centric Skeleton Generation (CVPR 2026).
- **OmniFaceRig**: automatic face rigs with up to 155 blendshapes. Relevant for facial animation later.
- Make-It-Poseable: skinning-free posing of fused meshes.

## 3. Classical and template tools

- **Blender bone heat ("Automatic Weights")** fails on non-manifold or multi-island generated
  meshes. Run it on a **voxel-remeshed watertight proxy**, then transfer the weights.
- **Robust Skin Weights Transfer** (Epic, SIGGRAPH Asia 2023, MIT, libigl). Inpaints weights where
  the transfer is unreliable. Core of our fallback.
- **Mesh2Motion** (MIT code, **CC0 rigs and animations**). Templates: human, fox (quadruped),
  bird, dragon, spider, snake, kaiju. **Best bundleable multi-species template and clip source.**
- **Mixamo-style marker rigging:** no mature open implementation exists, so we build it:
  1. Render orthographic front and side views.
  2. Detect 2D keypoints with **RTMPose/DWPose (Apache-2.0)**, or let the user click.
  3. Ray-cast each keypoint and take the mid-depth between entry and exit.
  4. Fit the template skeleton, with **MHR (Apache-2.0)** or **SOMA-X (Apache-2.0)** body
     proportions as a prior.
- **SMPL/SMPL-X fitting** is non-commercial, so ✘. Use MHR or SOMA-X as permissive body priors instead.
- **`bpy` on PyPI** is now 5.2.x and requires **Python 3.13**. UniRig and SkinTokens pin bpy 4.2
  (Python 3.11), so the Python versions conflict. That's another reason for per-engine
  venvs, and for running Blender as a subprocess.

## 4. Animation sources

| Source | Licence | Ship in app? |
|---|---|---|
| Quaternius Universal Animation Library 1/2 (250+ clips, UE/Unity/Godot-compatible rig) | CC0 | ✔ |
| Mesh2Motion clips (human + quadruped/bird/dragon/spider/snake) | CC0 | ✔ (main non-human source) |
| 100STYLE (100 locomotion styles, BVH) | CC BY 4.0 | ✔ with attribution |
| CMU mocap | Free use, **no resale of the data even converted** | Optional download/importer |
| Mixamo | Royalty-free in projects, **no redistribution, Adobe ID, ML training banned** | **User-import only** (support `mixamorig:`) |
| Truebones Zoo | redistribution prohibited | User-import only |
| Bandai Namco Research Motion, LAFAN1, AMASS, HumanML3D | NC / NC-ND | ✘ |
| Bones-SEED | gated custom licence | review first |

**Text-to-motion**
- **Kimodo** (NVIDIA, Mar 2026, updated Sep 2026). Apache-2.0 code; **SOMA checkpoints under the
  NVIDIA Open Model License (commercial OK)**; the SMPL-X checkpoint is R&D-only (✘). ~17 GB, or
  **<3 GB with `TEXT_ENCODER_DEVICE=cpu`**. 30 fps, up to 10 s, with keyframe/end-effector/path
  constraints. Linux native, Windows via Docker (we'd need our own Windows env).
- **HY-Motion 1.0** (Tencent): territory clause (no EU/UK/KR). ✘ by default.
- MoMask, MDM, MotionGPT, T2M-GPT are HumanML3D-trained (AMASS, non-commercial). ✘ for product use.
- UniMate (SIGGRAPH Asia 2026): arbitrary skeletons (quadrupeds). Weights licence unclear; watch.

**Video-to-motion:** **SAM 3D Body** (Meta, SAM License; commercial OK except military/ITAR) →
MHR output plus temporal smoothing. It's the only clean option; GVHMR, WHAM, 4DHumans and GEM are
all non-commercial or SMPL-bound.

**Retargeting:** Rokoko needs a login. Auto-Rig Pro is commercial. Blender 5.x has no built-in
retargeting and broke older add-ons (removed `action.fcurves`). **Update ([research 08](08-blender-integration.md)):**
the **Retarget extension** (Expy Kit fork, GPL-3, Blender 5.0+, Mixamo/UE/VRoid presets) runs in our
Blender subprocess, so **use it first** (ponytail). Fallback only if it falls short: our own numpy retargeter:
1. Align rest poses.
2. Transfer local rotations through a bone-mapping table.
3. Scale hip translation by the leg-length ratio.
4. Optionally clean up foot contacts with IK.

Mapping tables: Quaternius UAL, Mesh2Motion, Mixamo, CMU BVH, SOMA (Kimodo), MHR (SAM 3D Body).

## 5. Formats and the canonical skeleton

- **Canonical humanoid skeleton:** Mixamo names (Hips, Spine, Spine1, Spine2, Neck, Head,
  {Left,Right}{Shoulder,Arm,ForeArm,Hand,UpLeg,Leg,Foot,ToeBase}, plus optional fingers), a
  `root` bone, and an optional `mixamorig:` prefix. **Rest pose is T-pose** (best for Unity
  Humanoid); A-pose input is re-posed to T at the rest-pose step.
- **Export profiles:**
  - **Mixamo**
  - **UE5 Manny** names (root, pelvis, spine_01–05, clavicle_l, upperarm_l, lowerarm_l, hand_l,
    thigh_l, calf_l, foot_l, ball_l, …)
  - **Unity Humanoid** (auto-maps either naming; ~15 required bones)
  - optionally **VRM**
- **Constraints:**
  - glTF skins use 4 influences per set, and the UE5 glTF importer truncates to 4, so **always
    prune to 4 normalized influences**.
  - Metres.
  - No leaf bones.
- **glTF** is native in Godot. Unity needs glTFast, and there's no practical Humanoid avatar
  from glTF. **FBX is still required for Unity/Unreal humanoid workflows** → written by **Blender
  as a subprocess**: the Autodesk FBX SDK is proprietary, and ufbx only reads.

## 6. Recommended stack

**MVP (humanoid):**
1. Pre-generation **A-pose normalization** of the input image (see §7).
2. Generate the mesh, clean it up, retopologize.
3. **Fit the canonical skeleton**: automatic 2D keypoints → 3D mid-depth → MHR/SOMA prior, plus a
   Mixamo-style marker UI for correction.
4. Skin weights:
   - ≥14 GB: **SkinTokens `--use_skeleton`** (Blender-free integration path).
   - <14 GB or failure: **bone heat on a watertight proxy, then Robust Weight Transfer**.
5. Prune to 4 influences and normalize.
6. Run the **automatic deformation QA** (§7) and flag bad joints in the marker UI.
7. Animations: bundled CC0 clips via our retargeter. Export GLB, plus FBX via Blender.

**v1:**
- **Generic and creatures**: SkinTokens full rig, with UniRig as the ≥8 GB fallback.
- **Quadrupeds and birds** on Mesh2Motion templates, using the same marker fitting.
- **Kimodo text-to-motion** (SOMA → canonical retarget).
- **MIA as an opt-in "fast pose-reset" mode**, flagged for its Mixamo training-data provenance.

**Later:**
- SAM 3D Body video-to-motion.
- Face rigs (blendshapes).
- Spring bones for hair and capes.
- UniMate once its licence is clarified.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| TRELLIS.2 keeps the input pose; action poses break fitting and give a bad rest pose | **Canonicalize before 3D**: re-pose the reference image to an A-pose (arms ~30–45° down from horizontal, legs slightly apart, hands open, nothing held). Use **Qwen-Image-Edit-2509/2511 (Apache-2.0)** with pose/keypoint control, or CharacterGen/StdGEN (Apache-2.0) canonical multi-view. **Not FLUX Kontext-dev (NC).** |
| Fused limbs, mitten hands, hair or capes fused to the back → weight bleeding | Weights on a manifold voxel proxy + robust transfer. Left/right side masks and geodesic limits. Detect fused fingers → fall back to a 1–2-bone hand. Part segmentation to rigid-bind props. |
| Accessories (weapons, hats, skirts) | Rigid-bind to the hand/head bone. Spring bones later. |
| Licence provenance of training data | Per-model licence manifest with commercial/region flags in the UI. Bundle only CC0/CC-BY motion. |
| GPL from in-process `bpy` (UniRig, SkinTokens) | Use the pygltflib/trimesh path for GLB (MIT port exists). Use Blender only as an external process. |
| RTX 50 / CUDA ≥12.8 | Avoid CUDA 11.8 stacks (Puppeteer). Build our own spconv/flash-attn wheels or use SDPA. |
| VRAM stacking (TRELLIS.2 + SkinTokens 14 GB + Kimodo) | Sequential residency through the GPU scheduler. Kimodo text encoder on CPU. |
| Deformation quality is invisible until animated | **Automatic QA**: play a range-of-motion clip, measure triangle stretch, volume loss and self-intersection per joint, and show a heatmap before export. |

## Sources
github.com/VAST-AI-Research/SkinTokens · huggingface.co/VAST-AI/SkinTokens · arxiv.org/abs/2602.04805 ·
github.com/stevelittlefish/ComfyUI-SkinTokens-NoBlender · github.com/VAST-AI-Research/UniRig ·
github.com/jasongzy/Make-It-Animatable · github.com/Seed3D/Puppeteer · github.com/Seed3D/MagicArticulate ·
github.com/VAST-AI-Research/AniGen · github.com/Isabella98Liu/RigAnything · github.com/yfde/Anymate ·
github.com/zhan-xu/RigNet · arxiv.org/abs/2606.08043 (OmniFaceRig) · arxiv.org/abs/2605.13129 (Rigel3D) ·
github.com/scottpetrovic/mesh2motion-app · github.com/rin-23/RobustSkinWeightsTransferCode ·
github.com/facebookresearch/MHR · github.com/NVlabs/SOMA-X · pypi.org/project/bpy ·
github.com/nv-tlabs/kimodo · huggingface.co/nvidia/Kimodo-SOMA-SEED-v1.1 · github.com/Tencent-Hunyuan/HY-Motion-1.0 ·
github.com/Friedrich-M/UniMate · github.com/facebookresearch/sam-3d-body · github.com/zju3dv/GVHMR ·
quaternius.com/packs/universalanimationlibrary.html · zenodo.org/record/8127870 (100STYLE) ·
wwwimages2.adobe.com/content/dam/cc/en/legal/servicetou/Mixamo-Addl-Terms-en_US-20210623.pdf ·
huggingface.co/Qwen/Qwen-Image-Edit-2509 · github.com/hyz317/StdGEN · docs.unity3d.com/Packages/com.unity.cloud.gltfast@6.0 ·
godotengine.org/article/introducing-the-improved-ufbx-importer-in-godot-4-3 · meshy.ai/tutorials/character-auto-rigging-workflow ·
developers.tripo3d.com/en/docs/animations-rig.md
