"""M31 parts: the label merge rules, finding the views, the params, the views op around a faked Blender,
the segment op around a faked GeoSAM2 lift and a faked split, the rename op (M31b), and the torch twin
of GeoSAM2's mode."""

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from steps import parts
from steps._common import StepError


def test_merge_new_parts_take_faces_and_a_name_replaces_its_part():
    labels, found = parts.merge(None, np.array([1, 1, 0, 999, 2, 2]), [(1, "Helmet"), (2, "")])
    assert labels == [1, 1, 0, 0, 2, 2]
    assert found == [
        {"id": 1, "name": "Helmet", "faces": 2},
        {"id": 2, "name": "Part 2", "faces": 2},
    ]
    prev = {"labels": labels, "parts": found}
    # the same name again: the old Helmet goes, the new one takes its faces (one from Part 2 too)
    labels2, found2 = parts.merge(prev, np.array([0, 1, 1, 0, 1, 0]), [(1, "Helmet")])
    assert labels2 == [0, 3, 3, 0, 3, 2] and [p["name"] for p in found2] == ["Part 2", "Helmet"]
    # a new part covering all of an old one: the old one is gone
    labels3, found3 = parts.merge(prev, np.array([0, 0, 0, 0, 1, 1]), [(1, "Belt")])
    assert labels3 == [1, 1, 0, 0, 3, 3] and [p["name"] for p in found3] == ["Helmet", "Belt"]
    assert parts.merge(None, np.zeros(3, int), [(1, "x")]) == ([0, 0, 0], [])  # nothing found
    with pytest.raises(StepError):
        parts.merge(prev, np.zeros(5, int), [(1, "x")])  # another mesh


def test_merge_auto_parts_only_fill_free_faces_and_slivers_go():
    lab = np.zeros(100, int)
    lab[:9] = 5  # an auto part over the helmet (faces 0-7) and one face beside it: a sliver
    lab[10:60] = 6  # an auto part over free faces
    prev = {"labels": [1] * 8 + [0] * 92, "parts": [{"id": 1, "name": "Helmet", "faces": 8}]}
    labels, found = parts.merge(prev, lab, [(5, ""), (6, "")])
    assert found == [
        {"id": 1, "name": "Helmet", "faces": 8},
        {"id": 2, "name": "Part 2", "faces": 50},
    ]
    assert labels[:8] == [1] * 8 and labels[8:10] == [0, 0] and labels[10:60] == [2] * 50
    # a clicked part with the same label does take the faces
    labels, found = parts.merge(prev, lab, [(5, "Hat")])
    assert [p["name"] for p in found] == ["Hat"] and labels[:9] == [2] * 9


def test_views_of_a_views_version_or_a_segment_on_it(tmp_path):
    v1 = tmp_path / "001_parts"
    (v1 / "views").mkdir(parents=True)
    (v1 / "views" / "meta.json").write_text("{}")
    assert parts.views_of(v1) == (v1 / "views", None)
    v2 = tmp_path / "002_parts"
    v2.mkdir()
    pj = {"views": "001_parts", "labels": [0], "parts": []}
    (v2 / "parts.json").write_text(json.dumps(pj))
    assert parts.views_of(v2) == (v1 / "views", pj)
    (tmp_path / "003_bake").mkdir()
    with pytest.raises(StepError) as e:
        parts.views_of(tmp_path / "003_bake")
    assert e.value.code == "missing_input"
    (v2 / "parts.json").write_text(json.dumps(pj | {"views": "009_parts"}))
    with pytest.raises(StepError):
        parts.views_of(v2)


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"view": 12, "full": True},
        {"view": "a", "full": True},
        {"points": [[1, 2, 1]]},  # no name
        {"points": [[1, 2, 3]], "name": "x"},  # a label that is not 0/1
        {"points": [[1, 2]], "name": "x"},
        {"points": [[1, 2, 1]], "name": " body "},  # the rest of the model has that name
        {"points": [[1, 2, 1]], "name": "A{}"},  # a name the export would read as a template
    ],
)
def test_segment_bad_params(tmp_path, params):
    with pytest.raises(StepError) as e:
        parts.run("segment", str(tmp_path), str(tmp_path / "out"), params)
    assert e.value.code == "bad_params"


