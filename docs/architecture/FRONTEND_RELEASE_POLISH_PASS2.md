# F-frontend-release-polish-pass2

Polish pass that closes the three non-blocking visual items raised
by the `F-product-release-readiness-audit-pass1` report:

1. Mobile `<sm` IT-result card spacing vs. the floating cookie banner.
2. MA / TN country-landing hero crop ratio.
3. AR / Tajawal typography (no Arabic webfont was actually loaded;
   headings fell back to whatever the OS shipped, which read
   noticeably heavier than the IT/FR Cormorant + Inter rhythm).

No DB / legal / calculator / wizard logic touched. No country
activations. Italia 35/10/0 still produces 26 268 / 27 353 / 28 439
EUR; the IT PDF still serves `%PDF`.

## What changed

### 1) Cookie-banner spacing

`templates/partials/cookie_consent_banner.html` now publishes the
banner's measured height as a CSS custom property
(`--cookie-banner-h`) on `<html>` while the banner is visible, and
clears it once the user accepts. `static/css/site.css` reads that
variable on `body { padding-bottom: var(--cookie-banner-h, 0px); }`,
so every page reserves exactly the room the banner needs.

The padding is additive on top of any per-page bottom padding and
applies on every viewport, so the banner can never overlap the
result-page CTA cluster on mobile (which was the original critique)
or the footer on desktop.

When the banner is dismissed, the variable is cleared and the
padding collapses to zero — no permanent bottom whitespace.

### 2) Country-landing hero — uniform aspect ratio

Every Pexels country photo in the manifest is `1200×627`
(ratio ≈ 1.914). The previous template used `h-56 sm:h-72 lg:h-80`
which forced different visible-area aspect ratios at every
breakpoint and yielded different crops per country depending on
the photo's focal point.

The hero `<img>` now carries the new utility:

```css
.country-hero-photo {
  width: 100%;
  height: auto;
  aspect-ratio: 1200 / 627;
  object-fit: cover;
  object-position: center 35%;
  display: block;
}
```

The container shape is identical at all breakpoints, the photo
fills it without zoom-cropping, and the slight upward focal point
(`center 35%`) keeps monuments / faces in frame on every country.

### 3) AR typography

`templates/base.html` now requests Amiri (serif Arabic) and Tajawal
(sans Arabic) from Google Fonts in the same `<link>` as Cormorant
Garamond and Inter. The local `static/css/site.css` adds the
RTL-only family rules:

```css
[dir="rtl"] body {
  font-family: 'Tajawal', 'Inter', system-ui, sans-serif;
}
[dir="rtl"] h1, [dir="rtl"] h2, [dir="rtl"] h3, [dir="rtl"] h4,
[dir="rtl"] .font-serif {
  font-family: 'Amiri', 'Cormorant Garamond', Georgia, serif;
  letter-spacing: 0;
}
```

Same pairing intent as the LTR side: serif (Amiri ↔ Cormorant) for
display headings, sans (Tajawal ↔ Inter) for body. `letter-spacing`
is reset because Arabic typography does not benefit from the
slightly negative tracking applied to Cormorant.

The same rules are mirrored inside the inline `<style>` block of
`templates/base.html` so the very first paint already gets the
correct family before `site.css` arrives.

## Browser visual QA

Capture script: `scripts/capture_frontend_release_polish_pass2.py`
(`--phase before|after`). The Tailwind CDN is route-aborted so the
rendered layout exercises only `static/css/site.css`.

Screenshot bundles:

```
docs/screenshots/live_qa/frontend_release_polish_pass2/
├── before/
│   ├── desktop/   {01_country_morocco, 02_country_tunisia, 03_result_it_calculated}
│   ├── mobile/    {01_country_morocco, 02_country_tunisia, 03_result_it_calculated}
│   └── rtl_locale/{01_home_ar, 02_country_morocco_ar, 03_wizard_ma_inheritance_ar, 04_result_ma_unavailable_ar}
└── after/         (same set, after the fix)
```

