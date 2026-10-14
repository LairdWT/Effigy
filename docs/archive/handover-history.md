# Handover history (moved out of docs/HANDOVER.md, 2026-10-13)

History, not instructions: the session log before 2026-10-13, the next-session notes of 2026-10-06 to 2026-10-12,
the GPU bring-up plan and the pre-bring-up roadmap. The current state is docs/HANDOVER.md; decisions are in
docs/PLAN.md and docs/IMPLEMENTATION.md.

## From §1, Where things stand: the session log, 2026-10-12 and earlier

- **2026-10-12, end of day: the pixel-art character route, finished for a user** (main `cbedb60`):
  - **How-to**: `docs/howto/animate-a-pixel-art-character.md`, with `docs/howto/README.md` and the README's 2D rows
    and Double Dragon picture. It goes from a description or picture to a Godot `AnimatedSprite2D`, button by
    button, with a GDScript and the agent route.
  - **Animate this character is the visible next step**: an open section right under a still character's pixel art,
    holding the panel's main button (the export below it is now secondary), and after Make pixel art on its
    pictures. Not offered for wallpapers, backgrounds, portraits, icons or sheets (`Panels.animatable`).
  - **The redraw.** The owner's female viking (`a_female_viking_maid_in_harnisch_wit_2`) came out as cardboard.
    TRELLIS reads volume from shading, and her pixel-art picture made a standee 0.45 as deep as wide at the waist,
    printed front and back.
    - `canon` takes `look: "render"`: a softly lit 3D render in the standing pose, which keeps the clothes' length and
      footwear and draws a face. Without those two clauses, 4 of 4 seeds cut her floor-length dress short and left
      her barefoot, and 3 of 9 faces came out blank.
    - A Faithful model from the redraw is 1.0 as deep as wide, with a real back.
    - Animate this character now runs upload → prep → canon `{look: "render"}` → prep (about a minute) and opens at the
      redrawn cut-out. Without the `canon-flux` model it links to its Setup card.
    - **Redraw again** sits beside Generate 3D on a redrawn cut-out (same look, a random seed).
    - The hands are emptied, so a held weapon is not in the model.
  - **Tools ▾** says at which stage each tool opens ("at Prepare, once textured", "at Prepare (one still frame) or
    after Character (animated)", …) instead of "not for this checkpoint". In a 2D asset the 3D tools say "3D models
    only".
  - **MCP**:
    - `import_file(library_file="<asset>/<version>/<file>")` brings a 2D asset's picture into a new 3D asset through
      the API, and its result names the redraw as the next step.
    - `SKILL.md` now has the app's three move sets and six fighting sentences in full (they had drifted), the redraw
      route and flat sprites.
    - The owner's MCP clients need a restart to see the new parameter.
  - **Also found on her `_2`**:
    - Sprites for 2D on a prepared still model (no skeleton yet) gives one "still" frame per view.
    - Her drawn ground shadow became a 1–2 cm film around the boots; the redraw's plain background avoids it.
    - "Lit" darkens a picture-made texture a second time; "Flat" keeps its look.
  - **Checks**: targeted only (the owner's rule): ruff, `test_canon`, `test_mcp_server` (library_file), tsc, build,
    and Playwright for Animate, Redraw again, Tools, 2D and sprites. Real runs on scratch copies of her assets: the
    button end to end in a browser, Redraw again, 11 redraws over three prompt versions, one Faithful model from a
    redraw, and the MCP import. Full suites not run since mesh-gates.

- **2026-10-12: the 2D track** (research 15). Merged into main: the contract and M51 Pixelize (the other
  session's `2d-contract` + `2d-pixelize`), its CIEDE2000 colours (`2d-lab-palette`) and its `mesh-gates` (see
  below). **M50 Pictures** on `m50`: pictures from a description on the resident Z-Image (any aspect, 1–4, the
  `pixel` / `painting` / `drawing` styles as a new optional download group `styles`, a cut-out), a 2D asset in the
  UI (New asset → "A 2D picture or sprite", the pixel viewer, Make pixel art, a recolour), benched on the laptop
  (`docs/bench/m50.md`: 29 s a 1920 × 1088 picture warm, 8.3 GB torch peak, 11.4 GB on the card) and run end to
  end over the real API. The app needs `uv sync --group ml` (peft) through Setup's repair or a restart's check, and
  `npm run build`; the styles download from Setup's "2D styles" card. **M52 Sprites** (`m52`): a 3D character's
  animations rendered in whole pixels from the side (Tools → Sprites for 2D), in place, one scale per asset, then
  Make pixel art; the brawler-hero proof ran on the viking with two Kimodo moves (`docs/bench/m52.md`, the sheet and
  a GIF; 126 frames in 3.5 s). The owner asked whether the picture generator could make the sheet: tried, the
  character holds but the poses do not move (m52.md). **Then, the same day**: the 2D panels rebuilt in the app's own
  look (the owner: raw links and a different form layout; file buttons, stacked fields, the 3D view's frame and time
  bar now) and *Animate this character* (a 2D picture into a new 3D asset); **M53** (`godot-2d`: a SpriteFrames
  `.tres` + an AnimatedSprite2D `.tscn` standing on its feet, checked in Godot 4.7.1 headless; `unreal-2d` Paper2D,
  the owner's editor check; the 2D checklist); **move sets** (Brawler / Sword fighter from the pack, six fighting
  sentences) and one-shot moves; the viking's 21-move brawler set ran end to end in under a minute (m52.md). The
  owner's goal: sprite animations for a Golden Axe / Double Dragon game. Next: tiles and props (M54), parallax
  layers (M55), the pixel editor (M56/M57). Done after it: the joint loops judge elbows and knees only (no bench
  rig flagged), and a clip that never moves after a retarget is named on the animated model's panel.

- **2026-10-12: mesh gates** (`mesh-gates`, merged 2026-10-12 with today's main): four ideas from the owner's
  sidetask review of `witnesstodark/mr-mak-workspace` (its bundled `img2threejs`, Apache-2.0, and its viewer,
  MIT), reimplemented, nothing copied: `validate` gets `self_intersection` and `parts_apart` (ray parity);
  `rig_skin` gets `joint_loops` (vertex bands along the bone at each joint); `parts` views report the views
  with a hole through the model (`metrics.holes`, a flood fill of the render's alpha); Wireframe on a quad
  mesh draws the quads. IMPLEMENTATION "Mesh gates" has the details. Checked with the unit tests and one
  browser test on a synthetic cube; **not run**: a real Blender QuadriFlow GLB (the quad pairing assumes the
  exporter's consecutive triangles; the laptop's first quad remesh with Wireframe ticked is the check) and
  a real character's `joint_loops` (the 0.35 window and 3 bands are img2threejs's numbers, tune on the
  bench characters if they flag dense meshes). The CIEDE2000 palette mapping is on `2d-lab-palette`, on top
  of `2d-pixelize` (section 2's merge order: contract → pixelize → lab palette). Checks here: `uv run pytest`
  365 passed, 47 skipped, the `.venv-ml` export test deselected, and `test_api::test_install_runs_download_models`
  failing on the environment alone (it needs 18 GB free on C:, this machine has 16); Playwright 42 passed with
  the two known thumbnail-404 failures and three load flakes that pass alone (pytest ran beside the suite).
  **Checked on the laptop at the merge**: Wireframe on the dwarf's real QuadriFlow remesh (`570_remesh`, 7265
  quads) draws exactly 29 060 quad edges, a clean grid; validate with the two new items takes 0.7–1.5 s on
  14–20k-face library meshes. Two limits seen: `self_intersection` samples closed components only, and a
  Faithful body is usually open, so on the bench characters it tests small closed pieces (20–40 samples) or
  skips; `joint_loops` flagged all 16 bench rigs at Spine/Spine1/Spine2 (no vertex within the window: the torso
  is wider than 0.35 of a spine bone), now not judged (`_rig.joint_loops`, an empty window). Still flagged after
  that, on 10 of 16: Neck, Head, shoulders, hips (2 bands, where the window catches a slice of a wide part);
  elbows and knees never. Tune the window or limit it to limb bends before trusting the warning.

- **2026-10-12, last: the UX review is built** (`docs/ux-review/2026-10-12/`). Pass 2 reviewed and merged
  (`cb9fc97`), Pass 3 (`398c8b5`: the export package to a folder, the batch preview, the library's view kept, Setup's
  cards, links and one login) and Pass 4 (`ux-pass4`: field outlines, announced errors, the skip link and headings,
  the keys as a list in the animation editor, card management under More, Select assets, and **Recently deleted** with
  Restore, backed by `GET /api/trash` and `POST /api/trash/{name}/restore`). IMPROVEMENTS.md's checkboxes say how each
  item was done. Checked with targeted browser tests and the library/API tests only (the owner runs the full suites on
  request). After the merge: `npm run build` in `ui/` and **restart the app** (two new server routes). Left: NVDA and a
  real 200 % zoom.

- **2026-10-12: import an animation** (owner): FBX, GLB, glTF or BVH on a Mixamo, Unreal (Manny, Quinn) or Kimodo
  skeleton onto a character skinned here, from the Import page (pick the character) or the Animate panel; the new step
  `import_motion`, the retarget reads Mixamo names (IMPLEMENTATION "Import an animation"). Earlier the same day: the
  app's port in Setup (App address), the UX review's Pass 1 and its follow-ups (the timeline's canvases, a result
  during an unsaved edit, the time bar's glyphs).
- **2026-10-12, the work machine's session: its wins, in one place** (written before the laptop session merged
  `ux-pass2` as `cb9fc97` and took this note in; all on the owner's work machine `C:\CODE\Effigy`, a
  code-only clone: nothing GPU-, Blender- or model-dependent ran). The owner's other session merged most of it the same
  day: `main` at `2dd9ce5` holds mesh-gates, the Lab palette with `2d-contract` and `2d-pixelize`, ux-pass3, ux-pass4,
  import-animation and the Pass 1 fixes; **`ux-pass2` is the one branch left** (item 5):
  1. **UX Pass 2 built** (`ux-pass2`, `f5e06ab`): five tasks instead of fourteen stages, the Tools ▾ menu, the main
     action first in every panel, the preparation states, readiness links, the renames. The bullet below has it all.
  2. **The Mr. Mak sidetask** (`witnesstodark/mr-mak-workspace`, read in a scratch clone, nothing run): a Tauri
     desktop shell for CLI agents plus prompt workflows for paid cloud generators; its one algorithmic payload is the
     bundled `img2threejs` (Apache-2.0, a code-built three.js reconstruction pipeline with pure-stdlib Python gates).
     Verdict: nothing to lift as code, six ideas worth having; the owner took four (item 3 and 4 below). **Left on
     the table, both small and worth a later PR**: (a) a "clips that play silently" gate for `anim` (fail a retarget
     whose sampled bone transforms never change across a clip, plus bind-restore after stop and every visible mesh
     bound: the silent-failure class a bad bone map produces; Effigy's skin QA has nothing of the kind); (b) clip
     measurement for imported animations (travel, rise, speed, hand and foot ranges as fractions of the figure height
     → idle/walk/run/jump/in-place/gesture labels, and the loop flag from whether the last pose returns to the first,
     not from root travel). Their prompt skills (fal.ai, Higgsfield, character sheets) are not for Effigy (owner: local
     only); their video keyframe extractor, delivery hash manifest and Godot project detector are thin wrappers.
  3. **Mesh gates** (`mesh-gates`, `b5e74c5`; merged on `main` as `2dd9ce5`): `validate` items `self_intersection` and `parts_apart` (ray
     parity, `skip` when nothing is closed), `rig_skin` item `joint_loops` (advisory, outside the engine ranking),
     `parts` op `views` → `metrics.holes` (a flood fill of each render's alpha) with a note in the Parts panel, and the
     viewer's Wireframe drawing a quad mesh's quads. IMPLEMENTATION §3.9 and its "Mesh gates" section have the
     numbers; the step reviewer's findings (an inward winding read as a fold, a touching part read as sunk, an
     uncapped cost, the loop rule passing irregular meshes) are fixed in the commit.
  4. **CIEDE2000 palette mapping** (`2d-lab-palette`, `5f51786`; merged on `main` as `95a9148`, with `2d-contract`
     and `2d-pixelize`): pixelize maps colours in
     Lab by ΔE00 instead of RGB distance (`_pixel.srgb_to_lab`, `delta_e00`; Sharma's pairs in the test).
  5. **What is left to merge**: `ux-pass2` alone. Its `be0bc56` merge of `main` predates mesh-gates, so merge `main`
     once more; expect conflicts in `ui/src/main.tsx` (mesh-gates' `FIXES` and `SKIN_CHECKS` rows, the `ViewerPane`
     `quads` prop and its effect, the Parts panel's note, and the Checklist's `<li>` line, which Pass 2 re-indented
     inside a `<details>`: keep Pass 2's structure with mesh-gates' two changes, "–" for a null value and the fix hint
     only on warn/fail), at the end of `ui/tests/smoke.spec.ts` (keep both tests), in `docs/IMPLEMENTATION.md` near the
     UX section (keep both) and in this file's §1 (keep both bullets). After the merge, on the laptop: `npm run build`
     in `ui/`; the merged steps apply at the next job, no server restart.
  6. **Checks run here** (every number honest): Pass 2 and mesh-gates each had the full Python suite and the full
     browser suite; see their bullets. **Environment facts of this machine**, not defects: `UI loads…` and `Setup
     shows capabilities…` fail on thumbnail 404s (no Blender); `Animate: a video becomes a motion…` is a harness flake
     (5 of 6 runs fail on unchanged code: its mocked `qa.json` sometimes never resolves); `test_api::
     test_install_runs_download_models` needs 18 GB free on C: (16 here); `test_mcp_server::test_export_to_folder`
     needs `.venv-ml`; running pytest beside the browser suite makes three or four more tests time out, so run them
     one after the other; the working tree is CRLF under `core.autocrlf` (scripted patches must keep the file's
     endings); `ruff check .` stays red on `main` for the review's `verify-review.py` (owner's call).
- **2026-10-12, later: UX Pass 2 built** (`ux-pass2`, pushed, unmerged; the same code-only clone, nothing GPU-dependent
  run). `docs/ux-review/2026-10-12/PASS2-NAVIGATION.md` with the owner's five decisions, as one PR; its §8 lists where the
  build departs from the design, IMPROVEMENTS.md's Pass 2 boxes say how each item was done, IMPLEMENTATION.md's UX
  section has the summary. **What changed**: `ui/src/workflow.ts` (`TASKS_3D` Reference · Generate · Prepare ·
  Character · Finish, `TASKS_2D` for `asset.kind === "2d"`, `taskOf`, `prepState`; `STAGES` and `stageOf` are gone),
  `main.tsx` (the row with an "Imported model" chip and a Tools ▾ menu on a native `details`; `Actions` leads every
  checkpoint with its main action, the tools and the rig form under disclosures, Export right after a check; the
  clean/simplify/unwrap/bake states completed · active · interrupted · historical, so a checked chain never says it
  stopped; the setup link as the main action when concept or generator files are missing, a restricted export
  disabled; the animation source as radios, ready-made by default; "Attach to skeleton", "Remove baked shadows", the
  specialist fields under Advanced with visible help, the long help under Help), `styles.css` (`.chip`, `.tools`,
  `.modes` in two columns), `api.ts` (`Asset.kind`), `anim/Editor.tsx` (its instructions under Help). **Checks**:
  `ui/tests/workflow.spec.ts` (the rules on fixture lineages) and four new browser tests (the row at 1280 px, the
  preparation states with the chip, the acceptance walk at 1280×720, readiness); the existing tests adjusted where
  controls moved (the tools and the rerun settings under disclosures, the renames, the Tools menu carrying the panel's
  disclosure names, the generator mocked as installed because UX-09 now replaces Generate 3D with its setup link when
  the files are missing, a failed step that leaves no version). Playwright here: 51 browser tests, 47 passed and 4 failed in the last full run; two are the known thumbnail-404 failures (`UI loads…`, `Setup shows capabilities…`, red on `main` too), one was the texture-detail test's own race (it moved on while its job's result was about to open; the test now waits for it, then passed three times in a row) and one is `Animate: a video becomes a motion…`, a pre-existing harness flake (its mocked `qa.json` sometimes never resolves, so the skin panel stays on "Loading the checks…": 5 of 6 runs fail on the code *without* this change, 1 of 3 with it; the owner's call whether to fix the mock). `uv run pytest`: 363 passed,
  47 skipped, `test_export_to_folder` deselected (needs `.venv-ml`). `npm run build` green. **Not run**: anything with
  a GPU, Blender or models; whether the Tools ▾ menu works out in use is the owner's call on the laptop (tabs are the
  fallback). After the merge: `npm run build` in the laptop checkout's `ui/`; no server code changed, no restart.
- **2026-10-12, the 2D studio and the UX review (a session on the owner's work machine, `C:\CODE\Effigy`: a
  code-only clone, no models, library, ML venvs, Blender or GPU; `.venv`, `ui/node_modules` and Playwright's
  Chromium installed; everything GPU-dependent is "not run").**
  - **Research 15** (`docs/research/15-2d-studio.md`, five agents, licences read at their sources 2026-10-12): the
    plan to make Effigy a 2D/3D studio. **Owner decisions folded in**: everything **purely local** (no external
    editor: Aseprite, Pixelorama and the like are orientation only, never launched, embedded or written to); 2D
    assets are *created* here, **animating a picture is left to the user's tools** (no video models); character
    sprites come from the 3D rig (`sprites`, M52), hand-made frames from the in-app pixel editor (M56/M57);
    pixel art is post-processing (`pixelize`, M51); the Z-Image `image` op for stills (M50); exports for Godot
    first (M53); milestones M50–M58 in the note's §8, the contract rows in IMPLEMENTATION §3.2.
  - **Built and pushed, unmerged**: `2d-contract` (research 15; the 8.0 contract: `asset.json.kind: "2d"`, the §3.2
    rows for `concepts` (image, tile), `pixelize`, `sprites`, `layers`, 2D validate and exports; MCP
    `create_asset(kind=)`, `import_file(kind=)` skips `prep` for a 2D picture) and `2d-pixelize` on top of it (M51:
    `steps/pixelize.py`, `_pixel.py`, `_sheet.py`, `palettes/pico-8.gpl` (CC0, `licenses.yaml`); thumbs and `look`
    show pixel art with whole pixels; runnable through the API and MCP, **no panel yet**; `tests/test_pixelize.py`).
    Merge order: `2d-contract` → `2d-pixelize`. Full suite there: 363 passed, 46 skipped.
  - **UX review** (`docs/ux-review/2026-10-12/`, the owner's review agent; 15 findings, 4 passes). **Pass 1 built and
    merged** (`32f24f2`, UX-01..04, UX-08: the dirty guard `useUnsaved`/`leave`, History and Licences as one docked
    region in its own column, the panel's grids shrink, the timeline gives way; three browser regressions). **Pass 2
    designed**: `PASS2-NAVIGATION.md` on `ux-pass2` (pushed). **Owner decisions 2026-10-12**: (1) the task names
    **Reference · Generate · Prepare · Character · Finish** approved; (2) the optional tools as a **Tools ▾ menu**,
    tried first — if it does not work out, fall back to tabs; (3) the renames **"Skin it" → "Attach to skeleton"**,
    **"Shadows only" → "Remove baked shadows"** approved; (4) Pass 2 as **one PR** (2a + 2b together); (5) the 2D row
    **Picture · Pixelize · Layers · Tiles · Edit · Finish** approved. Sequencing (owner): UX Pass 1 first, **the 2D
    UI arrives with Pass 2** (`TASKS_2D` in the same row model), the 2D backend continues meanwhile.
  - **Environment facts of this checkout**: `test_mcp_server::test_export_to_folder` fails here (export runs in
    `.venv-ml`, absent); Playwright: 44 passed, two fail on `main` too (`UI loads…`, `Setup shows capabilities…`:
    console 404s for thumbnails, no Blender to render them). **`ruff check .` is red on `main`** since the review
    commit: `docs/ux-review/2026-10-12/evidence/verify-review.py` uses `re.M` (FURB167, two lines; or exclude
    `docs/` in ruff's config) — the owner's call, not touched. The owner's other session merged `app-port` (the
    port is configurable) while this one worked: **fetch right before every push**.
- **2026-10-11, late: the open items after the audit.** Merged: the name sweep (`693bfa9`: the research notes and
  the engine patch say Effigy, no home path in §11b), bake's GLB lists the ORM once for both its slots
  (`6becd09`, `glb-orm-once`; the cold-start pre-flight test pins its RAM reading), and `rigged-no-hull` (a rigged
  source ships no collision hull: Unreal 5.8 imported it as a stray static mesh). **The engine-import checks are
  done** (`docs/bench/engine-import.md`): the refined wall, the animated viking and the fox-template cat in
  Godot 4.7.1 and Unreal 5.8, headless; the retarget onto Unreal's mannequin is an editor-side step. The library
  sketch of §11 is fully built (M28 + M42). Still open and the owner's: the `delight` default (the sheet in
  `docs/bench/m43c.md` says 0.5), the clean-VM install of the portable zip, the refine keep/drop and 4K (a
  bench with the lite Tile, to run in the owner's terminal), the test spider/snake mesh contacts.
  **The owner's agent's fence report** (`docs/audit/2026-10-11-agent-fence/findings.md`, untracked), closed
  2026-10-12 in three merges: `fence-quick` (items 4, 5, 7, 9a: a `uv_overlap` item in validate, `{"preset":
  name}` and no-op-means-generate for trellis2, the brief keeps a prompt's own view, the weld note in the guide),
  `fence-geometry` (items 1–3: `straighten` levels only onto a floor covering 60 % of the footprint, the fence's
  18° sliver no longer; `bake {"detaper": true}` undoes a picture's taper after the sampling, the tall end kept;
  `remesh {"close": metres}` shuts slits before simplifying) and `blender-pull-version` (item 6:
  `pull_from_blender(asset, version)`, the note naming what else was open, `close_in_blender`). Left from it:
  item 8 (the unseen back of a thin panel is torn: two-view generation or a mirror option, a research item), 9b/c
  (the unwrap's island count, the look sheet's lighting). The prepare forms expose all three since 2026-10-12
  (`ui-fence-options`: Level it and turn it square, Close slits up to (mm), Square a flat prop's perspective taper).
- **2026-10-11, evening, merged on the owner's go: the audit's Mediums and its Low.** BE-002 + BE-004 + BE-005
  (`f854d94`: one version allocation and one metadata change at a time, a step that exits non-zero after its
  RESULT is a failure) and UI-003 .. UI-008 (`1e7c30e`: a reconnect reselects a surviving version and ends a
  job the restarted server lost; Compare reads the checklist itself; the clip picker hears the keyboard; a
  cleared viewer stops and drops its rig, a disposed one its gizmo). With these all 19 findings of
  `docs/audit/2026-10-10/06-findings.md` are closed (notes in `IMPLEMENTATION.md` beside the M45 bullet; the
  audit folder stays untracked). The app still needs its restart for the server-side fixes (`run.bat`).
  Known and left: `delight` stays 0 by default.
- **2026-10-11, later, merged on the owner's go: the audit's last two High findings.** BE-006 + BE-007 (`07331d6`: a
  warm resident run reads what other programs took since the worker went idle, the serve request carries the
  job's budget and the worker re-caps itself; a cancel during the spawn evicts the fresh worker) and UI-001 +
  UI-002 (`180cc5d`: the skeleton, marker and animation editors keep their edits when a save is refused and
  close only on a new version; the animation editor can save a return to the base). All seven High findings
  are closed; the Mediums (BE-002, BE-004, BE-005, UI-003..UI-006, UI-008) and the Low (UI-007) are next, in
  `HANDOFF.md`'s packages. The app still needs its restart for the server-side fixes (`run.bat`).
- **2026-10-11, merged on the owner's go** (`agent-findings`): the owner's second agent (connected over MCP with
  Setup's absolute config; the relative `.mcp.json` block fails from any other folder, README and SETUP say so)
  made a brick-wall bay end to end (`by02_wall_boundary_brick_wall_bay`, 24 versions, Godot and Unreal exports,
  refine judged worth keeping) and reported findings, fixed: `read_file` reads YAML (e346054); a prop's concept
  prompt no longer says "full body"; the size gate lets a long object fill the frame's width; `clean`
  `straighten` (default false: the floor levelled from the hull's largest downward plane, the footprint's
  smallest bounding rectangle squared, long side on X; a prop from a three-quarter picture comes out at 45° by
  construction, Faithful being pixel-aligned to that camera; the picture's perspective taper is not a rigid
  motion and stays); `refine` plans no top-down view for a model wider than tall (it invented tiles on the
  coping, and on the chest's lid in M43b); the FBX export writes a picture packed twice (a bake's ORM, which
  trimesh embeds as metallic-roughness and as occlusion) once; the agent guide: positive phrasing, an imported
  file has no lineage (edit through Blender), `refine` for the texture's weak side. Closed 2026-10-11: the GLB
  listed the ORM twice (two images and textures over one buffer view; `glb-orm-once`: one of each).
- **Cloud session 2026-10-10/11, branch `ccr-3bd14478-pui9wd`, merged with main's state on 2026-10-13, then into
  main the same day on the owner's go**: the owner asked for UI-001, BE-006/007 and then the open Phase-3 items, "all items you can do without a
  GPU", validation on the laptop afterwards. **UI-001, BE-006 and BE-007 were fixed on main meanwhile** (audit-ui-editors,
  the warm worker's idle baseline, the `--serve` `budget`): the merge keeps main's versions and drops the branch's
  (`jobs._admit`, the `_spawn` cancel guard; their descriptions below are history). What the branch adds: M46 generic rigs
  (renumbered **M59** at the merge: main's M46a–c are the bigger GPUs), the batch mode, the texture items, the thumbnails,
  the login message, the scrub; at the merge the stale `.ws-title h2` selector of the "late answer" smoke test followed
  the title to `h1` (it failed on main as it stood). Seven commits at first, each with its tests green here (pytest 343 passed, the two
  failures below are this container's; Playwright 37 passed, two failures are this container's resource 404s on untouched
  main too; ruff clean; `tsc` clean): **UI-001** (the three editors' saves run through `chain` and close or clear only
  on a version; a failed save keeps the edits), **BE-006 + BE-007** (a warm resident worker is pre-flighted on the live
  nvidia-smi reading and gets this job's `budget` in every `--serve` request, §3.1 extended; a refusal with a warm
  worker evicts it and measures again, `jobs._admit`; `_spawn` kills a process whose job was cancelled while
  `Popen` ran, worker or one-shot), **M46 generic rigs** (`rig_skin {full: true}`: SkinTokens' own skeleton and skin
  for an object with moving parts, "Something else" in the Rig panel, `template: "generic"`, no clips; plus its step
  review's fixes), **CLI batch mode** (`tools.bench --export <profile> --to <folder>`, README), **texture items**
  ("Redraw this view" in the Detail panel: the window the 3D view frames plus a description through `refine`'s
  `views`, the masked edit without a new model; a 4K checkbox; the `detail` metric now structure-weighted, bench rerun
  open), and the plan's stale lines (PLAN §7 states per item, §10; IMPLEMENTATION's Phase 3 header). **Decided and
  recorded, not built**: SAM 3D Body as a second video-to-motion engine (licence was checked 2026-10-08; GEM-X covers
  it), the own Blender bridge add-on (ARCHITECTURE §4's trigger has not come up), a model-based masked inpaint
  (research 14 §5). **Needs the owner**: (1) PLAN §6: a generic rig has no Blender bone-heat alternative to SkinTokens'
  training-data provenance; the option ships saying so, drop it by deleting its `RIG_KINDS` row if unwanted; (2) the
  GPU checks listed under M45 "As built" (BE-006/007 lines), M46 "Acceptance", and the m43b bench rerun for the new
  `detail` number; (3) the restart of the app for `server/jobs.py` and the `--serve` request's `budget` (the
  `steps.trellis2 --serve` worker must be restarted too: the old one ignores the field). The remaining audit Mediums and
  the Low were not touched (the audit folder is untracked and not in the cloud clone). Two tests fail in that container
  only: `test_cancel_takes_the_steps_children_with_it` (the sandbox does not deliver SIGTERM to a grandchild) and
  `test_export_to_folder` (no `.venv-ml`). **Continued 2026-10-11** in the same session: the three unreviewed commits
  got their step review; the Setup card says "Needs a Hugging Face login first" only while the account may not read the
  gated repo (`/api/hf`'s access; the status poll answers the unknown status instead of a 503 without `.venv-ml`); a
  missing thumbnail is a blank PNG, not a 404 (the library's and the history's `<img>` logged a browser error for every
  brief, check or unrendered mesh; the smoke tests count those, and CI has no Blender: the two Playwright failures
  above were that); `test_export_to_folder` skips without `.venv-ml`; the old name is gone from the tracked files and
  §11b no longer names the owner's token file or user folder.
- **Merged 2026-10-10 night on the owner's go** (six branches, disjoint files, each with its regression test and its
  suite green before the merge): **the AO of torn double shells** (`9902c51`, `docs/bench/m43c.md` "fixed in bake",
  `m43c_ao.jpg`: every Faithful character kept an inner shell that showed black through tears in the outer one;
  `_bake.ao_faces` opens enclosed faces, `_bake.fill_dark_islands` fills small dark islands of the AO map; on the
  six bench characters the bright texels at AO < 0.1 fall from 15–43 % to 0.3–3.3 %, the props are untouched,
  AO +0.3–0.5 s; four per-face rules tried and dropped, each measured there) and **five of the audit's seven High
  findings**: BE-001 user files served inert (`de63b84`), BE-003 a pull keeps replaced and mixed sources'
  lineage (`a16f9e6`), PIPE-002 one PNG per packed image in the FBX export (`8928e0a`), OPS-001 + OPS-002 the
  model move's staging name and rollback (`c5732b3`), PIPE-001 the cleanup drops a part only when every vertex
  is inside (`e0caf21`). **The app needs a restart** for the server-side ones (`/files` headers, the pull, the
  move; `run.bat`); the step changes (bake, clean/remesh, export) apply to the next job as they are. The
  library's existing bakes keep their old AO: re-bake an asset to get the new one (a new version).
  **Open from the audit**: UI-001 (a failed save in the animation / skeleton / marker editors drops the edits:
  `anim/Editor.tsx` closes on any result of `onSave`; the skeleton and marker handlers clear their history
  before the POST; fix: close and clear only on a version result), BE-006 + BE-007 (warm resident jobs skip
  the live VRAM check and keep their startup cap; a cancel during an unregistered spawn leaves the worker:
  `server/jobs.py` `_preflight`, `_spawn`, `steps/_common.py` the cap), the 11 Mediums and the Low
  (`docs/audit/2026-10-10/06-findings.md`, packages in `HANDOFF.md`). The audit folder is untracked on purpose.
  **Worktrees** `.claude/worktrees/{m43c,readme}` were removed at the end of the session (their junctions to the
  venvs, models, Blender and `ui/node_modules` first); the merged branches are still on origin.
- **Merged 2026-10-10 evening on the owner's go: M43c** (`2c28a8e`, "Remove baked shadows": `refine`'s `delight`
  divides the bake's AO back out of the base colour, alone in ~2 s with `views: []`; the default stays 0 until the
  owner picks one from `docs/bench/m43c.jpg`; the same PR fixes refine's closing pass, which rewrote bake's edge
  texels on every run) and **the public-ready README** (`22d8855`: badges, a capability grid, mermaid diagrams;
  SETUP.md without the private-repo wording). The app needs no restart (no server code changed); `ui/dist` was
  rebuilt in the checkout. **Found, not fixed**: a Faithful mesh's inner-shell faces show through torn outer
  shells and come out black in the AO (the pirate's sleeves and face; `docs/bench/m43c.md`): a clean/remesh item
  (drop interior layers / close the shell), not a bake one. **The owner's audit** (a separate review agent,
  2026-10-10) sits untracked in `docs/audit/2026-10-10/`: 19 findings against `47d0d7a` (7 High, 11 Medium,
  1 Low; `06-findings.md`, fix packages in `HANDOFF.md`, reproduction scripts in `evidence/`), none fixed yet; the
  High ones: HTML in a model zip runs in the app's origin (BE-001), a Blender pull can lose licence lineage
  (BE-003), warm resident jobs skip the live VRAM check (BE-006), a failed editor save drops the edits (UI-001),
  clean deletes intersecting visible parts (PIPE-001), FBX export overwrites same-role textures (PIPE-002), a
  model move deletes an unowned `.effigy-partial` sibling (OPS-001). Before the repo goes public: ~~the old name
  is still in 8 tracked files~~ and ~~§11b below names the owner's token file and user folder~~ (both scrubbed 2026-10-11).
  The fresh clone (§11b) is done: the checkout is `D:\CODE\Effigy`, models and library moved into it.
- **Merged 2026-10-09 on the owner's go** (`0f15252`): **M37** animation editor (a time bar under any clip; a
  correction layer of keys with falloff, trim, speed, loop, ground, in place and smoothing, saved as
  `anim_edit` versions, the same maths in the preview and the bake), **M38** animation tools (foot locks with
  leg IK, IK drag, hips moves, curves, motion paths and onion skins, zoom), **M39** import (FBX, glTF/GLB, OBJ,
  USD, STL, PLY or a zip; a known skeleton and its clips kept), every underlined link a compact button,
  **M40** agent access over MCP (`mcp/effigy_server.py`, server `effigy`: a workflow tool set with `look`
  previews, import from a path, bounded jobs, export into a folder; Setup → "Connect an agent"; the API answers
  only `127.0.0.1`/`localhost` requests without a foreign Origin; Ask Claude removed) and the **rename to
  Effigy**. Then (`91c7423`) the **internal names** too: settings `LT2_*` → `EFFIGY_*` (`EFFIGY_LIBRARY`,
  `EFFIGY_MODELS`, `EFFIGY_BLENDER`, `EFFIGY_BLENDER_MCP_PRO_DIR`, …; the owner's user variable copied to the
  new name, the old one left), the bridge `mcp/effigy_server.py`, the subagents `effigy-*`, Blender's
  `EFFIGY_` collections and tags (a scene opened before still pulls), the packages `effigy` / `effigy-ui`.
  Kept: the old checkout folder. **The code moved to the new private GitHub repo
  `SifuInTheShell/Effigy` on 2026-10-09** (full history; `origin` points there; the old repo is left behind). The app needs a restart
  (`run.bat`); an agent connected earlier (as `lt2`, or to `mcp/lt2_server.py`) is re-added from Setup →
  "Connect an agent". **Then merged on the owner's go (2026-10-09): M42** the library rework, the rest (turntable
  thumbnails on hover, compare two versions, licence chips + a Licences panel, tags, batch export into a folder)
  **and M44** duplicate clips in the animation editor (Duplicate / Rename / Delete; a layer's `from`). **Merged 2026-10-10 on the owner's go: M45** GPU and RAM safeguards (a measured VRAM need per step, the
  per-process cap, a pre-flight for VRAM, other programs' VRAM and host RAM, a model switch in a fresh process;
  docs/bench/m45.md), **M41** all five creatures (kaiju, shark, dragon, spider, snake: every Mesh2Motion rig is
  in; a tilted flat mesh is stood up; docs/bench/m41a–e) and **M43a+b** (bake: supersampling, AO, seam
  levelling; the `refine` step with the lite Tile, Setup card "Texture detail"; docs/bench/m43a–b). Open after
  M43b: a per-view keep/drop for invented detail, a real detail metric, 4K for characters, M43c delighting. Rule since the laptop froze
  on 2026-10-09: ONE heavy job at a time (GPU model runs, full test suites, benches, Blender batches), never
  parallel agents with heavy runs. Still open besides: the clean-VM check, a UE5 retarget check, an engine
  import of a creature.
- **Branches on 2026-10-08**: `main` has everything through M34 (M30 and M31 merged on the owner's go
  on 2026-10-08; the app needs a restart once for the resident motion step and the `.venv-parts`
  route). **M31b** merged on the owner's go the same day. **M32** and **M34** (motion from video, GEM-X) accepted and merged 2026-10-08 (the app needed a restart for
  the `mocap` route; `.venv-gemx`: `GIT_LFS_SKIP_SMUDGE=1 UV_PROJECT_ENVIRONMENT=.venv-gemx uv sync --frozen --group
  gemx`). Next, the owner's order: **M35 setup for everyone** (M35a space, M35b install and repair, M35c first run),
  then M33 print split, then creature skeletons. Merge only when the owner says so. **M35a** (Setup, Space on disk:
  a bar per drive, one even table per kind with safe cleanups, a low-space gauge in the top bar) accepted and merged
  2026-10-08 (the app needs a restart for the `/api/storage` routes); next **M35b**. **M35b** (install and
  repair: a card sets up its environment too, "installed" checked against `tools/models_manifest.json`,
  Repair, queued installs with progress) accepted and merged 2026-10-08 after the owner's Repair clicks and a
  full check of the install (192 files, 83 hashed = 141 GB all matching; every environment imports with
  CUDA; the unused HF-cache copy of GeoSAM2 from the M31 spike deleted). **M35c** (the guided first run:
  machine check, models folder chosen and movable, presets, the Hugging Face token pasted in the app, one
  install queue; the first start opens it by itself) accepted and merged 2026-10-08; the app needs a restart.
  M35 is done. **M33** (print split) accepted and merged 2026-10-08: a parts version prints as closed
  solids that fit together (the cut made in the volume); HoloPart out on its licence (HunyuanDiT code, as
  TripoSG). **M36** (creature skeletons: Mesh2Motion's fox, horse and bird fitted, skinned and animated with
  their own clips), "Edit in Blender" only on versions with a model, and the generation background (a dark
  subject on grey for Fast: a black cat's back no longer comes out missing) merged 2026-10-08 on the owner's
  go; the creature clips come with `python -m tools.download_models clips`; the app needs a restart.
- **Branch**: `main` has everything through M24 (merged 2026-10-06: the M22 bench, the skeleton and
  marker editor, the faces from the image with the 4× upscale and the local colour match, the three code
  reviews' fixes). M25 (the UX pass: panel texts, placement help for joints and markers) accepted and merged
  2026-10-06. M23b (thin and dark features in generated geometry) accepted as is on 2026-10-07 and noted
  for a version 2 (PLAN Phase 4, §9 below). **M26 Animate from a text prompt** (Kimodo) and **M27 one tab per step** are accepted and merged
  (2026-10-07: the owner's viking `520_anim` with a custom motion "works foundationally"). Kimodo is NVIDIA's model, not an owner plugin: the clone at
  `D:\CODE\kimodo` is upstream, unmodified. The `kimodo` model group (16 GB, gated Llama 3) is
  downloaded on this laptop.
  Work on a branch per milestone off `main`; ask the owner before merging back.
- **CI is manual** (`workflow_dispatch` on `ci.yml`, `package.yml`, `wheels.yml`): the owner's build
  minutes are limited. **Never trigger a workflow or add a push trigger unless the owner asks.** Run the
  checks locally (section 5) before every push.
- Checks run on the laptop for the last commits: ruff clean; `test_mesh_checks`, `test_blender_ops`,
  `test_pixal3d_patches`, `test_trellis2_step` green; UI build + Playwright 6/6. CI not run since the
  bring-up (the owner's minutes).
- **Owner status**: works from this dev checkout (`D:\CODE\Effigy` since 2026-10-10, `run.bat`), Faithful is the
  default engine, all model groups are downloaded (incl. `multiview`, `pose`, `canon-flux`).
- Export priority: **Godot and Unreal**; Unity is a nice-to-have.


## From §2, What to do here: the earlier next-session notes

#### Earlier next-session note (2026-10-12 morning, after the UX Pass 2 / mesh-gates session)

1. ~~**Merge `ux-pass2`**~~ merged 2026-10-12 (`cb9fc97`) with Passes 3 and 4 after it (section 1). Try the Tools ▾
   menu in use; fall back to tabs only if it fails there.
2. **The 2D track** (research 15): ~~the contract, M51 Pixelize, the Lab palette~~, ~~M50 pictures~~, ~~M52
   sprites~~ and ~~M53~~ are merged (section 1). Was next: **M53** the Godot 2D export (`SpriteFrames`/`TileSet` `.tres`, a
   `.aseprite` file, `.paper2dsprites`; a 2D `validate`; the Godot 4.7.1 headless check of the viking's sheet), then
   M54 props and tiles, M55 parallax layers, M56/M57 the pixel editor.
3. **The laptop checks of mesh-gates**, run 2026-10-12 at its merge (section 1's mesh-gates bullet): the dwarf's
   QuadriFlow remesh shows exactly its quads; validate takes 0.7–1.5 s on 14–20k faces; `joint_loops` flagged every
   bench rig's spine (fixed: an empty window is not judged) and still flags necks, heads, shoulders or hips on 10 of
   16 (never an elbow or knee): tune the window or limit it to limb bends before trusting the warning. Not run yet:
   an M43c character with an inner shell (`parts_apart` near 100 % expected) and the largest library mesh.
4. ~~**Small follow-ups from the Mr. Mak review**~~ done 2026-10-12 (`675f3d3`): the "clips that play
   silently" gate for `anim` and the measured clip labels / loop flag for imported animations (section 1, the
   2026-10-12 work-machine bullet, item 2).
5. ~~Fix `ruff check .` on `main`~~: done with the app port (`99f3986`), ruff skips `docs/`.

#### Earlier next-session note (owner decision, 2026-10-07 evening)

The owner tried M31 on the viking and asked what a parts version is good for. Found: nothing after it
uses the parts yet. The Godot export (`blender_ops/export.py` imports through `_lib.import_mesh`, which
joins every mesh) and skinning (`blender_ops/skin_proxy.py`, the same import) turn them back into one
mesh; checked on the scratch copy (`viking.glb` from a Helmet + Skirt version: one mesh node;
`rigged.glb`: one mesh). The owner chose the recommended order ("gonna follow your recommendation"):

1. ~~**Ask the owner to merge `m31-parts`** (brings M30), then restart the app.~~ Merged 2026-10-08.
2. **M31b: the parts in the game files**: **built 2026-10-08** on `m31b-parts-export` (IMPLEMENTATION
   M31b "As built", `docs/bench/m31.md`); next the owner tries Rename parts and an export, then the
   merge, then M32. The plan as it was written:
   - Export keeps one object per part, named like the part, for Godot, Unreal, Unity and OBJ: for a
     source version that has `parts.json`, import without joining (a `join` switch on `import_mesh`,
     or a separate import in `export.py`) and keep the names; LODs and the collision hull per profile
     as now, decide whether LODs go per part or stay on the joined mesh (gltfpack's simplifier on a
     multi-node GLB: check it keeps the nodes, its `-kn` flag keeps named nodes). Web: gltfpack with
     `-kn`. 3D print stays one joined STL until M33.
   - Rename a part from the Parts list, without the GPU: a new light version (renamed `parts.json`
     and node names in `mesh.glb`; the `parts` step evicts the resident worker for every op today,
     so either a Blender-only op that skips that, or accept the eviction). The automatic names
     ("Part 1" …) are what the owner has on `522_parts`.
   - Make the Setup card true or plainer: it says "for naming, rigid binding and printing" while only
     naming exists until M32/M33.
   - Acceptance: the viking's `522_parts` (after renaming) exported for Godot and Unreal shows one
     node or mesh per part with the names, in the Godot headless import (M13/M21 path) and the Unreal
     FBX (`docs/bench/m13.md`).
3. **M32: rigid parts on the skeleton**: **built 2026-10-08** on `m32-rigid-parts` (IMPLEMENTATION M32
   "As built", `docs/bench/m32.md`); the owner tries Skin it with a rigid part, then the merge, then M33.
   The Collision hull tickbox defaults to off for rigged versions (owner 2026-10-08). The plan as written: `rig_skin` keeps the parts as separate
   objects in `rigged.glb`; a part marked rigid (helmet, shield, a weapon) gets all its weight on one
   bone, by default the joint nearest its centre (Helmet → Head, a held shield → the hand), changeable
   in the Parts or Skin panel; the other parts skinned as now. This also covers the case M31 did not
   check: `skin_proxy` keeps hand weights only on mesh edge-connected to the hand, so a part cut off at
   a hand lost its hand weights. Acceptance: the viking's helmet moves solid with the head in Walk and
   the custom motion, checked with renders of the body and close-ups (the rule in memory: measure and
   look before reporting a rig fix), exported to Godot and Unreal.
4. **M33: print split** (Phase 3 "print split"): the 3D-print profile writes one STL per part and a 3MF
   with one object per part. HoloPart (VAST-AI, MIT, 3.7 GB) to close the hidden side of a cut-off part
   (the skull under the helmet) is a spike first: VRAM, time, licence of its dependencies.

**Then the rest of Phase 3, in PLAN §7's order** (PLAN.md "Phase 3: Breadth and quality"):
- **Creature skeletons**: quadruped, bird and creature templates (Mesh2Motion CC0 rigs and clips), and
  SkinTokens' full-rig mode for generic objects. This was next on the list before the parts work.
- Optional video-to-motion (SAM 3D Body): licence check first.
- Projection refine and edit (texture edits with masks, seam healing), delighting: the faces part is
  done (M23/M24, the 4× upscale).
- More export formats (USDZ/BLEND/3MF breadth, multi-colour 3MF, printability check/repair): **dropped
  for now by the owner (2026-10-07)**; the print split above is the exception.
- CLI batch mode; the optional own Blender bridge add-on.
- **MX1 (Hunyuan, experimental): skipped by the owner for now (2026-10-07).**
- Later, Phase 4: the version-2 geometry note (thin and dark features, PLAN §7 Phase 4).

Still open and deferred: the Unity Humanoid check; "Needs a Hugging Face login first" is shown for any
missing gated model, not only for one that needs the login.

#### Earlier notes (2026-10-06)

1. **Phase 2 is closed and merged**: M22 (`docs/bench/m22.md`, 12 of 16 need no marker fix) and M22b
   (the skeleton and marker editor) were accepted by the owner on 2026-10-06 after their own edits on the
   viking (`bench_faithful_viking` `380_rig_fit` → `410_anim`) and merged to `main` the same day. Open
   from the run: a once-seen 18 min `canon` load stall. **M23 faces from the image** is built on
   `m23-faces` (`docs/bench/m23.md`) and accepted by the owner on 2026-10-06 ("good for now"). **M24**
   (`docs/bench/m24.md`, `m24_faces.jpg`) sharpens the image 4× first and takes the baked lighting out
   with a local colour match; the owner installs the `texture` model group on the Setup page (67 MB; the
   step works without it and says so). **Accepted by the owner on 2026-10-06 ("good for now") and merged.**
   The knight's visor is a generation recess (M23b family), not a projection fault. **M23b** (heads and hands geometry) is investigated, not fixed
   (`docs/bench/m23.md` "M23b"): the hair tear comes from `clean`'s surface rebuild merging hair
   strands into a pitted hood (a finer rebuild makes holes instead), the fingers from the generator plus
   the 15k decimation. The owner picks: a closing of the rebuild's narrow band (research), a higher or
   region-wise face budget for characters, or the 1536 generator profile; or accept both for now. Then
   MX1 or the rest of Phase 3.
   The owner's Unity Humanoid check is deferred (2026-10-05: "skip any unity checks for now"); it stays in
   `docs/bench/m21.md` "Open" for later. Found by the owner on the dwarf and fixed the same day: `rig_fit` read the
   facing off unreadable face scores (helmet, cartoon face) and turned the dwarf and the runner around;
   now face ≥ 0.5, else the feet, else +Z (`facing_by`), sides swapped when the labels contradict it, the
   retarget's forward from the toes; then on three more (viking, kid, mage): palm normals from the mesh where the finger keypoints are implausible,
   the ankle snapped onto the foot, and SkinTokens measured non-deterministic (the mage; open). Next, the owner's order: (a) ~~a marker editor with a gizmo~~ (M22b), (b) faces
   like the generated image (project the input image onto the head: PLAN Phase 3 "projection refine"
   pulled forward) and a heads/hands geometry pass (the kid's torn hair, the hiker's stub fingers),
   (c) MX1 (Hunyuan, experimental) or the rest of Phase 3; the version-number widening
   and the sparse-projection patch below are the two small open decisions.
2. With the owner, not scheduled: UI slice 3 (the library browser with thumbnails, section 11), a
   re-pose button, the open owner checks below, ~~the version-number widening~~ (decided 2026-10-07: versions count by one,
   001 … 999, so an asset holds 999 versions; older assets continue from their last number) and the sparse-projection
   patch gated on a phase-level memory profile (`docs/archive/CODE_REVIEW_2026-10-05.md`, outcome).
3. **Record** every measured number in `docs/bench/*.md` and the milestone's "As built" note
   (section 10). Never round estimates into the docs as if measured.

**Open owner checks**: Unity import of `a_dwarf_blacksmith_with_hammer_2/560_export/unity/` (headless
needs a signed-in Unity Hub); the portable zip on a clean VM; a manual `ci.yml` run when convenient.

**Known issues found this session, not fixed**:
- A single-view Faithful run once hung > 25 min on one CPU core after sampling; not reproducible (92 s
  fresh). Steps now dump all thread stacks to `jobs.log` after 10 min: if a job hangs again, read the
  `Thread ...` / `File ...` lines there (`docs/bench/m17.md` "Open").
- ~~`clean` opens raw Faithful meshes further~~ **fixed 2026-10-05**: a raw Faithful mesh can have a
  quarter of its edges shared by 3+ faces (robot 80k, pirate 78k); `clean` now rebuilds such a surface
  with CuMesh narrow-band dual contouring (`rebuild: auto`, > 1 % non-manifold) instead of dropping faces
  (robot 12k mesh: 4,531 open edges → 0, `420_validate` watertight; farmer 0 open edges, 1 part), refills the small holes its repair
  leaves, and a rebuilt surface keeps its winding (face_outward's ray votes flipped correct faces on thin
  plates); meshes below the threshold (the bench barrels) take the old path unchanged.
- The pose gate (M16) can't count limbs: the FLUX re-pose gave the knight four arms and passed.
- `remesh` quad symmetry mirrors one-handed props (opt-in; off by default).

**Working on this laptop (learned the hard way)**:
- Three venvs now: `.venv` (server), `.venv-ml` (steps), `.venv-skin` (`rig_skin` only: the SkinTokens
  port, pinned git dependency, group `skin`; `run.bat` syncs it, `uv lock` must be run when the group
  changes). `server/jobs.py` routes `rig_skin` there and it takes the GPU lock. Since M26 and M31 two
  more, which `run.bat` does not create: `.venv-kimodo` (`motion`, group `kimodo`) and `.venv-parts`
  (`parts`, group `parts`: GeoSAM2 with OpenCV 4); `UV_PROJECT_ENVIRONMENT=<venv> uv sync --frozen
  --group <group>`, and the step's error names the command.
- - Step code edits don't reach a resident worker (`trellis2`, `concepts`: `SERVE` in `server/jobs.py`):
  stop the `steps.trellis2 --serve` process (PowerShell `Get-CimInstance Win32_Process ... | Stop-Process`)
  or restart the app. One-shot steps (`clean`, `remesh`, `prep`, ...) pick edits up per job.
- Long GPU/RAM runs as background shells get reaped for low memory: run them through the app's API
  (the app runs in the owner's terminal) and poll, or ask the owner to run them.
- Never edit step code while a run uses the working tree.
- Write multi-line patch scripts to files, not heredocs with escapes; the formatter re-wraps code, so
  patch anchors from before a `ruff format` may not match.
- Free RAM sits at 3-5 GB with Faithful loaded (24 GB weights): close Blender for multi-view runs.


## From §6 and §7: the GPU bring-up plan, Without DINOv3

### 6. GPU bring-up plan

Each check: what to run, what "pass" means, where to record, where to look if it fails. A step's
stdout/stderr is in the app's job log and in the `run.bat` window; a failed version folder keeps its
partial outputs; `meta.json` of a finished version has `metrics` (seconds, `peak_vram_gb`, …).

1. **Smoke** (M1): `.\.venv-ml\Scripts\python.exe -m tools.smoke_m1` prints torch 2.8.0+cu128, the
   GPU, `(12, 0)` with `sm_120` in the arch list, and `cumesh ok`. Fails → a DLL/ABI problem in
   `wheels/` (built with CUDA 12.8.1, MSVC 2022, torch 2.8.0+cu128; `.github/workflows/wheels.yml`) or
   the driver (≥ 575).
2. **Concepts** (M10): Create → prompt → 4 images. Record warm time and VRAM in `docs/bench/m10.md`
   (target < 60 s warm, ≤ 14.5 GB). Code: `steps/concepts.py` (Z-Image-Turbo bf16 with CPU offload; the
   diffusers 0.40 call signature was checked, the model never ran). Prep/BiRefNet GPU fp16 path:
   `steps/_birefnet.py` (CPU path tested).
3. **Fast generate** (M2), needs DINOv3: pick → "cut out + generate: fast". First run is slow
   (model load + FlexGEMM's one-time Triton autotune, cached in `models/flex_gemm_autotune_cache.json`).
   Check: `hi.glb` is upright (Y up), its base on the floor, facing the camera like the image; textures
   look right; `peak_vram_gb` ≤ 14.5. Record cold and warm seconds + VRAM in `docs/bench/m2.md`.
   Likely failure points, in order: `steps/trellis2.py::_load` (writes `effigy_pipeline.json` pointing at
   `models/`), the patches in `engine/trellis2/patches.py` (attention shim speed/correctness on real
   sizes; DINOv3 fix on real weights), `_simplify_unwrap` (CuMesh calls written from source, never
   executed), `steps/_bake.py` on real sizes. M2's "DC remesh fragmentation" check is moot: generate uses
   upstream's non-remesh branch (simplify + unwrap); write that down in m2.md. If FlexGEMM reports
   "device not ready", the deferred fix is `EXPLICIT_GEMM` (PATCHES.md).
4. **Chain** (M4, M3, M7): on the generated version `clean {}` → `remesh {"faces": 20000}` → `uv {}` →
   `bake {"texture_size": 2048}` → `validate {}` → `export {"profile": "godot"}` and `"unreal"`.
   Pass: 0 non-manifold edges, UVs in [0,1], bake coverage high, textures match `hi.glb`'s look, normal
   map mean ≈ (128, 128, 255). M3's "within 5 % of upstream `to_glb`" can't be run (to_glb needs
   nvdiffrast, which is excluded): compare the bake's mean base colour with `hi.glb`'s instead and note
   the substitution. Code: `steps/clean.py`, `remesh.py`, `uv.py` (`_cumesh_*` wrappers),
   `steps/bake.py::_projector` (cuBVH `ray_trace` / `unsigned_distance`, never executed).
5. **Faithful** (M2): the same image with "generate: faithful". Check orientation against Fast: Pixal3D's
   axis change `PIXAL3D_TO_GLTF` in `steps/_common.py` was derived from its `inference.py`, never seen on
   a real output; if the model is turned or lying down, fix that matrix (test in `tests/test_frames.py`).
   Watch system RAM (~24 GB of weights on 32 GB): if Windows swaps hard, note it. Camera = manual FOV
   0.2 rad (`fov` param); MoGe-2 estimation isn't wired. Code: `_load_pixal3d`, `engine/pixal3d/patches.py`
   (`na2d` at 1024² is a chunked gather: memory-bounded, maybe slow; time it).
6. **Retexture** (M12): `trellis2` preset `retexture` on the `bake` version and on a Blender-pulled
   version. Pass: new textures, vertices/UVs unchanged (compare UV layout in Blender's UV editor).
   Code: `steps/trellis2.py::texture` + `_load_texturing` (upstream stages; never executed).
7. **Blender + agents** (M8, M9, M40): Open in Blender → edit → Pull → new `NNN_blender` version. An agent
   connects over MCP (`mcp/effigy_server.py`; Setup → "Connect an agent"). Code: `server/blender_client.py`
   (add-on socket 127.0.0.1:9877). Ask Claude (`claude_runner`) was removed in M40.
8. **Bench** (M11): `docs/archive/LAPTOP.md` Part 4 and `docs/bench/phase0.md`. Acceptance: ≥ 9/10 per preset,
   every step ≤ 14.5 GB, Fast-vs-Faithful A/B recorded and the default picked in `docs/PLAN.md` §3 row 1.
9. **Engine imports** (M13): `docs/bench/m13.md`, Godot and Unreal first. The Unreal collision name
   `UCX_<name>_LOD0_00` is our best reading of the FBX importer: confirm or fix in `steps/export.py`.
10. **Install** (M15): the owner's first-start time from the zip → `docs/bench/install.md`
    "reference laptop" row.

#### Code that has never executed (highest risk first)

`steps/trellis2.py` (`_load*`, `_simplify_unwrap`, `texture`'s pipeline calls) · `steps/bake.py::_projector` ·
`steps/clean.py` / `remesh.py` / `uv.py` CuMesh wrappers · `steps/concepts.py` (Z-Image) · BiRefNet on
GPU · `engine/*/patches.py` on real weights and sizes · `gltfpack.exe` (only downloaded on Windows) ·
`blender_ops/*` on Windows Blender · the live link and `claude -p` against the real add-on/CLI on
Windows.

### 7. Without DINOv3 (approval pending)

DINOv3 is used only by `steps/trellis2.py` (Fast, Faithful, texture). Everything else can be brought up
first: smoke, concepts + prep, the golden images (`tools.bench --make-golden`), the chain on an uploaded
GLB (clean → remesh → uv → validate → export; `bake` needs a generated volume), engine imports, Blender
live link, Ask Claude. `tools.download_models` skips the gated repo and fetches the rest; after approval
and `hf auth login`, "Install fast" fetches only DINOv3. Don't work around the gate with a re-hosted copy.


## From §11: the roadmap before bring-up

### 11. After bring-up: the roadmap

Phase 1 closes when M12–M15's acceptance is recorded. Phase 2 (characters, `docs/IMPLEMENTATION.md`
§4): M16 pose canonicalization (bake-off of the candidate models first), M17 multi-view (Pixal3D-MV;
weights group `multiview`, the na2d stand-in already covers it), M18 quad remesh, M19 rig fit, M20
skinning, M21 animation, M22 bench. MX1 (Hunyuan, experimental, restricted outputs) can start any time
after Phase 1 if the owner wants it. One milestone per PR, acceptance checks in the PR description (§7).

#### Owner requests (2026-10-04), not scheduled yet

- **Animation from the owner's Kimodo project (2026-10-05).** The owner already animates rigged
  characters with Kimodo (NVIDIA text-to-motion, PLAN Phase 3) in a Godot plugin of their own: reuse
  its code and model setup here so characters can be animated in this app later (after M21's clip
  packs, or instead of them for custom motions). On this laptop `D:\CODE\kimodo` is an unmodified
  clone of upstream `nv-tlabs/kimodo` (Apache-2.0 code; SOMA checkpoints under the NVIDIA Open Model
  License, allowed by PLAN §6). 2026-10-07: the owner confirmed Kimodo "sits in its own repository
  parallel to this one"; there is no Godot plugin of theirs, the clone is what they use. Kimodo outputs the SOMA 77-joint skeleton: a SOMA → our 52-joint Mixamo retarget map
  is the bridge (research 05).

- **Library UI rework: working with many generations.** The flat "Your assets" list and the per-asset
  version list become unreadable fast (one bench run alone adds 10 assets × ~9 versions; reruns repeat
  names). Problems seen: no thumbnails, no search/sort/filter, no way to hide test or failed runs, no
  delete/archive/rename, the version list shows every intermediate step at the same level.
  First sketch to discuss with the owner before building: an asset grid with thumbnails (the bake's
  preview), search, sort by date/name, filter by status/source (bench, golden, mine), archive + delete;
  versions as a collapsed tree that shows the "milestones" (concepts, 3D model, game-ready, exports)
  with intermediate steps folded, a star/keep mark, and compare two versions side by side. Needs an
  `archived`/`starred` field in `asset.json`/`meta.json` (a §3.2 contract change, its own PR).
  Owner, later the same day: "a form of browser with thumbnails to see which image or model we want to
  work on further, much like Meshy does it": the grid is the main way in, showing both concept images
  and 3D models (turntable thumbnails), and picking one opens it for the next step.
  **Done 2026-10-05 (first piece)**: thumbnails (`server/thumbs.py`, `GET /api/assets/{id}/thumb` and
  `.../versions/{v}/thumb`, cached as `_thumb.png` in the version folder): the textured model first,
  else any model (grey render), else the picture (concepts as a 2×2 grid), else the parent's. Shown on
  the library cards and in History.
  **Done 2026-10-05**: delete an asset, delete a version with everything made from it (History ×),
  rename an asset (`DELETE /api/assets/{id}`, `DELETE .../versions/{v}`, `PATCH /api/assets/{id}`):
  deleted folders move to `library/_trash/<time>_<asset>[_<version>]` (recover by moving back), refused
  (409) while a job runs on that asset or branch. Version ids aren't renumbered (gaps are fine; History
  shows labels). **Done 2026-10-07 (M28)**: search/sort/filter, archive, version labels and stars, the folded version
  tree. **Done 2026-10-09 (M42)**: comparing two versions side by side, turntable thumbnails. The sketch is built.

