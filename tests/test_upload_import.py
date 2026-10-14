"""M39 upload: streamed to disk, models and zips (checked before extraction)."""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from server import library
from server.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    with TestClient(app) as c:
        c.asset = c.post("/api/assets", json={"name": "Crate"}).json()["id"]
        yield c


def put(c, name, body):
    return c.put(f"/api/assets/{c.asset}/upload/{name}", content=body)


def zipped(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for path, data in members.items():
            z.writestr(path, data)
    return buf.getvalue()


def versions(c):
    return sorted(p.name for p in library.asset_dir(c.asset).iterdir() if p.name[:3].isdigit())


def inbox(c):
    return list((library.asset_dir(c.asset) / "inbox").glob("*"))


def refused(c, body, code="bad_zip", msg=""):
    r = put(c, "m.zip", body)
    assert r.status_code == 400 and r.json()["error"]["code"] == code
    assert msg in r.json()["error"]["message"]
    assert versions(c) == [] and inbox(c) == []


@pytest.mark.parametrize("bad", ["../a.obj", "/a.obj", "C:/a.obj", "a/../../b.obj", "..\\a.obj"])
def test_unsafe_member_names(client, bad):
    refused(client, zipped({"ok.obj": b"o", bad: b"o"}), msg="absolute or parent")


def test_zip_refusals(client, monkeypatch):
    refused(client, zipped({"in.zip": zipped({"a.obj": b"o"}), "a.obj": b"o"}), msg="in.zip")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.obj", b"o")
        z.infolist()[0].flag_bits |= 1
    refused(client, buf.getvalue(), msg="a.obj: encrypted")
    refused(client, zipped({"readme.txt": b"hi"}), "no_model")
    refused(client, b"not a zip at all", msg="not a zip")
    monkeypatch.setattr(library, "ZIP_MEMBERS", 2)
    refused(client, zipped({"a.obj": b"o", "b.txt": b"1", "c.txt": b"2"}), msg="3 members")
    monkeypatch.setattr(library, "ZIP_BYTES", 10)
    refused(client, zipped({"a.obj": b"o" * 11}), msg="unpacks to more")


def test_model_choice_and_extraction(client):
    body = zipped(
        {
            "__MACOSX/._a.obj": b"x",
            ".hidden/b.glb": b"x",
            "a.obj": b"o" * 5,
            "deep/dir/a.glb": b"g",
            "deep/other.obj": b"o" * 50,
            "top.obj": b"o" * 9,
            "deep/dir/a.mtl": b"m",
            "deep/dir/tex/a.png": b"p",
        }
    )
    m = put(client, "pack.zip", body).json()
    assert m["outputs"] == {"model": "source/deep/dir/a.glb"} and m["params"] == {
        "name": "pack.zip"
    }
    assert m["provenance"] == "upload" and m["parent"] is None
    src = library.version_dir(client.asset, m["version"]) / "source"
    files = sorted(p.relative_to(src).as_posix() for p in src.rglob("*") if p.is_file())
    assert files == [
        "a.obj",
        "deep/dir/a.glb",
        "deep/dir/a.mtl",
        "deep/dir/tex/a.png",
        "deep/other.obj",
        "top.obj",
    ]
    # the shallowest .obj, then the largest of those
    m = put(client, "p.zip", zipped({"x/a.obj": b"1", "b.obj": b"1", "c.obj": b"123"})).json()
    assert m["outputs"] == {"model": "source/c.obj"}
    # a model in a subfolder: its .mtl and texture land beside it
    m = put(client, "p.zip", zipped({"s/a.obj": b"o", "s/a.mtl": b"m", "s/t.png": b"p"})).json()
    assert m["outputs"] == {"model": "source/s/a.obj"}
    assert (library.version_dir(client.asset, m["version"]) / "source/s/t.png").read_bytes() == b"p"


def test_single_files(client):
    m = put(client, "Dwarf (v2) é.FBX", b"fbx").json()
    safe = "Dwarf _v2_ _.FBX"
    assert m["outputs"] == {"model": f"source/{safe}"} and m["params"]["name"] == "Dwarf (v2) é.FBX"
    assert (
        library.version_dir(client.asset, m["version"]) / "source" / safe
    ).read_bytes() == b"fbx"
    long = put(client, "a" * 150 + ".stl", b"s").json()["outputs"]["model"]
    assert len(long) == len("source/") + 100 and long.endswith(".stl")
    assert put(client, "m.glb", b"glb").json()["outputs"] == {"mesh": "mesh.glb"}
    assert put(client, "p.PNG", b"png").json()["outputs"] == {"image": "image.png"}
    r = put(client, "x.docx", b"x")
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"
    assert inbox(client) == []


def test_over_the_cap_streams_to_413(client, monkeypatch):
    monkeypatch.setattr("server.app.MAX_UPLOAD", 100)

    def chunks():
        for _ in range(5):
            yield b"x" * 60

    r = put(client, "m.fbx", chunks())
    assert r.status_code == 413 and r.json()["error"]["code"] == "too_large"
    assert versions(client) == [] and inbox(client) == []
