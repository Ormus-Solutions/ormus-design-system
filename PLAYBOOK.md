# Ormus design system: the playbook

This file is written for a coding agent (Claude Code, Codex, Grok) and is
readable by a person. Do the steps in order. Each step is one action, a
"Verify:" command and the result to expect. Stop at the first result that
does not match and report what you saw.

In the commands, replace these three words:

- `DS`: the folder of this repo (the clone of ormus-design-system).
- `PROJECT`: the root folder of the web project you are changing.
- `VENDOR`: where the Ormus files go inside PROJECT. Use `public/vendor/ormus`
  for a static site or any app that serves a public folder, and `vendor/ormus`
  when a bundler imports the CSS. Keep `assets/` inside it, next to `fusion.css`.
  The folder just above `ormus` must be named `vendor`, because the searches
  below skip folders by that name.
- `SRC`: the folder inside PROJECT that holds the app's own source (`src`, `app`,
  `pages`, or the folder with the HTML pages). It must not contain VENDOR.

Use absolute paths for DS and PROJECT (a relative DS breaks after a script
changes folder). Run each command from anywhere; the commands name PROJECT.

## Goal

PROJECT looks like Ormus work: its colors, fonts, radii and motion come from
the `--ormus-*` variables, the page shell wears the fusion surface, buttons
and cards use the fusion classes, the rules of the style guide hold, and the
change is one reviewable branch with a passing build. Nothing is merged or
deployed by this playbook.

## Before you start

| Need | Check | Expected | If it fails |
|---|---|---|---|
| this repo is intact | `bash DS/check.sh \| tail -n 1` | `check: ok` | `git -C DS status`, then fix or re-clone before going on |
| git, and a clean project | `git -C PROJECT status --porcelain \| wc -l` | `0` | commit or stash the person's changes first; never mix them into this branch |
| the project builds today | the project's own build command (for example `npm run build`) | exit code 0 | stop and tell the person; do not start on a broken build |
| Python 3.11 or newer (for the contrast helper) | `python3 -c 'import sys; print(sys.version_info >= (3, 11))'` | `True` | skip step 14's helper and use the table in DS/README.md |
| the project is about Ormus work | ask the person | yes | if it is for another company, stop: read DS/BRAND.md; the system may be borrowed, the marks may not |

## Steps

### 1. Branch

Write down the branch the project is on now: it is BASE, and the Undo block
needs it.

```bash
git -C PROJECT rev-parse --abbrev-ref HEAD
git -C PROJECT switch -c chore/ormus-design-system
```

Verify: `git -C PROJECT branch --show-current`
Expected: `chore/ormus-design-system` (and you wrote down BASE).

### 2. Read the project's shape

Find out four facts and write them down: the framework (plain HTML, Vite,
Next.js, other), the stylesheet the pages load first (the "entry CSS"), the
place where static files are served from, and whether Tailwind is used (and
which major version). These choices decide VENDOR and steps 8 to 9.

```bash
ls PROJECT
grep -E '"(tailwindcss|next|vite|react|vue|svelte|astro)"' PROJECT/package.json
```

Verify: `test -d PROJECT/SRC && echo src-ok; test -f PROJECT/package.json && echo node-project || echo static-project`
Expected: `src-ok` and one of the two project words. If `src-ok` is missing, fix SRC before going on. Write down the facts before step 3.

### 3. Count the colors and fonts the project writes itself

This is the baseline that step 10 drives to zero. The helper counts hex,
rgb(), hsl(), oklch() and similar in any case, and named colors in color
declarations, custom properties and `var()` fallbacks (the same rules as the
demo page check). It skips node_modules, vendor, dist and build folders.

```bash
python3 DS/scripts/find_colors.py PROJECT | tail -n 1
```

Verify: the command above
Expected: `colors: N`. Write N down as BASELINE.

### 4. Copy the files in

