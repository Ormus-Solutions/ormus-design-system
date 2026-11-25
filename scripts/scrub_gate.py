#!/usr/bin/env python3
"""The scrub, run the way check.sh needs it.

tokens.css, tokens.json and fusion.css are copied byte for byte from the
internal ormus-brand repo, and they hold ordinary CSS words (a pointer state,
theme names). A local deny-list entry that equals such a word would flag them
on every run. So one kind of finding is excused, and only this one:

  a "deny-list entry" hit in one of those three files, when the bytes of that
  version of the file hash to the sha256 that SOURCE.lock records for it
  (in the working tree, and in every commit of every ref: each commit is
  judged against the SOURCE.lock it holds).

Everything else fails: any other rule, any other file, any other version of
those files, a hit committed and later removed, a SOURCE.lock that breaks its
strict line grammar, an author e-mail, gitleaks, a setup error of the scrub,
a named deny-list that is missing or empty, a file name with control
characters. SOURCE.lock itself is never excused.

A sync that changes a synced file and its SOURCE.lock line together counts as
a sync, unless an ormus-brand checkout is at hand (ORMUS_BRAND_DIR, or a
sibling folder named ormus-brand). Then every lock the gate uses, the current
one and each one in history, is verified: each sha256 line must equal the
sha256 of `git -C BRAND show COMMIT:path` for that lock's commit, and a commit
the checkout lacks fails. Without a checkout the gate says the source was not
verified.

ODS_REQUIRE_BRAND=1 makes two things failures that are otherwise a notice: no
ormus-brand checkout ("source not verified"), and no deny-list found at all.
Run it before publishing:
  ODS_REQUIRE_BRAND=1 ORMUS_BRAND_DIR=<checkout> ./check.sh
With a checkout, every lock's commit, on any ref, must be the working-tree
lock's commit or an ancestor of it, so a rollback to an older brand commit
fails, on this branch or on another one.

The last line printed is always the "source:" line.

Usage: scripts/scrub_gate.py            (run from anywhere; scrub_gate.sh calls it)
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCUSABLE = ("tokens.css", "tokens.json", "fusion.css")
LOCK_PATHS = re.compile(
    r"tokens\.css|tokens\.json|fusion\.css|assets/midnight-lacquer\.jpg|assets/marks/[a-z0-9-]+\.png")
LOCK_FIXED = {
    "# Written by scripts/sync.sh. Do not edit by hand.",
    "# tests/test_drift.py checks every copied file against this record.",
    "source ormus-brand (internal to Ormus Solutions)",
}
HIT_FILE = re.compile(r"^(tokens\.css|tokens\.json|fusion\.css):\d+:\d+: deny-list entry \d+$")
HIT_HISTORY = re.compile(r"^history [0-9a-f]+: deny-list entry \d+$")


def parse_lock(text: str) -> dict[str, str] | None:
    """The sha256 of each file in a SOURCE.lock, or None when any line is off grammar."""
    if not text.endswith("\n"):
        return None
    sums: dict[str, str] = {}
    seen: set[str] = set()
    for line in text[:-1].split("\n"):
        if line in LOCK_FIXED:
            if line in seen:
                return None
            seen.add(line)
        elif re.fullmatch(r"commit [0-9a-f]{40}", line):
            if "commit" in seen:
                return None
            seen.add("commit")
        elif re.fullmatch(r"version \d+\.\d+\.\d+", line):
            if "version" in seen:
                return None
            seen.add("version")
        else:
            m = re.fullmatch(r"sha256 ([0-9a-f]{64})  (.+)", line)
            if not m or not LOCK_PATHS.fullmatch(m.group(2)) or m.group(2) in sums:
                return None
            sums[m.group(2)] = m.group(1)
    if not {"commit", "version"} <= seen:
        return None
    return sums


def brand_checkout() -> tuple[Path | None, str]:
    """(checkout, '') or (None, why-not). A named checkout that is not one is an error."""
    named = os.environ.get("ORMUS_BRAND_DIR")
    if named:
        brand = Path(named)
        if not (brand / ".git").exists():
            return None, f"ORMUS_BRAND_DIR is not a git checkout: {named}"
        return brand, ""
    sibling = ROOT.parent / "ormus-brand"
    if (sibling / ".git").exists():
        return sibling, ""
    return None, ""


def lock_commit(text: str) -> str:
    m = re.search(r"(?m)^commit ([0-9a-f]{40})$", text)
    return m.group(1) if m else ""


def verify_lock_against_brand(brand: Path, text: str) -> str:
    """'' when every sha256 line of this lock equals the brand's file at the lock's commit."""
    lock = parse_lock(text)
    if lock is None:
        return "a SOURCE.lock does not follow its line grammar"
    commit = lock_commit(text)
    have = subprocess.run(["git", "-C", str(brand), "cat-file", "-e", f"{commit}^{{commit}}"],
                          capture_output=True)
    if have.returncode != 0:
        return f"the ormus-brand checkout does not hold the locked commit {commit[:12]}"
    for path, want in lock.items():
        held = subprocess.run(["git", "-C", str(brand), "show", f"{commit}:{path}"],
                              capture_output=True)
        if held.returncode != 0:
            return f"{path} is not in ormus-brand at {commit[:12]}"
        if sha256(held.stdout) != want:
            return f"{path} does not match ormus-brand at {commit[:12]} (a sync must come from the brand)"
    return ""


def all_lock_texts() -> list[str]:
    """Each distinct SOURCE.lock in history order (oldest first), then the working-tree one."""
    texts: list[str] = []
    revs = subprocess.run(["git", "rev-list", "--all", "--reverse", "--topo-order"],
                          capture_output=True, text=True).stdout.split()
    for rev in revs:
        shown = subprocess.run(["git", "show", f"{rev}:SOURCE.lock"], capture_output=True)
        if shown.returncode == 0:
            text = shown.stdout.decode("utf-8", errors="replace")
            if text not in texts:
                texts.append(text)
    current = (ROOT / "SOURCE.lock").read_text(encoding="utf-8")
    if current in texts:
        texts.remove(current)
    texts.append(current)
    return texts


def check_forward(brand: Path, texts: list[str]) -> str:
    """'' when every lock's commit, on any ref, is the working-tree lock's commit or
    an ancestor of it. The working-tree lock is last in `texts`."""
    commits = [lock_commit(t) for t in texts]
    newest = commits[-1]
    for cur in commits[:-1]:
        if cur == newest:
            continue
        ok = subprocess.run(["git", "-C", str(brand), "merge-base", "--is-ancestor", cur, newest],
                            capture_output=True)
        if ok.returncode != 0:
            return (f"the lock went back or sideways: the brand commit {cur[:12]}, locked on some ref, "
                    f"is not an ancestor of the current one {newest[:12]}")
    return ""


def check_each_step_forward(brand: Path) -> str:
    """'' when no commit of any ref holds a lock older than its parent's lock, and the
    working-tree lock is not older than HEAD's. A rollback on a branch that is not
    checked out is caught here."""
    def is_forward(older: str, newer: str) -> bool:
        return older == newer or subprocess.run(
            ["git", "-C", str(brand), "merge-base", "--is-ancestor", older, newer],
            capture_output=True).returncode == 0

    def lock_at(rev: str) -> str:
        shown = subprocess.run(["git", "show", f"{rev}:SOURCE.lock"], capture_output=True)
        return lock_commit(shown.stdout.decode("utf-8", errors="replace")) if shown.returncode == 0 else ""

    rows = subprocess.run(["git", "rev-list", "--all", "--parents"],
                          capture_output=True, text=True).stdout.splitlines()
    for row in rows:
        sha, *parents = row.split()
        mine = lock_at(sha)
        for parent in parents:
            before = lock_at(parent)
            if mine and before and not is_forward(before, mine):
                return (f"the lock went back: commit {sha[:9]} locks brand {mine[:12]}, "
                        f"older than its parent's {before[:12]}")
    head = lock_at("HEAD")
    now = lock_commit((ROOT / "SOURCE.lock").read_text(encoding="utf-8"))
    if head and now and not is_forward(head, now):
        return f"the lock went back in the working tree: {now[:12]} is older than HEAD's {head[:12]}"
    return ""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def index_filter() -> int:
    """git filter-branch --index-filter: drop each excusable file of a commit
    when its blob matches the SOURCE.lock held by that same commit."""
    shown = subprocess.run(["git", "show", ":SOURCE.lock"], capture_output=True)
    if shown.returncode != 0:
        return 0
    lock = parse_lock(shown.stdout.decode("utf-8", errors="replace"))
    if lock is None:
        return 0
    for name in EXCUSABLE:
        staged = subprocess.run(["git", "ls-files", "-s", "--", name],
                                capture_output=True, text=True).stdout.split()
        if len(staged) < 2:
            continue
        blob = subprocess.run(["git", "cat-file", "blob", staged[1]],
                              capture_output=True, check=True).stdout
        if lock.get(name) == sha256(blob):
            subprocess.run(["git", "rm", "-q", "--cached", "--ignore-unmatch", "--", name],
                           check=True)
    return 0


def run_scrub(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(ROOT / "scripts" / "scrub.sh"), str(target)],
                          capture_output=True, text=True, errors="replace")


def fail(msg: str) -> int:
    print(f"check: {msg}", file=sys.stderr)
    return 1


def history_is_clean_apart_from_matching_blobs() -> tuple[bool, str]:
    """Scrub every ref's history with the matching synced blobs removed."""
    tmp = Path(tempfile.mkdtemp(prefix="ods-hist-"))
    try:
        clone = tmp / "h"
        env = {**os.environ, "FILTER_BRANCH_SQUELCH_WARNING": "1"}
        subprocess.run(["git", "clone", "-q", "--no-local", str(ROOT), str(clone)],
                       check=True, capture_output=True)
        subprocess.run(["git", "fetch", "-q", str(ROOT), "+refs/*:refs/orig/*"],
                       cwd=clone, check=True, capture_output=True)
        subprocess.run(
            ["git", "filter-branch", "-f", "--index-filter",
             f"python3 '{Path(__file__).resolve()}' --index-filter",
             "--tag-name-filter", "cat", "--", "--all"],
            cwd=clone, env=env, check=True, capture_output=True)
        shutil.rmtree(clone / ".git" / "refs" / "original", ignore_errors=True)
        subprocess.run(["git", "reflog", "expire", "--expire=now", "--all"],
                       cwd=clone, check=True, capture_output=True)
        subprocess.run(["git", "gc", "-q", "--prune=now"], cwd=clone, capture_output=True)
        res = run_scrub(clone)
        text = (res.stdout + res.stderr)
        return res.returncode == 0, text
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


