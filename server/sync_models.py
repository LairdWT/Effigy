"""Read-only owner of the isolated SyncMVD runtime and pinned snapshot bindings."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from server import settings


@dataclass(frozen=True)
class SyncSnapshot:
    path: Path
    repo: str
    revision: str


@dataclass(frozen=True)
class SyncComponents:
    python: Path
    source_revision: str
    sd15: SyncSnapshot
    normal: SyncSnapshot


def resolve() -> SyncComponents:
    file = settings.ROOT / "syncmvd.local.json"
    if not file.is_file():
        raise FileNotFoundError("SyncMVD is not provisioned. Run tools/provision_syncmvd.py --online separately")
    value = json.loads(file.read_text(encoding="utf-8"))
    if not value.get("ready"):
        raise FileNotFoundError("SyncMVD's pinned SD1.5 or normal-ControlNet snapshot is incomplete. Run tools/provision_syncmvd.py --online separately; other adapters remain independent")
    python = Path(value["python"])
    if not python.is_file():
        raise FileNotFoundError("SyncMVD's isolated interpreter is missing; rerun explicit provisioning")
    owned = settings.models_root().resolve()
    snapshots: dict[str, SyncSnapshot] = {}
    for key in ("sd15", "normal"):
        row = value[key]
        root = Path(row["path"]).resolve()
        if not root.is_relative_to(owned):
            raise PermissionError("SyncMVD snapshot resolves outside the configured owned model store")
        for relative, size in row["files"].items():
            component = (root / relative).resolve()
            if not component.is_relative_to(root):
                raise PermissionError("SyncMVD component escapes its snapshot")
            if not component.is_file() or component.stat().st_size != size:
                raise FileNotFoundError(f"Pinned SyncMVD component is unavailable: {key}/{relative}")
        snapshots[key] = SyncSnapshot(root, row["repo"], row["revision"])
    return SyncComponents(python, value["source_revision"], snapshots["sd15"], snapshots["normal"])
