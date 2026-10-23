# Inspect 360 degrees and repaint continuous stylized surfaces

Spoke: S03
Outcome: Inspect 360 degrees and repaint continuous stylized surfaces.
Depends-on: S02
Decisions: D5
Constraints: C1, C2, C3, C5, C6
Skills: python:python-core, art:texture-painting-core, art:art-3d-realtime-core
Read-set: INDEX.md, 02-full-hut.md#result, CODE.md, tools/fibo_trial_worker.py, steps/paint.py, steps/_views.py
Write-set: tools/fibo_trial_worker.py, docs/plans/fibo-trial/03-overlap-retry.md, scratch/lanes/fibo2
State: done

## Context

The owner rejected 039 for mismatched joins throughout the building and a roof
that reads as realistic straw. Preserve the good masonry and edited geometry;
repaint the roof with broader stylized brush shapes and repair actual joins.
The owner explicitly requests a 360 presentation and another painting round.
Expected 96 turns; standing 256-turn breaker and implementation ceiling apply.

Art profile: 409 triangles, unique padded UV atlas, 1024 cap, 432.322 texels per
Effigy asset unit; no metre conversion. The current candidate 039 supplies
accepted non-roof context, not whole-asset acceptance. Pre-FIBO 006 can supply
the roof core's simpler source appearance; it is not called raw retail imagery.
The supplied inn screenshot remains an appearance reference.

## Evidence

- scratch/lanes/fibo2/hut_surface_pass.py:71 excludes faces at 90 percent coverage,
  preventing deliberate core overlap across established paint boundaries.
- steps/paint.py:240 guards selected texels but does not prove visual continuity.
- The invoked cumulative-painting guidance separates full-frame context, core,
  transition and UV write permission. Its corner core crosses both adjoining
  faces; overlap must be measured against actual predecessor paint.
- The invoked brush-painting guidance rejects hard view ownership and uses
  cross-boundary strokes. It supplies style and continuity principles here;
  FIBO remains instruction editing, not a claim of executing brush dabs or the
  canonical Comfy 26-view graph.

## Steps

1. Render the requested before 360 and inspect the complete exterior.
2. Produce and inspect a broad-stroke roof anchor, protecting non-roof surfaces.
   Keep materials, palette and camera tilt consistent around subsequent views.
3. Use new core plus an explicit band of previously changed paint. Measure both
   before generation. Preserve complete updated context; project through the
   original mask. Inspect the saved mesh, not just the generated plate.
4. Close the orbit and repair wall joins across their boundaries, retaining the
   good masonry pattern. Render and inspect the resulting full 360.
5. Record actual runtime, preservation and visual limitations in this spoke.

## Files to touch

- tools/fibo_trial_worker.py
- docs/plans/fibo-trial/03-overlap-retry.md
- scratch/lanes/fibo2

## Verification

1. Scoped Ruff and plan structure must pass; no code tests or hashes.
2. Ordinary application jobs must retain exact geometry/UVs, 1024 texture and
   protected pixels. Measured overlap must include a core crossing the join.
3. Before/after 360 presentations and baked views must be inspected for stroke
   scale, palette, row alignment, material boundaries and orbit closure.
4. Primary runtime and other GPU work remain intact; no downloads or promotion.

## Risks

FIBO may redraw features or preserve excessive detail. Reject such anchors
before propagating them. More cameras alone do not fix absent overlap or bad
style. A generation mask is distinct from final write permission; neither a
feather setting nor a high coverage percentage proves a good join.

## RESULT

- Delivered 103_paint, job fb6b33868a35: repaired masonry, muted painted roof,
  localized crown healing and requested full 360. Saved appearance revision 3.
- Outputs: asset rim_elm_hut_fibo_trial on port 8380; mesh.glb (3861888 bytes),
  presentations/103_paint-360.mp4 and .png. Compare before 039_paint-360.
- Exact geometry/UVs; 409 triangles; one 1024 RGBA16 atlas; protected samples
  unchanged. Scoped Ruff, plan structure and whitespace checks pass.
