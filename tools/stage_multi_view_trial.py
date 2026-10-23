"""Stage named multi-view source files into the existing trial; never provision."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "scratch" / "lanes" / "fibo2"
BACKEND = (
    "server/paint_sessions.py", "server/paint_routes.py", "server/app.py", "server/library.py",
    "server/jobs.py", "server/reference_models.py", "server/presets.py", "steps/_paint_set.py",
    "steps/paint_set.py", "steps/paint_generate.py", "steps/_paint_projection.py", "tools/native_reference_entry.py",
    "server/paint_contracts.py", "server/sync_models.py", "steps/reference.py",
    "steps/sync_paint.py", "steps/_sync_renderer.py", "steps/_sync_scheduler.py",
    "licenses/SyncMVD.txt",
    "steps/paint.py", "steps/_paint_mask.py", "steps/_paint_seams.py", "steps/describe.py",
    "server/finish_contracts.py", "steps/_finish_plan.py", "steps/_finish_cut.py",
    "steps/paint_finish.py", "steps/paint_finish_generate.py",
    "steps/uv_context.py", "steps/_paint_handoff.py",
    "steps/_uv_transfer.py", "steps/repair_baseline.py",
    "server/authoring_contracts.py", "tools/blender_prepare.py", "server/blender_client.py",
    "steps/_sampling_plan.py",
)
UI = ("ui/src/MultiViewPaint.tsx", "ui/src/AuthoringWorkspace.tsx", "ui/src/AutomaticFinish.tsx", "ui/src/multi-view-paint.css", "ui/src/multi-view-api.ts", "ui/src/viewer/Viewer.ts", "ui/src/Compare.tsx", "ui/src/SurfacePaint.tsx", "ui/src/PaintSelection.tsx", "ui/src/LocalRuntimeStatus.tsx", "ui/src/events.ts")


def replace(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Trial staging anchor is ambiguous or absent: {old[:80]}")
    return text.replace(old, new, 1)


def backend(relative: str, text: str) -> str:
    if relative == "server/app.py":
        text = replace(text, "def run_step(asset_id: str, step: str, body: RunStep):\n",
                       'def run_step(asset_id: str, step: str, body: RunStep):\n'
                       '    if step not in ("paint", "reference", "import_model", "describe", "uv_context", "repair_baseline"):\n'
                       '        raise ApiError(400, "unsupported", "Use the multi-view session controls for batch painting")\n')
    elif relative == "server/jobs.py":
        text = replace(text, 'SERVE = {"trellis2", "concepts", "motion", "reference"}', 'SERVE = {"trellis2", "concepts", "motion"}')
        text = replace(text, 'return ROOT / venv /', 'return Path(settings.read()["environment_root"]) / venv /')
    elif relative == "server/reference_models.py":
        text = replace(text, 'Literal["krea", "qwen", "flux", "moss"]', 'Literal["krea", "qwen", "flux", "moss", "fibo2"]')
        text = replace(text, 'MODELS: tuple[ReferenceModel, ...] = (',
                       'MODELS: tuple[ReferenceModel, ...] = (\n'
                       '    ReferenceModel("fibo2-turbo", "FIBO 2 Edit Turbo (INT8 trial)", "edit",\n'
                       '                   "trial-fibo/diffusion_models/fibo2_edit_turbo_int8_convrot.safetensors",\n'
                       '                   "shared-text-encoders/qwen3vl_4b_fp8_scaled.safetensors", 4,\n'
                       '                   architecture="fibo2", vae="shared-vaes/flux2-vae.safetensors", operations=("edit",)),')
        text = replace(text, 'def runtime(model_id: str | None = None) -> NativeRuntime:',
                       'MODELS = tuple(model for model in MODELS if model.id in ("fibo2-turbo", "krea-genesis", "moss-turbo"))\n\n\n'
                       'def runtime(model_id: str | None = None) -> NativeRuntime:')
        text = replace(text, 'selected = model_id or os.environ.get("EFFIGY_REFERENCE_MODEL")',
                       'selected = model_id or os.environ.get("EFFIGY_REFERENCE_MODEL", "fibo2-turbo")')
    elif relative == "steps/reference.py":
        text = replace(text, 'def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:\n',
                       'def run(op: str, in_dir: str | None, out_dir: str, params: dict) -> dict:\n'
                       '    if params.get("model") == "fibo2-turbo":\n'
                       '        from steps.fibo_trial import run as run_fibo\n'
                       '        return run_fibo(op, in_dir, out_dir, params)\n')
    elif relative == "server/presets.py":
        text = replace(text, '"flux-ghibli": 17.0,', '"flux-ghibli": 17.0, "fibo2-turbo": 16.0,')
    elif relative == "tools/native_reference_entry.py":
        text = replace(text, 'step = os.environ.get(',
                       'from server.runtime_policy import activate\n\nactivate()\nstep = os.environ.get(')
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui", action="store_true", help="Also stage the completed multi-view UI")
    parser.add_argument("--only", nargs="+", choices=BACKEND + UI, help="Stage only these named files")
    args = parser.parse_args()
    if not (LANE / "settings.json").is_file():
        raise RuntimeError("Existing trial settings are missing; no provisioning is performed")
    for relative in args.only or BACKEND + (UI if args.ui else ()):
        source, target = ROOT / relative, LANE / relative
        if not source.is_file() or not target.resolve().is_relative_to(LANE.resolve()):
            raise RuntimeError(f"Unsafe or missing staged source: {relative}")
        text = backend(relative, source.read_text(encoding="utf-8"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        print(relative)
    if args.only is None:
        worker_source = ROOT / "tools" / "fibo_trial_worker.py"
        worker_target = LANE / "steps" / "fibo_trial.py"
        worker_target.write_text(worker_source.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    if args.ui and args.only is None:
        target = LANE / "ui/src/main.tsx"
        text = target.read_text(encoding="utf-8")
        if 'import { MultiViewPaint }' not in text:
            text = replace(text, 'import { SurfacePaint } from "./SurfacePaint";',
                           'import { SurfacePaint } from "./SurfacePaint";\nimport { MultiViewPaint } from "./MultiViewPaint";')
            text = replace(text, '{kind !== "2d" && <SurfacePaint asset={id} version={v} versions={versions} chain={props.chain} />}',
                           '{kind !== "2d" && <SurfacePaint asset={id} version={v} versions={versions} chain={props.chain} />}\n'
                           '          {kind !== "2d" && <MultiViewPaint asset={id} version={v} versions={versions} />}')
            target.write_text(text, encoding="utf-8", newline="\n")
        if "const multiSession = x.params.session_id;" not in text:
            canonical = (ROOT / "ui/src/main.tsx").read_text(encoding="utf-8")
            start = canonical.index("    const multiSession = x.params.session_id;")
            end = canonical.index('    const capture = x.step === "paint"', start)
            text = replace(text, "  for (const x of shown) {\n", "  for (const x of shown) {\n" + canonical[start:end])
            target.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
