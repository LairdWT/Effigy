"""Parts: click a part of the model (IMPLEMENTATION.md M31): GeoSAM2 (VAST-AI, Apache-2.0, engine/geosam2)
in .venv-parts, one-shot.

op "views" (in: any version with a mesh): Blender renders GeoSAM2's twelve views of the mesh into
    views/ (blender_ops/parts_views: colour and normals as RGBA WEBP, depth as EXR, the cameras in
    views/meta.json, and the mesh in the face order the labels follow as views/mesh.glb); mesh.glb is
    that mesh. Once per mesh, about a minute.
op "segment" (in: a views version, or a segment version made from one): the clicks on one view become
    a named part. params: {"view": 3, "points": [[x, y, 1], [x, y, 0]], "name": "Helmet"} (x, y in
    the 1024² view; 1 = on the part, 0 = not the part). {"full": true} instead decomposes the whole
    model from the view and its opposite into parts named by size (clicks optional, naming one part).
    Outputs: parts.json ({"views", "labels": one int per face, 0 = no part, "parts": [{"id", "name",
    "faces"}]}), mesh.glb (one node per part, the rest as "Body"; blender_ops/parts_split), click.png
    (the view with the 2D mask, when clicked). A segment on a segment keeps its parts; a new part takes
    its faces from older ones, and a part with the same name is replaced.
op "rename" (in: a segment version): {"names": {"Part 1": "Helmet"}} → parts.json and mesh.glb with the
    new names; seconds, no GPU (server/jobs.py lets it keep the resident worker).
"""

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from steps import _glb
from steps._blender import BlenderError, run_blender
from steps._common import StepError, main, progress

MODEL_ID = "VAST-AI/GeoSAM2"
CFG = "configs/geosam2.yaml"  # inside the sam2 package of our geosam2 wheel
NUM_VIEWS = 12
# GeoSAM2's post-process: a part under 2 % of the largest one (in faces and area) joins its neighbours.
# ponytail: so a buckle beside a body vanishes; a lower PA for small parts if that is asked for
PA = 0.02
NONE = (0, 999)  # GeoSAM2's labels for "no part": unseen and background
# ponytail: measured to 149k faces (docs/bench/m31.md); GeoSAM2's lifting and post-process grow with the
# faces (Python loops over the face adjacency), so above this the views ask for a simplified mesh first
MAX_FACES = 200_000
MODELS = Path(os.environ.get("EFFIGY_MODELS", Path(__file__).resolve().parents[1] / "models"))
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")  # GeoSAM2 reads its depth maps through cv2


def _ckpt() -> Path:
    p = MODELS / "GeoSAM2" / "geosam2.pt"
    if not p.is_file():
        raise StepError("missing_input", "the `parts` model group is not installed (Setup → Parts)")
    return p


def _geosam2():
    """GeoSAM2's scripts, our torch twin of its compiled mode helper registered first
    (engine/geosam2/PATCHES.md)."""
    from engine.geosam2 import mode_ext

    sys.modules.setdefault("utils.mode_ext", mode_ext)
    from engine.geosam2 import inference
    from engine.geosam2 import single_view_point_prompt_infer as single

    return inference, single


def enclosed_background(opaque) -> int:
    """Background pixels the silhouette encloses (after img2threejs's turntable gate): a hole through the
    model as seen from this view, a handle's, a torn shell's or an arm on the hip's; a flood fill of the
    background from the border never reaches them."""
    from scipy import ndimage

    opaque = np.asarray(opaque, bool)
    return int((ndimage.binary_fill_holes(opaque) & ~opaque).sum())


