"""§3.1 step protocol, exercised through steps._echo."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINE = re.compile(r"^(PROGRESS( \S+)? \d\.\d{3}( .*)?|(RESULT|ERROR)( \S+)? \{.*\}|READY)$")


def echo(*args, stdin=None):
    cmd = [sys.executable, "-m", "steps._echo", *args]
    return subprocess.run(cmd, cwd=ROOT, input=stdin, capture_output=True, text=True, check=False)


def last(p):
    kind, payload = p.stdout.strip().splitlines()[-1].split(" ", 1)
    return kind, json.loads(payload)


def test_success_and_stdout_isolation(tmp_path):
    p = echo("--out", str(tmp_path / "v"), "--params", '{"op": "x", "a": 1}')
    assert p.returncode == 0, p.stderr
    assert all(LINE.match(line) for line in p.stdout.splitlines()), p.stdout
    assert "noise" not in p.stdout and "library noise" in p.stderr and "C-level" in p.stderr
    assert last(p) == (
        "RESULT",
        {"outputs": {"echo": "echo.json"}, "metrics": {"op": "x"}, "licenses": []},
    )
    assert json.loads((tmp_path / "v" / "echo.json").read_text())["params"] == {"a": 1}


def test_exit_codes(tmp_path):
    out = str(tmp_path / "v")
    cases = [
        (["--out", out, "--params", "not json"], 2, "bad_params"),
        (["--params", "{}"], 2, "bad_params"),
        (["--in", str(tmp_path / "missing"), "--out", out], 2, "missing_input"),
        (["--out", out, "--params", '{"oom": true}'], 3, "oom"),
        (["--out", out, "--params", '{"fail": "failed"}'], 1, "failed"),
    ]
    for args, code, err in cases:
        p = echo(*args)
        assert p.returncode == code, (args, p.stdout, p.stderr)
        assert last(p) == ("ERROR", last(p)[1]) and last(p)[1]["code"] == err


def test_serve_round_trip(tmp_path):
    reqs = [
        {"id": "r1", "op": "gen", "out": str(tmp_path / "a"), "params": {}},
        {"id": "r2", "op": "gen", "out": str(tmp_path / "b"), "params": {"oom": True}},
        {"op": "quit"},
    ]
    p = echo("--serve", stdin="".join(json.dumps(r) + "\n" for r in reqs))
    lines = p.stdout.splitlines()
    assert p.returncode == 0 and lines[0] == "READY"
    assert all(LINE.match(line) for line in lines), lines
    assert lines[1] == "PROGRESS r1 0.500 op=gen"
    assert lines[2].startswith("RESULT r1 ") and lines[-1].startswith("ERROR r2 ")
    assert json.loads(lines[-1].split(" ", 2)[2])["code"] == "oom"


def test_params_from_file(tmp_path):
    big = {"a": "x" * 50000}
    f = tmp_path / "p.json"
    f.write_text(json.dumps(big))
    p = echo("--out", str(tmp_path / "v"), "--params", f"@{f}")
    assert p.returncode == 0, p.stderr
    assert json.loads((tmp_path / "v" / "echo.json").read_text())["params"] == big
    p = echo("--out", str(tmp_path / "w"), "--params", f"@{tmp_path / 'nope.json'}")
    assert p.returncode == 2 and last(p)[1]["code"] == "bad_params"
