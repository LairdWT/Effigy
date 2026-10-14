# Concrete improvement backlog

Review complete; Pass 1 and Pass 2 are built (the log in [STATE.md](STATE.md)), Passes 3 and 4 are pending. A ticked box says how it was built. Use [FINDINGS.md](FINDINGS.md) for evidence and [STATE.md](STATE.md) when resuming.

## Recommended order

| Pass | Objective | Findings | Main files | Completion evidence |
|---|---|---|---|---|
| 1 | Prevent lost work and repair obstructed controls | UX-01–UX-04, UX-08 | `ui/src/main.tsx`, `ui/src/styles.css`, `ui/src/anim/Editor.tsx`, `Transport.tsx` | Dirty-exit browser checks; licence visibility; no motion-panel overflow; laptop/compact editor captures; keyboard drawer walkthrough |
| 2 | Make the ordinary path obvious | UX-05–UX-07, UX-09, UX-15 | `main.tsx`, `workflow.ts`, `styles.css` | First-time prop/import/character paths at 1280×720; current task and next action visible; optional tools discoverable |
| 3 | Finish delivery, navigation and setup | UX-10–UX-12 | `main.tsx`, `api.ts`, existing setup/export endpoints | Complete-file export, consistent batch defaults, Back/filter restoration, capability-specific setup links |
| 4 | Accessibility and library polish | UX-13–UX-15 | `main.tsx`, `Import.tsx`, `DopeSheet.tsx`, `styles.css` | Contrast measurement; keyboard key editing; NVDA/zoom walkthrough; uncluttered library |

Keep React, plain CSS, native controls, the viewer and existing APIs. The findings do not require a component library, state framework or UI rewrite. If packaging requires a new ZIP endpoint, implement that as explicit backend scope after considering the existing folder-copy route.

## Pass 1 checklist

- [x] Track real unsaved changes in animation, skeleton and marker editing; guard Close, version changes and navigation. Preserve failed-save state. *(built 2026-10-12, branch `ux-pass1`: `ui/src/hooks.ts` `useUnsaved`/`leave`, a `confirm` on Close/Cancel, on `navigate` and on an outside hash change (the address goes back), a dirty-only `beforeunload`; the guard rests while a save runs so its result can open)*
- [x] Make motion-panel grid/flex children shrink and wrap; fix the intrinsic overflow rather than clipping it. *(built: `.panel` and its grids get `grid-auto-columns: minmax(0, 1fr)` / `min-width: 0`, selects and videos `max-width: 100%`)*
- [x] Allocate visible space for Licences, with consistent disclosure/dialog semantics and close/focus behavior. *(built: Licences is a docked `region` in its own grid column, like History; Close focuses the trigger)*
- [x] Let the animation timeline and transport adapt to available width/height. Keep a usable canvas area and avoid overflow into the action panel. *(built: the timeline is `flex: 0 1 280px`, min 150, max 50 %; the canvas min 180 px; the transport wraps; compact screens scroll the page)*
- [x] Resolve History's covered focus targets and Escape behavior. Pick either a modal overlay or a docked non-modal panel and implement that choice consistently. *(built: docked non-modal `region` for History and Licences, one Escape listener on the window while open; the batch panel stays inline)*

Meaningful regression cases: dirty speed edit + Close/Keep editing; dirty + hash navigation; save refusal then retry; Licences with several credit lines; motion panel with long filenames/clip names; editor at 1280×720 and 640×360; full Tab/Escape sequence through History. Existing tests must still pass.

## Pass 2 checklist