def views(in_dir: Path, out: Path) -> dict:
    meta = json.loads((in_dir / "meta.json").read_text(encoding="utf-8"))
    glb = next((f for f in meta["outputs"].values() if f.endswith(".glb")), None)
    if not glb or not (in_dir / glb).is_file():
        raise StepError("missing_input", f"{in_dir.name} has no .glb")
    progress(0.05, "rendering the twelve views")
    t = time.time()
    try:
        res = run_blender(
            "parts_views", [in_dir / glb], out / "views", {"max_faces": MAX_FACES}, timeout=900
        )
    except BlenderError as e:
        raise StepError("failed", str(e)) from e
    from PIL import Image

    for f in ("parts_views_job.json", "parts_views.log"):  # absolute paths: not for the library
        (out / "views" / f).unlink(missing_ok=True)
    if res["faces"] > MAX_FACES:
        raise StepError(
            "bad_params",
            f"{res['faces']:,} faces: parts work up to {MAX_FACES:,}; simplify the model first",
        )
    # GeoSAM2 reads WEBP with alpha; Blender's WEBP writer drops the alpha, so the op wrote PNGs
    for png in sorted((out / "views").glob("*.png")):
        Image.open(png).convert("RGBA").save(png.with_suffix(".webp"), lossless=True)
        png.unlink()
    holes = {}  # view → background pixels inside the silhouette: a hole through the model from there
    for webp in sorted((out / "views").glob("color_*.webp")):
        n = enclosed_background(
            np.asarray(Image.open(webp).convert("RGBA"))[..., 3] > 0
        )  # all opaque: no alpha kept
        if n:
            holes[int(webp.stem[6:])] = n
    shutil.copyfile(out / "views" / "mesh.glb", out / "mesh.glb")
    return {
        "outputs": {"mesh": "mesh.glb", "views": "views/meta.json"},
        "metrics": {
            "views": out.name,
            "faces": res["faces"],
            "seconds": round(time.time() - t, 1),
            "holes": holes,
        },
    }


def views_of(in_dir: Path) -> tuple[Path, dict | None]:
    """The views folder this input segments, and the parts.json it builds on (a segment version)."""
    if (in_dir / "views" / "meta.json").is_file():
        return in_dir / "views", None
    if (in_dir / "parts.json").is_file():
        prev = json.loads((in_dir / "parts.json").read_text(encoding="utf-8"))
        d = in_dir.parent / prev["views"] / "views"
        if (d / "meta.json").is_file():
            return d, prev
        raise StepError("missing_input", f"the views of {in_dir.name} ({prev['views']}) are gone")
    raise StepError("missing_input", f"{in_dir.name} has no views: run the views op first")


def lift(views_dir: Path, view: int, points: list, full: bool, out: Path):
    """GeoSAM2: the clicks → a 2D mask on the view (out/click.png) → one label per face (an int array;
    1 = the clicked part, the auto parts above, NONE elsewhere), as its two scripts do it; and the
    peak VRAM in GB."""
    ckpt = _ckpt()
    progress(0.05, "loading GeoSAM2")
    import numpy as np
    from sam2.automatic_mask_generator_geosam2 import SAM2AutomaticMaskGenerator
    from sam2.build_sam import build_sam2, build_sam2_video_predictor_geosam2

    inference, single = _geosam2()
    device = inference.init_env()
    predictor = build_sam2_video_predictor_geosam2(CFG, str(ckpt), device=device)
    root = views_dir.as_posix()
    mask = None
    if points:
        progress(0.2, "the clicks on the view")
        state = predictor.init_state(video_path=root, video_id_list=[view])
        predictor.reset_state(state)
        predictor.add_new_points_or_box(
            inference_state=state,
            frame_idx=0,
            obj_id=1,
            points=np.array([p[:2] for p in points], np.float32),
            labels=np.array([p[2] for p in points], np.int32),
        )
        masks = {}
        for _, ids, logits in predictor.propagate_in_video_v2(state, start_frame_idx=0):
            masks = {int(i): (logits[k] > 0).cpu().numpy().squeeze() for k, i in enumerate(ids)}
        rgb = single.load_rgb(root, view)
        label_map = np.zeros(rgb.shape[:2], np.int32)
        for i, m in masks.items():
            label_map[m] = i
        if not label_map.any():
            raise StepError("failed", "nothing found at the clicks: click on the part itself")
        single.save_outputs(label_map, rgb, str(out), view)
        mask = out / f"mask_view{view:04d}.npy"
        (out / f"mask_view{view:04d}_vis.png").rename(out / "click.png")
    progress(
        0.4, "lifting the mask onto the faces" + (" and finding the other parts" if full else "")
    )
    generator = None
    if full:
        sam2 = build_sam2(CFG, str(ckpt), device=device, apply_postprocessing=False)
        generator = SAM2AutomaticMaskGenerator(  # GeoSAM2's own settings (inference.py main)
            model=sam2,
            points_per_side=64,
            points_per_batch=128,
            pred_iou_thresh=0.7,
            stability_score_thresh=0.7,
            stability_score_offset=0.7,
            crop_n_layers=0,
            box_nms_thresh=0.7,
            crop_n_points_downscale_factor=2,
            min_mask_region_area=25.0,
            use_m2m=True,
        )
    data = inference.read_data(
        root, mask_path=str(mask) if mask else None, mask_view=view if mask else None
    )
    res = inference.segment_with_mask_prompts(
        predictor,
        generator,
        data,
        opposite_auto_segmentation=full,
        enable_postprocess=True,
        postprocess_pa=PA,
        output_dir=str(out / "_geo"),
        start_frames=[view],
        start_to_seed_views={view: [view, (view + 6) % NUM_VIEWS] if full else [view]},
    )
    shutil.rmtree(out / "_geo", ignore_errors=True)
    if mask:
        mask.unlink()
    if res["face_label"] is None:  # upstream drops a 2D mask under 64 pixels before the lift
        raise StepError("failed", f"the part is too small to find in this view: {SMALL}")
    import torch

    peak = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else 0.0
    return res["face_label"].cpu().numpy().astype(int), round(peak, 2)


