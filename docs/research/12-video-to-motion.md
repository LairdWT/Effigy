# Research 12: video to motion (2026-10-08)

> PLAN Phase 3 lists "optional video-to-motion (SAM 3D Body): licence check first". The owner asked to explore
> it (2026-10-08). The question: which monocular video → 3D human motion model can ship in a commercial game sold
> in the EU, on a 16 GB laptop on Windows, and land on our rig the way Kimodo's motions do (M26: a BVH →
> `clip.glb` → `blender_ops/retarget.py` → our 52-joint Mixamo skeleton).
> Sources: model cards, repos and LICENSE files fetched on 2026-10-08 (list at the end). "Unverified" marks what
> no fetched page states.

## The candidates

| Candidate | Code | Weights | Training data / SMPL exposure | Output | Fit for us |
|---|---|---|---|---|---|
| **NVIDIA GEM-X** (NVlabs/GEM-X, `nvidia/GEM-X`) | Apache-2.0 | NVIDIA Open Model License (allowed in PLAN §6, as Kimodo) | "trained exclusively on internally generated synthetic video data": Bones RigPlay-1 (350k mocap sequences), Bones Audio2Gesture, RenderPeople, internal characters, HDRI Haven; no SMPL, AMASS or BEDLAM named; the repo: "commercially usable, trained on NVIDIA-owned data only" | **SOMA, 77 joints incl. hands**, the skeleton Kimodo already writes; world-space root in metres from an estimated camera path | Best. Our SOMA → Mixamo map (M26) should take it as it is. Linux, PyTorch 2.10, CUDA 12.1+ documented; Windows untested; Detectron2 and PyTorch3D in the install. **Blocked by the wording of PLAN §6** (below) |
| **SAM 3D Body** (+ SAM-Body4D for video) | SAM License (+ MIT for SAM-Body4D) | SAM License, gated on HF | annotation pipeline (keypoints, optimisation, multi-view); datasets not named; SMPL exposure unverified | MHR mesh and rig (Apache-2.0), per frame, camera-relative; no BVH, no world root | Licence-clean (no EU block; no military/ITAR use). A heavy stack (PyTorch3D, Detectron2, SAM 3, torch 2.7.1 pins), an MHR → Mixamo map and a world root to build. Second choice |
| **MoCapAnything V2** | MIT (a "clean reimplementation") | MIT (`kehong/MoCapAnythingV2-weights`, 464 MB) | Truebones Zoo animals + Objaverse; no human data, no human benchmark | BVH on any rig from a reference pose; camera-frame, root-relative | Not as shipped: fetches RMBG-1.4 at run time (commercial use needs a BRIA agreement, PLAN §6 bans RMBG-2.0 for the same reason); animals, not people. Interesting later for creatures |
| NVIDIA GEM / GENMO | NVIDIA OneWay Noncommercial | – | SMPL | SMPL | Out (the "NVIDIA GEM" of PLAN §6) |
| GVHMR, WHAM, TRAM, PromptHMR, CameraHMR, 4D-Humans | – | – | SMPL family | SMPL | Out by PLAN §6 (their own licences not rechecked) |

## The policy question

PLAN §6 "Never used" names "NVIDIA GEM". Research 05 gave the reason: GVHMR, WHAM, 4DHumans and GEM are "all
non-commercial or SMPL-bound". That is GEM/GENMO (2025: SMPL, NVIDIA OneWay Noncommercial). **GEM-X** is a later,
separate release with Apache code, NVIDIA Open Model License weights and synthetic training data on SOMA, so
neither reason applies. Allowing it means narrowing the §6 entry to "NVIDIA GEM / GENMO (SMPL, noncommercial)":
an owner decision.

## Open before or in a spike

- GEM-X on Windows with our drivers: PyTorch 2.10 in its own venv (`.venv-gemx`, like `.venv-kimodo`), Detectron2
  and PyTorch3D builds; WSL2 only as a last resort (the app is Windows-native).
- Which parts run at inference: the bundled SOMA 2D keypoint detector (its licence and data unverified), the
  SAM 3D Body tracker (optional per the card: full-frame boxes and a static camera otherwise; gated download if
  used), the focal-length estimator.
