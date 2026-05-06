# Remove Tailwind CDN runtime — pass 2

**Iter:** `F-frontend-remove-tailwind-cdn-runtime-pass2`.

This pass removes the Tailwind CDN runtime entirely. The local
`static/css/site.css` becomes the **sole** CSS source. The site
renders premium without any external network dependency for layout.

The previous iter
(`F-frontend-local-css-premium-visual-qa-pass1`) had landed the
local stylesheet alongside the CDN as enrichment. Pass 2 deletes
the CDN script tag plus the inline `tailwind.config` runtime, runs a
gap audit to identify what the local stylesheet still doesn't cover,
extends it to close every layout-critical gap, and re-captures the
public pages to confirm the visual result is intact.

---

## CDN removal confirmation

`templates/base.html` no longer contains:

- `<script src="https://cdn.tailwindcss.com"></script>`
- `<script>tailwind.config = {…}</script>`

Verified at three levels:

1. **Source check.** `test_base_html_does_not_reference_tailwind_cdn`
   asserts the strings `cdn.tailwindcss.com` and `tailwind.config`
   are absent from `templates/base.html`.
2. **Render check.** `test_home_page_html_carries_no_tailwind_cdn`
   GET-s `/` through the test client and asserts neither string
   appears in the rendered HTML.
3. **Sweep check.** `test_public_pages_return_200_and_link_local_css`
   walks every public path (12 routes), asserts each returns 200,
   links the local CSS, and does not reference the CDN.

The pass-1 regression net was inverted accordingly:
`apps/core/test_frontend_local_css_pass1.py::test_public_pages_load_local_css_only`
now asserts the CDN reference is **absent** rather than present.

---

## Local CSS coverage audit

`scripts/audit_local_css_coverage.py`:

- Walks every HTML file under `templates/`.
- Extracts class tokens using a Tailwind-shaped regex.
- Looks each token up in `static/css/site.css` (with proper escaping
  for `:` `.` `/` `[` `]`).
- Writes a markdown report at
  `docs/architecture/LOCAL_CSS_COVERAGE_AUDIT_PASS2.md`.
- Flags layout/typography primitives as `[CRITICAL]`.

Audit progression during this iter:

```
First run (after CDN removal, before extending site.css):
  323 classes, 200 covered, 119 missing (91 CRITICAL)

After adding pass-2 batch to site.css (fractional spacing,
arbitrary tracking values, alpha overlays, sm:/lg: variants,
extra hover/gradient stops):
  323 classes, 318 covered,   1 missing (0 CRITICAL)

After adding `prose-lg`:
  323 classes, 319 covered,   0 missing (0 CRITICAL)
```

The 4-class delta between 323 and 319 is keyword-only tokens
(`italic`, `uppercase`, etc.) the audit treats specially; every
meaningful utility is now mapped.

---

## What was added to site.css

`static/css/site.css` grew from ~18 KB to ~28 KB. The new sections:

**Arbitrary tracking values** — `tracking-[0.10/0.16/0.20/0.24em]`
for the uppercase eyebrows used across cards.

**Fractional spacing rungs** — `gap-1.5`, `gap-2.5`, `mt-1.5`,
`mt-2.5`, `mt-3.5`, `mt-9`, `mt-14`, `mb-1.5`, `px-1.5`, `px-2.5`,
`px-7`, `py-0.5`, `py-3.5`, `py-5`, `py-9`, `py-14`, `py-24`,
`pt-5`, `pb-0`, `pb-14`.

**Sizing rungs** — `w-2`, `h-2`, `w-9`, `h-9`, `w-14`, `h-14`,
`h-20`, `h-40`, `h-44`, `h-52`, `h-56`, `h-64`, `h-72`, `h-80`,
`h-full`, `min-h-10`, `min-h-[40px]`, `max-w-md`, `max-w-xl`,
`max-w-2xl`, `max-w-none`.

**Typography rungs** — `text-[10px]`, `text-[12px]`, `text-6xl`,
`leading-none`, `leading-snug`, `leading-[1.05]`.

