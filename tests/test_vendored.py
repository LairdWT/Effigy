"""The vendored engines are complete in git: a bare `models/` ignore rule once swallowed both `models/`
packages, so neither generator could import outside the machine that vendored them."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vendored_models_packages_are_tracked():
    for pkg in ("engine/trellis2/trellis2", "engine/pixal3d/pixal3d"):
        init = f"{pkg}/models/__init__.py"
        assert (ROOT / init).is_file(), init
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", init], cwd=ROOT, check=False
        ).returncode
        assert ignored == 1, f"{init} is git-ignored"
