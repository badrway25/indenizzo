# C1 Public Polish — landing-content / i18n cleanup — Plan

**Branch:** `feature/c1-public-polish-i18n-cleanup` (from `product/staging-readiness-p0` @ `750fa81`).
**Date:** 2026-06-22.

> Product/UX/i18n only. No engine/formula/amount/approved-source/source_version
> change; no new legal claim.

## 1. Residues found (audit)

The visible English on the **default Italian site** came from already
`gettext_lazy`-wrapped source strings that simply lacked an Italian translation
in the catalog (so Django rendered the English msgid):

- **`apps/core/case_type_landings.py`** — 111 `_()`-wrapped strings: per
  case-type `h1`, `meta_title`, `meta_description`, `intro`, `when_it_applies`
  bullets, and "what the Studio does" process steps, across all 8 case types
  (road-accident, bodily-injury, insurance-offer-review, work-injury,
  medical-malpractice, death-of-relative, foreigners-in-italy, cross-border).
- **`templates/partials/mandate_notice.html`** — the "Professional engagement"
  label + 2 `blocktranslate` paragraphs (shown on the result page).

Extracted via AST/template scan: **154 public msgids, 124 untranslated in IT**
(the rest were already-Italian FAQ source strings, which render fine).

## 2. What was NOT a residue

- Home, wizard, result range/confidence/disclaimer, methodology, privacy,
  footer/header chrome — already Italian (translated in earlier C1 work).
- The provenance block (H1-8) — already Italian.
- EN pages: the source IS English, so they render correctly with no work.

## 3. Strategy

- **IT (primary public language):** translate all 124 to professional Italian,
  faithfully and in the existing **indicative/disclaimered register** (no new
  claim, no figure invented), using a shared glossary for consistent legal
  terminology ("valutazione preliminare indicativa", "fonti legali validate",
  "non una garanzia di risultato", "senza alcun incarico automatico", "danno
  biologico", "responsabilità medica", etc.). Proper names kept verbatim
  (Tabella Unica Nazionale 2025, INAIL, ITT/ITP, DVR, CAI).
- **EN:** no work (source is English).
- **FR / AR:** left as a documented follow-up requiring Studio linguistic
  review — consistent with the project's standing rule that FR/AR legal-adjacent
  text awaits the Studio. The new msgids are present (untranslated) in the FR/AR
  catalogs, ready for that pass. The coverage floors for fr/ar are unchanged.

## 4. Coverage gate

IT real coverage rose from 47.9% to **58.8%** (645/1097). The CI gate floor is
raised `it=46 → it=56` to lock the gain (honest floor, margin for msgid churn).
fr/ar floors unchanged (35).

## 5. RTL / legal risk

- No template/layout change → no RTL regression; the AR pages render the same
  structure (AR landing copy stays English/source until the Studio pass — no new
  RTL risk introduced).
- No legal risk: translations are faithful to the existing indicative copy; no
  new promise, figure, or jurisdiction claim. Engines/datasets/provenance/canary
  untouched.

## 6. Not touched

Engines, formulas, amounts, approved datasets, source_version, official hashes,
FR/BE/MA/TN activation, sources. No DB data migration (the landing copy lives in
code as gettext strings, not in the DB).
