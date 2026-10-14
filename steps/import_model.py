"""Import a model (IMPLEMENTATION.md M39): an `upload` version holding a model file → mesh.glb, or, when the
file's skeleton is one the app knows, rigged.glb + skeleton.json + qa.json (+ rigged_anim.glb + clips.json).

Input: an upload version (output `model`, else a `.glb` `mesh`). params: {"scale": 1 (0 < s <= 1000, on top
of the file's own units), "rig": true (false: a still mesh even with a known skeleton)}.
blender_ops/import_model does the work; this step hands it the known skeletons, adds what needs numpy
(a creature's yaw) and judges the skin with rig_qa. Not named `import`: a Python keyword.
"""

import json
import shutil
import urllib.parse
from pathlib import Path

import numpy as np

from steps import _mesh, _rig, _templates
from steps._blender import BlenderError, run_blender
from steps._common import StepError, main, progress
from steps.rig_skin import checklist


def _check_gltf(model: Path) -> None:
    """A .gltf names its .bin and textures beside it: a lone file can't load (upload the folder as a .zip)."""
    try:
        doc = json.loads(model.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return  # not JSON: Blender's own message says so
    uris = [x["uri"] for k in ("buffers", "images") for x in doc.get(k, []) if "uri" in x]
    for uri in uris:
        if not uri.startswith("data:") and not (model.parent / urllib.parse.unquote(uri)).is_file():
            raise StepError("missing_input", f"the .gltf needs {uri}: upload its folder as a .zip")


def _yaw(template: str, joints: list[dict]) -> float:
    """The turn about +Y (degrees, [0, 360), 0.1° steps) that takes the template's joint heads onto the
    imported ones, as rig_fit made it: the lean (about -45..45) and a quarter turn, the template then
    stretched along the body's own axes (_templates.fit). The turn with the least left over after that
    stretch (x and z scaled apart, above 0)."""
    head = {b["name"]: b["head"] for b in _templates.bones(template)}
    # the limbs only: rig_fit bends the head and the tail to the mesh's own, off the template's turn
    joints = [j for j in joints if j["name"] in _templates.limbs(template)]
    h = np.array([head[j["name"]] for j in joints])[:, [0, 2]]
    q = np.array([j["position"] for j in joints])[:, [0, 2]]
    h, q = h - h.mean(0), q - q.mean(0)

    def turn(a):  # _templates._yaw on (x, z): a column vector turned
        c, s = np.cos(np.radians(a)), np.sin(np.radians(a))
        return np.array([[c, s], [-s, c]])

    def left(y):
        base = (y + 45) % 90 - 45
        a, b = (
            q @ turn(base),
            h @ turn(y - base).T,
        )  # the mesh turned back by the lean; the template by the quarter
        k = (a * b).sum(0) / (b * b).sum(0)
        return ((a - np.maximum(k, 0) * b) ** 2).sum()

    return min((round(y * 0.1, 1) for y in range(3600)), key=lambda y: left(y))


def run(op, in_dir, out_dir, params):
    src, out = Path(in_dir or ""), Path(out_dir)
    if set(params) - {"scale", "rig"}:
        raise StepError("bad_params", f"unknown params {sorted(set(params) - {'scale', 'rig'})}")
    scale, rig = params.get("scale", 1), params.get("rig", True)
    if (
        isinstance(scale, bool)
        or not isinstance(scale, (int, float))
        or not 0 < scale <= 1000
        or not isinstance(rig, bool)
    ):
        raise StepError("bad_params", "scale: a number above 0 and up to 1000; rig: true or false")
    if not in_dir or not (src / "meta.json").is_file():
        raise StepError("missing_input", "import_model needs an upload version")
    outputs = json.loads((src / "meta.json").read_text(encoding="utf-8")).get("outputs", {})
    rel = outputs.get("model") or outputs.get("mesh")
    if not rel or not (src / rel).is_file():
        raise StepError("missing_input", f"{src.name} holds no model file")
    model = src / rel
    if model.suffix.lower() == ".gltf":
        _check_gltf(model)
    known = {_templates.HUMAN: [list(j) for j in _rig.template()]} | {
        t: [[b["name"], b["parent"]] for b in _templates.bones(t)] for t in _templates.TEMPLATES
    }
    progress(0.1, f"importing {model.name}")
    try:
        res = run_blender(
            "import_model",
            [model],
            out / "_import",
            {"scale": scale, "rig": rig, "templates": known},
            timeout=900,
        )
    except BlenderError as e:
        raise StepError("failed", str(e)) from e
    rep = res["report"]
    for f in res["outputs"].values():
        shutil.move(out / "_import" / f, out / f)
    shutil.rmtree(out / "_import", ignore_errors=True)
    result_outputs = dict(res["outputs"])
    clips = rep.pop("clip_list", [])
    joints = rep.pop("joints", None)
    if joints is not None:
        t = rep["skeleton"]
        order = {n: i for i, (n, _) in enumerate(known[t])}
        joints.sort(key=lambda j: order[j["name"]])
        skel = {"template": t, "frame": "gltf_yup_m"}
        if t != _templates.HUMAN:
            tb = {b["name"]: b for b in _templates.bones(t)}
            for j in joints:
                kids = [c for c in tb.values() if c["parent"] == j["name"]]
                to = next(
                    (
                        c["name"]
                        for c in kids
                        if np.allclose(c["head"], tb[j["name"]]["tail"], atol=1e-4)
                    ),
                    None,
                )
                if to:
                    j["to"] = to
            skel |= {"yaw": _yaw(t, joints), "sides": list(_templates.TEMPLATES[t][1])}
        else:
            for j in joints:
                del j["tail"]
            # the hands' twist, as rig_fit writes it: the retarget's palm frame
            v = _mesh.read_glb(out / "rigged.glb")[0]
            palms = _rig.palm_normals({j["name"]: np.asarray(j["position"]) for j in joints}, v)
            for j in joints:
                n = (
                    palms.get(j["name"].removesuffix("Hand"))
                    if j["name"].endswith("Hand")
                    else None
                )
                if n is not None:
                    j["twist"] = np.round(n, 5).tolist()
        skel["joints"] = joints
        (out / "skeleton.json").write_text(json.dumps(skel, indent=1), encoding="utf-8")
        progress(0.7, "judging the skin")
        sym = {k: skel[k] for k in ("sides", "yaw") if k in skel}
        try:
            report = run_blender("rig_qa", [out / "rigged.glb"], out / "_qa", sym, timeout=600)[
                "report"
            ]
        except BlenderError as e:
            raise StepError("failed", str(e)) from e
        shutil.rmtree(out / "_qa", ignore_errors=True)
        qa = {
            "picked": "import",
            "items": checklist(report),
            "report": report,
            "engines": {"import": report},
        }
        (out / "qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
        result_outputs |= {"skeleton": "skeleton.json", "qa": "qa.json"}
        rep |= {"template": t, "engine": "import"}
        if clips:
            clips_json = {"clips": clips, "fps": 24, "missing": [], "height_scale": 1}
            (out / "clips.json").write_text(json.dumps(clips_json, indent=2), encoding="utf-8")
            result_outputs["clips"] = "clips.json"
    # rigged_anim first: export takes the first .glb
    first = [k for k in ("rigged_anim", "rigged", "mesh") if k in result_outputs]
    ordered = {
        k: result_outputs[k] for k in (*first, "skeleton", "clips", "qa") if k in result_outputs
    }
    return {"outputs": ordered, "metrics": rep}


if __name__ == "__main__":
    main(run)
