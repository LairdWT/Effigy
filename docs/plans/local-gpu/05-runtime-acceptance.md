# Observe offline GPU feature samples

Spoke: S05
Outcome: Representative normal application operations establish the observed full baseline, with precise incomplete capabilities.
Depends-on: S04
Decisions: D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13
Constraints: C1, C2, C3, C4, C5, C6, C7, C8
Skills: planning:planning-core
Read-set: INDEX.md, 04-provision-baseline.md#result, CODE.md, local setup instructions, server/presets.py, existing step descriptions and export contracts
Write-set: N:/generated/Effigy/, scratch/, docs/plans/local-gpu/05-runtime-acceptance.md, steps/parts.py, engine/geosam2/PATCHES.md, steps/mocap.py, steps/import_motion.py
State: done

## Context

Expected 20 model turns. Acceptance finalization targets 300000 tokens, ceiling 1032000; 256 turns and 14500000 tokens per active hour remain limits. The owner authorized normal runtime samples, not a code-test suite or a renamed automated test. Use synthetic/local demonstration inputs and ordinary application output only.

## Evidence

- server/presets.py:113 computes GPU budget from available memory; preserve that ownership.
- The owner chose application offline controls plus connection observation, without OS firewall changes.
- Existing Blender is 5.2.0; compatibility with upstream's expected 5.2.2 remains unqualified.
- Backend, worker, and browser boundaries all contribute to observed runtime behavior.

### Sample observations

| Family | Ordinary job/output references | Observation |
|---|---|---|
| Persistence | effigy_setup_crate versions 001-011, reopened after backend restart | Browser rendered persisted mesh and history |
| Fast 3D | d0e25b4068ed; effigy_setup_figure/003_trellis2 | 11370 faces; preview inspected; 2.62 GiB Torch peak |
| Mesh/textures | f127aeb15950, e0f22fc5662d, 0af524cb35ba, 5eb70b5121e1; crate/003_clean through 007_bake | Clean, simplify, UV and bake completed |
| 2D | 33898d7cc21f; effigy_setup_landscape/001_concepts; ffec88964960; figure/005_pixelize | Visible landscape and pixel art; generation peak 7.69 GiB, 424 seconds including cold load |
| Rigging | 5f9b3b088706, 3ccda86abbb0, 5eb0d1dab1d6; figure/004_rig_fit, 008_rig_skin, 010_rig_skin | Blender weights: 0 QA failures. SkinTokens completed but stretch QA failed (29.403), symmetry warning (0.1628); quality not accepted |
| Animation | 25fdac09edda, e53c14399ed5, e44e92733387; figure/007_motion, 009_anim, 011_anim_edit | 3-second text motion, bundled Idle_A, retargeting and speed/in-place edit completed |
| Exports | abce94c96120, 32064c6926d3, 785fc806a0fe; crate/008_export through 010_export | GLB/USDZ, STL/3MF and FBX produced; GLB/FBX reopened through jobs 7072efd662fc and 56a04eea156c in effigy_export_reopen |
| Blender round-trip | POST open/pull for crate/007_bake -> crate/011_blender | Existing configured Blender 5.2.0, isolated PID 80400, loopback 8371; normal scene untouched |
| Segmentation | c348bb58df13; corrected retry 739e4688c6c1 | First full segmentation aborted after RESULT with ucrtbase 0xc0000409. Scoped autocast retry passed: figure/013_parts, two parts and remaining body, 47.8 seconds |
| More 2D | 66af4eb41df8, ded586eb9e8b, ac42de90e8e8, c2ae0e9f81cc, f5712069f4ac; landscape/002_concepts through 006_layers | Style, depth, 2x upscale, redraw and three parallax layers completed; redraw drift/window/seam advisories passed |
| Faithful/retexture | 717fb4218447, ac8cf821045a; figure/012_trellis2 and 016_trellis2 | Faithful preview inspected; 10883 faces, 9.2 GiB peak, 453.5 seconds including load. Retexturing completed |
| Multiview | 53f22598a998; effigy_setup_multiview/006_trellis2 | Four-view generation completed; 11386 faces, 10.11 GiB peak, 255.8 seconds; coherent preview inspected |
| Texture detail | 25fe40797a19; figure/020_refine | Full Tile, 17 views; 12.05 GiB peak, 339.7 seconds; before/after views inspected, drift 0.91, seam delta improved 3.986 to 2.412 |
| Repose | 0b191f5976f2; effigy_setup_repose/003_canon | A-pose visibly restored from the wave input; pose gate passed, 9.17 GiB peak, 173 seconds |
| Video motion | 99c38c8a45fe; figure/018_mocap | 89 frames, 4.3 GiB peak, 126.6 seconds; original mp4v preview failed browser playback. H.264 retry 2ef7ae4dd3d0 -> figure/021_mocap completed in 123.4 seconds and played visibly in the browser |
| Automatic skin and captured motion | 2dc4b6908331, fa5042aa11a4, 674d2e03235d; figure/022_rig_skin through 024_sprites | Auto compared both engines and selected Blender, zero QA failures; retargeted video motion and 24-frame sprite preview visibly inspected |
| Final restart and delivery | c3d0b86dfbd8; figure/025_export | Started through run.bat, reopened saved history, exported animated Godot GLB and played it in the browser. Godot engine import itself is not claimed |
| Offline controls | HF status, borrowed DELETE, install refusal; backend/worker socket snapshots | HF status local, forbidden actions 403; observed backend/worker/isolated Blender endpoints loopback only. IAB shares the desktop app's network process, so its unrelated internet sockets cannot be attributed to Effigy. initial CSP blocked local blob textures; connect-src blob correction restored them. Final restart, export and animation playback left CSP violations at zero |

