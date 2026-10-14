# Research 06: Meshy feature parity, competitors, and existing local projects

> Status: research notes, 2026-10-03. Compiled from a delegated survey of docs.meshy.ai (API
> reference, changelog, pricing), competitor docs, and GitHub. We re-verified the licences and
> activity of 3DGenStudio, trellis2.c and Modly by cloning them. Secondary-source items are
> marked *(unverified)*.

## 1. Meshy (as of Sep 2026): the spec we imitate

The Meshy API parameters work as a ready-made option list. Models: Meshy-6 (Jan 2026),
Meshy-7 (Aug 2026), Meshy-7.1 (Sep 2026), and "Smart Topology" `meshy-t2` (clean, part-separated,
100–15k tris).

| Meshy feature | Key parameters (API) | Our local equivalent | Phase |
|---|---|---|---|
| **Image → 3D** | `model_type` standard/smart-topology, `geometry_resolution` standard/2k/4k, `should_texture`, `enable_pbr` (+normal, emission), `texture_resolution` 2k/4k/8k, `texture_prompt`, `texture_image_url` | TRELLIS.2 / Pixal3D, 512/1024/1536 presets per VRAM tier, PBR + baked normal/AO | MVP |
| Preview → Refine | preview (geometry) then refine (texture) | Fast 512 shape-only preview, then 1024/1536 + texture | MVP |
| Remesh | `topology` quad/triangle, `target_polycount` 100–300k, `decimation_mode` 1–4, `save_pre_remeshed_model` | CuMesh decimate (tri), quad remesher (quad), keep hi-poly | MVP (tri) / v1 (quad) |
| Pose | `pose_mode` ""/a-pose/t-pose | Image re-posing before generation (Qwen-Image-Edit + AnyPose LoRA, Apache-2.0) | v1 |
| Scale/origin | `auto_size`, `resize_height`, `origin_at` bottom/center | Height in metres plus origin options in cleanup; auto-size via a VLM later | MVP |
| Pre-processing | `image_enhancement`, `remove_lighting` | BiRefNet, crop, upscale; delight (StableDelight) | MVP / v1 |
| **Multi-image → 3D** | 1–4 images, first is the front (2–8 in the UI) | Pixal3D-MV (needs cameras) or TRELLIS.2 multi-view blending | v1 |
| **Text → 3D** | prompt ≤800 chars, preview/refine | Local T2I (Z-Image-Turbo / FLUX.2-klein-4B / Qwen-Image) → image→3D | MVP |
| Text → Image | `generate_multi_view`, `pose_mode`, `remove_background` | Same T2I with a "character template" prompt + Multiple-angles LoRA for turnarounds | MVP / v1 |
| **Retexture** | `text_style_prompt` / `image_style_url` / `multiview_image_urls`, `enable_original_uv`, `enable_pbr` | TRELLIS.2 shape-conditioned texturing (keeps UVs) and the text→image→texture path | v1 |
| Texture Edit / Smart Healing | masked inpaint from any view, seam-healing brush | Projection inpaint pass ([04 §4b](04-texturing.md)) + seam brush | v2 |
| UV Unwrap | ≤40k faces, triangulates | CuMesh/xatlas, Blender for seam-aware characters | MVP |
| **Rigging** | humanoid (API); humanoid + quadruped via markers (web); `height_meters`; faces +Z; ≤300k faces | Template skeleton fitting + markers + learned/classic skinning ([05](05-rigging-animation.md)) | v1 |
| **Animation** | 591-clip biped library, `action_ids` (merge ≤10), `post_process` change_fps/fbx2usdz/extract_armature; text-to-motion (Aug 2026) | CC0 libraries + retargeter; Kimodo text-to-motion | v1 / v2 |
| Export | glb, obj, fbx, stl, usdz, 3mf, blend | GLB native; FBX/USDZ/BLEND via Blender subprocess; STL/3MF via trimesh | MVP (glb/obj/stl), v1 (fbx/usdz) |
| 3D print | analyze/repair printability, multi-colour 3MF (`max_colors` 1–16), Auto Split with connectors | Watertight repair, wall thickness check, colour quantization → 3MF; part split later | v2 |
| Workspace | history, community, plugins (Blender, Unity, Unreal, Godot…), 3D Agent | Local library with versions, REST API, Blender add-on, MCP server | MVP / v2 |

Notable: Meshy dropped `symmetry_mode` ("no longer affects output"). Its rigging requires a
**+Z-facing humanoid** and recommends **remeshing before rigging**. Meshy itself makes T/A-pose
concept art with a hosted image model before 3D, which confirms our "canonicalize the image
first" approach.

