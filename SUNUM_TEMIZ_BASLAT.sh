#!/usr/bin/env bash
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$ROOT/scripts/sunum_cleanup.py"
exec bash "$ROOT/SUNUM_BASLAT.sh" "${1:-pink}"
