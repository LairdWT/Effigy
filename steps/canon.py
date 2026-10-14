"""Re-pose a character to an A-pose before 3D, then gate it (IMPLEMENTATION.md M16).

Input: a prep version (image.png, the RGBA cut-out). params: {"seed", "steps", "look": "render", "offload": true|false
(default: by the budget, M46a)}.
look "render" also redraws a flat picture (pixel art, a drawing) as a shaded 3D figure: TRELLIS reads volume from
shading, and a flat one comes out as a cardboard standee (the owner's female viking from pixel art: 0.45 as deep as
wide; redrawn first, 1.0, with a back of its own).
Output: image.png (the re-posed character on light grey; `prep` cuts it out again) and gate.json (DWPose
on the result: pose a|t|other|unsure, arm and elbow angles). The model gets the character as image 1
and the shipped A-pose reference (prompts/apose_ref.png, how it was made: blender_ops/apose_guide.py) as image 2.
FLUX.2-klein-4B, 4 steps: the M16 bake-off winner (docs/bench/m16.md; Qwen-Image-Edit-2511 + AnyPose
didn't fit 16 GB usefully and is gone).
"""

import json
import os
import random
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from steps import _birefnet, _pose
from steps._common import StepError, main, offload, progress

ROOT = Path(__file__).resolve().parents[1]
MODELS = Path(os.environ.get("EFFIGY_MODELS", ROOT / "models"))
REFERENCE = ROOT / "prompts" / "apose_ref.png"
GREY = (200, 200, 200)
# AnyPose's prompt (made for Qwen) made klein keep the knight's raised sword arms and add the
# mannequin's: say what to keep and what to drop
PROMPT = (
    "Show the same character as in image 1, {look}but standing in the exact pose of the mannequin in image 2: "
    "exactly two arms, both straight and held 45 degrees away from the body, hands open and empty, nothing "
    "in the hands (no weapon, no tool, no object), feet slightly apart, facing the viewer, full body. Keep "
    "the character's design, armour or clothes, colours and proportions from image 1. Do not copy the "
    "mannequin's look. Plain light-grey background."
)
LOOKS = {
    "": "",
    "render": "drawn as a smooth, softly lit 3D game character render with natural shading and volume, not pixel art "
    "(no visible pixels, no outlines, no dithering), with exactly the same clothes, as long as in image 1 (a dress that "
    "reaches the floor still reaches the floor), and the same footwear, with a clearly drawn face (eyes, eyebrows, nose "
    "and mouth), ",  # without the last two: the mannequin's bare legs (4 of 4 seeds) and a blank face (3 of 9)
}
WEIGHTS = ["black-forest-labs/FLUX.2-klein-4B"]
# M46a: the budget that holds the whole pipeline on the GPU. The weights are 14.9 GB (text encoder 7.49, transformer
# 7.22, VAE 0.16) plus ~2 GB at work (the offloaded run peaks at 9.17 with one part on the GPU); out of memory under a
# 12.5 GB cap on the laptop while loading (docs/bench/m46.md). So 24 GB cards; est. until a user's report measures it.
GPU_GB = 17.0


def _load(off: bool):
    from diffusers import Flux2KleinPipeline

    pipe = Flux2KleinPipeline.from_pretrained(
        str(MODELS / "FLUX.2-klein-4B"), torch_dtype=torch.bfloat16
    )
    if off:  # each part on the GPU only while it runs (16 GB cards)
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")
    return pipe


def _on_grey(path: Path) -> Image.Image:
    rgba = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", rgba.size, GREY + (255,))
    return Image.alpha_composite(bg, rgba).convert("RGB")


def run(op, in_dir, out_dir, params):
    src = Path(in_dir or "") / "image.png"
    if not in_dir or not src.is_file():
        raise StepError("missing_input", "canon needs a prep version (image.png)")
    seed, steps = params.get("seed", random.randrange(2**31)), int(params.get("steps", 4))
    look = params.get("look", "")
    if look not in LOOKS:
        raise StepError("bad_params", f"look {look!r}: only {sorted(LOOKS)}")
    t0, out = time.time(), Path(out_dir)

    off = offload(params, GPU_GB)
    progress(0.05, "loading FLUX.2-klein-4B" + (" (offloaded)" if off else ""))
    pipe = _load(off)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t1 = time.time()
    progress(0.3, f"re-posing ({steps} steps)")
    image = pipe(
        image=[_on_grey(src), Image.open(REFERENCE).convert("RGB")],
        prompt=PROMPT.format(look=LOOKS[look]),
        num_inference_steps=steps,
        generator=torch.Generator("cpu").manual_seed(seed),
        guidance_scale=1.0,
    ).images[0]
    t2 = time.time()
    peak = torch.cuda.max_memory_allocated() / 2**30 if torch.cuda.is_available() else 0.0
    del pipe
    torch.cuda.empty_cache()
    image.save(out / "image.png")

    progress(0.9, "pose gate")
    rgb = np.asarray(image.convert("RGB"))
    alpha = _birefnet.matte(_birefnet.load(), rgb)
    g = _pose.gate(*_pose.keypoints(_pose.load(), rgb, alpha))
    (out / "gate.json").write_text(json.dumps(g, indent=2), encoding="utf-8")
    licences = [*WEIGHTS, _pose.MODEL, _birefnet.MODEL]
    return {
        "outputs": {"image": "image.png", "gate": "gate.json"},
        "metrics": {
            "pose": g["pose"],
            "seconds": round(time.time() - t0, 1),
            "seconds_load": round(t1 - t0, 1),
            "seconds_edit": round(t2 - t1, 1),
            "peak_vram_gb": round(peak, 2),
            "offload": off,
            "seed": seed,
        },
        "licenses": licences,
    }


if __name__ == "__main__":
    main(run)
