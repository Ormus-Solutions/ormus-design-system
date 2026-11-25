#!/usr/bin/env python3
"""Check the text and background pairs the Ormus style guide promises.

Reads tokens.json, computes the WCAG 2.x contrast ratio of each pair, prints
the measured ratio, and exits 1 when a pair is under the minimum.

Minimums: 4.5 for normal text, 3.0 for large text (24px and up), icons and
graphical marks. The style guide promises dim only at 24px and up.

Usage: python3 scripts/contrast.py [--quiet]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

Pair = tuple[str, str, str, float]  # label, foreground, background, minimum


def parse_hex(value: str) -> tuple[float, float, float]:
    """'#rrggbb' as three 0..255 floats."""
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def blend(top: tuple[float, float, float], alpha: float,
          under: tuple[float, float, float]) -> str:
    """A translucent color laid over an opaque one, as '#rrggbb'."""
    mixed = [round(t * alpha + u * (1 - alpha)) for t, u in zip(top, under)]
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def luminance(value: str) -> float:
    channels = []
    for c in parse_hex(value):
        c /= 255
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def ratio(fg: str, bg: str) -> float:
    a, b = luminance(fg) + 0.05, luminance(bg) + 0.05
    return max(a, b) / min(a, b)


def theme_pairs(c: dict[str, str], name: str) -> list[Pair]:
    """The promises of one dark theme: the first is the brand, the rest are options."""
    pairs: list[Pair] = []
    for ground in ("deep", "midnight", "codeBg"):
        pairs += [
            (f"{name}: ink on {ground}", c["ink"], c[ground], 4.5),
            (f"{name}: inkMuted on {ground}", c["inkMuted"], c[ground], 4.5),
            (f"{name}: gold on {ground}", c["gold"], c[ground], 4.5),
            (f"{name}: dim on {ground} (24px and up)", c["dim"], c[ground], 3.0),
        ]
    pairs += [
        (f"{name}: goldBright on deep", c["goldBright"], c["deep"], 4.5),
        (f"{name}: onGold on gold (primary button)", c["onGold"], c["gold"], 4.5),
        (f"{name}: danger on deep (large text, icons)", c["danger"], c["deep"], 3.0),
        (f"{name}: danger on midnight (large text, icons)", c["danger"], c["midnight"], 3.0),
    ]
    # The muted surface layer (--ormus-bg-muted, white at 4%) over midnight.
    lifted = blend((255, 255, 255), 0.04, parse_hex(c["midnight"]))
    pairs += [
        (f"{name}: ink on midnight + muted layer", c["ink"], lifted, 4.5),
        (f"{name}: inkMuted on midnight + muted layer", c["inkMuted"], lifted, 4.5),
    ]
    # A text field (--ormus-bg-muted, white at 4%) on either page ground: its
    # placeholder is body-size text, so it reads at 4.5:1.
    for ground in ("deep", "midnight"):
        field = blend((255, 255, 255), 0.04, parse_hex(c[ground]))
        pairs.append((f"{name}: placeholder (inkMuted) on field over {ground}",
                      c["inkMuted"], field, 4.5))
    return pairs


def all_pairs(tokens: dict[str, Any]) -> list[Pair]:
    color: dict[str, str] = tokens["color"]
    pairs = theme_pairs(color, "brand")
    for key, accent in tokens["accents"].items():
        if key.startswith("$"):
            continue
        pairs += [
            (f"accent {key} on midnight", accent, color["midnight"], 3.0),
            (f"deep letter on accent {key}", color["deep"], accent, 4.5),
        ]
    p = tokens["print"]
    pairs += [
        ("print: ink on paper", p["ink"], p["paper"], 4.5),
        ("print: inkMuted on paper", p["inkMuted"], p["paper"], 4.5),
        ("print: gold on paper", p["gold"], p["paper"], 4.5),
        ("print: onGold on gold (primary button)", p["onGold"], p["gold"], 4.5),
    ]
    return pairs


def planet_pairs(tokens: dict[str, Any]) -> dict[str, list[Pair]]:
    """The optional dark themes. The first planet equals the brand colors, so it
    is skipped here (all_pairs already covers it)."""
    planets = [(k, v) for k, v in tokens["planets"].items() if not k.startswith("$")]
    return {name: theme_pairs(palette, name) for name, palette in planets[1:]}


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    tokens = json.loads((ROOT / "tokens.json").read_text(encoding="utf-8"))
    failures = 0

    pairs = all_pairs(tokens)
    if not quiet:
        print(f"{'pair':<48} {'ratio':>7}  {'min':>4}")
    for label, fg, bg, minimum in pairs:
        r = ratio(fg, bg)
        ok = r >= minimum
        failures += 0 if ok else 1
        if not quiet or not ok:
            print(f"{label:<48} {r:>6.2f}:1  {minimum:>4}  {'ok' if ok else 'FAIL'}")

    for name, plist in planet_pairs(tokens).items():
        bad = [(label, ratio(fg, bg), m) for label, fg, bg, m in plist if ratio(fg, bg) < m]
        low = min(ratio(fg, bg) / m for _, fg, bg, m in plist)
        failures += len(bad)
        for label, r, m in bad:
            print(f"{label:<48} {r:>6.2f}:1  {m:>4}  FAIL")
        if not quiet:
            print(f"planet {name}: {len(plist)} pairs, "
                  f"{'all ok' if not bad else f'{len(bad)} FAIL'} "
                  f"(tightest margin x{low:.2f} of its minimum)")

    total = len(pairs) + sum(len(v) for v in planet_pairs(tokens).values())
    print(f"contrast: {total - failures}/{total} pairs meet their minimum")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