Copy, do not link. A copied file cannot change under the app. `SOURCE.lock`
records which ormus-brand commit the copy came from. Only the texture is
copied here; marks are copied in step 13 and the Tailwind files in step 9, so
the project holds only what it uses.

```bash
mkdir -p PROJECT/VENDOR/assets
for f in tokens.css tokens.json fusion.css base.css SOURCE.lock; do cp DS/$f PROJECT/VENDOR/$f; done
cp DS/assets/midnight-lacquer.jpg PROJECT/VENDOR/assets/
```

Verify: `for f in tokens.css tokens.json fusion.css base.css assets/midnight-lacquer.jpg; do cmp DS/$f PROJECT/VENDOR/$f || echo DIFF $f; done; echo checked`
Expected: `checked` and no `DIFF` line.

### 5. Make re-vendoring one command

Write `PROJECT/scripts/vendor-ormus.sh` so the next update is a command, not a
memory. It takes DS (an absolute path) as its first argument and refreshes
what is already vendored: the core files, the texture, and any marks, Tailwind
files or BRAND.md present.

```bash
mkdir -p PROJECT/scripts
cat > PROJECT/scripts/vendor-ormus.sh <<'SH'
#!/usr/bin/env bash
# Copies the Ormus design system files into VENDOR. Usage: scripts/vendor-ormus.sh ABSOLUTE_DS_FOLDER
set -euo pipefail
ds="${1:?usage: scripts/vendor-ormus.sh ABSOLUTE_DS_FOLDER}"
[[ "$ds" == /* ]] || { echo "vendor-ormus: give an absolute path" >&2; exit 2; }
cd "$(dirname "$0")/.."
dest="VENDOR"
mkdir -p "$dest/assets"
for f in tokens.css tokens.json fusion.css base.css SOURCE.lock; do cp "$ds/$f" "$dest/$f"; done
cp "$ds/assets/midnight-lacquer.jpg" "$dest/assets/"
for f in BRAND.md tailwind/preset.cjs tailwind/theme.css; do
  if [[ -e "$dest/$f" ]]; then cp "$ds/$f" "$dest/$f"; fi
done
for m in "$dest"/assets/marks/*.png; do
  if [[ -e "$m" ]]; then cp "$ds/assets/marks/$(basename "$m")" "$m"; fi
done
echo "vendored $(grep '^commit ' "$dest/SOURCE.lock" | cut -c1-19)"
SH
chmod +x PROJECT/scripts/vendor-ormus.sh
```

Put the real VENDOR path in the `dest=` line. If the project has a
`package.json`, add the script `"vendor:design": "bash scripts/vendor-ormus.sh /absolute/path/to/ormus-design-system"`.

Verify: `bash PROJECT/scripts/vendor-ormus.sh DS | grep -c '^vendored commit'`
Expected: `1`. Run it twice: the second run changes no file (`git -C PROJECT status --porcelain` lists the same entries).

### 6. Load the fonts

Add this to the `<head>` of every page, or of the shared layout (Next.js:
`app/layout.tsx` or `pages/_document.tsx`; Vite: `index.html`). Fonts are
Google Fonts under the SIL Open Font License.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

In Next.js you may use `next/font/google` for the same three families instead
(`Cormorant_Garamond`, `Inter`, `JetBrains_Mono`); keep the weights above and
map the font variables to `--ormus-font-display`, `--ormus-font-sans` and
`--ormus-font-mono` only if the person agrees.

Verify: `grep -rl -E 'family=Cormorant\+Garamond|Cormorant_Garamond' PROJECT --include='*.html' --include='*.tsx' --include='*.jsx' --include='*.ts' --include='*.js' --include='*.vue' --exclude-dir=node_modules --exclude-dir=.git | head`
Expected: at least one file (the layout, the index page or the font setup).

### 7. Load the CSS in order

Order matters: tokens define the variables, fusion uses them, base adds the
starter layer, and the app's own CSS comes last so it can refine them. With
plain HTML, add `<link>` tags. With a bundler, put `@import` lines at the very
top of the entry CSS.