- [x] Move check/export ahead of optional parts/rig tools for static and imported models. *(built 2026-10-12, branch `ux-pass2`: `Actions` puts Check model, then Export, first; Face, Texture detail and Parts sit in a `Tools` disclosure (`#tools`, open when the shown checkpoint is that tool's own), the rig form in a `Character` disclosure (`#character`) on a prepared mesh; a checked mesh shows the checklist summary, then Export as the primary, the items under Details (open when any needs attention))*
- [x] Show ready-made / text / video as explicit animation-source choices; render only the selected form. *(built: `ClipPicker` radios Ready-made · From a sentence · From a video, ready-made by default when a clip or a motion exists; `SkinQA` leads with the weights line, the picker next, the skin checks under a disclosure)*
- [x] Keep the current primary action accessible in a clear action bar; provide safe scroll padding if sticky. *(built without anything sticky: the main section is first in the panel, so the primary is in the panel's first screen at 1280×720; the acceptance walk measures the Export button inside the panel's box)*
- [x] Put rerun settings below continuation; compute preparation text from the selected checkpoint, active recipe and available later result. *(built: `workflow.ts` `prepState` (completed · active · interrupted · historical, from the descendants on the branch and the running job's input version); Continue preparation only when steps remain; View checked result / Open the newest otherwise; Run this step again under a disclosure in every state)*
- [x] Replace the 14-step primary navigation with broad tasks; retain every detailed step in Prepare, optional tools and History. *(built: `TASKS_3D` Reference · Generate · Prepare · Character · Finish and `taskOf`; a Tools ▾ menu (a native `details`) with Face, Texture detail, Parts, Edit in Blender, Advanced, each with its state; `TASKS_2D` Picture · Pixelize · Layers · Tiles · Edit · Finish for `asset.kind === "2d"`; History unchanged)*
- [x] Use Imported model as the imported starting state and explain missing prerequisites beside task actions. *(built: an "Imported model" chip replaces Reference and Generate; a task without a checkpoint opens where it is configured, or is disabled with a title "Needs a prepared model" and the like)*
- [x] Replace known-unavailable generation/export buttons with the relevant setup path or disabled action and explanation. *(built: missing concept files make "Set up concept images" the main action on New asset and on a description (the draft stays); a missing generator makes "Set up Faithful" the main action; a restricted version's Export is disabled with its explanation)*
- [x] Move preparation's specialist fields and lengthy background/editor help into discoverable advanced help. *(built: `PrepareForm` keeps budget, texture size and height; topology, level and square, close slits and the taper sit under Advanced with their help visible; the generator's radios, background and seed under Advanced; the raw model's, the fit form's, the skeleton, marker and animation editors' instructions under Help; one outcome sentence per form; "Skin it" → "Attach to skeleton", "Shadows only" → "Remove baked shadows", Back names its target)*
- [x] Make the two creation modes occupy two equal columns. *(built: `.modes` is two columns)*

Suggested default panel order:

| Checkpoint | First visible content | Main action | Optional content |
|---|---|---|---|
| Description | Short description preview and readiness | Generate 4 concepts | Edit description/category |
| Concepts | Candidate grid and current selection | Use selected image | Generate more; checks details |
| Cut-out reference | Generator recommendation | Generate 3D | Background/seed help |
| Raw generated mesh | Budget, texture size, optional height | Prepare model | Topology/alignment/slit/taper settings |
| Interrupted preparation | Completed/remaining steps and reason | Continue preparation | Rerun a single step |
| Prepared static/imported mesh | Brief result/import summary | Check model | Parts, textures, rig, Blender |
| Checked static mesh | Check summary and destination | Export package | Warning detail; optional tools |
| Fitted skeleton | Placement/fit summary | Attach to skeleton | Joint/marker corrections |
| Skinned character | Animation source, clips and selected count | Add animations | Text/video-specific configuration |
| Animation editor | Clip, selected bone and changes | Save version | Help and specialist correction tools |
| Export result | Completed destination and file count | Save all files / Download package | Individual files; export another destination |

Acceptance walk: a new user can take one prop from reference to delivery without seeing creature templates, raw JSON or manual file assembly. A character user can choose clips and save a correction without hunting for the relevant action. Keep warnings explicit when exporting a model that needs attention.

## Pass 3 checklist

- [x] Reuse export-copy for saving a complete selected export to a folder. Add a ZIP route only if a direct packaged download is wanted. *(built 2026-10-12, branch `ux-pass3`: `SaveExport` on the export result, `/api/export/copy` into `<folder>/<asset>_<profile>`, the main action when the export has several files, the folder remembered in localStorage; no ZIP route)*
- [x] Explain destination import in one sentence; include material, texture and credit files. *(built: `EXPORTS[].next`, one sentence per destination under the result's heading; the folder copy carries every file, credits included; a single-file export keeps its credit files as downloads)*
- [x] Preview batch checkpoint choices and align single/batch destination defaults. *(built: "What will be exported" lists each asset's pick (label, number, starred) before it runs; both default to Godot and the server's LOD and collision defaults, said in the dialog)*
- [x] Preserve Library query, sort, tags, filter and return position through navigation; use hash parameters if possible with the existing parser. *(built: `#/?q=…&sort=…&filter=…&tag=…` by `replaceState`, no new history entry; remembered in `libView` for the Library button, the scroll position too)*
- [x] Add Clear filters and name the update-based sort accurately. *(built: Clear filters beside the tools while any is set and in the no-match line; "Recently changed" / "Changed longest ago")*
- [x] Add normal setup cards for skinning and ready-made animations, with links from blocked tasks. *(built: cards Standing pose, Character skeleton, Learned skinning, Ready-made animations; `#/setup?cap=<group>` scrolls to and marks the card; every blocked action's link (concepts, the generator, Face detail, Texture detail, Parts, the clips, the Tools menu) points at its card)*
- [x] Reconcile Hugging Face instructions and use the existing guided login flow from Setup. *(built: `HfLogin`, the guided setup's login as one component, in Get started and in a gated card's "Before you install"; the terminal step and "never asks for a token" are gone)*
- [x] Summarize readiness for the desired capability, making optional features clearly optional. *(built: "Ready for props and objects, game characters." from the guided setup's sets, then "Not installed, each optional until you want it: …")*

## Pass 4 checklist

- [x] Strengthen required input boundaries without reducing existing readable text contrast. *(built 2026-10-12, branch `ux-pass4`: `--field: #7d8792` on text fields, selects and text areas only: 4.9:1 on the page, 4.4:1 on a panel, 3.8:1 on the field's own fill; buttons and text keep their colours; a browser test measures the outline against its background)*
- [x] Announce file/form errors and associate them with the affected control. *(built: `role="alert"`, `aria-invalid` and `aria-describedby` on the Import model and animation file fields, the New asset picture and the motion panel's animation file)*
- [x] Add skip-to-main and a workspace h1; keep heading levels consistent. *(built: "Skip to the content" is the first Tab stop and focuses `<main id="main">` without changing the address; the asset name is the page's h1 at its old size; History, Licences and a hidden "Next step" heading are h2)*
- [x] Make before/after image enlargement a labeled button. *(built: Face detail's overlay and Texture detail's views are buttons, "Enlarge the …" / "Show the … small" with `aria-pressed`)*
- [x] Add a keyboard-operable key/frame/value list alongside pointer timeline editing. *(built: `KeyList` in `anim/DopeSheet.tsx`, "Keys as a list" under the editor's Save: each keyed bone's frames as buttons that select and go there, "A frame earlier/later" for the selection, X deletes; in Curves each key's X/Y/Z as number fields. Found on the way: the bone's turn fields kept their old value after a curve drag; they refresh now)*
- [x] Move card management into a native accessible disclosure; keep it available on focus/touch. *(built: Rename, Tags, Archive and Delete under each card's `details` "More", named "More for <asset>")*
- [x] Make Select assets / Done selecting explicit and provide an in-app restore path before promising simple recoverability. *(built: the toggle says "Select assets" / "Done selecting"; `GET /api/trash` and `POST /api/trash/{name}/restore` (`library.trash`, `library.restore`: refused when an asset of that id or a version of that number is there again, or the branch's asset or parent is gone); "Recently deleted" at the end of the library lists both kinds with Restore, refreshes while open; the delete confirmations name it)*
- [x] Shorten routine help and clarify specialist action labels. Keep advanced guidance available without relying on hover. *(Pass 2 did the labels, the Help disclosures and Advanced; here: a task that is not reachable yet stays focusable with its reason as its description, shown under it on keyboard focus; the editor says why Move or IK drag is off; Help explains Curves, Motion path, Onion skin and the key list)*

## Verification after implementation

Run `npm run build` and `npm test` in `ui/` after substantive source changes. Add focused behavior regressions for lost-work prevention and corrected workflow contracts; cosmetic spacing changes need rendered inspection, not implementation-mirroring unit tests.

Capture the same fixture screens at 1440×900 and 1280×720, plus compact layouts. Supplement with actual browser zoom and NVDA for accessibility claims. Verify no unintended horizontal overflow, no covered focus, and no controls that claim to run a known-missing capability. These are acceptance checks, not permission gates.

## Continuation

Start with Pass 1. Re-read its current callers and the frozen API/step contracts before editing. Some October 10 technical findings are already fixed; use the current baseline and tests rather than restoring older implementation guidance. No implementation was performed as part of this review.
