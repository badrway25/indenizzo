# Frontend — local premium CSS, pass 1

**Iter:** `F-frontend-local-css-premium-visual-qa-pass1`.

This pass removes the visual dependency on the Tailwind CDN. Before
this iter, every public page relied on `https://cdn.tailwindcss.com`
to render: Playwright sandboxes, restricted-network clients and
offline previews all received an unstyled page. After this iter, a
hand-written `static/css/site.css` covers every layout-critical
utility used across the templates, so the site renders premium even
when the CDN is blocked at the network layer. The CDN is kept as
*enrichment* (it still loads when reachable) but is no longer a
blocker for visual QA.

---

## CSS strategy

`static/css/site.css` is a hand-curated, Tailwind-compatible subset.
It is loaded **before** the CDN script in `templates/base.html`, so
the local rules form the baseline; the CDN's runtime layer only adds
extra utilities when present.

What the local stylesheet covers:

- **Design tokens** as CSS variables: `--ink-*`, `--gold-*`,
  `--sand-*`, `--stone2-*`, `--ok-600`, `--red-*`, `--shadow-card`.
- **Reset + base typography**: body font, headings font (Cormorant
  Garamond), background color (`#faf6ef`), text color, line-height,
  flex column body for sticky-footer layout.
- **Spacing scale**: `m-{0,1,2,3,4,5,6,8,10,12,16,20}` and
  per-direction variants (`mt-*`, `mb-*`, `mx-*`, `my-*`, `pt-*`,
  `pb-*`, `px-*`, `py-*`, `gap-*`, `space-y-*`).
- **Sizing**: `w-*`, `h-*`, `max-w-{3xl,4xl,5xl,6xl,7xl}`,
  `min-h-screen`, `flex-1`, `flex-shrink-0`.
- **Display**: `block`, `inline-block`, `flex`, `inline-flex`,
  `grid`, `hidden`.
- **Flex**: `flex-{col,row,wrap}`, `items-*`, `justify-*`,
  `self-*`.
- **Grid**: `grid-cols-{1,2,3,4}`, `col-span-2`, with `sm:` and
  `lg:` responsive variants.
- **Typography**: `text-{xs,sm,base,lg,xl,2xl,3xl,4xl,5xl}`,
  `font-{normal,medium,semibold,bold}`, `font-{sans,serif,mono}`,
  `leading-{tight,relaxed}`, `tracking-[…]` arbitrary values,
  `uppercase`, `text-{left,center,right}`, `break-{all,words}`,
  `whitespace-nowrap`, `list-{decimal,disc,inside}`, `underline`.
- **Palette**: `bg-`, `text-`, `border-` for every token shade
  used across the templates (white, ink, gold, sand, stone2, ok,
  red).
- **Borders**: `border`, `border-{t,b,y}`, `border-{token}`,
  `rounded-{md,lg,xl,2xl,3xl,full}`.
- **Shadows**: `shadow-card`, `shadow-sm`, `shadow`,
  `drop-shadow`.
- **Positioning**: `relative`, `absolute`, `fixed`, `sticky`,
  `top-*`, `bottom-*`, `left-*`, `right-*`, `inset-0`, `z-{10..50}`.
- **Misc**: `cursor-pointer`, `overflow-{hidden,auto}`, `divide-y`,
  `aspect-video`, `object-cover`, `opacity-50`, `backdrop-blur`.
- **Gradients**: `bg-gradient-to-{br,t,tr}` + `from-`/`to-`/`via-`
  for the project palette.
- **Accessibility**: `sr-only`, `focus:not-sr-only`,
  `focus-visible:outline-{2,offset-2,gold-400}`, focus-state
  helpers on `bg/text/border` for inputs and skip links.
- **Hover**: `hover:bg-*`, `hover:text-*`, `hover:border-*`,
  `hover:underline` for ink/gold/sand/stone2.
- **Responsive**: `sm:` (≥640 px) and `lg:` (≥1024 px) media
  queries for the most-used utilities.
