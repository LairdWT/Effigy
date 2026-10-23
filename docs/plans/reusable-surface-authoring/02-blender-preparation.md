# Integrate isolated Blender preparation and reversible round trips

Spoke: S02
Outcome: Integrate reversible Blender and UV preparation
Depends-on: S01
Decisions: D1, D2, D3, D4, D5
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, powershell:powershell-core
Read-set: docs/plans/reusable-surface-authoring/INDEX.md, docs/plans/reusable-surface-authoring/01-authoring-contract.md#result, server/blender_client.py, steps/_uv_transfer.py, docs/adr/8a04ffd6-isolate-the-local-blender-editing-session.md, docs/adr/cb12259a-reuse-configured-portable-blender.md
Write-set: server/blender_client.py, server/app.py, server/library.py, steps/uv_context.py, tools/blender_prepare.py, tools/stage_multi_view_trial.py, docs/plans/reusable-surface-authoring
State: done

## Context

Use blender-core -> blender-asset-workflows and its uv-addon-tools reference for preparation; use blender-mcp-cowork only for the explicitly identified private workfile. The existing loopback bridge is the integration seam. Blender provides mesh/UV inspection, deterministic preparation and manual painting; Effigy remains the session and publication owner.

Expected turns: 18. Preserve standing budgets and prior results. Source changes remain uncommitted. Ordinary app outputs are runtime artifacts under C4, not extra evidence packs.

## Evidence

- server/app.py:294 exposes Open; server/app.py:312 exposes Pull through server/blender_client.py.
- server/blender_client.py:306 owns opening a version; server/blender_client.py:324 owns importing the edited result.
- steps/_uv_transfer.py:24 binds corresponding triangles before transferring texture samples.
- docs/plans/painting-completion/09-source-locked-repairs.md:56 records the actual UV Squares BMLoopUV.select incompatibility; :58 records zero-overlap 90-degree UVPackmaster packing.

## Steps

1. Resolve Blender and provider paths from the existing portable tools configuration. Open only a copied, revision-bound workfile in the isolated Effigy session; verify process, scene and source identity before commands. Never fall back to another Blender socket or save an unrelated open scene.

2. Add preparation inspection for geometry contract, transforms, material/image sharing, UV overlaps, degenerates, stretch, texel allocation and actual gutter clearance. Preserve original UV layers. Present defects and proposed operations; already valid UVs do not trigger another unwrap.

3. Wrap the maintained generic UV adapter rather than copying provider internals. ZenUV handles selected unwrap; UVPackmaster packs with alignment, 90-degree rotation only and no flips for the current architectural profile. Compute required padding from the profile and output filtering; measure achieved clearance. Do not apply those choices universally to organic or line-art profiles.

4. Treat UV Squares as unavailable on the observed Blender/API combination until a compatible operation is qualified. Use it only on eligible grid-like patches. Existing rigid alignment may serve a separately named operation; it must never be reported as successful UV Squares execution. Add-on repair or version replacement requires its own approved change.

5. Return UV-only edits through exact triangle correspondence with one transfer from the named source. Return topology edits as a new geometry revision with explicit new-surface/unmapped coverage; invalidate affected masks, captures and candidates. Preserve old versions. Do not use nearest-colour transfer to conceal failed correspondence.

6. Expose inspect, prepare, open and pull status through existing jobs, including cancellation and saved-file freshness. Keep helper objects out of exported game meshes. Save one private authoring workfile and reference ordinary output versions; no automatic proliferation of Blend/GLB copies per image.

## Files to touch

- server/blender_client.py
- server/app.py
- server/library.py
- steps/uv_context.py
- tools/blender_prepare.py
- tools/stage_multi_view_trial.py
- docs/plans/reusable-surface-authoring

## Verification

1. Through trial Open/Pull, inspect a copied fixture, perform one eligible UV operation and reopen it. Confirm the unrelated Blender scene/profile is unchanged and the returned version names its source.
   Expected: The isolated round trip names its source and leaves unrelated scenes and preferences unchanged.

2. Observe zero positive-area UV overlaps for a unique-atlas result, measured clearance, unchanged geometry for UV-only work and bounded source resampling. For topology editing, expect explicit invalidation and unmapped-face reporting.
   Expected: UV-only edits preserve geometry; topology changes invalidate dependent inputs and report unmapped faces.

3. Exercise the known UV Squares incompatibility and a mismatched bridge scene using ordinary preparation actions; expect specific errors without fallback or source modification.
   Expected: Specific errors preserve the source and do not invoke another provider.

4. Run scoped Ruff for changed Python and inspect the bounded staging manifest. Do not install providers or invoke a broad Blender verifier.
   Expected: Changed Python passes Ruff; staging names only authorized files.

## Risks

Packing cannot repair contradictory painted features. UV-only resampling introduces filtering; repeat transfers must start from a named source rather than repeatedly baking previous transfers. A new topology revision cannot inherit an old selection merely because filenames match.

## RESULT

Implemented isolated provider preparation, source/paint UV roles, exact triangle-colour transfer, explicit UV scale, geometry lineage and scene identity guards. Trial inspections: hut314, crate002/004/006/008, curved figure002. UVPM job2f4df98421ef produced crate007 with362 exact source triangles/normals; exact clearance jobf577038ee8c9 measured4.9974px minimum gap, zero overlapping island pairs. ZenUV+UVPM job4b31e2b51b16 produced009. Open/Pull on003 produced005 in isolated8381. Failed attempts preserved source and identified autosave lifecycle, scratch identity and native NO_SPACE constraints. Nonconstant secondary-map rebakes and transparent-surface UV preparation remain explicitly unsupported; painting preserves its prepared source. Scoped Ruff passes. AEP standards check reports broader typing findings under the accepted upstream-checks deviation; it is not a strict-analysis pass. UI/lifecycle qualification remains S07/S09.
