"""Sprite frames from the 3D character (research 15 §5.4, M52): its clips rendered side-on in headless Blender
(blender_ops/render_sprites.py), orthographic, no anti-aliasing, one pixels-per-metre for the whole asset, then
packed into a sheet that pixelize, the viewer and the 2D exports read. LIGHT: Blender on the CPU, no model.

Input: an animated version (`rigged_anim` + `clips`: anim, anim_edit, an imported animated model), or a still
`mesh` (a prop: one frame per yaw). Params:
  clips: [names] (default: every clip of the version)
  yaws: [degrees] (default [90]: facing right; 270 faces left, 0 shows the front, 180 the back)
  height_px: the standing height in pixels (default: the asset's earlier sprites' scale, else 104; given, it
    sets a new scale for this and every later run)
  cell: the least cell in pixels (default 128; grown so every frame fits), pitch_deg: 0-45 (default 12)
  fps: 1-30 (default 12), shading: "textured" (default, studio light) | "flat" (the texture unlit)
  supersample: 1 (default) | 2 (rendered at twice the size: pixelize with scale 2 brings it down)
Outputs: frames/<clip>_<yaw>_<NNNN>.png, sheet.png, sheet.json (Aseprite json-array, one tag per clip and yaw,
the durations), camera.json {ppm, height_px, pitch_deg, cell, supersample}, preview.png (whole pixels).
"""

import json
import re
import time
from pathlib import Path

from PIL import Image

from steps import _sheet
from steps._blender import BlenderError, run_blender
from steps._common import StepError, main, progress

SHADINGS = ("textured", "flat")
# a move a game plays once and waits out (its `animation_finished`), though the pack's clip ends in its start pose: an
# attack, a hit, a fall, a jump's start or landing, a throw (the Mesh2Motion pack's names; research 15 §2's brawler list)
ONCE = re.compile(
    r"jab|punch|hook|kick|attack|sword_regular|spell|hit_|death|throw|pick ?up|jump_start|jump_land|land_|lay ?to|"
    r"roll|dodge|melee|uppercut|elbow|grab",
    re.IGNORECASE,
)


def _params(params: dict) -> dict:
    p = {
        "clips": params.get("clips"),
        "yaws": params.get("yaws", [90]),
        "height_px": params.get("height_px"),
        "cell": params.get("cell", 128),
        "pitch_deg": params.get("pitch_deg", 12),
        "fps": params.get("fps", 12),
        "shading": params.get("shading", "textured"),
        "supersample": params.get("supersample", 1),
    }
    num = (int, float)
    ok = (
        (
            p["clips"] is None
            or (
                isinstance(p["clips"], list)
                and p["clips"]
                and all(isinstance(c, str) for c in p["clips"])
            )
        )
        and isinstance(p["yaws"], list)
        and 1 <= len(p["yaws"]) <= 8
        and all(type(y) is int and 0 <= y < 360 for y in p["yaws"])  # not a bool
        and len(set(p["yaws"])) == len(p["yaws"])
        and (
            p["height_px"] is None
            or (isinstance(p["height_px"], int) and 8 <= p["height_px"] <= 1024)
        )
        and isinstance(p["cell"], int)
        and 16 <= p["cell"] <= 1024
        and isinstance(p["pitch_deg"], num)
        and 0 <= p["pitch_deg"] <= 45
        and isinstance(p["fps"], num)
        and 1 <= p["fps"] <= 30
        and p["shading"] in SHADINGS
        and p["supersample"] in (1, 2)
    )
    if not ok:
        raise StepError("bad_params", f"see the sprites docstring: {params}")
    return p


def _scale(asset_dir: Path) -> dict | None:
    """The asset's newest earlier sprites scale (camera.json): one pixels-per-metre for every run."""
    found = sorted(asset_dir.glob("*_sprites/camera.json"))
    if not found:
        return None
    try:
        cam = json.loads(found[-1].read_text(encoding="utf-8"))
        if float(cam["ppm"]) > 0:
            return cam
    except (OSError, ValueError, KeyError, TypeError):
        pass
    raise StepError("failed", f"{found[-1]}: no scale in it; give height_px to set a new one")


