# Research 03: Retopology, decimation, UV and baking

> Status: research notes, 2026-10-03. Compiled from a delegated survey that included **local
> CPU benchmarks** on TRELLIS.2's own example mesh. We re-verified the key licences by cloning:
> AutoRemesher is **MIT** (relicensed from GPLv3 in 2026), QuadWild-BiMDF is **GPL-3**, and the
> MakeHuman base mesh and assets are **CC0**. Correction to the survey: `Trellis2TexturingPipeline.run()`
> does **not** keep input UVs (see [01 §5](01-trellis2-deep-dive.md)). It needs the PR #173/#175 patch.

## 1. Bottom line

- **No open tool automatically produces animation-ready character topology** (loops at
  shoulders, elbows, knees, eyes and mouth). The Blender manual says the same. Feature-aligned quad
  remeshers get close on clean input. **Fitting a CC0 humanoid template** (MakeHuman hm08) is the
  only route that guarantees joint and face loops.
- **Learned "artist mesh" retopology isn't usable for us yet.** The open models are non-commercial
  (MeshAnything, FastMesh, MeshFlow), Tencent territory-restricted (BPT), triangle-only, or capped
  at ~1.6k–11k faces. The quad-native ones (QuadGPT, Hunyuan PolyGen 1.5, Tripo P2.0) are closed
  or API-only. → Watch-list.
- **TRELLIS.2 + CuMesh already cover the low-poly basics**: GPU cleanup, decimation, UV and
  attribute bake. We add only: a **"bake onto any mesh" entry point**, a **normal map**, tangents,
  **quads**, and LODs.
- **Raw O-Voxel meshes are messy.** The example knight has **938 components and 45k boundary
  edges**. That breaks QuadriFlow and makes decimators stall at high face counts. **A robust "make
  it manifold" step before any remesher is mandatory.**

## 2. What's already there (CuMesh, MIT, GPU)

`fill_holes`, `remove_duplicate_faces`, `repair_non_manifold_edges`, `remove_non_manifold_faces`,
`remove_small_connected_components`, `unify_face_orientations`, `simplify` (GPU edge collapse),
`remesh_narrow_band_dc` (watertight shell; **doubles thin parts like capes**), `uv_unwrap`
(GPU clustering + xatlas), and `cuBVH` (closest point, ray trace).

Notes:
- The GPU decimator credits **pamo (AGPL-3.0)** as its reference implementation. That's provenance
  only, not a licence issue, but worth recording.
- The PyPI package called `cumesh` is **a different project**. Install from git or our own wheels.

## 3. Candidates

### Quad remeshers (all CPU, so sm_120 doesn't matter)

| Tool | Licence | Result on messy AI mesh (knight) | Result on clean humanoid (90k tris) | Integration |
|---|---|---|---|---|
| **QuadriFlow** (also built into Blender as `object.quadriflow_remesh`) | BSD-3 | **failed** ("wrong init"), hung >15 min after repair | **244 s → 6,746 pure quads, closed, 0 non-manifold, 1.8% irregular**; symmetry option in Blender | Blender subprocess (needs manifold input, scaled so edges > 1e-4) |
| **QuadWild + Bi-MDF** | **GPL-3** (binaries for Win/Linux) | not benchmarked (build blocked) | best open feature-aligned quality per paper; organic/mechanical configs; feature lines become patch borders | subprocess only (GPL). QRemeshify (GPL Blender add-on) adds symmetry and guide edges |
| **AutoRemesher 1.2.0** (Aug 2026: native quad parameterizer, `--anisotropy`, fewer leftover triangles/irregular vertices, fixed Windows zip) | **MIT (2026)** | 2.5–3.7 s but 344–376 non-manifold edges | 41 s → 13.4k quads, 170 boundary edges, 12 non-manifold edges | headless CLI, Win/Linux builds |
| Instant Meshes (PyNanoInstantMeshes) | BSD-3 | 2.4–9.9 s, ~3.9k boundary edges, 90 non-manifold edges | 13–18 s, 13.4k quads, 750+ boundary edges (holes) | wheels cp38–cp312 (no cp313); fast but needs repair |
| Blender Voxel Remesh | GPL (Blender) | watertight pre-step only | – | Blender subprocess |
| Exoside Quad Remesher | commercial; EULA forbids automation/SDK use | – | – | ✘ can't bundle |

