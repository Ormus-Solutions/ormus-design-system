#!/usr/bin/env python3
"""Check an HTML page of this repo: structure, local files, brand rules.

It is a small structural check built on the standard library (there is no
network and no extra tool to install). It looks for:
  - a doctype, <html lang>, charset, viewport and a <title>
  - one <h1>, an alt on every <img>, unique ids
  - tags that open and close in the right order
  - every local href and src (and every url() in a linked local .css) points at a file
  - the only outside address is Google Fonts
  - no color written in the page, in a style attribute, in a presentation
    attribute (fill, stroke, bgcolor, meta theme-color) or in its local CSS (hex,
    rgb() in any case, named colors, custom properties and var() fallbacks;
    colors come from the --ormus-* variables), and no em dash or emoji in
    visible copy

Usage: python3 scripts/check_html.py PAGE.html [...]
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "source", "track", "wbr"}
ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
COLOR_LITERAL = re.compile(r"#[0-9a-f]{3,8}\b|\b(?:rgb|hsl|hwb|lab|lch|oklab|oklch|color)a?\(", re.I)
NAMED_COLORS = frozenset("""
aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown
burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan
darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid
darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet
deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro
ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki
lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow
lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray
lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine
mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise
mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab
orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru
pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown
seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan
teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen
""".split())
COLOR_PROPS = re.compile(
    r"(?<![-\w])((?:background|border|outline|text-decoration|column-rule|text-emphasis)(?:-[a-z]+)*|"
    r"color|fill|stroke|box-shadow|text-shadow|caret-color|accent-color|scrollbar-color|"
    r"stop-color|flood-color|lighting-color|filter|backdrop-filter|"
    r"-webkit-text-(?:stroke|fill)(?:-color)?)\s*:\s*([^;}]+)", re.I)
CUSTOM_PROP = re.compile(r"(?<![\w-])(--[\w-]+)\s*:\s*([^;}]+)")
# HTML and SVG presentation attributes that carry a color in the markup.
COLOR_ATTRS = frozenset({"fill", "stroke", "color", "bgcolor", "text", "link", "vlink", "alink",
                         "stop-color", "flood-color", "lighting-color"})
NEUTRAL = frozenset({"", "none", "currentcolor", "inherit", "transparent", "initial", "unset"})


def _words(value: str) -> set[str]:
    """The words of a CSS value, with var(--x) removed but a var(--x, fallback) fallback kept."""
    value = re.sub(r"var\(\s*--[\w-]+\s*\)", "", value)
    value = re.sub(r"var\(\s*--[\w-]+\s*,", "(", value)
    return set(re.findall(r"[a-z]+", value.lower()))


def color_problems(css: str) -> list[str]:
    """Colors written out in CSS text or in a style attribute: hex, rgb(), hsl()
    and the like in any case, and named colors in a color-bearing declaration,
    a custom property or a var() fallback. url() contents are file names, not colors.
    var(--ormus-*) is the only way to name a color."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"url\([^)]*\)", "url()", css, flags=re.I)
    out: list[str] = []
    if COLOR_LITERAL.search(css):
        out.append("a color is written out; use a --ormus-* variable")
    values = [v for _, v in COLOR_PROPS.findall(css)] + [v for _, v in CUSTOM_PROP.findall(css)]
    named = sorted({w for v in values for w in _words(v)} & NAMED_COLORS)
    if named:
        out.append(f"named color {', '.join(named)} written out; use a --ormus-* variable")
    return out


