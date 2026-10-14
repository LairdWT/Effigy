"""GPU report (research 16, M46): how this computer's GPU runs the app's GPU steps, as a file for the developer, so
the bigger settings get numbers from cards other than the 16 GB reference laptop. Start the app first (run.bat),
then in the app's folder:

    uv run python -m tools.gpu_report           # 20–40 minutes; writes gpu-report-<card>-<date>.json here
    uv run python -m tools.gpu_report --send    # the same, then opens a GitHub issue with the report filled in
    uv run python -m tools.gpu_report --send gpu-report-....json    # send a report made before, no run
    uv run python -m tools.gpu_report --probes fast,faithful    # only these probes

Every probe is an ordinary job on a scratch asset, so the app's safeguards hold (M45: the pre-flight refusal, the
VRAM cap, the RAM check): a setting too big for the card ends refused or in a clean out-of-memory error, which is a
result too. A probe whose models are not downloaded is skipped. The report holds the card, driver, RAM, OS and, per
probe, its outcome, seconds and VRAM peaks; no pictures, file names or paths. The scratch asset is deleted at the
end (Recently deleted keeps it a while).
"""

import argparse
import json
import platform
import re
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

from server import settings
from server.presets import PRESETS, ram_gb
from tools.bench import ROOT, call, gpu_query, run_job, version_meta

ISSUES = "https://github.com/SifuInTheShell/Effigy/issues/new"
IMAGE = ROOT / "tests" / "fixtures" / "golden" / "barrel.png"
SEED = 7
FAST, FAITHFUL = (PRESETS["trellis2"][w] | {"seed": SEED} for w in ("fast", "faithful"))
# (name, step, params, the model groups it needs (any one), the probe whose version it runs on). In this order the
# Fast worker stays resident through its probes, and each family's riskiest setting comes last.
PROBES = [
    ("prep", "prep", {}, "fast faithful", "upload"),
    ("fast", "trellis2", FAST, "fast", "prep"),
    ("fast-1536", "trellis2", FAST | {"pipeline_type": "1536_cascade"}, "fast", "prep"),
    ("clean", "clean", {}, None, "fast"),
    ("remesh", "remesh", {"faces": 10_000}, None, "clean"),
    ("uv", "uv", {}, None, "remesh"),
    ("bake", "bake", {"texture_size": 2048}, None, "uv"),
    ("refine", "refine", {"seed": SEED, "tile": "lite"}, "refine", "bake"),
    (
        "refine-full",
        "refine",
        {"seed": SEED, "tile": "full"},
        "refine-full",
        "bake",
    ),  # M46c, where it fits
    ("faithful", "trellis2", FAITHFUL, "faithful", "prep"),
    (
        "faithful-20-4k",
        "trellis2",
        FAITHFUL | {"steps": 20, "texture_size": 4096},
        "faithful",
        "prep",
    ),
    ("faithful-1536", "trellis2", FAITHFUL | {"pipeline_type": "1536_cascade"}, "faithful", "prep"),
    # M46a: offloaded (every card), then the whole model on the GPU where the budget should hold it (NEED)
    ("canon", "canon", {"seed": SEED, "offload": True}, "canon-flux", "prep"),
    ("canon-gpu", "canon", {"seed": SEED, "offload": False}, "canon-flux", "prep"),
    (
        "motion",
        "motion",
        {"prompt": "A person walks forward.", "seed": SEED, "offload": True},
        "kimodo",
        None,
    ),
    (
        "motion-gpu",
        "motion",
        {"prompt": "A person walks forward.", "seed": SEED, "offload": False},
        "kimodo",
        None,
    ),
]
# What the app's pre-flight does not size yet (VRAM_GB keys trellis2 on its weights only, M46b): the least VRAM (GB)
# a probe needs. Fast at 1536 filled the 16 GB laptop's card to 15.5 of 15.9 GB (torch 12.6) and once ended the
# worker without a word (docs/bench/m46.md); a card with a smaller budget skips these instead of going to the edge.
# The -gpu probes: steps/canon.GPU_GB and steps/motion.ENCODER_GPU_GB, the budgets at which the steps stop offloading.
# refine-full: the full Tile's 15.57 GB reserved on the laptop (m43b), the one run that restarted it before the cap.
NEED = {
    "fast-1536": 15.1,
    "faithful-1536": 15.1,
    "canon-gpu": 17.0,
    "motion-gpu": 18.0,
    "refine-full": 15.6,
}


