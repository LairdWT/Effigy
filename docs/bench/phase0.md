# Phase 0 bench (M11)

**Status: both measured (2026-10-04, `phase0_fast.csv`, `phase0_faithful.csv`); default to be confirmed by the owner.** RTX 5080 Laptop, driver
617.14, max power mode (an earlier OEM power cap at ~52 W roughly halved every GPU step), Blender open.

## Procedure (IMPLEMENTATION.md §5)

1. Laptop plugged in, max power profile, nothing else on the GPU; start the backend (`run.bat`).
2. Once, make the golden images (Z-Image-Turbo on our own prompts, `tests/fixtures/golden/prompts.yaml`),
   look at them, commit them:
   `uv run python -m tools.bench --make-golden --set tests/fixtures/golden`
3. Fast and Faithful over the same 10 images:
   `uv run python -m tools.bench --preset game-prop --weights fast --out docs/bench/phase0_fast.csv`
   `uv run python -m tools.bench --preset game-prop --weights faithful --out docs/bench/phase0_faithful.csv`
4. Paste each run's printed summary below, fill the A/B table, and write the pick into PLAN.md §3 row 1.

Chain `game-prop` (`server/presets.py` `CHAINS`): upload → prep → trellis2 (1024_cascade, 12 steps) →
clean → remesh 10k tris → uv → bake 2K → validate (budget 10k) + export (Godot GLB).
CSV: one row per image; `s_<step>` seconds, `vram_<step>` whole-GPU peak (nvidia-smi, 0.5 s sampling),
`torch_<step>` the step's own allocator peak where it reports one, then faces, non-manifold edges,
components, UV texel-density p10/p90 (relative to the median) and checklist fails.

## Acceptance

- [ ] ≥ 9/10 succeed (each preset)
- [ ] every step's peak VRAM ≤ 14.5 GB
- [ ] Fast vs Faithful A/B recorded, default picked in PLAN.md §3 row 1

## Results

| | Fast (commit c9d0e13) | Faithful (commit a23bf93) |
|---|---|---|
| succeeded | **10/10** (0 checklist fails) | **10/10** (0 checklist fails) |
| trellis2 median s (range) | 195 s (98–705) | **160 s (106–204)** |
| trellis2 torch peak / whole-GPU peak | 3.0–7.6 GB / 6.5–15.5 GB | 13.3 GB / 15.4 GB |
| whole chain median s | 258 s | **232 s** |
| faces after remesh | 9,531–9,927 (budget 10k) | similar (budget 10k) |
| non-manifold edges (median) | 14.5 | 7.5 |
| looks closer to the image (count of 10) | 2 (barrel, chair) | **7** (anvil, chest, crate, drone, mushrooms, potion, teapot); lantern a tie |

Side by side, golden image | Fast | Faithful, game-ready bakes from the same camera:
`phase0_ab_1.jpg` (anvil–crate), `phase0_ab_2.jpg` (drone–teapot).

- Faithful follows the input view and colours: Pixal3D is pixel-aligned. Fast's anvil, drone and teapot
  come out turned against the picture, its potion black instead of purple, its mushrooms too dark.
- **Faithful's bakes have white patches on 4/10** (anvil stump, barrel hoops, chair seat, mushroom moss):
  the shapes are right, so it's the bake from Pixal3D's volume. To fix before Faithful becomes the default.
- Faithful needs ~24 GB system RAM (Fast ~18.6 GB) on the 32 GB laptop: Claude Code's background shells
  were reaped twice; the owner's own terminal ran it fine.

Fast per step (median / max s): prep 21.9 / 24.4, trellis2 194.7 / 704.6, clean 10.8 / 14.1, remesh
4.0 / 6.8, uv 3.4 / 3.5, bake 23.0 / 32.3, validate 1.2, export (Godot) 2.3.

- **VRAM acceptance (≤ 14.5 GB per step) is missed on 3/10 images, and they're the slow ones.** The
  steps' own torch peak never exceeds 7.6 GB, but the whole GPU reached ~15.5 of 16 GB on crate,
  mushrooms and potion (allocator cache from models moving on and off the GPU, the desktop, Blender),
  and those took 356–705 s instead of 98–224 s: Windows spills to shared memory when the card is full.
  **Cause found (probe per stage on the crate):** sampling stays at ≤ 6.9 GB whole-GPU; mesh decoding
  (`decode_shape_slat`, 15.8M faces) made torch's caching allocator reserve **23.7 GB** for an 8.1 GB peak
  (fragmentation) and Windows spilled to shared memory (23 s for that stage). `garbage_collection_threshold`
  / `max_split_size_mb` didn't help; **`backend:cudaMallocAsync`** did: 9.0 GB reserved, 2 s, 10.3 GB
  whole-GPU. The server now sets it for every step process (`server/jobs.py` `_env`, before the child
  imports torch: torch picks the backend at import). Also fixed: switching engines in the resident worker
  freed nothing (faithful -> fast left 15.8 GB in use); the worker empties its cache after each job and
  is stopped after 5 idle minutes (RAM).
- The resident TRELLIS worker keeps its cache through the light steps (clean/remesh/uv show ~15 GB
  whole-GPU while using almost none themselves).
- This run's meshes predate the last hole fix (undecided faces spread from neighbours); timings and
  VRAM are unaffected, the bench anvil showed inward faces at its waist.

## Rerun after the fixes (Faithful, commit 92dd745, 2026-10-04 18:40)

`phase0_faithful.csv` now holds this run (owner's terminal, Blender open, max power, laptop raised).

| | before (a23bf93, 14:46) | after (92dd745) |
|---|---|---|
| succeeded / checklist fails | 10/10, 0 | 10/10, 0 |
| non-manifold edges | median 7.5 | **0 on all 10** |
| trellis2 median (max) | 160 s (204) | **132 s (165)** |
| whole chain median (max) | 232 s | **192 s (228)** |
| whole-GPU during clean/remesh/uv | ~15 GB (resident worker's cache) | **1.4 GB** |
| trellis2 torch peak / whole-GPU | 13.3 / 15.4 GB | 13.3 / 15.6 GB |

VRAM acceptance: every step's own peak is within 14.5 GB (generate 13.3 GB, the rest ≤ 3.3 GB whole-GPU).
During generate the whole-GPU reading is 15.6 GB; that includes the CUDA context, the cudaMallocAsync
pool and other programs on the card (desktop, browser, Blender open); generate times are steady
(106–165 s), so nothing spills any more. Strict "whole-GPU ≤ 14.5 GB with Blender open" is not met:
owner's call.
