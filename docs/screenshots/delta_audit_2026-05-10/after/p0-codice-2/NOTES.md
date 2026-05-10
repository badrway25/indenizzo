# Browser-live verification — P0-CODICE-2 batch (hreflang globale)

**Data:** 2026-05-10
**Branch:** `audit/indennizzati-platform`
**Server:** `http://127.0.0.1:64048/` (porta libera assegnata
runtime, runserver Django con `DJANGO_DEBUG=true`)
**Browser:** Playwright MCP (Chrome 130+), viewport 1440 × 900.

## Pre-check eseguiti

1. **Working tree pulito**: 11 modificati + 5 untracked pre-esistenti
   (Tunisia CSP + EU 650) stashati con label
   `pre-existing tunisia-csp-eu650 before p0-codice-2` (`stash@{0}`).
2. **Coerenza /contact/**: rimosso `{% block meta_robots %}noindex, nofollow{% endblock %}`
   da `templates/public/contact.html:5`. Ora `/contact/` eredita
   `index, follow` dal default di `base.html`. Coerente con
   `Allow: /contact/` in robots.txt e con la sua natura di pagina
   pubblica utile a SEO/lead.

## Risultati verifica P0-CODICE-2

### Pagine indicizzabili → 5 hreflang attesi (it, fr, en, ar, x-default)

| # | URL | hreflang count | langs | meta robots | OK |
|---|---|---|---|---|---|
| 1 | `/` (home) | 5 | it, fr, en, ar, x-default | `index, follow` | ✅ |
| 2 | `/contact/` (post pre-check 2) | 5 | it, fr, en, ar, x-default | `index, follow` | ✅ |
| 5 | `/countries/italy/` | 5 (no doppione) | it, fr, en, ar, x-default | inherit | ✅ |
| 6 | `/ar/` (RTL) | 5 | it, fr, en, ar, x-default | `index, follow`; `dir="rtl" lang="ar"` | ✅ |
| 7 | `/case-types/` | 5 | it, fr, en, ar, x-default | `index, follow` | ✅ |

### Pagine NOINDEX → 0 hreflang attesi

| # | URL | hreflang count | meta robots | OK |
|---|---|---|---|---|
| 3 | `/contact/thank-you/` | 0 | `noindex, nofollow` | ✅ |
| 4 | `/wizard/result/<uuid>/` | 0 | `noindex, nofollow` | ✅ |
| 8 | `/wizard/it/road-accident/` | 0 | `noindex, nofollow` | ✅ |

### Country IT — verifica no-duplicate

`hreflang_attr_count: 5` (non 10). Confermato: la rimozione
dell'iter `for alt in hreflang_alternates` da
`templates/public/country_landing.html` `head_extra` ha eliminato
il doppione che si sarebbe creato col nuovo `{% block hreflang %}`
in `base.html`.

## Esempio body hreflang (`/contact/`)

```html
<link rel="alternate" hreflang="it" href="http://127.0.0.1:64048/contact/">
<link rel="alternate" hreflang="fr" href="http://127.0.0.1:64048/fr/contact/">
<link rel="alternate" hreflang="en" href="http://127.0.0.1:64048/en/contact/">
<link rel="alternate" hreflang="ar" href="http://127.0.0.1:64048/ar/contact/">
<link rel="alternate" hreflang="x-default" href="http://127.0.0.1:64048/contact/">
```

## Screenshots

- `01_home_it_hreflang.png` — home IT con 5 hreflang.
- `02_contact_indexable_with_hreflang.png` — contact form ora `index, follow` + 5 hreflang.
- `03_thank_you_no_hreflang.png` — thank-you noindex, 0 hreflang.
- `04_wizard_result_no_hreflang.png` — result page noindex, 0 hreflang.
- `05_country_italy_no_duplicate_hreflang.png` — country landing IT con 5 hreflang (non 10).
- `06_home_ar_rtl_hreflang.png` — home AR/RTL con 5 hreflang.
- `07_case_types_hreflang.png` — case-types hub con 5 hreflang.
- `08_wizard_it_no_hreflang_noindex.png` — wizard IT noindex, 0 hreflang.

## Allowlist `_GLOBAL_HREFLANG_VIEW_NAMES`

In `apps/core/context_processors.py`:

- ✅ `core:home`, `core:methodology`, `core:disclaimer`,
  `core:privacy`, `core:countries`, `core:case_types`
- ✅ `core:country_italy/france/belgium/morocco/tunisia` (le view
  passano gia' `hreflang_alternates` dalla view; la allowlist
  documenta l'intento ed e' fallback)
- ✅ `cases:wizard_start`
- ✅ `crm:contact` (post pre-check 2)

**Esclusi volutamente**:
- 5 wizard pubblici (`cases:wizard_italy_road_accident`, ecc.) —
  noindex per scelta esistente; pagine di raccolta dati, non
  SEO-utili. La SEO va sulla country landing.
- `cases:wizard_result` (parametrico UUID).
- `crm:contact_thank_you` (post-submit).
- `/admin/`, `/staff/`, `/reports/` (back-office).

## Console errors

- `/robots.txt`: 1 console error per favicon non trovato
  (irrilevante per text/plain).
- altre pagine: 0 errors.
