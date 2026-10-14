"""The creature fit on Mesh2Motion's sample meshes (IMPLEMENTATION.md M41): the table every creature PR shows
before and after.

    uv run python -m tools.creature_bench [fox kaiju …] [--glb library/cat/029_rig_fit/mesh.glb=fox] [--out docs/bench/m41a.md]

Each pinned sample mesh (CC0, fetched once into the temp folder) is centred on its base and turned 0/90/180/270 degrees;
rig_fit's fit runs on it unchanged: `yaw` (right when it equals the turn), the joints inside before and after rig_fit's
snap, and Check fit's score (steps/_rig.fit_quality). `--glb path=template` adds a mesh of your own at its own
turn (the owner's cat: no known facing, so its yaw is only shown). Runs in the ML venv; no GPU, no Blender.
"""

import argparse
import hashlib
import tempfile
import urllib.request
from pathlib import Path

import numpy as np

from steps import _rig, _templates
from steps._mesh import read_glb, weld

PIN = _templates.PIN
SAMPLES = {  # id: SHA-256 of static/models/model-<id>.glb at the pinned commit
    "fox": "e7fa40f76fbfc3b2c97690d0716e0854850c796dea2181842d01b60ec6d62514",
    "horse": "8db92371d4f303894fa64dc4c53028ee3312cc072ee7b1ecf4d7054988f0d1ed",
    "bird": "6d66addfe2108c420abd35c9c98a0084dbcb20ed33129e619df7f8c5a8e7d84f",
    "kaiju": "720fa706d11815c7360b7ac9781bcc2564d77177ca2b3dba5c4ef5db0dd0927a",
    "shark": "cc947584ebb08024c8fc49dc207ff6162c93554fb17b0028ee4eb6131fe809a6",
    "dragon": "4ea7600bdad99d234bfb21396e597b41ba36732ee22592a7894b96664fd01c39",
    "spider": "7c2e298c101f74956153b5932e3667b537c824f28e472f6c8e3df0c45f1950c7",
    "snake": "07fd75c7b6645247f4d0545e2355aadf1ddf5357387041a1aa4d5eaa12668cdc",
}
CACHE = Path(tempfile.gettempdir()) / "effigy_creature_bench"


def sample(name: str) -> Path:
    path = CACHE / f"model-{name}.glb"
    if not (path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == SAMPLES[name]):
        data = urllib.request.urlopen(f"{PIN}/static/models/model-{name}.glb", timeout=60).read()
        if hashlib.sha256(data).hexdigest() != SAMPLES[name]:
            raise SystemExit(f"model-{name}.glb: SHA-256 mismatch")
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return path


def measure(template: str, v: np.ndarray, f: np.ndarray, turn: float | None):
    """(yaw, raw inside, inside after the snap, joints, score, right) for the fit of `template` on the mesh."""
    bones, yaw = _templates.fit(template, v, None, f)
    names = list(bones)
    pos = np.array([bones[n]["position"] for n in names])
    raw = _rig.inside(v, f, pos)
    reach = 0.05 * float(np.ptp(v[:, 1]))  # rig_fit's snap
    for i in np.flatnonzero(~raw):
        if bones[names[i]]["parent"]:
            pos[i] = _rig.snap_inside(v, f, pos[i], reach)
    joints = [{"name": n, "parent": bones[n]["parent"], "position": p} for n, p in zip(names, pos)]
    q = _rig.fit_quality(v, f, joints)
    right = None if turn is None else abs((yaw - turn + 180) % 360 - 180) < 10
    return (
        yaw,
        int(sum(r for r, n in zip(raw, names) if bones[n]["parent"])),
        q["inside"],
        q["joints"],
        q["score"],
        right,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("templates", nargs="*", help="sample meshes to run (default: all eight)")
    ap.add_argument("--glb", action="append", default=[], metavar="PATH=TEMPLATE")
    ap.add_argument("--out", help="also write the table here (Markdown)")
    a = ap.parse_args()
    runs = []  # (label, template, mesh path, turns, a pinned sample)
    for name in a.templates or SAMPLES:
        runs.append((name, name, sample(name), (0, 90, 180, 270), True))
    for g in a.glb:
        path, template = g.rsplit("=", 1)
        runs.append((Path(path).parent.name, template, Path(path), (0,), False))
    rows = [
        "| mesh | template | turn | yaw | facing | inside raw | inside after snap | score |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label, template, path, turns, sample_mesh in runs:
        v, f = weld(*read_glb(path)[:2])
        if sample_mesh:  # centred on its base, as the app's generated meshes are
            v = v - [
                (v[:, 0].min() + v[:, 0].max()) / 2,
                v[:, 1].min(),
                (v[:, 2].min() + v[:, 2].max()) / 2,
            ]
        for turn in turns:
            yaw, raw, inside, n, score, right = measure(
                template, v @ _templates._yaw(turn).T, f, turn if sample_mesh else None
            )
            ok = {None: "-", True: "ok", False: "WRONG"}[right]
            rows.append(
                f"| {label} | {template} | {turn} | {yaw:.1f} | {ok} | {raw}/{n} | {inside}/{n} | {score} |"
            )
    table = "\n".join(rows)
    print(table)
    if a.out:
        Path(a.out).write_text(table + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
