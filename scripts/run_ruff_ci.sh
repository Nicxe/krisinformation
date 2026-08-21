#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

RUFF_VERSION="${RUFF_VERSION:-0.15.12}"

if command -v uvx >/dev/null 2>&1; then
  RUFF=(uvx --from "ruff==${RUFF_VERSION}" ruff)
else
  RUFF=(python -m ruff)
fi

TARGET="custom_components/krisinformation"

"${RUFF[@]}" check "$TARGET"
"${RUFF[@]}" format --check "$TARGET"
