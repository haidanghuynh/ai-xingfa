# Chay XingfaCAD GUI (tu dong dung .venv va nap .env)
# Dung: .\run.ps1            (mac dinh 127.0.0.1:8010)
#       .\run.ps1 --port 8020
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $root 'scripts\run.ps1') @args
