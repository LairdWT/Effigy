@echo off
rem Start Effigy: sync the backend env, build the UI when its source changed, serve on 127.0.0.1 (port 8000
rem unless chosen in Setup or set in EFFIGY_PORT; python -m server opens the browser there).
cd /d "%~dp0"
rem portable zip (tools/package.py): the bundled uv; Python, uv cache and envs stay in this folder
if exist uv.exe (
  set "PATH=%~dp0;%PATH%"
  set "UV_PYTHON_INSTALL_DIR=%~dp0python"
  set "UV_CACHE_DIR=%~dp0cache"
  set "UV_PYTHON_PREFERENCE=only-managed"
)
where uv >nul 2>nul || (echo uv not found: install it from https://docs.astral.sh/uv/ & exit /b 1)
uv sync --frozen || exit /b 1
rem the ML venv for steps (torch cu128 + our wheels); a no-op once synced
cmd /c "set UV_PROJECT_ENVIRONMENT=.venv-ml&& uv sync --frozen --group ml" || exit /b 1
rem the skinning venv (M20, SkinTokens): its own because of a GPL-provenance subtree; a no-op once synced
cmd /c "set UV_PROJECT_ENVIRONMENT=.venv-skin&& uv sync --frozen --group skin" || exit /b 1
rem pinned Blender 5.2.2, downloaded and SHA-256 checked on first run
uv run python -m server.blender_install || exit /b 1
uv run python -m server.gltfpack_install || exit /b 1
rem the UI: built when missing or older than its source (a pull), npm ci first when its lock changed
uv run python tools\ui_stale.py
set "stale=%errorlevel%"
if "%stale%"=="0" goto ui_ready
where npm >nul 2>nul && goto ui_build
if exist ui\dist\index.html (
  echo ui\dist is older than ui\src and npm was not found: serving the old UI
  goto ui_ready
)
echo ui\dist missing and npm not found: install Node 22 from https://nodejs.org/ & exit /b 1
:ui_build
pushd ui
if "%stale%"=="2" (call npm ci || exit /b 1)
call npm run build || exit /b 1
popd
:ui_ready
uv run python -m server