## 2. Competitors (pipeline stages)

| Product | Notable stages |
|---|---|
| **Tripo** (VAST) | multiview (4 images), `quad` / `smart_low_poly` / `face_limit`, parts, PBR 8K, delight; rig types biped/quadruped/hexapod/octopod/avian/serpentine/aquatic with a **`spec: mixamo`** naming option. Open source: TripoSG (MIT, geometry only), TripoSF, UniRig/SkinTokens/AniGen (MIT) |
| **Rodin** (Hyper3D Gen-2/2.5) | 1–5 images, part-based generation, quad presets 4k/8k/18k/50k, **T/A-pose toggle**, delight |
| **Hunyuan3D 3.x / Studio** | hosted only. Studio paper: parts (P3-SAM/X-Part), **PolyGen autoregressive retopo**, semantic UV, PBR, auto rig/skin. Open: 2.0/2.1/2mv/Omni/Part-lite under a licence that **excludes the EU/UK/KR** |
| CSM Cube | turnaround-sheet input, "Image to Kit" parts, AI retopo, animation + text-to-animation |
| Kaedim | human-in-the-loop production assets, LODs |

## 3. Existing local / open projects (build vs. reuse)

| Project | Licence (verified) | What it covers | Use for us |
|---|---|---|---|
| **trellis2.c / "Trellis Studio"** (Wimacs, v0.1.0 Jul 2026) | **MIT** (deps MIT/MPL/zlib; weights keep their own licences, documented in THIRD_PARTY_NOTICES) | **Native CUDA/Vulkan, no Python**: `trellis2-image-to-gltf`, `pixal3d-image-to-gltf`, `trellis2-texture-mesh`, `trellis2-segment-mesh` (SegViGen), `tokenskin-rig` (TokenRig/SkinTokens), BiRefNet, Vulkan mesh postprocessor and **texture baker**, Windows installer | **Strong candidate for a native generation backend** (no wheel hell, no nvdiffrast, Vulkan → also AMD). Evaluate in Phase 0 against the Python path for quality, VRAM and speed |
| **trellis.cpp** (pwilkin) | MIT | GGML/GGUF port of TRELLIS.2 (+Pixal3D), CUDA/ROCm/Vulkan/Metal, Tauri app; 1024 cascade ≈16 GB, 512 ≈5.6 GB | Alternative native backend (quantized weights for 8 GB cards) |
| **Modly** (lightningpixel) | **MIT** | Electron desktop image→3D app with an **extension system** (`manifest.json` + generator) | Reference for our engine-manifest design |
| **3DGenStudio** (visualbruno) | **Custom "3D Gen Studio Community License"**: no selling, no SaaS, no paid bundles (outputs usable commercially) | Closest prior art: React/Three.js + Node + Python, ComfyUI-backed. Kanban/graph/batch, mesh editor (projection texturing, inpaint, paint, Auto UV, Auto Retopo, AutoRig via SkinTokens, weight paint), Kimodo, MoCapAnything, mesh2motion, SAM 3.1 segmentation, LOD/collision, MCP. Changes almost daily (2026-09-27) | **Learn from, don't fork** (non-OSI licence). Our differentiation: permissive MIT, no ComfyUI runtime, commercial-clean default profile, character-first guided pipeline |
| ComfyUI-Trellis2 (visualbruno) | MIT | TRELLIS.2 + multi-view + mesh texturing + hi→lo projection + Pixal3D MV, Windows wheels, FP8 | MIT reference code and wheel source |
| ComfyUI-TRELLIS2 (PozzettiAndrea) | MIT | gen, PBR, remesh, UV, export | Reference |
| ComfyUI core native TRELLIS.2/Pixal3D (Aug 2026) | GPL-3.0 | No nvdiffrast, no compiled CUDA extensions, remesh/decimate/unwrap/bake normal+AO | Algorithm reference only (GPL) |
| IgorAherne/TRELLIS.2-stableprojectorz | MIT | Windows one-click, 8 GB tuning, SPZ API | Wheel set and VRAM patches ([01](01-trellis2-deep-dive.md)) |
| StableProjectorz | AGPL-3.0 | Projection texturing app (Unity), Agent Bridge, MCP | Companion process only |
| Mesh2Motion | MIT code / CC0 assets | Open Mixamo alternative: templates, weights, clips | Bundle templates and clips |
| Hunyuan3D-2-WinPortable, Hunyuan3D-2GP, kijai wrapper | Tencent licence (EU/UK/KR excluded) | Hunyuan pipelines | Avoid by default |
| ComfyUI-3D-Pack | MIT | many models | Stale since Nov 2025, no TRELLIS.2 |
| Pinokio scripts | various | one-click installers | The TRELLIS.2 script is alpha. Not a dependency |

