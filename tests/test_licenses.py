"""Licence gate (IMPLEMENTATION.md §3.8): commercial-only, nothing from PLAN §6 "never"."""

import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# PLAN.md §6 "Never used" (lowercase substrings of a row name).
NEVER = [
    "rmbg-2.0",
    "nvdiffrast",
    "nvdiffrec",
    "flux.1-dev",
    "flux.2-dev",
    "kontext-dev",
    "klein-9b",
    "qwen-image-2.1",
    "smpl",
    "amass",
    "humanml3d",
    "gvhmr",
    "genmo",
    "riganything",
    "partpacker",
    "fastmesh",
    "meshanything",
    "partfield",
    "partuv",
    "bandai",
    "lafan",
    "bones-seed",
    "make-it-animatable",
    "hunyuan",
    "hy-motion",
    "ultrashape",
    "x-part",
    "sam3d-part",
    "xformers",
    "flash-attn",
    "flash_attn",
    "pymeshlab",
    "meshlib",
]
EXPERIMENTAL_ALLOWED = {"tencent/hunyuan3d-2.1"}  # IMPLEMENTATION.md MX1


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.lower())


def rows():
    return yaml.safe_load((ROOT / "licenses.yaml").read_text())


def test_rows_are_commercial_and_not_never():
    for r in rows():
        assert {"name", "kind", "license", "commercial"} <= r.keys(), r
        name = r["name"].lower()
        if r.get("experimental"):
            assert name in EXPERIMENTAL_ALLOWED, f"unknown experimental engine: {r}"
            continue
        assert r["commercial"] is True, f"not commercial: {r}"
        assert not r.get("region_note"), f"region-restricted rows must be experimental: {r}"
        assert not any(bad in name for bad in NEVER), f"PLAN §6 never-list: {r}"


def test_every_direct_dependency_has_a_row():
    # ponytail: direct dependencies only; transitive ones are reviewed when a direct one is added
    known = {norm(r["name"]) for r in rows()}
    py = tomllib.loads((ROOT / "pyproject.toml").read_text())
    reqs = py["project"]["dependencies"] + [r for g in py["dependency-groups"].values() for r in g]
    deps = {norm(re.match(r"[A-Za-z0-9._-]+", r).group()) for r in reqs}
    pkg = ROOT / "ui" / "package.json"
    if pkg.exists():
        js = json.loads(pkg.read_text())
        deps |= {norm(n) for n in {**js.get("dependencies", {}), **js.get("devDependencies", {})}}
    assert not deps - known, f"add licenses.yaml rows for: {sorted(deps - known)}"
