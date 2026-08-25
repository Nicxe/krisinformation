#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

PYTHON_BIN="${PYTHON_BIN:-python3.14}"

"$PYTHON_BIN" -m pytest -q custom_components/krisinformation/tests "$@"