### Learned retopology (watch-list only)

| Model | Licence | Max faces | Note |
|---|---|---|---|
| MeshAnything V2 | S-Lab **NC** code (weights tagged MIT, conflicting) | 1.6k | ✘ |
| BPT | Tencent Hunyuan 2.0 licence (**no EU/UK/KR**); GPL point encoder | >8k | ✘ |
| DeepMesh 0.5B | Apache-2.0 / MIT | (1B unreleased ~30k) | candidate to watch; Linux, CUDA 11.8 |
| TreeMeshGPT | MIT (checkpoints without licence) | 5.5k–11k | ? |
| Mesh Silksong | MIT / MIT | – | manifold-friendly; Docker on Windows |
| FastMesh, MeshFlow (Meta) | **NC** | – | ✘ |
| QuadGPT, PolyGen 1.5, Tripo P2.0, Meshtron, Nautilus | closed / no code | – | ✘ |

### Decimation and cleanup

| Library | Licence | Note |
|---|---|---|
| **CuMesh** | MIT | GPU; already in the pipeline → **primary** |
| meshoptimizer / gltfpack | MIT | attribute-aware simplify, `Prune` (floaters), `Regularize` (better under skinning). The gltfpack CLI gives LODs + compression with no Python binding needed |
| fast-simplification, pyfqmr | MIT | CPU fallbacks. **Stall on open boundaries** unless cleaned first or border locking is off |
| trimesh, manifold3d, Open3D | MIT / Apache | utilities; `trimesh.registration.nricp_amberg` for template fitting |
| pymeshlab, pymeshfix | **GPL-3** | subprocess only, if at all |
| MeshLib | **non-commercial** | ✘ (used by a ComfyUI-Trellis2 hole-fill node) |

### UV

- **CuMesh `uv_unwrap` / xatlas** (MIT). Fast (0.1 s at 20k faces) but **fragments charts** on noisy
  meshes (1.4–1.65× seam vertex duplication). Fine for props.
- **Blender**: Unwrap with **Minimum Stretch (SLIM, 4.3+)**, Smart UV Project, Pack Islands. Best for
  characters with explicit seams.
- **Character seam heuristic** (ours to implement later): cut at part or skin-weight boundaries
  (neck, shoulders, wrists, waist, ankles), one longitudinal cut per limb on the inner/back
  side, head seam behind the ears, separate face and hand islands with a texel-density boost.
- PartUV (Apache but depends on NC PartField, Linux-only) ✘. Learned seam models (SeamGPT, ArtUV, …)
  have no code yet.

### Baking

- **Albedo/roughness/metallic/alpha:** reuse the `to_glb` attribute-sampling block on the new
  mesh and its UVs. Use a **cage ray-cast** (cuBVH `ray_trace`) where closest point picks the wrong
  layer (fingers, capes).
- **Normal map:** dense-mesh normals expressed in the low-poly **MikkTSpace** tangent frame, and
  **the same tangents exported in the GLB**.
- **Blender Cycles fallback:** Selected-to-Active with cage. There is **no metallic pass**; route
  metallic into Emission and bake Emit. **bpy 4.5 LTS and 5.2 Windows wheels ship native sm_120
  cubins**, so Cycles baking works on the RTX 5080.
- xNormal (closed, Windows-only, unmaintained) and Marmoset (commercial) ✘.

## 4. Recommended pipelines (ponytail-sized)

### MVP: game-ready triangle low-poly (props + characters)
1. Keep the dense mesh and `ovoxel.npz` from generation.
2. **CuMesh clean:** `fill_holes` → `remove_duplicate_faces` → `repair_non_manifold_edges` →
   `remove_small_connected_components` → `unify_face_orientations`.
3. **CuMesh `simplify`** to the brief's triangle budget (two passes, as `to_glb` does).
4. **CuMesh `uv_unwrap`**.
5. **Bake** PBR from `ovoxel.npz` + normal map (§3 Baking).
6. Export GLB with tangents. LODs via **gltfpack** later.

