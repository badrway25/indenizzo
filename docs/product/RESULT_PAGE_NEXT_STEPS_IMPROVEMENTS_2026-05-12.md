# Result-page next-steps improvements — 2026-05-12

**Iter**: `PRODUCT-5-result-page-next-pages`
**Branch**: `product/result-page-next-pages`
**Companion of**: `docs/product/RESULT_PAGE_NEXT_STEPS_AUDIT_2026-05-12.md` (phase 1 audit).
**Verdict**: shipped — case-type-aware recommendation section on the wizard result page, data-driven, deontologically clean.

## 1. What was added

A new section on `/wizard/result/<uuid>/`:

> **Useful pages for your case**
> Read more before requesting a review
>
> These pages describe the kinds of cases the Studio handles and what to prepare. They are informational; they do not replace the legal review you can request below.
>
> — 1-3 informational cards linking to the PRODUCT-4 case-type landings most relevant to the simulation's `case_type`.

The section appears:

- **After** disclaimer + mandate notice.
- **Before** simulation ID + timestamp + primary CTAs.

So the primary CTA ("Request legal review" with `?sim=<uuid>`) remains the last and strongest action on the page; the recommendations are a soft on-ramp for users not yet ready to write the case.

## 2. case_type → recommended landings mapping

Data-driven, lives in `apps.core.case_type_landings._RECOMMENDATIONS_BY_CASE_TYPE`. Capped at 3 per result page. Ordered: most-relevant first.

| Simulation `case_type` | Recommended landings (in order) |
|---|---|
| `road_accident_bodily_injury` | bodily-injury, insurance-offer-review, cross-border-cases |
| `medical_malpractice` | medical-malpractice, insurance-offer-review |
| `work_injury` | work-injury, insurance-offer-review |
| `death_compensation` | death-of-relative, cross-border-cases |
| `parental_loss` | death-of-relative |
| `international_inheritance` | cross-border-cases, foreigners-in-italy |
| `inheritance_basic` | cross-border-cases |
| `generic_legal_assessment` | insurance-offer-review, cross-border-cases |
| `patrimonial_damage` | insurance-offer-review, cross-border-cases |
| *unmapped / empty* | section silently omitted |

A sync-guard test ensures every slug in this mapping resolves to a real `CaseTypeLanding` — protects against future drift between PRODUCT-4's `LANDINGS` and PRODUCT-5's recommendation table.

## 3. Impact expected

- **Lower bounce on the result page**: users who are not yet ready to submit a contact have a structured second action ("read more about this kind of case") that keeps them inside the funnel.
- **Better-qualified contact submissions**: a user who first reads `/case-types/insurance-offer-review/` arrives at the contact form with the right mental model and the right documents in mind.
- **Stronger internal linking**: each result page now adds 1-3 internal links to high-intent landings, improving site coherence (the result page itself is `noindex`, but the recommendations are crawlable destinations).
- **Per-case-type personalisation**: a road-accident user no longer sees the same generic "next steps" as a medical-malpractice user. Studio handles them differently; the platform now reflects that.

Calculator output is **unchanged**. Mandate notice + disclaimer + primary CTA are **unchanged**. The new section is purely additive.

## 4. Files modified / created

| File | Change |
|---|---|
| `apps/core/case_type_landings.py` | Added `_RECOMMENDATIONS_BY_CASE_TYPE` mapping + `get_recommended_landings(case_type)` helper + `RESULT_PAGE_RECOMMENDATION_LIMIT = 3` constant. No new dataclass fields — recommendations reuse the existing `CaseTypeLanding` entries from PRODUCT-4. |
| `apps/cases/views.py` | `wizard_result()` now resolves the simulation's `case_type` via the helper and injects `recommended_landings` into the template context. ~5 LOC. |
| `templates/public/wizard_result.html` | New `{% if recommended_landings %}` section between the mandate notice and the simulation meta / CTAs. ~20 LOC. Uses the landing's `h1` as the card label + a translatable read-more hint (no English fallback risk on /fr/ /ar/). |
| `apps/cases/test_product_5_result_page_next_pages.py` *(new)* | 22 tests: audit doc + mapping + helper + per-case-type expected slugs + capping + sync guard + result-page renders the section for IT/FR + contact CTA preserved + recommended links resolve 200 + no banned phrases + noindex preserved + unmapped omits silently + AR/RTL renders. |
| `scripts/capture_product_5_result_page_next_pages.py` *(new)* | Playwright harness: IT result + a recommended landing + contact-linked + FR review-gated result, at desktop + mobile. |
| `docs/product/RESULT_PAGE_NEXT_STEPS_AUDIT_2026-05-12.md` *(new)* | Phase 1 audit. |
| `docs/product/RESULT_PAGE_NEXT_STEPS_IMPROVEMENTS_2026-05-12.md` *(new)* | This file. |
| `docs/screenshots/.../after/product-result-page-next-pages/` *(new)* | 8 PNGs documenting the new section across IT/FR × desktop/mobile. |

No model migration. No new form. No France activation. No CRM / webhook / email change. No banned-phrase introduction. No new template, only an extension of the existing result template.

