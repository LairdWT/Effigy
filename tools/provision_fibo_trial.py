"""Provision an isolated, pinned FIBO trial without changing the primary runtime."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "scratch" / "lanes" / "fibo2"
COMFY_REVISION = "e3699a745d513941f17ecbc9a3c58d00fc7768cb"
MODEL_REVISION = "41e6a0331eff43d5a323107197056e377288c642"
MODEL_FILE = "diffusion_models/fibo2_edit_turbo_int8_convrot.safetensors"
MODEL_SIZE = 8408562474


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"Source changed; expected one adaptation in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def configure_ui() -> None:
    path = LANE / "ui/src/SurfacePaint.tsx"
    text = path.read_text(encoding="utf-8")
    text = text.replace('"krea-genesis"', '"fibo2-turbo"')
    text = text.replace('saved.steps : 8', 'saved.steps : 4').replace('steps: 8,', 'steps: 4,')
    text = text.replace('model !== "qwen-edit"', '!(["qwen-edit", "fibo2-turbo"].includes(model))')
    text = text.replace('setSteps(value.startsWith("krea") ? 8 : value === "flux-ghibli" ? 30 : 20)', 'setSteps(value === "fibo2-turbo" ? 4 : value === "flux-ghibli" ? 30 : 20)')
    text = text.replace('<summary>Projection painting</summary>', '<summary>FIBO trial - projection painting</summary>')
    text = text.replace('Incremental: generate only inside the mask', 'FIBO: masked edit with protected projection')
    text = text.replace('<option value="full_view">Restyle the full view, then project the selection</option>', '')
    text = text.replace('The full captured image stays in context. Only the green selection is denoised; the rest of the preview stays unchanged. Use brush, lasso or faces to extend your painted area.', 'FIBO sees the full frame with the green region blanked for editing. Only selected pixels enter the preview and mesh. Protected pixels remain exact; this is native mask conditioning, not Genesis differential denoising.')
    text = text.replace('Krea2 Genesis image-to-image uses the captured texture and your resulting-appearance description. No FLUX LoRAs are attached.', 'FIBO 2 Edit Turbo uses four steps and your edit instruction. Keep the original silhouette and material boundaries in your instructions.')
    text = text.replace('<input type="number" min="1" max="50" value={steps}', '<input disabled type="number" min="4" max="4" value={steps}')
    text = text.replace('disabled={busy || !appearanceReady} onClick={() => perform(async () => {\n        localStorage', 'disabled onClick={() => perform(async () => {\n        localStorage')
    text = text.replace('Uses local Q3.5-9B OpusGLM Q8 and its vision projector. Suggestions describe observed pixels; your desired style stays separate.', 'Description generation is disabled in this bounded trial. The copied appearance record remains editable.')
    path.write_text(text, encoding="utf-8")
    replace_once(LANE / "server/reference_models.py", '\ndef runtime() -> NativeRuntime:',
                 '\nMODELS = tuple(model for model in MODELS if model.id == "fibo2-turbo")\n\ndef runtime() -> NativeRuntime:')
    replace_once(LANE / "server/app.py", 'def run_step(asset_id: str, step: str, body: RunStep):',
                 'def run_step(asset_id: str, step: str, body: RunStep):\n    if step not in ("paint", "reference", "import_model"):\n        raise ApiError(400, "unsupported", "This trial supports capture, FIBO preview, projection and mesh import only")')


def provision() -> None:
    if LANE.exists():
        raise RuntimeError(f"Trial already exists; preserve its work: {LANE}")
    settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    tools_file = Path(settings["tools_config"])
    original_tools = json.loads(tools_file.read_text(encoding="utf-8"))
    native_python = (tools_file.parent / original_tools["comfyUi"]["embeddedPython"]).resolve()
    native_site = native_python.parent / "Lib" / "site-packages"
    owned = Path(settings["models"]) / "fibo2-trial"
    runtime_models = owned.parent / "fibo2-runtime"
    library = Path(settings["library"]) / "_trials" / "fibo2"
    for folder, required in ((ROOT, 4 * 2**30), (owned.parent, MODEL_SIZE + 2**30)):
        if shutil.disk_usage(folder).free < required:
            raise RuntimeError(f"Insufficient capacity at {folder}")
    LANE.mkdir(parents=True)
    names = subprocess.check_output(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT
    ).decode("utf-8").split("\0")
    prefixes = ("server/", "steps/", "tools/", "blender_ops/", "prompts/", "engine/", "ui/src/")
    roots = {"pyproject.toml", "uv.lock", "licenses.yaml", "AGENTS.md", "CODE.md", "ui/package.json", "ui/package-lock.json", "ui/tsconfig.json", "ui/vite.config.ts", "ui/index.html"}
    for name in sorted(set(names)):
        if not name or not (name.startswith(prefixes) or name in roots):
            continue
        source = (ROOT / name).resolve()
        if not source.is_relative_to(ROOT) or not source.is_file():
            raise RuntimeError(f"Unsafe source entry: {name}")
        target = LANE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for source in (ROOT / "ui" / "dist").rglob("*"):
        if not source.is_file():
            continue
        target = LANE / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    engine = LANE / "native-engine"
    archive = LANE / "native-engine.zip"
    urllib.request.urlretrieve(
        f"https://codeload.github.com/kijai/ComfyUI/zip/{COMFY_REVISION}", archive
    )
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            parts = Path(member.filename).parts[1:]
            if not parts or member.is_dir():
                continue
            target = (engine.joinpath(*parts)).resolve()
            if not target.is_relative_to(engine.resolve()):
                raise RuntimeError("Native source archive escapes the trial")
            target.parent.mkdir(parents=True, exist_ok=True)
            with package.open(member) as incoming, target.open("wb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
    archive.unlink()
    python = LANE / ".venv-fibo" / "Scripts" / "python.exe"
    uv = (tools_file.parent / original_tools["uv"]["executable"]).resolve()
    subprocess.run([str(uv), "venv", "--python", str(ROOT / ".venv" / "Scripts" / "python.exe"),
                    str(python.parents[1])], check=True)
    site = python.parents[1] / "Lib" / "site-packages"
    (site / "borrowed-runtime.pth").write_text(str(native_site) + "\n", encoding="utf-8")
    subprocess.run([str(uv), "pip", "install", "--python", str(python), "--no-deps",
                    "--only-binary", ":all:", "comfy-kitchen==0.2.39", "comfy-aimdo==0.5.6", "av==17.0.0"], check=True)
    from huggingface_hub import hf_hub_download

    owned.mkdir(parents=True, exist_ok=True)
    model = Path(hf_hub_download("Comfy-Org/Fibo-2.0", MODEL_FILE,
                                revision=MODEL_REVISION, local_dir=owned))
    if model.stat().st_size != MODEL_SIZE:
        raise RuntimeError("Downloaded transformer size differs from the pinned published object")
    bindings = json.loads((ROOT / "model-bindings.local.json").read_text(encoding="utf-8"))
    bindings["trial-fibo"] = {"path": str(owned), "revision": MODEL_REVISION}
    (LANE / "model-bindings.local.json").write_text(json.dumps(bindings, indent=2), encoding="utf-8")
    library.mkdir(parents=True, exist_ok=True)
    runtime_models.mkdir(parents=True, exist_ok=True)
    settings.update(library=str(library), models=str(runtime_models), port=8380,
                    trial_native_python=str(python), trial_native_source=str(engine),
                    environment_root=str(ROOT), blender_start=False, blender_free_port=8381)
    (LANE / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    replace_once(LANE / "server/runtime_policy.py", 'os.environ["EFFIGY_PORT"] = "8370"',
                 'os.environ["EFFIGY_PORT"] = "8380"')
    replace_once(LANE / "server/jobs.py", 'return ROOT / venv /',
                 'return Path(settings.read()["environment_root"]) / venv /')
    replace_once(LANE / "server/jobs.py", 'SERVE = {"trellis2", "concepts", "motion", "reference"}',
                 'SERVE = {"trellis2", "concepts", "motion"}')
    replace_once(LANE / "server/reference_models.py", '    config: Path = Path(settings.read()["tools_config"])',
                 '    return NativeRuntime(Path(settings.read()["trial_native_python"]), Path(settings.read()["trial_native_source"]))\n\n\ndef configured_primary_runtime() -> NativeRuntime:\n    config: Path = Path(settings.read()["tools_config"])')
    replace_once(LANE / "server/reference_models.py", 'Literal["krea", "qwen", "flux"]',
                 'Literal["krea", "qwen", "flux", "fibo2"]')
    replace_once(LANE / "server/reference_models.py", 'MODELS: tuple[ReferenceModel, ...] = (',
                 'MODELS: tuple[ReferenceModel, ...] = (\n    ReferenceModel("fibo2-turbo", "FIBO 2 Edit Turbo (INT8 trial)", "edit",\n                   "trial-fibo/diffusion_models/fibo2_edit_turbo_int8_convrot.safetensors",\n                   "shared-text-encoders/qwen3vl_4b_fp8_scaled.safetensors", 4,\n                   architecture="fibo2", vae="shared-vaes/flux2-vae.safetensors", operations=("edit",)),')
    replace_once(LANE / "server/presets.py", '"flux-ghibli": 17.0,', '"flux-ghibli": 17.0, "fibo2-turbo": 16.0,')
    replace_once(LANE / "steps/reference.py", '    try:\n        choice = reference_models.get',
                 '    if params.get("model") == "fibo2-turbo":\n        from steps.fibo_trial import run as run_fibo\n        return run_fibo(op, in_dir, out_dir, params)\n    try:\n        choice = reference_models.get')
    shutil.copy2(ROOT / "tools/fibo_trial_worker.py", LANE / "steps/fibo_trial.py")
    replace_once(LANE / "tools/native_reference_entry.py", 'runpy.run_module(',
                 'from server.runtime_policy import activate\nactivate()\nrunpy.run_module(')
    replace_once(LANE / "ui/dist/index.html", "<title>Effigy</title>", "<title>Effigy - FIBO trial 8380</title>")
    configure_ui()
    print(json.dumps({"lane": str(LANE), "library": str(library), "model": str(model),
                      "native_revision": COMFY_REVISION, "model_revision": MODEL_REVISION}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    provision()
