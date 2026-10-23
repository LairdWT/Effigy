# Local workstation setup

Run `run.bat` from this checkout. It starts the installed backend at
`http://127.0.0.1:8370` and opens the UI. An occupied port is an error. Keep its
terminal open; Ctrl+C shuts down this instance and its owned workers.

Normal startup does not synchronize dependencies, build the UI, or download
models. Model installation and repair, account checks, and port changes are
disabled in the running application. Hugging Face and Transformers use offline
resolution; Python workers reject outbound internet sockets. This is an
application boundary, not Windows firewall containment.
The page also uses a same-origin Content Security Policy. Blocked page resources
increment the local `/api/runtime/policy` counter and are logged without their contents.

## Provisioning

Close Effigy before updating its installed dependencies. Run `provision.bat`
explicitly when public internet downloads are wanted. It uses the frozen
upstream lock, installs each isolated environment, builds the UI, installs
gltfpack, and downloads all supported model groups. To resume model downloads
without reinstalling environments, run `provision.bat --models-only`.
An optional `--groups fast kimodo` limits model groups.

Provisioning uses the existing Hugging Face token store if present. No token is
stored in this repository. Exact published runtime objects for Llama come from
the pinned public mirror recorded in `tools/model_sources.json`; its owned
snapshot retains source provenance. Existing DINOv3 can be borrowed only when
recorded metadata matches every required published object and byte size.

## Storage and tools

Ignored `settings.json` selects the NAS model root and asset library, and points
to the existing 3DGen `tools.config.json` for Blender and uv. Ignored
`model-bindings.local.json` identifies read-only shared checkpoints. Effigy may
read borrowed files; removal, repair, and relocation are refused. Generated
TRELLIS pipeline configuration goes into local scratch rather than beside weights.
Each worker processes its version in local scratch and publishes completed files
to the persistent NAS version. Inputs and model weights remain at their declared
locations. Motion-name lookups continue to use the persistent asset history.

On this workstation:

- Source, seven Python environments, caches, and scratch: `D:/AI/Effigy`.
- Newly downloaded models and HF cache: `N:/generated/3DGen-models/Effigy`.
- Persistent assets and their version history: `N:/generated/Effigy`.
- Blender comes from the configured installation, version 5.2.0. Upstream used
  5.2.2; individual operations require runtime qualification.

Open in Blender uses a separate offline scene and profile on loopback port 8371.
It loads the configured local-only add-on read-only. Effigy never falls back to
your existing Blender listener when this explicit binding is present. Pull
returns that session's tagged asset objects to a new library version.

Backend/ML, SkinTokens, Kimodo, GeoSAM2, GEM-X, and MoGe remain separate. GEM-X
keeps its Torch 2.10 environment; the other upstream groups retain their frozen
versions. Other applications' pins and processes are unaffected.

## Verification and acceptance

Static checks and runtime sample results live in the existing AEP plan spokes
under `docs/plans/local-gpu`. Baseline source checks are project Ruff and the UI build; broader AEP analyzer findings remain advisory by owner decision. Installation alone does not establish GPU execution
or output quality. Ordinary sample assets retain their job records and output
versions in the application library. No code tests or runtime model hashes are
part of startup, verification, or acceptance.

MCP implementation remains available in source; no hosted assistant is registered.
Git changes remain uncommitted until the owner explicitly authorizes publication.

## Observed baseline limits

All supported feature families have ordinary sample outputs in the library.
SkinTokens ran but its direct sample failed stretch QA. Automatic skinning compared
both engines and selected Blender weights with zero QA failures; keep Auto unless
you intend to review another result. Generated meshes still need visual cleanup.
Cold NAS model loads can take several minutes; progress and CUDA use are visible
in Activity. No other GPU workload was stopped for acceptance.

The two authorized storage audits retained a preexisting C: Hugging Face cache
reserve failure. Selected destinations had 246.62 GiB free on D: and 3.88 TiB on NAS.
Baseline upgrade research is in `docs/plans/local-gpu/06-upgrade-options.md`.

## Optional local models in the 3D workflow

New asset -> A 3D model -> From a description includes a Reference model selector.
Z-Image remains the default. Existing Krea2 Anime Genesis, Genesis NVFP4 and Turbo
FP8 checkpoints can generate references for the same preparation and mesh stages.
Choose Character for a full-body A-pose, separated limbs and a plain background.
These image models supply the reference; TRELLIS generates the mesh.

On a reference version, Edit this reference uses the installed Qwen Image Edit
2511 checkpoint. On a static UV mesh, Edit the reference and retexture this mesh
runs Qwen, removes the edited image's background, then transfers new textures
onto the existing geometry and UVs. Ask for a specific appearance change while
preserving pose, framing and design. Review the resulting mesh before rigging.
Continue with skeleton fitting, Auto skinning, animation and export as usual.

The anime sample's retexture lost facial detail. For Faithful meshes, Tools ->
Face from image restores aligned face detail after retexturing. It follows the
original geometry camera and uses the edited reference. Turn off Match existing
texture lighting when you want the reference's original colours. Inspect the
result; the silhouette-alignment guard can refuse a mismatched reference.

Setup reports local availability. These optional workers reuse the native engine
and interpreter resolved from tools.config.json in isolated processes; no shared
engine, environment or model files are changed. Normal offline and GPU admission
controls still apply. Missing components fail locally without downloads.

Genesis stores NVFP4 weights, but this checkpoint's metadata requests higher
precision matrix multiplication. Compressed storage does not establish native
FP4 arithmetic acceleration. Workflow observations and limitations belong to
`docs/plans/local-upgrades/02-anime-workflow.md`.

