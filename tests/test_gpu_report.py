"""tools/gpu_report.py against a real backend (uvicorn in a thread) with steps._echo standing in for the probes."""

import json
import urllib.parse

from tools import gpu_report
from tools.bench import call


def test_the_report_records_each_probe_and_deletes_the_scratch_asset(
    tmp_path, monkeypatch, live_server
):
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path / "library"))
    monkeypatch.setattr(
        gpu_report,
        "PROBES",
        [
            ("a", "_echo", {"op": "a"}, None, "upload"),
            ("b", "_echo", {"op": "b", "fail": "failed"}, None, "a"),
            ("c", "_echo", {}, None, "b"),  # b failed: nothing to run on
            ("d", "_echo", {}, "no-such-group", "a"),
            ("e", "_echo", {}, None, "a"),  # bigger than any card's budget
        ],
    )
    monkeypatch.setitem(gpu_report.NEED, "e", 10_000)
    out = tmp_path / "report.json"

    assert gpu_report.main(["--api", live_server, "--out", str(out)]) == 0
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert [(p["name"], p["status"]) for p in rep["probes"]] == [
        ("a", "done"),
        ("b", "failed"),
        ("c", "skipped"),
        ("d", "skipped"),
        ("e", "skipped"),
    ]
    assert rep["probes"][1]["message"] == "asked to fail" and rep["probes"][0]["seconds"] >= 0
    assert {"gpu", "driver", "budget_gb", "ram_gb", "os"} <= rep.keys()
    assert call(live_server, "GET", "/api/assets") == []


def test_the_issue_link_leaves_the_json_out_when_it_gets_too_long():
    rep = {
        k: "x"
        for k in ("gpu", "vram_gb", "driver", "compute_cap", "budget_gb", "ram_gb", "os", "torch")
    }
    short = rep | {"probes": [{"name": "fast", "status": "done", "params": {}}]}
    query = urllib.parse.urlsplit(gpu_report.issue_url(short)).query
    (body,) = urllib.parse.parse_qs(query)["body"]
    assert "```json" in body and json.loads(body.split("```json\n")[1].split("\n```")[0]) == short

    long = rep | {
        "probes": [
            {"name": f"p{i}", "status": "done", "params": {"x": "y" * 100}} for i in range(60)
        ]
    }
    url = gpu_report.issue_url(long)
    assert len(url) <= 8000 and "attached" in urllib.parse.unquote_plus(url)


def test_nothing_private_leaves_the_machine(monkeypatch, tmp_path):
    home = tmp_path / "Users" / "Jane Doe"
    monkeypatch.setattr(gpu_report.Path, "home", lambda: home)
    root = str(gpu_report.ROOT)
    text = (
        rf"{root}\steps\x.py; {gpu_report.ROOT.as_posix().lower()}/y; {home}\AppData\x; "
        r"C:/Users/someone/models/z; d:\users\other\w"
    )
    out = gpu_report.private(text)
    assert root.lower() not in out.lower() and "Jane" not in out and "someone" not in out
    assert "other" not in out and r"<app>\steps" in out and "Users/<user>/models" in out
