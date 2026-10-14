# Research 08: Blender integration (interactive + headless + MCP)

> Status: research notes, 2026-10-03. The survey **ran Blender 5.2.2 LTS in the sandbox**
> (Linux, 4 vCPU, no GPU). We re-checked: `blender --version` → *5.2.2 LTS, Python 3.13.13*;
> `ahujasid/blender-mcp` is **MIT**, last commit 2026-09-30, add-on socket on `localhost:9876`
> with `execute_code` + `get_viewport_screenshot`; Blender Lab's official MCP server is v1.0.3 and
> needs **Blender 5.1+**. Owner decisions: **interactive Blender**, **Claude via MCP**.

## 1. Versions and the pin

| Version | Python | Status |
|---|---|---|
| 4.5 LTS | 3.11 | supported until Jul 2027 |
| 5.0 (Nov 2025) | 3.11 | **big API break** (see §5) |
| 5.1 (Mar 2026) | **3.13** | |
| **5.2 LTS** (Jul 2026; 5.2.2 on 2026-09-15) | 3.13 | **supported until Jul 2028 → our pin** |
| 5.3 | – | due Nov 2026 |

- **Pin Blender 5.2.2 LTS, the official portable zip** (`blender-5.2.2-windows-x64.zip`, ~404 MB),
  **downloaded on first run** from download.blender.org and verified against the published
  `.sha256`. Extract it to `%LOCALAPPDATA%\Effigy\blender\5.2.2\` with a **`portable/`**
  folder, so the user's own Blender prefs and add-ons never leak in. Downloading rather than
  redistributing keeps us clear of GPL source-distribution duties.
- RTX 50 / sm_120 works in Cycles since 4.4. The **5.2 OptiX backend needs NVIDIA driver ≥ 575**,
  so check the driver at startup.
- Optional: accept the user's own install (≥ 4.5 LTS) with a warning when it isn't 5.2.

## 2. Measured facts that shape the design

| Fact | Consequence |
|---|---|
| Cold start ~1.9 s, warm 0.5–0.6 s | **Subprocess per headless operation is cheap.** No persistent worker or RPC protocol needed (ponytail) |
| `bpy.app.timers` **never fire in `-b` mode** | Headless scripts run top to bottom and exit. Interactive add-ons use timers (fine in the GUI) |
| `cycles.device='GPU'` with no usable GPU **silently bakes on CPU** | **Assert a non-empty device list** and record the device actually used |
| Bone heat on a bad mesh prints "failed to find solution" but **returns `{'FINISHED'}` with 0 weighted vertices** | **Always validate weights.** Proxy method verified: voxel-remesh proxy → bone heat → `DATA_TRANSFER` (`VGROUP_WEIGHTS`, `POLYINTERP_NEAREST`) → **0 of 45,330 vertices unweighted** |
| `pose.rigify_generate` works headless (5.6 s, 706 bones / 160 deform) | Rigify is usable, but its DEF bones hang off ORG/MCH, so we need our own clean game skeleton (or extract the DEF bones) |
| 4K normal bake 224k→11k tris: 17.7 s on CPU, 4.3 GB RSS | **CPU bakes are acceptable on the laptop**, so the GPU stays free for ML. GPU only for AO/high-sample/8K, under the global GPU lock |
| QuadriFlow 90k → 4.8k quads in 2.5 s after voxel remesh; can hang on bad input | Always voxel-first + **watchdog timeout** |
| First OptiX use compiles kernels (minutes) | Run a tiny warm-up bake at install time and after driver updates |

## 3. Interactive Blender + Claude

> **Update:** the owner already runs a Blender MCP that exposes a lot of functionality. **We reuse
> it.** The backend becomes an MCP client of it for Open/Pull, and Claude uses it directly. The
> analysis below of `blender-mcp`, Blender Lab MCP and an own bridge is the fallback and the
> checklist we'll use to examine the owner's server.

### The owner's server: **Blender MCP Pro v1.3.0** (examined 2026-10-03)

Source examined from the owner's itch.io zip in a scratch folder. **No code is copied into this repo.**

| Aspect | Finding |
|---|---|
| Licence | **Add-on: MIT** (per README; no LICENSE file in the zip). **MCP server: proprietary**, $5/month subscription via Gumroad. Key in env `BLENDER_MCP_PRO_LICENSE`, verified against `api.gumroad.com` at server start, with a **72 h offline cache** in `~/.blender-mcp-pro/` |
| Architecture | add-on TCP server on **`localhost:9877`** (no clash with blender-mcp/Blender Lab on 9876). Protocol: **4-byte big-endian length + JSON `{"command", "params"}`**. Per-connection threads → `queue.Queue` → **persistent** main-thread timer (50 ms) + **watchdog** (2 s) that re-arms it. Each command has a 120 s wait cap |
| Tools | **120 add-on commands in 19 modules** (add-on needs Blender ≥ 3.6); the server loads 15 core tools and the rest lazily via `list_tool_categories()` / `enable_tools(category)`. Relevant for us: `import_file`, `export_object`, `export_scene` (FBX/OBJ/glTF/GLB/USD/STL/PLY…), `execute_python`, `get_viewport_screenshot` (via `render.opengl(write_still=True)`, which is the method verified to work, not the black `screenshot_area`), `analyze_mesh` (incl. non-manifold), `cleanup_scene`, `apply_all_transforms`, `unwrap_uv` (7 methods), `bake_texture`, modifiers (22 types incl. remesh/decimate), `prepare_for_export`, rigging (`create_armature`, `parent_mesh_to_armature`, vertex groups, constraints), **`diagnose_rig`, `fix_bone_names`, `normalize_weights(limit_per_vertex=4)`, `mirror_bones`**, animation/actions/NLA, `batch_export`, `render_turntable` |
| Network | the licence check at server start; Poly Haven/Sketchfab downloads only when those tools are called. No telemetry found |
| Gaps | no socket auth (localhost bind); **no undo checkpoints or backups**; `execute_python` is plain `exec`; Collada import/export breaks on Blender 5.x (`wm.collada_*` removed); `material.use_nodes` deprecation warnings; long ops (big bakes, QuadriFlow) can hit the 120 s cap → keep those in headless `blender_ops/` |

**How we use it (ponytail: reuse, fill only the gaps):**
1. **Claude ↔ Blender: the owner's licensed Blender MCP Pro server**, unchanged, in `.mcp.json` /
   `--mcp-config` as `blender-mcp-pro`, with `BLENDER_MCP_PRO_LICENSE` taken from the user's
   environment and never stored in the repo. Tool names: `mcp__blender-mcp-pro__*`.
   - Agent presets tell Claude which categories to `enable_tools` (scene utilities, modifiers, UV &
     texture, rigging, rig diagnostics, import/export, workflows).
   - The `assets` category isn't enabled.
2. **Backend ↔ Blender (live link): a ~30-line client for the add-on's socket protocol** (MIT
   add-on, so no licence key or proprietary server needed for Open/Pull). Commands:
   - `import_file` for Open
   - `execute_python` to create the `LT2_<asset>_v<N>` collection, tag objects, save a backup
     `.blend` copy, and push an undo step
   - `export_object` for Pull
   - `get_viewport_screenshot` for UI thumbnails
   - `analyze_mesh` / `diagnose_rig` to feed the validation checklist
3. **Gaps filled by us**, not by replacing the server:
   - backup + undo push before every agent run (an `execute_python` snippet)
   - asset/version tagging
   - long ops (QuadriFlow, high-res bakes, retarget) stay in headless `blender_ops/`
4. **Public builds** (users without a Pro subscription): Claude can use the free `blender-mcp`
   instead. The backend live link only needs the MIT add-on's protocol. Vendoring that add-on
   later is possible (MIT), but needs a LICENSE file from the author first.

### Verified live-session mechanics (interactive Blender 5.2.2 under Xvfb)

These apply to whichever server we use. They're also the **capability checklist** for the owner's MCP:

| Need | Verified mechanism | Gotcha |
|---|---|---|
| Run on the main thread | socket → queue → **`bpy.app.timers.register(…, persistent=True)`**, re-armed in `load_post` | **non-persistent timers are silently dropped when a .blend loads** |
| Undo per agent job | run the job as an operator with `bl_options={'REGISTER','UNDO'}` via `bpy.ops.<op>('EXEC_DEFAULT', True)` inside `context.temp_override(window, area=VIEW_3D, region)`; or `bpy.ops.ed.undo_push(message=…)` after raw code | undo is one global linear stack; undoing an agent step also undoes later user edits |
| Backup before a run | `bpy.ops.wm.save_as_mainfile(filepath=…, copy=True)` (user's file untouched); asset-only: `bpy.data.libraries.write(path, {objs}, path_remap='RELATIVE_ALL')` | |
| Viewport screenshot | **`gpu.types.GPUOffScreen(w,h).draw_view3d(...)` → `texture_color.read()`**, or `render.opengl(write_still=True)` | **`screen.screenshot_area` returns all-black** when the window isn't composited in the foreground |
| Load a version | new collection `LT2_<asset>_v<N>` as active layer collection → `import_scene.gltf` → tag `obj["lt2_asset_id"]`, `obj["lt2_version"]` | switch to OBJECT mode first; never run while a modal operator is active |
| Push edits back | export the tagged collection (glTF) + optional `.blend` via `libraries.write` → backend records version N+1 with provenance (user/agent, job id) | |

**Capability checklist for the owner's MCP**:
1. a run-Python tool or import/export tools
2. a viewport screenshot that isn't black
3. save a copy (backup)
4. any auth on its socket
5. undo handling
6. port (9876 clashes between blender-mcp and Blender Lab)
7. Blender 5.x API compatibility (e.g. `action.fcurves`, removed in 5.0)

Gaps get filled by a few `lt2` MCP tools, not by replacing the owner's server.

### Reference: `blender-mcp`

`ahujasid/blender-mcp` (MIT, ~30k ★, active):
- The add-on runs a JSON-over-TCP server on `localhost:9876`.
- Client threads → `queue.Queue` → one main-thread timer executes the commands.
- An MCP server (stdio) exposes `get_scene_info`, `execute_blender_code`, `get_viewport_screenshot`,
  plus optional Poly Haven / Sketchfab / Hyper3D / Hunyuan3D integrations. Those are off by
  default and **stay off**. Telemetry is opt-in and **stays off**.

Known gaps: no socket auth; `execute_code` is plain `exec` with no undo or backup; telemetry is
on by default (`DISABLE_TELEMETRY=true`); still reads `action.fcurves`, so animation info is
silently empty on 5.x. The PyPI package is now `mcp-for-blender`.

**If no other server were available, this one add-on covers both needs:**
1. **Live link from our backend**: we send `execute_code` commands to `localhost:9876`, e.g.
   - `bpy.ops.import_scene.gltf(filepath=…)` for "Open version N"
   - `bpy.ops.wm.save_as_mainfile(copy=True)` + `export_scene.gltf` for "Pull"

   Imported objects get tagged with `obj["lt2_asset_id"]`, `obj["lt2_version"]`. **No add-on of
   our own** in the MVP.
2. **Claude's Blender MCP server**: the same add-on, through blender-mcp's stdio MCP server in our
   `.mcp.json` / `--mcp-config`.

Alternatives and their trade-offs:
- **Blender Lab MCP** (official, GPL-3, 5.1+, v1.0.3): also has a background-Blender tool and API-docs
  lookup. **Its default port is also 9876**, so don't run both. It's the fallback if blender-mcp
  stalls.
- **Our own bridge add-on** (GPL-3.0-or-later, stdlib only, outbound connection to our backend):
  only if we need things blender-mcp can't do (selection/material live sync via
  `depsgraph_update_post`/`msgbus`, a "Send back" button inside Blender).

**Safety** (both MCP servers execute LLM-written Python "without any guards"):
- Snapshot (pull) before every Claude run, then Accept/Revert.
- `localhost` only (binding to 0.0.0.0 would trigger the Windows Firewall prompt).
- Claude's tool allowlist covers MCP tools only, with no shell
  ([research 10](10-claude-mcp-integration.md)).
- An optional "expert mode" toggle for raw `execute_blender_code`. By default, prefer our
  **versioned operation scripts** exposed through the `lt2` MCP server (`mesh.cleanup`,
  `uv.unwrap`, `bake.transfer`, `rig.autoskin`, `export.gltf`), which run headless on a copy.

## 4. Headless operation scripts (`blender_ops/`, GPL-3.0-or-later)

`blender -b --factory-startup --offline-mode --python-exit-code 1 --python blender_ops/<op>.py -- <json>`.
One file per operation. Paths go in the JSON (not argv) to dodge Windows MAX_PATH and quoting.
Run with `CREATE_NO_WINDOW`, and kill via a Job Object on timeout. Key operators (5.2 names):

| Area | Operators |
|---|---|
| Cleanup | `mesh.remove_doubles`, `delete_loose`, `dissolve_degenerate`, `fill_holes`, `normals_make_consistent`, `dissolve_limited`, `symmetrize`, `quads_convert_to_tris(quad_method='BEAUTY')` |
| Remesh | `object.voxel_remesh()` (set `mesh.remesh_voxel_size`), `object.quadriflow_remesh(target_faces, use_mesh_symmetry, use_preserve_sharp, seed)`, modifiers `DECIMATE`, `SHRINKWRAP`, `CORRECTIVE_SMOOTH`, `WEIGHTED_NORMAL` |
| Shading (4.1+) | `object.shade_smooth_by_angle` / `shade_auto_smooth` (`use_auto_smooth` was removed) |
| UV | `uv.smart_project`, `uv.unwrap(method='MINIMUM_STRETCH')` (SLIM, 4.3+), `uv.seams_from_islands`, `uv.average_islands_scale`, `uv.pack_islands(shape_method='CONCAVE', rotate_method='ANY', margin=…)`. Texel density computed via bmesh |
| Bake | `object.bake(type='NORMAL'/'AO'/'DIFFUSE'(pass_filter={'COLOR'})/'ROUGHNESS'/'EMIT', use_selected_to_active, cage_extrusion, max_ray_distance)`. The target image must be the **active Image Texture node** in every material. **No METALLIC type** → wire it to Emission and bake EMIT. `normal_g='NEG_Y'` for DirectX/Unreal. Triangulate before baking and export the same triangulation so MikkTSpace tangents match. ORM packing with numpy outside Blender |
| LOD / collision / transforms | `DECIMATE` chain, `mesh.convex_hull()` (`UCX_` naming for Unreal), `object.origin_set(type='ORIGIN_CURSOR')`, `transform_apply` |
| Rig | Rigify headless (`armature_human_metarig_add` → fit → `pose.rigify_generate`), or our own template skeleton. Skinning `parent_set(type='ARMATURE_AUTO')` **on a voxel proxy + DATA_TRANSFER**. Then `vertex_group_clean`, `vertex_group_limit_total(limit=4)`, `vertex_group_normalize_all` |
| Animation | **Retarget extension** (Expy Kit fork, GPL-3, Blender 5.0+, presets for Mixamo/UE/VRoid) inside Blender, plus `nla.bake(visual_keying=True, clear_constraints=True)`. **Use this before writing our own retargeter** (ponytail). 5.0 removed `action.fcurves`; use channelbags (`anim_utils.action_ensure_channelbag_for_slot`) |
| Export | glTF (`export_draco_mesh_compression_enable`, meshopt, `export_image_format='WEBP'`, `export_animation_mode='ACTIONS'`, `export_influence_nb=4`, `export_def_bones`, `export_leaf_bone`). FBX for Unity: `apply_scale_options='FBX_SCALE_ALL'`, `bake_space_transform`, `axis_forward='-Z'`, `axis_up='Y'`. FBX for Unity and Unreal: `add_leaf_bones=False`, `use_armature_deform_only`, `bake_anim_use_all_actions`, `use_tspace`. USD (`export_textures_mode`), OBJ/STL/PLY (C++), **Collada removed in 5.0**, 3MF via the threemf-io extension (GPL-2) |
| Validate | bmesh: non-manifold/boundary edges, zero-area faces, flipped normals, UV overlap/out of bounds, texel density, ≤4 normalized influences, unweighted vertices; `BVHTree.overlap` for self-intersection. Khronos **glTF-Validator** on exports |

**GPL boundary:**
- `blender_ops/` and any add-on of ours are **GPL-3.0-or-later**, in their own folder with a
  `LICENSE`.
- The MIT backend never imports them and only exchanges JSON with file paths, which counts as
  separate programs per the FSF FAQ ("pipes, sockets and command-line arguments").
- `pip install bpy` is **not used**: it would pin Python 3.13 and conflict with torch's native libs
  in the ML venv.

## 5. Blender 5.x traps (for our scripts)
- `action.fcurves` / `groups` / `id_root` removed (5.0) → channelbags + slots.
- `scene['cycles']` IDProperty access removed → `scene.cycles`.
- `material.use_nodes` deprecated. Engine `BLENDER_EEVEE_NEXT` → `BLENDER_EEVEE`. Boolean `FAST` → `FLOAT`.
- `--factory-startup` doesn't persist Cycles device prefs → set them in every script.
- `mathutils` → numpy is now float32.
- UV selection moved to attributes (`BMLoopUV.select` removed).
- Type checking: `fake-bpy-module-5.2`. Feature detection with `hasattr` in one `compat.py`.

## 6. VRAM (16 GB laptop) and Windows notes
- **Bakes default to CPU.** The GPU is used only under the **global GPU lock** and in a
  short-lived bake process (its CUDA/OptiX context is released on exit).
- Keep the interactive Blender viewport on the **iGPU (Optimus)** where possible, and don't run
  Cycles viewport rendering while an ML step runs.
- NVIDIA "CUDA Sysmem Fallback": set *Prefer No Sysmem Fallback* for our processes, so OOM fails
  fast instead of crawling.
- Launch `blender.exe` (not `blender-launcher.exe`). Redirect stdout/stderr to a log file (an
  undrained pipe can deadlock Blender). Write new files and rename (Windows file locks). Expect
  Windows Defender to slow the first extraction and launch.

## 7. Tests
- `blender -b --factory-startup --python-exit-code 1 --python tests/blender/run.py` against
  fixtures: a real TRELLIS output and pathological meshes.
- Assert invariants, not bytes:
  - manifold, face budget, UVs in [0,1] with no overlap
  - influences ≤ 4 and normalized, no unweighted vertices
  - glTF-Validator clean, re-import round trip
  - normal-map mean ≈ (0.5, 0.5, 1)
- Blocking target: 5.2 LTS. 5.3/daily: canary, run manually until there's CI.

## Sources
blender.org/releases/5-2 · download.blender.org/release/Blender5.2 · developer.blender.org/docs/release_notes/{5.0/python_api,5.0/pipeline_io,5.1/python_api,5.2/cycles,4.4/cycles,4.4/animation_rigging,4.1/modeling,4.3/modeling} ·
docs.blender.org/api/current/{bpy.ops.object,bpy.ops.mesh,bpy.ops.uv,bpy.ops.export_scene,bpy.ops.nla,bpy.app.timers,info_gotchas_threading,info_advanced_blender_as_bpy} ·
docs.blender.org/manual/en/latest/advanced/{command_line/arguments,blender_directory_layout,extensions/getting_started,extensions/licenses} ·
docs.blender.org/manual/en/latest/addons/scene_gltf2 · pypi.org/project/bpy · blender.org/about/license · gnu.org/licenses/gpl-faq.html#MereAggregation ·
blender.org/lab/mcp-server · projects.blender.org/lab/blender_mcp · github.com/ahujasid/blender-mcp · github.com/sandraschi/blender-mcp ·
docs.meshy.ai/en/webapp/plugins/blender/bridge-to-blender · tripo3d.ai/blog/tripo-dcc-bridge-for-blender · extensions.blender.org/add-ons/retarget ·
extensions.blender.org/add-ons/print3d-toolbox · extensions.blender.org/add-ons/threemf-io · github.com/sentfromspacevr/robust-weight-transfer ·
github.com/ksami/QRemeshify · github.com/franMarz/TexTools-Blender · pypi.org/project/fake-bpy-module-5.2
