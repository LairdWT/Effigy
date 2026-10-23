"""Isolated local editing bridge; GPL-3.0-or-later, see LICENSE in this directory."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import bpy

ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server import runtime_policy

runtime_policy.activate()
addon: Path = Path(os.environ["EFFIGY_BLENDER_ADDON"])
spec = importlib.util.spec_from_file_location("effigy_local_blender_bridge", addon)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load configured local Blender bridge")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
bridge = module.BlenderMCPServer(host="127.0.0.1", port=int(os.environ["EFFIGY_BLENDER_PORT"]))
bridge.start()
bpy.context.scene["effigy_isolated_session"] = True
print(f"Effigy isolated bridge listening on {bridge.port}", flush=True)