## 5. Deontological / GDPR / SEO — what stays clean

| Risk | How addressed |
|---|---|
| Promise of result | None. New copy is informational ("These pages describe the kinds of cases the Studio handles and what to prepare. They are informational; they do not replace the legal review you can request below.") |
| EUR amount in new section | None. Test pin: no EUR pattern in any result-page body after the change (for both IT estimate path AND FR review-gated path). |
| Banned marketing phrases | None. Test pin: 7-phrase banned list scanned, zero matches. |
| France activation | None. The FR result page still publishes no EUR amount. The new section appears on FR result pages with FR-relevant recommendations, but those are links to read-only case-type landings — not calculations. |
| `noindex, nofollow` regression | Preserved. The result page stays a parametric per-user page excluded from search. Test pin asserts `content="noindex, nofollow"` is still in the rendered HTML. |
| Empty section for unmapped case_type | Silently omitted. Test pin sets `simulation.case_type = "__unmapped__"` and asserts the section is NOT in the rendered HTML. |
| Injection from `simulation.case_type` value | `_RECOMMENDATIONS_BY_CASE_TYPE.get(case_type, ())` returns empty tuple for any unknown key. No SQL, no template injection. |
| AR / RTL regression | Test pin asserts `/ar/wizard/result/<uuid>/` returns 200 with `dir="rtl"`. |

## 6. Tests

| Suite | Before | After |
|---|---|---|
| Full `pytest -q` | 2068 passed, 1 skipped | **2090 passed, 1 skipped** (+22 new PRODUCT-5) |
| `apps/cases/test_product_5_result_page_next_pages.py` | n/a | 22/22 passed |
| `python manage.py check` | clean (only W001 STUDIO_* dev) | unchanged |
| `python scripts/legal_data/audit_non_it_readiness.py` | APPROVED-PARTIAL × 4 | APPROVED-PARTIAL × 4 |
| `python scripts/audit_legal_content_hygiene.py --strict` | no findings | no findings |

## 7. Screenshots

`docs/screenshots/delta_audit_2026-05-10/after/product-result-page-next-pages/`
contains 8 PNGs:

- IT result desktop + mobile (new section visible above CTAs)
- IT bodily-injury landing (the page reached via one of the recommendations) desktop + mobile
- Contact form linked from result with `?sim=<uuid>` desktop + mobile
- FR review-gated result page with recommendations desktop + mobile

Visual check confirmed:

- The new "Useful pages for your case" card sits between the mandate notice and the simulation ID — exactly where the audit said it should.
- Three soft read-more links, no aggressive CTAs.
- Primary CTA ("Request legal review") still the last/strongest action below.
- FR review-gated path shows the section + zero EUR amount.

## 8. Residual risks

| Risk | Severity | Mitigation |
|---|---|---|
| Recommendation copy ("Read more before requesting a review") uses new translatable strings not yet in .po files | low | English fallback on /fr/ and /ar/ is acceptable on `/wizard/result/<uuid>/` because the page is `noindex, nofollow` (not crawlable). The translation team picks up the new strings in the next .po cycle. |
| Three cards may stretch the result page on mobile | low | Mobile screenshot confirms layout works; cards stack naturally. Cap at 3 keeps the page from sprawling. |
| Studio may want to refine the mapping (e.g. add a 4th recommendation for road-accident) | low — easy follow-up | One-dict edit in `case_type_landings.py`. No template / view change. |
| Inheritance simulations today (MA / TN) are review-gated and use `international_inheritance` — the recommendation set (cross-border-cases + foreigners-in-italy) is on point but Studio may want a dedicated `/case-types/inheritance/` landing | low | Easy to add: append a new `CaseTypeLanding` entry to `LANDINGS` + map it in `_RECOMMENDATIONS_BY_CASE_TYPE`. Not in scope for this iter. |

## 9. Next improvements

In order of value:

1. **Sessione Studio Francia** — the Studio sign-off pack from PRODUCT-1 / STUDIO-1 remains the highest-value pending item. PRODUCT-5 makes the result page ready to upsell France-related landings the moment FR goes live.
2. **PRODUCT-6 — case-type-specific FAQ section** — small per-landing FAQ that addresses the 3-4 most common worries (e.g. "is the simulation a legal opinion?", "can I bring my case if it's >5 years old?", "what if my insurer already rejected my claim?"). Same data-driven pattern as PRODUCT-4. Improves SEO long-tail capture and on-page time.
3. **PRODUCT-7 — Studio case-type review iter** — Studio reviews the copy on the 4 most legally-sensitive landings (medical-malpractice, death-of-relative, insurance-offer-review, work-injury) at its convenience, no time pressure. Outputs go into the data module by one-line edits.

## 10. Rollback

A single `git revert` of the PRODUCT-5 commit:

- removes the recommendations mapping + helper from `case_type_landings.py`;
- removes the `recommended_landings` context key from `wizard_result()`;
- removes the new section from `wizard_result.html`;
- removes the new test file + capture script + this report.

No DB rollback needed. Mapping is purely Python data, not persisted.
