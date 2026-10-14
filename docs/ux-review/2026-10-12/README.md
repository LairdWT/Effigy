# Effigy UX review — 12 October 2026

The interface has a solid visual foundation. The main improvement is to make each workspace checkpoint lead with the next useful task and keep specialist tools secondary. Several concrete layout and lost-work issues should be fixed first.

The review mapped **14 user workflows**, captured **34 interface states**, and recorded **15 prioritized findings**. Existing validation passed: production build and **42 tests**. Production app code was not changed.

## Read the review

- [WORKFLOWS.md](WORKFLOWS.md): destinations, controls, states and end-to-end paths.
- [FINDINGS.md](FINDINGS.md): prioritized issues, reproduction evidence and desired behavior.
- [IMPROVEMENTS.md](IMPROVEMENTS.md): pending implementation passes and acceptance checks.
- [STATE.md](STATE.md): completed work and continuation pointer.
- [Validation record](evidence/VALIDATION.md): what ran and what it establishes.

## First changes to make

1. Protect unsaved editor changes when closing or navigating.
2. Repair clipped motion controls, hidden Licences content and the compact animation layout.
3. Put check/export and animation selection ahead of optional parts/rig/text/video forms.
4. Simplify the 14-stage navigation, correct preparation status and link blocked actions to exact setup requirements.
5. Deliver complete export packages and preserve library context, then finish accessibility and copy polish.

Start implementation with Pass 1 in IMPROVEMENTS.md. All product-fix checkboxes are still pending; this review does not claim they were implemented.

## Representative screens

| Screen | Evidence |
|---|---|
| Library and repeated management actions | [Library](evidence/screenshots/library.png) |
| Clear starting form | [New asset](evidence/screenshots/new-description.png) |
| Long preparation/action panel | [Bake](evidence/screenshots/laptop-bake.png) |
| Optional rigging before export | [Checked model](evidence/screenshots/checked-model.png) |
| Clipped motion form | [Skinned model](evidence/screenshots/laptop-skin.png) |
| Timeline overflow on laptop | [Animation editor](evidence/screenshots/laptop-editor.png) |
| Individual export-file delivery | [OBJ export](evidence/screenshots/export-obj.png) |
| Compact editor overlap | [Compact editor](evidence/screenshots/zoom-equivalent-editor.png) |

Screens use controlled local fixtures, not newly generated production assets. The methodology is documented in [PLAN.md](PLAN.md); runtime measurements are in [observations.json](evidence/observations.json).
