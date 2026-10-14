"""SkinTokens skin-only engine for rig_skin (IMPLEMENTATION.md M20). Imports only in `.venv-skin`.

The MIT no-Blender port (comfyui-skintokens-noblender, pinned in pyproject) vendors the upstream torch
core, whose `michelangelo` subtree is GPL-3 by provenance (research 05): the rig_skin step process is
the subprocess boundary, the server never imports any of this. Weights: the pinned local copies from
`tools/download_models.py skin` (no network here).

The model's skin-only mode knows exactly the 52-joint Mixamo template, by the `mixamorig:` names of its
part-order table; our skeleton.json carries the same joints without the prefix, so it's added for the
model and stripped from its output. The rig is then transferred onto the input GLB itself, which keeps
its textures.
"""

import json
import os
import time
from pathlib import Path

import numpy as np

MODELS = (
    Path(os.environ.get("EFFIGY_MODELS", Path(__file__).resolve().parents[1] / "models"))
    / "SkinTokens"
)
PATHS = {
    "tokenrig": MODELS / "experiments/articulation_xl_quantization_256_token_4/grpo_1400.ckpt",
    "skin_vae": MODELS / "experiments/skin_vae_2_10_32768/last.ckpt",
    "qwen_dir": MODELS / "Qwen3-0.6B",
}
PREFIX = "mixamorig:"


def load():
    import torch
    from skintokens import model_loader

    missing = [str(p) for p in PATHS.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"SkinTokens weights missing ({missing[0]}): python -m tools.download_models skin"
        )
    model_loader.resolve_weights = lambda **_: {k: str(v) for k, v in PATHS.items()}  # ours, pinned
    return model_loader.load_model(
        device="cuda" if torch.cuda.is_available() else "cpu", download=False
    )


def _seed(seed: int) -> None:
    import random

    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _metrics(t0: float, t1: float, cuda: bool, **more) -> dict:
    import torch

    peak = round(torch.cuda.max_memory_allocated() / 2**30, 2) if cuda else 0.0
    t = {"seconds": round(time.time() - t0, 1), "seconds_load": round(t1 - t0, 1)}
    return {"engine": "skintokens"} | t | {"peak_vram_gb": peak} | more


def skin(
    mesh_glb, skeleton_json, out_glb, cls: str = "mixamo", num_beams: int = 1, seed: int = 0
) -> dict:
    """mesh.glb + skeleton.json (rig_fit's) → out_glb skinned by the model; returns metrics. Seeded:
    the surface sampler and the skin decoder draw random numbers (unseeded, one farmer run stretched
    5.6x in the test poses and the next 74x)."""
    import torch

    _seed(seed)
    from skintokens import glb_io, infer, transfer

    t0 = time.time()
    bundle = load()
    t1 = time.time()
    skel = json.loads(Path(skeleton_json).read_text(encoding="utf-8"))["joints"]
    index = {j["name"]: i for i, j in enumerate(skel)}
    parents = np.array([index[j["parent"]] if j["parent"] else -1 for j in skel], np.int64)
    joints = np.array([j["position"] for j in skel], np.float32)
    asset = glb_io.load_asset(str(mesh_glb), cls=cls)
    matrix_local = np.tile(np.eye(4, dtype=np.float32), (len(skel), 1, 1))
    matrix_local[:, :3, 3] = joints
    asset.matrix_local, asset.parents = matrix_local, parents
    asset.joint_names = [PREFIX + j["name"] for j in skel]
    cuda = torch.cuda.is_available()
    if cuda:
        torch.cuda.reset_peak_memory_stats()
    rigged = infer.rig_asset(
        bundle, asset, generate_kwargs={"num_beams": num_beams}, use_skeleton=True
    )
    # skin-only: the result names no joints, and its joints are the tokenizer's quantized copies; its
    # bones are the input's in the order the transform arranged them (prepare_asset reordered `asset`
    # in place), so the input's names and exact positions go back on
    if rigged.skin.shape[1] != len(asset.joint_names) or not np.array_equal(
        rigged.parents, asset.parents
    ):
        raise RuntimeError("SkinTokens returned a skeleton that isn't the input's")
    rigged.joint_names = [n.removeprefix(PREFIX) for n in asset.joint_names]
    rigged.matrix_local = asset.matrix_local
    transfer.transfer_rigging(rigged, str(mesh_glb), str(out_glb))
    return _metrics(t0, t1, cuda, joints=len(rigged.joint_names), vertices=len(asset.vertices))