- Offline runtime observed; primary and trial backends unchanged. No tests,
  hashes, downloads, commits, pushes or shared-runtime changes.
- Agent-selected retry, awaiting owner visual judgment. Roof uses the earlier
  painted base plus restrained FIBO detail; FIBO alone did not establish the
  requested inn finish. Brush variation and soft vent/eave transitions remain.

## Runtime observations

Before/after 360 presentations use 48 frames, 7.5-degree yaw increments, pitch
-29 and six frames per second. Eight-angle sheets were inspected. Final103 has
a quieter matte roof and improved joins; perfect seams, equivalent inn quality
and owner acceptance are not claimed.

| Yaw | New texels | Prior overlap | Full-strength overlap | Result |
|---|---:|---:|---:|---|
| 25 | 61265 | 0 | 0 | 050 -> 051_paint |
| 70 | 20148 | 11710 | 10614 | 054 -> 055_paint |
| 115 | 17362 | 13260 | 11211 | 058 -> 059_paint |
| 160 | 20326 | 6220 | 5145 | 061 -> 062_paint |
| 205 | 11091 | 16560 | 12221 | 064 -> 067; 069 -> 070_paint |
| 250 | 3730 | 14080 | 11995 | 072 -> 073_paint |

These planned footprints include a 64-pixel band into predecessor paint; final
masks exclude invented details. Roof centroid height stays >=0.48 to exclude
stone ledges. Yaw295 found no substantial new core and submitted no generation.
Coverage does not prove quality. 064's invented chimney was excluded, then healed
by069. Rejected anchors046/047/065/066/096-099 were never projected. They returned
flat patches, copied architecture, fine fibres, isolated dashes or splinters.
The canonical Comfy 26-view workflow is not qualified here.

Wall cores span both writer regions with 16-pixel half-width and 8-pixel feather.
Writer IDs are sampled without interpolation; UV gutters are excluded. Materials
have separate prompts/masks. Retained:078->079 at yaw70 (38043 planned texels);
081->082 at160 (26201);084->085 at250 (frame only, invented beams excluded);
087->088 at250 (walls/ledge only, buff foundation band excluded);090->091 at340
(limewash,12921);093->094 at340 (foundation,25200). Openings/roof stay protected.

Palette-only study075 retained uneven roof marks. Selected100_upload derives
from094 using 75% of the owner's painted roof002_import_model plus25% cumulative
FIBO detail. One material-wide affine colour adjustment at strength0.55 uses
049 swatch RGB10/50/90 percentiles. Swatch049 is the inn screenshot crop
(560,160)-(700,300). This changes130847 roof texels and owned empty gutters only.
Four geometry/UV accessors are compared before reusing face ownership. This is
explicit texture composition, not FIBO alone or per-view darkening.

The blend exposed an inherited crown rectangle. Capture101 -> reference102
(job b302a3fc54ee) uses full-frame native blank-region context and23256 roof-only
texels. It continues subdued neighboring strokes. Projection103 (fb6b33868a35),
strength1/feather10, removes the mark. Appearance revision3 retains FIBO and
carries the revised roof description.

Independent final checks: four exact geometry/UV accessors;409 triangles; one
1024 RGBA16 atlas;233978 changed occupied texels, zero outside paint/roof
permissions; unchanged alpha. Palette100 changes zero occupied non-roof texels
vs094. Repair103 changes zero occupied texels outside its permission vs100.
All14 projected reference images have exact protected pixels and alpha.
Reference102 reports103.36s model execution and14.17GiB peak allocation; these
exclude cold-start latency. Final GLB:3861888 bytes.

Offline=true; zero browser violations; sampled worker connections empty. This
is observation, not OS containment. No FIBO workers remain. PrimaryPID49908 and
trialPID53432 retain their start times. Sources remain uncommitted. Requested
presentations and ordinary app versions remain; no library cleanup ran.
