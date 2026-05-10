# Browser-live verification — P0-CODICE-3 batch (footer professionale)

**Data:** 2026-05-10
**Branch:** `audit/indennizzati-platform`
**Browser:** Playwright MCP (Chrome 130+).

## Risultati verifica

### Footer EMPTY (env vars NON settate)

Server: `runserver` con `DJANGO_DEBUG=true` (sole env var di default).
Porta: 23723.

| # | Path | Viewport | Sezione presente | Placeholder visibili |
|---|---|---|---|---|
| 1 | `/` | 1440 × 900 | ✅ "Professional identification" | 6 (su 6 macro-aree) |
| 2 | `/fr/` | 1440 × 900 | ✅ heading invariato | 6 |
| 3 | `/ar/` | 1440 × 900 RTL (`dir="rtl" lang="ar"`) | ✅ | 6 |
| 4 | `/` | 390 × 844 (mobile) | ✅ stack 1-col | 6 |

Placeholder pattern: `[da configurare prima del go-live]` in
giallo/amber, visibile per ogni campo non valorizzato. Lo Studio
vede subito cosa manca.

### Footer POPULATED (env vars settate)

Server: `runserver` con tutte le `STUDIO_*` env settate (vedi
NOTES sotto). Porta: 54398.

| # | Path | Viewport | placeholder | Lawyer rendered |
|---|---|---|---|---|
| 5 | `/` | 1440 × 900 | 0 | "Avv. Test Demo" ✅ |
| 6 | `/` | 390 × 844 (mobile) | 0 | "Avv. Test Demo" ✅ |

Tutti i 10 campi (`STUDIO_LEAD_LAWYER_NAME`, `STUDIO_BAR_ASSOCIATION`,
`STUDIO_BAR_REGISTRATION_NUMBER`, `STUDIO_VAT_NUMBER`,
`STUDIO_TAX_CODE`, `STUDIO_PEC_EMAIL`, `STUDIO_PHYSICAL_ADDRESS`,
`STUDIO_PROFESSIONAL_INSURANCE_INSURER`,
`STUDIO_PROFESSIONAL_INSURANCE_POLICY`,
`STUDIO_PROFESSIONAL_INSURANCE_CEILING`) sono renderizzati al posto
del placeholder.

## Demo env vars usate (NON dati reali)

```bash
STUDIO_LEAD_LAWYER_NAME="Avv. Test Demo"
STUDIO_BAR_ASSOCIATION="Ordine degli Avvocati di Milano"
STUDIO_BAR_REGISTRATION_NUMBER="A12345"
STUDIO_VAT_NUMBER="IT12345678901"
STUDIO_TAX_CODE="DEMOXX99X99X999X"
STUDIO_PEC_EMAIL="studio.demo@pec.it"
STUDIO_PHYSICAL_ADDRESS="Via Demo 1, 20100 Milano, Italia"
STUDIO_PROFESSIONAL_INSURANCE_INSURER="Generali Assicurazioni S.p.A."
STUDIO_PROFESSIONAL_INSURANCE_POLICY="POL-DEMO-2026-0001"
STUDIO_PROFESSIONAL_INSURANCE_CEILING="EUR 2.500.000"
```

> **DA VALIDARE STUDIO**: i valori reali dovranno essere forniti
> prima del go-live (env var di produzione). Lo Studio fornisce
> i dati ufficiali (Foro reale, P.IVA reale, polizza reale, ecc.).
> Mai dati inventati nel repo.

## System check verification

- `manage.py check` con `DJANGO_DEBUG=true` (env vuote):
  → `core.W001` Warning consolidato (non blocca dev).
- `manage.py check` con `DJANGO_DEBUG=false` (env vuote):
  → 7 `core.E001` Error (uno per campo obbligatorio mancante)
  + `crm.E001` (LEAD_NOTIFICATION_TO_EMAILS) → blocca deploy.
- `manage.py check` con `DJANGO_DEBUG=false` + tutte le STUDIO_* settate
  + `LEAD_NOTIFICATION_TO_EMAILS=lead@...`:
  → 0 issues, deploy permesso.

## Test summary

- 15 nuovi test in `apps/core/test_studio_identification.py`: tutti
  verdi.
- Suite apps/crm + apps/core: 826 passed (+15), 1 skipped.
- Suite globale (escluso fail EU650 isolato in branch
  `work/tunisia-csp-eu650-restore`): 1613 passed, 1 skipped.

## Screenshots

- `01_footer_empty_placeholder_desktop_it.png` (full page)
- `02_footer_empty_placeholder_desktop_fr.png` (full page)
- `03_footer_empty_desktop_ar_rtl.png` (full page, RTL)
- `04_footer_empty_mobile_390_it.png` (full page)
- `05_footer_populated_desktop_it.png` (full page)
- `06_footer_populated_mobile_390_it.png` (full page)

## Console errors

- Una sola favicon-not-found console error (irrilevante).
- Nessun errore funzionale.