### Visual notes — desktop

- **Country MA / TN (`01_…`, `02_…`)**: the after frames render
  the photo with the source 1200/627 ratio, so MA's mausoleum and
  TN's coastline both occupy the same banner shape. The previous
  fixed-height crop visibly compressed TN; now both feel
  intentional.
- **Result IT calculated (`03_…`)**: the cookie banner now sits
  directly above the disclaimer card with breathing room from the
  CTAs. The full-page screenshot still shows the banner because of
  fixed-position rendering, but the body has the additive bottom
  padding visible at the foot of the page.

### Visual notes — mobile

- **Result IT calculated**: pre-fix, the cookie banner overlapped
  the simulation-ID + PDF + back-to-wizard CTAs. Post-fix, the
  banner reserves its own height and the CTAs sit cleanly above
  it.
- **Country MA / TN**: the hero shape now matches its desktop
  twin proportionally (no more letterbox-ish look).

### Visual notes — RTL/locale

- **Home AR (`01_home_ar`)**: H1 renders in Amiri — the
  calligraphic serif gives the Arabic display the same gravitas
  as Cormorant on the IT page.
- **Country MA AR (`02_…`)**: heading "المغرب — لا نغطّيه حالياً"
  renders in Amiri with an upright weight that pairs well with
  the gold eyebrow above it. Body in Tajawal reads cleanly.
- **Wizard MA AR (`03_…`)**: form labels (Tajawal, body weight)
  match the wizard chrome; the heading stays in Amiri.
- **Result MA unavailable AR (`04_…`)**: the
  "International inheritance review" panel now uses Amiri for the
  H1 and Tajawal for the body — matching the IT calculated page's
  rhythm.

## Audits and validation

| Check | Result |
|-------|--------|
| `audit_public_content_hygiene.py` | OK (0 pages with issues) |
| `audit_public_result_messages.py` | OK (no technical strings) |
| `audit_local_css_coverage.py` | 318 / 322 covered, 0 critical (one less utility selector now that fixed heights were removed from the country-landing hero) |
| `audit_product_release_readiness.py` | OK (it_baseline OK, FR/BE/MA/TN unavailable 4/4, counts unchanged) |
| `run_public_lighthouse_audit.py --mode=playwright` | every URL passes |
| `pytest -q` | 1353 passed, 1 skipped |
| `ruff check .` | All checks passed |
| `black --check .` | 287 files unchanged |
| `manage.py check` | No issues |
| `manage.py makemigrations --check` | No changes |

## Files touched

- `static/css/site.css` — `body { padding-bottom: var(--cookie-banner-h, 0px); }`, `.country-hero-photo`, `[dir="rtl"]` typography pair.
- `templates/base.html` — Google Fonts URL extended with `Amiri` + `Tajawal`; inline `<style>` mirrors the AR rules.
- `templates/partials/cookie_consent_banner.html` — JS publishes/clears `--cookie-banner-h` and re-syncs on `resize` / dismiss.
- `templates/public/country_landing.html` — Pexels hero `<img>` now uses `country-hero-photo` instead of `h-56 sm:h-72 lg:h-80 object-cover`.
- `scripts/capture_frontend_release_polish_pass2.py` — before/after capture script.

## What did NOT change

- No `LegalSource` / `CompensationDataset` / `CalculationFormula`
  / `CompensationTableRow` rows touched.
- No FR / BE / MA / TN activations.
- No Italy calculator math change.
- No wizard / form / view / URL logic.
- No deploy.

## Server live

- URL: `http://127.0.0.1:48107`
- Stop: `netstat -ano | grep ":48107.*LISTENING"` to find the PID,
  then `Stop-Process -Id <pid> -Force`.

## Next step

The release-readiness audit's three non-blocking polish items are
closed. The next public-facing work is whatever the next iter
brings — there are no remaining items in the audit's "non-blocking
polish" list.