## 4. Alternative generators (optional engines)

| Model | Licence | VRAM | Multi-view | Notes |
|---|---|---|---|---|
| TRELLIS.2-4B | MIT (+DINOv3 terms) | 8 GB (fork) – 24 GB | via community blending | default |
| Pixal3D | MIT (HF EU flag) | low-VRAM 1024 | **yes (Sep 2026)** | see [02](02-pixal3d-algorithms.md) |
| TRELLIS v1 | MIT | 8–16 GB | yes (tuning-free) | text variants; legacy |
| TripoSG | MIT | ≥8 GB | no | geometry only |
| Direct3D-S2 | MIT | 10–24 GB | no | geometry only |
| Step1X-3D | Apache-2.0 | 27–29 GB | no | heavy |
| PartCrafter / OmniPart / **SegViGen** | MIT | ≥8 GB | – | part-aware generation / segmentation (SegViGen repurposes TRELLIS.2) |
| SAM 3D Objects | SAM License | ≥32 GB, Linux | – | real-photo objects; too heavy |
| Hunyuan3D-2.x / 2mv / Omni | Tencent (no EU/UK/KR) | 6–29 GB | 2mv: 4 views | plugin only |
| PartPacker | NVIDIA NC | – | – | ✘ |

## 5. Local image models (concept art, turnarounds, T/A-pose)

| Model | Licence | Notes |
|---|---|---|
| **Z-Image-Turbo** (6B) | Apache-2.0 | fast T2I, ~16 GB (quantized less) |
| **FLUX.2-klein-4B** | Apache-2.0 | T2I + edit + multi-reference, ~13 GB (FP8 less) |
| **Qwen-Image / Edit-2509 / Edit-2511** (20B) | Apache-2.0 | needs FP8/GGUF for 12–24 GB. Edit-2509 takes **keypoint/depth/edge** control. **AnyPose LoRA** (Apache-2.0) for T/A-pose; **Multiple-angles LoRA** (Apache-2.0) for side/back views |
| HiDream-O1-Image 8B | MIT | T2I + edit + subject personalization |
| SDXL (+ControlNet OpenPose) | OpenRAIL++ | 8 GB, huge ecosystem |
| MV-Adapter | Apache-2.0 | 6 consistent views from text or image |
| FLUX.1-dev / Kontext-dev / FLUX.2-dev / klein-9B | **non-commercial** | user-download only, if at all |
| Qwen-Image 2.1 (Sep 2026) | **research-only** | ✘ |

Caveat: generated side/back views invent hidden detail. The UI needs a **consistency review step**
(side-by-side views, silhouette-height check) before multi-view 3D.

## Sources
docs.meshy.ai/en/api/{image-to-3d,text-to-3d,multi-image-to-3d,remesh,retexture,rigging-and-animation,animation,animation-library,text-to-image,uv-unwrap,multi-color-print,changelog,pricing} ·
docs.meshy.ai/en/webapp/{changelog,guides/3d-model/rigging,guides/animate,guides/texture-edit} · meshy.ai/pricing ·
developers.tripo3d.com/en/docs/animations-rig.md · github.com/VAST-AI-Research/TripoSG · arxiv.org/abs/2509.12815 ·
github.com/Tencent-Hunyuan/Hunyuan3D-2.1 · github.com/Wimacs/trellis2.c · github.com/pwilkin/trellis.cpp ·
github.com/lightningpixel/modly · github.com/visualbruno/3DGenStudio · github.com/visualbruno/ComfyUI-Trellis2 ·
github.com/PozzettiAndrea/ComfyUI-TRELLIS2 · blog.comfy.org/p/trellis2-and-pixal3d-are-now-native ·
github.com/IgorAherne/TRELLIS.2-stableprojectorz · github.com/IgorAherne/StableProjectorz ·
github.com/Mesh2Motion/mesh2motion-app · github.com/MrForExample/ComfyUI-3D-Pack · github.com/Nelipot-Lee/SegviGen ·
github.com/wgsxm/PartCrafter · github.com/HKU-MMLab/OmniPart · github.com/facebookresearch/sam-3d-objects ·
huggingface.co/Tongyi-MAI/Z-Image-Turbo · huggingface.co/black-forest-labs/FLUX.2-klein-4B ·
huggingface.co/Qwen/Qwen-Image-Edit-2509 · huggingface.co/oldmonk69/AnyPose · huggingface.co/dx8152/qwen-edit-2509-multiple-angles ·
huggingface.co/HiDream-ai/HiDream-O1-Image · github.com/huanngzh/MV-Adapter
