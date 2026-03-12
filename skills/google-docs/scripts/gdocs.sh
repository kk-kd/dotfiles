#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not found" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/gdocs.py" "$@"