All asset paths above are under N:/generated/Effigy. Job lines remain in each asset's ordinary jobs.log; version metadata and outputs remain in the library. No extra evidence pack was created. The hidden isolated Blender session was closed after its successful round-trip; the owner's existing Blender process remained untouched. Subsequent Open in Blender launches the configured visible isolated session. Generated meshes retain small surface artifacts; these samples establish operation, not universal production quality.

## Steps

1. Launch at loopback 8370, open the UI, create an asset, restart, and reopen its saved versions.
2. Generate a 2D image, apply a supported style, upscale/redraw it, and create pixel art and parallax layers.
3. Exercise Fast, Faithful, and multiview generation; clean, simplify, unwrap, bake, retexture, and refine texture detail.
4. Repose a character, fit a rig, exercise both supported skinning approaches, and segment a part.
5. Apply a bundled clip, generate text motion, process a local motion video, and exercise animation editing/retargeting.
6. Export representative game/web/print formats, reopen inspectable outputs, create sprites, and exercise the Blender round-trip.
7. Observe actual CUDA execution, free/used memory, application errors, and visible outputs. Observe backend, worker, and browser connections throughout representative operations.
8. Record ordinary job identifiers and output references in RESULT. Never cancel another GPU workload; refuse or wait when resources are unavailable.

## Files to touch

- N:/generated/Effigy/
- scratch/
- docs/plans/local-gpu/05-runtime-acceptance.md
- steps/parts.py
- engine/geosam2/PATCHES.md
- steps/mocap.py
- steps/import_motion.py


## Verification

1. Each sample family must produce its expected inspectable output. Unexpected internet activity fails offline acceptance. Missing dependencies, memory pressure, and incompatible Blender behavior remain explicit incomplete items. Export-file inspection does not claim successful import into an absent game engine. Connection observation does not claim OS containment. No code tests, automated suites, extra evidence packs, or runtime model hashes.


## Risks

Procedural or generated samples can expose real capability failures; do not hide them by narrowing the promised feature set. Exhausted budget or a change requiring new dependencies stops the unit. RESULT stays at most 1024 characters and links ordinary outputs rather than duplicating logs.

## RESULT

All requested sample families exercised; job/output ledger is in Evidence. Assets persist under N:/generated/Effigy. Fast/Faithful/multiview, 2D styles/redraw/layers, mesh/textures, repose/parts, both skin engines, text/video motion, editing, sprites, exports/reopen and Blender 5.2.0 round-trip completed. SkinTokens-only stretch quality failed; auto job 2dc4b6908331 selected Blender with zero QA failures. GeoSAM crash and video playback compatibility were fixed and rerun successfully. Final restart/export c3d0b86dfbd8 and browser playback passed; CSP violations zero, observed owned sockets loopback only. IAB shares unrelated desktop networking, so OS containment is not claimed. No code tests or model hash sweeps.