The completed workflow sample is `anime_workflow_local_checkpoint`: original blue
texture at 008_bake, crimson front-projected texture at 014_project, both walk and
Kimodo wave clips at 019_anim, three-view sprites at 020_sprites, and animated GLB
at 021_export. `anime_workflow_reopened_glb` reimports that export and preserves its
clips and textures. Both skin engines passed hard QA on this sample; Auto selected
Blender. Ears/neck, fingers and peripheral texture artifacts still need cleanup.
Keep Qwen retexturing as a reviewed variant; the sample does not establish finished
production quality or an unattended texture upgrade.

## Captured-view surface painting

Open a static textured mesh, including an imported Blender mesh. **Paint textures:
image-to-image** appears above the existing actions.

1. Orbit and frame the target, then choose **Capture view for painting**. This saves
   a fixed unlit 1024 view, triangle map and a reference to the existing mesh.
   Captures do not copy the GLB.
2. Save materials/palette, desired style and preservation intent with **Use for
   this asset**. New views inherit these fields and model settings; each view has
   separate instructions, pixel selection and seed. **Use previous recipe** loads
   prior text for review. The exact composed prompt is visible before submission.
3. Select the whole visible surface, individual triangles, or brush/lasso regions.
   Triangle add/remove works in the fixed image or 3D viewer. Brush strokes stay
   inside the selected triangle boundary. Zoom and scroll to pan; undo/redo and
   named triangle selections support repeated edits. Triangle IDs belong to the
   geometry/UV revision; reimporting or remeshing invalidates them.
4. New surface painting uses **Krea2 Genesis (NVFP4 weights)**. Its image-to-image
   path encodes the capture and uses descriptive appearance wording. Start at
   denoise 0.35; the 0.60 hut sample moved openings and chimney geometry in the
   candidate image. This checkpoint requests full-precision matrix multiplication
   for its NVFP4 weights, so native FP4 acceleration is not claimed. Qwen remains
   available for instruction edits, and historical FLUX recipes remain readable.
   Denoise, steps and seed are separate
   controls. The current FLUX recipe uses Ghibli 0.7. The previously configured
   Arcane file matched zero FLUX weights and has been removed from this recipe
   under the owner's direction. LoRA loading now rejects unmatched weights
   before generation and records applied coverage. **Save
   painting draft** retains the prompt, settings and mask in this browser for
   the captured version, including while GPU work is unavailable.
5. Choose **Incremental: generate only inside the mask**, then press
   **1. Generate projection preview**. Krea/FLUX denoise only the selected region
   while the complete fixed capture provides context. Review the preview beside
   the mesh, then press **2. Project onto mesh**. You may narrow its mask before
   projecting; expanding outside the generated area requires another preview.
   Re-running generation starts from the same capture for a comparable sibling.
6. Orbit the resulting mesh and capture another view for cumulative work.
   **Tools -> Texture detail** also works on static imports and surface-paint
   versions; **Redraw this view** is the existing Z-Image Tile refinement path.

**Suggest description from this view** runs the selected Q3.5-9B OpusGLM Q8 GGUF
and matching Q8 vision projector through the existing llama.cpp runtime. Its
loopback server belongs to that job and exits afterward. Nothing launches Ollama.
Observed text stays separate from desired appearance: edit it, append it to
materials, replace explicitly selected material text, or discard it. It can confuse
thatch and shingles; the owner brief remains authoritative.

History groups each capture and its candidates/descriptions in a painting session.
Stars explicitly retain versions. Deletion previews list exact versions and bytes,
and refuse retained image/source dependencies, starred versions or active jobs.
Moving to Recently deleted is recoverable and does not reclaim disk space.
New reference outputs alias a single PNG. New painted GLBs remove obsolete image
payloads while retaining referenced material maps and exact geometry/UV data;
unsupported GLB extension references fail clearly. Existing files are not migrated.

Surface painting always keeps the existing atlas dimensions and 8-bit or 16-bit
channel precision. It replaces only
the base-colour image in the GLB; geometry/UV accessors and other material maps
remain intact. CPU capture and projection do not reserve GPU memory. Model
generation retains the existing offline worker and GPU admission rules.

Incremental mode uses a separate, inward-feathered differential sampler mask and
an independent pixel-write boundary. The full source image is encoded without
cropping, protected latents are restored during sampling, and the final preview
preserves unselected pixels exactly. The generation edge blend cannot expand the
selection. Qwen instruction editing and old recipes retain explicit **Restyle the
full view, then project the selection** behavior; they do not claim masked
diffusion. Changing the method does not retroactively change an existing preview.

Projection uses
the saved camera and exact source-triangle visibility, rejects grazing samples,
preserves alpha and refreshes only adjacent empty atlas gutters. The adjustable
edge blend transitions inward, without expanding the selected region. A candidate from
another capture/source version is rejected. UV overlap is checked at texel
centres; subtexel overlap is not a complete geometric UV audit. Existing Texture
detail refinement still writes 8-bit output, identified in its panel.

Current scope: one static triangle primitive, a unique UV0 atlas, embedded images,
no texture transform and a baked base-colour factor. Multiple materials, skins,
animation or tiled UVs require a separate baked static copy. Existing unrelated
Blender and GPU work is never stopped to make a generation fit.

The broader suite integration map is maintained in
[S06](plans/local-upgrades/06-interactive-surface-paint.md): prompt/source roles,
Blender preparation, explicit brush painting, character shading/rigging, motion,
review and delivery have separate capabilities and acceptance states.
