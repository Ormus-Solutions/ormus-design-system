"""The copies from ormus-brand must match what the recorded commit holds.

Two checks:
  1. Always: every copied file matches the sha256 in SOURCE.lock, and the lock
     lists exactly the files in scripts/sync-files.txt.
  2. When an ormus-brand checkout is at hand (the ORMUS_BRAND_DIR variable, or a
     sibling folder named ormus-brand): it must hold the recorded commit, and
     every copied file is byte-for-byte what `git show COMMIT:path` returns.
     The test skips only when ORMUS_BRAND_DIR is unset and no sibling exists.
Fix a failure by running scripts/sync.sh, never by editing a copy.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_lock() -> tuple[str, dict[str, str]]:
    commit = ""
    sums: dict[str, str] = {}
    for line in (ROOT / "SOURCE.lock").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if parts[0] == "commit":
            commit = parts[1]
        elif parts[0] == "sha256":
            sums[parts[2].strip()] = parts[1]
    return commit, sums


def listed_files() -> list[str]:
    lines = (ROOT / "scripts" / "sync-files.txt").read_text(encoding="utf-8").splitlines()
    return [x for x in lines if x and not x.startswith("#")]


def brand_state(environ: Mapping[str, str], root: Path, commit: str) -> tuple[str, str]:
    """('ok'|'skip'|'fail', why): is there an ormus-brand checkout holding the commit?

    Skip only when ORMUS_BRAND_DIR is unset and no sibling checkout exists. A
    checkout that is named or found but cannot give the commit is a failure,
    because the check would otherwise pass without having run."""
    named = environ.get("ORMUS_BRAND_DIR")
    sibling = root.parent / "ormus-brand"
    if named:
        brand = Path(named)
        if not (brand / ".git").exists():
            return "fail", f"ORMUS_BRAND_DIR is not a git checkout: {named}"
    elif (sibling / ".git").exists():
        brand = sibling
    else:
        return "skip", "no ormus-brand checkout (set ORMUS_BRAND_DIR); checksums were checked"
    have = subprocess.run(["git", "-C", str(brand), "cat-file", "-e", f"{commit}^{{commit}}"],
                          capture_output=True)
    if have.returncode != 0:
        return "fail", f"the ormus-brand checkout {brand} does not hold {commit[:12]} (git fetch there)"
    return "ok", str(brand)


class Drift(unittest.TestCase):
    def test_lock_lists_the_synced_files(self) -> None:
        commit, sums = read_lock()
        self.assertRegex(commit, r"^[0-9a-f]{40}$")
        self.assertEqual(sorted(sums), sorted(listed_files()))

    def test_copies_match_recorded_checksums(self) -> None:
        _, sums = read_lock()
        for path, want in sums.items():
            got = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            self.assertEqual(got, want, f"{path} drifted from SOURCE.lock: run scripts/sync.sh")

    def test_copies_match_the_recorded_commit(self) -> None:
        commit, sums = read_lock()
        state, why = brand_state(os.environ, ROOT, commit)
        if state == "skip":
            self.skipTest(why)
        self.assertEqual(state, "ok", why)
        for path in sums:
            held = subprocess.run(["git", "-C", why, "show", f"{commit}:{path}"],
                                  capture_output=True, check=True).stdout
            self.assertEqual((ROOT / path).read_bytes(), held,
                             f"{path} differs from ormus-brand@{commit[:12]}: run scripts/sync.sh")

    def test_a_checkout_without_the_commit_fails_instead_of_skipping(self) -> None:
        commit, _ = read_lock()
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True, capture_output=True)
            state, _ = brand_state({"ORMUS_BRAND_DIR": tmp}, ROOT, commit)
            self.assertEqual(state, "fail")
            state, _ = brand_state({"ORMUS_BRAND_DIR": tmp + "/missing"}, ROOT, commit)
            self.assertEqual(state, "fail")

    def test_no_checkout_at_all_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_root = Path(tmp) / "repo"
            fake_root.mkdir()
            state, _ = brand_state({}, fake_root, "0" * 40)
            self.assertEqual(state, "skip")


if __name__ == "__main__":
    unittest.main()
