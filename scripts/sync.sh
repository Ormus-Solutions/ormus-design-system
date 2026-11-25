#!/usr/bin/env bash
# sync.sh: copy the brand files again from an ormus-brand checkout and record
# the commit they came from.
#
# Usage: scripts/sync.sh BRAND_CHECKOUT [REF]
#   BRAND_CHECKOUT  a git checkout of the internal ormus-brand repo
#   REF             the commit, branch or tag to copy (default: origin/main).
#                   Run `git fetch` in the checkout first; this script does not.
#
# It reads the files from the commit with `git show`, not from the working
# folder, so a half-finished edit in the checkout can never reach this repo.
# It writes SOURCE.lock: the commit and a sha256 of every copied file.
# tests/test_drift.py fails when a copy no longer matches that record.
set -euo pipefail
IFS=$'\n\t'
cd "$(dirname "$0")/.."

brand="${1:-}"
ref="${2:-origin/main}"
if [[ -z "$brand" ]]; then
  echo "usage: scripts/sync.sh BRAND_CHECKOUT [REF]" >&2
  exit 2
fi
if ! git -C "$brand" rev-parse --git-dir >/dev/null 2>&1; then
  echo "sync: not a git checkout: $brand" >&2
  exit 2
fi
commit=$(git -C "$brand" rev-parse --verify --quiet "${ref}^{commit}") || {
  echo "sync: $ref is not a commit in $brand (try git fetch there first)" >&2
  exit 2
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

files=()
while IFS= read -r line; do
  [[ -z "$line" || "$line" == \#* ]] && continue
  files+=("$line")
done < scripts/sync-files.txt

for f in "${files[@]}"; do
  mkdir -p "$tmp/$(dirname "$f")"
  git -C "$brand" show "${commit}:${f}" > "$tmp/$f" || {
    echo "sync: $f is not in commit $commit" >&2
    exit 1
  }
done

version=$(sed -n 's/^  "version": "\([^"]*\)".*/\1/p' "$tmp/tokens.json" | head -n 1)

{
  echo "# Written by scripts/sync.sh. Do not edit by hand."
  echo "# tests/test_drift.py checks every copied file against this record."
  echo "source ormus-brand (internal to Ormus Solutions)"
  echo "commit $commit"
  echo "version ${version:-unknown}"
  for f in "${files[@]}"; do
    echo "sha256 $(sha256sum "$tmp/$f" | cut -d' ' -f1)  $f"
  done
} > "$tmp/SOURCE.lock"

for f in "${files[@]}"; do
  mkdir -p "$(dirname "$f")"
  cp "$tmp/$f" "$f"
done
cp "$tmp/SOURCE.lock" SOURCE.lock
echo "sync: ${#files[@]} files from ormus-brand ${commit:0:12} (version ${version:-unknown})"
