"""Where the disk space goes, and getting it back (IMPLEMENTATION.md M35a).

Every big thing the app keeps, sized in one pass (6.7 s on the reference laptop, so on request, cached): the
model groups (from the pinned entries' own files), the Python environments, the library (the assets, the
archived ones, the trash), the bundled tools, and the free space of every drive involved.

Sizes count what removing an item would free: files with a single link. The environments share files with
each other and with uv's cache through hard links (torch_cpu.dll is one file in .venv-ml and .venv-skin),
so a link that has others counts once, under "shared". Junctions and symlinks are never followed.

Removing data: an asset or an environment is first renamed out of the way (atomic: it fails whole while a
file is open, nothing half-deleted stays in use), then deleted; what could not be deleted is reported and
listed for the next cleanup.
"""

import json
import os
import shutil
import subprocess
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from server import jobs, library, model_bindings, models
from server.library import ApiError

ROOT = Path(__file__).resolve().parents[1]
# the environments and what each one is for; the app's own and the core one stay
VENVS = {
    ".venv": ("the app itself", False),
    ".venv-ml": ("making and preparing models", False),
    ".venv-skin": ("skinning with SkinTokens", True),
    ".venv-kimodo": ("text to motion", True),
    ".venv-parts": ("parts", True),
    ".venv-gemx": ("motion from video", True),
    ".venv-moge": ("depth for parallax layers", True),
    ".venv-hunyuan": ("the experimental Hunyuan engine", True),
}
TOOLS = {"python": "The bundled Python", "blender": "Blender", "gltfpack": "gltfpack"}
LOW_BYTES, LOW_SHARE = 20 * 2**30, 0.10  # a drive is low under 20 GB or 10 % free
MAX_AGE = 300  # seconds a scan stays fresh
GONE = ".deleting"  # an environment renamed out of the way, waiting to be deleted
_lock = threading.Lock()
_last: dict | None = None


def _existing(p: Path) -> Path:
    p = Path(os.path.abspath(p))
    while not p.exists() and p.parent != p:
        p = p.parent
    return p


def _drive(p: Path) -> str:
    """The drive (Windows) or mount point (elsewhere) a path is on, even before the path exists."""
    p = _existing(p)
    if os.name == "nt":
        return p.anchor
    dev = p.stat().st_dev
    while p.parent != p and p.parent.stat().st_dev == dev:
        p = p.parent
    return str(p)


def drives() -> list[dict]:
    """Total and free space of every drive the app writes to; `low` under 20 GB or 10 % free."""
    out = {}
    for p in (ROOT, models.root(), library.root()):
        d = _drive(p)
        if d not in out:
            u = shutil.disk_usage(d)
            low = u.free < LOW_BYTES or u.free < LOW_SHARE * u.total
            out[d] = {"drive": d, "total": u.total, "free": u.free, "low": low}
    return list(out.values())


def _walk(path):
    """os.walk without going into junctions or symlinked folders (os.walk follows junctions on Windows)."""
    for d, dirs, names in os.walk(path):
        dirs[:] = [x for x in dirs if not os.path.isjunction(os.path.join(d, x))]
        yield d, dirs, names


class _Sizer:
    """Single-link bytes per path; multi-link files counted once, as shared."""

    def __init__(self):
        self.seen: set = set()
        self.shared = 0

    def file(self, f) -> int:
        try:
            st = os.stat(f, follow_symlinks=False)
        except OSError:
            return 0
        if st.st_nlink > 1:
            if (st.st_dev, st.st_ino) not in self.seen:
                self.seen.add((st.st_dev, st.st_ino))
                self.shared += st.st_size
            return 0
        return st.st_size

    def tree(self, path: Path) -> int:
        return sum(self.file(os.path.join(d, n)) for d, _, names in _walk(path) for n in names)


def _assets() -> list[tuple[str, dict]]:
    """(folder name, asset.json) for every asset folder with a valid id: the folder is what gets deleted."""
    lib = library.root()
    out = []
    for p in sorted(lib.glob("*/asset.json")) if lib.is_dir() else []:
        if library.ASSET_ID.match(p.parent.name):
            try:
                out.append((p.parent.name, json.loads(p.read_text(encoding="utf-8"))))
            except (OSError, ValueError):
                continue
    return out