- **Component-level tweaks**: form input + checkbox styling,
  cookie-banner accept button.

Total file size: ~18 KB uncompressed.

---

## Tailwind CDN dependency status

- Removed as a hard dependency for visual rendering.
- Still loaded as a `<script>` tag — when the CDN is reachable, the
  full Tailwind runtime adds any utilities the local file misses
  (defensive layering).
- When the CDN is unreachable, the local stylesheet alone produces
  premium-looking pages. The Playwright capture script
  (`scripts/capture_frontend_local_css_pass1.py`) deliberately
  blocks `cdn.tailwindcss.com` in both phases to verify this.

---

## base.html changes

`templates/base.html`:

- Added `<link rel="stylesheet" href="{% static 'css/site.css' %}">`
  immediately after the `<meta>` block and before any external
  resource.
- Replaced the previous single-line `{# ... #}` comments around the
  CSS block with `{% comment %}…{% endcomment %}` blocks.
  *Multi-line `{# ... #}` is NOT stripped by Django* — it leaks the
  comment text into the rendered HTML. The bug actually surfaced
  during this iter's first AFTER capture: the screenshot had the
  CSS-comment text showing as plain text at the top of every page.
  A regression test
  (`test_base_html_does_not_leak_comment_text`) prevents the same
  mistake from recurring.

---

## Visual review notes

Before / after screenshots live under
`docs/screenshots/live_qa/frontend_local_css_premium_visual_qa_pass1/`.

```
before/
  desktop/  home.png, countries.png, countries_italy.png,
            countries_morocco.png, wizard_start.png,
            wizard_it_road_accident.png, wizard_ma_inheritance.png,
            wizard_tn_inheritance.png, contact.png,
            result_it_calculated.png, result_ma_unavailable.png
  mobile/   home.png, countries.png, wizard_start.png,
            wizard_ma_inheritance.png, result_ma_unavailable.png,
            wizard_ma_inheritance_ar.png
after/
  (same paths, same dimensions, fully styled)
```

### Desktop 1440 × 900 — BEFORE

The shots show the historic broken state: white background, blue
underlined links, no hero card, form inputs are browser-default,
H1 is a default Times Roman heading with no spacing. There is
visibly no premium signal — the wizard looks like a 1995 PHP form.

### Desktop 1440 × 900 — AFTER

Every fixture renders premium:

- **Home** — sand background, hero with library photo overlay,
  three premium feature cards in a 3-column grid, ink CTA bar at
  the bottom. Country grid shows IT/FR/BE/MA/TN tiles in 3-column.
