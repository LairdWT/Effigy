"""tools/bench.py against a real backend (uvicorn in a thread) with steps._echo standing in for the chain."""

import csv
import time

import pytest
from PIL import Image

from server import jobs
from tools import bench


def test_bench_writes_one_row_per_image(tmp_path, monkeypatch, live_server):
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path / "library"))
    monkeypatch.setitem(
        bench.CHAINS,
        "echo",
        {"build": [("_echo", {"op": "a"})], "check": [("_echo", {"op": "b", "fail": "failed"})]},
    )
    golden = tmp_path / "golden"
    golden.mkdir()
    Image.new("RGB", (8, 8), (200, 50, 50)).save(golden / "red.png")
    (golden / "prompts.yaml").write_text("[]")  # not an image: ignored
    out = tmp_path / "bench.csv"
    argv = ["--api", live_server, "--preset", "echo", "--set", str(golden), "--out", str(out)]

    assert bench.main(argv) == 1  # the check step failed
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# commit: ") and any(x.startswith("# preset: echo") for x in lines)
    (row,) = csv.DictReader(x for x in lines if not x.startswith("#"))
    assert row["image"] == "red.png" and row["ok"] == "False" and row["failed_step"] == "_echo"
    assert row["error"] == "asked to fail" and float(row["s__echo"]) >= 0


def test_batch_mode_names_assets_by_image_and_exports(tmp_path, monkeypatch, live_server):
    """PLAN Phase 3 CLI batch mode: --export runs the export after the chain (here it fails: an echo version
    has nothing to export, or no .venv-ml), the asset is named after its image, --to needs --export."""
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path / "library"))
    monkeypatch.setitem(bench.CHAINS, "echo", {"build": [("_echo", {"op": "a"})], "check": []})
    golden, to = tmp_path / "golden", tmp_path / "game"
    golden.mkdir()
    to.mkdir()
    Image.new("RGB", (8, 8), (200, 50, 50)).save(golden / "red.png")
    out = tmp_path / "batch.csv"
    argv = ["--api", live_server, "--preset", "echo", "--set", str(golden), "--out", str(out)]
    with pytest.raises(SystemExit):
        bench.main([*argv, "--to", str(to)])
    assert bench.main([*argv, "--export", "obj", "--to", str(to)]) == 1
    lines = out.read_text(encoding="utf-8").splitlines()
    (row,) = csv.DictReader(x for x in lines if not x.startswith("#"))
    assert row["ok"] == "False" and row["failed_step"] == "export" and row["error"]
    assets = bench.call(live_server, "GET", "/api/assets")
    assert next(a["name"] for a in assets if a["id"] == row["asset"]) == "red"


def test_batch_copy_outcomes_and_the_folder_check(tmp_path, monkeypatch):
    """The copy block without a server: a copied folder lands in the row; a skipped or refused copy fails the
    row (the files were what was asked for); the preset's own godot export gives way; --to must exist."""
    calls = []

    def fake_call(api, method, path, body=None, raw=None):
        calls.append((method, path, body))
        if path == "/api/assets":
            return {"id": "lamp"}
        if path.startswith("/api/assets/lamp/upload/"):
            return {"version": "001_upload"}
        if path == "/api/export/copy":
            return outcome
        raise AssertionError(path)

    monkeypatch.setattr(bench, "call", fake_call)
    monkeypatch.setattr(
        bench,
        "run_job",
        lambda api, asset, step, parent, params: (
            {"status": "done", "version": f"0{step}"},
            1.0,
            None,
        ),
    )
    monkeypatch.setattr(bench, "version_meta", lambda api, asset, version: {"metrics": {}})
    img = tmp_path / "my lamp.png"
    img.write_bytes(b"png")
    chain = {"build": [("_echo", {})], "check": []}
    outcome = {"copied": [{"dir": str(tmp_path / "lamp_obj")}], "skipped": []}
    row = bench.bench_image("http://x", img, chain, "obj", tmp_path)
    assert row["ok"] and row["export"] == str(tmp_path / "lamp_obj") and "s_export" in row
    assert calls[1][1] == "/api/assets/lamp/upload/my%20lamp.png"  # a space in the name is quoted
    outcome = {"copied": [], "skipped": [{"reason": "exists"}]}
    row = bench.bench_image("http://x", img, chain, "obj", tmp_path)
    assert not row["ok"] and row["failed_step"] == "copy" and row["error"] == "not copied: exists"
    with pytest.raises(SystemExit):  # --to must be a folder before any chain runs
        bench.main(["--preset", "game-prop", "--export", "obj", "--to", str(tmp_path / "nope")])


def test_summary_counts_characters_that_need_no_marker_fix():
    steps = ["rig_fit", "rig_skin"]
    rows = [
        {
            "ok": True,
            "s_rig_fit": 9.0,
            "rig_fit_inside": 52,
            "rig_fit_joints": 52,
            "rig_skin_fail": 0,
        },
        {
            "ok": True,
            "s_rig_fit": 9.0,
            "rig_fit_inside": 51,
            "rig_fit_joints": 52,
            "rig_skin_fail": 0,
        },
        {
            "ok": True,
            "s_rig_fit": 9.0,
            "rig_fit_inside": 52,
            "rig_fit_joints": 52,
            "rig_skin_fail": 1,
        },
        {
            "ok": False,
            "s_rig_fit": 9.0,
            "rig_fit_inside": 52,
            "rig_fit_joints": 52,
            "rig_skin_fail": 0,
        },
    ]
    assert "no marker fix needed: 2/4" in bench.summary(rows, steps)  # a skin fail still counts


def test_a_turnaround_goes_through_prep_views_straight_to_generate(tmp_path):
    chain = {
        "build": [["prep", {}], ["canon", {}], ["prep", {}], ["trellis2", {}], ["clean", {}]],
        "check": [["validate", {}]],
    }
    (tmp_path / "dwarf.views.json").write_text('["front", "right", "back", "left"]')
    got = bench.chain_for(tmp_path / "dwarf.png", chain)
    assert [s for s, _ in got["build"]] == ["prep", "trellis2", "clean"]
    assert got["build"][0][1] == {"op": "views", "views": ["front", "right", "back", "left"]}
    assert got["check"] == chain["check"]
    assert bench.chain_for(tmp_path / "knight.png", chain) is chain


def test_ctrl_c_cancels_the_job_it_waits_for(tmp_path, monkeypatch, live_server):
    """A job left running would hold the GPU after the bench or the GPU report is stopped (M46 review)."""
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path / "library"))
    asset = bench.call(live_server, "POST", "/api/assets", {"name": "Crate"})["id"]

    def ctrl_c(fields):
        raise KeyboardInterrupt

    monkeypatch.setattr(bench, "gpu_query", ctrl_c)
    with pytest.raises(KeyboardInterrupt):
        bench.run_job(live_server, asset, "_echo", None, {"op": "ctrl-c", "sleep": 30})
    (job,) = [j for j in jobs.JOBS.values() if j.params.get("op") == "ctrl-c"]
    end = time.time() + 20
    while job.status != "cancelled":
        assert time.time() < end, job.status
        time.sleep(0.05)
