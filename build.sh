#!/usr/bin/env bash
# Build the Quartz static site from the vault.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_PATH="${VAULT_PATH:-$SCRIPT_DIR/vault}"
QUARTZ_DIR="$SCRIPT_DIR/quartz"
CONFIG_PATH="$SCRIPT_DIR/quartz.config.yaml"

echo "[build] Using vault: $VAULT_PATH"
echo "[build] Building Quartz..."

cd "$QUARTZ_DIR"
npx quartz build \
  --directory "$VAULT_PATH" \
  --config "$CONFIG_PATH" \
  --output "$QUARTZ_DIR/public"

echo "[build] Done. Output: $QUARTZ_DIR/public"
