"""rig_fit with joint and twist overrides (M22b, the skeleton editor): no detection, the rest kept."""

import json

import numpy as np
import pytest

trimesh = pytest.importorskip("trimesh")
pytest.importorskip("cv2")  # rig_fit imports the pose model module (the ML venv)
from steps import _rig, rig_fit


def test_joint_and_twist_overrides_land_in_the_skeleton(tmp_path):
    src, out = tmp_path / "100_rig_fit", tmp_path / "110_rig_fit"
    src.mkdir()
    out.mkdir()
    trimesh.creation.box((0.6, 1.8, 0.4)).apply_translation([0, 0.9, 0]).export(src / "mesh.glb")
    names = [n for n, _ in _rig.template()]
    parents = dict(_rig.template())
    joints = {n: [0.0, 0.9 + 0.01 * i, 0.0] for i, n in enumerate(names)}  # all inside the box
    (src / "skeleton.json").write_text(
        json.dumps(
            {
                "template": "mixamo52",
                "frame": "gltf_yup_m",
                "joints": [
                    {"name": n, "parent": parents[n], "position": joints[n]}
                    | ({"twist": [0, -1, 0]} if n == "RightHand" else {})
                    for n in names
                ],
            }
        )
    )
    (src / "markers.json").write_text(
        json.dumps({"markers": {}, "confidence": {}, "hands": {}, "facing": 1, "source": "dwpose"})
    )
    (src / "meta.json").write_text(
        json.dumps(
            {
                "version": "100_rig_fit",
                "outputs": {"mesh": "mesh.glb", "skeleton": "skeleton.json"},
                "metrics": {"parts": {"Helmet": 3, "Body": 9}},
            }
        )
    )
    (src / "parts.json").write_text('{"views": "x", "labels": [], "parts": []}')  # M32: rides along

    res = rig_fit.run(
        "run",
        str(src),
        str(out),
        {"joints": {"LeftHand": [0.2, 1.0, 0.05]}, "twists": {"LeftHand": [0, 0, -1]}},
    )
    skel = {x["name"]: x for x in json.loads((out / "skeleton.json").read_text())["joints"]}
    assert skel["LeftHand"]["position"] == [0.2, 1.0, 0.05] and skel["LeftHand"]["twist"] == [
        0,
        0,
        -1,
    ]
    assert skel["RightHand"]["twist"] == [0, -1, 0]  # the parent version's twist is kept
    assert skel["Hips"]["position"] == joints["Hips"] and "twist" not in skel["Hips"]
    assert (out / "parts.json").is_file() and res["outputs"]["parts"] == "parts.json"
    assert res["metrics"]["parts"] == {"Helmet": 3, "Body": 9}
    assert res["metrics"]["source"] == "edited" and res["metrics"]["twists"] == [
        "LeftHand",
        "RightHand",
    ]
    assert "models" not in res  # no pose model ran
    assert json.loads((out / "markers.json").read_text())["source"] == "edited"
    assert np.isclose(json.loads((out / "report.json").read_text())["inside"], 52)


def test_an_empty_edit_copies_the_skeleton_without_detection(tmp_path):
    src, out = tmp_path / "100_rig_fit", tmp_path / "110_rig_fit"
    src.mkdir()
    out.mkdir()
    trimesh.creation.box((0.6, 1.8, 0.4)).apply_translation([0, 0.9, 0]).export(src / "mesh.glb")
    names = [n for n, _ in _rig.template()]
    parents = dict(_rig.template())
    (src / "skeleton.json").write_text(
        json.dumps(
            {
                "joints": [
                    {"name": n, "parent": parents[n], "position": [0.0, 0.9 + 0.01 * i, 0.0]}
                    for i, n in enumerate(names)
                ]
            }
        )
    )
    (src / "meta.json").write_text(
        json.dumps({"version": "100_rig_fit", "outputs": {"mesh": "mesh.glb"}})
    )
    res = rig_fit.run("run", str(src), str(out), {"joints": {}, "twists": {}})
    before = json.loads((src / "skeleton.json").read_text())["joints"]
    after = json.loads((out / "skeleton.json").read_text())["joints"]
    assert np.allclose(
        [j["position"] for j in after], [j["position"] for j in before]
    )  # rounded to 5 decimals
    assert (
        res["metrics"]["source"] == "edited"
        and res["metrics"]["edited_joints"] == []
        and "models" not in res
    )
