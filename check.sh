#!/usr/bin/env bash
# check.sh: the one gate for this repo. Run it before every commit. It stops
# at the first failure and exits non-zero.
#   1. tests: the copies match SOURCE.lock (and the recorded ormus-brand
#      commit when a checkout is at hand), tokens.json agrees with tokens.css,
#      the Tailwind files and base.css follow the tokens, the demo is clean
#   2. contrast: the measured ratio of every text/background pair the style
#      guide promises
#   3. html: the demo page (structure, local files, no written-out colors)
#   4. shellcheck on every shell script, when it is installed
#   5. scrub: secrets, e-mails, hosts, home paths and your deny-list
set -euo pipefail
IFS=$'\n\t'
cd "$(dirname "$0")"

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "check: needs Python 3.11 or newer (python3 --version)" >&2
  exit 1
fi

echo "== tests"
python3 -m unittest discover -s tests

echo "== contrast"
python3 scripts/contrast.py

echo "== html"
python3 scripts/check_html.py examples/index.html

echo "== shellcheck"
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck check.sh scripts/*.sh
  echo "ok"
else
  echo "shellcheck is not installed; skipped"
fi

echo "== scrub"
bash scripts/scrub_gate.sh

echo "check: ok"
