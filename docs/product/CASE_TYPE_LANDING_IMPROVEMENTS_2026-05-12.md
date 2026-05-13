# Case-type landing improvements — 2026-05-12

**Iter**: `PRODUCT-4-case-type-landing-pages`
**Branch**: `product/case-type-landing-pages`
**Companion of**: `docs/product/CASE_TYPE_LANDING_AUDIT_2026-05-12.md` (phase 1 audit).
**Verdict**: shipped — 8 new public landings, data-driven, indexable, deontologically clean.

## 1. What was built

The funnel previously had only **two landing axes**:

- Country axis — `/countries/` hub + 5 country landings (IT, FR, BE, MA, TN).
- Wizard axis — `/wizard/` hub + 5 wizards.

The case-type axis ended at the hub. PRODUCT-4 fills the gap with **8 per-case-type landings** under `/case-types/<slug>/`, each one acting as a qualified entry point to the wizard or contact form.

## 2. Pages created

| # | URL | Topic | Primary CTA | Secondary CTA |
|---|---|---|---|---|
| 1 | `/case-types/road-accident/` | Road accident — bodily injury | IT wizard | Contact (`?case_type=road_accident_bodily_injury`) |
| 2 | `/case-types/bodily-injury/` | Bodily injury claims (TUN reading) | IT wizard | Contact (same code) |
| 3 | `/case-types/insurance-offer-review/` | Insurance offer review | Contact (`?case_type=generic_legal_assessment`) | Wizard hub |
| 4 | `/case-types/work-injury/` | Work injury | Contact (`?case_type=work_injury`) | Wizard hub |
| 5 | `/case-types/medical-malpractice/` | Medical malpractice | Contact (`?case_type=medical_malpractice`) | Wizard hub |
| 6 | `/case-types/death-of-relative/` | Death of a relative | Contact (`?case_type=death_compensation`) | Wizard hub |
| 7 | `/case-types/foreigners-in-italy/` | Foreign citizens injured in Italy | Contact | Wizard hub |
| 8 | `/case-types/cross-border-cases/` | Cross-border cases | Contact | Wizard hub |

## 3. Page structure (single shared template)

Every landing renders the same template
(`templates/public/case_type_landing.html`) with content from
the `apps.core.case_type_landings.LANDINGS` data module:

1. **Hero image** (Pexels, premium).
2. **H1** + intro paragraph.
3. **"When this applies"** card with 3-4 bulleted typical situations.
4. **"Documents to prepare"** — shared partial from PRODUCT-2 (`_documents_to_prepare.html`), `variant="result"`.
5. **"What the Studio does"** numbered list of 3-4 concrete actions.
6. **Mandate notice partial** — explicit separation of simulation from professional engagement.
7. **Primary + secondary CTAs** as styled pill buttons.
8. **Disclaimer paragraph** adjacent to the CTAs.
9. **Useful-pages nav** — back to hub, methodology, privacy, disclaimer.

## 4. CTA strategy + `?case_type=` prefill

Landings with a direct wizard (road-accident, bodily-injury) link to that wizard as the primary CTA. Landings without a direct wizard (work-injury, medical-malpractice, death-of-relative, foreigners-in-italy, cross-border-cases, insurance-offer-review) link to `/contact/?case_type=<enum_code>`.

`crm.views.contact` was extended (~10 LOC) to honour
`?case_type=<code>` as `initial["case_type"]` if no `?sim=` already
prefilled it. The accepted set of codes is whitelisted against the
`CaseType` enum to prevent injection — unknown codes are silently
ignored, the form opens with the default empty case-type
selector. Failure-soft as in PRODUCT-2.

## 5. Deontological + GDPR — risks addressed

