"""Writes quad_box.glb: a 1 m cube of six quads, each as the two consecutive triangles (a, b, c), (a, c, d) that
Blender's glTF exporter writes for a quad; positions and indices only. The viewer's quad wireframe pairs them.
Stdlib only."""

import json
import struct
from pathlib import Path

pos = [(x, y, z) for z in (-0.5, 0.5) for y in (-0.5, 0.5) for x in (-0.5, 0.5)]
# bottom, top, front, back, left, right: outward counter-clockwise
quads = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
idx = [i for a, b, c, d in quads for i in (a, b, c, a, c, d)]
blob = b"".join(struct.pack("<3f", *p) for p in pos) + struct.pack(f"<{len(idx)}H", *idx)
views = [(0, 96), (96, 2 * len(idx))]
gltf = {
    "asset": {"version": "2.0"},
    "scene": 0,
    "scenes": [{"nodes": [0]}],
    "nodes": [{"mesh": 0}],
    "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
    "buffers": [{"byteLength": len(blob)}],
    "bufferViews": [{"buffer": 0, "byteOffset": o, "byteLength": n} for o, n in views],
    "accessors": [
        {
            "bufferView": 0,
            "componentType": 5126,
            "count": 8,
            "type": "VEC3",
            "min": [-0.5, -0.5, -0.5],
            "max": [0.5, 0.5, 0.5],
        },
        {"bufferView": 1, "componentType": 5123, "count": len(idx), "type": "SCALAR"},
    ],
}
js = json.dumps(gltf, separators=(",", ":")).encode()
js += b" " * (-len(js) % 4)
blob += b"\0" * (-len(blob) % 4)
out = b"".join(
    [
        struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(blob)),
        struct.pack("<I4s", len(js), b"JSON"),
        js,
        struct.pack("<I4s", len(blob), b"BIN\0"),
        blob,
    ]
)
Path(__file__).with_name("quad_box.glb").write_bytes(out)
print(f"quad_box.glb: {len(out)} bytes, {len(idx) // 3} triangles")
