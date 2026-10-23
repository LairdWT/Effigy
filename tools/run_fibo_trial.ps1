param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$laneRoot = Join-Path $projectRoot 'scratch/lanes/fibo2'
$settingsPath = Join-Path $laneRoot 'settings.json'
if (-not (Test-Path -LiteralPath $settingsPath -PathType Leaf)) {
    throw 'FIBO trial is not provisioned. Run tools/provision_fibo_trial.py first.'
}
$listener = Get-NetTCPConnection -State Listen -LocalPort 8380 -ErrorAction SilentlyContinue
if ($listener) {
    throw 'Port 8380 is occupied. The existing process was left unchanged.'
}
$python = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Installed Effigy backend interpreter is missing.'
}
$scratchRoot = Join-Path $laneRoot 'scratch'
New-Item -ItemType Directory -Path $scratchRoot -Force | Out-Null
$env:EFFIGY_SETTINGS = $settingsPath
$env:EFFIGY_NO_BROWSER = '1'
$env:EFFIGY_PORT = '8380'
$env:EFFIGY_MULTI_VIEW = '1'
$env:EFFIGY_SCRATCH = $scratchRoot
$env:EFFIGY_LIBRARY = (Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json).library
$env:EFFIGY_MODELS = (Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json).models
$env:EFFIGY_GLTFPACK = Join-Path $projectRoot 'gltfpack/v0.25/gltfpack.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
$process = Start-Process -FilePath $python -ArgumentList @('-B', '-m', 'server') `
    -WorkingDirectory $laneRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $scratchRoot 'runtime.stdout.log') `
    -RedirectStandardError (Join-Path $scratchRoot 'runtime.stderr.log')
Write-Output "FIBO trial launcher PID $($process.Id), URL http://127.0.0.1:8380"
