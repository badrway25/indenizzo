# Public i18n catalog leak fix — QA report

**Branch:** `feature/p3-public-ux-redesign` · **Date:** 2026-06-24 · **Scope:** translation catalogs only (additive, fail-closed untouched).

## 1. Problem (from P1 §11/§15 and P3 deferred)

Both the P1 reality audit and the P3 QA flagged English/Italian text leaking
onto translated public pages (most visibly the `_documents_to_prepare.html`
partial: "Documents to prepare", "What the Studio will do", "While you wait…").

Root cause, confirmed by inspection: **the strings are correctly wrapped in
`{% translate %}` / `{% blocktranslate %}` — the leak is a catalog gap.** The
`msgstr` entries were empty (or `#, fuzzy`, which `msgfmt` skips at compile time),
so Django fell back to the English `msgid`. Because `LANGUAGE_CODE = "it"`, several
of these even leaked English onto the **Italian** default pages.

Two sub-problems were found:

1. **In catalog but untranslated** — public-facing `msgstr` empty/fuzzy:
   IT **21**, FR **113**, AR **113** (FR and AR share the identical msgid set).
2. **Not in the catalog at all** — the premium wizard stepper strings
   (`Simulation progress`, `Country & case`, `Your details`, `Result`) were added
   to `templates/partials/_premium_stepper.html` without re-extraction, so they
   leaked English in **every** language.

## 2. What was done

- **Translated all public-facing leaks** in IT / FR / AR (documents-to-prepare
  partial, disclaimer §1–9, privacy policy §1–9, result-page calculation labels,
  footer professional-identification labels, contact prefill, methodology meta,
  legal-version UI). House style preserved: IT "lo Studio"/"avvertenze";
  FR "le Cabinet"/"avertissement"/"fourchette indicative"; AR "المكتب"/"إخلاء
  المسؤولية"/"إرشادي".
- **Appended the 4 stepper strings** to it/fr/ar catalogs (translated). They were
  added surgically rather than via `makemessages`, because the catalogs are in an
  inconsistent location-comment state (`en` carries 880 `#:` lines; it/fr/ar carry
  none), so a full re-extraction would have churned hundreds of unrelated lines.
- **Fixed a pre-existing mis-merge** discovered during placeholder integrity
  checking: the Italy-wizard `<meta description>` msgid (no placeholder) carried a
  generic `%(country)s` country-landing translation in all three locales. Django's
  `blocktranslate` caught the resulting `KeyError` and silently fell back to
  English in the `<head>`. Replaced with the correct, placeholder-free translation.
- **Corrected wrong fuzzy auto-merges** (e.g. FR "Bar association" → was
  "Navigation principale"; "VAT number" → was "Téléphone"; "Working copy" → was
  "Accident du travail"). Fuzzy flags and stale `#| msgid` previous-source lines
  were stripped for every entry touched.

Method: a tested in-place `.po` patcher (empty-fill + fuzzy-fix + append), keyed by
exact msgid to avoid typo-induced duplicate entries. AR was keyed to the shared
English msgids and **alignment-spot-checked** after applying (0 mismatches).

## 3. Results

| Locale | Public leaks before | Public leaks after | Coverage before → after |
|---|---:|---:|---|
| IT | 21 (+4 not-in-catalog) | **0** | 58.9% → **61.0%** |
| FR | 113 (+4) | **0** | 49.5% → **59.9%** |
| AR | 113 (+4) | **0** | 49.5% → **59.9%** |

Placeholder integrity: **0 mismatches** in all three catalogs (every `%(…)s`
preserved). `msgfmt --check` clean for all three. Catalog entry counts intact
(1101 → 1105; only the 4 stepper strings appended, none lost).

## 4. Tests

- `manage.py check` — clean (only the pre-existing `STUDIO_*` go-live warning).
- `makemigrations --check` — no changes.
- `verify_calculation_provenance --canary --fail-on-drift` — **exit 0**,
  IT 35/10/0 → 26.268 / 27.353 / 28.439 € reproducible (engines untouched).
