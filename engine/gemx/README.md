# engine/gemx

NVIDIA GEM-X (Apache-2.0 code, `LICENSE` and `ATTRIBUTIONS.md` kept) and Meta's SAM 3D Body package (SAM
License, `LICENSE.sam-3d-body`) for the `mocap` step (IMPLEMENTATION M34, research 12): a video of a person
becomes a motion on the SOMA skeleton, then a clip for our rig through the Kimodo path (M26).

- `gem/`, `configs/`: GEM-X at `3299255` (github.com/NVlabs/GEM-X), unmodified. Not the demo scripts:
  `steps/mocap.py` drives the pipeline itself (its person detector, the DDIM switch, no renders).
- `sam_3d_body/`: SAM 3D Body at `b5c765a` (github.com/facebookresearch/sam-3d-body, GEM-X's submodule),
  unmodified; GEM-X imports it for its image features (the Best and Quick modes).
- Runs in `.venv-gemx` (dependency group `gemx`: torch 2.10 cu128, SOMA `py-soma-x` at `e0f8ff0`);
  `steps/mocap.py` puts this folder on `sys.path` and runs with `models/GEM-X` as its working folder,
  because GEM-X finds its files by relative `inputs/...` paths. `TORCH_HOME` and Warp's kernel cache point
  there too, so nothing lands in the user's profile.
- Weights: model group `mocap` (`tools/download_models.py`): `nvidia/GEM-X` at `5ccf5ca` (GEM-X's SOMA
  model, ViTPose, SAM 3D Body, MHR, the scale files; never `gem_smpl.ckpt`), SOMA's assets from its Git LFS
  at `e0f8ff0`, DINOv3's code at `6876159` (ViTPose's backbone class), YOLOX-L from `yzd-v/DWPose`.
- What differs from upstream's demo, and why: `PATCHES.md`.
