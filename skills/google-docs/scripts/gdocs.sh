#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not found" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALLER="$(cd "$SKILL_DIR/.." && pwd)/install-deps.py"

# Lazy-install deps on first use
if [[ -f "$SKILL_DIR/deps.json" ]] && [[ -f "$INSTALLER" ]]; then
    python3 "$INSTALLER" "$(basename "$SKILL_DIR")"
fi

exec python3 "$SCRIPT_DIR/gdocs.py" "$@"