def run(op, in_dir, out_dir, params):
    if op != "run":
        raise StepError("bad_params", f"op {op!r}: only run")
    if not in_dir:
        raise StepError("missing_input", "sprites needs an animated or a still model version")
    p = _params(params)
    src, out = Path(in_dir), Path(out_dir)
    meta = json.loads((src / "meta.json").read_text(encoding="utf-8"))
    outs = meta.get("outputs", {})
    glb = outs.get("rigged_anim") or outs.get("mesh")
    if not glb or not glb.endswith(".glb"):
        raise StepError(
            "missing_input", f"{meta['version']}: no animated model (rigged_anim) or model (mesh)"
        )
    seconds = 0.0
    if "rigged_anim" in outs and "clips" in outs:
        listed = json.loads((src / outs["clips"]).read_text(encoding="utf-8"))["clips"]
        have = [c["name"] for c in listed]
        if unknown := [c for c in p["clips"] or [] if c not in have]:
            raise StepError("bad_params", f"no clip {unknown} in {meta['version']}: {have}")
        clips = p["clips"] or have
        seconds = sum(float(c.get("seconds") or 2) for c in listed if c["name"] in clips)
    else:
        clips = []  # a still model: one frame per yaw
    # the frames to expect, for the sheet's size and the watchdog: a sheet past 8192 x 8192 px is refused
    frames_est = max(1, round(seconds * p["fps"])) * len(p["yaws"])
    side = p["cell"] * p["supersample"]
    if frames_est * side * side > 8192 * 8192:
        raise StepError(
            "bad_params",
            f"about {frames_est} frames of {side} px: more than one 8192 px sheet holds; fewer clips, views or fps",
        )
    earlier = None if p["height_px"] else _scale(src.parent)
    height_px = p["height_px"] or (earlier or {}).get("height_px", 104)
    t0 = time.time()
    progress(
        0.05,
        f"rendering {len(clips) or 1} clip{'s' if len(clips) != 1 else ''} × {len(p['yaws'])} view{'s' if len(p['yaws']) > 1 else ''}",
    )
    job = {
        "clips": clips,
        "yaws": p["yaws"],
        "fps": p["fps"],
        "pitch_deg": p["pitch_deg"],
        "cell": p["cell"],
        "shading": p["shading"],
        "supersample": p["supersample"],
        "height_px": height_px,
        **({"ppm": earlier["ppm"]} if earlier else {}),
    }
    try:
        r = run_blender(
            "render_sprites",
            [src / glb],
            out,
            job,
            timeout=120 + 2 * frames_est * p["supersample"] ** 2,  # 28 ms a frame measured (m52.md)
        )
    except BlenderError as e:
        raise StepError("failed", str(e)) from None
    progress(0.85, "the sheet")
    frames = [
        (Path(f["file"]).stem, Image.open(out / f["file"]).convert("RGBA")) for f in r["frames"]
    ]
    tags, start = [], 0
    for i, f in enumerate(r["frames"]):  # one tag per clip and yaw, in render order
        last = i + 1 == len(r["frames"]) or (
            r["frames"][i + 1]["clip"],
            r["frames"][i + 1]["yaw"],
        ) != (f["clip"], f["yaw"])
        if last:
            name = f["clip"] if len(p["yaws"]) == 1 else f"{f['clip']}_{f['yaw']:03d}"
            loops = r.get("loops", {}).get(f["clip"], True) and not ONCE.search(f["clip"])
            tags.append(  # Aseprite's repeat "1": a move that plays once (the Godot export's loop off)
                {
                    "name": name,
                    "from": start,
                    "to": i,
                    "direction": "forward",
                    "repeat": "0" if loops else "1",
                    "color": "#000000ff",
                }
            )
            start = i + 1
    sheet, data = _sheet.pack(frames, tags, [f["duration"] for f in r["frames"]])
    sheet.save(out / "sheet.png")
    (out / "sheet.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    _sheet.contact(sheet).save(out / "preview.png")
    camera = {
        "ppm": r["ppm"],
        "height_px": height_px,
        "height_m": round(r["height_m"], 4),
        "pitch_deg": p["pitch_deg"],
        "cell": r["cell"],
        "supersample": p["supersample"],
    }
    (out / "camera.json").write_text(json.dumps(camera, indent=2), encoding="utf-8")
    (out / "render_sprites_job.json").unlink(missing_ok=True)
    return {
        "outputs": {
            "frames": "frames",
            "sheet": "sheet.png",
            "data": "sheet.json",
            "camera": "camera.json",
            "preview": "preview.png",
        },
        "metrics": {
            "frames": len(frames),
            "clips": r["clips"],
            "yaws": p["yaws"],
            "cell": r["cell"],
            "height_px": height_px,
            "supersample": p["supersample"],
            "scale_from": "earlier" if earlier else "height_px",
            "height_px_now": round(r["ppm"] * r["height_m"]),  # this mesh at the kept scale
            "seconds": round(time.time() - t0, 1),
        },
    }


if __name__ == "__main__":
    main(run)
