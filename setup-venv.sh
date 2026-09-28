#!/usr/bin/env bash
# setup-venv.sh - Create .venv and install dependencies

set -e

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Virtual environment ready!"
echo "Activate with: source .venv/bin/activate"
echo "Run generator: python tools/generate_libvlc.py --help"