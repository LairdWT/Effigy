"""run.bat and tools/package.py: is ui/dist older than the UI's source (a pull brought UI changes)? Exit 0
up to date (also with no source at all: the portable zip ships the built UI only), 1 rebuild, 2 `npm ci`
first (node_modules missing or older than package-lock.json). Both used to build only when ui/dist was
missing, so the owner kept a day-old UI through a restart. ponytail: the source is ui/src, index.html and
the lock; a change to the build config alone (vite.config.ts, tsconfig) needs ui/dist deleted."""

import sys
from pathlib import Path


def stale(ui: Path) -> int:
    built, lock = ui / "dist" / "index.html", ui / "package-lock.json"
    source = [p for p in [*(ui / "src").rglob("*"), ui / "index.html", lock] if p.is_file()]
    if built.is_file() and (
        not source or built.stat().st_mtime >= max(p.stat().st_mtime for p in source)
    ):
        return 0
    installed = ui / "node_modules" / ".package-lock.json"
    return 2 if not installed.is_file() or installed.stat().st_mtime < lock.stat().st_mtime else 1


if __name__ == "__main__":
    code = stale(Path(__file__).resolve().parent.parent / "ui")
    if code:
        print(
            "the UI's source is newer than ui/dist: building it"
            + (", its packages first" if code == 2 else "")
        )
    sys.exit(code)
