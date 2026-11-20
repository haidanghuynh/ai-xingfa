#!/usr/bin/env bash
# Chay XingfaCAD sau khi da ./scripts/deploy.sh
# Dung: ./scripts/run.sh [--port 8020] [--host 0.0.0.0]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
else
  PY=""
  for cand in python3 python; do
    # Bo qua alias gia cua Windows Store (python3 stub tra exit 49)
    if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys' >/dev/null 2>&1; then
      PY="$cand"
      break
    fi
  done
fi
[ -n "${PY:-}" ] || { echo "Chua co Python - chay ./scripts/deploy.sh truoc" >&2; exit 1; }

if [ ! -f web/dist/index.html ]; then
  echo "[warn] Chua co web/dist - chay ./scripts/deploy.sh de build giao dien React" >&2
fi

exec "$PY" -m xingfacad serve --host "${HOST:-127.0.0.1}" --port "${PORT:-8010}" "$@"
