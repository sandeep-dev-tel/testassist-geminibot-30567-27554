#!/bin/bash
cd /home/kavia/workspace/code-generation/testassist-geminibot-30567-27554/backend_fastapi

# Use flake8 from virtualenv if available, else fall back to global
if [ -x "../venv/bin/flake8" ]; then
  ../venv/bin/flake8 .
elif command -v flake8 &>/dev/null; then
  flake8 .
else
  echo "ERROR: flake8 not found. Please install flake8."
  exit 1
fi

LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi
