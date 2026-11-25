#!/usr/bin/env python3
"""List the colors a project writes out, line by line, with the demo page's rules.

Counts hex, rgb(), hsl(), oklch() and the like in any case, and named colors in
color-bearing declarations, custom properties and var() fallbacks. url() file
names are not colors. Skips node_modules, .git, vendor, dist and build folders.

Usage: python3 scripts/find_colors.py PROJECT_FOLDER
Prints `path:line: what` for each hit and ends with `colors: N`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_html  # noqa: E402

SUFFIXES = {".css", ".scss", ".sass", ".less", ".html", ".htm", ".tsx", ".jsx", ".ts", ".js",
            ".vue", ".svelte", ".astro", ".mdx"}
SKIP = {"node_modules", ".git", "vendor", "dist", "build", ".next", ".nuxt", ".svelte-kit"}


def scan(root: Path) -> list[str]:
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SUFFIXES or SKIP & set(path.relative_to(root).parts):
            continue
        in_comment = False
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            # a line inside a /* ... */ block is not code; the line scan keeps it simple
            if in_comment:
                in_comment = "*/" not in line
                continue
            if line.lstrip().startswith("/*") and "*/" not in line:
                in_comment = True
                continue
            for problem in check_html.color_problems(line):
                hits.append(f"{path.relative_to(root)}:{number}: {problem}")
    return hits


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not Path(argv[0]).is_dir():
        print(__doc__, file=sys.stderr)
        return 2
    hits = scan(Path(argv[0]))
    for hit in hits:
        print(hit)
    print(f"colors: {len(hits)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