def test_run_needs_an_input_and_a_known_op(tmp_path):
    with pytest.raises(StepError) as e:
        parts.run("views", None, str(tmp_path), {})
    assert e.value.code == "missing_input"
    with pytest.raises(StepError) as e:
        parts.run("paint", str(tmp_path), str(tmp_path), {})
    assert e.value.code == "bad_params"


def test_views_op_converts_the_renders_and_links_the_mesh(tmp_path, monkeypatch):
    from PIL import Image

    src, out = tmp_path / "090_bake", tmp_path / "100_parts"
    src.mkdir()
    (src / "meta.json").write_text(json.dumps({"outputs": {"mesh": "mesh.glb"}}))
    (src / "mesh.glb").write_bytes(b"glb")

    def fake_blender(op, inputs, outdir, params, timeout=None):
        assert op == "parts_views" and inputs[0] == src / "mesh.glb"
        assert params == {"max_faces": parts.MAX_FACES}
        Path(outdir).mkdir(parents=True)
        for i in range(2):
            Image.new("RGBA", (4, 4), (1, 2, 3, 255)).save(Path(outdir) / f"color_{i:04d}.png")
            Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(Path(outdir) / f"normal_{i:04d}.png")
        (Path(outdir) / "mesh.glb").write_bytes(b"joined")
        (Path(outdir) / "meta.json").write_text("{}")
        (Path(outdir) / "parts_views_job.json").write_text("{}")  # run_blender's, absolute paths
        return {"faces": faces}

    faces = 10

    monkeypatch.setattr(parts, "run_blender", fake_blender)
    res = parts.run("views", str(src), str(out), {})
    assert res["outputs"] == {"mesh": "mesh.glb", "views": "views/meta.json"}
    assert res["metrics"]["views"] == "100_parts" and res["metrics"]["faces"] == 10
    assert sorted(p.name for p in (out / "views").iterdir()) == [
        "color_0000.webp",
        "color_0001.webp",
        "mesh.glb",
        "meta.json",
        "normal_0000.webp",
        "normal_0001.webp",
    ]
    assert Image.open(out / "views" / "normal_0000.webp").mode == "RGBA"
    assert (out / "mesh.glb").read_bytes() == b"joined"
    faces = parts.MAX_FACES + 1  # a full-resolution mesh: simplify first
    with pytest.raises(StepError) as e:
        parts.run("views", str(src), str(tmp_path / "110_parts"), {})
    assert e.value.code == "bad_params" and "simplify" in str(e.value)


@pytest.fixture
def fake_lift(monkeypatch):
    """lift() returns the labels this dict names per call; the split writes the GLB."""
    seen = {"labels": None, "lift": [], "split": []}

    def lift(views_dir, view, points, full, out):
        seen["lift"].append((views_dir.name, view, points, full))
        out.mkdir(parents=True, exist_ok=True)  # _common._call makes it in the real flow
        if points:
            (out / "click.png").write_bytes(b"png")
        return np.array(seen["labels"]), 0.3

    def fake_blender(op, inputs, outdir, params, timeout=None):
        assert (
            op == "parts_split" and inputs[0].name == "mesh.glb" and inputs[1].name == "parts.json"
        )
        pj = json.loads(inputs[1].read_text())
        Path(outdir).mkdir(parents=True)
        (Path(outdir) / "mesh.glb").write_bytes(b"split")
        counts = Counter(pj["labels"])
        seen["split"].append(pj)
        return {"parts": {p["name"]: counts[p["id"]] for p in pj["parts"]} | {"Body": counts[0]}}

    monkeypatch.setattr(parts, "lift", lift)
    monkeypatch.setattr(parts, "run_blender", fake_blender)
    return seen


