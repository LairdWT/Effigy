# SPDX-License-Identifier: GPL-3.0-or-later
"""Bone name maps from our 52 joints to the clip sources the retarget reads (no bpy: tests import this)."""

# our 52 joints (steps/_rig.template) → UE5 Manny; fingers thumb_01_l … pinky_03_l
UE5 = {
    "Hips": "pelvis",
    "Spine": "spine_01",
    "Spine1": "spine_02",
    "Spine2": "spine_03",
    "Neck": "neck_01",
    "Head": "head",
}
for _s, _x in (("Left", "l"), ("Right", "r")):
    UE5 |= {
        f"{_s}Shoulder": f"clavicle_{_x}",
        f"{_s}Arm": f"upperarm_{_x}",
        f"{_s}ForeArm": f"lowerarm_{_x}",
        f"{_s}Hand": f"hand_{_x}",
        f"{_s}UpLeg": f"thigh_{_x}",
        f"{_s}Leg": f"calf_{_x}",
        f"{_s}Foot": f"foot_{_x}",
        f"{_s}ToeBase": f"ball_{_x}",
    }
    for _f in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
        UE5 |= {f"{_s}Hand{_f}{k}": f"{_f.lower()}_0{k}_{_x}" for k in (1, 2, 3)}

# our 52 joints → Kimodo's SOMA 77-joint skeleton (M26): SOMA's Spine1/Spine2/Chest are our three spine
# joints, Neck1 our neck (Neck2 unmapped), Leg/Shin our UpLeg/Leg; its fingers carry a metacarpal joint 1
# before the three phalanges (our 1–3 are SOMA 2–4), the thumb has none; Root, HeadEnd, Jaw, the eyes, the
# *End joints and the toe ends have no counterpart
SOMA = {
    "Hips": "Hips",
    "Spine": "Spine1",
    "Spine1": "Spine2",
    "Spine2": "Chest",
    "Neck": "Neck1",
    "Head": "Head",
}
for _s in ("Left", "Right"):
    SOMA |= {
        f"{_s}{n}": f"{_s}{n}" for n in ("Shoulder", "Arm", "ForeArm", "Hand", "Foot", "ToeBase")
    }
    SOMA |= {f"{_s}UpLeg": f"{_s}Leg", f"{_s}Leg": f"{_s}Shin"}
    SOMA |= {f"{_s}HandThumb{k}": f"{_s}HandThumb{k}" for k in (1, 2, 3)}
    for _f in ("Index", "Middle", "Ring", "Pinky"):
        SOMA |= {f"{_s}Hand{_f}{k}": f"{_s}Hand{_f}{k + 1}" for k in (1, 2, 3)}

# our 52 joints are Mixamo's names (an animation from Mixamo or another Mixamo-rigged file, owner 2026-10-12);
# Mixamo's own files prefix them, "mixamorig:Hips" (or "mixamorig1:" …): source_map adds the prefix it finds
MIXAMO = {n: n for n in UE5}

SOURCES = {
    "ue5": (UE5, "pelvis"),
    "soma": (SOMA, "Hips"),
    "mixamo": (MIXAMO, "Hips"),
}  # name map, the root bone the hips travel reads


def kind(names) -> str | None:
    """Which clip source a skeleton's bone names are: "ue5", "soma", "mixamo", or None (none the retarget reads).
    SOMA and Mixamo share Hips and Spine1; SOMA's legs are Leg/Shin and it has a Chest, Mixamo's are UpLeg/Leg."""
    bare = {n.rsplit(":", 1)[-1] for n in names}
    if "pelvis" in bare:
        return "ue5"
    if "LeftShin" in bare or "Chest" in bare:
        return "soma"
    if {"Hips", "LeftUpLeg", "RightUpLeg", "LeftArm", "RightArm"} <= bare:
        return "mixamo"
    return None


def source_map(arm) -> tuple[dict, str]:
    """(our name → source bone, source root) for an imported clip armature, told apart by its bones (a
    clip the retarget did not know before, None, reads as SOMA as it always did)."""
    names = [b.name for b in arm.data.bones]
    m, root = SOURCES[kind(names) or "soma"]
    pre = next((n[: -len(root)] for n in names if n.endswith(":" + root)), "")
    return ({k: pre + v for k, v in m.items()}, pre + root) if pre else (m, root)
