# Carry appearance between captured views

Spoke: S01
Outcome: Persist reusable appearance separately from view instructions.
Depends-on: S00
Decisions: D1, D3, D4
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, web:typescript-core
Read-set: INDEX.md, 00-genesis-edit.md#result, CODE.md, ui/src/SurfacePaint.tsx, server/library.py, server/app.py
Write-set: server/library.py, server/app.py, ui/src/api.ts, ui/src/SurfacePaint.tsx, steps/paint.py, docs/LOCAL-SETUP.md, docs/plans/surface-paint-ux/01-appearance.md
State: done

## Context

The owner is painting another camera angle of the same hut. Re-entering its
materials and style should not be necessary. Keep shared appearance distinct
from local instructions such as repairing the edge of the chimney.
Use the owner-invoked project `3dgen-prompt-core` guidance for model wording.

## Evidence

Baseline anchors describe the pre-implementation behavior.

- `ui/src/SurfacePaint.tsx:169` keys browser drafts by asset and capture/source
  version. Lines 171-179 initialize from candidate params or that draft; a new
  capture has no inherited prompt.
- `ui/src/SurfacePaint.tsx:217` submits camera and size only during capture.
- `server/library.py:252` owns asset metadata updates; `server/app.py:145`
  exposes name/archive/tags only. Add persistence through this existing owner.
- `ui/src/SurfacePaint.tsx:245` saves drafts in browser storage. Existing generated
  candidates retain exact prompts; preserving those snapshots supports old work.

### Runtime observations

Implemented and qualified on 2026-10-20. Library-owned appearance metadata holds
literal materials, desired style, preservation intent, model defaults and a
revision. Optimistic revision checks prevent silent overwrites. Captures freeze
the selected record; candidates freeze its text plus separate view instructions
and the exact submitted prompt. Capture and candidate drafts have independent
keys. Legacy full prompts do not inherit and duplicate newly shared prose.

The hut's shared record was saved through the UI as revision 1 using material
and brushwork intent from the existing 111 recipe, with Genesis selected and no
FLUX LoRA settings. Revision 2 changes denoise to 0.35 after the observed 0.60
shape drift. Captures 123/124, two angles, reopening/reload and candidate draft
save/reload were exercised. Revision 1 snapshots remained unchanged after the
shared record changed. Pixel masks and seeds did not migrate to a new angle;
loading the named triangle boundary was a separate explicit action.

Unsaved shared appearance must be saved or explicitly restored before a new
capture, preventing silent loss during navigation. The UI exposes current shared
appearance, previous recipe text, a separate view
field, exact prompt preview and an explicit restore-current action. Reviewed
caption text appended only to the material draft; restoring shared appearance
kept style and view instructions separate. Ordinary asset metadata and existing
job records contain the result; no additional evidence package. Source checks
and UI build passed.

## Steps

1. Obtain scope approval from the index before implementation. Define a bounded
   asset appearance record: materials/palette, desired style, features to preserve
   and model defaults. Keep angle-specific instructions outside that record.
2. Extend the library-owned asset API with validated appearance updates and a
   revision identifier. Preserve unrelated asset fields and exact owner prose.
3. Add "Use for this asset" and "Use previous recipe" actions. Seed the hut's first
   proposed material/style text from the existing 111 recipe, with Krea2 Genesis
   selected under D4. Do not copy FLUX model settings, LoRA bindings or
   camera-specific wording into shared defaults.
4. Snapshot the selected appearance revision into each new capture. Show shared
   appearance and this-view change separately; expose the exact resulting prompt
   before generation. Use Krea2 appearance wording for new work; keep historical
   FLUX/Qwen recipes readable without converting or replacing them.
5. Give an existing view draft precedence over inherited defaults. Never replace
   unsaved edits after an API refresh. New views inherit style/model/denoise/steps;
   camera-space masks and old random seeds are not silently carried across angles.
6. Keep legacy captures usable. If no appearance exists, offer the prior recipe
   explicitly. Saving appearance creates metadata, not another mesh version.

## Files to touch

- server/library.py
- server/app.py
- ui/src/api.ts
- ui/src/SurfacePaint.tsx
- steps/paint.py
- docs/LOCAL-SETUP.md
- docs/plans/surface-paint-ux/01-appearance.md

## Verification

1. `.venv/Scripts/ruff.exe check server/library.py server/app.py steps/paint.py`
   and `npm --offline --prefix ui run build`. Expected: pass without tests or downloads.
2. Ordinary hut UI: save appearance, capture a second angle, reload, change only
   its local instruction. Expected: shared appearance persists, mask resets and
   the original view's prompt remains unchanged.
3. Inspect generated recipe metadata. Expected: literal submitted prompt and
   appearance revision remain recoverable after subsequent appearance edits.

## Risks

An inherited description can incorrectly describe hidden features. Shared material
intent must not force every window or doorway into every angle. Browser draft
conflicts need a visible recovery option. Model suggestions belong to S04.

## RESULT

Implemented and qualified. Asset appearance revisions, frozen capture/candidate snapshots, exact prompt display and independent candidate drafts are present. Shared revision 2 uses Genesis/8 steps/denoise 0.35. UI save, alternate-angle inheritance, reload, previous text, explicit restore-current and reviewed caption append were exercised. Legacy full prompts remain separate from new shared prose. Masks/random seeds do not silently cross angles. Ruff/UI build pass. Runtime observations above retain the qualified behavior and limits.