def merge(prev: dict | None, lab, found: list[tuple[int, str]]) -> tuple[list[int], list[dict]]:
    """The labels and parts after this run: `found` = (GeoSAM2 label, name) in the order the parts are
    made. A clicked part (named) takes its faces from older parts, and a name already in use replaces
    that part; an auto part (name "") only takes faces no part has, and one left with less than PA of
    the mesh is dropped (a sliver beside a clicked part)."""
    import numpy as np

    lab = np.asarray(lab)
    labels = np.array(prev["labels"]) if prev else np.zeros(len(lab), int)
    parts = [dict(p) for p in prev["parts"]] if prev else []
    if len(labels) != len(lab):
        raise StepError("failed", f"{len(lab)} faces labelled, the parts so far have {len(labels)}")
    next_id = max((p["id"] for p in parts), default=0) + 1
    for gid, name in found:
        sel = lab == gid
        if not name:
            sel &= labels == 0
        if sel.sum() < (1 if name else PA * len(lab)):
            continue
        for p in parts:
            if name and p["name"] == name:
                labels[labels == p["id"]] = 0
        parts = [p for p in parts if not (name and p["name"] == name)]
        labels[sel] = next_id
        parts.append({"id": next_id, "name": name or f"Part {next_id}"})
        next_id += 1
    for p in parts:
        p["faces"] = int((labels == p["id"]).sum())
    return labels.tolist(), [p for p in parts if p["faces"]]


# A part name becomes an object name in Blender (63 bytes) and the engines ("UCX_<name>_00",
# "<name>_LOD3"; blender_ops/export fills "{}" templates), and "Body" is the rest of the model.
BAD_NAME = re.compile(r"[{}/\\\x00-\x1f]|_LOD\d+$")
NAMES = "a name up to 56 bytes, not Body, without { } / \\ or a _LOD<n> ending"


def name_ok(name: str) -> bool:
    return (
        bool(name)
        and name.lower() != "body"
        and not BAD_NAME.search(name)
        and len(name.encode()) <= 56
    )


SMALL = (
    "click more points on it or try another view; a part smaller than about 2 % of the model is "
    "merged into its neighbours"
)


