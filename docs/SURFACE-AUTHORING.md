# Effigy surface authoring

The trial workspace runs on `http://127.0.0.1:8380`. Primary 8370 is unchanged. These instructions describe the implemented controls; interactive acceptance remains open in the [qualification plan](plans/reusable-surface-authoring/07-cross-asset-qualification.md). Backend samples alone do not prove the interface is usable.

## Quickstart

1. Open a supported mesh, expand **Multi-view paint**, and create or reopen a saved session. In **Surface authoring**, declare the original source, prepared source, material regions and appearance goal. Save the contract. Inspect UVs before deciding whether a new preparation is needed.
2. Select the surface once and use **Capture view set**. Inspect the actual input sheet and sampling report. Choose a method under **Appearance and source contract**: model edit, registered source or native Blender brush return. Make one bounded edit; retain good surrounding pixels.
3. Inspect the baked mesh and close views before publishing. **Mark preferred**, **Reject appearance**, publication and **Accept appearance** are separate actions. Only the owner's explicit visual decision accepts appearance. Publication references the reviewed candidate; it does not overwrite the source.

## Source and profile

The current contract accepts one static triangle primitive with embedded textures, one unique square base-colour atlas and no skin, animation, morph target, texture transform or overlapping paint UVs. Existing multi-material and animation tooling remains separate. Create an explicitly approved static copy when necessary; do not silently flatten a production asset.

Source roles distinguish original, working, preferred, accepted, appearance reference, donor and rejected history. A donor is an explicit registered mesh, not whichever rejected render happens to be newest. State belongs to the asset's saved paint session. Its preparation revision binds source, geometry/UV identity, atlas size, UV profile and requested packing margin.

Describe each material by identity, palette, feature size relative to the mesh or a measured reference, brush marks and preservation intent. Observations describe the source; requested style describes the intended result. Face subsets are disjoint. An unassigned default material provides context for remaining selected surfaces. Keep intentional beams, stair treads and material boundaries distinct.

Physical density requires a measured metres-per-unit scale. Without it, inspection reports texels per asset unit. Do not invent physical dimensions or use a universal density target. The model-call budget belongs to the saved pass; a new finishing pass shows its own explicit allowance.

## Prepare

**Inspect UVs** measures current topology, occupancy, degeneracy, native-raster overlap and geometric island clearance. Geometric clearance is distinct from the raster estimate; do not interpret one as the other. The interface reports the measured result, not merely the solver's requested margin.

**Pack with UVPackmaster** creates a new prepared version with 90-degree rotations and no flips. **ZenUV unwrap and pack** first unwraps, then packs. UV scale is explicit; a `NO_SPACE` result never silently reduces it. The requested gutter includes a solver reserve, then a separate inspection checks the resulting layout. Exact triangle correspondence transfers appearance once from the named source. Original files remain unchanged.

UV preparation currently requires opaque surface texels and constant secondary maps. Nonconstant maps need a separately qualified rebake. Transparent atlas gutters are allowed. The current UV Squares provider fails on `BMLoopUV.select`; do not describe installation as a successful operation. A square line-art profile is a declaration, not an automatic UV Squares implementation.

**Open working copy in Blender** uses Effigy's configured isolated scene and bridge. It does not target another open Blender scene. **Pull Blender changes as donor** saves a separate version. Save the contract with that donor before masked reconstruction. If geometry changed, create a new source session and selection; do not force an old mask onto it.

Preparation keeps the selected painting session locked while its job is active. Finish or cancel that operation before switching sessions. Each session has its own displayed inspection state. A progress-connection failure keeps the job active and retries; it is not reported as successful completion.

## Select and capture

Face selection and visible strokes change one authoritative UV mask. Every camera derives screen permission from that mask and front-most face ownership. Green means paint here. Changing the viewing camera does not change the captured projection cameras.

Captures are unlit base colour. The sampling report measures both axes of UV-to-camera projection at native input resolution. Detail mode requires the declared minimum camera samples per reachable atlas texel. Orange indicates undersampling; purple indicates inaccessible texels that stay unchanged. Study mode is explicitly a lower-resolution style experiment. Enlarging a finished image does not retroactively qualify missing source samples.

If a full-asset capture is undersampled, select a smaller meaningful material region or explicitly choose a supported higher-resolution capture. Do not bypass the floor or enlarge the final atlas automatically. After contract changes, **Refresh camera masks and sampling** rebinds admission. Use the diagnostic projection before inference when registration is uncertain.

