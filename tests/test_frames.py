"""§3.3 ovoxel.npz round trip and §3.4 frame conversions (CPU)."""

import numpy as np
import pytest

from steps._common import (
    PIXAL3D_TO_GLTF,
    StepError,
    library_to_trellis,
    load_ovoxel,
    save_ovoxel,
    trellis_to_library,
)


def apply(m, pts):
    return (np.c_[pts, np.ones(len(pts))] @ m.T)[:, :3]


def test_frames_round_trip_and_landmarks():
    lo, hi = np.array([-0.2, -0.1, -0.4]), np.array([0.2, 0.3, 0.35])
    m = trellis_to_library(lo, hi, height_m=1.8)
    base, top = [0.0, 0.1, -0.4], [0.0, 0.1, 0.35]  # base and top centre in TRELLIS (Z up)
    np.testing.assert_allclose(apply(m, np.array([base, top])), [[0, 0, 0], [0, 1.8, 0]], atol=1e-9)
    np.testing.assert_allclose(
        apply(m, np.array([[0.2, 0.1, -0.4]]))[0], [0.48, 0, 0], atol=1e-9
    )  # +X stays +X
    pts = np.random.default_rng(0).uniform(-0.5, 0.5, (100, 3))
    np.testing.assert_allclose(apply(library_to_trellis(m), apply(m, pts)), pts, atol=1e-6)
    assert np.linalg.det(m[:3, :3]) > 0  # still right-handed


def test_pixal3d_frame_is_y_up_facing_the_camera():
    lo, hi = np.array([-0.2, -0.4, -0.1]), np.array([0.2, 0.35, 0.3])  # Y up in Pixal3D's volume
    m = trellis_to_library(lo, hi, height_m=1.5, to_gltf=PIXAL3D_TO_GLTF)
    base, top = [0.0, -0.4, 0.1], [0.0, 0.35, 0.1]
    np.testing.assert_allclose(apply(m, np.array([base, top])), [[0, 0, 0], [0, 1.5, 0]], atol=1e-9)
    # +X stays +X and the front (+Z, towards the camera) stays +Z: not turned around
    np.testing.assert_allclose(apply(m, np.array([[0.2, -0.4, 0.3]]))[0], [0.4, 0, 0.4], atol=1e-9)
    assert np.linalg.det(m[:3, :3]) > 0


def test_ovoxel_round_trip(tmp_path):
    rng = np.random.default_rng(1)
    coords = rng.integers(0, 1024, (500, 3))
    attrs = rng.random((500, 6))
    layout = {"base_color": [0, 3], "metallic": [3, 4], "roughness": [4, 5], "alpha": [5, 6]}
    save_ovoxel(tmp_path / "ovoxel.npz", coords, attrs, layout, 1024)
    v = load_ovoxel(tmp_path / "ovoxel.npz")
    assert v["coords"].dtype == np.int32 and v["attrs"].dtype == np.float16
    np.testing.assert_array_equal(v["coords"], coords)
    np.testing.assert_allclose(v["attrs"], attrs, atol=1e-3)
    assert v["layout"] == layout and v["resolution"] == 1024
    np.testing.assert_allclose(v["voxel_size"], [1 / 1024] * 3)
    np.testing.assert_array_equal(v["aabb"], [[-0.5] * 3, [0.5] * 3])
    np.savez(tmp_path / "bad.npz", frame="library")
    with pytest.raises(StepError):
        load_ovoxel(tmp_path / "bad.npz")
