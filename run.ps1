# Chạy XingfaCAD GUI mà không cần pip install -e .
# Dùng: .\run.ps1            (mặc định cổng 8010)
#       .\run.ps1 --port 8020
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = Join-Path $root 'src'
Set-Location $root
python -m xingfacad serve @args