STATE = {"source": ""}


def main(argv: list[str]) -> int:
    if argv[:1] == ["--index-filter"]:
        return index_filter()
    code = run(argv)
    sys.stdout.flush()
    sys.stderr.flush()
    if STATE["source"]:
        print(STATE["source"], file=sys.stderr if code else sys.stdout)
    return code


def run(argv: list[str]) -> int:
    _ = argv
    os.chdir(ROOT)

    named = os.environ.get("PLAYBOOK_DENYLIST")
    if named:
        path = Path(named).expanduser()
        if not path.is_file():
            return fail(f"PLAYBOOK_DENYLIST names a file that does not exist: {named}")
        entries = [x for x in path.read_text(encoding="utf-8", errors="replace").splitlines()
                   if x.strip() and not x.strip().startswith("#")]
        if not entries:
            return fail(f"PLAYBOOK_DENYLIST names a deny-list with no entries: {named}")

    listed = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                            capture_output=True, check=True).stdout.split(b"\0")
    for raw in listed:
        name = raw.decode("utf-8", errors="replace")
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
            return fail("a file name has control characters (it could fake a scrub line); rename it")

    lock = parse_lock((ROOT / "SOURCE.lock").read_text(encoding="utf-8"))
    if lock is None:
        return fail("SOURCE.lock does not follow its line grammar (see scripts/scrub_gate.py)")

    flag = os.environ.get("ODS_REQUIRE_BRAND", "")
    if flag not in ("", "1"):
        return fail('ODS_REQUIRE_BRAND must be exactly "1" (any other value is refused, not ignored)')
    require = flag == "1"
    if require and not named:
        default = Path("~/.config/playbooks/denylist.txt").expanduser()
        if not default.is_file() or not any(
                x.strip() and not x.strip().startswith("#")
                for x in default.read_text(encoding="utf-8", errors="replace").splitlines()):
            return fail("ODS_REQUIRE_BRAND=1 and no deny-list was found (set PLAYBOOK_DENYLIST)")

    brand, problem = brand_checkout()
    if problem:
        return fail(problem)
    if brand is None:
        STATE["source"] = "source: NOT VERIFIED (no ormus-brand checkout; set ORMUS_BRAND_DIR)"
        if require:
            return fail("ODS_REQUIRE_BRAND=1 and no ormus-brand checkout was found")
    else:
        texts = all_lock_texts()
        for text in texts:
            why = verify_lock_against_brand(brand, text)
            if why:
                return fail(f"source check failed: {why}")
        why = check_forward(brand, texts) or check_each_step_forward(brand)
        if why:
            return fail(f"source check failed: {why}")
        STATE["source"] = f"source: verified against the ormus-brand checkout ({len(texts)} lock(s) checked)"

    res = run_scrub(ROOT)
    output = res.stdout + res.stderr
    if res.returncode == 2:
        print(output, file=sys.stderr)
        return fail("the scrub could not run (setup error shown above)")
    warnings = [x for x in output.splitlines() if x.startswith("scrub: warning")]
    if res.returncode == 0:
        print("\n".join(warnings))
        print("scrub: clean (scripts/scrub_gate.py)")
        return 0
    if "scrub: gitleaks found" in output:
        print(output, file=sys.stderr)
        return fail("gitleaks found something")

    excused = 0
    history_hits = 0
    rest: list[str] = []
    for line in output.splitlines():
        if not line or line.startswith("scrub:"):
            continue
        if HIT_FILE.match(line):
            name = line.split(":", 1)[0]
            if lock.get(name) == sha256((ROOT / name).read_bytes()):
                excused += 1
                continue
        elif HIT_HISTORY.match(line):
            history_hits += 1
            continue
        rest.append(line)
    if rest:
        print("\n".join(warnings + rest))
        return fail("the scrub found something that is not a matching synced brand file")

    if history_hits:
        ok, text = history_is_clean_apart_from_matching_blobs()
        if not ok:
            print("\n".join(x for x in text.splitlines() if not x.startswith("scrub: warning")))
            return fail("a deny-list word is in the git history outside the matching synced files")

    print("\n".join(warnings))
    print(f"scrub: clean apart from {excused} deny-list words in the synced brand files "
          f"({history_hits} history entries), excused by checksum (scripts/scrub_gate.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
