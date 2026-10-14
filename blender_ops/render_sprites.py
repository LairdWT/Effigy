# SPDX-License-Identifier: GPL-3.0-or-later
"""Sprite frames of a rigged, animated model (or a still one turned) for the 2D track (research 15 §5.4, M52).

in: [rigged_anim.glb or mesh.glb]; params: {"clips": [names] (default: every clip), "fps": 12, "yaws": [90],
"pitch_deg": 12, "ppm": pixels per metre (default from height_px and the rest pose's height), "height_px": 104,
"cell": 128 (the least; grown to fit every frame), "shading": "textured" | "flat", "supersample": 1 | 2}
→ frames/<clip>_<yaw>_<NNNN>.png (the clip's name made safe for a file) + result.json {frames: [{file, clip, yaw,
duration}], cell, ppm, height_m}.

Orthographic, no anti-aliasing, a transparent background, one pixels-per-metre for every frame. Yaw 0 shows the
front, 90 the model facing right (the camera on its right side), 180 its back, 270 facing left. A clip plays in
place: the camera follows the straight drift of the bone that travels (the root, or the hips under a still root)
from the first frame to the last, a walk's stride, so the sway and the bob stay. It follows exactly, not in whole
pixels: the frame holds nothing but the model, so the body keeps one sub-pixel place and its edges do not crawl
(snapping would add up to half a pixel of jitter). The ground under the drift sits a few pixels above the cell's
bottom edge, on one row for every clip."""

import re
import sys
from math import ceil, cos, floor, radians, sin
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, job, load

j = job()
p = j["params"]
out = Path(j["out_dir"])
(out / "frames").mkdir(parents=True, exist_ok=True)
fps, yaws, pitch = (
    float(p.get("fps", 12)),
    [int(y) for y in p.get("yaws", [90])],
    radians(p.get("pitch_deg", 12)),
)
ss = int(p.get("supersample", 1))
bpy.ops.wm.read_factory_settings(use_empty=True)
objs = load(j["in"][0])
scene = bpy.context.scene
meshes = [o for o in objs if o.type == "MESH"]
arm = next((o for o in objs if o.type == "ARMATURE"), None)
assert meshes, f"no mesh in {j['in'][0]}"
scene_fps = scene.render.fps / scene.render.fps_base


def action(name: str):
    return next(
        (a for a in bpy.data.actions if a.name == name or a.name.endswith("|" + name)), None
    )


def clip_name(a) -> str:
    return a.name.split("|")[-1]


def use(act) -> None:
    """The glTF importer parks clips in NLA tracks and leaves one action on top: mute them, set ours."""
    for o in [o for o in scene.objects if o.animation_data]:
        ad = o.animation_data
        for t in ad.nla_tracks:
            t.mute = True
        ad.action = act
        if act is not None and act.slots:
            ad.action_slot = act.slots[0]


# the last pose within 0.2 % of the height of the first, on average: the clip loops. Measured (M53): the pack's Idle,
# Walk and Jog end 0.00-0.02 % from where they began; Kimodo's punch 0.8 %, its kick 3.2 %, "hide behind a wall" 31 %
LOOP = 0.002


def goto(f: float) -> None:
    whole = floor(f)
    scene.frame_set(whole, subframe=f - whole)


def points() -> np.ndarray:
    """Every vertex of the evaluated (posed) meshes in world space: the exact extent, not a box's corners."""
    dg = bpy.context.evaluated_depsgraph_get()
    out_ = []
    for o in meshes:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get("co", co)
        m = np.array(ev.matrix_world)
        out_.append(co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3])
        ev.to_mesh_clear()
    return np.concatenate(out_)


# the standing height in the rest pose: the scale every clip and every later run shares
if arm:
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
v = points()
lo, hi = v.min(0), v.max(0)
height_m, ground = float(hi[2] - lo[2]), float(lo[2])
if height_m < 0.05 * float(
    (hi - lo).max()
):  # a flat model (a sign lying down, a decal): its largest side
    height_m = float((hi - lo).max())
assert height_m > 1e-6, f"{j['in'][0]} has no size"
if arm:
    arm.data.pose_position = "POSE"
ppm = float(p.get("ppm") or p.get("height_px", 104) / height_m)

# what to render: (clip, its action, frames in the scene's time, its range); a still model is one "still" frame
plan = []
if arm and bpy.data.actions:
    want = p.get("clips") or [clip_name(a) for a in bpy.data.actions]
    missing = [c for c in want if action(c) is None]
    assert not missing, f"no clip {missing} in {[clip_name(a) for a in bpy.data.actions]}"
    for c in want:
        act = action(c)
        f0, f1 = act.frame_range
        n = max(1, round((f1 - f0) / scene_fps * fps))  # the end is the start again: left out
        plan.append((c, act, [f0 + k * scene_fps / fps for k in range(n)], (f0, f1)))
else:
    plan.append(("still", None, [float(scene.frame_current)], None))

# file stems: the clip's name made safe (a prompt-named motion, a "Walk/Run"), unique
stems, seen = {}, set()
for c, *_ in plan:
    s = re.sub(r"[^A-Za-z0-9 ._-]+", "_", c).strip(" .") or "clip"
    while s in seen:
        s += "_"
    stems[c] = s
    seen.add(s)


