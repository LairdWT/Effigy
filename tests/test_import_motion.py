"""steps/import_motion without Blender: what it refuses before it starts one (owner 2026-10-12)."""

import json

import pytest

from steps import import_motion
from steps._common import StepError


def _upload(tmp_path, rel, name):
    up = tmp_path / "asset" / "010_upload"
    (up / rel).parent.mkdir(parents=True)
    (up / rel).write_bytes(b"x")
    (up / "meta.json").write_text(
        json.dumps({"outputs": {"model": rel}, "params": {"name": name}}), encoding="utf-8"
    )
    return up


def test_import_motion_refuses_a_model_file_and_unknown_params(tmp_path):
    up = _upload(tmp_path, "source/chair.obj", "chair.obj")
    out = tmp_path / "asset" / "020_import_motion"
    out.mkdir()
    with pytest.raises(StepError) as e:
        import_motion.run("run", str(up), str(out), {})
    assert e.value.code == "missing_input" and ".bvh" in str(e.value)
    with pytest.raises(StepError) as e:
        import_motion.run("run", str(up), str(out), {"clips": ["Walk"]})
    assert e.value.code == "bad_params"


def test_import_motion_says_what_blender_found(tmp_path, monkeypatch):
    """No animation, an unknown skeleton, a clip the file lacks: each a message that says so; a known one moves
    clip.glb into the version, with the name Blender gave it from the names in use in the asset."""
    up = _upload(tmp_path, "source/Samba Dancing.fbx", "Samba Dancing.fbx")
    out = tmp_path / "asset" / "020_import_motion"
    out.mkdir()
    replies = iter(
        [
            {"clips": [], "bones": [], "skeleton": None},
            {"clips": ["Samba Dancing"], "bones": ["Bip01", "Bip01 Pelvis"], "skeleton": None},
            {"clips": ["Samba Dancing"], "bones": [], "skeleton": None, "missing": "Run"},
        ]
    )
    monkeypatch.setattr(import_motion, "run_blender", lambda *a, **k: next(replies))
    monkeypatch.setattr(import_motion, "taken_names", lambda asset: set())
    for words in ("no skeleton with an animation", "Bip01", "no animation 'Run'"):
        with pytest.raises(StepError) as e:
            import_motion.run("run", str(up), str(out), {"clip": "Run"} if "Run" in words else {})
        assert words in str(e.value)

    def blender(op, inputs, out_dir, params, timeout):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "clip.glb").write_bytes(b"glb")
        seen.update(params)
        return {
            "clips": ["Samba Dancing"],
            "picked": "Samba Dancing",
            "name": "Samba Dancing 020",
            "bones": [],
            "skeleton": "mixamo",
            "frames": 30,
            "seconds": 1.0,
        }

    seen = {}
    monkeypatch.setattr(import_motion, "run_blender", blender)
    monkeypatch.setattr(
        import_motion, "taken_names", lambda asset: {"Samba Dancing"}
    )  # already one of that name
    res = import_motion.run("run", str(up), str(out), {"for": "015_rig_skin"})
    assert res["outputs"] == {"clip": "clip.glb"} and (out / "clip.glb").is_file()
    assert seen["taken"] == ["Samba Dancing"] and seen["suffix"] == "020" and seen["name"] is None
    assert res["metrics"]["name"] == "Samba Dancing 020" and res["metrics"]["skeleton"] == "mixamo"
    assert res["metrics"]["file"] == "Samba Dancing.fbx" and res["metrics"]["clips"] == [
        "Samba Dancing"
    ]
