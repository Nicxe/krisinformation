#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

RUFF_VERSION="${RUFF_VERSION:-0.15.12}"

if ! command -v uvx >/dev/null 2>&1; then
  echo "uvx is required to run Ruff ${RUFF_VERSION}" >&2
  exit 1
fi

TARGET="custom_components/krisinformation"

uvx --from "ruff==${RUFF_VERSION}" ruff format "$TARGET"
uvx --from "ruff==${RUFF_VERSION}" ruff check --fix "$TARGET"
