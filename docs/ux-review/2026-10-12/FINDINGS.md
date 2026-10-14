# Effigy interface and workflow findings

Reviewed 2026-10-12 at baseline `06be15b87798128a6ed1024c2f1f19d5c2aa8946`. Production source was not modified. All findings below remain **open for implementation**.

The visual foundation is sound: consistent charcoal surfaces, readable body text, clear creation modes, a large preview, immutable history, useful import disclosure and descriptive main buttons. The biggest problem is task hierarchy. The workspace presents processing steps and specialist tools together, often putting the user's next ordinary action behind several screens of optional work. A new visual theme would not resolve that.

## Priority register

P1: address first because users can lose work or encounter inaccessible/obstructed controls. P2: resolve common workflow friction and clarity. P3: polish after the common paths are reliable. A design recommendation is identified separately from a reproduced defect.

| ID | Priority | Finding | Evidence type | Main workflow |
|---|---|---|---|---|
| UX-01 | P1 | Closing the animation editor silently loses unsaved changes | Reproduced; navigation sibling source-confirmed | W09, W14 |
| UX-02 | P1 | Motion controls exceed the fixed side-panel width | Rendered and measured | W08 |
| UX-03 | P1 | Opening Licences puts its content underneath the workspace | Reproduced and measured | W10, W12 |
| UX-04 | P1 | Timeline toolbar overflows at laptop size; compact editor collapses the model view | Rendered and measured | W09 |
| UX-05 | P1 | Optional tools bury check/export and compete with the main action | Measured hierarchy problem; proposed remedy | W04, W05, W08, W10 |
| UX-06 | P2 | Fourteen stage buttons expose the pipeline rather than the user's task | Rendered/source evidence; design recommendation | W02–W10 |
| UX-07 | P2 | Intermediate preparation says it stopped even when checking is running or finished | Reproduced and source-confirmed | W05, W14 |
| UX-08 | P2 | History allows focus behind the drawer; Escape then does not close it | Keyboard reproduction | W12 |
| UX-09 | P2 | Missing generation files are warned about while the main action still offers generation | Reproduced; restricted-export sibling source-confirmed | W01–W03, W10 |
| UX-10 | P2 | A prominent single-file download leaves companion-file exports incomplete | Rendered/source evidence; design recommendation | W10, W11 |
| UX-11 | P2 | Library search, filters and sorting reset on navigation | Search reproduced; siblings share local state | W12 |
| UX-12 | P2 | Setup omits ordinary character prerequisites and contradicts the guided login instructions | Source-confirmed | W01, W07, W08 |
| UX-13 | P2 | Form boundaries have low contrast; specialist controls have remaining accessibility gaps | Contrast measured; gaps source-confirmed | W01–W09 |
| UX-14 | P3 | Every library card repeats four management buttons and a Delete action | Rendered/source evidence; design recommendation | W12 |
| UX-15 | P3 | Long instructions and advanced settings dominate small action panels | Rendered/source evidence; design recommendation | W03–W10 |

## UX-01 — Protect unsaved editor work

**Current behavior.** Open an animated checkpoint, choose Edit animation, expand Clip tools, set Speed to `0.5`, then click Close. Save is enabled before closing, no confirmation opens, and reopening shows Speed `1`. No save request occurred. Persisted checkpoints are safe, but the unsaved edit is gone.

**Evidence.** `ui/src/anim/Editor.tsx:822` calls `onClose` directly; `ui/src/main.tsx:3475` removes the editor. Main navigation/hash handling does not consult editor dirty state. Rig/marker Cancel also stops local history directly; that sibling was traced, not reproduced with an unsaved rig in this pass. Probe: `unsaved_animation_close` in [observations](evidence/observations.json).

**Desired behavior.** Keep an explicit dirty indicator. Close, version switch and navigation should preserve the draft or offer Save / Discard / Keep editing when there are real changes. Browser reload/close needs a dirty-only `beforeunload` guard. Cancel in skeleton/marker editing should make the discard consequence clear. Avoid a warning on clean editors.

**Acceptance.** The same speed edit survives Keep editing and a failed save; Discard is explicit; a successful save produces a new checkpoint and clears the warning. Test version/history/main-navigation exits as well as the Close button. The existing failed-save path now retains speed `0.5`; do not regress that improvement.

## UX-02 — Contain motion controls within the panel

**Current behavior.** At 1440×900 and 1280×720, the skinned-model action panel is 336 px wide, but Add animations and other section controls lay out at 384 px. The panel's `scrollWidth` is 416 px. Text and controls clip at the right edge and require horizontal scrolling in an otherwise vertical form.

