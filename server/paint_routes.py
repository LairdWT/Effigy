"""Typed localhost entrypoints for multi-view painting."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from server import paint_sessions
from server.library import ApiError

router = APIRouter(prefix="/api/assets/{asset_id}/paint-sessions")


@contextmanager
def storage_boundary() -> Iterator[None]:
    try:
        yield
    except OSError as error:
        raise ApiError(503, "storage_unavailable", "Asset storage is unavailable. Reconnect the configured drive; completed work has not been redirected to another location.") from error


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: Literal["fibo2-turbo", "krea-genesis", "moss-turbo", "syncmvd"] = "fibo2-turbo"
    prompt: str = Field(default="", max_length=20000)
    materials: str = Field(default="", max_length=20000)
    style: str = Field(default="", max_length=20000)
    preserve: str = Field(default="", max_length=20000)
    seed: int = Field(default=24031, ge=0, lt=2**53)
    denoise: float = Field(default=0.35, gt=0, le=1)
    conditioning: Literal["preserve_structure", "blank_region"] = "preserve_structure"
    style_image: str | None = None
    feather: int = Field(default=0, ge=0, le=32)
    moss_steps: Literal[4, 6, 8] = 8


class Create(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    recipe: Recipe = Field(default_factory=Recipe)
    front_yaw: float = Field(default=0, ge=-360, le=360)
    faces: list[int] | None = Field(default=None, max_length=100000)
    reuse_session: str | None = None
    strategy: Literal["pairs", "whole_sheet", "synchronized"] = "pairs"
    selection_source: str | None = None
    panel_size: Literal[192, 256, 384, 512] = 512


class CandidateReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    excluded: bool


class Update(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    recipe: Recipe | None = None
    excluded: list[str] | None = None
    group_instructions: dict[str, str] | None = None
    candidate_version: str | None = None
    candidate_review: CandidateReview | None = None


class FinishOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_patches: int = Field(default=3, ge=1, le=3)
    correction_budget: int = Field(default=1, ge=0, le=1)
    protected_faces: list[int] = Field(default_factory=list, max_length=100000)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    action: Literal["capture", "select", "generate", "preview", "apply", "diagnostic", "finish_plan", "finish", "finish_apply"]
    groups: list[str] | None = None
    regenerate: bool = False
    diagnostic_mode: Literal["mask", "source"] = "mask"
    view_id: str | None = None
    selection: dict | None = None
    selection_mode: Literal["add", "erase", "all", "clear", "faces", "refresh"] = "add"
    finish_options: FinishOptions | None = None


@router.get("")
def list_sessions(asset_id: str) -> list[dict]:
    with storage_boundary():
        return paint_sessions.list_sessions(asset_id)


@router.post("")
def create(asset_id: str, body: Create) -> dict:
    with storage_boundary():
        return paint_sessions.create(asset_id, body.source, body.recipe.model_dump(), body.front_yaw, body.faces,
                                     body.reuse_session, body.strategy, body.selection_source, body.panel_size)


@router.get("/{session_id}")
def get(asset_id: str, session_id: str) -> dict:
    with storage_boundary():
        return paint_sessions.get(asset_id, session_id)


@router.patch("/{session_id}")
def update(asset_id: str, session_id: str, body: Update) -> dict:
    with storage_boundary():
        return paint_sessions.update(asset_id, session_id, body.revision,
                                     body.recipe.model_dump() if body.recipe is not None else None, body.excluded,
                                     body.group_instructions, body.candidate_version,
                                     (body.candidate_review.version, body.candidate_review.excluded) if body.candidate_review is not None else None)


@router.post("/{session_id}/actions")
def action(asset_id: str, session_id: str, body: Action) -> dict:
    with storage_boundary():
        return paint_sessions.action(asset_id, session_id, body.model_dump())