class Page(HTMLParser):
    def __init__(self, base: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.problems: list[str] = []
        self.stack: list[str] = []
        self.ids: set[str] = set()
        self.h1 = 0
        self.title = ""
        self.in_title = False
        self.in_style = False
        self.in_script = False
        self.lang = False
        self.charset = False
        self.viewport = False
        self.text: list[str] = []
        self.css_files: list[Path] = []
        self.style_text: list[str] = []
        self.style_attrs: list[str] = []

    def problem(self, text: str) -> None:
        line, _ = self.getpos()
        self.problems.append(f"line {line}: {text}")

    def check_ref(self, value: str, what: str) -> Path | None:
        if value.startswith(("#", "mailto:", "data:")):
            return None
        url = urlparse(value)
        if url.scheme in ("http", "https") or value.startswith("//"):
            if url.hostname not in ALLOWED_HOSTS:
                self.problem(f"{what} points outside the repo: {url.hostname}")
            return None
        target = (self.base / url.path).resolve()
        if not target.is_file():
            self.problem(f"{what} does not exist: {value}")
            return None
        return target

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "html" and a.get("lang"):
            self.lang = True
        if tag == "meta":
            if "charset" in a:
                self.charset = True
            if a.get("name") == "viewport":
                self.viewport = True
        if tag == "h1":
            self.h1 += 1
        if tag == "img" and "alt" not in a:
            self.problem("<img> without alt")
        if "style" in a:
            self.style_attrs.append(a["style"])
        for attr in COLOR_ATTRS & a.keys():
            value = a[attr].strip().lower()
            if value not in NEUTRAL and not value.startswith("url("):
                self.problem(f"<{tag} {attr}> writes a color in markup; use CSS with a --ormus-* variable")
        if tag == "meta" and a.get("name") == "theme-color":
            self.problem("meta theme-color writes a color in markup")
        if "id" in a:
            if a["id"] in self.ids:
                self.problem(f"duplicate id {a['id']}")
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if key in a:
                target = self.check_ref(a[key], f"{tag} {key}")
                if target and target.suffix == ".css" and tag == "link":
                    self.css_files.append(target)
        if tag == "title":
            self.in_title = True
        if tag == "style":
            self.in_style = True
        if tag == "script":
            self.in_script = True
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID:
            return
        if tag == "title":
            self.in_title = False
        if tag == "style":
            self.in_style = False
        if tag == "script":
            self.in_script = False
        if not self.stack or self.stack[-1] != tag:
            self.problem(f"</{tag}> closes {self.stack[-1] if self.stack else 'nothing'}")
            if tag in self.stack:
                while self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data
        elif self.in_style:
            self.style_text.append(data)
        elif not self.in_script:
            self.text.append(data)


def css_problems(path: Path) -> list[str]:
    out: list[str] = []
    text = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
    out += [f"{path.name}: {p}" for p in color_problems(text)]
    for ref in re.findall(r"url\(['\"]?([^'\")]+)", text):
        if not ref.startswith(("data:", "#")) and not (path.parent / ref).is_file():
            out.append(f"{path.name}: url({ref}) does not exist")
    return out


def check(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    page = Page(path.parent)
    if not re.match(r"\s*<!doctype html>", raw, re.I):
        page.problems.append("no <!doctype html> at the top")
    page.feed(raw)
    page.close()
    if page.stack:
        page.problems.append(f"never closed: {', '.join(page.stack)}")
    if not page.lang:
        page.problems.append("<html> has no lang")
    if not page.charset:
        page.problems.append("no <meta charset>")
    if not page.viewport:
        page.problems.append("no viewport meta")
    if not page.title.strip():
        page.problems.append("no <title>")
    if page.h1 != 1:
        page.problems.append(f"expected one <h1>, found {page.h1}")
    for p in color_problems("\n".join(page.style_text)):
        page.problems.append(f"in <style>: {p}")
    for attr in page.style_attrs:
        for p in color_problems(attr):
            page.problems.append(f"in a style attribute: {p}")
    for css in page.css_files:
        # Only the page's own css is held to the rule: tokens.css defines the colors.
        if css.parent.name == "examples":
            page.problems += css_problems(css)
    visible = " ".join(page.text)
    if "—" in visible or "&mdash;" in raw:
        page.problems.append("em dash in visible copy (STYLE rule: no em dashes)")
    if EMOJI.search(visible):
        page.problems.append("emoji in visible copy (STYLE rule: none in product UI)")
    return page.problems


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    bad = 0
    for name in argv:
        problems = check(Path(name))
        for p in problems:
            print(f"html: {name}: {p}")
        bad += len(problems)
        if not problems:
            print(f"html: {name}: ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