def test_segment_makes_a_part_and_builds_on_it(tmp_path, fake_lift):
    v1 = tmp_path / "001_parts"
    (v1 / "views").mkdir(parents=True)
    (v1 / "views" / "meta.json").write_text("{}")
    (v1 / "views" / "mesh.glb").write_bytes(b"glb")
    fake_lift["labels"] = [1, 1, 999, 0, 0, 0]
    out = tmp_path / "002_parts"
    res = parts.run(
        "segment", str(v1), str(out), {"view": 3, "points": [[10, 20, 1]], "name": "Helmet"}
    )
    assert fake_lift["lift"] == [("views", 3, [[10.0, 20.0, 1]], False)]
    assert res["outputs"] == {"mesh": "mesh.glb", "parts": "parts.json", "click": "click.png"}
    assert res["metrics"]["new"] == ["Helmet"] and res["metrics"]["views"] == "001_parts"
    assert res["metrics"]["peak_vram_gb"] == 0.3
    assert res["metrics"]["parts"] == {"Helmet": 2, "Body": 4}
    assert "VAST-AI/GeoSAM2" in res["licenses"] and (out / "mesh.glb").read_bytes() == b"split"
    pj = json.loads((out / "parts.json").read_text())
    assert pj["views"] == "001_parts" and pj["labels"] == [1, 1, 0, 0, 0, 0]
    # the full decomposition on top: the helmet stays, the rest becomes parts by size
    fake_lift["labels"] = [1, 1, 2, 2, 2, 7]
    res2 = parts.run("segment", str(out), str(tmp_path / "003_parts"), {"full": True})
    assert fake_lift["lift"][-1] == ("views", 0, [], True)
    assert res2["metrics"]["new"] == ["Part 2", "Part 3"] and "click" not in res2["outputs"]
    assert res2["metrics"]["parts"] == {"Helmet": 2, "Part 2": 3, "Part 3": 1, "Body": 0}
    # nothing at the clicks: an error, not an empty version
    fake_lift["labels"] = [0, 0, 0, 0, 0, 0]
    with pytest.raises(StepError) as e:
        parts.run(
            "segment", str(out), str(tmp_path / "004_parts"), {"points": [[1, 1, 1]], "name": "x"}
        )
    assert e.value.code == "failed"


def test_rename_writes_the_names_into_parts_json_and_the_glb(tmp_path):
    """M31b: new names without the GPU; the GLB's binary chunk stays byte for byte."""
    import trimesh

    v = tmp_path / "003_parts"
    v.mkdir()
    scene = trimesh.Scene()
    for name in ("Part 1", "Part 2", "Body"):
        scene.add_geometry(trimesh.creation.box(), geom_name=name, node_name=name)
    scene.export(v / "mesh.glb")
    pj = {
        "views": "001_parts",
        "labels": [1, 1, 2, 0, 0, 0],
        "parts": [{"id": 1, "name": "Part 1", "faces": 2}, {"id": 2, "name": "Part 2", "faces": 1}],
    }
    (v / "parts.json").write_text(json.dumps(pj))
    out = tmp_path / "004_parts"
    out.mkdir()
    res = parts.run(
        "rename", str(v), str(out), {"names": {"Part 1": " Helmet ", "Part 2": "Part 2"}}
    )
    assert res["outputs"] == {"mesh": "mesh.glb", "parts": "parts.json"}
    assert res["metrics"]["parts"] == {"Helmet": 2, "Part 2": 1, "Body": 3}
    assert res["metrics"]["views"] == "001_parts"
    new = json.loads((out / "parts.json").read_text())
    assert new["labels"] == pj["labels"] and [p["name"] for p in new["parts"]] == [
        "Helmet",
        "Part 2",
    ]
    got = trimesh.load(out / "mesh.glb")
    assert sorted(got.graph.nodes_geometry) == ["Body", "Helmet", "Part 2"]
    glb, old = (out / "mesh.glb").read_bytes(), (v / "mesh.glb").read_bytes()
    n, m = int.from_bytes(glb[12:16], "little"), int.from_bytes(old[12:16], "little")
    assert glb[20 + n :] == old[20 + m :] and n % 4 == 0
    assert int.from_bytes(glb[8:12], "little") == len(glb)
    # a rename on a rename builds on it, like a segment does
    (tmp_path / "001_parts" / "views").mkdir(parents=True)
    (tmp_path / "001_parts" / "views" / "meta.json").write_text("{}")
    assert parts.views_of(out)[1]["parts"] == new["parts"]


