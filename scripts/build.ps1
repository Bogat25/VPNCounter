$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    & uv sync --extra gpu --extra build
    if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }
    & .venv\Scripts\python.exe -m PyInstaller --noconfirm VPNCounter.spec
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
    Write-Output 'Built dist\VPNCounter\VPNCounter.exe. Keep the entire folder together.'
} finally {
    Pop-Location
}
