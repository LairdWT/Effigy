# Research 09: Is there a more capable open model than TRELLIS.2? (survey, 2026-10-03)

> Status: research notes. Compiled from a delegated survey. We re-verified the following ourselves:
> the **3D Arena leaderboard** (live API, same numbers), the **CuMesh remesh bug on Blackwell sm_120**
> (`ThatButters/trellis2-blackwell-fix`), and **Pixal3D's licence history** (HF discussion #2:
> custom restrictive terms until ~late May 2026, now MIT). Evaluated against the reference machine:
> **RTX 5080 Laptop, 16 GB, sm_120, Windows 11, 32 GB RAM**.

## 1. Bottom line

- **There is no "TRELLIS.3".** The only notable new open, *textured* generator of 2026 is **Pixal3D**,
  which is fine-tuned from TRELLIS.2 (same code, same O-Voxel output).
- **Human-preference data says TRELLIS.2 isn't the best open model.** On 3D Arena, TRELLIS.2-4B
  ranks **#18/24 on renders** and **#11/21 on topology**:

  | Model | Render ELO (votes) | Topology ELO (votes) | Open? | Usable for us? |
  |---|---|---|---|---|
  | TRELLIS (v1) | 1304 (5.8k) | 1328 | MIT | yes, but older stack (spconv) |
  | Hunyuan3D-2 / 2.1 | 1284 / 1273 | **1360** / 1313 | Tencent licence | **not in EU/UK/KR** |
  | **Pixal3D** | **1262 (303)** | 1224 (239) | **MIT** | **yes** |
  | Hi3DGen (geometry) | – | 1232 | MIT | yes (geometry only) |
  | TripoSG (geometry) | – | 1222 | MIT | yes (geometry only) |
  | **TRELLIS.2-4B** | 1126 (1.4k) | 1143 | MIT | yes |
  | *Meshy-6 / Meshy-7 (closed)* | *1358 / 1308* | *1327 / 1277* | – | reference bar |

  **Caveats:**
  - Vote counts are small for the new models.
  - The TRELLIS.2 entries came from HF-Space defaults (~12 MB GLBs vs. 35–44 MB for Pixal3D), so
    decimation and presentation probably skew the result.
  - The TRELLIS.2 paper reports a 66.5% preference over Hunyuan3D-2.1/Step1X/Direct3D-S2/Hi3DGen.
  - **Treat the Arena as a signal, not a verdict. We'll A/B on our own golden set.**
- **Most "stronger" models are closed or legally unusable** for an EU-facing tool:
  - closed: Hunyuan3D 2.5/3.x, LATTICE, Sparc3D/Hitem3D, Seed3D 2.0, Ultra3D, Meta AssetGen
  - Tencent territory clause: Hunyuan3D-2.1/Omni/Part/2mini, and UltraShape, which requires a
    Hunyuan coarse mesh
- **Character-specific evidence is thin.** Meta's AssetGen paper notes TRELLIS.2 "fails to recover
  letters" and "distorts fingers". Pixal3D's pixel-aligned conditioning targets exactly the
  faithfulness to the input view (faces, logos, silhouette).

## 2. Ranked candidates (fit for RTX 5080 Laptop / 16 GB / Windows)

