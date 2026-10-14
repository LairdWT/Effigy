# GeoSAM2 patches

| what | where | why |
|---|---|---|
| `utils.mode_ext` replaced by `mode_ext.py` (torch) | registered in `sys.modules` by `steps/parts.py` before `utils.inference_utils` is imported | upstream compiles `utils/mode_ext.cpp` at import with ninja and a C++ compiler; the step processes have neither |
| no CUDA extension in the wheel | `wheels/geosam2-0.1.0-py3-none-any.whl`, `GEOSAM2_BUILD_CUDA=0` | optional; its absence only skips a mask post-process, with a warning upstream prints once |
| `opencv-python` and `ninja` dropped from the wheel's requirements | the wheel's metadata (`wheel.patch` on upstream's `pyproject.toml` before the build) | our base dependency is `opencv-python-headless` (a second cv2 package overwrites the first); ninja only served the compiled helper above |
| `OPENCV_IO_ENABLE_OPENEXR=1` and opencv-python 4 | the `parts` dependency group, `steps/parts.py` | upstream reads its EXR depth maps through `cv2.imread`; OpenCV 5 returns nothing |