def installed(api: str) -> set[str]:
    """The model groups whose every row is downloaded."""
    rows = call(api, "GET", "/api/models")
    return {
        g
        for r in rows
        for g in r["groups"]
        if all(x["installed"] for x in rows if g in x["groups"])
    }


def private(text: str) -> str:
    """No user name or install folder in what leaves the machine: either slash, any case, any Users/<name>."""
    for path, name in ((ROOT, "<app>"), (Path.home(), "~")):
        for form in {str(path), path.as_posix()}:
            text = re.sub(re.escape(form), name, text, flags=re.IGNORECASE)
    return re.sub(r"(?i)(users[\\/])[^\\/\s]+", r"\1<user>", text)


def machine(api: str) -> dict:
    name, mib, driver, cap = (
        gpu_query("name,memory.total,driver_version,compute_cap") or ",,,"
    ).split(",")
    gpu = next((c for c in call(api, "GET", "/api/setup/machine") if c["id"] == "gpu"), {})
    try:
        from server.jobs import _python

        torch = subprocess.run(
            [_python("trellis2"), "-c", "import torch; print(torch.__version__)"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        ).stdout.strip()
    except (OSError, RuntimeError, subprocess.SubprocessError):
        torch = None
    version = ROOT / "VERSION"
    app = (
        version.read_text().strip()
        if version.is_file()
        else _git("describe", "--always", "--dirty")
    )
    return {
        "app": app,
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "gpu": name.strip(),
        "vram_gb": round(float(mib) / 1024, 2) if mib.strip() else None,
        "driver": driver.strip(),
        "compute_cap": cap.strip(),
        "budget_gb": gpu.get("budget_gb"),
        "ram_gb": round(ram_gb()[0], 1),
        "os": platform.platform(),
        "torch": torch,
    }


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def probe(
    api: str, asset: str, versions: dict, have: set, spec: tuple, budget: float | None
) -> dict:
    name, step, params, groups, on = spec
    row = {"name": name, "step": step, "params": params}
    if groups and not have & set(groups.split()):
        return row | {"status": "skipped", "message": f"not downloaded: {groups}"}
    if (need := NEED.get(name)) and (budget or 0) < need:
        return row | {
            "status": "skipped",
            "message": f"needs about {need} GB, this card allows {budget}",
        }
    if on and on not in versions:
        return row | {"status": "skipped", "message": f"needs {on}"}
    print(f"{name} ...", flush=True)
    before = gpu_query("memory.used")
    try:
        job, secs, peak = run_job(api, asset, step, versions.get(on), dict(params))
    except (
        OSError
    ) as e:  # the app refused the request itself (an older app, say): on to the next probe
        return row | {"status": "error", "message": private(str(e))[:400]}
    row |= {"status": job["status"], "seconds": secs, "gpu_peak_gb": peak}
    row["gpu_before_gb"] = round(int(before) / 1024, 2) if before else None
    if job["status"] == "done":
        versions[name] = job["version"]
        m = version_meta(api, asset, job["version"]).get("metrics", {})
        return row | {
            "torch_peak_gb": m.get("peak_vram_gb", m.get("vram_peak_gb")),  # bake: vram_peak_gb
            "torch_reserved_gb": m.get("peak_reserved_gb"),
            # M46a: where the model ran (canon's offload, Kimodo's text encoder), and a resident worker's load
            **{
                k: m[k]
                for k in ("offload", "encoder_device", "generate_seconds", "seconds_edit")
                if k in m
            },
        }
    error = job.get("error") or {}
    return row | {"error": error.get("code"), "message": private(error.get("message") or "")[:400]}


def table(report: dict) -> str:
    lines = [
        (
            f"{report['gpu']} ({report['vram_gb']} GB, driver {report['driver']}, sm {report['compute_cap']}), "
            f"budget {report['budget_gb']} GB, {report['ram_gb']} GB RAM, {report['os']}, torch {report['torch']}"
        ),
        "",
        "| probe | result | s | GPU peak GB | torch peak GB |",
        "|---|---|---|---|---|",
    ]
    for p in report["probes"]:
        result = (
            p["status"] if p["status"] == "done" else f"{p['status']}: {p.get('message', '')[:120]}"
        )
        lines.append(
            f"| {p['name']} | {result} | {p.get('seconds', '')} | {p.get('gpu_peak_gb', '')} "
            f"| {p.get('torch_peak_gb') or ''} |"
        )
    return "\n".join(lines)


def issue_url(report: dict) -> str:
    """A new issue with the report filled in; without the JSON when that makes the link too long for a browser
    (then the file is attached by hand)."""
    title = f"GPU report: {report['gpu']}"
    full = f"{table(report)}\n\n```json\n{json.dumps(report, separators=(',', ':'))}\n```"
    for body in (full, f"{table(report)}\n\n(The JSON file is attached.)"):
        body = private(body)  # again: a report from an older tool, or edited by hand
        url = f"{ISSUES}?{urllib.parse.urlencode({'title': title, 'body': body})}"
        if len(url) <= 8000:
            return url
    return f"{ISSUES}?{urllib.parse.urlencode({'title': title})}"


def report(api: str, out: Path | None, only: set[str] | None, keep: bool) -> tuple[dict, Path]:
    rep = machine(api) | {"probes": []}
    slug = re.sub(r"\W+", "-", rep["gpu"] or "gpu").strip("-").lower()
    out = out or Path(f"gpu-report-{slug}-{time.strftime('%Y%m%d-%H%M')}.json")
    have = installed(api)
    asset = call(api, "POST", "/api/assets", {"name": "gpu report"})["id"]
    try:
        up = call(api, "PUT", f"/api/assets/{asset}/upload/{IMAGE.name}", raw=IMAGE.read_bytes())
        versions = {"upload": up["version"]}
        for spec in PROBES:
            if only is None or spec[0] in only:
                rep["probes"].append(probe(api, asset, versions, have, spec, rep["budget_gb"]))
                # after every probe: an interrupted run keeps what ran
                out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    finally:
        if not keep:
            for _ in range(
                20
            ):  # after Ctrl+C the cancelled job takes a moment to stop (409 till then)
                try:
                    call(api, "DELETE", f"/api/assets/{asset}")
                    break
                except OSError:
                    time.sleep(0.5)
            else:
                print(f"could not delete the scratch asset {asset!r}: delete it in the library")
    return rep, out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--api", default=f"http://127.0.0.1:{settings.port()}")  # Setup → App address
    ap.add_argument("--out", type=Path)
    ap.add_argument(
        "--probes", help="comma-separated probe names: " + ", ".join(p[0] for p in PROBES)
    )
    ap.add_argument("--keep", action="store_true", help="keep the scratch asset")
    ap.add_argument(
        "--send",
        nargs="?",
        const=True,
        type=Path,
        help="open a GitHub issue with the report filled in; with a report file: send that one, no run",
    )
    a = ap.parse_args(argv)
    only = set(a.probes.split(",")) if a.probes else None
    if only and (bad := only - {p[0] for p in PROBES}):
        ap.error(f"no probe {', '.join(sorted(bad))}")
    if isinstance(a.send, Path):
        webbrowser.open(issue_url(json.loads(a.send.read_text(encoding="utf-8"))))
        return 0
    rep, out = report(a.api, a.out, only, a.keep)
    print(f"\n{table(rep)}\n\nReport: {out.resolve()}")
    if a.send:
        webbrowser.open(issue_url(rep))
    else:
        print(
            f'Send it to the developer: attach the file, or: "{sys.executable}" -m tools.gpu_report --send {out}'
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
