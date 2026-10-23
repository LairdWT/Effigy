"""Versioned records for bounded, resumable surface finishing."""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Literal

FINISH_SCHEMA = 1
FINISH_ENGINE = "hard_cut_v1"
FinishModel = Literal["fibo2-turbo", "krea-genesis"]


@dataclass(frozen=True)
class FinishSettings:
    max_patches: int = 3
    correction_budget: int = 1
    protected_faces: tuple[int, ...] = ()

    @classmethod
    def from_dict(cls, value: dict) -> FinishSettings:
        if set(value) - {"max_patches", "correction_budget", "protected_faces"}:
            raise ValueError("Unknown finishing setting")
        count = value.get("max_patches", 3)
        corrections = value.get("correction_budget", 1)
        faces = value.get("protected_faces", [])
        if type(count) is not int or not 1 <= count <= 3:
            raise ValueError("Finishing supports one to three patches per pass")
        if type(corrections) is not int or not 0 <= corrections <= 1:
            raise ValueError("Finishing permits at most one correction per pass")
        if not isinstance(faces, (list, tuple)) or any(type(i) is not int or i < 0 for i in faces):
            raise ValueError("Protected faces must be non-negative triangle IDs")
        return cls(count, corrections, tuple(sorted(set(faces))))

    def to_dict(self) -> dict:
        return {"max_patches": self.max_patches, "correction_budget": self.correction_budget,
                "protected_faces": list(self.protected_faces)}


@dataclass(frozen=True)
class FinishCamera:
    id: str
    yaw: float
    pitch: float
    center: tuple[float, float, float]
    extent: float

    def view(self) -> dict:
        return {"yaw": self.yaw, "pitch": self.pitch, "center": list(self.center), "extent": self.extent}

    @classmethod
    def from_dict(cls, row: dict) -> FinishCamera:
        camera = cls(row["id"], float(row["yaw"]), float(row["pitch"]), tuple(row["center"]), float(row["extent"]))
        if not isinstance(camera.id, str) or re.fullmatch(r"v(?:0\d|1\d|2[0-5])", camera.id) is None:
            raise ValueError("Invalid finishing camera identity")
        if len(camera.center) != 3 or camera.extent <= 0 or not all(
                math.isfinite(v) for v in (camera.yaw, camera.pitch, camera.extent, *camera.center)):
            raise ValueError("Invalid fixed finishing camera")
        return camera


@dataclass(frozen=True)
class FinishPatch:
    id: str
    camera: FinishCamera
    pair_indices: tuple[int, ...]
    component: int
    score: float
    prompt: str | None = None
    correction_prompt: str | None = None
    context_zoom: float = 1.0
    material_faces: tuple[int, ...] | None = None
    footprint_filter: bool = False

    @classmethod
    def from_dict(cls, row: dict) -> FinishPatch:
        if row.get("id") not in ("p00", "p01", "p02"):
            raise ValueError("Invalid finishing patch identity")
        indices = row["pair_indices"]
        if not isinstance(indices, list) or not indices or any(type(i) is not int or i < 0 for i in indices):
            raise ValueError("Finishing patch requires recorded seam pairs")
        if any(row.get(key) is not None and not isinstance(row[key], str) for key in ("prompt", "correction_prompt")):
            raise ValueError("Finishing prompts must be literal text")
        zoom = row.get("context_zoom", 1.0)
        if type(zoom) not in (int, float) or not math.isfinite(zoom) or not 1 <= zoom <= 2:
            raise ValueError("Finishing context zoom must be between one and two")
        material_faces = row.get("material_faces")
        if material_faces is not None and (not isinstance(material_faces, list) or not material_faces
                                          or any(type(face) is not int or face < 0 for face in material_faces)):
            raise ValueError("Finishing material permission requires recorded nonnegative faces")
        footprint_filter = row.get("footprint_filter", False)
        if type(footprint_filter) is not bool:
            raise ValueError("Finishing footprint policy must be a boolean")
        return cls(row["id"], FinishCamera.from_dict(row["camera"]), tuple(indices), int(row["component"]),
                   float(row["score"]), row.get("prompt"), row.get("correction_prompt"), float(zoom),
                   None if material_faces is None else tuple(material_faces), footprint_filter)