def segment(in_dir: Path, out: Path, params: dict) -> dict:
    try:
        view = int(params.get("view", 0))
        points = [[float(x), float(y), int(lab)] for x, y, lab in params.get("points") or []]
        full = bool(params.get("full", False))
        name = str(params.get("name", "")).strip()
    except (TypeError, ValueError):
        raise StepError("bad_params", f"bad parts params: {params}") from None
    if (
        not 0 <= view < NUM_VIEWS
        or not (points or full)
        or any(p[2] not in (0, 1) for p in points)
        or ((points or name) and not name_ok(name))
    ):
        raise StepError(
            "bad_params",
            f"bad parts params: {params} (a view 0–{NUM_VIEWS - 1}; points [x, y, 1|0] with a "
            f"name, or full: true; {NAMES})",
        )
    views_dir, prev = views_of(in_dir)
    t = time.time()
    lab, peak = lift(views_dir, view, points, full, out)
    lift_s = time.time() - t
    found = [(1, name)] if points else []
    if full:
        import numpy as np

        ids, counts = np.unique(lab, return_counts=True)
        found += [
            (int(i), "")
            for i, _ in sorted(zip(ids, counts), key=lambda t: -t[1])
            if i not in NONE and not (points and i == 1)
        ]
    labels, parts = merge(prev, lab, found)
    before = {p["id"] for p in prev["parts"]} if prev else set()
    new = [p["name"] for p in parts if p["id"] not in before]
    if not new:
        raise StepError("failed", f"no new part found: {SMALL}")
    (out / "parts.json").write_text(
        json.dumps({"views": views_dir.parent.name, "labels": labels, "parts": parts}),
        encoding="utf-8",
    )
    progress(0.85, "splitting the mesh into its parts")
    try:
        split = run_blender(
            "parts_split", [views_dir / "mesh.glb", out / "parts.json"], out / "_split", {}
        )
    except BlenderError as e:
        raise StepError("failed", str(e)) from e
    shutil.move(str(out / "_split" / "mesh.glb"), str(out / "mesh.glb"))
    shutil.rmtree(out / "_split", ignore_errors=True)
    outputs = {"mesh": "mesh.glb", "parts": "parts.json"}
    if (out / "click.png").is_file():
        outputs["click"] = "click.png"
    return {
        "outputs": outputs,
        "metrics": {
            "views": views_dir.parent.name,  # the UI finds the thumbnails there
            "view": view,
            "full": full,
            "new": new,
            "parts": split["parts"],
            "faces": len(labels),
            "lift_seconds": round(lift_s, 1),
            "seconds": round(time.time() - t, 1),
            "peak_vram_gb": peak,
        },
        "models": [{"id": MODEL_ID}],
        "licenses": [MODEL_ID, "geosam2"],
    }


def rename_glb(src: Path, dst: Path, names: dict) -> None:
    """The GLB with its nodes and meshes renamed: the JSON chunk rewritten, the binary chunk as it was."""
    doc, blob = _glb.read(src)
    for item in doc.get("nodes", []) + doc.get("meshes", []):
        if item.get("name") in names:
            item["name"] = names[item["name"]]
    _glb.write(dst, doc, blob)


def rename(in_dir: Path, out: Path, params: dict) -> dict:
    """New names for the parts of a segment version, without the GPU or Blender (M31b)."""
    if not (in_dir / "parts.json").is_file():
        raise StepError("missing_input", f"{in_dir.name} has no parts to rename")
    prev = json.loads((in_dir / "parts.json").read_text(encoding="utf-8"))
    old = [p["name"] for p in prev["parts"]]
    names = params.get("names")
    ok = isinstance(names, dict) and all(isinstance(v, str) for v in names.values())
    new = {str(k): v.strip() for k, v in names.items()} if ok else {}
    final = [new.get(n, n) for n in old]
    if (
        final == old  # nothing changes
        or set(new) - set(old)
        or not all(map(name_ok, new.values()))
        or len(set(final)) < len(final)
    ):
        raise StepError(
            "bad_params", f"bad names {names}: {{old: new}} for the parts {old}, each once; {NAMES}"
        )
    parts = [p | {"name": new.get(p["name"], p["name"])} for p in prev["parts"]]
    (out / "parts.json").write_text(json.dumps(prev | {"parts": parts}), encoding="utf-8")
    rename_glb(in_dir / "mesh.glb", out / "mesh.glb", new)
    counts = {p["name"]: p["faces"] for p in parts}
    if body := prev["labels"].count(0):
        counts["Body"] = body
    return {
        "outputs": {"mesh": "mesh.glb", "parts": "parts.json"},
        "metrics": {"views": prev["views"], "renamed": new, "parts": counts},
    }


def run(op, in_dir, out_dir, params):
    if not in_dir:
        raise StepError("missing_input", "parts needs an input version (--in)")
    if op == "views":
        return views(Path(in_dir), Path(out_dir))
    if op == "segment":
        return segment(Path(in_dir), Path(out_dir), params)
    if op == "rename":
        return rename(Path(in_dir), Path(out_dir), params)
    raise StepError("bad_params", f"unknown op {op!r}: views | segment | rename")


if __name__ == "__main__":
    main(run)