```css
@import "VENDOR/tokens.css";
@import "VENDOR/fusion.css";
@import "VENDOR/base.css";
```

(Write the real relative path from the entry CSS to VENDOR.)

Verify: `python3 DS/scripts/check_import_order.py ENTRY`
Expected: `import order: ok`, where ENTRY is the entry CSS or the HTML file. The script ignores commented lines and fails when tokens.css is missing or the order is wrong.

### 8. Put the surface on the page shell

Add `class="surface-firm"` to the element that wraps the whole app: `<body>`
in plain HTML, the root `<div id="root">` or the body in a React or Vue app.
The class paints the midnight lacquer, the gold dust, the heading fonts and
the ink color. There is one theme, and it is night.

Verify: `grep -rn 'surface-firm' PROJECT --include='*.html' --include='*.tsx' --include='*.jsx' --include='*.vue' --include='*.svelte' --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=VENDOR | head -n 3`
Expected: at least one line, on the shell element.

### 9. Map the framework's theme onto the variables

Without Tailwind, skip to step 10. With Tailwind, copy the two files first:

```bash
mkdir -p PROJECT/VENDOR/tailwind
cp DS/tailwind/preset.cjs DS/tailwind/theme.css PROJECT/VENDOR/tailwind/
```

- v3: in `tailwind.config.js` add `presets: [require("./VENDOR/tailwind/preset.cjs")]`.
- v4: in the main CSS, after `@import "tailwindcss";` and the tokens import, add `@import "VENDOR/tailwind/theme.css";`.

Remove the project's own color and font entries from its Tailwind theme when
the preset covers them (`ormus-*` colors, `ormus-accent-*`, `display`, `sans`,
`mono`, the three radii). Ask the person before you delete a color the preset
does not cover.

Verify: `grep -rn -E "(require\(|import[^;]* from )['\"][^'\"]*tailwind/preset\.cjs|@import[[:space:]]+(url\()?['\"]?[^'\")]*tailwind/theme\.css" PROJECT --include='tailwind.config.*' --include='*.css' --exclude=preset.cjs --exclude=theme.css --exclude-dir=node_modules --exclude-dir=.git | grep -v -E '^[^:]+:[0-9]+:[[:space:]]*(//|/\*|\*|<!--)' | head -n 3`
Expected: at least one line, from the project's own config or CSS (the vendored copies and commented lines are excluded, so an empty result means the import is missing).

### 10. Replace written-out colors with variables

For each hit the step 3 helper lists (run it without `| tail -n 1`), replace the value with the variable. Exact
matches are mechanical: `#14213d` is `var(--ormus-midnight)`, `#0e1830` is
`var(--ormus-deep)`, `#d29e3d` is `var(--ormus-gold)`, `#eceae3` is
`var(--ormus-ink)`, and so on (the table is in DS/README.md; the full list is
VENDOR/tokens.json). A color with no exact token is a decision: show the person
the nearest token and the contrast of the pair, and change it only on a yes.
Charts, graphs and canvas read `VENDOR/tokens.json` (`canvas` group), never a
pasted hex. A risk matrix or audit may keep a restrained red, amber, green
trio, scoped to that one view.

Also replace written-out font stacks with `var(--ormus-font-display)`,
`var(--ormus-font-sans)` or `var(--ormus-font-mono)`.

Verify: `python3 DS/scripts/find_colors.py PROJECT`
Expected: the last line `colors: N` has N lower than BASELINE, and every hit listed above it is one the person approved (a chart exception, a third-party embed). Aim for 0 in app code.

### 11. Apply the rules

Search for each violation and fix it. The rules are in DS/README.md. The
commands name SRC; if a command prints `grep: ... No such file`, SRC is wrong:
fix it before reading the result.

