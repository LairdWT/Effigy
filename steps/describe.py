"""One on-demand local caption, with a job-owned GGUF server and no resident model."""
from __future__ import annotations

import base64
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from server import library, reference_models, runtime_policy
from steps._common import StepError, budget_gb, main, progress

PROMPT = (
    "Describe only the visible asset in this image, in 80-140 words. "
    "Name visible shapes, surface materials, colours, brushwork and relative placement. "
    "Distinguish uncertain material readings using 'appears'. Do not invent hidden sides. "
    "Do not propose edits or a desired style. Return only the description."
)


def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    if op != "run" or params:
        raise StepError("bad_params", "Describe takes one captured view and no generation parameters")
    if not in_dir:
        raise StepError("missing_input", "Capture a view before requesting a description")
    budget = budget_gb()
    if budget is None or budget < 12:
        raise StepError("oom", "The selected Q3.5 description worker requires 12 GiB available VRAM")
    src, out = Path(in_dir), Path(out_dir)
    meta = library._read(src / "meta.json")
    if meta.get("step") != "paint" or meta.get("params", {}).get("op") != "capture":
        raise StepError("bad_params", "Describe requires an unchanged painting capture")
    image = library.resolve_output(src, "image")
    if image.stat().st_size > 16 * 2**20:
        raise StepError("bad_params", "Capture exceeds the 16 MiB description input limit")
    executable, model, projector = reference_models.description_paths()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    key = secrets.token_urlsafe(32)
    command = [
        str(executable), "--model", str(model), "--mmproj", str(projector),
        "--alias", "effigy-description", "--host", "127.0.0.1", "--port", str(port),
        "--ctx-size", "4096", "--parallel", "1", "--n-gpu-layers", "999",
        "--device", "CUDA0", "--mmproj-device", "CUDA0",
        "--jinja", "--reasoning", "off", "--flash-attn", "on", "--no-webui",
        "--offline", "--fit", "off",
    ]
    env = os.environ | runtime_policy.OFFLINE | {"LLAMA_API_KEY": key}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    address = f"http://127.0.0.1:{port}"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    started = time.perf_counter()
    progress(0.05, "loading selected Q3.5 Q8 model and matching vision projector")
    process = subprocess.Popen(
        command, cwd=executable.parent, env=env, stdin=subprocess.DEVNULL,
        stdout=sys.stderr, stderr=sys.stderr, shell=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        while True:
            if process.poll() is not None:
                raise StepError("missing_input", f"Selected GGUF runtime exited ({process.returncode}); see this job's log for architecture/projector compatibility")
            try:
                with opener.open(urllib.request.Request(address + "/health", headers=headers), timeout=2) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.5)
        progress(0.4, "describing visible materials; owner appearance remains unchanged")
        observed = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        gpu_pid_seen = str(process.pid) in {line.strip() for line in observed.stdout.splitlines()}
        if not gpu_pid_seen:
            raise StepError("failed", "The selected description server was not observed on CUDA; no caption was requested")
        memory = subprocess.run(
            ["nvidia-smi", "--id=0", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        request = {
            "model": "effigy-description", "temperature": 0, "max_tokens": 384,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(image.read_bytes()).decode("ascii")}},
            ]}],
        }
        with opener.open(urllib.request.Request(
            address + "/v1/chat/completions", json.dumps(request).encode(), headers=headers,
        ), timeout=600) as response:
            raw = json.load(response)
        choice = raw["choices"][0]
        text = choice["message"]["content"]
        if not isinstance(text, str) or not text.strip() or len(text) > 8000 or choice.get("finish_reason") != "stop":
            raise StepError("failed", "Description was empty, oversized or truncated; owner appearance was not changed")
        result = {"text": text, "prompt": PROMPT, "source": src.name,
                  "model": model.name, "projector": projector.name, "response": raw}
        (out / "description.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return {"outputs": {"description": "description.json"}, "models": [{"id": "q35-opusglm", "file": model.name}],
                "metrics": {"seconds": round(time.perf_counter() - started, 2), "source": src.name,
                            "description": text, "runtime": executable.parent.name,
                            "cuda_process_observed": gpu_pid_seen, "device": "CUDA0",
                            "gpu_total_used_mib_after_load": int(memory.stdout.strip()),
                            "model_bytes": model.stat().st_size, "projector_bytes": projector.stat().st_size}}
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait()


if __name__ == "__main__":
    main(run)
