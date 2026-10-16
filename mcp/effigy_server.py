"""The Effigy MCP server (stdio): the Effigy library and steps as tools for an agent (IMPLEMENTATION.md §3.7).

A thin client of the backend's REST API (EFFIGY_API, else 127.0.0.1 on EFFIGY_PORT or the port chosen in
Setup, else 8000), so it needs the
backend running. Versions are append-only: no tool deletes or overwrites anything. Requests carry no
Origin header and go to 127.0.0.1, which is what the API's Host/Origin check lets through.
"""

import ast
import contextlib
import io
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import anyio.from_thread
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import (
    ToolError,
)  # its message reaches the agent; others are hidden
from mcp.server.mcpserver.utilities.types import Image
from mcp.types import ToolAnnotations

ROOT = Path(__file__).resolve().parents[1]


def _api() -> str:
    """EFFIGY_API, else 127.0.0.1 on EFFIGY_PORT or the port chosen in Setup (settings.json, as the backend reads
    it at start), else 8000."""
    if api := os.environ.get("EFFIGY_API"):
        return api
    f = Path(os.environ.get("EFFIGY_SETTINGS") or ROOT / "settings.json")
    try:
        saved = json.loads(f.read_text(encoding="utf-8")).get("port")
    except (OSError, ValueError):
        saved = None
    return f"http://127.0.0.1:{os.environ.get('EFFIGY_PORT') or saved or 8000}"


API = _api()
GUIDE = Path(__file__).with_name("SKILL.md")


def _hints(read_only=False, idempotent=False) -> ToolAnnotations:
    return ToolAnnotations(
        read_only_hint=read_only,
        destructive_hint=False,  # append-only: nothing is deleted or overwritten
        idempotent_hint=read_only or idempotent,
        open_world_hint=False,
    )


READ, ADD, SAME = _hints(True), _hints(), _hints(idempotent=True)
STOP = ToolAnnotations(  # cancelling throws away the work done so far
    read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False
)

INSTRUCTIONS = (
    "Effigy: a local 3D asset pipeline. An asset holds versions (001_upload, 002_clean...), each made "
    "by a step from a parent version; nothing is overwritten. Usual order: import_file, or run_step brief, "
    "concepts, prep; then trellis2, clean, remesh, uv, bake, rig_fit, rig_skin, anim, validate, export. "
    "Steps are jobs, one GPU job at a time: a result with status running has a job_id, poll job_status. "
    "look shows a version; describe_steps and the resource effigy://guide have the params and the how-to."
)
server = MCPServer("effigy", instructions=INSTRUCTIONS)


# --- the API ----------------------------------------------------------------------------------


def _err(e: urllib.error.HTTPError) -> ToolError:
    try:
        err = json.load(e).get("error", {})
    except ValueError:
        err = {}
    return ToolError(f"{err.get('code', e.code)}: {err.get('message', e.reason)}")


def api(method: str, path: str, body=None, raw: bool = False, timeout: int = 300):
    """JSON in and out (`raw`: the response bytes); an API error becomes a ToolError, not a crash."""
    headers = {} if body is None else {"content-type": "application/json"}
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data, headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read() if raw else json.load(r)
    except urllib.error.HTTPError as e:
        raise _err(e) from None
    except urllib.error.URLError as e:
        raise ToolError(
            f"unreachable: Effigy backend not at {API} ({e.reason}), start run.bat"
        ) from None


