$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Run scripts/setup.ps1 first.'
}
Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'vpn_counter') -WorkingDirectory $projectRoot -WindowStyle Hidden