**Evidence.** [Laptop skin screen](evidence/screenshots/laptop-skin.png); captures `skin-animation-options` and `laptop-skin`. `ui/src/main.tsx:2830` renders ClipPicker, including VideoMotion, inside a grid section. `ui/src/styles.css:591` gives the panel a fixed grid track but no `minmax(0, 1fr)` internal column; several nested flex/grid items retain their intrinsic minimum widths.

**Desired behavior.** Give the action-panel grid a shrinkable column; let section/form children shrink; constrain long selects/inputs and wrap the seconds/seed/action row. Keep visible labels and full button text. Hiding overflow alone would hide the symptom and leave inaccessible controls.

**Acceptance.** The motion panel's `scrollWidth` does not exceed `clientWidth` by more than rounding, at 1280, 1024 and 900 px viewport widths. Long clip names and video filenames still leave every field and button reachable. Test with all text/video/clip controls present.

## UX-03 — Give Licences its own layout space

**Current behavior.** Clicking Licences adds the dialog to the DOM, but its heading and credit text are covered by the next workspace row. The measured grid rows are `97px 0px 711.156px`: the Licences row receives zero height, while the workspace body starts at the same y-coordinate. A hit test at the licence heading finds the covering workspace.

**Evidence.** `licences_layout` probe; [Licences screen](evidence/screenshots/licences.png). `ui/src/styles.css:525` declares two rows; `ui/src/main.tsx:1416` conditionally inserts a third child before the body. The fixture included a real visible-text licence entry, so an empty list does not explain the result.

**Desired behavior.** Either add a correctly sized conditional row, or open a proper drawer/dialog with its own scrolling and focus behavior. Use a disclosure/region if it remains inline. Preserve the readable credit and imported-file notes.

**Acceptance.** Clicking Licences visibly exposes its title, component terms, credit text and Close at 1440×900 and 1280×720. A long list scrolls without covering the preview controls. Keyboard focus moves to a useful visible location and returns to the trigger on close.

## UX-04 — Make the animation layout adapt to the available space

**Current behavior.** The fixed 280 px timeline takes more than half the 531 px laptop preview height. At 1280×720 the unwrapped transport toolbar extends over the right panel. At 640×360, the preview is 216 px high while the timeline remains 280 px; the model canvas collapses and the preview toolbar overlaps the timeline. The document grows to 1037 px wide despite a 640 px viewport.

**Evidence.** [Laptop editor](evidence/screenshots/laptop-editor.png), [compact editor](evidence/screenshots/zoom-equivalent-editor.png). `ui/src/styles.css:895` fixes timeline height; `:1095` fixes the compact preview to `60vh`; `:787` adds rigid transport sections; `ui/src/anim/Transport.tsx:46` renders the toolbar. The 640×360 case is a **zoom-equivalent CSS viewport**, not a claim that a real browser at 200% zoom was tested.

**Desired behavior.** Reserve a minimum usable model area, size the timeline from remaining space and let the transport wrap or collapse secondary display controls. At compact sizes allow the editor to use a taller scrolling region. Keep play, frame and save controls visible, and hide routine check/export forms while editing.

**Acceptance.** At 1280×720, controls stay within the viewer and the model remains inspectable. At 640×360 there is no unintended page-wide horizontal overflow or toolbar overlap. Repeat with real 200% desktop browser zoom before claiming zoom accessibility.

## UX-05 — Put the next ordinary action before optional work

**Current behavior.** A checked prop displays its checklist, then the entire nine-template rigging form, then export. In the 1440×900 fixture the Export for Godot button starts at y=1355, outside a panel ending at y=864. The rig action is above it. An imported still model shows Parts before Check model, then rigging before export. The 1280×720 import panel contains 1725 px of content in 531 px of available height. Skinned characters show text and video motion forms before the ready-made clip picker; Add animations starts at y=1515.

**Evidence.** [Checked model](evidence/screenshots/checked-model.png), [imported model](evidence/screenshots/laptop-imported.png), [animation choices](evidence/screenshots/laptop-skin.png); measured captures. Ordering is explicit in `ui/src/main.tsx:1923`, `:1960` and `:2870`.

**Desired behavior.** Give each checkpoint one main outcome at the top: Generate, Prepare, Continue, Check, Add animations or Export. After checks, place export immediately after the summary. Collapse Parts, Rig, Face and Detail into optional tools; do not remove them. For animation provide a simple source choice: Ready-made / From text / From video. Default to ready-made clips when available. Put save/exit in a visible editor action bar. A sticky bar must leave enough scroll padding to avoid covering focused fields.

