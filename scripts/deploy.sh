#!/usr/bin/env bash
# XingfaCAD - cai dat & build tren may moi (Linux / macOS / WSL / Git Bash)
# Dung: ./scripts/deploy.sh [--no-web] [--skip-install] [--check]
#   --no-web       khong cai/build giao dien React (dung static/ fallback)
#   --skip-install bo qua pip/npm, chi build web + kiem tra
#   --check        chi kiem tra Python/Node, khong cai gi
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NO_WEB=0
SKIP_INSTALL=0
CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --no-web) NO_WEB=1 ;;
    --skip-install) SKIP_INSTALL=1 ;;
    --check) CHECK_ONLY=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Tham so khong hop le: $arg" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[loi]\033[0m %s\n' "$*" >&2; exit 1; }

PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    PY="$cand"
    break
  fi
done
[ -n "$PY" ] || fail "Can Python >= 3.10 (cai them python3 + python3-venv)"
log "Python: $($PY --version 2>&1)"

if [ "$NO_WEB" -eq 0 ]; then
  command -v node >/dev/null 2>&1 || fail "Can Node >= 18 de build giao dien (hoac chay --no-web)"
  node -e 'process.exit(parseInt(process.versions.node, 10) >= 18 ? 0 : 1)' \
    || fail "Node phai >= 18 (hien tai $(node --version))"
  command -v npm >/dev/null 2>&1 || fail "Khong tim thay npm"
  log "Node: $(node --version) | npm: $(npm --version)"
else
  log "Bo qua giao dien React (--no-web)"
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  log "Moi truong OK. Chay: ./scripts/run.sh"
  exit 0
fi

if [ "$SKIP_INSTALL" -eq 0 ]; then
  if [ ! -d .venv ]; then
    log "Tao virtualenv .venv"
    "$PY" -m venv .venv || fail "Khong tao duoc venv - cai python3-venv roi thu lai"
  fi
  # shellcheck disable=SC1091
  . .venv/bin/activate
  log "Cai Python dependencies"
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r requirements.txt
  python -m pip install -e .
else
  if [ -x .venv/bin/python ]; then
    # shellcheck disable=SC1091
    . .venv/bin/activate
  else
    warn "Chua co .venv - dung Python he thong"
  fi
fi

if [ "$NO_WEB" -eq 0 ]; then
  log "Cai & build giao dien React"
  cd web
  if [ -f package-lock.json ]; then npm ci; else npm install; fi
  npm run build
  cd "$ROOT"
fi

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  log "Da tao .env tu .env.example (dien API key neu dung AI)"
fi

log "Kiem tra nhanh"
python -c "import xingfacad, fastapi, openpyxl, ezdxf, reportlab; print('xingfacad', xingfacad.__version__)"
if [ -f web/dist/index.html ]; then
  log "Giao dien: web/dist OK"
else
  warn "Chua co web/dist - server se dung static/ fallback"
fi

cat <<'EOF'

Xong. Chay server:
  ./scripts/run.sh                              # http://127.0.0.1:8010
  HOST=0.0.0.0 PORT=8010 ./scripts/run.sh       # cho may khac trong LAN

run.sh tu nap .env (API key AI) neu co. De build lai giao dien: cd web && npm run build
EOF
