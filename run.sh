#!/usr/bin/env bash
# Udyam Digital: starts the app on http://localhost:8000  (back office: http://localhost:8000/admin)
set -e
cd "$(dirname "$0")"
VENV=".venv-$(uname -s)"
PY=python3
if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -c "import fastapi" >/dev/null 2>&1; then
  echo "Setting up Python environment in $VENV (first run only)…"
  $PY -m venv "$VENV"
  "$VENV/bin/python" -m pip install -q --upgrade pip
  "$VENV/bin/python" -m pip install -q -r requirements.txt
fi
if ! command -v tesseract >/dev/null 2>&1; then
  if ! "$VENV/bin/python" -c "import rapidocr_onnxruntime" >/dev/null 2>&1; then
    echo "Tesseract not found (Mac: brew install tesseract). Installing the pure-Python OCR fallback instead…"
    "$VENV/bin/python" -m pip install -q rapidocr-onnxruntime
  fi
fi
echo "Open http://localhost:${PORT:-8000}  ·  back office: http://localhost:${PORT:-8000}/admin"
exec "$VENV/bin/python" -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
