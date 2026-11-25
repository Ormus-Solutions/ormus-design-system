"""The scrub gate must excuse deny-list words in the synced brand files by
checksum and nothing else, in the files and in the git history."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Built at run time so this file never holds the words itself.
SYNCED_WORD = "ho" + "ver"
OTHER_WORD = "zzq" + "unique" + "word"
ENV = {**os.environ,
       "GIT_AUTHOR_NAME": "Test", "GIT_COMMITTER_NAME": "Test",
       "GIT_AUTHOR_EMAIL": "test@users.noreply.github.com",
       "GIT_COMMITTER_EMAIL": "test@users.noreply.github.com"}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env=ENV, check=True,
                          capture_output=True, text=True).stdout


class Gate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ods-gate-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "vendor")
        self.denylist = self.tmp / "deny.txt"
        self.denylist.write_text(f"{SYNCED_WORD}\n{OTHER_WORD}\n", encoding="utf-8")

    def run_gate(self, denylist: Path | str | None = None,
                 extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = {**ENV, "PLAYBOOK_DENYLIST": str(denylist or self.denylist)}
        env.pop("ORMUS_BRAND_DIR", None)
        env.update(extra_env or {})
        return subprocess.run(["bash", "scripts/scrub_gate.sh"], cwd=self.repo, env=env,
                              capture_output=True, text=True)

    def make_brand(self, overrides: dict[str, bytes] | None = None) -> str:
        """A stand-in ormus-brand checkout holding the synced files; returns its commit."""
        brand = self.tmp / "brand"
        if not brand.exists():
            git(self.tmp, "init", "-q", "-b", "main", "brand")
        files = [x for x in (self.repo / "scripts" / "sync-files.txt").read_text(encoding="utf-8").splitlines()
                 if x and not x.startswith("#")]
        for name in files:
            dest = brand / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((overrides or {}).get(name, (self.repo / name).read_bytes()))
        git(brand, "add", "-A")
        git(brand, "commit", "-q", "--allow-empty", "-m", "brand")
        return git(brand, "rev-parse", "HEAD").strip()

    def lock_commit(self, sha: str) -> None:
        lock = self.repo / "SOURCE.lock"
        lock.write_text(re.sub(r"(?m)^commit [0-9a-f]{40}$", f"commit {sha}",
                               lock.read_text(encoding="utf-8")), encoding="utf-8")

    def reset_history(self) -> None:
        """One root commit holding the working tree, as the repo has after its squash."""
        shutil.rmtree(self.repo / ".git")
        git(self.repo, "init", "-q", "-b", "main")
        self.commit("root")

    def brand_env(self) -> dict[str, str]:
        return {"ORMUS_BRAND_DIR": str(self.tmp / "brand")}

    def gate(self) -> int:
        return self.run_gate().returncode

    def commit(self, msg: str = "c") -> None:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", msg)

    def lock_with(self, name: str, data: bytes) -> None:
        """Rewrite the SOURCE.lock sha256 line of one file to match `data`."""
        lock = self.repo / "SOURCE.lock"
        digest = hashlib.sha256(data).hexdigest()
        text = re.sub(rf"(?m)^sha256 [0-9a-f]{{64}}  {re.escape(name)}$",
                      f"sha256 {digest}  {name}", lock.read_text(encoding="utf-8"))
        lock.write_text(text, encoding="utf-8")

    # --- what is excused -------------------------------------------------
    def test_synced_file_words_are_excused_by_checksum(self) -> None:
        res = self.run_gate()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("excused by checksum", res.stdout)
        self.assertNotIn("FAILED", res.stdout)

    def test_a_real_resync_with_a_new_lock_is_excused(self) -> None:
        css = self.repo / "tokens.css"
        data = css.read_bytes() + f"/* {SYNCED_WORD} */\n".encode()
        css.write_bytes(data)
        self.lock_with("tokens.css", data)
        self.commit("resync")
        self.assertEqual(self.gate(), 0)

    # --- the source is verified against ormus-brand when a checkout is at hand
    def test_without_a_checkout_it_says_the_source_was_not_verified(self) -> None:
        res = self.run_gate()
        self.assertEqual(res.returncode, 0)
        self.assertIn("source: NOT VERIFIED", res.stdout)

    def test_a_locked_commit_the_checkout_lacks_fails(self) -> None:
        self.make_brand()
        res = self.run_gate(extra_env=self.brand_env())  # the lock names a commit the stand-in lacks
        self.assertNotEqual(res.returncode, 0)

    def test_a_matching_checkout_verifies_the_source(self) -> None:
        self.lock_commit(self.make_brand())
        self.reset_history()
        res = self.run_gate(extra_env=self.brand_env())
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("source: verified", res.stdout)

    def test_a_self_consistent_planted_sync_fails_with_a_checkout(self) -> None:
        self.lock_commit(self.make_brand())
        css = self.repo / "tokens.css"
        planted = css.read_bytes() + f"/* {OTHER_WORD} */\n".encode()
        css.write_bytes(planted)
        self.lock_with("tokens.css", planted)  # file and lock changed together
        self.reset_history()
        self.assertEqual(self.gate(), 0)  # without a checkout this passes by design
        res = self.run_gate(extra_env=self.brand_env())
        self.assertNotEqual(res.returncode, 0)

    def test_a_real_resync_passes_with_a_checkout(self) -> None:
        css = self.repo / "tokens.css"
        data = css.read_bytes() + f"/* {SYNCED_WORD} */\n".encode()
        sha = self.make_brand({"tokens.css": data})
        css.write_bytes(data)
        self.lock_with("tokens.css", data)
        self.lock_commit(sha)
        self.reset_history()
        res = self.run_gate(extra_env=self.brand_env())
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_a_planted_historical_lock_fails_with_a_checkout(self) -> None:
        css = self.repo / "tokens.css"
        original = css.read_bytes()
        self.lock_commit(self.make_brand())
        self.reset_history()
        planted = original + f"/* {OTHER_WORD} */\n".encode()
        css.write_bytes(planted)
        self.lock_with("tokens.css", planted)
        self.commit("planted sync")
        css.write_bytes(original)
        self.lock_with("tokens.css", original)
        self.commit("restored")
        res = self.run_gate(extra_env=self.brand_env())
        self.assertNotEqual(res.returncode, 0)

    # --- ODS_REQUIRE_BRAND, forward-only locks, source line last ---------------
    def test_require_brand_fails_without_a_checkout(self) -> None:
        res = self.run_gate(extra_env={"ODS_REQUIRE_BRAND": "1"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("NOT VERIFIED", res.stdout + res.stderr)

    def test_require_brand_passes_with_a_matching_checkout(self) -> None:
        self.lock_commit(self.make_brand())
        self.reset_history()
        res = self.run_gate(extra_env={**self.brand_env(), "ODS_REQUIRE_BRAND": "1"})
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_require_brand_fails_when_no_denylist_is_found(self) -> None:
        self.lock_commit(self.make_brand())
        self.reset_history()
        home = self.tmp / "emptyhome"
        home.mkdir()
        res = self.run_gate(extra_env={**self.brand_env(), "ODS_REQUIRE_BRAND": "1",
                                       "PLAYBOOK_DENYLIST": "", "HOME": str(home)})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("no deny-list", res.stdout + res.stderr)

    def test_a_forward_resync_passes_the_order_check(self) -> None:
        css = self.repo / "tokens.css"
        original = css.read_bytes()
        self.lock_commit(self.make_brand())
        self.reset_history()
        newer = original + f"/* {SYNCED_WORD} */\n".encode()
        sha2 = self.make_brand({"tokens.css": newer})
        css.write_bytes(newer)
        self.lock_with("tokens.css", newer)
        self.lock_commit(sha2)
        self.commit("forward resync")
        res = self.run_gate(extra_env=self.brand_env())
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_a_rollback_to_an_older_brand_commit_fails(self) -> None:
        css = self.repo / "tokens.css"
        original = css.read_bytes()
        sha1 = self.make_brand()
        newer = original + f"/* {SYNCED_WORD} */\n".encode()
        sha2 = self.make_brand({"tokens.css": newer})
        css.write_bytes(newer)
        self.lock_with("tokens.css", newer)
        self.lock_commit(sha2)
        self.reset_history()
        css.write_bytes(original)
        self.lock_with("tokens.css", original)
        self.lock_commit(sha1)
        self.commit("rollback")
        res = self.run_gate(extra_env=self.brand_env())
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("went back", res.stdout + res.stderr)

    def test_the_source_line_is_the_last_line(self) -> None:
        res = self.run_gate()
        self.assertTrue((res.stdout + res.stderr).strip().splitlines()[-1].startswith("source:"))
        self.lock_commit(self.make_brand())
        self.reset_history()
        res = self.run_gate(extra_env=self.brand_env())
        self.assertTrue(res.stdout.strip().splitlines()[-1].startswith("source: verified"))

    # --- H1: only the exact bytes the lock names are excused ---------------
    def test_modified_synced_file_is_not_excused(self) -> None:
        css = self.repo / "tokens.css"
        css.write_bytes(css.read_bytes() + f"/* {OTHER_WORD} */\n".encode())
        self.assertNotEqual(self.gate(), 0)

    def test_planted_word_in_a_synced_file_then_restored_still_fails(self) -> None:
        css = self.repo / "tokens.css"
        original = css.read_bytes()
        css.write_bytes(original + f"/* {OTHER_WORD} */\n".encode())
        self.commit("plant")
        css.write_bytes(original)
        self.commit("restore")
        self.assertNotEqual(self.gate(), 0)

    # --- H2: nothing is excused through SOURCE.lock or sync-files.txt -------
    def test_a_comment_appended_to_the_lock_fails(self) -> None:
        lock = self.repo / "SOURCE.lock"
        lock.write_text(lock.read_text(encoding="utf-8") + f"# {OTHER_WORD}\n", encoding="utf-8")
        self.assertNotEqual(self.gate(), 0)

    def test_an_unknown_lock_line_fails(self) -> None:
        lock = self.repo / "SOURCE.lock"
        lock.write_text(lock.read_text(encoding="utf-8") + "note hello\n", encoding="utf-8")
        self.assertNotEqual(self.gate(), 0)

    def test_an_extra_name_in_sync_files_and_lock_is_not_excused(self) -> None:
        data = f"{OTHER_WORD}\n".encode()
        (self.repo / "extra.txt").write_bytes(data)
        with (self.repo / "scripts" / "sync-files.txt").open("a", encoding="utf-8") as f:
            f.write("extra.txt\n")
        with (self.repo / "SOURCE.lock").open("a", encoding="utf-8") as f:
            f.write(f"sha256 {hashlib.sha256(data).hexdigest()}  extra.txt\n")
        self.assertNotEqual(self.gate(), 0)

    def test_a_word_in_the_lock_itself_fails(self) -> None:
        lock = self.repo / "SOURCE.lock"
        text = lock.read_text(encoding="utf-8").replace(
            "source ormus-brand (internal to Ormus Solutions)", f"source {OTHER_WORD}")
        lock.write_text(text, encoding="utf-8")
        self.assertNotEqual(self.gate(), 0)

    # --- the rest of the scrub still bites ----------------------------------
    def test_word_in_a_working_tree_file_fails(self) -> None:
        (self.repo / "notes.txt").write_text(f"{OTHER_WORD}\n", encoding="utf-8")
        self.assertNotEqual(self.gate(), 0)

    def test_word_added_then_removed_still_fails(self) -> None:
        note = self.repo / "notes.txt"
        note.write_text(f"{OTHER_WORD}\n", encoding="utf-8")
        self.commit("add")
        note.unlink()
        self.commit("remove")
        self.assertNotEqual(self.gate(), 0)

    def test_word_only_in_a_non_branch_ref_still_fails(self) -> None:
        git(self.repo, "switch", "-q", "-c", "tmp")
        (self.repo / "notes.txt").write_text(f"{OTHER_WORD}\n", encoding="utf-8")
        self.commit("hidden")
        sha = git(self.repo, "rev-parse", "HEAD").strip()
        git(self.repo, "switch", "-q", "main")
        git(self.repo, "branch", "-q", "-D", "tmp")
        git(self.repo, "update-ref", "refs/stash", sha)
        self.assertNotEqual(self.gate(), 0)

    def test_a_file_name_with_a_newline_fails(self) -> None:
        name = "a\ntokens.css:1:1: deny-list entry 1"
        (self.repo / name).write_text(f"{OTHER_WORD}\n", encoding="utf-8")
        self.assertNotEqual(self.gate(), 0)

    # --- M-a: setup errors stop the gate ------------------------------------
    def test_a_missing_denylist_fails_when_one_is_named(self) -> None:
        res = self.run_gate(self.tmp / "nope.txt")
        self.assertNotEqual(res.returncode, 0)
        self.assertNotIn("excused", res.stdout)

    def test_an_empty_denylist_fails_when_one_is_named(self) -> None:
        empty = self.tmp / "empty.txt"
        empty.write_text("# nothing\n", encoding="utf-8")
        self.assertNotEqual(self.run_gate(empty).returncode, 0)

    def test_a_denylist_inside_the_folder_stops_the_gate(self) -> None:
        inside = self.repo / "deny.txt"
        inside.write_text(f"{SYNCED_WORD}\n", encoding="utf-8")
        res = self.run_gate(inside)
        self.assertNotEqual(res.returncode, 0)
        self.assertNotIn("excused", res.stdout)


if __name__ == "__main__":
    unittest.main()
