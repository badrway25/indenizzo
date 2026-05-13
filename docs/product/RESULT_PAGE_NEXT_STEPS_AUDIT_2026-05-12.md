# Result-page next-steps audit — 2026-05-12

**Iter**: `PRODUCT-5-result-page-next-pages`
**Branch**: `product/result-page-next-pages`
**Scope**: read-only audit of the wizard result page focused on
"where does the user go after seeing the result". Drives phase 2.
Companion of `LEAD_FUNNEL_AUDIT_2026-05-12.md` and
`CASE_TYPE_LANDING_IMPROVEMENTS_2026-05-12.md`.

## 1. What the result page shows today

URL: `/wizard/result/<uuid>/`. Template:
`templates/public/wizard_result.html`. View:
`apps/cases/views.wizard_result()` (lines ~210-312).

Robots: `noindex, nofollow` (correct for a parametric, user-private
result page).

Sections rendered, in order:

### Estimate path (`has_estimate=True`, today: Italy live, France/Belgium not yet)

1. Top tag + H1 ("Preliminary result").
2. **Status box** — green badge + `min / mid / max` grid in EUR.
3. **"What this means"** — plain-language explanation of the range as a bargaining anchor, not a verdict.
4. **"Next steps"** — 4-item ordered list (PDF, request review, gather documents, keep simulation ID).
5. **"Calculation basis"** — 3-column expansion of min/mid/max definitions.
6. **Assumptions** list (if present).
7. **Public warnings** list (if present).
8. **Documents to prepare** — shared partial from PRODUCT-2 (`_documents_to_prepare.html` variant=result).
9. **Cited legal sources** list.
10. **Disclaimer** — dark block, gold accent.
11. **Mandate notice partial** — separation between simulation and engagement.
12. **Simulation ID + timestamp**.
13. **CTAs**: primary `/contact/?sim=<uuid>` ("Request legal review"), secondary `/reports/<uuid>/pdf`, tertiary back to methodology.

### Review-gated path (`has_estimate=False`, today: France, Belgium, MA/TN)

1. Top tag + H1.
2. **Public message** card — status panel + "What happens next" with `public_message.public_next_steps`.
3. **Documents to prepare** partial.
4. **Assumptions/warnings** (none typically on this path).
5. **Disclaimer**.
6. **Mandate notice**.
7. **Simulation ID + timestamp**.
8. **CTAs**: primary = `public_message.primary_cta_label` → `contact_url`, secondary = `public_message.secondary_cta_label` → wizard start.

## 2. CTAs that exist today

| CTA | Target | When shown |
|---|---|---|
| **Request legal review** | `/contact/?sim=<uuid>` | always (estimate + review-gated paths) |
| **Download PDF report** | `/reports/<uuid>/pdf` | estimate path |
| **Back to methodology** | `/methodology/` | estimate path |
| **Back to wizard start** | `/wizard/` | review-gated path |

## 3. What's missing

The result page already does a lot. But three gaps remain:

| # | Gap | Impact |
|---|---|---|
| R0.1 | **No deep links to case-type landings**. After seeing the result, a user may want to (a) understand more about the type of damage (`/case-types/bodily-injury/`), (b) understand what to do with an insurance offer (`/case-types/insurance-offer-review/`), (c) check cross-border angles (`/case-types/cross-border-cases/`). These pages exist (PRODUCT-4) but the result page doesn't surface them. | Funnel leak — user has to know the URLs or use the footer nav. |
| R0.2 | **Recommendations are not personalised by case-type**. Whatever the simulation case-type, the result page offers the same set of next steps. | A user who ran an IT road-accident simulation could be more usefully pointed at `/case-types/insurance-offer-review/` than at `/methodology/`. |
| R0.3 | **No second-line CTA for "more reading"**. Today the primary CTA is "Request legal review" (high-commitment). A user who is not ready to write the case yet has no soft on-ramp. | Bounce risk for users on the fence. |

## 4. User needs after the result (qualitative)

- **"What does my number mean?"** — already covered by §3 "What this means" + §4 "Next steps".
- **"What documents do I need?"** — already covered by §8 "Documents to prepare".
- **"What if my insurer already made an offer?"** — *not* covered today. `/case-types/insurance-offer-review/` exists (PRODUCT-4).
- **"Is my situation cross-border?"** — *not* covered today. `/case-types/cross-border-cases/` exists.
- **"Am I a foreign citizen — does this still apply?"** — *not* covered today. `/case-types/foreigners-in-italy/` exists.
- **"How does the Studio handle this specific case-type?"** — partly covered by `/contact/`, but the case-type landing has more detail.

## 5. Recommended pages mapping (proposed for phase 2)

