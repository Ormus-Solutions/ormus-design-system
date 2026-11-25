"""What this repo adds on top of the synced files must stay in step with them."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_html  # noqa: E402
import check_import_order  # noqa: E402
import find_colors  # noqa: E402
import contrast  # noqa: E402

CSS = (ROOT / "tokens.css").read_text(encoding="utf-8")
TOKENS: dict[str, Any] = json.loads((ROOT / "tokens.json").read_text(encoding="utf-8"))

COLOR_VARS = {
    "midnight": "--ormus-midnight", "deep": "--ormus-deep", "gold": "--ormus-gold",
    "goldBright": "--ormus-gold-bright", "ink": "--ormus-ink", "inkMuted": "--ormus-ink-muted",
    "dim": "--ormus-dim", "hairline": "--ormus-hairline", "onGold": "--ormus-on-gold",
    "codeBg": "--ormus-code-bg", "danger": "--ormus-danger",
}


def css_var(name: str) -> str:
    m = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", CSS)
    assert m, f"{name} missing from tokens.css"
    return m.group(1).strip()


class Tokens(unittest.TestCase):
    def test_json_colors_match_css(self) -> None:
        for key, var in COLOR_VARS.items():
            self.assertEqual(TOKENS["color"][key], css_var(var), key)
        for key, value in TOKENS["accents"].items():
            if not key.startswith("$"):
                self.assertEqual(value, css_var(f"--ormus-accent-{key}"), key)

    def test_python_snippet_from_the_readme(self) -> None:
        with open(ROOT / "tokens.json", encoding="utf-8") as f:
            tokens = json.load(f)
        self.assertEqual(tokens["color"]["gold"], "#d29e3d")

    def test_contrast_promises_hold(self) -> None:
        pairs = contrast.all_pairs(TOKENS)
        for planet in contrast.planet_pairs(TOKENS).values():
            pairs += planet
        for label, fg, bg, minimum in pairs:
            self.assertGreaterEqual(contrast.ratio(fg, bg), minimum, label)


class Extras(unittest.TestCase):
    def test_base_css_type_scale_matches_tokens_json(self) -> None:
        base = (ROOT / "base.css").read_text(encoding="utf-8")
        for tag in ("h1", "h2", "h3"):
            m = re.search(rf"\.surface-firm {tag} \{{([^}}]*)\}}", base)
            self.assertIsNotNone(m, tag)
            body = m.group(1) if m else ""
            self.assertIn(f"font-size: {TOKENS['typeScale'][tag]['size']}", body)
            self.assertIn(f"line-height: {TOKENS['typeScale'][tag]['lineHeight']}", body)

    def test_base_and_demo_css_write_no_color(self) -> None:
        for name in ("base.css", "examples/demo.css", "tailwind/preset.cjs", "tailwind/theme.css"):
            text = re.sub(r"/\*.*?\*/", "", (ROOT / name).read_text(encoding="utf-8"), flags=re.S)
            self.assertEqual(check_html.color_problems(text), [], f"{name} writes a color")

    def expected_tailwind(self) -> dict[str, str]:
        """Every Tailwind name this repo promises, and the one variable it must hold."""
        want = {f"color:ormus-{k}": f"--ormus-{k}" for k in (
            "midnight", "deep", "gold", "gold-bright", "ink", "ink-muted", "dim",
            "hairline", "on-gold", "code-bg", "danger")}
        for k in TOKENS["accents"]:
            if not k.startswith("$"):
                want[f"color:ormus-accent-{k}"] = f"--ormus-accent-{k}"
        for k in ("display", "sans", "mono"):
            want[f"font:{k}"] = f"--ormus-font-{k}"
        for k in ("", "-container", "-pill"):
            want[f"radius:ormus{k}"] = f"--ormus-radius{k}"
        want["ease:ormus-reveal"] = "--ormus-ease-reveal"
        return want

    @staticmethod
    def theme_map(text: str) -> dict[str, str]:
        """The Tailwind v4 theme names and the variable each holds, comments ignored."""
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        got: dict[str, str] = {}
        for name, var in re.findall(r"--((?:color|font|radius|ease)-[a-z-]+):\s*var\((--ormus-[a-z-]+)\);", text):
            kind, _, rest = name.partition("-")
            got[f"{kind}:{rest}"] = var
        return got

    def test_theme_map_ignores_commented_out_mappings(self) -> None:
        self.assertEqual(self.theme_map("/* --color-ormus-ink: var(--ormus-ink); */"), {})
        self.assertEqual(self.theme_map("--font-sans: var(--ormus-font-sans);"),
                         {"font:sans": "--ormus-font-sans"})

    def test_tailwind_v4_theme_maps_each_name_to_its_own_variable(self) -> None:
        text = (ROOT / "tailwind" / "theme.css").read_text(encoding="utf-8")
        got = self.theme_map(text)
        self.assertEqual(got, self.expected_tailwind())
        for var in got.values():
            self.assertRegex(CSS, rf"{re.escape(var)}\s*:", f"theme.css uses undefined {var}")

    def test_tailwind_v3_preset_maps_each_name_to_its_own_variable(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        dump = (
            "const e=require('./tailwind/preset.cjs').theme.extend;const o={};"
            "for(const[k,v]of Object.entries(e.colors.ormus))o['color:ormus-'+k]=v;"
            "for(const[k,v]of Object.entries(e.fontFamily))o['font:'+k]=v[0];"
            "for(const[k,v]of Object.entries(e.borderRadius))o['radius:'+k]=v;"
            "for(const[k,v]of Object.entries(e.transitionTimingFunction))o['ease:'+k]=v;"
            "console.log(JSON.stringify(o))"
        )
        out = subprocess.run([node, "-e", dump], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        got = {k: re.fullmatch(r"var\((--ormus-[a-z-]+)\)", v).group(1)  # type: ignore[union-attr]
               for k, v in json.loads(out).items()}
        self.assertEqual(got, self.expected_tailwind())
        for var in got.values():
            self.assertRegex(CSS, rf"{re.escape(var)}\s*:", f"preset uses undefined {var}")

    def test_tailwind_preset_loads(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        out = subprocess.run(
            [node, "-e", "const p=require('./tailwind/preset.cjs');"
             "console.log(p.theme.extend.colors.ormus.gold)"],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(out, "var(--ormus-gold)")

    def test_demo_swatches_show_the_real_values(self) -> None:
        html = (ROOT / "examples" / "index.html").read_text(encoding="utf-8")
        pairs = re.findall(r'data-token="(--ormus-[a-z-]+)">([^<]+)<', html)
        self.assertGreaterEqual(len(pairs), 17)
        for var, shown in pairs:
            self.assertEqual(shown, css_var(var), var)

    def test_demo_page_is_clean(self) -> None:
        self.assertEqual(check_html.check(ROOT / "examples" / "index.html"), [])

    def test_color_check_catches_every_way_to_write_a_color(self) -> None:
        bad = ["a{color:#FFF}", "a{color:RGB(1,2,3)}", "a{background:Red}",
               "a{border:1px solid white}", "a{box-shadow:0 0 1px Gold}", "a{color:HSL(1 2% 3%)}",
               "a{stop-color:red}", "a{flood-color:blue}", "a{scrollbar-color:red blue}",
               "a{text-emphasis-color:red}", "a{-webkit-text-stroke:1px red}",
               "a{filter:drop-shadow(0 0 2px red)}", ":root{--x:red}", "a{color:var(--ormus-ink, red)}",
               "a{color:oklch(1 0 0)}"]
        for css in bad:
            self.assertTrue(check_html.color_problems(css), css)
        for css in ["a{color:var(--ormus-gold)}", "a{background:transparent}",
                    "a{background:url(red.png)}", "a{fill:url(#abc123)}", ":root{--x:var(--ormus-ink)}",
                    "a{border:1px solid var(--ormus-hairline)}", ".red-box{margin:0}"]:
            self.assertEqual(check_html.color_problems(css), [], css)

    def test_demo_check_catches_a_color_in_a_style_attribute(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "p.html"
            page.write_text(
                '<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width"><title>t</title></head>'
                '<body><h1 style="color: RED">x</h1></body></html>', encoding="utf-8")
            self.assertTrue(any("style attribute" in p for p in check_html.check(page)))

    def test_demo_check_catches_presentation_attributes(self) -> None:
        import tempfile
        head = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width"><title>t</title>%s</head>')
        cases = ['<svg fill="red"></svg>', '<table bgcolor="#fff"></table>',
                 '<svg><path stroke="gold"/></svg>']
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "p.html"
            for body in cases:
                page.write_text(head % "" + f"<body><h1>x</h1>{body}</body></html>", encoding="utf-8")
                self.assertTrue(check_html.check(page), body)
            page.write_text(head % '<meta name="theme-color" content="#000">'
                            + "<body><h1>x</h1></body></html>", encoding="utf-8")
            self.assertTrue(check_html.check(page), "theme-color")
            page.write_text(head % "" + '<body><h1>x</h1><svg fill="currentColor"></svg></body></html>',
                            encoding="utf-8")
            self.assertEqual(check_html.check(page), [])

    def test_placeholder_color_is_exactly_ink_muted(self) -> None:
        base = (ROOT / "base.css").read_text(encoding="utf-8")
        m = re.search(r"\.ormus-field::placeholder\s*\{([^}]*)\}", base)
        self.assertIsNotNone(m)
        block = m.group(1) if m else ""
        self.assertEqual(re.findall(r"color:\s*([^;]+);", block), ["var(--ormus-ink-muted)"])
        # Firefox dims a placeholder by default; the rule must set opacity to exactly 1.
        self.assertEqual(re.findall(r"opacity:\s*([^;]+);", block), ["1"])

    def test_import_order_script(self) -> None:
        good = '@import "a/tokens.css";\n@import url("a/fusion.css");\n@import "a/base.css";\n'
        self.assertEqual(check_import_order.check_text(good), [])
        self.assertTrue(check_import_order.check_text('@import "a/fusion.css";\n@import "a/tokens.css";\n'))
        self.assertTrue(check_import_order.check_text('@import "a/fusion.css";\n'))
        self.assertTrue(check_import_order.check_text('/* tokens.css */\n@import "a/fusion.css";\n'))
        html = '<link rel="stylesheet" href="v/tokens.css">\n<link rel="stylesheet" href="v/fusion.css">\n'
        self.assertEqual(check_import_order.check_text(html), [])

    def test_import_order_by_column_and_no_source_map(self) -> None:
        one_line = '<link href="v/tokens.css"><link href="v/fusion.css">'
        self.assertEqual(check_import_order.check_text(one_line), [])
        self.assertTrue(check_import_order.check_text('<link href="v/fusion.css"><link href="v/tokens.css">'))
        self.assertTrue(check_import_order.check_text('<link href="v/tokens.css.map">'))
        self.assertTrue(check_import_order.check_text('@import "v/tokens.css.map";\n@import "v/fusion.css";'))

    def test_find_colors_anchors_svg_json_and_attributes(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.html").write_text('<a href="#abc123">x</a>\n<a xlink:href=\'#def456\'>y</a>\n',
                                         encoding="utf-8")
            self.assertEqual(find_colors.scan(root), [])
            (root / "b.svg").write_text('<svg><path fill="#fff"/><path stroke="Gold"/>'
                                        '<path fill="currentColor"/><path fill="url(#g1)"/></svg>',
                                        encoding="utf-8")
            self.assertEqual(len(find_colors.scan(root)), 2)
            (root / "c.json").write_text('{"c": "color: #abcdef"}', encoding="utf-8")
            (root / "d.pcss").write_text("a{color:red}", encoding="utf-8")
            (root / "e.styl").write_text("a\n  color: rgb(1,2,3)\n", encoding="utf-8")
            files = {h.split(":")[0] for h in find_colors.scan(root)}
            self.assertEqual(files, {"b.svg", "c.json", "d.pcss", "e.styl"})

    def test_find_colors_counts_every_kind(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.css").write_text(
                "a{color:#fff}\nb{color:hsl(1 2% 3%)}\nc{background:Red}\nd{color:oklch(1 0 0)}\n"
                "e{color:var(--ormus-ink)}\nf{background:url(red.png)}\n/*\ng{color:red}\n*/\n",
                encoding="utf-8")
            (root / "vendor").mkdir()
            (root / "vendor" / "x.css").write_text("a{color:red}", encoding="utf-8")
            self.assertEqual(len(find_colors.scan(root)), 4)

    def test_demo_has_one_primary_button(self) -> None:
        html = (ROOT / "examples" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("fusion-btn--primary"), 1)

    def test_dim_text_is_only_24px_and_up_in_own_css(self) -> None:
        """The style guide promises --ormus-dim only for text of 24px and up."""
        for name in ("base.css", "examples/demo.css"):
            text = re.sub(r"/\*.*?\*/", "", (ROOT / name).read_text(encoding="utf-8"), flags=re.S)
            for sel, body in re.findall(r"([^{}]*)\{([^}]*)\}", text):
                if re.search(r"(?<![-\w])color:\s*var\(--ormus-dim\)", body):
                    size = re.search(r"font-size:\s*([\d.]+)rem", body)
                    self.assertTrue(size and float(size.group(1)) >= 1.5,
                                    f"{name}: {sel.strip()} sets dim text under 24px")

    def test_no_bold_serif_in_own_css(self) -> None:
        for name in ("base.css", "examples/demo.css"):
            for block in re.findall(r"([^{}]*)\{([^}]*)\}", (ROOT / name).read_text(encoding="utf-8")):
                sel, body = block
                if "var(--ormus-font-display)" in body:
                    self.assertNotRegex(body, r"font-weight:\s*(?:[6-9]00|bold)", sel)


if __name__ == "__main__":
    unittest.main()
