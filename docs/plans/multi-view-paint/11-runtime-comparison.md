# Compare four methods and prove preservation and lifecycle

Spoke: S11
Outcome: Compare four methods and prove preservation and lifecycle
Depends-on: S10
Decisions: D7, D8, D9, D10, D11, D12
Constraints: C1, C2, C3, C4, C5, C6
Skills: python:python-core, planning:planning-core
Read-set: CODE.md, docs/plans/multi-view-paint/INDEX.md
Write-set: docs/plans/multi-view-paint/11-runtime-comparison.md, scratch/lanes/fibo2
State: done

## Context

Owner approved the full-view revision on 2026-10-21. Prior paired-sheet anchors failed stone scale and mortar alignment; preserve their RESULT sections and rejected assets. Activate only trial 8380. Expected turns: 20; preserve usage history and standing circuit breakers. No per-unit handoff stops.

## Evidence

Later closure (2026-10-21): painting-completion/S04 added page-owned resource/CSP observation and exposed the actual connected EventSource origin. During live capture, repair generation and description operations, the UI reported258 resource entries from http://127.0.0.1:8380 only, zero external/blocked page requests and zero server CSP violations. This closes the historical per-page attribution gap for the observed operations without attributing unrelated desktop-host sockets or claiming OS containment. The original comparison RESULT below remains a historical record.

- server/paint_sessions.py:26 owns session creation; steps/_paint_set.py:25 owns surface projection.
- Session owner: server/paint_sessions.py; fixed captures and protected bake: steps/_paint_set.py.
- Prior S01-S05 RESULT sections distinguish implementation from incomplete visual and lifecycle acceptance.
- Source 167_upload and foundation selection 173_paint_set retain 409 triangles and the existing 1024 RGBA16 atlas.
- The earlier coverage calculation found fifteen cameras covering 92238 reachable texels; actual 512-resolution coverage must be recalculated.
- SyncMVD source: https://github.com/LIU-Yuxin/SyncMVD . MOSS v2 Euler recipe: https://huggingface.co/akhaliq/MOSS-Image-SFT-4-steps .

### Runtime comparison

The following comparison completed on 2026-10-21. Every painting candidate uses source167_upload, mask186_paint_set (derived from173), seed24031 and512-square camera panels. Each native method receives one2560-square sheet with21 panels; SyncMVD processes all25 eligible cameras. Candidate counts exclude admission refusals, the corrected MOSS worker failure and cancelled SyncMVD work.

| Method | Baseline candidate / bake | Correction1 candidate / bake | Correction2 candidate / bake | Sampling seconds | Peak allocated GiB | Verdict |
|---|---|---|---|---|---:|---|
| FIBO | 193 /195 | 207 /209 | 221 /223 | 91.77 /92.53 /107.10 | 13.416 | Replacement conditioning improves coherence; stones remain too large |
| Genesis | 196 /198 | 210 /213 | 224 /227 | 113.59 /114.87 /100.41 | 15.519 | Coarse front and fine rear persist |
| MOSS Turbo | 200 /202 | 214 /216 | 228 /230 | 47.25 /43.71 /43.02 | 13.416 | Coarse front and fine rear persist |
| SyncMVD | 204 /206 | 217 /219 | 231 /234 | 104.24 /111.03 /123.21 | 3.194 | Blurred foundation in all three |

Candidate numbers refer to paint_group versions; bake numbers refer to paint_set versions under rim_elm_hut_fibo_trial. Sampling timing excludes loading and bake time. Native load times are retained where measured in each candidate's metrics. Genesis reports256 NVFP4 layers with full_precision_mm. MOSS uses BF16 model computation, the borrowed encoder and all756 Turbo v2 LoRA keys; it does not establish FP4 acceleration.

Corrections were diagnosed from baked circumference reviews. FIBO first replaced selected detail using blank-region conditioning, then used explicit stone-to-wall-brick size wording. Genesis/MOSS increased denoise0.35->0.55->0.75; the last correction also specified miniature stones. SyncMVD used the same strengths and more explicit fine-masonry wording. No camera, source, selection, atlas or seed changed. No further inference is authorized by this twelve-candidate budget.

Runtime receipts remain in ordinary application metadata. Representative jobs: FIBO49158919be05; Genesis183661ae7f4a; MOSS e72b807687de; Sync resume1a40e56890b9. Failed MOSS70c3ff16fe56 reported inference-tensor version handling; no_grad in the Effigy worker resolved it. Sync5397a3fb80a3 was cancelled through the UI during step7; the replacement restarted from its recorded seed. Completed candidates survived idle restarts.

