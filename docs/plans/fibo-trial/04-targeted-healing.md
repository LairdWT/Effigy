# Heal the owner-marked hut defects

Spoke: S04
Outcome: Heal the owner-marked hut defects.
Depends-on: S03
Decisions: D5
Constraints: C1, C2, C3, C6
Skills: python:python-core, art:texture-painting-core
Read-set: INDEX.md, 03-overlap-retry.md#result, CODE.md, steps/paint.py
Write-set: docs/plans/fibo-trial/04-targeted-healing.md, docs/plans/fibo-trial/INDEX.md, scratch/lanes/fibo2
State: stale

## Context

The owner considers 103 reasonably good and supplied five close-up screenshots.
Continue masked local image editing. Preserve the muted roof finish, exact
geometry/UVs, 409 triangles and one 1024 atlas. Expected 64 turns; standing
256-turn circuit breaker applies. No tests, hashes, downloads or subagents.

## Evidence

steps/paint.py:68 owns the static atlas material contract. Project-local 3dgen-prompt-core supplies model-specific edit wording; it is not an external bundle-qualified skill name.

The white eave strips occupy downward-facing faces that the earlier elevated
views could not paint. The chimney top consists of four upward-facing triangles.
The foundation has inconsistent stone sizes and colour fields; wall shadow and
material smears remain. Numerical protection alone did not establish quality.

## Steps

1. Capture the chimney cap from above and eaves from below; bind selections to
   actual face ownership before generating.
2. Heal the cap, eave undersides and vent with small material-specific masks.
3. Continue one consistent grey-green foundation treatment through overlapping
   views, retaining context and stone scale across corners and step risers.
4. Remove wall stains/material smears without moving the stone courses.
5. Inspect baked close-ups and a final orbit. Keep every applied result in normal
   application history and record remaining defects explicitly.

## Files to touch

- docs/plans/fibo-trial/04-targeted-healing.md
- docs/plans/fibo-trial/INDEX.md
- scratch/lanes/fibo2

## Verification

1. Scoped Ruff. Expected: no findings for changed helpers.
2. Geometry/UV and texture inspection. Expected: exact accessors,409 triangles,1024 RGBA16.
3. Protected sample inspection. Expected: zero occupied changes outside selected permissions.
4. Baked close-ups/orbit. Expected: every owner-marked defect and side is inspected; remaining defects stay explicit.
5. Runtime observation. Expected: offline policy, primary session and other GPU work are preserved.

## Risks

Small cap texel allocation limits fine rim detail. Underside views may be
occluded. FIBO can invent features or change stone scale; inspect before applying.
Do not treat a good preview as proof until it is projected and re-rendered.

## Historical RESULT before multi-view replacement

- Active: selections and localized healing in progress.

## Runtime observations

Chimney cap: 105 sealed the flue and was rejected. Closer capture106 with
unblanked instruction editing produced107, projected as108 (9cb37f2dde79).
The four top faces own509 atlas texels; the baked close-up shows a dark opening
and continuous rim. No geometry hole was added; this is a texture repair.
Eave underside masks use actual downward-facing normals and a low camera.
The first side selection admits9417 texels; window-head wall infill is excluded
and belongs to the separate limewash repair.

Eaves: 110 was too gold and was not applied. Recolour edits111->113 and
115->116 match the muted roof. Front continuation118->119 includes2303
previously painted texels,1278 inside the full-strength core. The upper roof
remains outside these downward-face selections. Vent121->122 cleans the
front-facing slats; a lower capture exposes the remaining inner surfaces.
Foundation reference112_upload is an actual crop (653,763)-(743,817) from
101_paint, containing only the existing front fieldstones.

Vent lower-view124->125 repaints newly visible inner faces, with1851
overlapping texels and1457 inside the full-strength core. Local roof repair
127->128 removes the surrounding inherited brown blotches while preserving
the vent geometry/slats and the broader roof finish. It uses20733 roof texels.
Limewash selection includes the blank window-head infill and pale stone under
the sill, while retaining timber frame faces. First wall view129 is at yaw65,
pitch-12; its footprint is33889 texels.

Wall130 was retained only below image y=0.56 in131; its generated straw
window head was excluded. Native upper-wall inpaint133->134 fills the blank
head with pale stone courses and removes straw smears. Left-wall continuation
135 has29632 planned texels with1923 overlapping previous paint (945 core).

The left preview136 invented an extra window: the main footprint was
excluded in137 and healed as solid stone by139->140. A second false opening
near the doorway appeared in the subsequent front check;142->143 removes it.
The foundation starts from143. Anchor145->146 selects larger, cleaner
grey-green fieldstones than the prior patchwork, with protected wooden treads.
This is an agent-selected scale change for consistency, not owner acceptance.
The yaw85 continuation has27638 planned texels,17403 overlapping prior paint
and13725 overlapping in the full-strength core. Camera advance is60 degrees.

Owner correction: the foundation stones are too large and do not match the
styling. The larger-stone wrap145->161 is rejected. Preserve the other repairs;
restore or rework only the foundation using the smaller stone scale from143.
The subsequent ledge repair163->164 is separate. Door-recess candidate166
completed but remains unreviewed and unapplied.

The owner proposed joint multi-view painting and a single combined bake.
Inspection confirms the existing Legaia26-direction camera set and best-view
projection compositor. Effigy's current paint apply consumes one camera, and
the FIBO adapter produces one1024-square preview with an optional style image.
A shared view-sheet edit and combined atlas bake require additional plumbing;
neither simultaneous baking nor multiple reference inputs alone establishes
cross-view generation consistency. This is a proposal under discussion, not
an implemented or accepted replacement for the current healing workflow.

## RESULT

Superseded by the owner-approved multi-view-paint plan and painting-completion repair workflow. Original chimney, eave, vent and wall repairs are recorded above; the rejected large-stone foundation was restored in source167 before multi-view comparisons. Twelve full-set candidates and their limits remain in multi-view-paint/S11. Painting-completion/S03 retains wall260, roof265 and foundation268 on the separate whole-house branch; Genesis227 remains untouched. Painting-completion/S06 corrects projection-mask edge holes and provides explicit refresh for old sessions. Historical results are preserved. Material continuity and owner visual acceptance remain open; this stale unit does not authorize more inference or primary promotion.