Reuses the PRODUCT-4 landings already in tree. The mapping is
data-driven (lookup table by `CaseType` code) so adding new
case-types or new landings touches a single dict.

| Simulation `case_type` | Recommended landings (in order) |
|---|---|
| `road_accident_bodily_injury` | `/case-types/bodily-injury/`, `/case-types/insurance-offer-review/`, `/case-types/cross-border-cases/` |
| `medical_malpractice` | `/case-types/medical-malpractice/`, `/case-types/insurance-offer-review/` |
| `work_injury` | `/case-types/work-injury/`, `/case-types/insurance-offer-review/` |
| `death_compensation` | `/case-types/death-of-relative/`, `/case-types/cross-border-cases/` |
| `parental_loss` | `/case-types/death-of-relative/` |
| `international_inheritance` | `/case-types/cross-border-cases/`, `/case-types/foreigners-in-italy/` |
| `inheritance_basic` | `/case-types/cross-border-cases/` |
| `generic_legal_assessment` | `/case-types/insurance-offer-review/`, `/case-types/cross-border-cases/` |
| `patrimonial_damage` | `/case-types/insurance-offer-review/`, `/case-types/cross-border-cases/` |
| *unmapped* | (no recommendations rendered) |

Capped at 3 recommendations per result page. Order matters: the
most relevant comes first.

Profile-style landings (`/case-types/foreigners-in-italy/`,
`/case-types/cross-border-cases/`) appear across several
case-types because they are about a user *situation*, not about a
case-type code.

## 6. UI placement (proposed for phase 2)

The new section "Pagine utili per il tuo caso" ("Useful pages for
your case") will sit:

- **After** the existing disclaimer + mandate notice (so it does
  NOT replace those — they remain the load-bearing legal blocks
  immediately before CTAs).
- **Before** the simulation ID + timestamp + CTA buttons (so the
  primary CTA "Request legal review" remains the last/strongest
  action on the page).

Visual treatment:

- Light card with a `gold-600` uppercase eyebrow text and a
  serif heading.
- 1-3 internal links displayed as small cards (h3 + short
  description from the landing's `meta_description` OR a
  dedicated short blurb).
- Each link is plain (no buttons) to keep visual hierarchy:
  contact = primary CTA, recommendations = secondary read-more
  links.

## 7. Deontological / GDPR / SEO — what stays

- **No new copy promising results**. Each card label uses the
  landing's existing H1, which is already deontologically
  reviewed.
- **No EUR amount** in the recommendation card descriptions.
- **No `noindex` regression** on the result page — it stays
  `noindex, nofollow` (this is a parametric per-user page,
  correctly excluded from search).
- **No France activation**. The recommended landings link to
  case-type pages, not to the FR wizard. Even an Italy-active
  simulation linking to `/case-types/cross-border-cases/` does not
  publish any FR amount.
- **CTAs preserved**. The "Request legal review" CTA with
  `?sim=<uuid>` remains the primary action.

## 8. What this iter will NOT do

- No model migration / settings change.
- No new view (the recommendation logic lives inside the existing
  `wizard_result` view).
- No new template (extension of `wizard_result.html`).
- No France activation, no formula promotion.
- No new landings (we surface the PRODUCT-4 set, no new ones).
- No new automations.
- No JS additions.

## 9. Phase 2 acceptance criteria

A change is good to ship if:

1. The result page renders 200 for both estimate and review-gated paths.
2. For an Italy road-accident simulation, the page surfaces links to `/case-types/bodily-injury/` AND `/case-types/insurance-offer-review/`.
3. For a France review-gated simulation, the page still shows no EUR amount AND the recommendation section appears with FR-relevant links.
4. Every recommended link reverses to a URL that returns 200.
5. The `?sim=<uuid>` querystring on the contact CTA is preserved.
6. The result page stays `noindex, nofollow`.
7. AR/RTL rendering of `/wizard/result/<uuid>/` still works.
8. No banned phrase appears in the new section.
9. The full test suite stays green; `APPROVED-PARTIAL × 4` unchanged; content hygiene clean.
10. If `simulation.case_type` is unmapped, the section is silently omitted (no broken empty card).

## 10. References

- `templates/public/wizard_result.html` — result template.
- `apps/cases/views.py:210-312` — `wizard_result` view.
- `apps/core/case_type_landings.py` — PRODUCT-4 landings.
- `apps/calculators/enums.py:18-38` — `CaseType` enum.
- `docs/product/LEAD_FUNNEL_AUDIT_2026-05-12.md` — funnel-level audit.
- `docs/product/CASE_TYPE_LANDING_IMPROVEMENTS_2026-05-12.md` — preceding landings iter.