UI acceptance exercised full-size linked comparison, before/after, selecting a complete candidate, excluding Sync204 and its409 excluded_candidate refusal, regeneration, and Apply226 referencing223 without a GLB copy. The applied version contains metadata only and reopened in the viewer. It is labelled a review copy, not accepted artwork. In the separate roof/chimney/eave session, removal233 reduced selection5944->3722; addition235 restored5944 with zero mask-pixel differences from191. Coverage191/192 reports5937 reachable and7 unseen texels. This diagnostic is explicitly labelled separately from the foundation.

Negative application operations:37f0206ceca3 rejects the original multi-primitive retail mesh;1449e10efc45 rejects a temporary tiled-UV import220. Only the separate input copy's UVs were changed; source167 remains immutable. An exclusive read lock on the diagnostic session file caused503 storage_unavailable during PATCH; releasing the lock restored access with revision2 unchanged and no redirected output. Incompatible source/selection returned409. Stale revision, missing-model and insufficient-memory refusals were also observed. No code-test suite or hash sweep was created or run.

All twelve bake metrics confirm409 triangles, identical geometry/UV accessors and other maps,1024RGBA16, zero alpha/protected changes and132 unseen selected texels preserved. CPU projection uses at most two workers. Primary8370 stayed PID49908. Model workers had no established TCP connections at observed sampling points; trial backend connections were loopback. Shared browser-host PID49600 connects both to Effigy and external ChatGPT/browser services; per-tab attribution is unavailable, so browser-specific offline acceptance is held. Observation is not OS network containment.

## Steps

Use source 167_upload and mask 173_paint_set. Verify registration with a normal diagnostic projection. Generate one MOSS reference and a whole-set baseline per method, only above 28 GiB free VRAM. Fix technical failures before judging art. Allow two diagnosed corrections per method, at most twelve painting candidates, with fixed source, mask, cameras, resolution and baseline seed. Compare baked circumference, corners, risers, small stones, mortar, material identity and painted style; inspect protected treads, walls and roof. Confirm 409 triangles, identical geometry/UVs, 1024 RGBA16, exact alpha, other maps and zero unauthorized pixels. Exercise roof/chimney/eave coverage, UI cancellation, idle restart, resume, stale rejection and alias Apply. Exercise missing-model, VRAM, UV and storage errors without moving shared models or disconnecting NAS. Record CUDA, peak memory, timing and connections in ordinary job metadata and RESULT.

## Files to touch

- docs/plans/multi-view-paint/11-runtime-comparison.md
- scratch/lanes/fibo2

## Verification

1. Run scoped static commands after relevant source changes; expected zero findings. Record runtime acceptance separately below.
Run scoped Ruff after Python changes, the offline trial UI build after UI changes, and AEP plan validation after plan changes. Do not write or run code tests or hash sweeps. Use ordinary application jobs and baked renders for runtime acceptance. Installation and static success do not establish art quality. Preserve completed work across interruption.

## Risks

- Whole sheets may alter framing, stone scale or style despite shared context; inspect baked candidates.
- SyncMVD is a new masked adaptation requiring qualification, not a proven drop-in renderer replacement.
- GPU capacity, local compatibility or NAS failures may block runtime work; report exact errors and preserve completed candidates.
- Rejected art is a valid comparison result, not production qualification. No acceptable winner is permitted as a comparison conclusion; technical blockers remain incomplete.
- Owner visual acceptance and primary promotion remain separate. Network observation does not prove OS containment.

## Historical RESULT before page-observation closure

Completed the twelve-candidate comparison: three each for FIBO, Genesis, MOSS and SyncMVD. No acceptable winner; FIBO223 is the closest coherent wrap but stone scale remains too coarse. Genesis/MOSS retain front/rear scale mismatches; SyncMVD remains blurred. All12 bakes preserve409 triangles, UVs,1024RGBA16, other maps, exact alpha and protected texels;132 unreachable selected texels stay unchanged. UI comparison, exclusion, cancellation, idle restart, resume, selection edits and alias Apply226 passed. Failure samples reject unsupported geometry/UVs, stale state, mismatched selection and unavailable storage. PrimaryPID49908 unchanged. Workers showed no established TCP connections; backend connections were loopback. Browser process49600 also serves ChatGPT and had external connections that cannot be attributed per tab. Browser-specific offline acceptance remains incomplete; no OS-containment claim. Candidate budget exhausted; no further inference or primary promotion.

## RESULT

Completed12 candidates: three each for FIBO, Genesis, MOSS and SyncMVD. No production-qualified art winner; rejected and owner-retained candidates remain recorded. All bakes preserve409 triangles, UVs,1024 RGBA16, alpha, other maps and protected pixels. UI comparison, exclusion, cancellation, restart/resume, selection edits, failure paths and alias Apply226 passed. The former browser-attribution gap is closed for observed page operations by painting-completion/S04:258 localhost resource entries, connected localhost progress stream and zero external/blocked requests or CSP violations. This does not attribute unrelated desktop-host sockets or establish OS containment. Primary8370 remains unchanged. The12-candidate comparison budget remains closed; no primary promotion.
