"""CPU planning and reference-only publication of automatic finishing drafts."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from server import library
from steps._common import StepError, main
from steps._finish_plan import build_plan
from steps._paint_set import Surface
from steps.paint import metadata, version_dir

logger = logging.getLogger(__name__)


def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    if os.environ.get("EFFIGY_MULTI_VIEW") != "1" or in_dir is None:
        raise StepError("bad_params", "Automatic finishing requires a saved mesh in the isolated trial")
    source = Path(in_dir)
    if source.name != params["source"] or library.geometry_revision(source) != params["geometry_revision"]:
        raise StepError("bad_params", "Finishing source or geometry revision changed")
    if op == "plan":
        try:
            return build_plan(Surface(source), Path(out_dir), params)
        except (IndexError, ValueError):
            logger.exception("Finishing planner failed for the recorded source and selection")
            raise
    if op == "finalize":
        from steps.paint_finish_generate import run as finalize

        return finalize("finish", in_dir, out_dir, params | {"replay_only": True})
    if op != "apply":
        raise StepError("bad_params", "Unsupported finishing operation")
    candidate = version_dir(source.parent, params["preview"])
    record = metadata(candidate)
    if (record["step"] != "paint_finish" or record["params"].get("op") != "finish"
            or record["parent"] != source.name or record["params"].get("plan_version") != params["plan_version"]):
        raise StepError("bad_params", "Review a finishing draft from this exact source and plan")
    outputs = {key: "@" + value for key, value in record["outputs"].items()}
    return {"outputs": outputs, "output_refs": {key: {"version": candidate.name, "key": key} for key in outputs},
            "metrics": record["metrics"] | {"applied_preview": candidate.name, "duplicate_mesh_bytes": 0}}


if __name__ == "__main__":
    main(run)