| # | Model | Licence | Output | Fits 16 GB? | Windows / sm_120 | Verdict |
|---|---|---|---|---|---|---|
| 1 | **Pixal3D** (May 2026; multi-view Sep 2026) | **MIT / MIT** (HF card still has a stale `extra_gated_eu_disallowed` flag; repo not gated. The dreamrec ComfyUI wrapper's NOTICE still calls it "non-commercial, not for EU", which predates the May 2026 relicense; the GitHub LICENSE and HF card say MIT) | mesh + PBR (O-Voxel), single + 4-view | **yes at 1024 with 12 steps + 2K texture (~14 GB)**; 16 steps/4K ≈ 17 GB; 1536 ≈ 32 GB (wrapper author's RTX 5090 measurements) | community Windows build with torch 2.8 cu128 claims RTX 50; **natten wheel is sm89+PTX, so build for sm_120** | **"Faithful" weight set**, co-default candidate |
| 2 | **TRELLIS.2-4B** (Dec 2025) | MIT / MIT (deps: see licence audit) | mesh + PBR, 512–1536; **texturer for any mesh** | **yes: 1024 cascade verified on a 16 GB RTX 5060 Ti (Blackwell)**, about 3.5–5.5 min in PyTorch | community cu128 wheels; SDPA/xformers attention; **CuMesh `remesh_narrow_band_dc` broken on sm_120** | **"Fast" weight set**, co-default candidate |
| 3 | TripoSG (Mar 2025) | MIT / MIT | geometry only, watertight SDF | yes (8 GB) | generic torch; avoid its pymeshlab (GPL) | optional: **TripoSG + TRELLIS.2 texturer** = all-MIT, watertight (good for print) |
| 4 | Hi3DGen (Mar 2025) | MIT / MIT | geometry only, sharp relief | probably | TRELLIS v1 stack (spconv) | optional; low priority |
| 5 | Hunyuan3D-2.1 (+ UltraShape) | Tencent (no EU/UK/KR) | watertight shape + PBR paint | shape yes; paint only with offload | community cu128 guide | **region-restricted plugin only** |
| 6 | Direct3D-S2, Step1X-3D | MIT / Apache | geometry (+texture) | 24–27 GB | Linux, old triton/cu121 | ✘ for 16 GB |
| 7 | SAM 3D Objects | SAM licence (gated) | splats/mesh, no PBR | 32 GB | Linux, cu121 | ✘ |
| 8 | AniGen | MIT (NC CUBVH bundled) | rigged mesh in one step | 18 GB | spconv issues on Blackwell | watch |
| – | SF3D/SPAR3D, UniLat3D, Roblox Cube/CubePart, Stability Arbor | various | – | – | – | weaker or text-geometry only. **Text→image→3D beats native text-to-3D** |

## 3. "Geometry model + separate texturer" vs. one model

- `Trellis2TexturingPipeline` is a cheap, MIT building block. It loads the shape encoder, one 1.3B
  texture flow and the decoder, and textures **any** mesh from one image, with PBR, well under 16 GB.
  So any geometry engine can feed it.
- **One model wins on faithfulness:** pixel-aligned Pixal3D matches the input view better than a
  shape-then-texture pipeline, which can drift on visible parts.
- **Combos are worth having** where they add something specific:
  - TripoSG (watertight) + TRELLIS.2 texturer → 3D print / clean solids
  - Hunyuan3D-2.1 + UltraShape → highest geometric detail, non-EU profile only

## 4. What this changes in the plan

1. **Generator = the TRELLIS.2 runtime with two MIT weight sets:**
   - **Fast** (TRELLIS.2)
   - **Faithful** (Pixal3D, single image or 4 views)

   **Phase 0 A/B on the reference laptop decides the default.** Both write the same
   `hi.glb + ovoxel.npz`, so nothing downstream changes. ponytail: no engine/plugin framework
   needed, just a `--weights fast|faithful` flag on `steps.generate`.
2. **Phase 0 must test `remesh_narrow_band_dc` on the 5080.** It's broken on sm_120 per the
   blackwell-fix repo. Our MVP path doesn't need it (clean → simplify → unwrap works without DC
   remesh). Watertight output for quads/print goes through **Blender voxel remesh** instead, or
   marching cubes from voxels as in the fix repo. A CuMesh rebuild for sm_120 can be retried later.
3. Optional engines, only when needed: TripoSG + TRELLIS.2 texturer (watertight/print); Hunyuan
   region-restricted plugin. Each goes in its own venv only if its pins conflict (they do: older
   torch/cu12x).
4. **Licence audit (unchanged, confirmed):**
   - swap RMBG-2.0 → BiRefNet
   - nvdiffrast is NC → own torch UV rasterizer before commercial use (**LocalMeshEngine's
     `uvraster.py`, Apache-2.0, is a reference implementation**)
   - DINOv3: ship the licence + "Built with DINOv3" (the `timm/vit_large_patch16_dinov3.lvd1689m`
     mirror is ungated, same licence)
   - cuBVH credits instant-ngp (NVIDIA NC): grey area, noted
5. **Memory:** total weights are ≈9.5 GB (single image) / ≈14.3 GB (4-view) per LocalMeshEngine's
   figures. Staged loading fits **32 GB RAM** and **16 GB VRAM**, with **1024 cascade as the
   ceiling on the laptop**.

## 4b. Engine-base review (2026-10-03, verified)

