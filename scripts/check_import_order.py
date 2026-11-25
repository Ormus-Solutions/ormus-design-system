#!/usr/bin/env python3
"""Check that an entry CSS or HTML file loads the Ormus files in order.

The order is tokens.css, then fusion.css, then base.css (each optional after
tokens, but tokens.css is required once fusion.css or base.css is used). A file
named only in a comment does not count. Both `@import "x"`, `@import url(x)`,
`<link href="x">` and a bundler `@import "@ormus/design-system/x"` are seen.

Usage: python3 scripts/check_import_order.py ENTRY_FILE
Prints ok, or what is wrong, and exits 1 on a problem.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ORDER = ("tokens.css", "fusion.css", "base.css")


def check_text(text: str) -> list[str]:
    stripped = re.sub(r"/\*.*?\*/|<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    stripped = re.sub(r"(?m)^\s*//.*$", "", stripped)
    at: dict[str, tuple[int, int]] = {}
    for number, line in enumerate(stripped.splitlines(), 1):
        for name in ORDER:
            m = re.search(rf"(?<![\w.-]){re.escape(name)}(?![\w-]|\.\w)", line)
            if m and name not in at:
                at[name] = (number, m.start() + 1)
    problems: list[str] = []
    if "tokens.css" not in at:
        problems.append("tokens.css is not loaded (it must come first)")
    present = [(n, at[n]) for n in ORDER if n in at]
    for (a, la), (b, lb) in zip(present, present[1:]):
        if la >= lb:
            problems.append(f"{a} (line {la[0]}, column {la[1]}) must load before {b} "
                            f"(line {lb[0]}, column {lb[1]})")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not Path(argv[0]).is_file():
        print(__doc__, file=sys.stderr)
        return 2
    problems = check_text(Path(argv[0]).read_text(encoding="utf-8"))
    for p in problems:
        print(f"import order: {p}")
    if not problems:
        print("import order: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
