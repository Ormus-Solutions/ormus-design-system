#!/usr/bin/env bash
# scrub_gate.sh: the scrub, run the way check.sh needs it. The logic is in
# scrub_gate.py (read its header for what is excused and why).
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/scrub_gate.py "$@"
