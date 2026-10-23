"""One owner for read-only borrowed models and writable installed models."""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from server import settings


@dataclass(frozen=True, slots=True)
class ModelBinding:
    path: Path
    owned: bool
    revision: str = ""
    source_revision: str = ""
    recorded_objects: tuple[tuple[str, str], ...] = ()


@lru_cache(maxsize=1)
def borrowed() -> Mapping[str, ModelBinding]:
    config: Path = settings.ROOT / "model-bindings.local.json"
    if not config.is_file():
        return MappingProxyType({})
    data = json.loads(config.read_text(encoding="utf-8"))
    result: dict[str, ModelBinding] = {}
    for name, value in data.items():
        if Path(name).is_absolute() or len(Path(name).parts) != 1:
            raise ValueError("Borrowed model names must be single relative folder names")
        path: Path = Path(value["path"])
        if not path.is_absolute():
            raise ValueError("Borrowed model paths must be absolute")
        result[name] = ModelBinding(
            path.resolve(), False, str(value["revision"]),
            str(value.get("source_revision", value["revision"])),
            tuple(value.get("recorded_objects", {}).items()),
        )
    return MappingProxyType(result)


def resolve(relative: str) -> ModelBinding:
    rel: Path = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("Model path must be a non-empty relative path without parent traversal")
    shared: ModelBinding | None = borrowed().get(rel.parts[0])
    if shared is not None:
        target: Path = (shared.path / Path(*rel.parts[1:])).resolve()
        if not target.is_relative_to(shared.path):
            raise PermissionError("Borrowed model link escapes its declared root")
        return replace(shared, path=target)
    root: Path = settings.models_root().resolve()
    target = (root / rel).resolve()
    if not target.is_relative_to(root):
        raise PermissionError("Owned model path resolves outside the owned model store")
    for binding in borrowed().values():
        if target.is_relative_to(binding.path):
            raise PermissionError("Owned path aliases a borrowed model")
    return ModelBinding(target, True)


def require_owned(relative: str) -> Path:
    binding: ModelBinding = resolve(relative)
    if not binding.owned:
        raise PermissionError("Shared model is read-only; operation refused")
    return binding.path


def validate_borrowed(folder: str, revision: str, rows: dict[str, list]) -> Path | None:
    binding: ModelBinding = resolve(folder)
    if binding.owned:
        return None
    if binding.revision != revision:
        raise ValueError(f"Borrowed revision mismatch: {folder}")
    objects: dict[str, str] = dict(binding.recorded_objects)
    for relative, (size, _) in rows.items():
        path: Path = resolve(str(Path(folder) / relative)).path
        metadata: Path = binding.path / ".cache" / "huggingface" / "download" / (relative + ".metadata")
        if not path.is_file() or path.stat().st_size != size:
            raise ValueError(f"Borrowed file missing or wrong size: {folder}/{relative}")
        if not metadata.is_file():
            raise ValueError(f"Borrowed revision metadata missing: {folder}/{relative}")
        recorded: list[str] = metadata.read_text(encoding="utf-8").splitlines()
        if not recorded or recorded[0] != (binding.source_revision or revision):
            raise ValueError(f"Borrowed revision metadata mismatch: {folder}/{relative}")
        if binding.source_revision != revision and (
            len(recorded) < 2 or objects.get(relative) != recorded[1]
        ):
            raise ValueError(f"Borrowed published-object metadata mismatch: {folder}/{relative}")
    return binding.path