### Phase 2: quad character
1. Make it watertight: CuMesh DC remesh or Blender voxel remesh → keep the largest component →
   decimate to 100–200k.
2. **Blender QuadriFlow** with symmetry and a time limit. It works well on clean, watertight input
   (verified above).
3. **AutoRemesher 1.2 CLI (MIT)** runs alongside QuadriFlow on organic shapes (reported better there);
   keep the result with fewer non-manifold edges / holes after CuMesh repair. Its Blender bridge add-on
   is GPL, so call the CLI ourselves.
4. Validate automatically: 0 non-manifold edges, 0 holes, irregular-vertex share, Hausdorff
   distance to the dense mesh.
5. UV in Blender (Minimum Stretch + Pack Islands), then bake as in the MVP.
6. **Export note:** FBX/USD/.blend keep quads; **GLB always triangulates**.

### Later: guaranteed edge loops for humanoids
- **Template fitting:** pose and scale a CC0 MakeHuman hm08 (or our own 4–8k-quad game template
  with authored loops, UVs and weights) to the rig's joints, then non-rigid ICP
  (`trimesh.nricp_amberg`) with joint and face landmarks. That gives guaranteed loops, template UVs
  and pre-authored weights. Clothing, hair and props are segmented and remeshed separately.
- **QuadWild-BiMDF** (GPL subprocess) with feature lines from part/weight boundaries, for creatures.

## 5. Risks

1. **NC/GPL traps:**
   - Non-commercial: nvdiffrast (inside `to_glb`), MeshAnything, FastMesh, MeshFlow, MeshLib,
     PartUV/PartField.
   - Tencent territory licences: BPT.
   - GPL tools (QuadWild, pymeshlab, Blender) stay out-of-process.
   - Exoside can't be bundled.
2. **Messy raw meshes** break remeshers. The manifold step is mandatory, and DC remeshing doubles
   thin parts.
3. **No automatic joint loops** without templates.
4. **Bake bleeding** with closest-point lookup (use a cage ray-cast); tangent frames must match the export.
5. **Packaging:**
   - bpy pins Python 3.11 (4.5 LTS) / 3.13 (5.x), which is why Blender runs as a subprocess.
   - Community TRELLIS wheels contain **sm_86 SASS + PTX only**. On the 5080 they'd JIT on first
     load; **build our own with 12.0**.
   - PyNanoInstantMeshes has no cp313 wheel.

## Sources
github.com/microsoft/TRELLIS.2 (o_voxel/postprocess.py, trellis2_texturing.py) · github.com/JeffreyXiang/CuMesh ·
github.com/SarahWeiii/pamo · github.com/ashawkey/cubvh · github.com/NVlabs/nvdiffrast · github.com/NVIDIAGameWorks/kaolin ·
github.com/wjakob/instant-meshes · github.com/vork/PyNanoInstantMeshes · github.com/hjwdzh/QuadriFlow ·
docs.blender.org/manual/en/latest/modeling/meshes/retopology.html · github.com/cgg-bern/quadwild-bimdf · github.com/ksami/QRemeshify ·
github.com/huxingyi/autoremesher · exoside.com/quadremesher · static.makehumancommunity.org/about/license.html ·
github.com/buaacyw/MeshAnythingV2 · github.com/Tencent-Hunyuan/bpt · github.com/zhaorw02/DeepMesh · github.com/sail-sg/TreeMeshGPT ·
github.com/jhkim0759/FastMesh · github.com/gaochao-s/Mesh-Silksong · github.com/facebookresearch/meshflow ·
digitalproduction.com/2026/09/29/tripo-p2-0-put-quad-mesh-generation-to-the-test · github.com/zeux/meshoptimizer ·
github.com/pyvista/fast-simplification · pypi.org/project/pymeshlab · github.com/MeshInspector/MeshLib ·
github.com/jpcy/xatlas · github.com/EricWang12/PartUV · docs.blender.org/manual/en/latest/render/cycles/baking.html ·
developer.blender.org/docs/release_notes/4.3/modeling · pypi.org/project/bpy · blender.org/about/license
