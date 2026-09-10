#!/usr/bin/env bash
# Launch the standalone voice assistant from its dedicated Python 3.12 venv.
set -euo pipefail
cd "$(dirname "$0")/.."
exec ./voice-venv/bin/python -m voice_assistant "$@"
