# Changelog

Every change a reader should know about, newest first.

## 0.1.1 - 2026-11-24

- First release. `tokens.css`, `tokens.json`, `fusion.css` and the marks and
  texture in `assets/` are copied from ormus-brand 0.4.0 at the commit
  recorded in `SOURCE.lock`, with `scripts/sync.sh` to copy them again.
- `base.css` (body type, heading sizes from `tokens.json`, focus ring,
  disabled state, field, chip, error line), a Tailwind v3 preset and a
  Tailwind v4 theme (`ormus-accent-*` for the identity accents), and
  `examples/index.html`.
- `README.md`, `PLAYBOOK.md` (an agent applies the system to an existing web
  project, step by step) and `BRAND.md` (what the Ormus name and marks allow).
- `check.sh`, the one gate: the drift test (`tests/test_drift.py`, which fails
  when a copy no longer matches `SOURCE.lock` or the recorded ormus-brand
  commit), the contrast measure (`scripts/contrast.py`), the demo page check
  (`scripts/check_html.py`), shellcheck and the scrub.
- The scrub gate (`scripts/scrub_gate.py`): a deny-list hit is excused only in
  `tokens.css`, `tokens.json` or `fusion.css`, and only for the version whose
  sha256 is in the `SOURCE.lock` held by the same commit. `SOURCE.lock` keeps a
  strict line grammar and is never excused. With an ormus-brand checkout at
  hand, every lock (current and historical) is verified against
  `git show COMMIT:path` in that checkout; without one the gate says the source
  was not verified. Setup errors, a missing or empty named deny-list and
  control characters in file names stop the gate; every ref is scanned.
- Helpers for the playbook: `scripts/find_colors.py` and
  `scripts/check_import_order.py`.
