"""§3.2: asset ids, version numbering, branching, meta.json, restricted propagation."""

import json
import os
from pathlib import Path

import pytest

from server import library
from server.library import ApiError


def finish(asset_id, step, parent, result=None):
    out = library.new_version(asset_id, step)
    return library.write_meta(out, parent, {"p": 1}, result or {"outputs": {}})


def test_numbering_branching_and_meta(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    a = library.create_asset("Dwarf Blacksmith!")["id"]
    assert a == "dwarf_blacksmith"
    assert library.create_asset("dwarf  blacksmith")["id"] == "dwarf_blacksmith_2"

    prep = finish(a, "prep", None, {"outputs": {}, "licenses": ["MIT"]})
    gen = finish(a, "trellis2", "001_prep", {"outputs": {}, "metrics": {"frame": {"x": 1}}})
    branch = finish(a, "trellis2", "001_prep")  # branch from the older parent
    assert [prep["version"], gen["version"], branch["version"]] == [
        "001_prep",
        "002_trellis2",
        "003_trellis2",
    ]
    assert gen["licenses"] == ["MIT"] and gen["frame"] == {"x": 1} and "frame" not in branch
    assert [m["version"] for m in library.chain(a, "003_trellis2")] == ["003_trellis2", "001_prep"]
    meta = json.loads((tmp_path / a / "003_trellis2" / "meta.json").read_text())
    assert meta["schema"] == 1 and meta["parent"] == "001_prep" and meta["provenance"] == "step"
    assert [v["version"] for v in library.get_asset(a)["versions"]] == [
        "001_prep",
        "002_trellis2",
        "003_trellis2",
    ]


def test_restricted_propagates_down_the_chain(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    a = library.create_asset("x")["id"]
    finish(a, "prep", None)
    hy = finish(a, "hunyuan", "001_prep")
    clean = finish(a, "clean", hy["version"])
    other = finish(a, "clean", "001_prep")
    assert hy["restricted"] and clean["restricted"] and not other["restricted"]


def test_ids_from_urls_are_checked(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    a = library.create_asset("x")["id"]
    (tmp_path / a / "001_prep").mkdir()  # no meta.json: not a finished version
    for bad in [lambda: library.asset_dir("../x"), lambda: library.version_dir(a, "../x")]:
        with pytest.raises(ApiError):
            bad()
    with pytest.raises(ApiError):
        library.version_dir(a, "001_prep")


def test_brief_is_copied_into_the_asset(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    a = library.create_asset("gargoyle")["id"]
    out = library.new_version(a, "brief")
    (out / "brief.yaml").write_text("prompt: stone gargoyle\ncategory: creature\n")
    library.write_meta(out, None, {}, {"outputs": {"brief": "brief.yaml"}})
    assert library.get_asset(a)["asset"]["brief"] == {
        "prompt": "stone gargoyle",
        "category": "creature",
    }


def test_version_numbers_end_at_999(tmp_path, monkeypatch):
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    a = library.create_asset("full")["id"]
    (
        tmp_path / a / "520_prep"
    ).mkdir()  # an asset numbered in tens before 2026-10-07 continues by one
    assert library.new_version(a, "clean").name == "521_clean"
    (tmp_path / a / "999_prep").mkdir()  # the last number NNN_step can hold
    with pytest.raises(ApiError, match="used up its version numbers"):
        library.new_version(a, "prep")
    assert not (tmp_path / a / "1000_prep").exists()  # nothing unreadable was created


def test_archive_star_and_label_are_kept_and_listed(tmp_path, monkeypatch):
    """M28: archived on the asset, starred and label on a version; the listing carries counts and the
    newest time for the grid."""
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    a = library.create_asset("crate")["id"]
    finish(a, "prep", None)
    assert library.update_asset(a, archived=True)["archived"] is True
    assert (
        library.update_asset(a, name="box")["name"] == "box"
        and library.get_asset(a)["asset"]["archived"]
    )
    with pytest.raises(ApiError):
        library.update_asset(a, name="  ")
    m = library.update_version(a, "001_prep", starred=True, label="  the good one  ")
    assert m["starred"] is True and m["label"] == "the good one"
    assert library.versions(a)[0]["starred"] is True
    listed = {x["id"]: x for x in library.list_assets()}[a]
    assert (
        listed["versions"] == 1
        and listed["updated"] == library.versions(a)[0]["created"]
        and listed["archived"]
    )


def test_two_steps_allocating_at_once_get_different_numbers(tmp_path, monkeypatch):
    """BE-002: a job and an upload allocating together took the same number with different suffixes; the
    scan and the mkdir are one now. The scan is slowed so the race shows without the lock."""
    import threading
    import time
    from pathlib import Path

    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    asset = library.create_asset("crate")["id"]
    real = Path.iterdir

    def slow(self):
        time.sleep(0.005)
        return real(self)

    monkeypatch.setattr(Path, "iterdir", slow)
    made = []

    def allocate(step):
        for _ in range(12):
            made.append(library.new_version(asset, step).name)

    threads = [threading.Thread(target=allocate, args=(s,)) for s in ("clean", "upload")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    numbers = [n[:3] for n in made]
    assert len(made) == 24 and len(set(numbers)) == 24, sorted(made)


def test_two_patches_at_once_both_persist(tmp_path, monkeypatch):
    """BE-004: an archive and a tag patch at the same time: both land (the read is slowed to show the race)."""
    import threading
    import time

    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    asset = library.create_asset("crate")["id"]
    real = library._read

    def slow(p):
        d = real(p)
        time.sleep(0.02)
        return d

    monkeypatch.setattr(library, "_read", slow)
    threads = [
        threading.Thread(target=library.update_asset, args=(asset,), kwargs={"archived": True}),
        threading.Thread(target=library.update_asset, args=(asset,), kwargs={"tags": ["keep"]}),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    final = real(library.asset_dir(asset) / "asset.json")
    assert final["archived"] is True and final["tags"] == ["keep"]
    assert not list(library.asset_dir(asset).glob("*.tmp"))


def test_deleted_assets_and_branches_come_back_from_the_trash(tmp_path, monkeypatch):
    """UX-14: the trash lists what deleting moved there (an asset, a branch) and restore puts it back; a place taken
    since, a deleted asset under a branch, or a reused number refuses with its reason."""
    import pytest

    from server.library import ApiError

    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    a = library.create_asset("crate")["id"]
    up = library.new_version(a, "upload")
    library.write_meta(up, None, {}, {"outputs": {}}, provenance="upload")
    cl = library.new_version(a, "clean")
    library.write_meta(cl, up.name, {}, {"outputs": {}})
    re_ = library.new_version(a, "remesh")
    library.write_meta(re_, cl.name, {}, {"outputs": {}})

    assert library.delete_versions(a, cl.name) == [cl.name, re_.name]
    [row] = library.trash()
    assert (
        row["kind"] == "versions"
        and row["asset_id"] == a
        and row["versions"] == [cl.name, re_.name]
    )
    assert row["first"]["step"] == "clean" and row["asset_name"] == "crate"
    library.restore(row["name"])
    assert [m["version"] for m in library.versions(a)] == [
        up.name,
        cl.name,
        re_.name,
    ] and not library.trash()

    library.delete_versions(a, re_.name)
    [branch] = library.trash()
    other = library.new_version(a, "remesh")  # the number is free again and taken
    assert other.name == re_.name
    with pytest.raises(ApiError) as e:
        library.restore(branch["name"])
    assert e.value.code == "exists"
    other.rmdir()

    library.delete_asset(a)
    rows = library.trash()
    whole = next(r for r in rows if r["kind"] == "asset")
    assert whole["asset_id"] == a and whole["versions"] == 2
    with pytest.raises(ApiError) as e:
        library.restore(branch["name"])  # its asset is in the trash too
    assert e.value.code == "asset_gone"
    library.create_asset("crate")  # a new asset took the id
    with pytest.raises(ApiError) as e:
        library.restore(whole["name"])
    assert e.value.code == "exists"
    import shutil

    shutil.rmtree(tmp_path / a)
    library.restore(whole["name"])
    library.restore(branch["name"])
    assert [m["version"] for m in library.versions(a)] == [up.name, cl.name, re_.name]
    with pytest.raises(ApiError) as e:
        library.restore("20260101T000000_nothing")
    assert e.value.code == "not_found"

    # a file open elsewhere halfway through a branch: everything goes back to the trash, a retry then works
    library.delete_versions(a, cl.name)
    [branch] = library.trash()
    real = os.rename

    def locked(s, d):
        if Path(s).name == re_.name and "_trash" in str(s):
            raise PermissionError("in use")
        real(s, d)

    monkeypatch.setattr(library.os, "rename", locked)
    with pytest.raises(ApiError) as e:
        library.restore(branch["name"])
    assert e.value.code == "busy"
    assert [m["version"] for m in library.versions(a)] == [up.name] and library.trash() == [branch]
    monkeypatch.setattr(library.os, "rename", real)
    library.restore(branch["name"])
    assert [m["version"] for m in library.versions(a)] == [up.name, cl.name, re_.name]

    # storage's half-deleted leftover of an archived asset is not offered
    left = tmp_path / "_trash" / f"20260101T000000_{a}_deleted"
    left.mkdir()
    (left / "asset.json").write_text(json.dumps({"id": a, "name": "crate"}), encoding="utf-8")
    assert library.trash() == []


def test_asset_kind(tmp_path, monkeypatch):
    """Research 15: `kind: "2d"` is optional on asset.json, absent for a 3D asset, listed as is."""
    monkeypatch.setenv("EFFIGY_LIBRARY", str(tmp_path))
    flat = library.create_asset("wall tiles", kind="2d")
    solid = library.create_asset("barrel")
    assert flat["kind"] == "2d" and "kind" not in solid
    by_id = {a["id"]: a for a in library.list_assets()}
    assert by_id["wall_tiles"]["kind"] == "2d" and "kind" not in by_id["barrel"]
    with pytest.raises(ApiError):
        library.create_asset("x", kind="4d")
