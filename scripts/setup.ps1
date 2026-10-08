param([switch]$CpuOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        if ($CpuOnly) { & uv sync --python 3.12 }
        else { & uv sync --python 3.12 --extra gpu }
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    } else {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 or uv before running setup.' }
        $pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
        & $pythonPath -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw 'pip preparation failed.' }
        $package = if ($CpuOnly) { '.' } else { '.[gpu]' }
        & $pythonPath -m pip install -e $package
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    }
    Write-Output 'Setup complete. Launch with Start VPN Counter.cmd or scripts/run.ps1.'
    Write-Output 'The model is downloaded the first time you start listening.'
} finally {
    Pop-Location
}