## Author

| Method | Input and behavior | Limits |
|---|---|---|
| Local model edit | Fixed source captures, shared appearance brief and exact permission mask; model-specific controls remain visible | Whole-sheet editing shares image context but is not synchronized 3D diffusion. Layout, feature scale and art quality still require baked review. |
| Registered source reconstruction | A donor with matching triangle positions supplies RGB only inside the saved selection | Exact registration is required. Source geometry/UVs, alpha and other maps are preserved. No model loads. |
| Native Blender brush return | Explicit Texture Paint/image_paint strokes on the private copied mesh; Pull supplies the registered donor | A brush stroke is a deliberate native operation, not an automatically generated painter. The same reconstruction guard protects the destination. |

**Refine current** retains the existing capture as conditioning. **Restore registered source** substitutes donor colour only inside the permitted core; current surrounding context stays in place. **Restyle** states the intended resulting material explicitly. None of these operations may silently choose another source or model.

Genesis uses the installed NVFP4 checkpoint with full-precision matrix multiplication; this is not native FP4 kernel acceleration. FIBO supports its structure-preserving edit and optional reference image. A style image is rejected for other adapters or FIBO blank-region conditioning. MOSS uses the installed Turbo v2 recipe and its actual recorded precision; measure complete local timing rather than relying on publisher speed claims. Check `server/reference_models.py` and job metadata for exact bindings rather than copying model paths into prompts.

Paired and whole-set generation preserve fixed panel rectangles. Completed captures/results survive restart. Generated pixels are independently composited against permission and alpha. The combined bake uses exact ownership and replacement instead of averaging contradictory line patterns. Only permitted empty gutters are refreshed.

Dense captures use bounded footprint filtering when transferred into the atlas: each target texel samples its projected area within one eligible face and camera. This reduces aliasing without blending competing views. Unchanged source pixels bypass resampling. Excessive projection cost reports a UV-distortion/region-size error. Historical finishing plans keep their recorded filter policy; newly planned repairs use the current policy.

Repair diagnosis retains accumulated writer ownership across partial edits. New labels cover only changed surface texels; unchanged prior ownership survives. Older partial bakes can reconstruct labels from immutable parent pixels, while unknown source context remains a baseline label. These labels locate possible joins; they do not prove a visible seam or coherent art.

## Hand-paint handoff and heal

A generated or reconstructed surface is a basis that hand painting finishes. **Export hand-paint handoff** writes a new `uv_context` version that references the source mesh and adds: `guide/<id>.png` unlit base-colour renders at the session's front yaw and its 90, 180 and 270 degree turns at the review pitch (-25 degrees), `faces/<id>.png` face IDs (24-bit RGB, face index plus one), `cameras.json`, `uv-layout.png`, `basecolor.png`, `permission.png` (the saved selection, or every covered texel when none is saved), `handoff.json` and `contact-sheet.png`. The handoff needs a saved contract, not a capture.

`handoff.json` records source, geometry and authoring revisions, atlas size, bit depth, UV profile, gutter, materials, cameras and measured texels per asset unit (p10, p50, p90). `declared_density_pixels_per_metre` is the contract's declared density, or null when none is declared; Effigy never assumes a density. `physical_scale` is `declared` only when the contract records measured metres per asset unit, and only then does `texels_per_metre_p50` appear.

**Mark seam-heal zone** writes a UV permission mask around joins between different writer labels inside one UV shell, widened by max(3, round(atlas size x 0.012)) pixels and kept inside that shell. It also writes per-guide overlays and `manifest.json` with `zone_source`, `mode` and `pixels`. When the history has no writer ownership, the shell-border mode (`heal_mask:shells`, the UI checkbox) marks texels along UV shell borders instead; its manifest reports `fallback: true`. Neither mode changes pixels.

Paint the returned copy in Blender, Pull it as the donor and save the contract. **Reconstruct seam heal** then copies donor RGB only inside the saved heal zone through the same guard as masked reconstruction. Writer ownership now also counts reconstruction and publication permissions, so advisory seams on older sessions may differ; labels change, pixels do not.

## Review and publish

Review the mesh, not only the generated sheet. Each reconstruction also writes `comparison.png` (source above result at yaws 0, 90, 180 and 270) and the `source_render_comparison` metric; the workspace shows it beside `review.png`. Use source/result comparison at matched camera and scale, the 360 output, close seams and ownership/disagreement overlays. Look for feature-size drift, mixed detail levels, lighting painted into base colour, ghost contours and broken mortar. Adequate sampling cannot sharpen an already soft source by itself.