**Palette overlays (alpha)** — `bg-sand-50/95`, `bg-gold-500/10`,
`bg-gold-500/15`, `bg-ok-600/5`, `bg-ok-600/10`,
`border-gold-400/40`, `border-gold-500/40`, `border-ink-700/40`,
`border-ink-950/15`, `border-ok-600/30`, `border-sand-50/30`,
`border-sand-50/40`, `text-sand-50/{70,80,90}`,
`text-sand-100/80`.

**Responsive sm: variants** — gap, items, padding, height, text
size up to `sm:text-5xl`.

**Responsive lg: variants** — flex direction, sticky positioning,
grid columns up to `lg:grid-cols-12`, col-span 2/5/7, gap, padding,
height, text size up to `lg:text-6xl`.

**Hover variants** — `hover:text-gold-{400,600}`, `hover:bg-*`,
`hover:border-gold-400/60`, `hover:shadow-card`, `hover:shadow-lg`,
`group:hover .group-hover:text-gold-600`.

**Gradient endpoints with alpha** — `to-ink-950/0`,
`from-ink-950/{30,55,85}`, `to-ink-800`, `to-ink-900/65`,
`via-ink-950/{0,15,75}`, `from-sand-50`, `from-sand-100`,
`to-sand-50/100`, `from-transparent`, `to-transparent`.

**Logical properties** — `ms-2`, `ms-auto` (RTL-aware margin-inline-start).

**Spacing scale** — `space-y-1`, `gap-12`, `mt-24`, `mt-32`,
`text-justify`, `tabular-nums`.

**Prose helpers** — `.prose`, `.prose-lg` for long-form content
(methodology / disclaimer pages).

**Print-friendly tweaks** — `@media print { … }` removes shadows,
forces solid backgrounds, ensures the PDF generator (which
snapshots CSS) produces a clean print-ready output.

---

## Visual review notes

Screenshots: `docs/screenshots/live_qa/remove_tailwind_cdn_pass2/after/`.

24 fixtures captured (16 desktop + 8 mobile).

### Desktop 1440 × 900

- **`home.png`** — premium hero with library photo overlay, two
  CTAs, "Copertura MVP" 5-column country grid (IT/FR/BE/MA/TN),
  three feature cards "Solo fonti validate / Intervalli
  trasparenti / Revisione umana", ink-950 callout "Pronto per una
  valutazione legale reale?", footer.
- **`countries.png`** — country index grid.
- **`countries_italy.png`**, **`countries_france.png`**,
  **`countries_morocco.png`** — per-country pages with status
  panel + "Base legale" tables.
- **`case_types.png`**, **`methodology.png`** — content pages with
  prose layout.
- **`wizard_*.png`** — every wizard form (IT road accident, MA/TN
  inheritance) renders the premium card chain (sections, inputs,
  CTA pills) with sand background and ink/gold palette.
- **`result_it_calculated.png`** — calculated path: range card 26
  268 / 27 353 / 28 439 EUR, "Caso ipotetico", numbered next steps,
  Calculation basis 3-column grid, Ipotesi, Fonti legali citate
  card, ink disclaimer, CTAs. Public-warning callout from the
  previous iter still renders.
- **`result_ma_unavailable.png`** — no-estimate path: status badge
  "Analisi successoria internazionale", "Cosa succede ora" card,
  applicable-law hint sand-100 callout, three numbered next steps,
  ink disclaimer, CTAs.
- **`contact.png`** — contact form premium styled.
- **`home_FR_locale.png`** — full FR locale rendering of the
  homepage; every CTA / heading / disclaimer translated.
- **`wizard_ma_inheritance_AR_locale.png`** — full RTL Arabic,
  hero, status panel, three sections in Arabic with checkbox cards
  mirroring right-to-left.

### Mobile 375 × 800

- All fixtures collapse to a clean single-column stack.
- No horizontal overflow, no clipped content.
- The wizard's family-situation 3-col grid stacks vertically.
- Result pages render the range card and warning callout in
  single column.