**Acceptance.** At 1280×720 a user can identify and reach the next action without first scrolling past unrelated tools. A checked prop can export without encountering the creature template list. An imported model can check/export before Parts. A character can reach clip selection without passing text/video forms. Specialist actions remain discoverable.

## UX-06 — Simplify stage navigation

**Current behavior.** The row contains 14 buttons, including six optional tools, with chevrons suggesting one ordered chain. Some buttons open checkpoints and others scroll to forms. Future Check/Export buttons are disabled even though relevant forms may already be available lower in the panel. An imported model is marked at Clean although no clean step ran. The row wraps across multiple lines on compact screens.

**Evidence.** `ui/src/workflow.ts:43` defines STAGES and `:69` maps imported geometry to Clean; `ui/src/main.tsx:1375` renders mixed checkpoint/tool behavior. [Compact workspace](evidence/screenshots/compact-workspace.png), [generation workspace](evidence/screenshots/laptop-generate.png).

**Recommendation.** Use broad task navigation such as Reference / Generate / Prepare / Export. Put character tools under an explicit optional tool entry or workspace mode. Show the detailed pipeline and intermediate versions inside Prepare/History. Use Imported model as a clear starting state. Let task navigation open configuration without running an operation; leave processing disabled only when its prerequisites are missing.

**Acceptance.** The primary stage row fits a normal laptop without wrapping; a newcomer does not need to infer what Skin or Bake means to export a prop. Experts can still inspect/re-run every current step. Preserve hash history and branch-specific checkpoints. This is a design recommendation, not evidence that every current user is confused.

## UX-07 — Describe preparation state accurately and lead with continuation

**Current behavior.** Every clean/remesh/UV/bake checkpoint starts with Run this step again and an amber rerun button. Below it, Preparation in progress says preparation stopped partway. That text also appears on a baked checkpoint with an existing later check, and while an active job says Checking. It describes a selected intermediate version as though it proves the whole process stopped.

**Evidence.** `ui/src/main.tsx:1934` chooses the RECIPE branch without examining active/completed descendants. `preparation_copy_with_active_job` contains both Checking and Preparation stopped partway. [Bake screen](evidence/screenshots/laptop-bake.png).

**Desired behavior.** Distinguish a historical checkpoint, an active recipe, an interrupted recipe and a completed preparation. Put Continue preparation first only when steps actually remain. On a finished chain say Textures baked / Model checked, with View checked result or export. Put rerun settings in a secondary disclosure.

**Acceptance.** An active chain never says it stopped. Returning to a historical bake after successful validation says what that checkpoint is and offers the later result. A genuinely interrupted clean/UV step offers the remaining recipe from the correct parent.

## UX-08 — Keep keyboard focus visible when History is open

**Current behavior.** Tabbing through History eventually reaches the underlying Inspect selector, Wireframe and Frame model. Their focus is behind the drawer. Pressing Escape after focus has left the drawer does not close it, because the key handler is only on the drawer.

**Evidence.** `history_keyboard_focus` recorded three underlying controls covered at their centers and `drawerRemainsAfterEscapeFromPreview: 1`. `ui/src/main.tsx:1447`; `ui/src/styles.css:989`. The existing Close action does return focus to the History trigger.

**Desired behavior.** Decide between a modal drawer with contained focus/inert background, or a non-modal docked panel that does not cover focusable controls. Do not add `aria-modal` without implementing modal behavior. Give Escape a reliable drawer-level lifecycle.