The workspace shows original/prepared source, preferred version and owner-accepted version separately. A technically retained finishing patch remains a draft. An operator can reject appearance even when preservation and regression measurements pass. The rejected hut312 and reconstruction313 are regression examples, not default sources or styles; see the prior [quality result](plans/painting-completion/11-material-base-quality.md#result).

**Apply texture** or **Publish reviewed draft by reference** creates metadata pointing to the reviewed outputs. It does not duplicate that GLB or imply artistic acceptance. Historical candidate dependencies remain protected. The plan performs no automatic cleanup.

Repeating publication of the same reviewed draft returns the existing version. No new job or version is allocated. The UI links to that publication and disables the repeated action; a different reviewed draft remains publishable.

## Recover

- Invalid UVs or insufficient clearance: return to preparation on a copy. Inspect the new revision before painting.
- Undersampled detail: revise the captured region or choose explicit study mode. Do not spend generation attempts on a technical admission failure.
- Stale source, material contract or mask: reopen the saved session and capture/refresh its current inputs. Old candidates remain inspectable; there is no silent rebase.
- Cancelled finishing: reopen the saved pass and select **Resume automatic finishing**. Completed patches and generation receipts are reused. An interrupted inference without a completed receipt consumes another reservation when retried. A surviving image with no completion record is retained and reported explicitly; it is not silently regenerated.
- Model or memory unavailable: retain the pass and report the named limitation. Do not substitute models, reduce camera coverage or stop another application's GPU work implicitly.
- Storage unavailable: restore the configured NAS access. Publication fails in place; do not redirect asset output to an accidental local folder.
- Saved versus unsaved Blender edits: Pull the intended isolated scene after saving it. Scene identity guards reject another application's scene.
- Numeric retention with worse art: reject the draft and keep its source. Finishing is finite; stop that region when the allowance is exhausted and continue independent work.
- `missing_heal_mask`: Reconstruct seam heal ran before a seam-heal zone was saved. Mark the zone first; the source is unchanged.
- No writer ownership or no writer join: Mark seam-heal zone reports it and writes nothing. Use the shell-border mode (`heal_mask:shells`) explicitly; it is a reported fallback, never automatic.

Repair timing reports its scope and whether the engine was fresh, reused or replaying a receipt. A fast warm patch is not whole-asset throughput. A batch with every attempt rejected keeps its source pixels; do not publish it as an improvement.

## API entry points

UI actions use the same owner in `server/paint_sessions.py`. URLs below are relative to the trial:

| Action | Endpoint |
|---|---|
| List/create sessions | `GET/POST /api/assets/{asset}/paint-sessions` |
| Read session | `GET /api/assets/{asset}/paint-sessions/{session}` |
| Save profile | `PUT .../{session}/authoring` with current `revision` and `profile` |
| Capture/select/generate/preview/apply/finish | `POST .../{session}/actions` with current `revision` and typed action |
| Reconstruct/publish donor result | `POST .../{session}/authoring/actions` with current `revision` and `action` |
| Export hand-paint bundle | `POST .../{session}/authoring/actions` with `action: handoff` |
| Mark seam-heal zone | `POST .../{session}/authoring/actions` with `action: heal_mask` or `heal_mask:shells` |
| Reconstruct inside the heal zone | `POST .../{session}/authoring/actions` with `action: reconstruct_heal` |
| Record review | `POST .../{session}/authoring/reviews` with session/profile revisions and explicit reviewer/verdict/note |
| UV inspection/preparation | `POST /api/assets/{asset}/steps/uv_context`, parent version and `params` containing `op: prepare`, operation, gutter and explicit scale |
| Job/cancellation | `GET /api/jobs/{id}`, `POST /api/jobs/{id}/cancel` |

Use the typed request definitions in `server/paint_routes.py`, `server/authoring_contracts.py` and `ui/src/multi-view-api.ts`. Do not edit persisted session JSON to bypass revision, job or budget checks. API success is not a substitute for the outstanding real-browser operator acceptance.

For repeated Apply or Publish, a confirmed existing result returns `outcome: already_converged`, `job_id: null`, its `version` and the current `session`. Callers should open that version instead of polling a nonexistent job. Missing output files still fail explicitly.
