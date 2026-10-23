"""Versioned, engine-independent boundaries for fixed-camera paint candidates."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Strategy = Literal["pairs", "whole_sheet", "synchronized"]
PERMISSION_PROJECTION = "same_face_all_selected_v2"


@dataclass(frozen=True)
class PanelRect:
    camera_id: str
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class ViewLayout:
    version: int
    width: int
    height: int
    panels: tuple[PanelRect, ...]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> ViewLayout:
        panels = tuple(PanelRect(**row) for row in value["panels"])
        layout = cls(value["version"], value["width"], value["height"], panels)
        if layout.version != 1 or not panels or layout.width <= 0 or layout.height <= 0:
            raise ValueError("Unsupported or empty paint layout")
        if len({p.camera_id for p in panels}) != len(panels):
            raise ValueError("A camera may occur only once in a joint layout")
        for i, panel in enumerate(panels):
            if min(panel.x, panel.y) < 0 or panel.width <= 0 or panel.height != panel.width:
                raise ValueError("Paint panels must be square positive rectangles")
            if panel.x + panel.width > layout.width or panel.y + panel.height > layout.height:
                raise ValueError("Paint panel exceeds the recorded sheet")
            for other in panels[:i]:
                if (panel.x < other.x + other.width and other.x < panel.x + panel.width
                        and panel.y < other.y + other.height and other.y < panel.y + panel.height):
                    raise ValueError("Paint panels overlap")
        return layout


@dataclass(frozen=True)
class CameraBinding:
    camera_id: str
    yaw: float
    pitch: float
    center: tuple[float, float, float]
    extent: float


@dataclass(frozen=True)
class AdapterInput:
    candidate_id: str
    strategy: Strategy
    source: str
    geometry_revision: str
    capture: str
    mask_version: str
    layout: ViewLayout
    seed: int


def joint_group(camera_ids: list[str], strategy: Strategy, panel_size: int = 512) -> dict:
    if strategy == "pairs":
        raise ValueError("Legacy pairs require their original layout")
    if not camera_ids:
        raise ValueError("No camera can reach the selected texels")
    if panel_size not in (192, 256, 384, 512) or (strategy == "synchronized" and panel_size != 512):
        raise ValueError("Unsupported camera panel size for this strategy")
    limit = 26 if panel_size < 512 else 25
    if strategy == "whole_sheet" and len(camera_ids) > limit:
        raise ValueError(f"Complete coverage needs {len(camera_ids)} views; this camera size supports at most {limit}")
    columns = 4 if len(camera_ids) <= 16 else 5 if len(camera_ids) <= 25 else 6
    panels = tuple(PanelRect(key, (i % columns) * panel_size, (i // columns) * panel_size, panel_size, panel_size)
                   for i, key in enumerate(sorted(camera_ids)))
    rows = columns if strategy == "whole_sheet" and len(panels) <= 25 else (len(panels) + columns - 1) // columns
    layout = ViewLayout(1, columns * panel_size, rows * panel_size, panels)
    return {"id": "complete", "views": [p.camera_id for p in panels],
            "overlap_texels": 0, "layout": layout.to_dict()}


def group_layout(group: dict) -> ViewLayout:
    if "layout" in group:
        return ViewLayout.from_dict(group["layout"])
    panels = tuple(PanelRect(key, i * 704, 0, 704, 704) for i, key in enumerate(group["views"]))
    return ViewLayout(1, len(panels) * 704, 704, panels)
