#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

card_test_dir="$(mktemp -d "${TMPDIR:-/tmp}/krisinformation-card.XXXXXX")"
trap 'rm -rf -- "$card_test_dir"' EXIT
card_module_path="$card_test_dir/krisinformation-alert-card.mjs"
cp custom_components/krisinformation/www/krisinformation-alert-card.js \
  "$card_module_path"

node --check "$card_module_path"
KRISINFORMATION_CARD_MODULE_PATH="$card_module_path" node \
  custom_components/krisinformation/tests/test_card.mjs
