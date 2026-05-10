# Screenshot folder — `delta_audit_2026-05-10`

Questa cartella raccoglie gli screenshot **mirati** ai 15 casi della
matrice QA in `docs/QA_TEST_PLAN.md`. Quando l'utente esegue il piano,
deposita qui i PNG, uno per caso, secondo lo schema:

```
before/QA-01_italian_road_30pct_desktop.png
before/QA-01_italian_road_30pct_mobile.png
before/QA-02_moroccan_pedestrian_no_docs_desktop.png
before/QA-03_family_abroad_wrongful_death_desktop.png
before/QA-04_insurance_offer_already_received_desktop.png
before/QA-05_inail_already_paid_desktop.png
before/QA-06_late_diagnosis_desktop.png
before/QA-07_french_belgian_cross_border_desktop.png
before/QA-08_arab_user_rtl_morocco_inheritance.png
before/QA-09_form_spam_attempt_desktop.png
before/QA-10_oversized_upload_desktop.png   (riservato P3 — area cliente futura)
before/QA-11_invalid_calculator_inputs_desktop.png
before/QA-12_mobile_safari_390_results_page.png
before/QA-13_slow_3g_connection_desktop.png
before/QA-14_no_javascript_desktop.png
before/QA-15_crm_webhook_failure_desktop.png   (riservato P1 — webhook futuro)
```

`notes/` contiene osservazioni testuali per casi che richiedono spiegazione
oltre allo screenshot (es. log Django snippet, network tab Chrome).

## Convenzioni

- Risoluzione desktop: **1440 × 900**.
- Risoluzione mobile (Safari-like): **390 × 844** (iPhone 13).
- Tablet: **768 × 1024** (iPad portrait), opzionale per casi dove
  cambia layout.
- Browser: Chrome 130+ (Playwright MCP) per consistenza; Safari
  Mobile reale solo per QA-12 se possibile.
- Flash dei flussi: per ogni caso, screenshot a 3 momenti chiave
  (form-pre-submit, post-submit-loading o errore, result o
  thank-you), con suffisso `_step1`, `_step2`, `_step3`.
- File naming: `QA-NN_short-slug_viewport.png`.
- PII fittizia: usare nomi/email del catalogo Sez. 3 di
  `QA_TEST_PLAN.md`, mai dati reali.

## Esistono già screenshot riusabili?

Sì, in larga parte:

- `docs/screenshots/live_qa/release_readiness_audit_pass1/after/`:
  78 frame coprono home/wizard/result/contact/disclaimer in 4 lingue
  (IT/FR/EN/AR) + RTL + mobile 375px. **Riusare** quando il caso
  QA non aggiunge nulla di nuovo.
- `docs/screenshots/live_qa/country_landing_pass4/`:
  Open Graph + RTL Morocco.
- vari `docs/screenshots/live_qa/<iter_name>/`.

I casi 1-15 della matrice cercano specificamente situazioni *non*
coperte dai pass precedenti (utente straniero, errori, edge case,
mobile Safari real). Se un caso *è* già coperto, citare il path
esistente in `notes/QA-NN.md` invece di duplicare lo screenshot.
