# Ormus design system

The code and CSS are MIT. The Ormus name and marks are not: see [BRAND.md](BRAND.md).

The Ormus colors, type, shape, motion and a small set of components, packaged
so an OS Crew project can look like Ormus work without copying values by hand.

## What it is

A **design system** in the "tokens plus a thin component layer" shape. The
tokens are named values (colors, fonts, radii, the easing curve) written once
as CSS custom properties (`--ormus-*`) and once as JSON. Every other file
reads those names and never repeats a value, so changing the brand means
changing one file. The values come from
ormus-brand, the source of
truth for the Ormus brand. That repo is internal to Ormus Solutions (private),
so most readers cannot open it. This repo copies the values at a pinned commit
(recorded in `SOURCE.lock`) and a test fails if a copy drifts. If this repo and
ormus-brand ever disagree, ormus-brand wins; outside the org, ask Ormus.

The idea: digital systems and tools, cast in liquid gold. A midnight lacquer
surface, gold as the one raised voice, serif display type over engineering
mono. Boutique, adult, quiet.

## Why it exists

A crew member asked for the Ormus colors. Ormus: "we should build the ormus
design system in a repo in ormus solutions". This is that repo.

## Who it is for

Crew members who build a web project about Ormus work and want it to match:
a tool, a demo, a page. Also their coding agents: [PLAYBOOK.md](PLAYBOOK.md)
applies the system to an existing project step by step. Skip it if the project
is for another company; that project takes its own brand (see [BRAND.md](BRAND.md)).

## Requirements

| Tool | Version | Check |
|---|---|---|
| a browser | any current one | |
| Python (only to run `check.sh`) | 3.11 or newer | `python3 --version` |
| git | any | `git --version` |
| node (optional, one test uses it) | 18 or newer | `node --version` |
| shellcheck (optional) | any | `shellcheck --version` |

Using the CSS needs none of these.

## Quick start

**Hand it to your agent.** Paste this into Claude Code, Codex or Grok, in your project:

```text
Read PLAYBOOK.md in the ormus-design-system folder (DS) and follow it, in
order, to apply the Ormus design system to this project (PROJECT). Run each
"Verify:" command and stop at the first result that does not match "Expected:".
Ask me before you replace a color that has no exact token.
```

**Do it by hand.** Copy `tokens.css`, `fusion.css`, `base.css` and `assets/`
into your project, load the fonts, link the files in that order, and put
`class="surface-firm"` on the page shell:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="vendor/ormus/tokens.css">
<link rel="stylesheet" href="vendor/ormus/fusion.css">  <!-- keep assets/ next to it -->
<link rel="stylesheet" href="vendor/ormus/base.css">    <!-- optional starter layer -->
<body class="surface-firm">
  <span class="mono-label">section</span>
  <h1>Plain confident sentences.</h1>
  <button class="fusion-btn fusion-btn--primary">Start a conversation</button>
</body>
```

Copy the files at build time and do not hotlink them: nothing then changes
under your app at runtime.

## Preview

`examples/index.html` shows the palette, type, buttons, cards, labels and
states. Open it in a browser (it links Google Fonts, so it needs a network for
the fonts; without one it falls back to Georgia and system fonts). This is the
text version of what it holds:

```text
/ PALETTE   Colors            11 swatches, then 6 identity accents
/ TYPE      Three families    h1 300, h2 400, h3 400, body, label
/ BUTTONS   One loud, one quiet   gold primary, hairline ghost, disabled, link
/ CARDS     Gold top hairline     3 cards that cut in on scroll
/ LABELS    Micro-labels, chips and shape   8px, 14px, pill
/ STATES    Fields and intensity  focus, error, locked; gold ink muted dim
```

## The palette

| Name | Token | Value | Role |
|---|---|---|---|
| Midnight | `--ormus-midnight` | `#14213d` | surface background |
| Deep | `--ormus-deep` | `#0e1830` | page ground, opaque panels, canvas |
| Gold | `--ormus-gold` | `#d29e3d` | the primary accent, the one raised voice |
| Gold bright | `--ormus-gold-bright` | `#e0b258` | pointer-over and active gold |
| Ink | `--ormus-ink` | `#eceae3` | primary text |
| Ink muted | `--ormus-ink-muted` | `#a5b0c4` | secondary text |
| Dim | `--ormus-dim` | `#6d7891` | quietest text (24px and up), fourth graph class |
| Hairline | `--ormus-hairline` | `rgba(236,234,227,0.12)` | borders |
| On gold | `--ormus-on-gold` | `#1a1407` | text on gold fills |
| Code | `--ormus-code-bg` | `#0b1226` | code panels |
| Danger | `--ormus-danger` | `#d44f4f` | errors only |

Six identity accents mark what a thing is (a tile, an author, a group):
rose `#e0849a`, teal `#4fbcae`, leaf `#86c272`, ember `#e8955f`, sky `#78a6ee`,
iris `#ad92e6` (`--ormus-accent-*`). They are never the only carrier of a state.

