# P36 — Premium Visual Acceptance Audit (2026-06-29)

Browsed as an ordinary client on the P36 build (navy navbar shell + premium forms from
P35 + the new home intent section). Scores 1–5 (5 = excellent). Pages below 4 were
addressed in this phase; remaining gaps are listed honestly at the end.

## Per-page scores

| Page | Beauty | Simplicity | Images | Navbar | Forms | Buttons | Type | Cards | Motion | Mobile | RTL | Trust |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Home | 4.5 | 4.5 | 4.5 | 4.5 | – | 4.5 | 4 | 4.5 | 4 | 4 | 4.5 | 5 |
| Documents upload | 4.5 | 4.5 | 5 | 4.5 | 4.5 | 4.5 | 4 | 4.5 | 4 | 4 | 4.5 | 4.5 |
| Contact (lead) | 4 | 4.5 | 4 | 4.5 | 4.5 | 4.5 | 4 | 4 | 3.5 | 4 | 4.5 | 4.5 |
| Precheck (form) | 4 | 4 | 4 | 4.5 | 4.5 | 4.5 | 4 | 4 | 3.5 | 4 | 4.5 | 4.5 |
| Sources | 4 | 4 | 4.5 | 4.5 | 4 | 4.5 | 4 | 4 | 4 | 4 | 4.5 | 5 |
| Case-types | 4.5 | 4 | 4.5 | 4.5 | – | 4.5 | 4 | 4.5 | 4 | 4 | 4.5 | 4.5 |
| Arabic home (RTL) | 4.5 | 4.5 | 4.5 | 4.5 | – | 4.5 | 4 | 4.5 | 4 | 4 | 5 | 5 |

## What changed in P36 (the visible leaps)
- **Home "What would you like to do?" intent section** — 4 premium image cards (gold
  balance scales, contract, tidy desk, globe) with gold medallion icons, simple human
  copy ("Fai una stima / Controlla un'offerta / Carica documenti / Quale legge si
  applica") and "Apri →" CTAs. Slow-zoom on hover, staggered reveal. This is the first
  thing a normal visitor sees below the hero and answers "what can I do here?" instantly.
- **New professional Pexels imagery** in those sections (validated, no people/kitsch).
- Icon medallions reworked so the glyph is never clipped by the image overflow.
- Navy navbar shell + premium forms (from P35) confirmed across desktop + RTL.

## Honest remaining gaps (not fully done this phase)
- **Navbar mega-menu panels with per-item icons** (Fase C): the dropdowns are clean
  text lists on a light panel; not yet icon-rich multi-column panels.
- **Imagery on every remaining section** (services cards, result page bodies): the home
  intent section + heroes are image-rich; some inner-page bodies are still text+cards.
- **New monetary estimates** (Fases L/M/N): **not activated** — see
  `P36_ESTIMATE_COVERAGE_AND_OFFICIAL_SOURCES_2026-06-29.md`. The candidate sources
  (INAIL D.M. 45/2019, Morocco Dahir/ACAPS, Tunisia barème) are `approval_needed`, so a
  figure would mean inventing unvalidated coefficients — forbidden by the platform's
  first rule. Pre-check/dossier remains the correct path.
- True 390 px mobile viewport is not capturable in this environment; verified via
  responsive CSS + RTL.

## Definition of done (met for the items in scope)
Home reads premium + human; the intent section is image-rich with visible icons; forms
are premium with separated actions; navy navbar is distinct; copy is simple; 0 site
console errors; no money on engine-less pages; i18n 0 fuzzy; RTL verified.
