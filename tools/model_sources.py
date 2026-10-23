"""Provision exact published model objects from an explicit pinned public source."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from server import model_bindings, runtime_policy

SOURCES: Path = Path(__file__).with_name("model_sources.json")


def pin_main(repo: str, revision: str) -> Path:
    root: Path = model_bindings.require_owned("hub/models--" + repo.replace("/", "--"))
    reference: Path = root / "refs" / "main"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_text(revision, encoding="ascii")
    return root / "snapshots" / revision


def fetch_mirror(repo: str, revision: str) -> bool:
    runtime_policy.require_provisioning()
    sources: dict[str, Any] = json.loads(SOURCES.read_text(encoding="utf-8"))
    source: dict[str, Any] | None = sources.get(repo + "@" + revision)
    if source is None:
        return False
    from huggingface_hub import HfApi, snapshot_download

    info = HfApi().model_info(source["repository"], revision=source["revision"], files_metadata=True)
    files = {file.rfilename: file for file in info.siblings}
    for name, expected in source["objects"].items():
        remote = files.get(name)
        if remote is None:
            raise RuntimeError(f"Mirror file missing: {name}")
        actual = remote.lfs.sha256 if remote.lfs else remote.blob_id
        if actual != expected:
            raise RuntimeError(f"Mirror published object mismatch: {name}")
    destination: Path = model_bindings.require_owned(
        "hub/models--" + repo.replace("/", "--") + "/snapshots/" + revision
    )
    snapshot_download(
        source["repository"], revision=source["revision"],
        local_dir=destination, allow_patterns=list(source["objects"]), max_workers=4,
    )
    receipt: dict[str, Any] = {
        "requested_repository": repo, "requested_revision": revision,
        "download_repository": source["repository"], "download_revision": source["revision"],
        "published_objects": source["objects"], "omitted_nonruntime_files": source["omitted_nonruntime_files"],
    }
    (destination / "effigy_source.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    pin_main(repo, revision)
    print(f"PUBLIC SOURCE {source['repository']} -> {repo} (matching runtime objects)", flush=True)
    return True
