$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    $targetExecutable = [IO.Path]::GetFullPath((Join-Path $projectRoot 'dist/VPNCounter/VPNCounter.exe'))
    $runningCopies = @(Get-Process -Name VPNCounter -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $targetExecutable })
    if ($runningCopies.Count -gt 0) {
        throw 'Exit the packaged VPN Counter from its tray menu before rebuilding dist/VPNCounter.'
    }
    & uv sync --locked --extra gpu --extra build
    if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }
    & .venv\Scripts\python.exe -m PyInstaller --noconfirm VPNCounter.spec
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
    Write-Output 'Built dist\VPNCounter\VPNCounter.exe. Keep the entire folder together.'
} finally {
    Pop-Location
}