def scan() -> dict:
    s, items = _Sizer(), []

    def item(key, kind, name, path, size, action=None):
        items.append(
            {
                "id": key,
                "kind": kind,
                "name": name,
                "bytes": size,
                "drive": _drive(path),
                "action": action,
            }
        )

    # model groups: each entry's own files; an entry several groups need is listed as shared by them
    groups, counted, borrowed_groups = defaultdict(int), set(), set()
    for e in models.entries():
        if not model_bindings.resolve(e["where"]).owned:
            borrowed_groups.add(tuple(e["groups"]))
        for f in models._files(e):
            counted.add(os.path.normcase(os.path.abspath(f)))
            groups[tuple(e["groups"])] += s.file(f)
    for gs, size in sorted(groups.items()):
        if size:
            one = len(gs) == 1
            name = f"Model files: {gs[0]}" if one else f"Model files shared by {' and '.join(gs)}"
            # a shared row removes what exactly those features share (the only Remove since Setup's model table)
            action = None if gs in borrowed_groups else f"group:{'+'.join(gs)}"
            if gs in borrowed_groups:
                name += " (includes read-only borrowed models)"
            item(f"models:{'+'.join(gs)}", "models", name, models.root(), size, action)
    other = sum(  # caches and leftovers in the models folder (unpacked code, kernel caches, old revisions)
        s.file(f)
        for d, _, names in _walk(models.root())
        for f in (os.path.join(d, n) for n in names)
        if os.path.normcase(os.path.abspath(f)) not in counted
    )
    if other:
        item("models:other", "models", "Other files in the models folder", models.root(), other)
    for v, (what, removable) in VENVS.items():
        if (ROOT / v).is_dir():
            action = f"venv:{v}" if removable else None
            item(
                f"venv:{v}", "venv", f"Python for {what} ({v})", ROOT / v, s.tree(ROOT / v), action
            )
    left = [p for p in ROOT.glob(f".venv*{GONE}") if p.is_dir()]
    if left:
        size = sum(s.tree(p) for p in left)
        item(
            "venv:leftovers",
            "venv",
            "Removed environments not fully deleted yet",
            ROOT,
            size,
            "leftovers",
        )
    if _own_cache():
        cache = _own_cache()
        item(
            "cache:uv",
            "cache",
            "Downloaded Python packages (uv's cache)",
            cache,
            s.tree(cache),
            "prune",
        )
    for t, what in TOOLS.items():
        if (ROOT / t).is_dir():
            item(f"tool:{t}", "tools", what, ROOT / t, s.tree(ROOT / t))
    lib = library.root()
    assets = [
        {
            "id": d,
            "name": a.get("name", d),
            "archived": bool(a.get("archived")),
            "bytes": s.tree(lib / d),
        }
        for d, a in _assets()
    ]
    live = [a for a in assets if not a["archived"]]
    arch = [a for a in assets if a["archived"]]
    item(
        "library:assets",
        "library",
        f"Your assets ({len(live)})",
        lib,
        sum(a["bytes"] for a in live),
    )
    if arch:  # deleted one by one, by name: the list is in "assets"
        size = sum(a["bytes"] for a in arch)
        item("library:archived", "library", f"Archived assets ({len(arch)})", lib, size)
    if (lib / "_trash").is_dir():
        size = s.tree(lib / "_trash")
        item(
            "library:trash",
            "library",
            "Deleted assets and versions (the trash)",
            lib,
            size,
            "trash",
        )
    if s.shared:
        name = "Python packages shared between environments and uv's cache"
        item("shared", "venv", name, ROOT, s.shared)
    items.sort(key=lambda i: -i["bytes"])
    return {
        "scanned": time.time(),
        "items": items,
        "assets": sorted(assets, key=lambda a: -a["bytes"]),
        "drives": drives(),
    }


def storage(refresh: bool = False) -> dict:
    global _last
    with _lock:  # one scan at a time; a fresh one is reused
        if refresh or not _last or time.time() - _last["scanned"] > MAX_AGE:
            t = time.time()
            _last = scan() | {"seconds": round(time.time() - t, 1)}
        return _last | {"drives": drives()}


