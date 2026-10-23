# Show the comparison sheet, add three buttons and document the seam

Spoke: S03
Outcome: Show the comparison sheet, add three buttons and document the seam
Depends-on: S02
Decisions: D1, D2, D3, D4
Constraints: C1, C2
Skills: web:typescript-core, python:python-core
Read-set: docs/plans/hand-paint-finish/INDEX.md, docs/plans/hand-paint-finish/02-heal-zone-ownership.md#result, ui/src/multi-view-api.ts, ui/src/AuthoringWorkspace.tsx, docs/SURFACE-AUTHORING.md, .codex/skills/effigy-surface-authoring/SKILL.md
Write-set: ui/src/multi-view-api.ts, ui/src/AuthoringWorkspace.tsx, docs/SURFACE-AUTHORING.md, .codex/skills/effigy-surface-authoring/SKILL.md, docs/plans/hand-paint-finish
State: done

## Context

Operators need the new actions in the workspace and a source-versus-result sheet beside the baked review. The operator guide and the local workflow skill must route to the new section.

## Evidence

Line numbers are before this change.

- ui/src/multi-view-api.ts:209 `authoringAction` accepted only reconstruct and publish; ui/src/multi-view-api.ts:26-27 `AuthoringState` had no handoff or heal-zone fields.
- ui/src/AuthoringWorkspace.tsx:205 section 3 holds the reconstruction buttons; ui/src/AuthoringWorkspace.tsx:212 section 4 holds review.
- docs/SURFACE-AUTHORING.md:41 Author, docs/SURFACE-AUTHORING.md:59 Review and publish, docs/SURFACE-AUTHORING.md:69 Recover and docs/SURFACE-AUTHORING.md:82 API entry points.

## Steps

1. multi-view-api.ts: widen the `authoringAction` union with `handoff`, `heal_mask`, `heal_mask:shells` and `reconstruct_heal`; add `handoff` and `heal_mask` to `AuthoringState` and its parser.
2. AuthoringWorkspace.tsx: a "Hand-paint handoff and seam heal" section with Export hand-paint handoff, Mark seam-heal zone (shell-border checkbox) and Reconstruct seam heal; show review.png and comparison.png for the chosen review version.
3. SURFACE-AUTHORING.md: section "Hand-paint handoff and heal" after Author, comparison sentence in Review, API rows for the three action strings, Recover bullets for `missing_heal_mask` and the shells fallback.
4. Route line in .codex/skills/effigy-surface-authoring/SKILL.md; this plan with RESULTs.

## Files to touch

- ui/src/multi-view-api.ts
- ui/src/AuthoringWorkspace.tsx
- docs/SURFACE-AUTHORING.md
- .codex/skills/effigy-surface-authoring/SKILL.md
- docs/plans/hand-paint-finish

## Verification

1. `node ui/node_modules/typescript/bin/tsc --noEmit -p ui/tsconfig.json`
   Expected: exit 0.
2. `npm --offline --prefix ui run build`
   Expected: exit 0.
3. `agent-code-skills plan check docs/plans/hand-paint-finish`
   Expected: exit 0.
4. Gated: interactive check of the three buttons in a real browser on :8380.
   Expected: each button starts one job and the session links its version.

## Risks

Interactive acceptance stays open while browser control is unavailable. The comparison image appears only for versions that carry `comparison.png`; older reconstructions show the review sheet alone.

## RESULT

Implemented as specified, plus a shell-border checkbox so the reported fallback is reachable from the UI. tsc exit 0; offline build exit 0; plan check exit 0. Item 4 gated, not run.
