"""M35a: where the disk space goes (server/storage.py) on a small fake install, and the cleanups; the install
refuses when a group does not fit."""

import json
import os
from pathlib import Path

import pytest

from server import jobs, models, storage
from server.library import ApiError


@pytest.fixture
def install(tmp_path, monkeypatch):
    """An app folder with two environments sharing a hard-linked package, a model group, a library with an
    archived asset and a trash."""
    root, lib, mod = tmp_path / "app", tmp_path / "library", tmp_path / "models"
    for d in (
        root / ".venv-ml",
        root / ".venv-kimodo",
        root / "blender",
        lib / "_trash" / "x",
        mod / "Fx",
    ):
        d.mkdir(parents=True)
    (root / ".venv-ml" / "torch.dll").write_bytes(b"t" * 3000)
    os.link(
        root / ".venv-ml" / "torch.dll", root / ".venv-kimodo" / "torch.dll"
    )  # one file, two links
    (root / ".venv-kimodo" / "kimodo.py").write_bytes(b"k" * 500)
    (root / "blender" / "blender.exe").write_bytes(b"b" * 200)
    (mod / "Fx" / "w.bin").write_bytes(b"w" * 1000)
    (mod / "leftover.lock").write_bytes(b"l" * 7)
    (lib / "_trash" / "x" / "old.glb").write_bytes(b"o" * 300)
    for aid, archived in (("keep", False), ("old", True)):
        (lib / aid).mkdir()
        (lib / aid / "asset.json").write_text(
            json.dumps({"id": aid, "name": aid, "archived": archived})
        )
        (lib / aid / "mesh.glb").write_bytes(b"m" * 100)
    monkeypatch.setattr(storage, "ROOT", root)
    monkeypatch.setenv("EFFIGY_LIBRARY", str(lib))
    monkeypatch.setenv("EFFIGY_MODELS", str(mod))
    monkeypatch.setattr(
        models,
        "entries",
        lambda: [
            {
                "name": "fx",
                "groups": ["fx"],
                "revision": "r",
                "where": "Fx",
                "filters": {},
                "hub": False,
                "key": "fx",
            }
        ],
    )
    monkeypatch.setattr(storage, "_last", None)
    return root, lib, mod


def by_id(st):
    return {i["id"]: i for i in st["items"]}


def test_sizes_count_what_removing_would_free(install):
    st = storage.storage()
    items = by_id(st)
    assert items["models:fx"]["bytes"] == 1000 and items["models:fx"]["action"] == "group:fx"
    assert items["models:other"]["bytes"] == 7  # not any entry's: a cache or a leftover
    # the hard-linked package frees nothing when one environment goes: it is counted once, as shared
    assert items["venv:.venv-ml"]["bytes"] == 0 and items["venv:.venv-ml"]["action"] is None
    assert items["venv:.venv-kimodo"]["bytes"] == 500
    assert items["venv:.venv-kimodo"]["action"] == "venv:.venv-kimodo"
    assert items["shared"]["bytes"] == 3000
    assert items["library:assets"]["bytes"] == 100 + len(
        '{"id": "keep", "name": "keep", "archived": false}'
    )
    assert items["library:archived"]["action"] is None  # deleted one by one, from the assets list
    assert [a["id"] for a in st["assets"] if a["archived"]] == ["old"]
    assert items["library:trash"]["bytes"] == 300
    assert items["tool:blender"]["action"] is None
    assert [a["id"] for a in st["assets"]] and st["drives"]


def test_cleanups_free_the_space(install):
    root, lib, mod = install
    assert storage.cleanup("trash")["failed"] == 0
    assert not (lib / "_trash").exists()
    storage.cleanup("archived:old")  # one archived asset, by its folder
    assert not (lib / "old").exists() and (lib / "keep").exists()
    storage.cleanup("venv:.venv-kimodo")  # renamed out of the way, then deleted
    assert not (root / ".venv-kimodo").exists() and not (root / ".venv-kimodo.deleting").exists()
    assert (root / ".venv-ml" / "torch.dll").is_file()  # the other link of the shared file
    storage.cleanup("group:fx")
    assert not (mod / "Fx").exists()
    assert not jobs.GPU.locked()  # released after the guarded cleanups
    for bad in ("venv:.venv-ml", "venv:../x", "prune", "nonsense"):
        with pytest.raises(
            ApiError
        ) as e:  # the core environment; no path from the request; no own cache
            storage.cleanup(bad)
        assert e.value.status == 400, bad