@pytest.mark.parametrize(
    "names",
    [
        None,
        {},
        {"Part 9": "x"},  # no such part
        {"Body": "Torso"},  # the rest of the model is not a part
        {"Part 1": " "},
        {"Part 1": "body"},
        {"Part 1": "Part 2"},  # a name twice
        {"Part 1": None},
        {"Part 1": "Part 1"},  # nothing changes
        {"Part 1": "Shield {old}"},  # braces: blender_ops/export fills "{}" templates
        {"Part 1": "Rock_LOD1"},  # read as an LOD of "Rock"
        {"Part 1": "a/b"},
        {"Part 1": "x" * 57},  # "UCX_<name>_00" past Blender's 63 bytes
    ],
)
def test_rename_bad_names(tmp_path, names):
    pj = {
        "views": "001_parts",
        "labels": [1, 2],
        "parts": [{"id": 1, "name": "Part 1", "faces": 1}, {"id": 2, "name": "Part 2", "faces": 1}],
    }
    (tmp_path / "parts.json").write_text(json.dumps(pj))
    with pytest.raises(StepError) as e:
        parts.run("rename", str(tmp_path), str(tmp_path / "out"), {"names": names})
    assert e.value.code == "bad_params"
    (tmp_path / "parts.json").unlink()
    with pytest.raises(StepError) as e:
        parts.run("rename", str(tmp_path), str(tmp_path / "out"), {"names": names})
    assert e.value.code == "missing_input"


def test_mode_twin_matches_the_cpp_rule():
    torch = pytest.importorskip("torch")
    from engine.geosam2.mode_ext import mode_except_negative_one

    rng = np.random.default_rng(0)
    rows = rng.integers(-1, 4, size=(2000, 7))
    rows[0] = 0  # all zero: 0
    rows[1] = [0, 0, 0, 0, 0, 0, 3]  # 0 wins but another label exists: that one
    got = mode_except_negative_one(torch.from_numpy(rows).to(torch.int32)).tolist()
    for row, g in zip(rows, got):
        top = Counter(row.tolist()).most_common()
        pick = top[1:] if top[0][0] == 0 and len(top) > 1 else top  # 0 only when alone
        if len(pick) > 1 and pick[0][1] == pick[1][1]:
            continue  # a tie: the C++ sort leaves the order unspecified
        assert g == pick[0][0], (row, g, pick)


def test_enclosed_background_is_a_hole_through_the_model(tmp_path, monkeypatch):
    """mesh-gates: background inside a view's silhouette (a ring's middle) is a hole through the model from
    there; a disc has none. The views op reports the views that show one."""
    import numpy as np
    from PIL import Image

    y, x = np.mgrid[:64, :64]
    r = np.hypot(x - 32, y - 32)
    assert parts.enclosed_background(r < 20) == 0
    ring = (r < 20) & (r > 8)
    assert parts.enclosed_background(ring) == int((r <= 8).sum())

    src, out = tmp_path / "090_bake", tmp_path / "100_parts"
    src.mkdir()
    (src / "meta.json").write_text(json.dumps({"outputs": {"mesh": "mesh.glb"}}))
    (src / "mesh.glb").write_bytes(b"glb")

    def fake_blender(op, inputs, outdir, params, timeout=None):
        Path(outdir).mkdir(parents=True)
        for i, opaque in enumerate((r < 20, ring)):
            rgba = np.zeros((64, 64, 4), np.uint8)
            rgba[opaque] = (1, 2, 3, 255)
            Image.fromarray(rgba, "RGBA").save(Path(outdir) / f"color_{i:04d}.png")
        (Path(outdir) / "mesh.glb").write_bytes(b"joined")
        (Path(outdir) / "meta.json").write_text("{}")
        return {"faces": 10}

    monkeypatch.setattr(parts, "run_blender", fake_blender)
    res = parts.run("views", str(src), str(out), {})
    assert res["metrics"]["holes"] == {1: int((r <= 8).sum())}