def view(yaw: int):
    """The camera's direction (from the model to it), its screen right and screen up for a yaw."""
    t = radians(yaw)
    d = Vector((-sin(t) * cos(pitch), -cos(t) * cos(pitch), sin(pitch)))
    right = (-d).cross(Vector((0, 0, 1))).normalized()
    return d, right, right.cross(-d).normalized()


# the bones a clip may travel by: the root and, under it, the bones that have children of their own (the hips)
movers = []
if arm:
    for b in arm.pose.bones:
        if b.parent is None and b.children:
            movers += [b] + [c for c in b.children if c.children]


def flat(b) -> Vector:
    w = arm.matrix_world @ b.head
    return Vector((w.x, w.y, 0.0))


# the drift: the travelling bone's straight line from the clip's first frame to its last, on the ground plane
drifts = {}
for c, act, frames, rng in plan:
    use(act)
    if act is None or not movers:
        drifts[c] = lambda f: Vector((0.0, 0.0, 0.0))
        continue
    goto(rng[0])
    a = {b.name: flat(b) for b in movers}
    goto(rng[1])
    z = {b.name: flat(b) for b in movers}
    best = max(movers, key=lambda b: (z[b.name] - a[b.name]).length)
    a0, z0 = a[best.name], z[best.name]
    drifts[c] = lambda f, a0=a0, z0=z0, rng=rng: a0.lerp(
        z0, (f - rng[0]) / max(rng[1] - rng[0], 1e-6)
    )

# a loop ends where it began: the last pose against the first, the drift taken out, as a share of the height (the
# Mr. Mak review's loop flag). A walk comes back to its first pose; a punch, a kick or a fall does not.
ends = {}
for c, act, frames, rng in plan:
    if act is None:
        ends[c] = 0.0
        continue
    use(act)
    goto(rng[0])
    first = points() - np.array(drifts[c](rng[0]))
    goto(rng[1])
    last = points() - np.array(drifts[c](rng[1]))
    ends[c] = float(np.linalg.norm(last - first, axis=1).mean() / height_m)

# pass 1: every frame's exact extent on screen around the drifting ground point, in pixels: one cell fits them all
xs, ys = [0.0], [0.0]
for c, act, frames, _ in plan:
    use(act)
    for f in frames:
        goto(f)
        g = np.array(drifts[c](f) + Vector((0, 0, ground)))
        rel = points() - g
        for yaw in yaws:
            _, right, up = view(yaw)
            x, y = rel @ np.array(right) * ppm, rel @ np.array(up) * ppm
            xs += [float(x.min()), float(x.max())]
            ys += [float(y.min()), float(y.max())]
pad = 2
need = max(2 * max(abs(min(xs)), abs(max(xs))), max(ys) - min(ys)) + 2 * pad
cell = int(max(int(p.get("cell", 128)), ceil(need / 2) * 2))
assert cell * ss <= 2048, (
    f"the frames would be {cell * ss} px: lower height_px (now {ppm * height_m:.0f})"
)
below = ceil(max(0.0, -min(ys))) + pad  # pixels under the ground point
lift = (cell / 2 - below) / ppm  # the cell's centre above the ground point, in metres

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = cell / ppm
cam.data.clip_end = 1000
scene.collection.objects.link(cam)
scene.camera = cam
r = scene.render
r.engine = "BLENDER_WORKBENCH"
r.resolution_x = r.resolution_y = cell * ss
r.resolution_percentage = 100
r.film_transparent = True
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
# half a stop brighter under studio light: generated textures read dark at sprite size (M52 bench: the viking, the
# nurse and the archer at 0, 0.5 and 1); the unlit flat look is the texture as it is
scene.view_settings.exposure = 0.0 if p.get("shading") == "flat" else 0.5
scene.display.render_aa = "OFF"  # pixel art: every pixel one colour, no blend with the background
sh = scene.display.shading
sh.color_type = "TEXTURE"
sh.light = "FLAT" if p.get("shading") == "flat" else "STUDIO"
sh.show_specular_highlight = False
reach = float(np.linalg.norm(hi - lo)) + 10

rows = []
for c, act, frames, _ in plan:
    use(act)
    for yaw in yaws:
        d, right, up = view(yaw)
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        for k, f in enumerate(frames):
            goto(f)
            target = drifts[c](f) + Vector((0, 0, ground)) + up * lift
            cam.location = target + d * reach
            name = f"{stems[c]}_{yaw:03d}_{k:04d}"
            r.filepath = str(out / "frames" / f"{name}.png")
            bpy.ops.render.render(write_still=True)
            assert Path(r.filepath).is_file(), "render wrote nothing"
            rows.append(
                {"file": f"frames/{name}.png", "clip": c, "yaw": yaw, "duration": round(1000 / fps)}
            )

done(
    j,
    {
        "frames": rows,
        "cell": cell * ss,
        "ppm": ppm,
        "height_m": height_m,
        "clips": [c for c, *_ in plan],
        "loops": {c: ends[c] < LOOP for c in ends},
        "ends": {c: round(ends[c], 4) for c in ends},
        "scene_fps": scene_fps,
    },
)
