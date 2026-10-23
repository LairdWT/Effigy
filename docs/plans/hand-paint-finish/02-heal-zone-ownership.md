# Own brush returns and expose the new authoring actions

Spoke: S02
Outcome: Own brush returns and expose the new authoring actions
Depends-on: S01
Decisions: D1, D3, D4
Constraints: C1, C2, C3, C4
Skills: python:python-core
Read-set: docs/plans/hand-paint-finish/INDEX.md, docs/plans/hand-paint-finish/01-handoff-bundle.md#result, steps/_paint_seams.py, server/paint_sessions.py, server/authoring_contracts.py, server/app.py
Write-set: steps/_paint_seams.py, server/paint_sessions.py, server/authoring_contracts.py
State: done

## Context

Writer ownership counted only `paint` apply permissions, so a Blender brush return reconstructed through `uv_context` left no writer label. The session owner needed actions for the export, the heal zone and a reconstruction limited to that zone.

## Evidence

Line numbers are before this change.

- steps/_paint_seams.py:77 counts only `paint` apply permissions; :94-130 builds advisory seams; :123-125 sets the dilation radius.
- server/paint_sessions.py:342-386 dispatches authoring actions; :349-350 requires a mask version; :363-374 publishes by reference.
- server/app.py `AuthoringAction.action` is a plain string, so new action strings need no route change.
- server/authoring_contracts.py:136-147 keeps acceptance owner-only.

## Steps

1. `ownership_map`: fold `uv_context` reconstruct and publish permission versions into writer labels; add the 24-bit label capacity guard before folding.
2. `authoring_action`: accept `handoff`, `heal_mask`, `heal_mask:shells` and `reconstruct_heal`. Handoff and heal-zone actions need a saved contract but no mask version or deterministic method. `reconstruct_heal` returns 409 `missing_heal_mask` without a saved zone and passes the zone as the reconstruction mask.
3. Publish takes `mask_version` from the candidate's own params, so a heal reconstruction publishes against its zone.
4. `_reconcile` maps `authoring_handoff` and `authoring_heal_mask`; `heal_mask:shells` and `reconstruct_heal` reuse the heal-mask and reconstruct mappings. `set_authoring` carries `handoff` and `heal_mask` forward.
5. `ReviewDecision` gains optional `round` (1-64 characters) to tag a hand-paint review round.

## Files to touch

- steps/_paint_seams.py
- server/paint_sessions.py
- server/authoring_contracts.py

## Verification

1. `.venv/Scripts/ruff.exe check .`
   Expected: exit 0.
2. `.venv-ml/Scripts/python.exe -c "import steps.uv_context, steps._paint_handoff, steps._paint_seams"`
   Expected: exit 0.
3. Gated: on the trial, `reconstruct_heal` before `heal_mask`.
   Expected: 409 `missing_heal_mask`; the source is unchanged.

## Risks

Folding reconstruction permissions changes advisory seam suggestions on historical sessions; labels only, no pixel change. A carried-forward heal zone stays bound to the session's geometry revision, which the session cannot change.

## RESULT

Implemented as specified. Ownership folds reconstruct and publish permissions behind the label capacity guard; the four action strings, publish mask binding, reconcile mappings, carry-forward and `ReviewDecision.round` are in place. Ruff exit 0; import smoke exit 0. Item 3 gated, not run.
