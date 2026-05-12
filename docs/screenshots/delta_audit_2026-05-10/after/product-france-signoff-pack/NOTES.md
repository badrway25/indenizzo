# PRODUCT-1 France activation signoff pack — visual QA

**Date**: 2026-05-12
**Iter**: `PRODUCT-1-france-activation-signoff-pack`
**Branch**: `product/france-activation-signoff-pack`
**Verdict**: France is review-gated as designed.

Playwright captures of the public France path **as it is today**,
before any of the 4 Studio signatures arrive. The screenshots
prove the current copy is Studio-honest:

- the `/countries/france/` landing renders the
  "Valutazione legale preliminare" panel citing Mornet, Gazette,
  Badinter and Dintilhac as **sources in legal review** — no
  amounts;
- the `/wizard/fr/road-accident/` form is accessible and complete
  but the result path emits no number;
- the `/contact/` CTA is intact and reachable.

When the 4 signatures arrive and France is activated
(`P0-MVP-1-ACTIVATE-france`), this capture set will be the
*before* reference; a paired *after* set captured at activation
time will show the same pages with computed amounts.

## Capture set

| File | Page | Viewport |
|---|---|---|
| `france-landing-desktop-1280.png` | `/countries/france/` | 1280×900 |
| `france-landing-mobile-390.png` | `/countries/france/` | 390×844 |
| `france-wizard-form-desktop-1280.png` | `/wizard/fr/road-accident/` (GET, form view) | 1280×900 |
| `france-wizard-form-mobile-390.png` | `/wizard/fr/road-accident/` (GET) | 390×844 |
| `france-result-review-gated-desktop-1280.png` | `/wizard/fr/road-accident/` (POST 35/5/0, review-gated) | 1280×900 |
| `france-result-review-gated-mobile-390.png` | `/wizard/fr/road-accident/` (POST) | 390×844 |
| `contact-desktop-1280.png` | `/contact/` | 1280×900 |
| `contact-mobile-390.png` | `/contact/` | 390×844 |

## How to reproduce

```bash
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
# In another shell:
.venv/Scripts/python.exe scripts/capture_product_1_france_signoff_pack.py
```

The capture script is also the reference smoke for the visual QA
the dev runs after the activation PR is opened (it can be
re-run against the activated state to produce the paired
*after-activation* captures).

## What to verify in the screenshots

- **No EUR amount** is visible anywhere on any page.
- The landing carries the "Preliminary legal assessment" badge
  (gold).
- Cited sources include Mornet 2024, Gazette du Palais 2022,
  Loi Badinter, Nomenclature Dintilhac.
- CTA to `/contact/` is visible on every France page.
- No dev-ese terminology ("scaffold", "placeholder", "engine
  pending", etc.) — copy lives in Studio register.

`apps/cases/test_product_1_france_signoff_pack.py` programmatically
asserts these contracts at the HTML level. The screenshots are
the visual companion that a human (Studio) can browse without
firing up the platform.
