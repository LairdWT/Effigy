"""M7: CREDITS.txt / LICENSES.json come from the version chain's meta.licenses."""

import pytest

from steps._common import StepError
from steps.export import credits

ROWS = [
    {"name": "facebook/dinov3-vitl16", "license": "DINOv3", "attribution": "Built with DINOv3"},
    {
        "name": "clip/walk_cycle",
        "license": "CC-BY-4.0",
        "attribution": "Walk cycle by A. Animator (CC BY 4.0)",
    },
    {"name": "microsoft/TRELLIS.2-4B", "license": "MIT", "attribution": ""},
    {"name": "unused", "license": "MIT"},
]


def test_credits_collect_every_attribution():
    names = [
        "microsoft/TRELLIS.2-4B",
        "facebook/dinov3-vitl16",
        "clip/walk_cycle",
        "facebook/dinov3-vitl16",
    ]
    text, used = credits(names, ROWS)
    assert "Built with DINOv3\n" in text and "Walk cycle by A. Animator (CC BY 4.0)\n" in text
    assert sorted(r["name"] for r in used) == sorted(set(names))


def test_unknown_component_fails():
    with pytest.raises(StepError, match="licenses.yaml"):
        credits(["mystery/model"], ROWS)
