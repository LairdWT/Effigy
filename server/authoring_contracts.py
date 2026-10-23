"""Versioned authoring intent; session persistence remains in paint_sessions."""
from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class SourceRole(StrEnum):
    ORIGINAL = "original"
    ACCEPTED = "accepted"
    WORKING = "working"
    PREFERRED = "preferred"
    APPEARANCE = "appearance"
    DONOR = "donor"
    REJECTED = "rejected"


class AuthoringMethod(StrEnum):
    GENERATED = "generated"
    REGISTERED_SOURCE = "registered_source"
    BLENDER_BRUSH = "blender_brush"


class SourceBinding(Record):
    role: SourceRole
    version: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    note: str = Field(default="", max_length=2000)


class SamplingPolicy(Record):
    mode: Literal["detail", "study"] = "detail"
    minimum_samples: float = Field(default=1.0, ge=1, le=4)
    density_per_metre: float | None = Field(default=None, gt=0)
    metres_per_unit: float | None = Field(default=None, gt=0)
    viewing_distance_units: float | None = Field(default=None, gt=0)
    native_display_pixels: int = Field(default=1024, ge=128, le=8192)

    @model_validator(mode="after")
    def physical_units(self) -> Self:
        if self.density_per_metre is not None and self.metres_per_unit is None:
            raise ValueError("Physical texel density requires a measured metres-per-unit scale")
        return self


class MaterialIntent(Record):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    identity: str = Field(min_length=1, max_length=4000)
    faces: tuple[int, ...] | None = None
    palette: str = Field(default="", max_length=2000)
    feature_scale: str = Field(min_length=1, max_length=2000)
    marks: str = Field(default="", max_length=2000)
    preserve: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def valid_faces(self) -> Self:
        if self.faces is not None and (not self.faces or min(self.faces) < 0):
            raise ValueError("A material face subset must contain nonnegative face indices")
        if self.faces is not None and len(set(self.faces)) != len(self.faces):
            raise ValueError("Material face indices must be unique")
        return self


class PreparationRevision(Record):
    source: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    geometry_revision: str = Field(min_length=1, max_length=128)
    uv_profile: Literal["padded_islands", "line_art_square"] = "padded_islands"
    atlas_size: int = Field(default=1024, ge=128, le=4096)
    gutter_pixels: int = Field(default=4, ge=0, le=64)
    pack_rotation: Literal[90] = 90

    @model_validator(mode="after")
    def square_power_of_two(self) -> Self:
        if self.atlas_size & (self.atlas_size - 1):
            raise ValueError("The declared atlas size must be a power of two")
        return self


class AuthoringProfile(Record):
    schema_version: Literal[1] = 1
    preparation: PreparationRevision
    sources: tuple[SourceBinding, ...] = Field(min_length=1, max_length=24)
    materials: tuple[MaterialIntent, ...] = Field(min_length=1, max_length=64)
    sampling: SamplingPolicy = Field(default_factory=SamplingPolicy)
    method: AuthoringMethod = AuthoringMethod.GENERATED
    operation: Literal["refine_current", "restore_source", "restyle"] = "refine_current"
    style: str = Field(default="", max_length=8000)
    observation: str = Field(default="", max_length=8000)
    preservation: str = Field(default="", max_length=8000)
    submission_budget: int = Field(default=3, ge=1, le=12)

    @model_validator(mode="after")
    def source_contract(self) -> Self:
        keys: tuple[tuple[SourceRole, str], ...] = tuple((s.role, s.version) for s in self.sources)
        if len(keys) != len(set(keys)):
            raise ValueError("Source bindings must be unique")
        originals: tuple[SourceBinding, ...] = tuple(s for s in self.sources if s.role == SourceRole.ORIGINAL)
        if len(originals) != 1:
            raise ValueError("Declare exactly one immutable original source")
        material_ids: tuple[str, ...] = tuple(m.id for m in self.materials)
        if len(material_ids) != len(set(material_ids)):
            raise ValueError("Material identifiers must be unique")
        face_owners: dict[int, str] = {}
        for material in self.materials:
            for face in material.faces or ():
                if face in face_owners:
                    raise ValueError(f"Face {face} belongs to both {face_owners[face]} and {material.id}; material regions must not overlap")
                face_owners[face] = material.id
        if self.operation == "restore_source" or self.method == AuthoringMethod.REGISTERED_SOURCE:
            donors: tuple[SourceBinding, ...] = tuple(s for s in self.sources if s.role == SourceRole.DONOR)
            if len(donors) != 1:
                raise ValueError("Source reconstruction requires exactly one registered donor")
        return self

    def description(self, instructions: bool = True) -> str:
        sections: list[str] = [self.style]
        for material in self.materials:
            description: list[str] = [f"{material.id}: {material.identity}", f"Feature scale: {material.feature_scale}"]
            if material.palette:
                description.append(f"Palette: {material.palette}")
            if material.marks:
                description.append(f"Marks: {material.marks}")
            sections.append(". ".join(description))
            if instructions and material.preserve:
                sections.append(f"Preserve: {material.preserve}")
        if instructions and self.preservation:
            sections.append(f"Preserve: {self.preservation}")
        return "\n".join(section for section in sections if section)


class ReviewDecision(Record):
    version: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    verdict: Literal["preferred", "rejected", "accepted"]
    reviewer: Literal["owner", "operator"]
    note: str = Field(min_length=1, max_length=4000)
    profile_revision: int = Field(ge=1)
    round: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def owner_acceptance(self) -> Self:
        if self.verdict == "accepted" and self.reviewer != "owner":
            raise ValueError("Only an explicit owner review accepts appearance")
        return self
