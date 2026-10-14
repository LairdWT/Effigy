# Windows portable zip: install bench (M15)

**Status: CI smoke green (87 s to the UI, nothing written outside the app folder); the owner's first
start on the reference laptop took ~79 s to a running server (2026-10-04). A clean Windows VM is still open.**

## What the zip is

`python tools/package.py` (stdlib only; Node 22 only if `ui/dist` isn't built yet) writes
`dist/Effigy-<git describe>-win64.zip` with one top folder, `Effigy\`:

- `uv.exe` 0.8.17 (`uv-x86_64-pc-windows-msvc.zip`, SHA-256 pinned in `tools/package.py` and equal to the
  release's `.sha256`) and `uv-LICENSE-MIT.txt`
- `run.bat`, `pyproject.toml`, `uv.lock`, `wheels\` (our sm_120 wheels), `licenses.yaml`, `LICENSE`,
  `README.md`, `.mcp.json`, `docs\` (the setup guide and plans)
- the code the app runs: `server\`, `steps\`, `engine\`, `blender_ops\`, `mcp\`, `prompts\`, `tools\`
- the built UI, `ui\dist\` (no Node needed on the user's machine)

Files come from `git ls-files` filtered by top-level entry (`KEEP` in `tools/package.py`), so tests,
UI sources, CI files and anything untracked (venvs, caches, `library\`, `models\`, `blender\`) stay out;
`tests/test_package.py` checks that. Local build at the M15 commit (on Linux; packing only):
25.2 MB zip, 207 files, 65 MB unpacked, of which `uv.exe` is 59 MB.

## Using it

1. Unzip to a short path, e.g. `C:\Effigy`: the ML env has deep paths, and Windows without
   long-path support stops at 260 characters (not hit yet; see "Still open").
2. Double-click `run.bat`. It finds `uv.exe` next to itself, puts it first on `PATH` and keeps everything
   in the folder: `UV_PYTHON_INSTALL_DIR=<folder>\python`, `UV_CACHE_DIR=<folder>\cache`,
   `UV_PYTHON_PREFERENCE=only-managed` (a system Python is never used). Without a `uv.exe` next to it
   (a git checkout) it uses the `uv` on `PATH` as before.
3. The first run downloads what's below, then opens http://127.0.0.1:8000. Later runs skip the
   downloads (the syncs are no-ops). Close the console window to stop the server.

Other `uv` commands from the README (e.g. `tools.download_models`) need the same three variables in that
console (`set UV_PYTHON_INSTALL_DIR=%CD%\python` …, then `uv.exe run …`); without them uv falls back to
its per-user folders and a system Python.

Moving the folder after the first run is fine: uv sees the venvs point at the old `python\` path and
rebuilds them from `cache\` without downloading (checked on Linux with uv 0.8.17, offline).

### What the first run downloads

File sizes as served on 2026-10-04 (not the time it takes):

| What | From | Size |
|---|---|---|
| CPython 3.12.11 `install_only_stripped` (python-build-standalone 20250902) | GitHub | 21.2 MB |
| backend packages (`.venv`: fastapi, uvicorn, numpy, opencv-headless, trimesh, mcp, …) | PyPI | see Results |
| torch 2.8.0+cu128 (`.venv-ml`) | download.pytorch.org | 3.46 GB |
| torchvision 0.23.0+cu128 | download.pytorch.org | 7.5 MB |
| other ML packages (diffusers, transformers, triton-windows 43 MB, …) | PyPI | see Results |
| Blender 5.2.2 `windows-x64.zip` (SHA-256 pinned, `server/blender_install.py`) | download.blender.org | 404 MB |

Model weights are not part of the first run (`tools/download_models.py`, installed separately).
Everything lands in the app folder: `python\`, `cache\`, `.venv\`, `.venv-ml\`, `blender\` (later
`models\`, `library\`). uv hardlinks from `cache\` into the venvs, so they don't take the space twice.

## CI smoke procedure (`.github/workflows/package.yml`)

On `windows-latest`, by hand only (Actions → package → Run workflow; build minutes are limited):

1. Build the zip with `python tools/package.py` (setup-python 3.12, setup-node 22; no setup-uv, so the
   runner's own uv dirs stay untouched) and upload it as the `Effigy-win64` artifact.
2. `Expand-Archive` into `$RUNNER_TEMP\effigy`, remove every `UV_*` variable, set `PATH` to the Windows
   system folders only (no uv, Python, Node or Git), set `EFFIGY_NO_BROWSER=1`.
3. Start `run.bat` in the background (log in `run1.log`), poll every 3 s for the folders it creates
   (`python`, `.venv`, `.venv-ml`, `blender`) and for `/api/health` and `/` answering 200 (90 min limit).
   Kill the process tree, then start it again (`run2.log`, 10 min limit) for the warm start.
4. Write the phase table, folder sizes and an "outside the app folder" check (file counts in
   `%APPDATA%\uv`, `%LOCALAPPDATA%\uv`, `~\.local\bin` before/after; registry key
   `HKCU\Software\Python\Astral`) to the job summary. Logs are uploaded (`first-run-logs`) and their
   tails printed on failure.

A phase ends when the next marker appears: CPython download → `.venv` created; backend env → `.venv-ml`
created; ML env → `blender\` created; Blender (+ any other first-run install `run.bat` gains) and server
start → `/api/health` answers. Runner bandwidth is far above a home line, so CI times are a floor for
the network-bound phases.

## Results

CI run 37183250788 (on the repo's earlier private home)
(windows-latest = Windows Server 2025 image `win25-vs2026`, datacentre bandwidth: the download phases are
a floor; on a home line the 3.5 GB torch wheel dominates). The first run before it (37183049421) failed
at the Blender download: download.blender.org returns 403 to urllib's default user agent, fixed in
`server/blender_install.py`.

| Run | Commit | Zip MB | Python s | .venv s | .venv-ml s | Blender + start s | First run to UI s | Warm start s |
|---|---|---|---|---|---|---|---|---|
| CI windows-latest | 2abaa74 | 24 | 7 | 0 ¹ | 71 | 9 | **87** | **1** |
| clean Windows VM | | | | | | | | |
| reference laptop ² | d892865 | 24 | ≈ 2 | 4 | 57 | 16 | **≈ 79** | – |

¹ the poll sees `.venv` and `.venv-ml` appear in the same 3 s tick; both syncs are inside 7 + 71 s.

² The owner's own first start (Windows 11, home line), read afterwards from the folders `run.bat` created
in the dev checkout and the server process's start time: `python\` + `cache\` 10:21:05, `.venv\`
10:21:07, `.venv-ml\` 10:21:11, `blender\` 10:22:08 (so the ML env with the 3.46 GB torch wheel took 57 s),
Blender unpacked 10:22:14, `gltfpack\` 10:22:18, server up 10:22:24. The CPython download before
10:21:05 isn't visible (≈ 2 s at that line speed is an estimate). Unzipped at 10:15:57 (the minutes before
the double-click are the owner's). Warm start not timed.

| Folder after first run (CI) | MB |
|---|---|
| python | 59 |
| cache | 7599 |
| .venv | 245 |
| .venv-ml | 7601 (hardlinked from `cache`: ~7.9 GB on disk for both together) |
| blender | 900 |

Outside the app folder (CI): 0 files before and after in uv's user dirs, no `HKCU\Software\Python\Astral`
key. The CI stand-in for "a clean machine reaches the UI" passes; the real clean-VM and laptop runs below
are still open.

## Still open

- [x] CI smoke green (`package.yml`), numbers above.
- [ ] Manual: a clean Windows 11 VM (no Python, uv, Node, Git): unzip, double-click `run.bat`, the UI
      opens in the browser. Note anything Windows asks (SmartScreen on `uv.exe` / `run.bat`, firewall
      prompt for port 8000, which only listens on 127.0.0.1).
- [ ] Reference laptop: the same from a fresh folder, then one generate job (the ML env on a real GPU),
      with a path under `Downloads\` to check the path-length note.
