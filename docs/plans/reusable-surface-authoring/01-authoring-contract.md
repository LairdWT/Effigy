# Define reusable authoring contracts and qualification fixtures

Spoke: S01
Outcome: Define source, profile and method contracts
Depends-on: none
Decisions: D1, D2, D3, D4, D5
Constraints: C1, C2, C3, C4, C5, C6
Skills: aep:aep-core, planning:planning-core, python:python-core
Read-set: docs/plans/reusable-surface-authoring/INDEX.md, server/paint_contracts.py, server/paint_sessions.py, docs/plans/painting-completion/11-material-base-quality.md#result
Write-set: server/authoring_contracts.py, server/paint_sessions.py, docs/plans/reusable-surface-authoring
State: done

## Context

This is the design and contract gate for the workflow, not permission to resume hut repairs. Extend the existing paint-session owner; do not create a competing painting database. New module names below are proposed implementation locations. Resolve architectural choices in this unit before dependent code starts.

Expected turns: 12. Preserve standing budgets and prior results. Source changes remain uncommitted. Ordinary app outputs are runtime artifacts under C4, not extra evidence packs.

## Evidence

- server/paint_sessions.py:45 binds a session to a source, geometry revision, recipe, selection and capture layout.
- server/paint_contracts.py:21 records exact panel rectangles; current panel sizes alone do not express a sampling-quality contract.
- docs/plans/painting-completion/11-material-base-quality.md:56 records source softness, 0.5605 median camera pixels per atlas texel and a 5.3346-fold difference from later repair sampling.

## Steps

1. Define typed versioned records for an authoring profile, source roles, material regions, sampling policy, method capabilities, preparation revision and review decision. Reuse existing version IDs and job records. Keep machine paths in local bindings. Describe backward-compatible loading of old pair, whole-sheet and finish sessions without rewriting them.

2. Separate immutable original, owner-accepted checkpoint, working draft, preferred candidate, appearance reference, registered donor and rejected comparison. A working draft may advance within one authorized finite batch; it never becomes owner-accepted automatically. Preserve provenance for inherited paint: Genesis foundation success does not establish who authored the walls.

3. Propose static, single-primitive, unique square-atlas RGB painting as the first qualified scope. Keep alpha and other maps protected. Native Blender workfiles may contain authoring helpers, but the export boundary must meet this contract. Deformation, shared-image multi-object editing, multiple materials and UDIM require separate capability contracts; do not flatten them silently.

4. Require an explicit UV profile, asset scale or declared scale-unknown status, atlas cap, intended viewing distance/native output extent, feature scale and reference appearance. Derive density from measured approved references when available; never invent pixels per metre. Distinguish padded islands from intentionally squared line-art UVs.

5. Freeze three fixture identities in this spoke before runtime: the existing hut, one different rectilinear prop/building, and one curved or recessed static object. Prefer existing owned assets; otherwise use disposable synthetic Blender geometry as ordinary application input. Pin source, constraints and review views. Do not use the accepted inn as a writable experiment.

6. Record implementation decisions and unresolved capability limits through the repository's supported ADR tooling when required. Proposed defaults in this plan become execution choices only after the owner authorizes implementation. Carry forward open visual acceptance, unavailable add-on operations and primary-lane promotion; do not relabel historical results.

## Files to touch

- server/authoring_contracts.py
- server/paint_sessions.py
- docs/plans/reusable-surface-authoring

## Verification

1. Inspect the typed records and the existing session API boundary: each mutable property has one owner, each source role has a distinct meaning, and older sessions remain readable.
   Expected: Records distinguish source roles and preserve legacy session loading.

2. Inspect the frozen fixture/profile entries in this spoke: all three have source identities, atlas/UV constraints, material targets and review conditions; unknown physical scale is explicit.
   Expected: All three fixture profiles name inputs, limits and review conditions; unknown scale stays explicit.

3. Run scoped Ruff on changed Python files and `agent-code-skills plan check docs/plans/reusable-surface-authoring`; expect no findings. No runtime qualification is claimed by this design unit.
   Expected: Scoped Ruff and plan validation pass; no runtime claim follows.

## Risks

A profile can become paperwork without enforcing decisions at Capture and Generate. Bind only fields consumed by admission, rendering, preservation or review. If a fixture needs unsupported geometry, replace the fixture with another representative static asset, not the user's source mesh.

### Frozen qualification inputs

Runtime imports create separate trial assets; the primary sources remain read-only.

| Fixture | Immutable input | Profile and review |
|---|---|---|
| Architecture | trial rim_elm_hut_fibo_trial/313_uv_context, with 227_paint_set as preferred appearance reference | 409 triangles; 1024 RGBA16; padded islands; scale unknown; preserve existing feature proportions; stone, wood, wall and thatch continuity; 26 directions plus eaves and chimney |
| Rectilinear prop | primary effigy_setup_crate/007_bake/mesh.glb | 362 triangles, one primitive, no skin; 1024 cap; padded islands; preserve wood structure; inspect six sides, corners and borders |
| Curved static figure | primary effigy_setup_figure/003_trellis2/hi.glb | 11370 triangles, one primitive, no skin; retain source atlas within 4096 cap; padded islands; scale unknown; preserve captured material identities; inspect curvature and recessed/occluded surfaces |

All use a detail sampling floor of one camera sample per atlas texel in both surface directions, native review extent 1024 pixels, and no invented physical density. A study preview remains explicitly unqualified for detail. Existing UVs and image encoding are inspected in S02 before painting; a failed preflight is not permission to simplify or remesh. S01 settles single static primitive, exact alpha/other-map preservation, three separate authoring methods and session-owned profiles/review records. Implementation sample submissions share S07's twelve-call cap.

## RESULT

Added immutable validated authoring records for source roles, preparation revision, material intent, sampling, method, budget and owner review. The existing paint-session owner now saves revision-bound profiles, retains referenced inputs, invalidates affected candidates and records preference/rejection/explicit owner acceptance separately. Legacy sessions remain opt-in and are not rewritten. Three sources are frozen above; GLB inspection confirmed the two additional fixtures are single-primitive and unskinned. Scoped Ruff passes for both changed modules. Route/UI and runtime qualification belong to later units; no generation, source publication or visual acceptance occurred. Portable goals are in GOALS.md; the native app refused another goal because its prior goal remains unfinished.
