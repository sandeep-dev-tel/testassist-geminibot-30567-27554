#!/bin/bash
cd /home/kavia/workspace/code-generation/testassist-geminibot-30567-27554/backend_fastapi
# Use full path to flake8 in virtualenv, do not require 'source'
../venv/bin/flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

