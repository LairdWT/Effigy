# Engine imports, headless: Godot 4.7.1 and Unreal 5.8 (2026-10-11)

The open "engine-import checks" of the handover, run on the reference laptop after the audit fixes and
with the app restarted on them. Recipe as in `m31.md`: Godot `--headless --path <scratch> --import`, then
`--script walk.gd` (an `extends SceneTree` script that instantiates each GLB and prints nodes, triangles,
materials, skeleton bones and animation clips); Unreal `UnrealEditor-Cmd <scratch>.uproject
-run=pythonscript -script=<py> -nullrhi -unattended -nosplash -nop4 -stdout -FullStdOutLogOutput` with the
default `AssetImportTask` (a scratch `.uproject` with PythonScriptPlugin + EditorScriptingUtilities, 8–45 s
per run). The exes' paths stay out of the repo (HANDOVER §10).

| asset (source version → export) | Godot 4.7.1 | Unreal 5.8 |
|---|---|---|
| the brick wall, refined (`by02_wall_boundary_brick_wall_bay` 024_refine → 026 godot, 028 unreal, both from today's app) | one `MeshInstance3D`, 5 964 triangles, 3.00 × 1.41 × 0.36 m, albedo + normal + ORM at 2048², a `StaticBody3D` with the hull. The GLB listed the ORM as two images (fixed since, `glb-orm-once`); Godot merged them itself (`Image_2-Image_3`) | one static mesh, LODs 5 964 / 2 982 / 1 490 / 779, one convex hull from `UCX_…_00`, `Material_0` with the base colour (sRGB) and normal textures, the ORM PNG beside the FBX to wire by hand (as in M31); Nanite on at import (M31's trap). **No duplicate ORM file any more** (the agent-findings fix; the pre-fix 027 export had `_orm_2.png`) |
| the viking, animated (`bench_faithful_viking` 530_anim → 533 unreal) | (Godot checked in M21) | a skeletal mesh with a 52-bone skeleton, a physics asset, two animation sequences (`500_motion` 5.00 s / 120 frames, `Walk` 1.67 s / 40 frames), one material with base colour + normal. Unreal merged the six part meshes into one skeletal mesh named after the first part (`Belt`). **The six `UCX_` hulls came in as stray static meshes** (Unreal uses UCX for static meshes only) |
| the cat, fox template (`cat` 031_anim → 032 godot, 033 unreal) | `Skeleton3D` 49 bones (root `root`), the skinned mesh 9 832 triangles, 0.61 × 0.99 × 0.85 m, albedo + normal + metal at 1024² (an older bake, no AO), an `AnimationPlayer` with `Idle` 1.38 s and `Walk` 1.04 s, a `StaticBody3D` with the hull | a skeletal mesh `cat` with a 49-bone skeleton, a physics asset, `Idle` 1.33 s / 32 frames and `Walk` 1.00 s / 24 frames, one material with base colour + normal; the same stray `UCX_cat_00` static mesh |

## 2D: a sprite sheet (M53, 2026-10-12)

The viking's pixel art from the M52 bench (`docs/bench/m52.md`: Idle, Walk, Jog and two Kimodo moves, 126 frames of
128 px, 15 colours) exported with `godot-2d` and `unreal-2d`.

- **Godot 4.7.1**, the `godot-2d` folder copied into a scratch project's `res://hero/`, `--import`, then a script that
  loads `bench_faithful_viking.tscn`: an `AnimatedSprite2D` with `centered = false`, `offset (-64, -123)` (the feet on
  the node's origin), `texture_filter` Nearest, `Idle_A` autoplaying; its `SpriteFrames` has the five animations with
  38, 20, 14, 24 and 30 frames at 12 fps, each frame an `AtlasTexture` of 128 × 128 on the 1536 × 1408 sheet. The
  `.tres` refers to `sheet.png` by a relative path and Godot resolves it beside the file. The moves that do not end
  where they began (the kick; the punch at 0.8 % of the height) play once (`loop: false`), from the sprites' tags.
- **Unreal 5.8**: the Paper2D sprite-sheet import (`.paper2dsprites` through `AssetImportTask`) asserts in the
  commandlet (`CurrentApplication.IsValid()`: the importer needs the editor's Slate application, which `-run=pythonscript`
  never starts). Left as the owner's editor check, as the UE retarget is: import the file in the editor, Create Flipbook
  per animation.

## Findings

- **A rigged model shipped a collision hull** in the Unreal and Godot profiles; Unreal imports it as a
  separate static mesh beside the skeletal mesh (a character gets a physics asset there, a capsule in
  Godot). Fixed in `steps/export.py` (`rigged-no-hull`, 2026-10-12: unless `collision: true` is sent, the export panel's choice): a source with a `skeleton.json` ships no hull
  in any profile, the export log says so.
- Unreal names a merged skeletal mesh after the first mesh node of the FBX (`Belt` for the viking's
  parts). Cosmetic; renaming in the editor is one click. If it bites, order the body first in
  `blender_ops/export.py`.
- The retarget onto Unreal's own mannequin is an editor-side step (IK Rig + IK Retargeter on the
  52 Mixamo bones that arrive); not run headless.
- Godot merges identical embedded images at import; the viewer and Blender did not (hence
  `glb-orm-once`).
