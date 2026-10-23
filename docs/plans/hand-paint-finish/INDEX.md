# Add the hand-paint finishing seam to surface authoring

## Outcome

Deliverable: hand-paint-finish-v1, requested 2026-10-23 by the AEP painterly-knowledge-ingestion plan (spoke S06). The trial on :8380 exports a hand-paint bundle per session, marks seam-heal zones from writer ownership, counts reconstruction permissions as writers and shows a source-versus-result sheet. Generated paint stays a basis; hand painting finishes it. Primary 8370 is unchanged.

## Decisions

- D1 (2026-10-23): The seam is additive inside the existing `uv_context` step and the existing authoring-actions endpoint. No new step module, HTTP route, model, package or GPU work.
- D2 (2026-10-23): `handoff.json` never defaults a density. `declared_density_pixels_per_metre` is the contract's declared density or null; `physical_scale` is `declared` or `unknown`; `texels_per_metre_p50` appears only with a measured metres-per-unit scale. An art-profile declaration for this repository is deferred to the owner.
- D3 (2026-10-23): The shell-border heal zone is an explicit, reported fallback (`heal_mask:shells`), never chosen automatically.
- D4 (2026-10-23): Writer ownership folds `uv_context` reconstruction and publication permissions into labels. Labels change on historical sessions; pixels do not.

## Constraints

- C1: No code tests, commits, pushes, CI, model downloads or GPU additions (AGENTS.md). Static checks and an import smoke only.
- C2: Edit only the declared write set. Untracked files of other lanes receive additive edits; never reformat, reorder or delete.
- C3: No `bpy` outside `blender_ops/`; no edits to server/app.py, server/jobs.py, server/library.py or server/presets.py.
- C4: Preserve source geometry, UVs, alpha and other maps; reconstruction keeps its existing permission guard.

## Terms

- Handoff bundle: guide renders, face IDs, cameras, UV layout, base colour, permission and `handoff.json` for one session source.
- Seam-heal zone: a UV permission mask around writer-label joins inside one UV shell.
- Basis: generated paint that hand painting finishes.

## Spokes

| ID | File | Outcome | Depends on | Skills | Write set | State | Commit | Result |
|---|---|---|---|---|---|---|---|---|
| S01 | 01-handoff-bundle.md | Export the hand-paint bundle and heal-zone helpers | none | python:python-core | steps/_paint_handoff.py, steps/uv_context.py, tools/stage_multi_view_trial.py | done | - | 01-handoff-bundle.md#result |
| S02 | 02-heal-zone-ownership.md | Own brush returns and expose the new authoring actions | S01 | python:python-core | steps/_paint_seams.py, server/paint_sessions.py, server/authoring_contracts.py | done | - | 02-heal-zone-ownership.md#result |
| S03 | 03-review-sheet-docs.md | Show the comparison sheet, add three buttons and document the seam | S02 | web:typescript-core, python:python-core | ui/src/multi-view-api.ts, ui/src/AuthoringWorkspace.tsx, docs/SURFACE-AUTHORING.md, .codex/skills/effigy-surface-authoring/SKILL.md, docs/plans/hand-paint-finish | done | - | 03-review-sheet-docs.md#result |

## Reading rule

Read this index, your own spoke and the RESULT of each spoke in its Depends-on field, then the named sources. One executor updates state.

## Non-goals

Painting an asset, running Blender or model jobs, a new art profile, automatic seam repair, cleanup of historical versions, primary promotion.

## Open questions

- Art-profile declaration for Effigy: deferred until the owner decides this repository's art pin; until then every handoff reports a missing density declaration.
- Runtime sample on :8380 (POST handoff after staging and restart): deferred until the owner frees the trial; resume with the S01 verification item 3.
