"""Launch an isolated offline Blender scene for Effigy's local editing bridge."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from server import runtime_policy, settings


def start(hidden: bool = False) -> subprocess.Popen:
    runtime_policy.configure()
    addon: Path = Path(os.environ.get("EFFIGY_BLENDER_ADDON", ""))
    if not addon.is_file():
        raise RuntimeError("Configured local Blender add-on is missing; provision that supporting tool first")
    scratch: Path = settings.ROOT / "scratch" / "blender"
    scratch.mkdir(parents=True, exist_ok=True)
    env: dict[str, str] = os.environ | runtime_policy.OFFLINE
    env["EFFIGY_BLENDER_PORT"] = str(settings.read().get("blender_free_port", 8371))
    for key, subdir in (
        ("BLENDER_USER_CONFIG", "config"),
        ("BLENDER_USER_SCRIPTS", "scripts"),
        ("BLENDER_USER_EXTENSIONS", "extensions"),
    ):
        folder: Path = scratch / "profile" / subdir
        folder.mkdir(parents=True, exist_ok=True)
        env[key] = str(folder)
    command: list[str] = [
        os.environ["EFFIGY_BLENDER"], "--factory-startup", "--offline-mode",
        "--python", str(settings.ROOT / "blender_ops" / "session_bridge.py"),
    ]
    startup = None
    if hidden and os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
    with (scratch / "session.log").open("w", encoding="utf-8") as log:
        return subprocess.Popen(command, cwd=settings.ROOT, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, startupinfo=startup)


if __name__ == "__main__":
    print(f"Effigy Blender PID: {start().pid}")
