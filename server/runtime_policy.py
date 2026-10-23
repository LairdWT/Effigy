"""Local runtime configuration and Python network boundary."""
from __future__ import annotations

import ipaddress
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from server import settings

OFFLINE: dict[str, str] = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "DO_NOT_TRACK": "1",
    "UV_OFFLINE": "1",
    "PIP_NO_INDEX": "1",
    "TEXT_ENCODER_MODE": "local",
    "LOCAL_CACHE": "true",
}
_active: bool = False
BROWSER_POLICY: str = (
    "default-src 'self'; connect-src 'self' blob:; script-src 'self' 'wasm-unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
    "media-src 'self' data: blob:; worker-src 'self' blob:; object-src 'none'; "
    "base-uri 'self'; form-action 'self'; report-uri /api/runtime/csp-report"
)
_browser_violations: int = 0


def record_browser_violation() -> None:
    global _browser_violations
    _browser_violations += 1
    logging.getLogger(__name__).error("offline browser policy blocked a page resource")


def browser_violations() -> int:
    return _browser_violations


def configure() -> None:
    """Resolve this workstation's ignored configuration without downloading."""
    config: dict[str, Any] = settings.read()
    os.environ.setdefault("EFFIGY_MODELS", str(settings.models_root()))
    os.environ.setdefault("EFFIGY_LIBRARY", str(config.get("library", settings.ROOT / "library")))
    os.environ["EFFIGY_PORT"] = "8370"
    os.environ.setdefault("EFFIGY_SCRATCH", str(settings.ROOT / "scratch"))
    os.environ.setdefault("UV_CACHE_DIR", str(settings.ROOT / "cache" / "uv"))
    os.environ.setdefault("UV_PYTHON_INSTALL_DIR", str(settings.ROOT / "python"))
    scratch: Path = Path(os.environ["EFFIGY_SCRATCH"]) / "tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(scratch)
    tempfile.tempdir = str(scratch)
    os.environ["FLEX_GEMM_AUTOTUNE_CACHE_PATH"] = str(
        settings.ROOT / "cache" / "flex_gemm_autotune_cache.json"
    )
    for key, folder in (
        ("HF_MODULES_CACHE", "huggingface/modules"),
        ("TORCH_HOME", "torch"),
        ("XDG_CACHE_HOME", "xdg"),
        ("NUMBA_CACHE_DIR", "numba"),
        ("WARP_CACHE_PATH", "warp"),
        ("npm_config_cache", "npm"),
    ):
        os.environ[key] = str(settings.ROOT / "cache" / folder)
    os.environ["HF_HUB_CACHE"] = str(settings.models_root() / "hub")
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    tools_file: Path = Path(config.get("tools_config", settings.ROOT.parent / "3DGen" / "tools.config.json"))
    tools_config: dict[str, Any] = json.loads(tools_file.read_text(encoding="utf-8"))
    blender: dict[str, Any] = tools_config["blender"]
    blender_path: str = os.environ.get(str(blender.get("environmentOverride", "")), "") or str(
        tools_file.parent / blender["executable"]
    )
    if not Path(blender_path).is_file():
        raise RuntimeError("Configured portable Blender is missing; runtime startup refused")
    os.environ["EFFIGY_BLENDER"] = blender_path
    bridge: dict[str, Any] | None = tools_config.get("mcpForBlender")
    if bridge is not None:
        os.environ["EFFIGY_BLENDER_ADDON"] = str(
            tools_file.parent / bridge["runtimeDirectory"] / "addon.py"
        )
    uv: dict[str, Any] = tools_config["uv"]
    os.environ["EFFIGY_UV"] = str(tools_file.parent / uv["executable"])


def _loopback(host: object) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="strict")
    if not isinstance(host, str):
        return False
    if host.lower() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    mapped = getattr(address, "ipv4_mapped", None)
    return address.is_loopback or (mapped is not None and mapped.is_loopback)


def _network_guard(event: str, args: tuple[Any, ...]) -> None:
    host: object
    if event == "socket.getaddrinfo":
        host = args[0]
    elif event in ("socket.connect", "socket.sendto"):
        address: object = args[-1]
        if not isinstance(address, tuple):
            return
        host = address[0]
    else:
        return
    if not _loopback(host):
        logging.getLogger(__name__).error("offline runtime blocked an outbound socket operation")
        raise PermissionError("Effigy runtime permits loopback sockets only; use separate provisioning")


def activate() -> None:
    """Always offline, including when the server is started through uvicorn."""
    global _active
    if _active:
        return
    configure()
    os.environ.pop("EFFIGY_PROVISIONING", None)
    os.environ.update(OFFLINE)
    sys.addaudithook(_network_guard)
    _active = True


def require_provisioning() -> None:
    if _active or os.environ.get("EFFIGY_PROVISIONING") != "1":
        raise RuntimeError("Online provisioning is unavailable in runtime; run provision.bat separately")
