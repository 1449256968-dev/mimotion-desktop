$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        throw 'Create .venv and install requirements-desktop.txt first; see INSTALL.md.'
    }
    & $python -m PyInstaller --noconfirm --clean --onefile --windowed --name MiMotionDesktop --icon assets/app.ico --add-data 'assets;assets' --add-data 'LICENSE;.' --add-data 'NOTICE.txt;.' --add-data 'THIRD_PARTY_NOTICES.txt;.' desktop_app.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    Write-Output 'Built dist\MiMotionDesktop.exe'
} finally {
    Pop-Location
}
