# Browser-live verification — P0-CODICE-4 batch (CSP)

**Data:** 2026-05-10
**Branch:** `audit/indennizzati-platform`
**Server:** `http://127.0.0.1:20984/` (`DJANGO_DEBUG=true`,
default CSP enforcing).
**Browser:** Playwright MCP (Chrome 130+).

## Header CSP osservato

Da `curl -sS -I http://127.0.0.1:20984/`:

```
Content-Security-Policy: connect-src 'self';
  script-src 'self' 'nonce-<random-per-request>';
  base-uri 'self';
  object-src 'none';
  font-src 'self' data: https://fonts.gstatic.com;
  frame-ancestors 'none';
  style-src 'self' https://fonts.googleapis.com 'nonce-<random-per-request>';
  img-src 'self' data: blob:;
  default-src 'self';
  form-action 'self'
```

Header **enforcing**, NON Report-Only. Nonce generato per request
(verificato: due GET consecutive → due nonce diversi, vedi
`apps/core/test_security_headers_csp.py::test_csp_nonce_changes_between_requests`).

## URL testate (tutte 1440 × 900)

| # | URL | Console errors (CSP) | Note |
|---|---|---|---|
| 1 | `/` | 0 (solo favicon 404) | header CSP presente, footer professionale visibile |
| 2 | `/contact/` | 0 | form indicizzabile (post pre-check P0-CODICE-2), inline `<style>` base.html con nonce |
| 3 | `/wizard/it/road-accident/` | 0 | inline `<script>` con nonce eseguito: `input.className` = "rounded-xl ..." (premium classes applicate) |
| 4 | `/wizard/result/<uuid>/` | 0 | full-page screenshot, range 26 268 / 27 353 / 28 439 EUR, noindex,nofollow |
| 5 | `/countries/italy/` | 0 | JSON-LD `application/ld+json` ha nonce, payload parsabile |
| 6 | `/ar/` | 0 | dir="rtl", lang="ar" |
| 7 | `/disclaimer/` | 0 | testo legale, footer professionale |
| 8 | `/wizard/ma/inheritance/` | 0 | inline `<script>` con nonce eseguito |

## Direttive temporanee motivate

**`style-src` include `https://fonts.googleapis.com`** e
**`font-src` include `https://fonts.gstatic.com`** — necessario
finche' Google Fonts non viene hostato localmente. Tracciato come
debito **P1-LEG-1** in `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md`
Sez. 4. Quando chiuso, rimuovere queste direttive.

NESSUN'altra deroga: niente `'unsafe-inline'`, niente `'unsafe-eval'`,
niente `'unsafe-hashes'`.

## Cambi al layer template

Per evitare di usare `'unsafe-inline'`:

1. **8 inline `<script>`** ora hanno `nonce="{{ CSP_NONCE }}"`:
   - `templates/partials/cookie_consent_banner.html`
   - `templates/public/_inheritance_wizard_fields.html`
   - `templates/public/wizard_italy_road_accident.html`
   - `templates/public/wizard_france_road_accident.html`
   - `templates/public/wizard_belgium_road_accident.html`
   - `templates/public/wizard_morocco_inheritance.html`
   - `templates/public/wizard_tunisia_inheritance.html`
   - `templates/public/country_landing.html` (JSON-LD)
2. **2 inline `<style>`** ora hanno `nonce`:
   - `templates/base.html`
   - `templates/admin/mfa_required.html`
3. **5 inline `style="..."` attributi** rimossi e sostituiti con
   classe utility `.is-honeypot` in `static/css/site.css`:
   - `templates/public/contact.html`
   - `templates/public/_inheritance_wizard_fields.html`
   - `templates/public/wizard_italy/france/belgium_road_accident.html`

## Eccezioni temporanee

Nessuna eccezione `'unsafe-inline'`/`'unsafe-eval'` necessaria.
Tutta la policy e' enforcing senza compromessi sui meccanismi
fondamentali di XSS protection.

## Test summary

- 28 nuovi test in `apps/core/test_security_headers_csp.py`: tutti
  verdi.
- Suite apps/crm + apps/core: 854 passed, 1 skipped.
- Suite globale: **1649 passed, 1 skipped, 0 failed** (artifact
  EU650 spostato fuori dal repo come da pre-check 0).

## Screenshots

- `01_home_csp_active_desktop.png`
- `02_contact_csp_active_desktop.png`
- `03_wizard_it_csp_inline_script_works.png` (premium input classes
  applied = JS eseguito sotto CSP)
- `04_wizard_result_csp_active.png` (full page)
- `05_country_italy_csp_jsonld_nonced.png`
- `06_home_ar_rtl_csp_active.png`
- `07_disclaimer_csp_active.png`
- `08_wizard_ma_inheritance_csp_inline_script.png`

## System check

- `manage.py check` (DEBUG=true, CSP_ENABLED=true, CSP_REPORT_ONLY=false):
  → 0 issues (oltre `core.W001` footer, separato).
- `manage.py check` (DEBUG=false, CSP_ENABLED=false):
  → `core.E002` Error blocca deploy.
- `manage.py check` (DEBUG=false, CSP_ENABLED=true, CSP_REPORT_ONLY=true):
  → `core.E003` Error blocca deploy.
- `manage.py check` (DEBUG=false, CSP_ENABLED=true, CSP_REPORT_ONLY=false):
  → 0 issues CSP-related.
