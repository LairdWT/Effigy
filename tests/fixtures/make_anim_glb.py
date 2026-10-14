"""Writes anim.glb (M37's UI test): a 1.5 m column skinned to three bones in a chain (Hips, Spine, Head), and two clips
baked as anim does: Walk (25 keys, the Hips travelling, the spine swaying) and Idle (13 keys), 24 fps, a LINEAR key every
frame on what moves, constant channels as 2-key STEP. Stdlib only."""

import json
import math
import struct
from pathlib import Path

FPS = 24
blob = bytearray()
views, accessors = [], []


def add(
    values: list[float], fmt: str, kind: str, count: int, comp: int = 5126, minmax: bool = False
) -> int:
    """Packs values as one bufferView + accessor (4-byte aligned) and returns the accessor's index."""
    while len(blob) % 4:
        blob.append(0)
    start = len(blob)
    blob.extend(struct.pack(f"<{len(values)}{fmt}", *values))
    views.append({"buffer": 0, "byteOffset": start, "byteLength": len(blob) - start})
    acc = {"bufferView": len(views) - 1, "componentType": comp, "count": count, "type": kind}
    if minmax:
        acc |= {"min": [min(values)], "max": [max(values)]}
    accessors.append(acc)
    return len(accessors) - 1


# the column: four rings of four vertices at y = 0, 0.5, 1.0, 1.5, each ring skinned to one bone
rings = [0.0, 0.5, 1.0, 1.5]
pos, joints = [], []
for r, y in enumerate(rings):
    for x, z in ((-0.15, -0.15), (0.15, -0.15), (0.15, 0.15), (-0.15, 0.15)):
        pos += [x, y, z]
        joints += [min(r, 2), 0, 0, 0]
idx = []
for r in range(3):
    for s in range(4):
        a, b, c, d = 4 * r + s, 4 * r + (s + 1) % 4, 4 * (r + 1) + (s + 1) % 4, 4 * (r + 1) + s
        idx += [a, b, c, a, c, d]
POS = add(pos, "f", "VEC3", 16)
accessors[POS] |= {"min": [-0.15, 0, -0.15], "max": [0.15, 1.5, 0.15]}
JOINTS = add(joints, "H", "VEC4", 16, 5123)
WEIGHTS = add([1.0, 0, 0, 0] * 16, "f", "VEC4", 16)
INDICES = add(idx, "H", "SCALAR", len(idx), 5123)
# bind pose: Hips at the floor, Spine 0.5 above, Head 0.5 above that (inverse bind = minus the world height)
ibm = []
for y in (0.0, 0.5, 1.0):
    ibm += [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, -y, 0, 1]
IBM = add(ibm, "f", "MAT4", 3)


def quat(axis: tuple[float, float, float], deg: float) -> list[float]:
    h = math.radians(deg) / 2
    return [axis[0] * math.sin(h), axis[1] * math.sin(h), axis[2] * math.sin(h), math.cos(h)]


def clip(name: str, frames: int, sway: float, travel: float) -> dict:
    times = [f / FPS for f in range(frames + 1)]
    t_all = add(times, "f", "SCALAR", len(times), minmax=True)
    t_two = add([0.0, times[-1]], "f", "SCALAR", 2, minmax=True)
    ph = [2 * math.pi * f / frames for f in range(frames + 1)]
    out = {
        "hips_t": add(
            [v for p in ph for v in (0.0, 0.02 * math.sin(2 * p), travel * p / (2 * math.pi))],
            "f",
            "VEC3",
            len(ph),
        ),
        "hips_r": add([0, 0, 0, 1] * 2, "f", "VEC4", 2),
        "spine_r": add(
            [v for p in ph for v in quat((0, 0, 1), sway * math.sin(p))], "f", "VEC4", len(ph)
        ),
        "head_r": add(
            [v for p in ph for v in quat((1, 0, 0), 0.5 * sway * math.cos(p))], "f", "VEC4", len(ph)
        ),
        "one": add([1.0, 1, 1] * 2, "f", "VEC3", 2),
        "spine_t": add([0, 0.5, 0] * 2, "f", "VEC3", 2),
        "head_t": add([0, 0.5, 0] * 2, "f", "VEC3", 2),
    }
    samplers, channels = [], []

    def ch(node: int, path: str, inp: int, output: int, interp: str) -> None:
        samplers.append({"input": inp, "output": output, "interpolation": interp})
        channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": path}})

    ch(0, "translation", t_all, out["hips_t"], "LINEAR")
    ch(0, "rotation", t_two, out["hips_r"], "STEP")
    ch(1, "rotation", t_all, out["spine_r"], "LINEAR")
    ch(2, "rotation", t_all, out["head_r"], "LINEAR")
    ch(1, "translation", t_two, out["spine_t"], "STEP")
    ch(2, "translation", t_two, out["head_t"], "STEP")
    for n in range(3):
        ch(n, "scale", t_two, out["one"], "STEP")
    return {"name": name, "samplers": samplers, "channels": channels}


animations = [clip("Idle", 12, 6, 0.0), clip("Walk", 24, 20, 0.5)]
while len(blob) % 4:
    blob.append(0)
gltf = {
    "asset": {"version": "2.0"},
    "scene": 0,
    "scenes": [{"nodes": [0, 3]}],
    "nodes": [
        {"name": "Hips", "children": [1]},
        {"name": "Spine", "children": [2], "translation": [0, 0.5, 0]},
        {"name": "Head", "translation": [0, 0.5, 0]},
        {"name": "Body", "mesh": 0, "skin": 0},
    ],
    "meshes": [
        {
            "primitives": [
                {
                    "attributes": {"POSITION": POS, "JOINTS_0": JOINTS, "WEIGHTS_0": WEIGHTS},
                    "indices": INDICES,
                }
            ]
        }
    ],
    "skins": [{"joints": [0, 1, 2], "inverseBindMatrices": IBM, "skeleton": 0}],
    "animations": animations,
    "buffers": [{"byteLength": len(blob)}],
    "bufferViews": views,
    "accessors": accessors,
}
js = json.dumps(gltf, separators=(",", ":")).encode()
js += b" " * (-len(js) % 4)
out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob))
out += (
    struct.pack("<II", len(js), 0x4E4F534A)
    + js
    + struct.pack("<II", len(blob), 0x004E4942)
    + bytes(blob)
)
Path(__file__).with_name("anim.glb").write_bytes(out)