| Risk | How addressed |
|---|---|
| Promise of result | None. All copy stays at "preliminary indicative assessment" / "the Studio reviews each case manually". |
| EUR amounts in copy | None. Test pin: every landing scanned for `\b\d{1,3}(?:[ \xa0.,]\d{3})+\s*(?:€|EUR)` — zero matches. |
| Banned marketing phrases | None. Test pin lists 10 banned phrases (`scopri quanto ti spetta`, `pay only if you win`, `no win no fee`, `risarcimento garantito`, `i migliori avvocati`, etc.) — zero matches across all 8 landings. |
| France activation by sleight-of-hand | None. The road-accident + bodily-injury landings link to the **IT wizard**; FR/BE wizards are still review-gated upstream. The case-type axis does not bypass the country-level review gate. |
| Mandate notice missing | Every landing includes `partials/mandate_notice.html` between the body and the CTAs. |
| GDPR / consent regression | Untouched. The new landings are informational read-only pages. Consent collection still happens at /wizard/ submit and /contact/ submit, both unchanged. |
| Garbage querystring injection | `?case_type=<code>` is whitelisted against the enum. Garbage values do NOT leak into rendered HTML (`test_contact_ignores_invalid_case_type_querystring`). |

## 6. SEO

- All 8 landings + the hub are **indexable** (default `index, follow`).
- `<title>` and `<meta name="description">` come from the data module per landing.
- `core:case_type_landing` view name added to the hreflang allowlist (`apps/core/context_processors.py:_GLOBAL_HREFLANG_VIEW_NAMES`) — every landing gets `<link rel="alternate" hreflang>` for IT / FR / EN / AR.
- URL slug convention is English snake-case to match the repo's existing routing (decision documented in the audit doc).

## 7. Files modified / created

| File | Change |
|---|---|
| `apps/core/case_type_landings.py` *(new)* | Data module: 8 `CaseTypeLanding` dataclass entries with H1, intro, when-it-applies bullets, what-Studio-does steps, meta title/description, primary + secondary CTA names + kwargs. |
| `apps/core/views.py` | New `case_type_landing(request, slug)` view (404 on unknown slug); `case_types` hub view extended to surface a `landing_slug` per case-type card + a separate `extra_landings` group for profile-style landings. |
| `apps/core/urls.py` | New URL pattern `case-types/<slug:slug>/` → `core:case_type_landing`. |
| `apps/core/context_processors.py` | `core:case_type_landing` added to `_GLOBAL_HREFLANG_VIEW_NAMES` allowlist. |
| `apps/crm/views.py` | `contact()` extended to honour `?case_type=<code>` querystring with enum whitelist. |
| `templates/public/case_type_landing.html` *(new)* | Single shared template. |
| `templates/public/case_types.html` | Hub now links each case-type card to its landing (when one exists) + renders the `extra_landings` group. |
| `apps/core/test_product_4_case_type_landings.py` *(new)* | 51 tests covering hub, 8 landings, 404, indexability, banned phrases, EUR leak, CTAs, prefill, anti-injection, AR/RTL, sync between data module and `CaseType` enum, URL reverses, hreflang allowlist. |
| `scripts/capture_product_4_case_type_landings.py` *(new)* | Playwright harness — hub + 8 landings + contact `?case_type=` + AR/RTL pair. |
| `docs/product/CASE_TYPE_LANDING_AUDIT_2026-05-12.md` *(new)* | Phase 1 audit. |
| `docs/product/CASE_TYPE_LANDING_IMPROVEMENTS_2026-05-12.md` *(new)* | This file. |
| `docs/screenshots/.../after/product-case-type-landings/` *(new)* | 24 PNGs (12 viewport pairs × 2 viewports). |

No model migration. No new form. No France activation. No
calculator change. No CRM / webhook / email change.

## 8. Tests

| Suite | Before | After |
|---|---|---|
| Full `pytest -q` | 2017 passed, 1 skipped | **2068 passed, 1 skipped** (+51 new) |
| `apps/core/test_product_4_case_type_landings.py` | n/a | 51/51 passed |
| `python manage.py check` | clean (only W001 STUDIO_* dev) | unchanged |
| `python scripts/legal_data/audit_non_it_readiness.py` | APPROVED-PARTIAL × 4 | APPROVED-PARTIAL × 4 (France stays review-gated) |
| `python scripts/audit_legal_content_hygiene.py --strict` | no findings | no findings |

## 9. Screenshots

