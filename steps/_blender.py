"""Run a blender_ops/<op>.py headless (IMPLEMENTATION.md §3.6). No import side effects (tests use it)."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BlenderError(RuntimeError):
    pass


def run_blender(op: str, inputs: list, out_dir, params: dict, timeout: float = 600) -> dict:
    """Blender in its own process; the timeout is the watchdog (QuadriFlow can hang). Returns result.json."""
    exe = os.environ.get("EFFIGY_BLENDER")
    if not exe or not Path(exe).is_file():
        raise BlenderError(
            f"Configured Blender not found at {exe!r}: check the tools_config path in settings.json"
        )
    out = Path(
        out_dir
    ).resolve()  # absolute: Blender resolves relative paths elsewhere (C:\library\…)
    out.mkdir(parents=True, exist_ok=True)
    spec = out / f"{op}_job.json"
    ins = [str(Path(p).resolve()) for p in inputs]
    spec.write_text(json.dumps({"in": ins, "out_dir": str(out), "params": params}))
    cmd = [exe, "-b", "--factory-startup", "--offline-mode", "--python-exit-code", "1"]
    cmd += ["--python", str(ROOT / "blender_ops" / f"{op}.py"), "--", str(spec)]
    log = out / f"{op}.log"
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    # a file, not a pipe: an undrained pipe can hang Blender
    with open(log, "w", encoding="utf-8") as f:
        try:
            rc = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                creationflags=flags,
                check=False,
            ).returncode
        except subprocess.TimeoutExpired as e:
            raise BlenderError(
                f"blender_ops/{op}.py timed out after {timeout:.0f} s (see {log.name})"
            ) from e
    result = out / "result.json"
    if rc or not result.is_file():
        tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-15:]
        raise BlenderError(f"blender_ops/{op}.py exited {rc}:\n" + "\n".join(tail))
    data = json.loads(result.read_text(encoding="utf-8"))
    result.unlink()  # several ops may share out_dir
    return data
