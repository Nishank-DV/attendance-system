#!/usr/bin/env bash
set -euo pipefail

echo "=== SmartVision Setup (Linux/macOS) ==="

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python is not installed or not in PATH. Install Python 3.10+ first."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  "$PYTHON_BIN" -m venv .venv
else
  echo "Virtual environment already exists."
fi

source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo ""
echo "Setup complete."
echo "Next commands:"
echo "1) source .venv/bin/activate"
echo "2) python backend/app.py"