```bash
EXC="--exclude-dir=node_modules --exclude-dir=.git --exclude-dir=vendor"
EMDASH=$(printf '\342\200\224')
# light mode: remove it, midnight is pinned
grep -rn -E "prefers-color-scheme:[[:space:]]*light|(^|[^[:alnum:]-])dark:|data-theme|theme-toggle" PROJECT/SRC $EXC
# bold serif: headings in the display font are weight 300 or 400
grep -rn -E "font-(bold|semibold|extrabold)|font-weight:[[:space:]]*(600|700|800|900|bold)" PROJECT/SRC $EXC
# em dashes in visible copy
grep -rn -F -e "$EMDASH" -e '&mdash;' PROJECT/SRC $EXC
# corner radii that are not 8px, 14px or a pill
grep -rn -E "border-radius:[[:space:]]*[0-9]+px|rounded-(sm|md|lg|xl|2xl|3xl)" PROJECT/SRC $EXC
```

Remove a light theme and its toggle. Take bold off any heading set in
Cormorant. Rewrite an em dash as two sentences or a comma. Move radii to
`var(--ormus-radius)` (keys, buttons, fields), `var(--ormus-radius-container)`
(cards, groups) or `var(--ormus-radius-pill)` (chips). Keep one gold element
per view: one primary button; turn any second one into a ghost button. Never
put `backdrop-filter: blur` under a panel over video. Remove emojis from the
interface text by reading it.

Verify: `test -d PROJECT/SRC && echo src-ok`, then run the four searches again.
Expected: `src-ok`; no output from the first three; the fourth lists only radii the person approved.

### 12. Use the fusion components

Replace the project's own button and card styles with the fusion classes:
`fusion-btn fusion-btn--primary` for the one main action, `fusion-btn
fusion-btn--ghost` for the rest; `fusion-card` for cards; `mono-label` (or
`mono-label mono-label--gold`) for section labels; `ormus-field`, `ormus-chip`
and `ormus-error` from base.css for fields, tags and error lines. Copy the
markup from DS/examples/index.html. An error line says "Error:" in words, and
danger is used for errors only.

Verify: `grep -rl -E 'fusion-btn|fusion-card|mono-label' PROJECT/SRC --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=vendor | head`
Expected: at least one file listed.

### 13. Add the marks

Copy only what the project needs: the 128 px gold mark for the favicon, the
512 px one for an avatar or header, the kintsugi mark for an ending or
sign-off. Scale down, never up. Do not use the marks if the project is not
about Ormus work (DS/BRAND.md); then skip this step.

```bash
mkdir -p PROJECT/VENDOR/assets/marks
cp DS/assets/marks/ormus-mark-gold-128.png PROJECT/VENDOR/assets/marks/
cp DS/BRAND.md PROJECT/VENDOR/BRAND.md
cp DS/assets/marks/ormus-mark-gold-128.png PROJECT/PUBLIC/favicon.png
```

Add `<link rel="icon" type="image/png" href="/favicon.png">` to the head.
(PUBLIC is the folder the project serves static files from.)

Verify: `cmp DS/assets/marks/ormus-mark-gold-128.png PROJECT/PUBLIC/favicon.png && echo same`
Expected: `same`

### 14. Check every text and background pair the project adds

The system's own pairs are already measured (DS/README.md). A pair the
project invents (text over an image, a tinted panel) must reach 4.5:1 for body
text and 3:1 for text of 24px and up. Measure it:

```bash
python3 -c "import sys; sys.path.insert(0, 'DS/scripts'); import contrast; print(round(contrast.ratio('#eceae3', '#0e1830'), 2))"
```

Replace the two hex values with the colors under test.

Verify: the command above with the project's pair
Expected: `14.63` for the example pair; for a project pair, at least 4.5 (or 3.0 for large text).

### 15. Motion

Give reveals the fusion pattern (`.fusion-reveal`, and `.is-revealed` set by an
IntersectionObserver; copy DS/examples/demo.js). Every transition and
animation the project adds uses `var(--ormus-ease-reveal)` for its curve, and
stops under `prefers-reduced-motion`.

