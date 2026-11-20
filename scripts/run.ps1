# Chay XingfaCAD sau khi da .\scripts\deploy.ps1
# Dung: .\scripts\run.ps1 [--port 8020] [--host 0.0.0.0]
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$envFile = Join-Path $root '.env'
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
      [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim(), 'Process')
    }
  }
}

$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
if (-not (Test-Path (Join-Path $root 'web\dist\index.html'))) {
  Write-Warning 'Chua co web/dist - chay .\scripts\deploy.ps1 de build giao dien'
}

$env:PYTHONPATH = Join-Path $root 'src'
$hostAddr = if ($env:HOST) { $env:HOST } else { '127.0.0.1' }
$port = if ($env:PORT) { $env:PORT } else { '8010' }
& $py -m xingfacad serve --host $hostAddr --port $port @args
