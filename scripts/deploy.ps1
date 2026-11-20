# XingfaCAD - cai dat & build tren Windows (PowerShell)
# Dung: .\scripts\deploy.ps1 [-NoWeb] [-SkipInstall]
param(
  [switch]$NoWeb,
  [switch]$SkipInstall
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (-not $SkipInstall) {
  if (-not (Test-Path '.venv')) {
    Write-Host '[deploy] Tao virtualenv .venv'
    python -m venv .venv
  }
  $py = Join-Path $root '.venv\Scripts\python.exe'
  & $py -m pip install --upgrade pip
  & $py -m pip install -r requirements.txt
  & $py -m pip install -e .
} else {
  $py = Join-Path $root '.venv\Scripts\python.exe'
  if (-not (Test-Path $py)) { $py = 'python' }
}

if (-not $NoWeb) {
  Write-Host '[deploy] Cai & build giao dien React'
  Push-Location web
  if (Test-Path 'package-lock.json') { npm ci } else { npm install }
  npm run build
  Pop-Location
}

if (-not (Test-Path '.env') -and (Test-Path '.env.example')) {
  Copy-Item '.env.example' '.env'
  Write-Host '[deploy] Da tao .env tu .env.example (dien API key neu dung AI)'
}

& $py -c "import xingfacad, fastapi, openpyxl, ezdxf, reportlab; print('xingfacad', xingfacad.__version__)"
if (Test-Path 'web\dist\index.html') {
  Write-Host '[deploy] Giao dien: web/dist OK' -ForegroundColor Green
} else {
  Write-Warning 'Chua co web/dist - server se dung static/ fallback'
}
Write-Host 'Xong. Chay: .\scripts\run.ps1' -ForegroundColor Green