The semantic roles most apps bind to: `--ormus-bg`, `--ormus-bg-deep`,
`--ormus-bg-elevated`, `--ormus-bg-muted`, `--ormus-fg`, `--ormus-accent`,
`--ormus-border`. `tokens.json` also holds seven dark planet themes under
`planets`, for an app that lets a person pick a theme (each has every key of
`color`). Sites and anything Ormus publishes use the default colors.

Contrast, measured by `scripts/contrast.py` (WCAG 2.x, run it to see all 156 pairs):

| Pair | Ratio | Minimum |
|---|---|---|
| ink on deep | 14.63:1 | 4.5 |
| ink muted on deep | 8.06:1 | 4.5 |
| gold on deep | 7.30:1 | 4.5 |
| gold bright on deep | 8.96:1 | 4.5 |
| on gold on gold (primary button) | 7.58:1 | 4.5 |
| placeholder (ink muted) on a text field over deep | 7.31:1 | 4.5 |
| placeholder (ink muted) on a text field over midnight | 6.54:1 | 4.5 |
| dim on deep | 3.98:1 | 3.0 (24px and up only) |
| dim on midnight | 3.61:1 | 3.0 (24px and up only) |
| danger on deep | 4.22:1 | 3.0 (large text and icons; under 4.5 at body size) |
| danger on midnight | 3.83:1 | 3.0 (large text and icons; under 4.5 at body size) |

Danger text at body size does not reach 4.5:1. Set an error line in danger
only with words that say it is an error (the demo does), and keep the message
short.

## Type

- Display: **Cormorant Garamond**, weight 300 for h1 (`-0.01em` tracking) and 400 for h2 and h3. Never bold the serif.
- Body: **Inter**, 1rem on a 1.8 line.
- Micro-labels and metadata: **JetBrains Mono**, 0.72rem, `0.08em` tracking, uppercase, prefixed with `/ ` (the class `.mono-label` does it).
- Bump serif headings one step over a sans equivalent; Cormorant runs optically small.

Load Cormorant 300 and 400, Inter and JetBrains Mono yourself; the tokens only
name them. Without the display font, headings fall back to Georgia.

## Shape

Soft corners, no hard ones: `--ormus-radius` 8px for keys, buttons and fields;
`--ormus-radius-container` 14px for cards, groups and bubbles;
`--ormus-radius-pill` 999px for chips and status pills. Cards carry a gold top
hairline at 70% and lift 2px when pointed at (`.fusion-card`).

## Motion

One curve: `cubic-bezier(0.16, 1, 0.3, 1)` (`--ormus-ease-reveal`). Reveals
are film-frame cut-ins (`.fusion-reveal`, then `.is-revealed` from an
IntersectionObserver; `examples/demo.js` shows it). The hidden start state
applies only when scripting is on, so no-JS clients see the content.
Everything honors `prefers-reduced-motion`.

## The rules

1. **One raised voice: gold.** One gold element per view: one primary button, one accent. State and class read through intensity (gold, ink, muted, dim), and a state shown in color also keeps a mark or words.
2. **No light mode.** Midnight is pinned. Print is the one exception: `fusion.css` turns it to white paper, gold `#8a6519`, near-black ink.
3. **Never bold Cormorant.** Weight 300 or 400.
4. **Never write a color or a font inside an app.** Use `--ormus-*` (or `tokens.json` where CSS variables cannot reach, such as canvas and WebGL). Map your framework's theme onto the variables.
5. **Danger is for errors only.** Identity accents never stand for a planet or a state alone.
6. **Panels over video are solid** (`--ormus-deep` at about 90%), never `backdrop-blur`.
7. **Voice:** plain confident sentences, lead with the answer, no em dashes, no emojis in product UI, quiet calls to action ("Start a conversation").
8. **Marks:** scale the gold mark down only. The swan is never line art. See [BRAND.md](BRAND.md).

## Use it

### Plain HTML

As in the quick start. `fusion.css` finds the texture at `./assets/midnight-lacquer.jpg`, so keep `assets/` next to it.

### With a bundler (Vite, Next.js, webpack)

Vendor the files (copy them at build time, recommended). People with read access to this private repo (the org) may instead install it as a git dependency:

```sh
npm install github:Ormus-Solutions/ormus-design-system
```

```css
/* global stylesheet, first lines */
@import "@ormus/design-system/tokens.css";
@import "@ormus/design-system/fusion.css";
@import "@ormus/design-system/base.css";
```

Canvas, WebGL and charts read `tokens.json`:

```js
import tokens from "@ormus/design-system/tokens.json" with { type: "json" };
ctx.fillStyle = tokens.canvas.background;
```

Python, slides and other tools read the same file:

```python
import json
tokens = json.load(open("tokens.json"))
gold = tokens["color"]["gold"]   # "#d29e3d"
```

`tokens.json` is nested and complete (color, canvas, print, planets, font,
typeScale, motion, radius, accents), so there is no separate flat export.

