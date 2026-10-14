# SPDX-License-Identifier: GPL-3.0-or-later
"""in: [.glb/.fbx/.obj/.stl] → result.json {"report": mesh_report}; the caller turns it into pass/warn/fail."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import done, import_mesh, job, mesh_report

j = job()
done(j, {"report": mesh_report(import_mesh(j["in"][0]))})
