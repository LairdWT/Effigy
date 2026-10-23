"""Bootstrap an Effigy worker with the configured standalone native interpreter."""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
step = os.environ.get("EFFIGY_WORKER_STEP", "reference")
if step not in ("reference", "paint_generate", "paint_finish_generate"):
    raise RuntimeError("Unsupported native worker entry")
one_shot_finish = step == "paint_finish_generate" and "--serve" not in sys.argv
if one_shot_finish:
    os.environ["EFFIGY_ONE_SHOT_FINISH"] = "1"
try:
    runpy.run_module(f"steps.{step}", run_name="__main__", alter_sys=True)
except SystemExit as result:
    if not one_shot_finish or type(result.code) is not int:
        raise
    protocol = sys.modules["steps._common"]
    protocol._out.flush()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(result.code)
