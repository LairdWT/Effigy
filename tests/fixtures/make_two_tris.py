"""Writes two_tris.glb: a 1 m quad (2 triangles) with normals, UVs and a PBR material. Stdlib only."""

import json
import struct
from pathlib import Path

pos = [(-0.5, 0, -0.5), (0.5, 0, -0.5), (0.5, 0, 0.5), (-0.5, 0, 0.5)]
uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
idx = [0, 2, 1, 0, 3, 2]  # counter-clockwise seen from +Y
blob = b"".join(struct.pack("<3f", *p) for p in pos)
blob += struct.pack("<3f", 0, 1, 0) * 4 + b"".join(struct.pack("<2f", *t) for t in uv)
blob += struct.pack("<6H", *idx) + b"\0\0"  # pad to 4 bytes
views = [(0, 48), (48, 48), (96, 32), (128, 12)]
gltf = {
    "asset": {"version": "2.0"},
    "scene": 0,
    "scenes": [{"nodes": [0]}],
    "nodes": [{"mesh": 0}],
    "meshes": [
        {
            "primitives": [
                {
                    "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                    "indices": 3,
                    "material": 0,
                }
            ]
        }
    ],
    "materials": [
        {"pbrMetallicRoughness": {"baseColorFactor": [0.8, 0.5, 0.2, 1], "roughnessFactor": 0.6}}
    ],
    "buffers": [{"byteLength": len(blob)}],
    "bufferViews": [{"buffer": 0, "byteOffset": o, "byteLength": n} for o, n in views],
    "accessors": [
        {
            "bufferView": 0,
            "componentType": 5126,
            "count": 4,
            "type": "VEC3",
            "min": [-0.5, 0, -0.5],
            "max": [0.5, 0, 0.5],
        },
        {"bufferView": 1, "componentType": 5126, "count": 4, "type": "VEC3"},
        {"bufferView": 2, "componentType": 5126, "count": 4, "type": "VEC2"},
        {"bufferView": 3, "componentType": 5123, "count": 6, "type": "SCALAR"},
    ],
}
js = json.dumps(gltf, separators=(",", ":")).encode()
js += b" " * (-len(js) % 4)
glb = struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(blob))
glb += struct.pack("<I4s", len(js), b"JSON") + js + struct.pack("<I4s", len(blob), b"BIN\0") + blob
Path(__file__).with_name("two_tris.glb").write_bytes(glb)
