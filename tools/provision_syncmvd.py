"""Explicit online provisioning for the isolated SyncMVD trial runtime."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "scratch/lanes/fibo2"
REVISION = "faa95621d220d7327847a994cd380608c04af5ab"
SNAPSHOTS = (
    ("stable-diffusion-v1-5/stable-diffusion-v1-5", "451f4fe16113bff5a5d2269ed5ad43b0592e9a14", "sd15",
     ["model_index.json", "scheduler/scheduler_config.json", "tokenizer/*", "text_encoder/config.json",
      "text_encoder/model.fp16.safetensors", "unet/config.json", "unet/diffusion_pytorch_model.fp16.safetensors",
      "vae/config.json", "vae/diffusion_pytorch_model.fp16.safetensors"]),
    ("lllyasviel/control_v11p_sd15_normalbae", "cb7296e6587a219068e9d65864e38729cd862aa8", "normal",
     ["config.json", "diffusion_pytorch_model.fp16.safetensors"]),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", required=True)
    parser.add_argument("--resolve-lock", action="store_true")
    parser.add_argument("--models-only", action="store_true")
    args = parser.parse_args()
    if not (LANE / "settings.json").is_file():
        raise RuntimeError("The existing 8380 trial must be configured first")
    local = json.loads((LANE / "settings.json").read_text(encoding="utf-8"))
    owned = Path(local["models"]) / "SyncMVD"
    if not owned.parent.is_dir():
        raise RuntimeError("Effigy-owned NAS model storage is unavailable")
    if shutil.disk_usage(owned.parent).free < 5 * 2**30:
        raise RuntimeError("SyncMVD provisioning needs 5 GiB free on the owned model drive")
    environment = dict(os.environ)
    for key in ("UV_OFFLINE", "PIP_NO_INDEX", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        environment.pop(key, None)
    environment.update(UV_CACHE_DIR=str(ROOT / "cache/uv"), HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1")
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("Installed uv command is unavailable")
    python = ROOT / ".venv-syncmvd/Scripts/python.exe"
    lock = ROOT / "requirements-syncmvd.lock"

    def command(arguments: list[str]) -> None:
        subprocess.run(arguments, cwd=ROOT, env=environment, check=True)

    if not args.models_only:
        if not python.exists():
            command([uv, "venv", "--python", str(ROOT / ".venv-ml/Scripts/python.exe"), str(python.parents[1])])
        if args.resolve_lock:
            command([uv, "pip", "compile", "requirements-syncmvd.in", "--python", str(python),
                     "--torch-backend", "cu128", "--output-file", str(lock),
                     "--custom-compile-command", "uv pip compile requirements-syncmvd.in --python .venv-syncmvd/Scripts/python.exe --torch-backend cu128 --output-file requirements-syncmvd.lock"])
        if not lock.is_file():
            raise RuntimeError("Resolve the separate lock explicitly with --resolve-lock before installation")
        command([uv, "pip", "sync", str(lock), "--python", str(python), "--torch-backend", "cu128"])
        command([str(python), str(Path(__file__)), "--online", "--models-only"])
        return

    for key, value in environment.items():
        os.environ[key] = value
    for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        os.environ.pop(key, None)
    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import HfHubHTTPError
    owned.mkdir(exist_ok=True)
    bindings = {"source_revision": REVISION, "python": str(python)}
    failures: list[str] = []
    for repo, revision, name, patterns in SNAPSHOTS:
        target = owned / name / revision
        print(f"Provisioning pinned {repo}@{revision}", flush=True)
        try:
            snapshot_download(repo_id=repo, revision=revision, allow_patterns=patterns,
                              local_dir=target, cache_dir=owned / "hub", max_workers=4)
        except (OSError, HfHubHTTPError) as error:
            failures.append(f"{repo}: {error}")
            print(f"INCOMPLETE {repo}: {type(error).__name__}", flush=True)
            continue
        bindings[name] = {"path": str(target), "repo": repo, "revision": revision,
                          "files": {str(p.relative_to(target)).replace('\\', '/'): p.stat().st_size
                                    for p in target.rglob('*') if p.is_file() and '.cache' not in p.parts}}
    source = ROOT / "scratch/syncmvd-upstream" / REVISION
    for relative in ("LICENSE", "src/syncmvd/step.py", "src/syncmvd/attention.py", "src/pipeline.py"):
        target = source / relative
        if target.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"https://raw.githubusercontent.com/LIU-Yuxin/SyncMVD/{REVISION}/{relative}") as response:
            target.write_bytes(response.read())
    bindings["source"] = str(source)
    bindings["ready"] = not failures
    target = LANE / "syncmvd.local.json"
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(bindings, indent=2), encoding="utf-8")
    temporary.replace(target)
    if failures:
        raise RuntimeError("Provisioning incomplete; retained successful components.\n" + "\n".join(failures))
    print(f"SyncMVD provisioned at {python}; local bindings {target}", flush=True)


if __name__ == "__main__":
    main()
