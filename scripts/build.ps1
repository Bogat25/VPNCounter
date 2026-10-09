$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    $targetExecutables = @(
        [IO.Path]::GetFullPath((Join-Path $projectRoot 'dist/VPNCounter/VPNCounter.exe')),
        [IO.Path]::GetFullPath((Join-Path $projectRoot 'dist/VPNCounter-portable.exe'))
    )
    $runningCopies = @(Get-Process -Name VPNCounter,VPNCounter-portable -ErrorAction SilentlyContinue | Where-Object { $_.Path -in $targetExecutables })
    if ($runningCopies.Count -gt 0) {
        throw 'Exit the packaged VPN Counter from its tray menu before rebuilding dist.'
    }
    & uv sync --locked --extra gpu --extra build
    if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }
    & .venv\Scripts\python.exe -m PyInstaller --noconfirm VPNCounter.spec
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
    Write-Output 'Built dist\VPNCounter\VPNCounter.exe. Keep the entire folder together.'
    Write-Output 'Built dist\VPNCounter-portable.exe. This file can run on its own.'
} finally {
    Pop-Location
}