def test_archived_assets_are_deleted_only_when_they_are_what_they_say(install):
    _root, lib, _mod = install
    with pytest.raises(ApiError) as e:
        storage.cleanup("archived:keep")  # live
    assert e.value.status == 409 and (lib / "keep").exists()
    # a copy of the live folder that says it is archived and names it: neither may go by the other's name
    (lib / "keep_copy").mkdir()
    (lib / "keep_copy" / "asset.json").write_text(json.dumps({"id": "keep", "archived": True}))
    with pytest.raises(ApiError):
        storage.cleanup("archived:keep_copy")  # its asset.json names another asset
    with pytest.raises(ApiError):
        storage.cleanup("archived:keep")  # the live one is still not archived
    assert (lib / "keep").exists() and (lib / "keep_copy").exists()
    with pytest.raises(ApiError) as e:
        storage.cleanup("archived:../app")  # not an asset id
    assert e.value.status == 404
    job = jobs.Job("old", "clean", None, {})
    jobs.JOBS[job.id] = job  # queued on the archived asset
    try:
        with pytest.raises(ApiError) as e:
            storage.cleanup("archived:old")
        assert e.value.status == 409 and (lib / "old").exists()
    finally:
        del jobs.JOBS[job.id]


@pytest.mark.skipif(os.name != "nt", reason="an open file blocks deletion on Windows only")
def test_files_in_use_are_reported_not_hidden(install):
    root, lib, _mod = install
    with open(lib / "_trash" / "x" / "old.glb", "rb"):
        res = storage.cleanup("trash")
    assert res["failed"] >= 1 and (lib / "_trash" / "x" / "old.glb").exists()
    with open(root / ".venv-kimodo" / "kimodo.py", "rb"), pytest.raises(ApiError) as e:
        storage.cleanup("venv:.venv-kimodo")  # the rename fails whole: nothing half-deleted
    assert e.value.status == 409 and (root / ".venv-kimodo" / "kimodo.py").is_file()


@pytest.mark.skipif(os.name != "nt", reason="junctions are a Windows thing")
def test_junctions_are_not_followed(install, tmp_path):
    import _winapi

    _root, _lib, mod = install
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "big.bin").write_bytes(b"x" * 5000)
    _winapi.CreateJunction(str(outside), str(mod / "Fx" / "linked"))
    items = by_id(storage.storage(refresh=True))
    assert items["models:fx"]["bytes"] == 1000  # the 5000 behind the junction are not ours
    storage.cleanup("group:fx")
    assert (outside / "big.bin").is_file()


def test_sizes_cover_every_group():
    from tools.download_models import SIZES

    assert set(SIZES) == models.GROUPS


def test_cleanup_waits_for_a_running_step(install):
    jobs.GPU.acquire()
    try:
        with pytest.raises(ApiError) as e:
            storage.cleanup("venv:.venv-kimodo")
        assert e.value.status == 409
    finally:
        jobs.GPU.release()
    assert (install[0] / ".venv-kimodo").exists()


def test_a_drive_is_low_under_20_gb_or_10_percent(install, monkeypatch):
    usage = type("U", (), {})
    for total, free, low in ((1e12, 4.3e10, True), (1e12, 2e11, False), (1e11, 1.9e10, True)):
        u = usage()
        u.total, u.free = int(total), int(free)
        monkeypatch.setattr(storage.shutil, "disk_usage", lambda d, u=u: u)
        assert storage.drives()[0]["low"] is low


def test_install_refuses_a_group_that_does_not_fit(install, monkeypatch):
    from server import install as installer

    monkeypatch.setattr(models, "MANIFEST_ROWS", {"k": {"w.bin": [50 * 10**9, None]}})
    monkeypatch.setattr(
        models,
        "entries",
        lambda: [
            {
                "name": "fx",
                "groups": ["fx"],
                "revision": "r",
                "where": "Fx",
                "filters": {},
                "hub": False,
                "key": "k",
            }
        ],
    )
    u = type("U", (), {"total": 10**12, "free": 10 * 10**9, "used": 0})()
    monkeypatch.setattr(installer.shutil, "disk_usage", lambda d: u)
    monkeypatch.setattr(models, "GROUPS", {"fx"})
    with pytest.raises(ApiError) as e:
        installer.install("fx")
    assert e.value.status == 507 and "50.0 GB more" in str(e.value)
    assert models.missing_bytes("fx") == 50 * 10**9
    assert Path(install[2]).exists()


def test_a_file_two_features_share_is_removed_from_its_shared_row(install, monkeypatch):
    """Space removes what one feature alone uses and leaves what it shares; the shared row removes what exactly those
    features share (the only Remove since Setup's model table lost its own)."""
    _root, _lib, mod = install
    own = models.entries()[0]
    shared = {
        "name": "s",
        "groups": ["fx", "fy"],
        "revision": "r",
        "where": "S",
        "filters": {},
        "hub": False,
        "key": "s",
    }
    monkeypatch.setattr(models, "entries", lambda: [own, shared])
    (mod / "S").mkdir()
    (mod / "S" / "w.bin").write_bytes(b"s" * 300)
    monkeypatch.setattr(storage, "_last", None)
    row = by_id(storage.storage())["models:fx+fy"]
    assert row["action"] == "group:fx+fy" and row["bytes"] == 300
    storage.cleanup("group:fx")
    assert not (mod / "Fx").exists() and (mod / "S" / "w.bin").is_file()  # still needed by fy
    storage.cleanup("group:fx+fy")
    assert not (mod / "S").exists()
    with pytest.raises(ApiError) as e:
        storage.cleanup("group:fx+nope")  # only known groups
    assert e.value.status == 400