- `compilemessages` — OK; `.mo` recompiled for it/fr/ar.
- `check_po_coverage --min it=30 --min fr=30 --min ar=30` — all OK, all risen.
- **Full suite: 2419 passed, 1 skipped** (matches the prior P3 baseline).
- 3 tests updated (they had asserted English strings that only appeared via the
  leak; now assert the Italian copy the default locale actually renders):
  `test_meta_description_overridden_pass2[/methodology/]`,
  `test_result_page_includes_documents_to_prepare`,
  `test_thank_you_includes_while_you_wait_block`.

## 5. Browser / HTTP QA (live server, port 8780)

**Real browser screenshots (desktop 1440):**

- **FR `/fr/disclaimer/`** — "MENTIONS LÉGALES / Avertissement", working-copy badge,
  sections "1. Caractère informatif / 2. Aucun conseil juridique automatisé /
  3. Aucune garantie de résultat", French cookie banner. Clean cards, no overflow,
  no English residue.
- **AR `/ar/disclaimer/`** — `lang="ar" dir="rtl"`, layout fully mirrored (logo
  right, CTA left, nav RTL); "إخلاء المسؤولية", sections "١. الطابع الإعلامي /
  ٢. لا استشارة قانونية آلية / ٣. لا ضمان للنتيجة"; Arabic cookie banner. No overflow.
- **FR `/fr/contact/thank-you/`** — the documents-to-prepare partial (the #1 cited
  leak): "DOCUMENTS À PRÉPARER / En attendant notre réponse" + four French checklist
  bullets (Rapports médicaux / Éléments relatifs à l'accident / Correspondance avec
  les assurances / Justificatifs de l'impact économique). Gold dots, contained card.
- **AR `/ar/contact/thank-you/`** — "تم استلام طلبك." with the "3–5 أيام عمل" en-dash
  preserved, the professional-mandate working-copy block, "المستندات المطلوب تحضيرها".
  Correct RTL mirroring, no overflow, no English.
- **Console: 0 errors / 0 exceptions** on the pages checked (no JS/CSP impact — no
  JS/template/CSS changed).

**HTTP render grep (all locales):** FR/AR methodology 0 "How we work"/"validation
lifecycle" residue; FR/AR disclaimer 0 English section markers; documents-to-prepare
translated in it/fr/ar; wizard `<meta description>` renders the corrected
placeholder-free copy; IT wizard stepper renders "Paese e tipo di caso / I tuoi
dati / Risultato".

> ⚠️ **Mobile 390px could not be captured** with the available Chrome automation
> (the window enforces a ~1568px minimum effective width). Compensating evidence:
> the change is **text-only** (no layout/CSS/template change), so the responsive
> containers are unchanged; the green `lighthouse-mobile` + responsive test suites
> and the prior P3 mobile-390 QA cover layout. The translated strings are normal
> prose that reflows inside existing `max-w-*` cards (no new unbreakable long tokens).
> A manual eyes-on mobile pass is still recommended per the team's standing QA rule.

## 6. Residual risks / human decisions

- ⚠️ **AR is a working translation pending native-speaker / Studio legal sign-off.**
  The MSA is professional and placeholder-safe, but the disclaimer and privacy
  texts are legally sensitive (and already carry the in-page "working copy" banner).
  **Do not raise the AR coverage floor to treat it as final** until a native legal
  review is filed. FR was done to production quality; IT is the primary market.
- **Out of scope (unchanged):** `en` catalog (default-locale fallback already shows
  English correctly), the ~370 non-public/admin msgids still untranslated per
  locale, the `STUDIO_*` footer legal identity (needs the firm's real data), and
  the consent-text legal sign-off. None are user-facing public leaks.
- **Coverage floors** (`check_po_coverage`) were left at 30 — consider raising the
  IT/FR floors now that public surfaces are fully covered, to prevent regressions.

## 7. Files changed

- `locale/{it,fr,ar}/LC_MESSAGES/django.po` + `django.mo` (translations only).
- `apps/crm/test_product_2_lead_funnel.py`,
  `apps/core/test_public_site_qa_polish_pass2.py` (assert the now-translated copy).

No engine, dataset, formula, source_version, hash, template, view, migration, or
`legal_data` change. Fail-closed governance and the IT TUN canary are intact.
