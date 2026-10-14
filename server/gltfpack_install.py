"""Pinned gltfpack (zeux/meshoptimizer, MIT; IMPLEMENTATION.md M13): LOD simplification and the web
profile's meshopt + WebP. One native binary, so exports need no Node. First run, SHA-256 checked.

    uv run python -m server.gltfpack_install      # run.bat/run.sh call this once

`EFFIGY_GLTFPACK` overrides the path.
"""

import os
import platform
from pathlib import Path

from server.blender_install import ROOT, fetch

TAG = "v0.25"
URL = f"https://github.com/zeux/meshoptimizer/releases/download/{TAG}/"
# release asset, its SHA-256 (hashed by us when pinning; the release lists none), executable
PINNED = {
    "Windows": (
        "gltfpack-windows.zip",
        "decc9a3492610bb2873781a73a766ab66f71780e01120f1962bb8601412fcf0c",
        "gltfpack.exe",
    ),
    "Linux": (
        "gltfpack-ubuntu.zip",
        "78fe884c216cf14434b11d932940891e891b9fa021082e4eeb6460e633d90d12",
        "gltfpack",
    ),
}


def gltfpack_exe() -> Path:
    """Where gltfpack is (or will be after install()); never downloads."""
    if env := os.environ.get("EFFIGY_GLTFPACK"):
        return Path(env)
    return ROOT / "gltfpack" / TAG / PINNED[platform.system()][2]


def install() -> Path:
    exe = gltfpack_exe()
    if not exe.exists():
        name, sha, _ = PINNED[platform.system()]
        fetch(URL + name, sha, exe.parent)
        exe.chmod(0o755)  # zip drops the executable bit
    return exe


if __name__ == "__main__":
    print(install())
