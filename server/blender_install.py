"""Pinned Blender 5.2.2 LTS (research 08 §1): downloaded on first run, SHA-256 checked, portable.

    uv run python -m server.blender_install      # run.bat/run.sh call this once

`EFFIGY_BLENDER` overrides the path (e.g. a Blender you already have). Downloading instead of shipping
Blender keeps us clear of GPL source-distribution duties.
"""

import hashlib
import os
import platform
import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://download.blender.org/release/Blender5.2/"
# file, SHA-256 (from download.blender.org/release/Blender5.2/blender-5.2.2.sha256), executable
PINNED = {
    "Windows": (
        "blender-5.2.2-windows-x64.zip",
        "3849d17a682cba006075aaa3f3597ecb5c9c30ec31035b2e092c53e40679b535",
        "blender.exe",
    ),
    "Linux": (
        "blender-5.2.2-linux-x64.tar.xz",
        "84098912789dc450e95697c4184fb8a90acbe5111c2ba4aede3fecb57806a168",
        "blender",
    ),
}


def blender_exe() -> Path:
    """Where Blender is (or will be after install()); never downloads."""
    if env := os.environ.get("EFFIGY_BLENDER"):
        return Path(env)
    name, _, exe = PINNED[platform.system()]
    return ROOT / "blender" / name.removesuffix(".zip").removesuffix(".tar.xz") / exe


def fetch(url: str, sha: str, home: Path) -> None:
    """Download url, check its SHA-256, unpack it (.zip or tar) into home; nothing is kept on a mismatch."""
    home.mkdir(parents=True, exist_ok=True)
    name = url.rsplit("/", 1)[1]
    part = home / (name + ".part")
    print(f"downloading {url} …", flush=True)
    # download.blender.org answers 403 to urllib's default "Python-urllib" user agent
    req = urllib.request.Request(url, headers={"User-Agent": "Effigy (first-run install)"})
    with urllib.request.urlopen(req) as r, open(part, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    with open(part, "rb") as f:
        got = hashlib.file_digest(f, "sha256").hexdigest()
    if got != sha:
        part.unlink()
        raise SystemExit(f"{name}: SHA-256 {got} != pinned {sha}; not installing")
    if name.endswith(".zip"):
        with zipfile.ZipFile(part) as z:
            z.extractall(home)
    else:
        with tarfile.open(part) as t:
            t.extractall(home, filter="data")
    part.unlink()


def install() -> Path:
    exe = blender_exe()
    if exe.exists():
        return exe
    name, sha, _ = PINNED[platform.system()]
    fetch(URL + name, sha, ROOT / "blender")  # ~400 MB
    (exe.parent / "portable").mkdir(exist_ok=True)  # user prefs/add-ons stay out (Blender ≥ 4.2)
    return exe


if __name__ == "__main__":
    print(install())
