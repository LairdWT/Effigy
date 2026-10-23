"""Import an animation (owner 2026-10-12): an `upload` version holding an animation made elsewhere (.fbx, .glb,
.gltf, .bvh) → clip.glb, a motion like a text or a video one: it lands among "Your motions" and `anim` puts it on a
skinned character (params.clips names this version, as "310_motion").

params: {"clip": which of the file's animations (its name as metrics.clips lists it; default the first), "name":
the clip's name (default that animation's own, the file's for a generic take such as Mixamo's "mixamo.com"; a name
in use in the asset or the clip pack gets the version's number), "for": the skinned version it is meant for (the
motion page's target, as mocap's)}. blender_ops/anim_clip does the work. The file's skeleton must be one the retarget reads
(blender_ops/_maps.kind): Mixamo (any "mixamorig:" prefix), Unreal's Manny/Quinn (UE5 names), Kimodo's SOMA. A
file has no lineage: its licence is the user's to check, as an imported model's.
Outputs: clip.glb. Metrics: name, file, skeleton, frames, seconds, clips (the file's animations), picked.
"""

import json
import shutil
from pathlib import Path

from steps._blender import BlenderError, run_blender
from steps._common import StepError, asset_directory, main, progress
from steps.import_model import _check_gltf
from steps.mocap import taken_names

TYPES = (".fbx", ".glb", ".gltf", ".bvh")
SKELETONS = "Mixamo, Unreal (Manny, Quinn) or Kimodo (SOMA)"


def run(op, in_dir, out_dir, params):
    if set(params) - {"clip", "name", "for"}:
        raise StepError(
            "bad_params", f"unknown params {sorted(set(params) - {'clip', 'name', 'for'})}"
        )
    if not in_dir:
        raise StepError(
            "missing_input", "import_motion needs an upload version with an animation file"
        )
    src, out = Path(in_dir), Path(out_dir)
    meta = json.loads((src / "meta.json").read_text(encoding="utf-8"))
    rel = (meta.get("outputs") or {}).get("model", "")
    f = src / rel
    if not rel or f.suffix.lower() not in TYPES or not f.is_file():
        raise StepError("missing_input", f"{src.name} has no animation file ({', '.join(TYPES)})")
    if f.suffix.lower() == ".gltf":
        _check_gltf(f)
    upload = (meta.get("params") or {}).get("name") or f.name  # the user's file name
    progress(0.2, f"reading {upload}")
    try:
        rep = run_blender(
            "anim_clip",
            [f],
            out / "_clip",
            {
                "name": params.get("name"),
                "clip": params.get("clip"),
                "taken": sorted(taken_names(asset_directory(out))),
                "suffix": out.name[:3],
            },
            timeout=600,
        )
    except BlenderError as e:
        raise StepError("failed", str(e)) from e
    if rep.get("missing"):
        raise StepError(
            "bad_params", f"{upload} has no animation {rep['missing']!r}; it has {rep['clips']}"
        )
    if not rep["clips"]:
        raise StepError("missing_input", f"{upload} has no skeleton with an animation")
    if rep["skeleton"] is None:
        first = ", ".join(rep["bones"][:6])
        raise StepError(
            "missing_input",
            f"{upload}: its skeleton ({first}…) is none the app can put on a character: {SKELETONS}",
        )
    shutil.move(out / "_clip" / "clip.glb", out / "clip.glb")
    shutil.rmtree(out / "_clip", ignore_errors=True)
    return {
        "outputs": {"clip": "clip.glb"},
        "metrics": {
            "name": rep["name"],
            "file": upload,
            "skeleton": rep["skeleton"],
            "frames": rep["frames"],
            "seconds": rep["seconds"],
            "clips": rep["clips"],
            "picked": rep["picked"],
        },
    }


if __name__ == "__main__":
    main(run)
