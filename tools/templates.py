"""Write the creature templates' bones (steps/templates/<id>.json) from Mesh2Motion's rigs (IMPLEMENTATION.md M36).

    uv run python -m tools.templates   (needs Blender: EFFIGY_BLENDER or `python -m server.blender_install`)

Each rig at the pinned commit is fetched, checked against its SHA-256, read by blender_ops/template_bones
(Blender turns the glTF joints back into bones with tails) and written as a small JSON the fitting reads.
The rigs are CC0 (Mesh2Motion's README: "the art assets (3d models, rigs, animations) are all CC0").
"""

import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path

from steps._blender import run_blender
from steps._templates import DIR, RIGS


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for name, (url, sha) in RIGS.items():
            data = urllib.request.urlopen(url, timeout=60).read()
            if hashlib.sha256(data).hexdigest() != sha:
                raise SystemExit(f"{url}: SHA-256 mismatch")
            rig = Path(tmp, f"{name}.glb")
            rig.write_bytes(data)
            run_blender("template_bones", [rig], Path(tmp, name), {})
            bones = json.loads(Path(tmp, name, "bones.json").read_text(encoding="utf-8"))
            (DIR / f"{name}.json").write_text(json.dumps(bones, indent=1) + "\n", encoding="utf-8")
            print(f"{name}: {len(bones)} bones")


if __name__ == "__main__":
    main()
