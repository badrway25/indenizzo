# Public site — release polish pass 5 (premium content cleanup)

Iter: F-product-public-site-release-polish-pass5-premium-content-cleanup.
Date: 2026-05-04.

Scope: rinse the public site of technical / "scaffold" wording and
replace it with premium, client-ready copy across IT/FR/AR/EN. **No**
changes to legal data, calculator engines, country activation status
or Italian dataset.

## 1. what got removed

The pass-5 hygiene audit
(`scripts/audit_public_content_hygiene.py`) walked every principal
public page in IT/FR/AR/EN (72 page renders) and flagged the
following banned wording in visible body text:

- "scaffold" — leaked into 27 visible texts (country cards, wizard
  cards, banners, meta descriptions).
- "in preparation" — leaked into the EN-locale countries / case-types
  pages.
- "Internal status code: unavailable_requires_legal_validation" —
  leaked into the FR (and any other) unavailable result page.
- "Module under legal validation — no automatic estimate." — banner
  copy on FR/BE wizard scaffolds.
- "Module under legal validation — no automatic shares computed." —
  banner copy on MA/TN wizard scaffolds.
- "Open France/Belgium validation wizard" — country-landing CTA.
- "Coming soon" disabled span — wizard start "else" tile.
- "Modules for this country are being prepared." — country card
  body.
- Various "wizard is in scaffold mode" / "calculator engine is in
  scaffold mode" / "in scaffold mode" / "validation wizard" strings.

Banned policy:
``scaffold | placeholder | under validation | in preparation |
coming soon | work in progress | in corso | modulo non operativo |
legal validation wizard | module pending | engine pending |
missing_documents | unavailable_requires_legal_validation``.

After pass-5 the audit returns
**`pages_with_issues=0`** — verdict OK on all 72 renders.

## 2. new public labels

| Internal status flag | Label | Description |
| --- | --- | --- |
| Italy today (calculator approved) | `Indicative calculation available` | "An indicative calculation is available, based on the verified national dataset for this country. The Studio remains available to review the case and discuss the next step." |
| FR / BE road-accident scaffolds | `Preliminary legal assessment` | "The Studio offers a preliminary legal assessment for this country: each case is reviewed manually and no automatic amount is published before the underlying quantification sources have been verified." |
| MA / TN inheritance scaffolds | `International inheritance review` | "The Studio reviews each inheritance case manually; inheritance shares are not computed automatically without an applicable-law mapping for the case." |
| Anything not yet wired (no public flow) | `Manual legal review` | "The Studio offers a manual legal review for this country on request, while the national quantification dataset is being verified by our team." |

The canonical copy for these statuses is centralised in
`apps/core/public_status.py` (with `gettext_lazy` strings), so future
templates / views can pull from a single source.

CTA labels:

- `Submit the case to the Studio` (was: "Open validation wizard").
- `Submit a France case to the Studio` / `Submit a Belgium case to
  the Studio` (was: "Open France validation wizard").
- `Request a manual legal review` (was: "Coming soon" disabled).

## 3. translations applied

`makemessages -l it -l fr -l en -l ar` extracted ~42 new pass-5
msgids; a force-replace script wrote IT/FR/AR translations in one
pass and stripped any msgmerge fuzzy hints. Sensitive legal terms
were NOT translated creatively — they remain verbatim in IT/FR/AR:
**Mornet**, **Gazette du Palais**, **Loi Badinter**, **Moudawana**,
**Code du statut personnel**, **Loi 98-97**, **EU Regulation
650/2012**.

After `compilemessages`, the FR and AR pages render full translated
copy (e.g. `/fr/countries/` shows
"Évaluation juridique préliminaire" and `/ar/countries/` shows
"تقييم قانوني أولي").

## 4. live funnel smoke

Live POSTs against `http://127.0.0.1:48107/`:

