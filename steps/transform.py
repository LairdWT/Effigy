"""Turn, scale and place a model without Blender (agent finding 11, 2026-10-13: every Blender pass of its session
was a scale, a turn or a stand-up, none needed the window, each needed a running Blender).

Input: a version with a still mesh (`.glb`: one mesh, no skin; a rigged model is Blender's or rig_fit's).
params (all optional, applied in this order, in the library frame, Y up):
  level: true            stand it upright (clean's level_transform: its floor levelled, a post on its shaft)
  square: true           turned square to the axes by the smallest turn about Y (its plan's rectangle), the side the
                         picture's camera saw, its front, then facing +Z
  face: "+z"|"-z"|"+x"|"-x"  the front (the camera's side, +Z) turned to face that axis: "-z" for a street side
                         (findings 22: the angle sums an agent worked out outside Effigy, now one param each)
  rotate_deg: [x, y, z]  turns about X, then Y, then Z (degrees; +Y turns +Z towards +X)
  scale: s | [x, y, z]   a scale, uniform or per axis (after the turn: fitting a brief's width, depth and height)
  height_m: h            or the uniform scale that makes it h metres tall
  ground: true           its base centre onto the origin (default true)
  translate_m: [x, y, z] then moved by this
Outputs: each `.glb` rewritten (positions, normals and tangents; UVs, materials and textures as they were) and the
pictures copied; reports, a volume, quads.obj are left out (`metrics.dropped`): bake finds the generator's volume up
the chain and follows `metrics.transform`, the 4×4 back to the parent's frame, as for clean. A version with a
skeleton, markers or parts is refused: they would no longer fit the moved mesh (move it before fitting them)."""

import json
import shutil
from pathlib import Path

import numpy as np

from steps import _glb
from steps._common import StepError, main, progress
from steps._mesh import read_glb

PICTURES = (".png", ".jpg")
FACES = {
    "+z": (0, 0, 1),
    "-z": (0, 0, -1),
    "+x": (1, 0, 0),
    "-x": (-1, 0, 0),
}  # where the front turns to  # textures: a move leaves UV space as it is
FITTED = ("skeleton", "markers", "parts")  # data placed on the mesh: stale once it moves


def _rot(deg) -> np.ndarray:
    """X, then Y, then Z, for row vectors (`v @ R`)."""
    x, y, z = np.radians(np.asarray(deg, float))
    rx = np.array([[1, 0, 0], [0, np.cos(x), np.sin(x)], [0, -np.sin(x), np.cos(x)]])
    ry = np.array([[np.cos(y), 0, -np.sin(y)], [0, 1, 0], [np.sin(y), 0, np.cos(y)]])
    rz = np.array([[np.cos(z), np.sin(z), 0], [-np.sin(z), np.cos(z), 0], [0, 0, 1]])
    return rx @ ry @ rz


def _vec(params: dict, key: str, default):
    x = params.get(key, default)
    if not (
        isinstance(x, list)
        and len(x) == 3
        and all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in x)
    ):
        raise StepError("bad_params", f"{key}: three numbers [x, y, z]")
    return np.asarray(x, float)


def run(op, in_dir, out_dir, params):
    if op != "run":
        raise StepError("bad_params", f"op {op!r}: only run")
    if not in_dir:
        raise StepError("missing_input", "transform needs a version with a mesh")
    src, out = Path(in_dir), Path(out_dir)
    meta = json.loads((src / "meta.json").read_text(encoding="utf-8"))
    glbs = {k: f for k, f in meta["outputs"].items() if f.endswith(".glb")}
    if not glbs:
        raise StepError("missing_input", f"{meta['version']} has no .glb")
    if fitted := [k for k in FITTED if k in meta["outputs"]]:
        raise StepError(
            "bad_params",
            f"{meta['version']} has a {', '.join(fitted)} placed on the mesh, which would no longer fit it: move the "
            "model before fitting them, or in Blender",
        )
    rotate, shift = _vec(params, "rotate_deg", [0, 0, 0]), _vec(params, "translate_m", [0, 0, 0])
    scale, height = params.get("scale"), params.get("height_m")
    positive = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool) and x > 0
    per_axis = scale if isinstance(scale, list) else [scale] * 3
    if scale is not None and not (len(per_axis) == 3 and all(map(positive, per_axis))):
        raise StepError("bad_params", "scale: a positive number, or three of them [x, y, z]")
    if height is not None and (not positive(height) or scale is not None):
        raise StepError("bad_params", "height_m: a positive number, and not with scale")
    flags = (("level", False), ("ground", True), ("square", False))
    if not all(isinstance(params.get(k, d), bool) for k, d in flags):
        raise StepError("bad_params", "level, square and ground: true or false")
    face = params.get("face")
    if face is not None and face not in FACES:
        raise StepError("bad_params", f"face: one of {sorted(FACES)}")

    progress(0.2, "working out the move")
    v, f = read_glb(src / next(iter(glbs.values())))[:2]  # the first mesh decides for all
    v = np.asarray(v, float)
    m = np.eye(3)
    if params.get("level", False):
        from steps.clean import level_transform

        m, _ = level_transform(v, np.asarray(f))
    if params.get("square", False):
        from scipy.spatial import QhullError

        from steps._templates import _yaw
        from steps.clean import _square

        try:
            if (a := _square((v @ m)[:, [0, 2]])) is not None and abs(a) >= 0.5:
                m = m @ _yaw(-a)
                if (
                    abs(_square((v @ m)[:, [0, 2]]) or 0.0) > 1
                ):  # turned the wrong way round: the other
                    m = m @ _yaw(2 * a)
        except QhullError:
            pass
    if face:  # the turn about Y that takes the front (+Z) to the named axis
        from steps._templates import _yaw

        m = m @ next(
            _yaw(d)
            for d in (0, 90, 180, -90)
            if np.allclose(np.array([0.0, 0, 1]) @ _yaw(d), FACES[face], atol=1e-9)
        )
    m = m @ _rot(rotate)
    w = v @ m
    s = np.broadcast_to(
        np.asarray(
            scale if scale is not None else (height / np.ptp(w[:, 1]) if height else 1.0), float
        ),
        3,
    )
    w = w * s
    lo, hi = w.min(0), w.max(0)
    base = np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])
    b = (-base if params.get("ground", True) else np.zeros(3)) + shift

    progress(0.5, "writing the moved mesh")
    for name in glbs.values():
        if why := _glb.rotate(src / name, out / name, m, b, scale=s):
            raise StepError(
                "bad_params", f"{meta['version']}: {name} cannot be moved here: {why} (use Blender)"
            )
    outputs, dropped = dict(glbs), []
    for k, name in meta["outputs"].items():
        if k in outputs:
            continue
        if name.lower().endswith(PICTURES) and (src / name).is_file():
            (out / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / name, out / name)
            outputs[k] = name
        else:
            dropped.append(name)
    t = np.eye(4)  # x' = A x + b, the convention of clean's metrics.transform (bake composes it)
    t[:3, :3], t[:3, 3] = np.diag(s) @ m.T, b
    w = w + b
    return {
        "outputs": outputs,
        "metrics": {
            "transform": t.round(9).tolist(),
            "size_m": np.ptp(w, 0).round(4).tolist(),
            "scale": [round(float(x), 6) for x in s]
            if not np.allclose(s, s[0])
            else round(float(s[0]), 6),
            "levelled": bool(params.get("level", False)) and not np.allclose(m, _rot(rotate)),
            "dropped": dropped,  # reports and data files the move would make stale
        },
    }


if __name__ == "__main__":
    main(run)
