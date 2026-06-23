# C2 Public Multilingual Polish — FR/AR landing translation — Plan

**Branch:** `feature/c2-public-multilingual-polish-fr-ar` (from `product/staging-readiness-p0` @ `1771d38`).
**Date:** 2026-06-22.

> i18n / editorial / UX only. No engine/formula/amount/approved-source/
> source_version change; no new legal claim. FR/AR wording is **prudent and
> review-safe**, and still benefits from a Studio linguistic review before a
> public go-live.

## 1. Residues found (audit)

Same public surface as C1 (`apps/core/case_type_landings.py` + the mandate
notice), this time in the **FR and AR** catalogs: 154 public msgids, each
needing a French / Arabic translation. The English source rendered through on
the `/fr/` and `/ar/` landing pages.

### Key finding — fuzzy guesses + stale `.mo`

C1's `makemessages` had auto-filled ~15 (FR) / ~16 (AR) public msgids with
**fuzzy truncated guesses** (e.g. the per-case `meta_title` got the translation
of the shorter "Preliminary legal assessment", marked `#, fuzzy`). Two
consequences:
- `msgfmt` **excludes fuzzy entries** from the compiled `.mo`, so those strings
  would never render translated even once a translation exists.
- The committed `fr.mo` / `ar.mo` were **stale** (C1 refreshed the `.po` but did
  not recompile the FR/AR `.mo`), so the `<title>` on `/fr/` and `/ar/` actually
  rendered a left-over **Italian** string.

Both are fixed here (see §3).

## 2. Translation (review-safe wording)

- **French:** professional, prudent register — "évaluation préliminaire
  indicative", "sources juridiques validées", "ne constitue pas une consultation
  juridique complète", "n'emporte pas automatiquement mandat professionnel",
  "sous réserve d'une analyse du dossier", "sans garantie de résultat". No
  outcome promise; no invented French/Belgian rule; Italy/TUN content kept
  clearly indicative and source-bound.
- **Arabic:** professional, prudent MSA, RTL-correct — "تقييم أولي إرشادي",
  "مصادر قانونية موثّقة ومعتمدة", "لا يُعدّ استشارة قانونية كاملة", "لا ينشئ
  توكيلاً أو تكليفاً مهنياً تلقائياً", "يخضع لدراسة الملف والوثائق". Proper
  names / official references (Tabella Unica Nazionale 2025, INAIL, ITT, ITP,
  DVR, CAI) kept in Latin script. No absolute promise; no invented MA/TN rule.
- **EN / IT:** unchanged (EN source is correct; IT was completed in C1).

## 3. Implementation

- Translate the 154 public strings per language with a shared glossary
  (faithful, prudent); apply to `fr.po` / `ar.po`, **clearing the fuzzy / `#|`
  markers** so `msgfmt` keeps them.
- **Force-recompile** `fr.mo` / `ar.mo` (the stale binaries are deleted and
  rebuilt) so the translations actually render. Verified via `gettext()` per
  language and via the live pages.
- No template/layout change. AR keeps `dir="rtl"` / `lang="ar"`.

## 4. Coverage gate

FR real coverage 36.4% → **49.3%**; AR 36.4% → **49.3%**. The CI floors are
raised `fr=35 → fr=48`, `ar=35 → ar=48` to lock the gain.

## 5. RTL / legal risk

- AR pages keep `dir="rtl"` and `lang="ar"`; no layout change → no RTL
  regression. Verified on disclaimer + landing.
- Wording is prudent/review-safe; no new promise, figure or jurisdiction claim.
  Engines/datasets/provenance/canary untouched. FR/AR remain subject to a Studio
  linguistic review before public go-live.

## 6. Not touched

Engines, formulas, amounts, approved datasets, source_version, official hashes,
FR/BE/MA/TN activation, sources, IT/EN catalogs. No DB data migration.