| Step | Result |
| --- | --- |
| GET `/wizard/it/road-accident/` | 200 + CSRF + cookie OK |
| POST IT 35/10/0 → result page | amounts present: `26268`, `27353`, `28439` |
| GET `/reports/simulation/<id>/pdf/` | PDF magic `%PDF-` ✓ |
| POST FR road-accident → unavailable result | no monetary amounts leak; no banned wording |

The "Internal status code: unavailable_requires_legal_validation"
line was removed from the unavailable card in `wizard_result.html`;
the new copy reads:

> Your case has been received — the Studio will reply with a
> preliminary legal assessment.
>
> For this jurisdiction and case type, a lawyer of the Studio
> reviews each submission manually rather than publishing an
> automatic amount. We will reply directly with the next step
> (applicable law, competent jurisdiction, documents to gather).

## 5. screenshots (live)

20 PNGs in
`docs/screenshots/live_qa/public_release_polish_pass5/`, three sets:

- `desktop__*.png` — 8 pages at 1440 × 900.
- `mobile__*.png` — 6 pages at 375 × 800.
- `locale__*.png` — 6 FR / AR variants at 1280 × 900.

Captured by
`scripts/capture_public_release_polish_pass5_screenshots.py`.

## 6. files changed

**Created**

- `apps/core/public_status.py` — premium status helper module.
- `scripts/audit_public_content_hygiene.py` — re-runnable hygiene
  audit across IT/FR/AR/EN.
- `scripts/capture_public_release_polish_pass5_screenshots.py` —
  Playwright capture for the visual QA set.
- `apps/cases/test_public_release_polish_pass5.py` — 12 tests / 49
  parametrized runs.
- `docs/architecture/PUBLIC_CONTENT_HYGIENE_AUDIT_PASS5.md` — current
  hygiene audit report (regenerated by the audit script).
- `docs/architecture/PUBLIC_RELEASE_POLISH_PASS5.md` — this document.
- `docs/screenshots/live_qa/public_release_polish_pass5/` — 20 PNGs.

**Modified (templates)**

- `templates/public/countries.html`
- `templates/public/country_landing.html`
- `templates/public/case_types.html`
- `templates/public/wizard_start.html`
- `templates/public/wizard_france_road_accident.html`
- `templates/public/wizard_belgium_road_accident.html`
- `templates/public/wizard_morocco_inheritance.html`
- `templates/public/wizard_tunisia_inheritance.html`
- `templates/public/wizard_result.html`

**Modified (locales)**

- `locale/{it,fr,ar,en}/LC_MESSAGES/django.{po,mo}`

## 7. residual / next step

- The home page (`templates/public/home.html`) was already premium
  in pass-3 / pass-4 and was not touched in pass-5.
- Status copy is centralised in `apps/core/public_status.py` but
  templates still inline the same wording as `{% translate %}`
  strings; both pull from the same catalogue, so the centralisation
  is for future use rather than a breaking refactor.
- A future iter can wire `apps/core/public_status.py` into the
  context of `country_landing.html` and `wizard_*.html` so the
  badge label / no-amounts disclaimer are read from the dict instead
  of being inlined per template.

## 8. validation

- `python manage.py makemigrations --check` — no new migrations.
- `python manage.py check` — 0 issues.
- `python manage.py compilemessages -l it -l fr -l ar -l en` — clean.
- `pytest -q` — green (1064 + 49 new = 1113 tests).
- `ruff check .` — clean.
- `black --check .` — clean.
- `python scripts/audit_public_content_hygiene.py` — verdict OK.
- Lighthouse / Playwright fallback audit — all 8 audited URLs
  PASS at desktop and mobile viewports.

## 9. summary

| Verdict | Detail |
| --- | --- |
| Hygiene audit | OK on all 72 renders (IT/FR/AR/EN × 18 paths). |
| Italia | 35/10/0 → 26 268 / 27 353 / 28 439 EUR — unchanged (smoke test passing). |
| Other countries | FR/BE/MA/TN remain inactive on calculation; banner copy is now premium. |
| Server | Live on `127.0.0.1:48107`. |
| Tools added | hygiene audit, screenshot capture, status helper, 49 pass-5 tests. |