def _q(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def _file_url(asset_id: str, version: str, name: str) -> str:
    return f"{API}/files/{_q(asset_id)}/{_q(version)}/{'/'.join(map(_q, name.split('/')))}"


# --- what the UI calls a version (ui/src/workflow.ts `label`) ---------------------------------

STEP_LABELS = {
    "brief": "Description",
    "concepts": "Concept images",
    "prep": "Cut-out reference",
    "canon": "Re-posed reference",
    "transform": "Moved model",
    "blender": "Blender edit",
    "claude": "Claude edit",
    "clean": "Cleaned",
    "remesh": "Simplified",
    "uv": "Unwrapped",
    "bake": "Textured model",
    "project": "Face from image",
    "refine": "Refined texture",
    "rig_fit": "Skeleton",
    "rig_skin": "Skinned model",
    "anim": "Animated model",
    "anim_edit": "Edited animation",
    "motion": "Motion from text",
    "import_motion": "Animation from a file",
    "parts": "Parts",
    "pixelize": "Pixel art",
    "redraw": "Redrawn picture",
    "sprites": "Sprites",
}
PROFILES = {
    "godot": "Godot",
    "unreal": "Unreal",
    "unity": "Unity",
    "web": "Web / AR",
    "obj": "OBJ",
    "print": "3D print",
    "godot-2d": "Godot 2D",  # M53: a sprite sheet (pixelize, sprites)
    "unreal-2d": "Unreal Paper2D",
}


def label(m: dict) -> str:
    step, out = m["step"], m.get("outputs", {})
    par, met = m.get("params") or {}, m.get("metrics") or {}
    if step == "upload":
        if any(k != "model" and f.endswith(".glb") for k, f in out.items()):
            return "Imported model"
        return "Original file" if "model" in out else "Uploaded picture"
    if step == "import_model":
        if "rigged_anim" in out:
            return "Imported animation"
        return "Imported rig" if "rigged" in out else "Imported model"
    if step == "export":
        return f"Export: {PROFILES.get(str(met.get('profile')), met.get('profile', ''))}"
    if step == "trellis2":
        return (
            "Retextured model"
            if par.get("op") == "texture"
            else f"Generated model ({par.get('weights', '')})"
        )
    if step == "parts":
        if par.get("op") == "views":
            return "Parts: views"
        names = [n for n in (met.get("parts") or {}) if n != "Body"]
        return f"Parts: {', '.join(names)}" if names else "Parts"
    if step == "validate":
        return f"Checks: {met['fail']} failed" if met.get("fail") else "Checks"
    if m.get("provenance") == "blender_pull":
        return STEP_LABELS["blender"]
    if m.get("provenance") == "claude_run":
        return STEP_LABELS["claude"]
    return STEP_LABELS.get(step, step)


# --- reading ----------------------------------------------------------------------------------


@server.tool(annotations=READ)
def list_assets(query: str = "", limit: int = 30, offset: int = 0) -> dict:
    """Use this first to find an asset id: lists the library, newest first, optionally only assets whose
    name or id contains `query`. Returns {assets: [{id, name, created, versions, newest: {version, label}}],
    total}; page with limit (1-100) and offset."""
    q = query.lower()
    found = [a for a in api("GET", "/api/assets") if q in a["id"].lower() or q in a["name"].lower()]
    found.sort(key=lambda a: a.get("updated", ""), reverse=True)
    page = []
    for a in found[max(0, offset) :][: max(1, min(limit, 100))]:
        vs = api("GET", f"/api/assets/{_q(a['id'])}")["versions"]
        newest = {"version": vs[-1]["version"], "label": label(vs[-1])} if vs else None
        page.append(
            {k: a[k] for k in ("id", "name", "created")} | {"versions": len(vs), "newest": newest}
        )
    return {"assets": page, "total": len(found)}


@server.tool(annotations=READ)
def get_asset(asset_id: str) -> dict:
    """Use this to see what an asset holds before choosing a parent version: every version with its step,
    label (as the app shows it), parent, created time, output file names and numeric metrics."""
    a = api("GET", f"/api/assets/{_q(asset_id)}")
    versions = [
        {
            "version": m["version"],
            "step": m["step"],
            "label": label(m),
            "parent": m.get("parent"),
            "created": m.get("created"),
            "outputs": list(m.get("outputs", {}).values()),
            "metrics": {
                k: v
                for k, v in (m.get("metrics") or {}).items()
                if isinstance(v, int | float | str | bool)
            },
        }
        for m in a["versions"]
    ]
    return {"id": asset_id, "name": a["asset"].get("name"), "versions": versions}


@server.tool(annotations=READ)
def get_version(asset_id: str, version: str) -> dict:
    """Use this for the full meta.json of one version: outputs, params, metrics, parent, licences, note."""
    for meta in api("GET", f"/api/assets/{_q(asset_id)}")["versions"]:
        if meta["version"] == version:
            return meta
    raise ToolError(f"not_found: no version {version!r} in {asset_id!r}, list them with get_asset")


@server.tool(annotations=READ)
def describe_steps(step: str = "") -> dict:
    """Use this to learn what the steps are and which params they take. Without `step`: the guide's summary
    and every runnable step with its purpose, its input and its presets. With `step`: that step's whole
    docstring (the params) and presets. The full how-to is the resource effigy://guide."""
    presets = api("GET", "/api/steps")

    def doc(name: str) -> str:
        return (
            ast.get_docstring(ast.parse((ROOT / "steps" / f"{name}.py").read_text("utf-8"))) or ""
        )

    if step:
        if step not in presets:
            raise ToolError(f"not_found: no step {step!r}, call describe_steps() for the list")
        return {"step": step, "doc": doc(step), "presets": presets[step]}
    summary = re.search(r"^description:\s*(.+)$", GUIDE.read_text("utf-8"), re.MULTILINE)
    steps = {}
    for name, p in presets.items():
        text = doc(name)
        into = re.search(r"(?:\bInput|\bin):\s*([^\n]*)", text)
        steps[name] = {
            "does": text.split("\n", 1)[0],
            "in": into[1][:160] if into else "",
            "presets": list(p),
        }
    return {"guide": summary[1] if summary else "", "steps": steps}


@server.tool(annotations=READ, structured_output=False)
def look(asset_id: str, version: str, clip: str = "", size: int = 768) -> list:
    """Use this to see a version: a mesh as a 2x2 sheet (front, right, back, three-quarter; textured if it
    has textures), a picture version as a grid, and with `clip` four frames of that animation clip. `size`
    256-1024. Returns one PNG and the path of the cached file."""
    size = max(256, min(size, 1024))
    path = f"/api/assets/{_q(asset_id)}/versions/{_q(version)}/look?clip={_q(clip)}&size={size}"
    req = urllib.request.Request(API + path)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            png, where = r.read(), r.headers.get("X-Effigy-File")
    except urllib.error.HTTPError as e:
        raise _err(e) from None
    except urllib.error.URLError as e:
        raise ToolError(
            f"unreachable: Effigy backend not at {API} ({e.reason}), start run.bat"
        ) from None
    return [
        Image(data=png, format="png"),
        *([f"saved at {urllib.parse.unquote(where)}"] if where else []),
    ]


@server.tool(annotations=READ)
def read_file(asset_id: str, version: str, name: str) -> dict:
    """Use this to read a JSON or text output of a version (report.json, skeleton.json, clips.json, qa.json,
    checklist.json, edit.json, meta.json, brief.yaml), at most 200 KB. For a picture or a mesh use look, or export."""
    meta = get_version(asset_id, version)
    if name != "meta.json" and name not in meta.get("outputs", {}).values():
        raise ToolError(f"not_found: {name!r} is not an output of {version}, see get_asset")
    if not name.endswith((".json", ".txt", ".yaml", ".yml", ".md", ".csv")):
        raise ToolError(f"not_readable: {name!r} is not text, use look, or export")
    try:
        with urllib.request.urlopen(_file_url(asset_id, version, name), timeout=30) as r:
            data = r.read(200_001)
    except urllib.error.HTTPError as e:
        raise _err(e) from None
    if len(data) > 200_000:
        raise ToolError(f"too_large: {name!r} is over 200 KB, read a smaller output")
    return {"name": name, "text": data.decode("utf-8", "replace")}


@server.tool(annotations=READ)
def fit_check(asset_id: str, version: str) -> dict:
    """Use this on a rig_fit or rig_skin version to score how well its skeleton sits in its mesh (joints
    outside the mesh, bone lengths); run it before skinning, fix the markers with run_step rig_fit."""
    return api("POST", f"/api/assets/{_q(asset_id)}/versions/{_q(version)}/fit-check", {})


@server.resource("effigy://guide", mime_type="text/markdown")
def guide() -> str:
    """How to use Effigy: pipelines, steps, animation edits, checking, exporting."""
    return GUIDE.read_text("utf-8")


# --- jobs -------------------------------------------------------------------------------------


def _progress(ctx: Context, job: dict) -> None:
    with contextlib.suppress(Exception):  # a courtesy: the loop's result does not depend on it
        anyio.from_thread.run(ctx.report_progress, job.get("progress", 0), 1, job.get("text", ""))


def _wait(job_id: str, wait_s: float, ctx: Context, own: bool) -> dict:
    """Poll a job each second for at most wait_s (0..45): the finished job, or status running. If this call
    is cancelled and started the job (`own`), the job is cancelled too."""
    end = time.monotonic() + max(0.0, min(wait_s, 45.0))
    try:
        while True:
            j = api("GET", f"/api/jobs/{_q(job_id)}")
            if j["status"] == "done":
                return j
            if j["status"] == "cancelled":
                raise ToolError(
                    "cancelled: the job was cancelled, run the step again if it is still wanted"
                )
            if j["status"] == "failed":
                e = j.get("error") or {}
                raise ToolError(
                    f"{e.get('code', 'failed')}: {e.get('message', 'the job failed')}"
                    ", adjust the params and run the step again"
                )
            _progress(ctx, j)
            anyio.from_thread.check_cancelled()
            if (left := end - time.monotonic()) <= 0:
                return j
            time.sleep(min(1.0, left))
    except (
        BaseException
    ) as e:  # this call cancelled (not an error): the job it started must not outlive it
        if own and not isinstance(e, Exception):
            with contextlib.suppress(Exception):
                api("POST", f"/api/jobs/{_q(job_id)}/cancel", {})
        raise


def _result(j: dict) -> dict:
    """A polled job as the tool result: done + its version's meta.json, or running + job_id."""
    if j["status"] == "done":
        return {
            "status": "done",
            "job_id": j["job_id"],
            "version": get_version(j["asset_id"], j["version"]),
        }
    return {k: j[k] for k in ("job_id", "progress", "text") if k in j} | {"status": "running"}


def _start(asset_id, parent, step, params, wait_s, ctx) -> dict:
    body = {"parent": parent, "params": params, "dedupe": True}
    job = api("POST", f"/api/assets/{_q(asset_id)}/steps/{_q(step)}", body)
    return _result(_wait(job["job_id"], wait_s, ctx, own=not job.get("deduped")))


@server.tool(annotations=ADD)
def run_step(
    asset_id: str,
    parent: str | None,
    step: str,
    params: dict | None = None,
    wait_s: float = 40,
    ctx: Context = None,
) -> dict:
    """Use this to run a pipeline step on a `parent` version (null for brief and other root steps); params
    are in describe_steps(step), or a preset's name as {"preset": "faithful"} (its params, yours on top;
    {"preset": "best"}: the best this card runs). Waits up to wait_s (0-45): {status: done, version: {meta.json}} or
    {status: running, job_id, progress}, then continue with job_status. The same request while a job for it
    runs returns that job. The result is a new version; nothing is overwritten."""
    return _start(asset_id, parent, step, params or {}, wait_s, ctx)


@server.tool(annotations=READ)
def job_status(job_id: str, wait_s: float = 0, ctx: Context = None) -> dict:
    """Use this to follow a job that run_step, validate, export or import_file left running: waits up to
    wait_s (0-45) for it; returns {status: running|done, job_id, progress, text, version}. A failure comes
    back as an error with its code and message."""
    return _result(_wait(job_id, wait_s, ctx, own=False))


@server.tool(annotations=STOP)
def cancel_job(job_id: str) -> dict:
    """Use this to stop a queued or running job (e.g. a wrong step); the job ends as cancelled and the
    library is unchanged. Returns {job_id, status}."""
    api("POST", f"/api/jobs/{_q(job_id)}/cancel", {})
    return {"job_id": job_id, "status": api("GET", f"/api/jobs/{_q(job_id)}")["status"]}


@server.tool(annotations=ADD)
def create_asset(name: str, kind: str = "") -> dict:
    """Use this to start an asset from a description: then run_step(asset_id, null, "brief", {prompt,
    category}). Returns {asset_id}: the name in lower case, other characters as _, cut at 36 characters (and
    _2, _3 when taken), so use the id it returns. kind="2d" for a picture, pixel-art or sprite asset (no 3D
    model); leave it empty for a 3D asset. To start from a file use import_file."""
    body = {"name": name} | ({"kind": kind} if kind else {})
    return {"asset_id": api("POST", "/api/assets", body)["id"]}


# --- import and export ------------------------------------------------------------------------

MODELS = {
    ".glb",
    ".gltf",
    ".fbx",
    ".usdz",
    ".usdc",
    ".usd",
    ".usda",
    ".obj",
    ".ply",
    ".stl",
    ".zip",
}
PICTURES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEOS = {".mp4", ".mov", ".webm"}


@server.tool(annotations=ADD)
def import_file(
    path: str = "",
    name: str = "",
    still: bool = False,
    kind: str = "",
    library_file: str = "",
    wait_s: float = 40,
    ctx: Context = None,
) -> dict:
    """Use this to bring a local file into the library as a new asset: an absolute path to a model (.glb
    .gltf .fbx .obj .stl .ply .usd*), a .zip of one, a picture (.png .jpg .webp) or a video (.mp4 .mov
    .webm), at most 1 GB. A model runs import_model (a known skeleton is kept unless still=true), a picture
    runs prep (the cut-out for 3D) unless kind="2d" (a wallpaper, tile or sprite picture: only uploaded,
    into a 2D asset); a video only uploads (run mocap yourself). Instead of `path`, library_file
    "<asset_id>/<version>/<file>" takes a picture already in the library: a 2D character's picture into a
    new 3D asset to animate (the app's Animate this character). Returns {asset_id, upload, ...} like run_step."""
    source = None
    if library_file:  # a picture of another asset, through the API: the agent needs no library path
        src, version, file = (library_file.split("/", 2) + ["", ""])[:3]
        if not file:
            raise ToolError(
                f"bad_path: library_file {library_file!r} is <asset_id>/<version>/<file>"
            )
        data = api(
            "GET", f"/files/{_q(src)}/{_q(version)}/{'/'.join(map(_q, file.split('/')))}", raw=True
        )
        source = api("GET", f"/api/assets/{_q(src)}")["asset"]
        p, size = Path(file), len(data)
        name = name or f"{source.get('name') or src} ({'2D' if kind == '2d' else '3D'})"
    else:
        p = Path(path)
        if not p.is_absolute() or not p.is_file():
            raise ToolError(f"bad_path: {path!r} must be the absolute path of an existing file")
        size = p.stat().st_size
    ext = p.suffix.lower()
    if ext not in MODELS | PICTURES | VIDEOS:
        raise ToolError(
            f"bad_type: {ext!r} is not a model, .zip, picture or video, convert it first"
        )
    if size > 2**30:
        raise ToolError(f"too_large: {size >> 20} MB, uploads are limited to 1024 MB")
    body = {"name": name or p.stem} | ({"kind": kind} if kind else {})
    asset_id = api("POST", "/api/assets", body)["id"]
    # a file streams from disk with a Content-Length, never read whole; a library picture is in memory already
    with io.BytesIO(data) if library_file else p.open("rb") as f:
        req = urllib.request.Request(
            f"{API}/api/assets/{_q(asset_id)}/upload/{_q(p.name)}",
            f,
            {"content-length": str(size), "content-type": "application/octet-stream"},
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                upload = json.load(r)["version"]
        except urllib.error.HTTPError as e:
            raise ToolError(f"{_err(e)}, the empty asset {asset_id} stays") from None
        except (urllib.error.URLError, OSError) as e:
            raise ToolError(
                f"upload_failed: {e}, the empty asset {asset_id} stays; is run.bat running?"
            ) from None
    head = {"asset_id": asset_id, "upload": upload}
    if ext in VIDEOS:
        return head | {
            "status": "uploaded",
            "note": "a video has no step yet: run_step mocap on it",
        }
    if kind == "2d" and ext in PICTURES:
        note = "a 2D picture: run_step pixelize on it, or redraw (op upscale | redraw) to enlarge or redraw it"
        return head | {"status": "uploaded", "note": note}
    step, params = ("prep", {}) if ext in PICTURES else ("import_model", {"rig": not still})
    # a flat picture (a 2D asset's) makes a cardboard model: the redraw comes first
    if source and source.get("kind") == "2d" and ext in PICTURES:
        head["next"] = 'on the prep: canon {"look": "render"}, then prep on that, then trellis2'
    return head | _start(asset_id, upload, step, params, wait_s, ctx)


@server.tool(annotations=ADD)
def validate(asset_id: str, version: str, wait_s: float = 40, ctx: Context = None) -> dict:
    """Use this to check a version before exporting: runs the validate step and returns {status: done,
    items: [{name, status pass|warn|fail, ...}]}, or running + job_id like run_step. Fix fails first."""
    out = _start(asset_id, version, "validate", {}, wait_s, ctx)
    if out["status"] == "done":
        meta = out["version"]
        rel = meta.get("outputs", {}).get("checklist")
        if not rel:
            raise ToolError(f"no_checklist: {meta['version']} wrote none, see get_version")
        out["items"] = json.loads(read_file(asset_id, meta["version"], rel)["text"])["items"]
    return out


@server.tool(annotations=ADD)
def export(
    asset_id: str,
    version: str,
    profile: str,
    options: dict | None = None,
    to_folder: str = "",
    wait_s: float = 40,
    ctx: Context = None,
) -> dict:
    """Use this to export a version for godot|unreal|unity|web|print|obj, or a sprite sheet (pixelize,
    sprites) for godot-2d|unreal-2d (files + CREDITS.txt + LICENSES.json). options: lods, collision. to_folder: an existing absolute directory; the files are
    also copied into a new <asset>_<profile> folder in it (an existing one is refused). Returns {status,
    version, files}, or running + job_id."""
    target = None
    if to_folder:
        d = Path(to_folder)
        if not d.is_absolute() or not d.is_dir():
            raise ToolError(
                f"bad_path: to_folder {to_folder!r} must be an existing absolute directory"
            )
        target = d / re.sub(r"[^A-Za-z0-9_-]", "_", f"{asset_id}_{profile}")
        if target.exists():
            raise ToolError(
                f"exists: {target} exists, pick another to_folder or remove it yourself"
            )
    params = {"profile": profile} | (options or {})
    # an identical export already made is reused: an export that outlived wait_s is fetched by asking again
    same = [
        m
        for m in api("GET", f"/api/assets/{_q(asset_id)}")["versions"]
        if m["step"] == "export" and m.get("parent") == version and m.get("params") == params
    ]
    if same:
        out = {"status": "done", "version": same[-1]}
    else:
        out = _start(asset_id, version, "export", params, wait_s, ctx)
    if out["status"] != "done":
        return out | {
            "note": "still exporting: when job_status says done, call export again with the same "
            "arguments: it reuses this export" + (" and copies it into to_folder" if target else "")
        }
    meta = out["version"]
    files = list(meta["outputs"].values())
    if target:
        dests = [
            target / Path(rel).relative_to(profile) for rel in files
        ]  # outputs: <profile>/<file>
        try:
            target.mkdir()  # never into an existing folder: this is the check that counts
        except FileExistsError:
            raise ToolError(f"exists: {target} exists, pick another to_folder") from None
        try:
            for rel, dest in zip(files, dests, strict=True):
                dest.parent.mkdir(parents=True, exist_ok=True)
                with (
                    urllib.request.urlopen(
                        _file_url(asset_id, meta["version"], rel), timeout=300
                    ) as r,
                    dest.open("xb") as f,
                ):
                    shutil.copyfileobj(r, f)
        except (urllib.error.URLError, OSError) as e:
            shutil.rmtree(target, ignore_errors=True)  # no half-filled folder that blocks a retry
            raise ToolError(
                f"copy_failed: {e}; nothing was left in {to_folder}, try again"
            ) from None
        files = [str(d) for d in dests]
    return out | {"files": files}


# --- Blender ----------------------------------------------------------------------------------


@server.tool(annotations=ADD)
def pull_from_blender(asset_id: str, version: str | None = None) -> dict:
    """Use this after editing in the live Blender scene: saves the asset's objects as a new version and
    returns its meta.json. With several versions of the asset open, `version` says which (else the one
    opened last; the note names what else was open)."""
    pulled = api("POST", f"/api/assets/{_q(asset_id)}/blender/pull", {"version": version})
    return get_version(asset_id, pulled["version"])


@server.tool(annotations=SAME)
def close_in_blender(asset_id: str, version: str | None = None) -> list[str]:
    """Use this to take an asset's open versions out of the Blender scene (`version`: just that one; else
    all of them), e.g. an older one before editing the newer. Returns the collections removed."""
    return api("POST", f"/api/assets/{_q(asset_id)}/blender/close", {"version": version})["closed"]


@server.tool(annotations=SAME)
def open_in_blender(asset_id: str, version: str) -> list[str]:
    """Use this to look at or edit a version in the live Blender: imports it into the scene (collection
    EFFIGY_<asset>_v<NNN>); returns the object names. With the app's Setup option "Start Blender when it is
    needed" on, a closed Blender is started first (up to 90 s); do not start one yourself."""
    return api("POST", f"/api/assets/{_q(asset_id)}/blender/open", {"version": version})["objects"]


if __name__ == "__main__":
    server.run()
