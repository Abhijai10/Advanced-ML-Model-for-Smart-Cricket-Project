#!/usr/bin/env bash
set -euo pipefail

if [ -n "${PYTHON:-}" ]; then
  PYTHON_BIN="$PYTHON"
elif [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif [ -x "ml/venv/bin/python" ]; then
  PYTHON_BIN="ml/venv/bin/python"
else
  PYTHON_BIN="python"
fi

PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/smart-cricket-pycache}" "$PYTHON_BIN" -m pytest
npm --prefix frontend run lint
npm --prefix frontend run build