### With Tailwind

Load `tokens.css` first; both files map Tailwind names to the variables, so no hex is repeated.

Tailwind v3, `tailwind.config.js`:

```js
module.exports = {
  presets: [require("@ormus/design-system/tailwind/preset.cjs")],
  content: ["./src/index.html", "./src/app.js"],
};
```

Tailwind v4, your main CSS:

```css
@import "tailwindcss";
@import "@ormus/design-system/tokens.css";
@import "@ormus/design-system/tailwind/theme.css";
```

You get `bg-ormus-gold`, `text-ormus-ink`, `border-ormus-hairline`, the identity
accents as `bg-ormus-accent-teal` and so on (`ormus-accent-*`, so they never
read as the legacy `--ormus-teal` green),
`font-display`, `rounded-ormus`, `rounded-ormus-container`,
`rounded-ormus-pill` and `ease-ormus-reveal`. Tailwind v3 cannot put an
opacity modifier on a `var()` color (`bg-ormus-gold/50`), so write a CSS rule
for a translucent color. These two files are checked structurally and the
preset is loaded by node in the tests; they are not compiled by Tailwind in
this repo's gate.

## Files

| Path | What it holds |
|---|---|
| `tokens.css`, `tokens.json` | the tokens, copied from ormus-brand |
| `fusion.css` | the component layer: surface, cards, buttons, labels, reveals, print. Copied from ormus-brand |
| `base.css` | starter layer added by this repo (not from ormus-brand): body type, heading sizes, focus ring, disabled state, `.ormus-field`, `.ormus-chip`, `.ormus-error` |
| `tailwind/` | `preset.cjs` (v3) and `theme.css` (v4) |
| `assets/midnight-lacquer.jpg`, `assets/marks/` | the texture; the flat gold mark at 1024, 512 and 128 px; the kintsugi mark (png) |
| `examples/` | the demo page and its small layout CSS and script |
| `SOURCE.lock` | the ormus-brand commit the copies came from, and a sha256 of each |
| `scripts/sync.sh` | copies the files again from an ormus-brand checkout |
| `scripts/contrast.py`, `scripts/check_html.py` | the contrast measure and the demo page check |
| `scripts/scrub.sh`, `scripts/scrub_gate.sh`, `scripts/scrub_gate.py` | the scrub copied unchanged from playbook-packaging, and the way `check.sh` runs it |
| `scripts/find_colors.py`, `scripts/check_import_order.py` | helpers the playbook calls: list written-out colors, check the CSS load order |
| `tests/` | the drift test and the checks on what this repo adds |
| `check.sh` | the one gate |
| `PLAYBOOK.md`, `BRAND.md`, `LICENSE`, `CHANGELOG.md` | the agent steps, the name and marks, MIT, the history |

Left out on purpose: the avatars, pantry, footage, 3D models, the liquid-gold
mark and the sigils (art for Ormus's own surfaces, and large), the story
document, and the brand book builder.

## Updating from ormus-brand

ormus-brand is internal to Ormus Solutions, so this section is for people with
access to it. Everyone else: the copies are guarded by the sha256 sums in
`SOURCE.lock`, which `check.sh` verifies on every run, and a brand change
reaches you as a new release of this repo. To ask for one, tell Ormus.

The brand changes in ormus-brand first. To take a change (org members):

```sh
git -C ../ormus-brand fetch
bash scripts/sync.sh ../ormus-brand origin/main   # copies, rewrites SOURCE.lock
bash check.sh
```

`sync.sh` reads the files from the commit with `git show`, so unfinished edits
in the checkout never come along. Never edit a synced file here: the drift
test fails, and the change would be lost on the next sync. To add or change a
brand value, open a PR in ormus-brand.

`check.sh` runs the drift test (always against the checksums in `SOURCE.lock`;
and against the recorded commit too when `ormus-brand` sits next to this repo
or `ORMUS_BRAND_DIR` points at it, in which case a checkout that lacks the
commit is a failure), the contrast measure, the demo page check, shellcheck and
the scrub (`scripts/scrub_gate.sh`). Run `bash check.sh` before every commit.

## What the scrub does not see

`scripts/scrub.sh` reads text files. A word planted inside a picture or any
other binary file is not found: look at each image yourself (the scrub says
how many it skipped). Deny-list words in the three synced brand files are
excused by checksum only (`scripts/scrub_gate.py`): the bytes must hash to the
sha256 in `SOURCE.lock`, and `SOURCE.lock` must keep its strict line format.
When an ormus-brand checkout is at hand (`ORMUS_BRAND_DIR`, or a sibling
folder), the gate also checks every lock against the brand's own files at the
locked commit; otherwise it prints that the source was not verified.

## Credits and license

Built for the OS Crew by Ormus Solutions. Code and CSS: MIT ([LICENSE](LICENSE)).
The Ormus name and marks: [BRAND.md](BRAND.md). Fonts: Google Fonts, SIL Open
Font License 1.1, loaded from Google and not bundled.