```bash
EXC="--exclude-dir=node_modules --exclude-dir=.git --exclude-dir=vendor"
# transition or animation declarations that do not use the curve (a "none" is fine)
grep -rn -E "(transition|animation)[^;{}]*[;}]" PROJECT/SRC $EXC | grep -v -E "ormus-ease-reveal|(transition|animation):[[:space:]]*none"
# reduced motion
grep -rl "prefers-reduced-motion" PROJECT/SRC $EXC
```

Verify: the two commands above.
Expected: the first prints nothing (fix each line it prints); the second lists at least one file whenever the project has any transition or animation. The search reads CSS declarations only: Tailwind `transition`, `duration-*` and `animate-*` classes are not covered, so read those by eye and give them `ease-ormus-reveal`.

### 16. Build, test and look

Run the project's build and tests. Then look at it: open the page and compare
it to DS/examples/index.html (midnight background, gold only on the one
primary action, serif headings, mono labels). With a headless browser:

```bash
rm -f /tmp/ormus-shot.png
chromium --headless=new --no-sandbox --window-size=1280,1600 --virtual-time-budget=6000 --screenshot=/tmp/ormus-shot.png URL
```

(URL is the dev server address or a file:// path to the built page. Open the
image and look at it yourself.)

Verify: the project's build command, then `test -s /tmp/ormus-shot.png && echo shot`
Expected: build exit code 0 and its tests pass; `shot`.

### 17. Commit on the branch

```bash
git -C PROJECT add -A
git -C PROJECT commit -m "chore(design): apply the Ormus design system"
```

Report to the person: the files copied, the SOURCE.lock commit, how many
written-out colors went from BASELINE to what remains, each decision you asked
about, and anything you could not verify. Do not push or merge unless they ask.

Verify: `git -C PROJECT log -1 --format=%s && git -C PROJECT status --porcelain | wc -l`
Expected: `chore(design): apply the Ormus design system` and `0`.

## Adapt it

| Setting | Where | Example |
|---|---|---|
| SRC | steps 2, 11, 12, 15 | `src`, `app`, `pages` |
| VENDOR | steps 4, 5, 7 | `public/vendor/ormus` (static), `vendor/ormus` (bundler) |
| PUBLIC | step 13 | `public`, `static`, `dist-src` |
| Entry CSS | step 7 | `src/app.css`, `app/globals.css`, `src/index.css` |
| Fonts via `next/font` | step 6 | keep weights 300 and 400 for Cormorant, 400 to 600 for Inter, 400 and 500 for the mono |
| Skip `base.css` | step 7 | when the project already sets body type, heading sizes and a focus ring; keep a visible focus ring |
| Skip the marks | step 13 | for a project that is not about Ormus work |

## Done when

- `bash DS/check.sh` ends with `check: ok`.
- The project builds and its tests pass on the branch.
- `cmp` finds every VENDOR file equal to its DS original, and `VENDOR/SOURCE.lock` names an ormus-brand commit.
- `python3 DS/scripts/find_colors.py PROJECT` ends with `colors: 0`, or each remaining hit was approved.
- The page shell has `surface-firm`, the fonts load, there is one primary button per view, no light mode, no bold serif, no em dash or emoji in visible copy.
- You looked at a screenshot and it matches the demo page's look.

## Undo

```bash
git -C PROJECT switch BASE
git -C PROJECT branch -D chore/ormus-design-system
```

(BASE is the branch you wrote down in step 1.)

Nothing outside PROJECT changed, and nothing was pushed.

## Safety

- It reads DS and PROJECT, and writes only inside PROJECT on the new branch (plus one screenshot in `/tmp`).
- It never pushes, merges, deploys, edits another repo or touches DS.
- It never edits `tokens.css`, `tokens.json` or `fusion.css` inside VENDOR. A brand change goes to ormus-brand first, then comes back through DS and `scripts/sync.sh`.
- It never defines a color or font inside the app. A color with no exact token is asked, not invented.
- It uses the Ormus name and marks only in projects about Ormus work (DS/BRAND.md).