def _own_cache() -> Path | None:
    """The app's own uv cache (the portable zip's `cache/`); a dev checkout's is the user's, not ours."""
    cache = Path(os.environ.get("UV_CACHE_DIR") or ROOT / "cache")
    return cache if cache.is_dir() and cache.resolve().is_relative_to(ROOT) else None


@contextmanager
def _quiet():
    """No step and no download while files go: the GPU lock held (every step runs under it, and a queued one
    waits), the resident worker stopped (it holds model files and its environment open)."""
    if models._downloading():
        raise ApiError(409, "busy", "a model download is running; clean up after it ends")
    if not jobs.GPU.acquire(blocking=False):
        raise ApiError(409, "busy", "a step is running; clean up after it ends")
    try:
        # ponytail: an install queued right now is caught here; one queued during the deletes is not (its
        # file download takes no lock, only its environment sync and repair deletes do); the window is the
        # deletes' few seconds
        if models._downloading():
            raise ApiError(409, "busy", "a model download started; clean up after it ends")
        jobs.evict()
        yield
    finally:
        jobs.GPU.release()


def _delete(path: Path) -> int:
    """Delete a tree; how many files could not be (open, read-only): they stay, for the next cleanup."""
    failed = []
    shutil.rmtree(path, onexc=lambda fn, p, exc: failed.append(p))
    return len(failed)


def cleanup(action: str) -> dict:
    """One cleanup (an item's `action`: trash, prune, leftovers, group:<g> or group:<g>+<g>... (the files exactly
    those groups share), venv:<name>, or archived:<asset> for one archived asset); the space it freed, the files
    that could not be deleted, a fresh scan."""
    before = sum(d["free"] for d in drives())
    kind, _, target = action.partition(":")
    lib, failed = library.root(), 0
    if kind == "trash" and (lib / "_trash").is_dir():
        failed = _delete(lib / "_trash")
    elif kind == "archived":
        d = library.asset_dir(target)  # a valid id and an existing folder, or 404
        a = json.loads((d / "asset.json").read_text(encoding="utf-8"))
        if not a.get("archived") or a.get("id", target) != target:
            raise ApiError(409, "not_archived", f"{target} is not an archived asset")
        with _quiet():
            if any(
                j.asset_id == target and j.status in ("queued", "running")
                for j in list(jobs.JOBS.values())
            ):
                raise ApiError(409, "busy", f"a step is queued or running on {target}")
            gone = (
                lib / "_trash" / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{target}_deleted"
            )
            gone.parent.mkdir(exist_ok=True)
            try:
                os.replace(d, gone)  # whole or not at all; a leftover stays in the trash
            except OSError as e:
                raise ApiError(409, "busy", f"{target} is in use (a file is open): {e}") from e
            failed = _delete(gone)
    elif kind == "prune":
        if not _own_cache():
            raise ApiError(400, "bad_request", "this install has no uv cache of its own to prune")
        try:
            r = subprocess.run(
                [jobs.uv(), "cache", "prune"],
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            raise ApiError(500, "failed", f"uv cache prune: {e}") from e
        if r.returncode:
            raise ApiError(500, "failed", f"uv cache prune: {r.stderr.strip()[-300:]}")
    elif kind == "leftovers":
        failed = sum(_delete(p) for p in ROOT.glob(f".venv*{GONE}") if p.is_dir())
    elif kind == "group" and set(gs := target.split("+")) <= {
        g for e in models.entries() for g in e["groups"]
    }:
        with (
            _quiet()
        ):  # the entries exactly these groups need; ones shared with others stay for them
            for i, e in enumerate(models.entries()):
                if e["groups"] == gs and models._files(e):
                    models.remove(i, locked=True)
    elif kind == "venv" and VENVS.get(target, ("", False))[1] and (ROOT / target).is_dir():
        with _quiet():
            gone = ROOT / f"{target}{GONE}"
            if gone.exists():
                _delete(gone)
            try:
                os.replace(ROOT / target, gone)  # fails whole while a file in it is open
            except OSError as e:
                raise ApiError(
                    409, "busy", f"{target} is in use (a program has a file open): {e}"
                ) from e
            failed = _delete(gone)
    else:
        raise ApiError(400, "bad_request", f"unknown cleanup {action!r}")
    freed = sum(d["free"] for d in drives()) - before
    return {"freed": max(freed, 0), "failed": failed, **storage(refresh=True)}
