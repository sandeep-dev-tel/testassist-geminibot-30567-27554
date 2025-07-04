#!/bin/bash
# Sets up Python venv and installs all requirements for the FastAPI backend.

set -e

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "Virtual environment and dependencies setup complete."
