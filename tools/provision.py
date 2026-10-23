"""Explicit public provisioning; never imported by normal runtime."""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from server import runtime_policy

ROOT: Path = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-only", action="store_true")
    parser.add_argument("--groups", nargs="*", default=[])
    args: argparse.Namespace = parser.parse_args()
    runtime_policy.configure()
    for key in runtime_policy.OFFLINE:
        os.environ.pop(key, None)
    os.environ.update(
        EFFIGY_PROVISIONING="1", HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1",
        GIT_LFS_SKIP_SMUDGE="1", UV_PYTHON_PREFERENCE="only-managed",
    )
    uv: str = os.environ["EFFIGY_UV"]
    python_version: str = (ROOT / ".python-version").read_text(encoding="ascii").strip()
    if not args.models_only:
        for group in ("backend", "ml", "skin", "kimodo", "parts", "gemx", "moge"):
            os.environ["UV_PROJECT_ENVIRONMENT"] = ".venv" if group == "backend" else ".venv-" + group
            command: list[str] = [uv, "sync", "--frozen", "--python", python_version]
            if group != "backend":
                command += ["--group", group]
            run(command)
        npm: str = "npm.cmd" if os.name == "nt" else "npm"
        run([npm, "--prefix", "ui", "ci"])
        run([npm, "--prefix", "ui", "run", "build"])
        run([str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "server.gltfpack_install"])
    python: Path = ROOT / ".venv-ml" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run([str(python), "-m", "tools.download_models", *args.groups])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
