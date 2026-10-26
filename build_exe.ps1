# Builds R00T_ACCS.exe  (Windows, Python 3.10+)
#   .\build_exe.ps1            -> dist\R00T_ACCS.exe          (single file, slower first start)
#   .\build_exe.ps1 -OneDir    -> dist\R00T_ACCS\R00T_ACCS.exe (folder, instant start)
# Tip: build from a short path (e.g. C:\src\r00t_accs). Very deep folders can break Windows DLL loading inside the venv.
param([switch]$OneDir)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Step($what, [scriptblock]$cmd) {
    & $cmd
    if ($LASTEXITCODE -ne 0) { throw "build step failed: $what (exit $LASTEXITCODE)" }
}

if (-not (Test-Path ".venv-build")) {
    Step "create venv" { python -m venv .venv-build }
}
$py = ".\.venv-build\Scripts\python.exe"
Step "pip upgrade" { & $py -m pip install --quiet --upgrade pip }
Step "install deps" { & $py -m pip install --quiet -r requirements.txt pyinstaller }
Step "make icon" { & $py tools\make_icon.py }

$mode = if ($OneDir) { "--onedir" } else { "--onefile" }
Step "pyinstaller" {
    & $py -m PyInstaller --noconfirm --clean $mode --windowed --name R00T_ACCS `
        --icon assets\icon.ico `
        --add-data "assets;assets" `
        --collect-all moderngl --collect-all glcontext `
        --exclude-module tkinter --exclude-module matplotlib --exclude-module scipy `
        r00t_accs.py
}

$exe = if ($OneDir) { "dist\R00T_ACCS\R00T_ACCS.exe" } else { "dist\R00T_ACCS.exe" }
if (-not (Test-Path $exe)) { throw "exe was not produced" }
$mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host ""
Write-Host "built: $exe ($mb MB)"
