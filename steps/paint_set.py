"""Normal job entrypoint for shared capture, UV selection and combined baking."""
from __future__ import annotations

import os
from pathlib import Path

from server import library
from steps._common import StepError, main
from steps._paint_set import Surface, capture, preview, select
from steps.paint import metadata, version_dir


def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:
    if os.environ.get("EFFIGY_MULTI_VIEW") != "1":
        raise StepError("bad_params", "Multi-view painting is enabled only in the isolated trial")
    if in_dir is None:
        raise StepError("missing_input", "Select a source mesh")
    source, out = Path(in_dir), Path(out_dir)
    if source.name != params["source"] or library.geometry_revision(source) != params["geometry_revision"]:
        raise StepError("bad_params", "Source geometry revision changed")
    if op == "apply":
        candidate = version_dir(source.parent, params["preview"])
        meta = metadata(candidate)
        if meta["step"] != "paint_set" or meta["params"].get("op") != "preview" or meta["parent"] != source.name:
            raise StepError("bad_params", "Apply requires a combined preview from this exact source")
        if meta["params"]["mask_version"] != params["mask_version"]:
            raise StepError("bad_params", "Preview selection changed; rebuild the preview")
        outputs = {key: "@" + value for key, value in meta["outputs"].items()}
        return {"outputs": outputs,
                "output_refs": {key: {"version": candidate.name, "key": key} for key in outputs},
                "metrics": meta["metrics"] | {"applied_preview": candidate.name, "duplicate_mesh_bytes": 0}}
    surface = Surface(source)
    if op == "capture":
        result = capture(surface, out, params)
    elif op == "select":
        result = select(surface, out, params)
    elif op in ("preview", "diagnostic"):
        result = preview(surface, out, params)
    else:
        raise StepError("bad_params", "Unknown multi-view operation")
    if "mesh" not in result["outputs"]:
        result["outputs"]["mesh"] = "@mesh.glb"
        result["output_refs"] = {"mesh": {"version": source.name, "key": "mesh"}}
    result["metrics"].update(geometry_revision=params["geometry_revision"], triangles=len(surface.mesh.faces),
                             texture_size=surface.size, bit_depth=surface.base.dtype.itemsize * 8)
    return result


if __name__ == "__main__":
    main(run)