| Base | Licence / activity | Verdict |
|---|---|---|
| IgorAherne SPZ fork | MIT; last commit 2026-04-28; cp311 wheels, arch undocumented, no sm_120 handling; xformers (aborts on sm_120) | **Patch donor only** (chunked decode, `EXPLICIT_GEMM` + torch fallback, `pipeline_worker.py` pattern) |
| **Quentincls/localmesh-engine** | **Apache-2.0**; created 2026-09-10; Python 3.12 + torch 2.8.0 cu128; FP8 TRELLIS.2 + Pixal3D MV; `uvraster.py` (344 lines, nvdiffrast-free) + decoy module; `sdpa_backend.py` for sm_120; BiRefNet_HR; staged NVML-budgeted loading; attribute volume first-class; 8 GB laptop measured 5.9 GB peak | **Primary patch donor.** Risk: single author, product wrapper not a library, wheel arch undocumented |
| visualbruno/ComfyUI-Trellis2 | MIT; active (Sep 2026); **issue #197: prebuilt wheels lack sm_120 kernels** | recipe reference, not wheels |
| MakitaToki/trellis2-blackwell-wheels | arch 12.0 but torch 2.7 and pre-PR-#29 CuMesh | don't reuse |
| Comfy-Org native port | GPL-3 | algorithm map only (pure-torch sparse conv, DC remesh, UV unwrap, BVH bake) |
| microsoft/TRELLIS.2 | MIT; no code since Jan 2026; PR #173 (keep UVs) closed-unmerged, folded into open PR #175; **PR #185 (Windows/Blackwell) open** | **the base we vendor** |
| CuMesh | **PR #29 (Blackwell stream fix) merged 2026-05-09**, tested RTX 5090 / Windows; issue #27 (fragmented remesh) open, possibly fixed by #29; PRs #39/#41 (OOB UDF, CUB identity) open | build from main ≥ May 9 |
| FlexGEMM | Triton ≥ 3.2 hard dependency (triton-windows 3.4 on Windows); issue #32 (Sep 2026): `shape_slat_decoder` crash on RTX 5070/WSL2 open; #13 silent failure on RTX 5080 open | build ourselves; `EXPLICIT_GEMM` fallback; test day one |
| natten (Pixal3D) | no official win_amd64; community cp312/cu128 sm_120 wheel (naxneri, unverified README) | verify `natten.HAS_LIBNATTEN` + a real `na2d` call, else build |

**Quantization on Blackwell:** FP8 (localmesh, visualbruno) and INT8 ConvRot (Comfy-Org) are memory
wins only; trellis.cpp data shows no throughput gain on RTX 50. → bf16 + staged loading first.

**Cold start:** no measured TRELLIS.2 numbers; Pixal3D's 24 GB loads in 1–3 min to RAM + 30–60 s to
GPU. → resident worker per heavy family (ARCHITECTURE §4).

## 4c. Owner decision on Hunyuan (2026-10-03)

Hunyuan3D-2.1 is added as an **isolated experimental engine** with restricted outputs (PLAN §6,
IMPLEMENTATION MX1): for A/B comparisons on topology (its strongest 3D Arena category), not for shipped
game assets.

## 5. Watch-list
- Hunyuan3D 3.x weights (if ever opened, licence permitting).
- LATTICE code, Sparc3D weights, Seed3D, Meta AssetGen.
- VAST Nexus (native mesh) and PixTex (texturing).
- trellis.cpp/GGUF (Vulkan), SymTRELLIS, Pixal3D multi-view fine-tunes.
- Meta's SA-3DAO leaderboard (was down when checked).
- Benchmark bar: Meshy-7, Tripo H3.1.

## Sources
3d-arena-3d-arena.hf.space/api/leaderboard?vote_type={render,topology} · huggingface.co/spaces/3d-arena/3d-arena ·
github.com/microsoft/TRELLIS.2 · arxiv.org/abs/2512.14692 · github.com/TencentARC/Pixal3D · huggingface.co/TencentARC/Pixal3D/discussions/2 ·
arxiv.org/abs/2605.10922 · github.com/dreamrec/ComfyUI-Pixal3D · github.com/ThatButters/trellis2-blackwell-fix ·
github.com/Quentincls/localmesh-engine · github.com/pwilkin/trellis.cpp · huggingface.co/Aero-Ex/Trellis2-GGUF ·
github.com/Tencent-Hunyuan/Hunyuan3D-2.1 · github.com/PKU-YuanGroup/UltraShape-1.0 · github.com/VAST-AI-Research/TripoSG ·
github.com/Stable-X/Hi3DGen · github.com/DreamTechAI/Direct3D-S2 · github.com/stepfun-ai/Step1X-3D ·
github.com/facebookresearch/sam-3d-objects · github.com/VAST-AI-Research/AniGen · arxiv.org/abs/2605.26137 (AssetGen) ·
arxiv.org/abs/2606.04108 (SymTRELLIS) · huggingface.co/Roblox/cubepart · github.com/Stability-AI/arbor