**Acceptance.** Keyboard focus is visible throughout the open drawer; Escape closes it from every allowed focus location; Close returns focus to History. Apply the same interaction decision to the licence and batch panels, using region semantics for ordinary inline sections. The relevant patterns are described by [WAI's dialog guidance](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) and [focus visibility guidance](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html).

## UX-09 — Make the main button match readiness

**Current behavior.** Missing concept-image files and a missing chosen generator both show a Setup link, but Generate 4 concepts and Generate 3D remain enabled with valid input. Texture detail handles this differently and disables its operation. A restricted export similarly says it cannot be exported while retaining an enabled Export button; that sibling is source-confirmed, not submitted here.

**Evidence.** `missing_feature_actions`: both warnings present, both actions enabled. [Missing concepts](evidence/screenshots/missing-concepts.png), [missing generator](evidence/screenshots/missing-generator.png). `ui/src/main.tsx:1050`, `:2132`, `:1692`, `:2303`.

**Desired behavior.** Where readiness is known to fail, make the primary action Set up concept images / Set up Faithful, linked directly to the relevant capability. Explain and preserve the draft/selected reference. Keep unknown readiness distinct from known missing files. For restricted exports disable processing and retain an explanation beside the action. Match actual prerequisite checks rather than guessing readiness from folder existence.

**Acceptance.** A known missing feature offers a single clear setup path; returning restores input and selections; repaired readiness re-enables generation. A restriction cannot present export as an available operation. Model downloads are not required to test this UI contract.

## UX-10 — Export a complete, usable package

**Current behavior.** The export result emphasizes Download lantern.obj, while its MTL, texture and credit files are separate small links. Copy says to keep companion files next to the main file. The interface therefore asks the user to assemble an export that the app already knows belongs together.

**Evidence.** [OBJ export](evidence/screenshots/export-obj.png); `ui/src/main.tsx:1894`. `BatchExport` already calls `/api/export/copy`, and `ui/src/workflow.ts:153` describes which profiles require multiple files.

**Recommendation.** Make Download export package or Save all files to folder the primary completion action. Reuse the existing folder-copy endpoint for a selected export before adding a new packaging abstraction. A ZIP download needs explicit backend work if desired. Keep individual files in a secondary list. Explain the next engine-import step in one short sentence. Include credits in the package.

**Acceptance.** OBJ/FBX/print outputs can be delivered as one complete action, with textures/materials/credits intact. Single GLB downloads remain simple. Batch export previews the chosen checkpoints and uses the same destination defaults as single export; avoid silently presenting a different starred checkpoint than the user expects.

## UX-11 — Preserve Library context

**Current behavior.** Search Dragon reduces the library to one card. Visit Setup and return to Library: the search is empty and all eight fixture cards return. Search/sort/filter/tag state belongs to a component that unmounts on navigation.

**Evidence.** `library_filter_navigation`; `ui/src/main.tsx:587`, `:597` and `:508`.

**Desired behavior.** Store search, sort and filters in the library route, using the existing hash parser/history, or at minimum preserve them in App. Restore the scroll position when returning from an asset. Offer Clear filters beside the no-match state. Clarify that Newest first uses last update time, not only creation time.

**Acceptance.** Search/filter/sort survive opening a model and returning, visiting Setup, and Back/Forward. Direct library links reproduce the query if URL-backed. Clearing filters returns to all active assets without affecting asset data.

## UX-12 — Complete and reconcile Setup guidance

**Current behavior.** The capability cards cover concepts, generators, face/detail, parts and generated motion. They omit skinning and ready-made clips, although the standard Game characters preset installs `skin` and `clips`. The empty clip picker tells the user to install the clips models on Setup, where that action is only under the advanced raw table. Gated Setup cards say the app never asks for or sends a token and instruct terminal login; Get started has a token field that sends the login request to the local backend.

**Evidence.** `ui/src/main.tsx:4066` CAPABILITIES, `:2916` clip warning, `:4760` gated instructions, `:4550` guided login; `server/install.py:49` character prerequisite groups. Current API wrapper is `ui/src/api.ts:147`/`hfLogin` (locate exact line before implementation). No claim is made that tokens leave the local machine.

**Desired behavior.** Add normal capability cards for character rigging/skinning and ready-made animations, with exact links from blocked tasks. Reuse the guided login controls/instructions in Setup. State accurately that the app passes the token to Hugging Face's local login storage and clears the form, consistent with actual implementation. Tie readiness summaries to the user's chosen workflow, not all optional capabilities.

**Acceptance.** A user can repair/install ready-made animations and skinning without using raw model tables or a terminal. Login instructions agree across both pages. Choosing a props-only setup does not imply failure because optional character features are absent.

## UX-13 — Finish contrast and specialist accessibility

**Measured contrast.** Main text on the page is 15.78:1 and secondary text on the panel is 7.79:1. Those tokens are strong. The default textarea border has only 1.76:1 against the page and 1.36:1 against its fill, making the empty field boundary faint. Preserve the existing theme while strengthening necessary control boundaries. [Non-text contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) explains the 3:1 requirement where a boundary is needed to identify a control.

**Source-confirmed gaps.** No skip-to-main link; normal workspace title is h2 with no page h1; image/file validation uses plain text without `aria-live`, `aria-invalid` or association to the field. DetailPanel's before/after image enlarges only on image click. The DopeSheet canvas has pointer selection/dragging but no focus/keyboard handlers; numerical trim and frame alternatives exist, so do not claim the entire editor is pointer-only. Keyboard access to key selection/time movement and curve adjustment needs a concrete alternative.

**Evidence.** `contrast_and_structure`; `ui/src/styles.css:99`; `ui/src/Import.tsx:77`; `ui/src/main.tsx:1355`, `:1090`, `:1656`; `ui/src/anim/DopeSheet.tsx:307`, `:327`. This is not a full screen-reader or WCAG conformance audit.

**Desired behavior.** Raise required field-boundary contrast, associate and announce input errors, add a skip link and workspace h1, use a button for image enlargement, and offer a keyboard-operable key list with frame/value editing alongside the timeline. Numeric data needs tabular figures where it updates rapidly.

**Acceptance.** Empty inputs are distinguishable; invalid-file errors are announced and tied to the field; all enlargements are keyboard actions; a user can select and move a correction key without a pointer. Verify with NVDA and actual browser zoom as a follow-up.

## UX-14 — Reduce library-management clutter

**Current behavior.** Every card has Rename / Tags / Archive / Delete, regardless of whether the user is organizing or simply browsing. Eight cards expose 32 secondary management actions, in addition to links and filters. The repeated red Delete buttons compete with the assets. Buttons are 28 px high.

**Evidence.** [Library](evidence/screenshots/library.png); `ui/src/main.tsx:700`, `ui/src/styles.css:1124`. Delete already confirms and retains trash on disk; do not describe it as immediate irreversible deletion.

**Recommendation.** Keep the whole card focused on opening the asset and move management into an accessible More actions disclosure. Use Select assets / Done selecting for the current selection toggle. Keep archive separate from deletion, and provide an in-app restore path if recoverability is promised. Four hidden hover-only actions would not solve keyboard/touch access.

**Acceptance.** The default library emphasizes thumbnails/names; management is one explicit click or keyboard action away; selection mode is unmistakable; confirmations identify the asset. A dense library remains usable with long names and without a mouse.

## UX-15 — Tighten copy, spacing and advanced controls

**Current behavior.** The side panel is only 304–336 px wide. Long paragraphs tell users to click buttons they can already read. Generation exposes a lengthy black-background explanation; preparation exposes slit closure, perspective correction and alignment alongside budget/size; animation displays a full instruction list ahead of bone selection and save. Creation's two mode buttons still use a three-column grid at desktop widths.

**Evidence.** [New asset](evidence/screenshots/new-description.png), [generation](evidence/screenshots/laptop-generate.png), [editor](evidence/screenshots/animation-editor.png). `ui/src/styles.css:439` mode grid; `ui/src/main.tsx:2106`, `:2151`, `ui/src/anim/Editor.tsx:510`.

**Recommendation.** Use two equal mode columns. Keep budget, texture size and optional physical height visible; put slit closure, alignment and taper correction under Advanced with visible helper text when open. Use one outcome sentence and optional help: Generate a 3D model from this reference / Simplify and texture the model for your project / Attach the mesh to the skeleton. Prefer Attach to skeleton over Skin it for newcomers. Rename Shadows only to Remove baked shadows and generic Back to the destination it opens. Avoid making technical help available only on hover.

**Acceptance.** Labels explain the outcome; each default form contains only decisions needed for the ordinary task; helper text is readable and discoverable by keyboard/touch. Keep the existing 8/12/16 px spacing rhythm, 40 px fields and 44 px main actions. Strengthen task ordering before enlarging every gap.

## Existing behavior worth preserving

- Native links/buttons, labeled fields, visible focus, current navigation state and specific main action labels.
- Description/image drafts survive a trip to Setup; image choice and computation are separate actions.
- Immutable history, branch-aware previews, warning-aware checklist and compare summary, imported-material preservation.
- Submission locks, foreground result opening, View result after navigation, honest GPU-disconnect state.
- Failed animation saves retain edits; deleting the last saved correction can return to base; reconnect selection/job recovery and keyboard clip choice now have passing regressions.
- Reduced-motion behavior prevents hover turntable loading; the existing dedicated test passed.

## Review limits and evidence

The [workflow map](WORKFLOWS.md) covers 14 goals. The [browser harness](evidence/browser-review.mjs) produced 34 captures and eight bounded probes with zero probe errors and zero page errors. API/files/EventSource were mocked; thumbnails use the same lantern fixture and meshes use synthetic geometry. The real isolated-backend suite passed 42 tests, including parameter and workflow assertions. Those checks do not measure generated asset quality, real downloads/GPU pressure, live Blender editing, screen-reader behavior or actual 200% browser zoom. Setup/Welcome screenshots capture the visible top of their internal scrolling page; below-fold login behavior here is source-reviewed and covered by the existing guided-setup test.

The first harness run had an incomplete generator preset fixture and an incorrect Frame selector; both were corrected before the final evidence. Earlier screenshots/logs were replaced by the final run. Do not treat those temporary harness errors as app defects.