- **Countries / countries/italy/ / countries/morocco/** — left
  column copy + right-side status panel card; "Base legale" rows
  with rounded badges.
- **Wizard MA / TN / IT / FR road-accident** — hero image, sand
  card with rounded-3xl + shadow-card, form fields with
  `bg-sand-50` + `border-stone2-200`, three-column grids for
  family-situation cards and counter inputs, ink-950 CTA pill.
- **Wizard result IT (calculated)** — ok-600 toned range card with
  three EUR amounts, "Calculation basis" 3-column grid, sources
  card list, ink disclaimer card at the bottom.
- **Wizard result MA (unavailable)** — gold-toned status panel,
  "Cosa succede ora" card with the applicable-law hint inside a
  sand-100 callout, three numbered next-steps, ink CTA + secondary
  pills, ink disclaimer.
- **Contact** — same chrome, lead form with grouped fieldset.

### Mobile 375 × 800 — AFTER

Every fixture collapses cleanly to single-column: hero stays
visible at the top, the wizard's family-situation 3-column grid
becomes a vertical stack, the result page's premium card chain
flows top-to-bottom without horizontal overflow.

### RTL (Arabic) — AFTER

The Arabic wizard mirrors layout right-to-left. The new logical
helpers in `site.css` (`[dir="rtl"] .text-left/right` rules) keep
text alignment correct without manual mirroring. The premium
status badge and form cards retain shape and palette.

### Premium fixes applied during this iter

- **Comment-leak bug.** Initial AFTER capture showed the CSS
  comment text rendering at the top of every page (multi-line
  `{# #}` in Django doesn't strip). Switched to
  `{% comment %}…{% endcomment %}` and added a regression test.
- **Form input baseline.** Added a generic `form input/select/
  textarea` rule in `site.css` so wizard inputs look styled even
  before per-page JS class injection runs.
- **Cookie banner button.** Added a styling rule for
  `#cookie-consent-accept` so it looks like a premium gold pill
  even with no Tailwind utilities applied.

---

## Confirmation: screenshots are styled locally

The capture script blocks `cdn.tailwindcss.com` in both BEFORE and
AFTER passes. The only difference between phases is whether
`static/css/site.css` is loaded by `base.html`:

- **BEFORE**: link absent + CDN blocked → unstyled HTML (verified
  visually).
- **AFTER**: link present + CDN blocked → premium-styled HTML
  (verified visually).

This proves the local stylesheet is sufficient on its own. The
capture script is committed under `scripts/capture_frontend_local_css_pass1.py`
so the visual QA is reproducible.

---

## No DB / legal changes

This iter is purely frontend: no model, migration, `LegalSource`,
`LegalReview`, `CompensationDataset`, `CompensationTableRow`, or
`CalculationFormula` change.

## FR / BE / MA / TN still no automatic calculations

`public_status` rows unchanged. POST FR/BE → preliminary review
(unstyled English warning is gone since iter
`F-inheritance-wizard-result-page-localization-pass1`). POST MA/TN
→ inheritance review with the applicable-law hint card (added in
the previous iter). No calculator activation here.

## Italia preserved

`test_italy_smoke_unchanged_with_local_css`:
35 / 10 / 0 → 26 268 / 27 353 / 28 439 EUR. Render of the result
page still shows the three amounts.

---

## Hygiene + audits

- `audit_public_content_hygiene.py`: **ok**, 0 issues, 6/6 rules.
- `audit_public_result_messages.py`: **OK**, 6/6 fixtures clean.
- `run_public_lighthouse_audit.py --mode playwright`: **OK**, 8/8
  routes pass.

## check / lint / test

- `manage.py makemigrations --check`: No changes detected.
- `manage.py check`: 0 issues.
- `compilemessages`: OK.
- `pytest -q`: 1259 passed, 1 skipped.
- `ruff check .`: All checks passed.
- `black --check .`: 270 files, 0 to reformat.

---

## What remains

- The local stylesheet covers utilities used by the templates as of
  this iter. New templates may introduce utilities the local file
  doesn't carry; the CDN runtime is the safety net while reachable,
  and a future iter can grow `site.css` as needed.
- A long-term improvement is to swap the CDN runtime for a built
  Tailwind output (PostCSS pipeline). That is a separate iter
  (`F-frontend-tailwind-build-pipeline-pass1`) that requires Node
  tooling — out of scope here.
- The legacy `<script>` tag for `cdn.tailwindcss.com` could be
  removed entirely once `site.css` is verified to cover every
  utility. This iter keeps it for safety; a follow-up iter could
  drop it after a wider regression sweep.

---

## Cross-references

- Stylesheet: `static/css/site.css`
- Template: `templates/base.html`
- Tests: `apps/core/test_frontend_local_css_pass1.py`
- Capture script: `scripts/capture_frontend_local_css_pass1.py`
- Audits: `scripts/audit_public_content_hygiene.py`,
  `scripts/audit_public_result_messages.py`,
  `scripts/run_public_lighthouse_audit.py`
- Lighthouse output: `docs/reports/lighthouse/frontend_local_css_premium_visual_qa_pass1/`
- Screenshots: `docs/screenshots/live_qa/frontend_local_css_premium_visual_qa_pass1/`