@dataclass(frozen=True)
class FinishPlan:
    source: str
    geometry_revision: str
    mask_version: str | None
    recipe: dict
    settings: FinishSettings
    size: int
    cameras: tuple[FinishCamera, ...]
    patches: tuple[FinishPatch, ...]
    coverage: dict
    schema: int = FINISH_SCHEMA
    engine: str = FINISH_ENGINE
    mask_policy: str = "close_context_v4"
    generation_policy: str = "source_locked_v1"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict) -> FinishPlan:
        if row.get("schema") != FINISH_SCHEMA or row.get("engine") != FINISH_ENGINE:
            raise ValueError("Finishing plan uses a different implementation; create a new plan")
        if row.get("size") != 1024 or row["recipe"].get("model") not in ("fibo2-turbo", "krea-genesis"):
            raise ValueError("Finishing requires1024 full-context views and a supported repair model")
        cameras = tuple(FinishCamera.from_dict(v) for v in row["cameras"])
        patches = tuple(FinishPatch.from_dict(v) for v in row["patches"])
        if len({patch.footprint_filter for patch in patches}) > 1:
            raise ValueError("A finishing plan must use one projection sampling policy")
        settings = FinishSettings.from_dict(row["settings"])
        mask_policy = row.get("mask_policy", "legacy_v1")
        if mask_policy not in ("legacy_v1", "seed_connected_v2", "feature_connected_v3", "close_context_v4"):
            raise ValueError("Unknown finishing mask policy")
        generation_policy = row.get("generation_policy", "reference_only_v1")
        if generation_policy not in ("reference_only_v1", "source_locked_v1"):
            raise ValueError("Unknown finishing generation policy")
        if len(patches) > settings.max_patches or len({p.id for p in patches}) != len(patches):
            raise ValueError("Finishing patch budget or identity changed")
        return cls(row["source"], row["geometry_revision"], row["mask_version"], row["recipe"], settings,
                   row["size"], cameras, patches, row["coverage"], mask_policy=mask_policy, generation_policy=generation_policy)


@dataclass
class FinishCheckpoint:
    binding: dict
    patches: list[dict]
    stage: str = "starting"
    corrections: int = 0

    def to_dict(self) -> dict:
        return asdict(self) | {
            "completed": sum(p.get("decision") in ("retained", "rejected", "skipped") for p in self.patches),
            "accepted": sum(p.get("decision") == "retained" for p in self.patches),
            "retained": sum(p.get("decision") == "retained" for p in self.patches),
            "rejected": sum(p.get("decision") == "rejected" for p in self.patches),
        }

    @classmethod
    def from_dict(cls, row: dict, binding: dict, ids: set[str]) -> FinishCheckpoint:
        saved_binding = row.get("binding", {})
        saved_binding = saved_binding | {"mask_policy": saved_binding.get("mask_policy", "legacy_v1")}
        saved_binding["generation_policy"] = saved_binding.get("generation_policy", "reference_only_v1")
        if saved_binding != binding:
            raise ValueError("Finishing checkpoint belongs to a different source, selection or recipe")
        patches = row.get("patches")
        if not isinstance(patches, list) or len({p.get("id") for p in patches}) != len(patches):
            raise ValueError("Finishing checkpoint has malformed patch records")
        if any(p.get("id") not in ids or p.get("decision") not in ("pending", "retained", "rejected", "skipped") for p in patches):
            raise ValueError("Finishing checkpoint contains an unknown patch or decision")
        corrections = row.get("corrections", 0)
        if type(corrections) is not int or not 0 <= corrections <= 1:
            raise ValueError("Finishing correction counter is invalid")
        return cls(binding, patches, str(row.get("stage", "interrupted")), corrections)
