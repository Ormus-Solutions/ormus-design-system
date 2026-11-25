"""The searches in PLAYBOOK.md must be able to fail: run them on planted input."""
from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def step_block(number: int) -> str:
    text = (ROOT / "PLAYBOOK.md").read_text(encoding="utf-8")
    m = re.search(rf"### {number}\. .*?(?=\n### |\n## )", text, re.S)
    assert m
    return m.group(0)


class Playbook(unittest.TestCase):
    def test_step_15_search_finds_every_declaration_without_the_curve(self) -> None:
        block = step_block(15)
        grep_line = next(x for x in block.splitlines()
                         if x.startswith('grep -rn -E "(^|[^-[:alnum:]_])(transition|animation)'))
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            (src / "a.css").write_text(
                ".a{transition:all .3s}\n"
                ".b{\n  transition:\n    opacity 1s\n}\n"
                ".c{transition: none}\n"
                ".d{transition: opacity 1s var(--ormus-ease-reveal);}\n"
                ".e{transition-property: opacity}\n"
                ".f{animation: spin 1s linear}\n", encoding="utf-8")
            cmd = 'EXC="--exclude-dir=node_modules --exclude-dir=.git --exclude-dir=vendor"\n' + \
                  grep_line.replace("PROJECT/SRC", str(src))
            out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True).stdout
            hits = sorted(int(x.split(":")[1]) for x in out.strip().splitlines())
            self.assertEqual(hits, [1, 3, 9], out)  # .a, the .b declaration line, .f


if __name__ == "__main__":
    unittest.main()