- Peak VRAM and seconds per second of video on the 5080 (no figure published); BVH export or our own writer from
  the SOMA joint rotations (Kimodo's path).
- Quality on real phone footage: GEM-X reports 115.2 mm W-MPJPE on its own synthetic test set only. Foot sliding,
  jitter, depth along the camera axis, root drift, fingers.

## Spike on the laptop (2026-10-08): GEM-X runs on Windows and the motion lands on the viking

No feature code and no library version: a scratch folder outside the repo, GEM-X at `3299255`, the owner's test
clip (a stock dance clip, 14.2 s, 30 fps, portrait 2160×3840, one person, full body, a still camera, a phone-app
overlay drawn over it), scaled to 720×1280 because the demo reads the whole video into RAM (4K: ~10 GB).

**Install** (Windows 11, RTX 5080 Laptop, driver 617.42): a uv venv, Python 3.12, **torch 2.10.0+cu128** (sm_120 in
its arch list), `pip install -e` SOMA (Git LFS assets, 827 MB) and GEM-X, SAM 3D Body's few runtime packages;
**no Detectron2, no PyTorch3D** (only SAM 3D Body's own detector and the demo's preview renderer import them, and
neither runs). Pitfalls met: the `sam-3d-body` submodule was left empty by the first clone; `inputs/soma_assets`
must point at the submodule's assets (else SOMA fetches another asset version from HF without `joint_parent_ids`);
`soma-retargeter`'s submodule URL is SSH (HTTPS works) and its configs are in LFS; ONNX Runtime's CUDA provider did
not load, so YOLOX ran on the CPU. Downloads at run time: `gem_soma.ckpt` 0.54 GB, `vitpose.pth` 3.39 GB (its
backbone is DINOv3: code fetched from GitHub by torch.hub), SAM 3D Body 2.11 GB and MHR 0.70 GB (both from
`nvidia/GEM-X`, under SAM License / Apache-2.0), YOLOX "humanart" ONNX from openmmlab (Apache-2.0 code; the
Human-Art training data's terms unverified). The SMPL variant (`gem_smpl.ckpt`) was not downloaded.

**Time and memory** (the 426 frames; the first runs included the downloads and two fixes, so per stage): person
detection and tracking ~80 s on the CPU, ViTPose 30 s, SAM 3D Body features ~1 min, GEM-X plus its preview
renders 120 s. Peak torch VRAM 3.89 GB (keypoints), 4.31 GB (SAM 3D Body), 1.30 GB (GEM-X). Estimate for a clean
run of this clip: 4–5 min, less with YOLOX on the GPU.

**Onto our rig**: GEM-X's own `export_soma_bvh` writes each offset in SOMA's joint-orient frames, so the BVH's rest
skeleton lies along X and our retarget (which matches rest poses) tumbled the viking. A small writer (the spike's
`soma_bvh_upright.py`) puts the bind pose's world offsets in the file and each joint's `body_pose` rotation as its
channel rotation (the same posed positions: checked in Blender), stands the rest skeleton on the floor, grounds
the motion (the 5th percentile of the lowest foot joint) and turns the first frame to face +Z from the origin, as
Kimodo's clips start (GEM-X's world had the dancer facing −Z, 175.7°). Then `blender_ops/bvh_clip` and
`blender_ops/retarget` unchanged, onto the viking's `529_rig_skin`: 340 frames at 24 fps, no SOMA bone missing,
height scale 0.526. `12_gemx_viking.jpg`: frames 0, 57, 113, 170, 227, 284 (the wave, the squat with a hand up,
the hop with the knees pulled up, the arm overhead, the lean, the hand on the hip); side by side with the clip
every frame matches the dancer, the same arm raised (both face the camera; checked by hand heights, not by eye
alone: the raised hand is the right one in both at 2.37 s and 7.1 s).

| on the viking | GEM-X dance | Kimodo "angrily hide behind a wall" | pack Walk (in place) |
|---|---|---|---|
| foot down frames (of all) | 29–33 of 341 | 114–117 of 121 | 24–26 of 41 |
| slide while down, median / p95 | 0.13–0.17 / 0.24–0.47 m/s | 0.01 / 0.21–0.64 m/s | 0.34–0.41 (treadmill) |
| hips drift / range | 0.34 / 0.43 m | 0.40 / 0.40 m | 0.00 / 0.03 m |
| hand acceleration, median / p99 | 4.2–6.9 / 20–22 m/s² | 0.4 / 7 m/s² | 1.0 / 3 m/s² |

A dance is far busier than standing, so some of the slide and acceleration is the motion itself (pivots, fast
arms); some is monocular noise. A foot-lock and a light smoothing pass are the expected cleanup.

**Three modes, the same clip** (owner 2026-10-08: offer options): GEM-X's regression pass (the default, "Quick"),
its 50-step DDIM sampling ("Best"), and DDIM without SAM 3D Body's image features, 2D keypoints only ("Keypoints
only", no SAM 3D Body download or licence in the chain). The demo's `--ddim` switch is broken upstream: it sets
`regression_only` on `model.pipeline`, while the sampler checks the flag on the diffusion module, so a "DDIM" run
is bit-identical to regression (measured: max difference 0.0); patched in the spike's copy by setting it on every
module that has it. Measured (the 3D stage alone, model load and preview renders included, ~60 s each; VRAM
1.29 GB; the 2D fit is the in-camera joints projected onto the 2D keypoints of confidence > 0.5, 720×1280 frame,
the dancer ~800 px tall):

| mode | 2D fit median / p90 | joint jitter (mean second difference) | root jitter | vs Quick |
|---|---|---|---|---|
| Quick | 28.9 / 65.9 px | 0.0069 rad | 6.1 mm | – |
| Best | 30.0 / 71.4 px | 0.0061 rad | 5.1 mm | joints up to 0.62 rad, root up to 0.23 m apart |
| Keypoints only | 31.0 / 88.0 px | 0.0057 rad | 2.8 mm | joints up to 1.53 rad, root up to 0.57 m |

On the viking (a four-way video, kept outside the repo) the three dance the same moves; Best is a touch calmer
than Quick, Keypoints only wanders sideways across the floor (its root path) and fits the video least. Read: Quick
or Best as the default with image features; Keypoints only as the "light" option when SAM 3D Body is not wanted.

**Verdict**: feasible on our stack with no CUDA builds; the motion reads right on our rig through the Kimodo path.
Open before a milestone: the owner's PLAN §6 decision on GEM-X; YOLOX on the GPU (ONNX Runtime CUDA provider) or
another detector; the licences of the bundled keypoint model's and the YOLOX humanart model's training data;
foot locking and smoothing; finger detail (two hand close-ups looked natural: an open hand, a raised hand with
spread fingers, no twisted wrist; not measured); a moving camera (this clip used `--static_cam`).

## Sources (fetched 2026-10-08)

- huggingface.co/nvidia/GEM-X: licences, synthetic training data, SOMA 77 joints, world-space root, Linux /
  PyTorch 2.10 / CUDA 12.1+, the SAM 3D Body tracker as optional input.
- github.com/NVlabs/GEM-X (README, `docs/INSTALL.md`, `ATTRIBUTIONS.md`): Apache-2.0, "commercially usable, trained
  on NVIDIA-owned data only", the bundled SOMA keypoint detector, Detectron2 / PyTorch3D / YOLOX / ByteTrack.
- github.com/NVlabs/GENMO: OneWay Noncommercial, SMPL.
- github.com/facebookresearch/sam-3d-body and its LICENSE; ai.meta.com (SAM 3D Body publication);
  github.com/facebookresearch/MHR (Apache-2.0); github.com/gaomingqi/sam-body4d (MIT, torch 2.7.1).
- huggingface.co/kehong/MoCapAnythingV2-weights; github.com/phongdaot/MocapAnything; arxiv.org/html/2604.28130;
  huggingface.co/briaai/RMBG-1.4 (commercial use needs a BRIA agreement).