- Arabic mobile shot mirrors layout right-to-left without manual
  override.

### What was improved during this iter

- **CDN entirely gone** from the rendered HTML on every public
  page.
- **CSS coverage 100% on layout-critical utilities** (after the
  audit + extension batch).
- **Print stylesheet** added so PDF snapshots use a flat
  white background and no shadows.
- **Logical inline-start margins** (`ms-2`, `ms-auto`) added so the
  RTL paths use the correct CSS without the engine needing to know.
- **Hover and group-hover states** restored for the header
  navigation links + feature cards.

---

## No DB / legal changes

No model edit, no migration, no `LegalSource`, `LegalReview`,
`CompensationDataset`, `CompensationTableRow`, `CalculationFormula`
created or promoted. Italy calculation values are byte-identical.

## FR / BE / MA / TN still no automatic calculations

`public_status` rows unchanged. POST on the public DB still returns
`unavailable_requires_legal_validation` for FR / BE / MA / TN. The
CDN removal is a frontend-only iter.

## Italia preserved + PDF %PDF

- 35 / 10 / 0 → 26 268 / 27 353 / 28 439 EUR (verified by
  `test_italy_smoke_unchanged_after_cdn_removal`).
- IT PDF response starts with `%PDF` (verified by
  `test_italy_pdf_remains_valid_after_cdn_removal`).
- Result page shows the public-warning callout (Italy-localised
  diagnostics from the previous iter).

---

## Hygiene + audits + lint

- `audit_public_content_hygiene.py`: **ok**, 0 issues, 6/6 rules.
- `audit_public_result_messages.py`: **OK**, 6/6 fixtures clean.
- `audit_calculator_diagnostic_strings.py`: 18 findings, 1 distinct
  literal slug (intentional `block` forward).
- `audit_local_css_coverage.py`: **323 classes, 319 covered, 0
  missing (0 CRITICAL)**.
- `run_public_lighthouse_audit.py --mode playwright`: **OK**, 8/8
  routes pass.

## check / lint / test

- `manage.py makemigrations --check`: No changes detected.
- `manage.py check`: 0 issues.
- `compilemessages`: OK.
- `pytest -q`: **1314 passed, 1 skipped** (1303 prior + 11 new).
- `ruff check .`: All checks passed.
- `black --check .`: 281 files, 0 to reformat.

---

## What remains for future iters

- **Fonts via local mirror.** The site still loads
  `https://fonts.googleapis.com/css2?…` for Cormorant Garamond +
  Inter. If full offline rendering is required (CSP-strict
  deployments, restricted networks), a future iter could mirror
  these fonts under `static/fonts/` with `@font-face` declarations
  in `site.css`.
- **`static/css/site.css` minification.** The file is ~28 KB
  uncompressed; a future iter could add a build step to minify it.
- **Italy's calculated path warning template.** The
  `templates/public/wizard_result.html` block introduced by the
  previous iter renders the public_warnings list. Future iters
  could add a per-warning icon based on the diagnostic code.

---

## Cross-references

- Template: `templates/base.html`
- Stylesheet: `static/css/site.css`
- Coverage audit: `scripts/audit_local_css_coverage.py` →
  `docs/architecture/LOCAL_CSS_COVERAGE_AUDIT_PASS2.md`
- Capture script: `scripts/capture_remove_tailwind_cdn_pass2.py`
- Tests: `apps/core/test_remove_tailwind_cdn_pass2.py`
- Lighthouse output:
  `docs/reports/lighthouse/remove_tailwind_cdn_pass2/`
- Screenshots:
  `docs/screenshots/live_qa/remove_tailwind_cdn_pass2/`
- Sibling iters:
  - `docs/architecture/FRONTEND_LOCAL_CSS_PREMIUM_VISUAL_QA_PASS1.md`
  - `docs/architecture/RESULT_PAGE_LOCALIZATION_PASS1.md`
  - `docs/architecture/ITALY_WARNING_STRINGS_TRANSLATABLE_PASS1.md`
