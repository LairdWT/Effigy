"""M40: the API closed to web pages, Connect an agent, and `look` (Blender skipped without it)."""

import io
import json
import os
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from server import agent, blender_install, look
from server.app import app

client = TestClient(app)
ANIM = Path(__file__).parent / "fixtures" / "anim.glb"
blender = pytest.mark.skipif(
    not blender_install.blender_exe().is_file(), reason="Blender not installed"
)


def test_host_and_origin_guard():
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "bad_origin"
    assert (
        client.get("/api/health", headers={"Origin": "https://localhost:5173"}).status_code == 403
    )
    for origin in ("http://localhost:5173", "http://127.0.0.1:8000", "http://[::1]:8000"):
        assert client.get("/api/health", headers={"Origin": origin}).status_code == 200
    assert client.get("/api/health", headers={"Host": "[::1]:8000"}).status_code == 200
    assert client.get("/api/health").status_code == 200


def test_setup_texts():
    s = client.get("/api/agent/setup").json()
    by = {c["id"]: c for c in s["clients"]}
    assert set(by) == {"claude-code", "claude-desktop", "codex", "cursor", "vscode", "gemini"}
    assert by["claude-code"]["text"].startswith("claude mcp add -s user effigy -- ")
    assert s["root"] in by["claude-code"]["text"] and s["server"].endswith("effigy_server.py")
    for i in ("claude-desktop", "cursor", "gemini"):
        e = json.loads(by[i]["text"])["mcpServers"]["effigy"]
        assert e["args"] == s["python"] and s["root"] in e["args"]
    e = json.loads(by["vscode"]["text"])["servers"]["effigy"]
    assert e["type"] == "stdio"
    t = tomllib.loads(by["codex"]["text"])["mcp_servers"]["effigy"]
    assert t["args"] == s["python"] and t["tool_timeout_sec"] == 120


def test_agent_test_reports_a_failure(monkeypatch):
    monkeypatch.setattr(agent, "command", lambda: ("python", ["-c", "import sys;sys.exit('boom')"]))
    r = client.post("/api/agent/test").json()
    assert r["ok"] is False and r["error"]


@pytest.mark.skipif(not agent.uv(), reason="uv missing")
def test_agent_test_lists_the_tools():
    r = client.post("/api/agent/test").json()
    assert r["ok"], r
    assert len(r["tools"]) >= 7 and "list_assets" in r["tools"]


def _version(tmp_path, monkeypatch, outputs: dict[str, bytes]) -> str:
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    d = tmp_path / "walker" / "010_bake"
    d.mkdir(parents=True, exist_ok=True)
    (tmp_path / "walker" / "asset.json").write_text(json.dumps({"id": "walker", "name": "walker"}))
    for name, data in outputs.items():
        (d / name).write_bytes(data)
    meta = {"version": d.name, "parent": None, "outputs": {n: n for n in outputs}}
    (d / "meta.json").write_text(json.dumps(meta))
    return "/api/assets/walker/versions/010_bake/look"


def _png(r) -> Image.Image:
    assert r.status_code == 200, r.text
    return Image.open(io.BytesIO(r.content))


def test_look_pictures_and_errors(tmp_path, monkeypatch):
    url = _version(tmp_path, monkeypatch, {})
    assert client.get(url).status_code == 400  # nothing to show
    buf = io.BytesIO()
    Image.new("RGB", (64, 96), (200, 30, 30)).save(buf, "PNG")
    url = _version(tmp_path, monkeypatch, {f"cand_{k}.png": buf.getvalue() for k in range(4)})
    assert _png(client.get(url + "?size=100")).size == (256, 256)  # clamped up
    assert client.get(url + "?clip=Walk").status_code == 400  # a picture has no clips


@blender
def test_look_model_and_clip(tmp_path, monkeypatch):
    os.environ.setdefault("EFFIGY_BLENDER", str(blender_install.blender_exe()))
    url = _version(tmp_path, monkeypatch, {"m.glb": ANIM.read_bytes()})
    names = look.clips(ANIM)
    assert "Walk" in names
    for q, size in (("", 768), ("?size=384", 384), ("?clip=Walk&size=512", 512)):
        im = _png(client.get(url + q))
        assert im.size == (size, size)
        lo, hi = im.convert("L").getextrema()
        assert hi - lo > 40  # something is drawn
    assert client.get(url + "?clip=nope").status_code == 400