`docs/screenshots/delta_audit_2026-05-10/after/product-case-type-landings/`
contains 24 PNGs:

- Hub desktop + mobile.
- 8 landings × 2 viewports = 16 PNGs.
- AR hub + AR road-accident landing × 2 viewports = 4 PNGs.
- Contact form with `?case_type=medical_malpractice` × 2 viewports = 2 PNGs.

Visual checks confirmed:

- Hub now shows clear "Read more" CTAs on case-type cards that have a landing.
- The "Specific situations" group surfaces the 3 profile-style landings (insurance offer review, foreigners in Italy, cross-border cases).
- Each landing carries H1 → intro → when-it-applies → documents-to-prepare → what-Studio-does → mandate notice → CTAs → disclaimer.
- AR/RTL renders without breakage on hub + landing.
- Contact form preselects the case-type when `?case_type=medical_malpractice` is in the URL.

## 10. Residual risks

| Risk | Severity | Mitigation |
|---|---|---|
| New strings in `case_type_landings.py` are not yet in `.po` files for IT/FR/AR/EN | low | The strings ship as English in non-EN locales until the translation team imports them. The `test_translated_locales_have_no_high_priority_english_fallback` test does NOT include the new `/case-types/<slug>/` paths, so it remains green. The hub itself was kept clean of long English fallback (the `meta_description` is rendered only inside each landing's `<head>`, not on the hub card). |
| Some landings (insurance-offer-review, foreigners-in-italy) describe a *situation* rather than a CaseType enum value; the `?case_type=` querystring on /contact/ uses `generic_legal_assessment` for them. Studio may want a more specific code in future. | low | Easy follow-up — add a new `CaseType` enum value and update the data module. The whitelist guard means we won't accept an arbitrary value without a code change. |
| The hub now has more content — slightly longer on mobile | low | Two-column grid on small screens stacks naturally. Mobile screenshot confirms the layout works. |
| Future Studio sign-off may want different copy on legally-sensitive case types (medical malpractice especially) | low — explicit | The landings stay at the "what the Studio does + what to bring" level; no legal-doctrinal claim is made. If Studio wants a more specific or restrictive copy, the change is a single edit in the data module — no template work. Logged as a content-review item for Studio's next session. |

## 11. Next content to validate with the Studio

These items are **not blockers** for the iter — the landings are
deontologically clean and shippable. But the Studio may want to
review/refine some copy at its convenience:

1. **Medical-malpractice page**: the wording "an avoidable harm" is conservative but the Studio may want a more precise phrasing aligned with Italian case-law on responsabilità sanitaria.
2. **Death-of-relative page**: the "discretion the case requires" line is generic. Studio may want a richer empathy framing.
3. **Cross-border cases**: the list of cited frameworks (Reg. 650/2012, etc.) is intentionally kept implicit. Studio may want to surface the technical references.
4. **Insurance-offer-review**: the line "do not sign a settlement without a legal review" is the strongest "advice" sentence in the whole pack. Studio may want to soften or formalise it.

All four can be tuned by editing `apps/core/case_type_landings.py`
alone — no template change, no test change. The translation team
will pick up the changes in the next `.po` cycle.

## 12. Next product steps

In order of value:

1. **Sessione Studio Francia** — the Studio sign-off pack from
   `docs/studio/` is still pending. The case-type landings make
   the funnel ready to handle a higher volume of qualified leads
   once France is activated.
2. **STUDIO-2 Belgium readiness pack** — mirror PRODUCT-1 + STUDIO-1
   for Belgium.
3. **PRODUCT-5 — wizard result-page calls-to-action improvement** — could surface a personalised "next pages to read" pointing to the relevant case-type landing based on the simulation's case_type. Small UX win, no model change.

## 13. Rollback

A single `git revert` of the PRODUCT-4 commit:

- removes the data module, view, URL, template, hub additions;
- restores the hub to its pre-iter state;
- removes the `?case_type=` extension in `crm.views.contact` (the line is small and isolated);
- removes the hreflang allowlist entry;
- removes the tests + capture + screenshots + this report.

No DB rollback needed.
