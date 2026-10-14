# engine/geosam2

GeoSAM2 (VAST-AI-Research, CVPR 2026; Apache-2.0, `LICENSE` and `NOTICE` kept) for the `parts` step
(IMPLEMENTATION M31): a click on one of twelve rendered views becomes per-face part labels.

- `wheels/geosam2-0.1.0-py3-none-any.whl`: upstream `b5de23c` built with `GEOSAM2_BUILD_CUDA=0`
  (the CUDA extension only speeds up a post-process) from `pip wheel --no-deps --no-build-isolation .`
  after dropping `opencv-python` and `ninja` from its `pyproject.toml` dependencies (`wheel.patch`; our base brings
  OpenCV headless, a second cv2 would overwrite it; nothing compiles); it carries the `sam2` package
  (GeoSAM2's modified SAM 2, with the model config) and `utils`. Runs in `.venv-parts` (dependency
  group `parts`).
- `inference.py`, `single_view_point_prompt_infer.py`: upstream's scripts, unmodified; they are not part
  of the wheel, and `steps/parts.py` imports them from here.
- `mode_ext.py`: our torch twin of `utils/mode_ext.cpp` (PATCHES.md).
- The twelve views come from `blender_ops/parts_views.py` (upstream's render script needs Blender 4's
  compositor); the conventions it must match are in `docs/bench/m31.md`.
- Weights: `VAST-AI/GeoSAM2` `geosam2.pt` (616 MB, Apache-2.0), model group `parts`.
