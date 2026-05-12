# Lead funnel audit — 2026-05-12

**Iter**: `PRODUCT-2-lead-funnel-improvements`
**Branch**: `product/lead-funnel-improvements`
**Scope**: read-only audit of the public lead funnel as it stands today. Output of phase 1 of PRODUCT-2. Drives the targeted improvements implemented in phase 2.

This document is **descriptive**, not prescriptive. It maps the funnel
as the code is today (post P2-PERF-4 + STUDIO-1 merges on
`audit/indennizzati-platform`), identifies friction points, and ranks
quick-wins. It deliberately does **not** propose model changes,
redesigns, France activation, or new automations.

## 1. Funnel map (step by step)

| # | Step | URL | Template | View | Form | Persists | Robots |
|---|---|---|---|---|---|---|---|
| 1 | Homepage | `/` | `public/home.html` | `core.views.home` | — | nothing | `index, follow` |
| 2 | Countries | `/countries/` | `public/countries.html` | `core.views.countries` | — | nothing | `index, follow` |
| 3 | Wizard landing | `/wizard/` | `public/wizard_start.html` | `cases.views.wizard_start` | — | nothing | `index, follow` |
| 4 | Wizard form (IT) | `/wizard/it/road-accident/` | `public/wizard_italy_road_accident.html` | `cases.views.wizard_italy_road_accident` | `ItalyRoadAccidentWizardForm` | `Simulation` + 2× `ConsentRecord` + `PrivacyAuditEvent` | `noindex, nofollow` |
| 5 | Wizard form (FR) | `/wizard/fr/road-accident/` | `public/wizard_france_road_accident.html` | `cases.views.wizard_france_road_accident` | `FranceRoadAccidentWizardForm` | `Simulation` (review-gated, no calc) + 2× `ConsentRecord` + `PrivacyAuditEvent` | `noindex, nofollow` |
| 6 | Result | `/wizard/result/<uuid>/` | `public/wizard_result.html` | `cases.views.wizard_result` | — | nothing (reads existing Simulation) | `noindex, nofollow` |
| 7 | Contact form | `/contact/` (optionally `?sim=<uuid>`) | `public/contact.html` | `crm.views.contact` | `ContactForm` | `Lead` (+ FK `simulation` if `?sim` resolves) + 2× `ConsentRecord` + `LeadEvent(CREATED)` + `PrivacyAuditEvent` + `LeadWebhookDelivery` (PENDING, env-gated) | `index, follow` |
| 8 | Thank-you | `/contact/thank-you/` | `public/contact_thank_you.html` | `crm.views.contact_thank_you` | — | nothing | `noindex, nofollow` |

## 2. What the user sees, step by step

### 4–5. Wizard form

- Inline form with optional fields (age, disability %, fault %, dates, expenses).
- Bottom of form: two GDPR consent checkboxes (art. 6 + art. 9).
- Submit → simulation runs server-side → redirect to result page (302).
- Honeypot field hidden; rate-limited POST.

### 6. Result page (with estimate)

- Status badge ("Indicative calculation available").
- `min / mid / max` in a 3-column grid.
- "What this means" plain-language block (range as bargaining anchor, not a verdict).
- "Next steps" 3-item ordered list (download PDF, request review, keep simulation ID).
- "Calculation basis" 3-column expansion of min/mid/max meaning.
- Assumptions list (if present).
- Public warnings (if present).
- Cited legal sources, each with title + citation + country/jurisdiction badges + official URL.
- Disclaimer block (dark, gold accent).
- Mandate notice partial (separation between simulation and engagement).
- Simulation ID + timestamp.
- Two main CTAs:
  - **primary** → `/contact/?sim=<public_id>` ("Request legal review")
  - **secondary** → `/reports/<public_id>/pdf` ("Download PDF report")
  - tertiary → back to methodology.

### 6. Result page (review-gated, no estimate — France today, IT non-cases)

- Status panel via `partials/_public_status_panel.html` (variant "landing").
- "What happens next" block with public_message.public_explanation + applicable_law_hint + public_next_steps.
- Cited sources + disclaimer + mandate notice + simulation meta.
- CTA labels come from `public_message.primary_cta_label` / `secondary_cta_label` (so they're status-aware).

### 7. Contact form

- 4-row "What happens next" reassurance (manual lawyer reply, 3–5 working days response time, no automatic engagement, retention policy).
- First/last name, email, phone (optional), preferred language, country (optional, FK), case type (optional), message (≥ 20 chars).
- Two GDPR consent checkboxes (art. 6 + art. 9).
- Hidden: `simulation_public_id` (set from `?sim=<uuid>` querystring).
- Honeypot `website` field.
- Submit → `create_lead_from_form()` → email enqueue + webhook outbox → redirect to `/contact/thank-you/` (302).

### 8. Thank-you

- ✓ icon + "Your request has been received".
- "3–5 working days" written reply guarantee.
- Retention policy note.
- "Submitting does not create a professional engagement" reminder.
- Mandate notice partial.
- 3 CTAs: back to wizard, back to homepage, visit institutional site (external).

## 3. Backend — what happens behind the curtain

### Simulation → Lead linkage

1. Wizard POST creates `Simulation(public_id=<uuid>)`.
2. Result page is rendered at `/wizard/result/<uuid>/`.
3. Result page CTA link = `/contact/?sim=<uuid>` (built in `cases.views.wizard_result` line 259).
4. Contact GET captures `request.GET.get("sim")` → puts into `initial["simulation_public_id"]`.
5. Hidden form field `simulation_public_id` carries the uuid into POST.
6. `create_lead_from_form()` queries `Simulation.objects.filter(public_id=…).first()`.
7. Resolved Simulation set as FK on the new `Lead.simulation`.

So the linkage is end-to-end. The Studio sees in admin which lead came from which simulation and can recover the exact input/output of that simulation.

### Email + webhook on Lead creation

- **Email**: `send_lead_notification(lead, request=…)` — plaintext, internal address list (`LEAD_NOTIFICATION_TO_EMAILS`). Failure-soft. Async via Celery if `LEAD_NOTIFICATION_ASYNC_ENABLED=True`, sync otherwise (with auto-fallback).
- **Webhook**: `enqueue_lead_webhook(lead, event_type="lead.created")` — writes a `LeadWebhookDelivery(status=PENDING)` outbox row. Actual HTTP delivery handled by the management command `dispatch_crm_webhooks` (out-of-band). HMAC-SHA256 signed. Env-gated by `CRM_WEBHOOK_ENABLED + CRM_WEBHOOK_URL + CRM_WEBHOOK_SECRET`.
- Both paths are **failure-soft**: an SMTP outage / broker outage cannot break the user redirect to thank-you.

### Privacy + audit

- `record_double_consent()` creates two `ConsentRecord` rows: `lead_contact` (art. 6) + `special_categories_processing` (art. 9).
- Denormalized flags + timestamps + versions on the `Lead` row.
- `PrivacyAuditEvent(CONSENT_GIVEN)` logged with purposes list.
- `LeadEvent(CREATED)` logged with country code + case_type + has_simulation.

## 4. Where users can be lost (friction points)

Each entry is a place where the user is alive in the funnel and **could drop out**. Ranked P0 (highest impact, lowest cost) → P2 (lowest impact).

### P0 — Quick wins, ship in this iter

| # | Location | Friction | Fix shape |
|---|---|---|---|
| F0.1 | Contact form arrives with `?sim=<uuid>` | The hidden field is filled, but **`country` and `case_type` are not prefilled** from the linked Simulation. The user must re-select them, duplicating work they did 30 seconds earlier in the wizard. | Backend (`crm.views.contact`): when `?sim` resolves, prefill `initial["country"]` and `initial["case_type"]` from the Simulation. No template change needed for the prefill itself; small badge to confirm. |
| F0.2 | Contact form arrives with `?sim=<uuid>` | The user has **no visual confirmation** that the form is connected to their simulation. The hidden field is invisible by definition. | Template: small confirmation banner above the form when `simulation_public_id` is set ("Connected to simulation #abc12345 — country and case type prefilled"). |
| F0.3 | Thank-you page | "3–5 working days" is reassuring but the user has **no actionable guidance** on what to do meanwhile. Many leave the page without preparing the materials the Studio will need. | Template: small "while you wait" block with generic, country-agnostic document-prep checklist (e.g. "gather medical reports", "find police/insurance correspondence", "if a witness was present, write down their contact"). Generic enough to ship without legal review. |
| F0.4 | Result page (estimate path) | Excellent next-steps but no "**documents to prepare**" hint. The user knows what to do (request review) but not what to bring. | Template: tighten the existing "Next steps" block with a fourth item linking to the same document-prep checklist used on thank-you (DRY via partial). |

### P1 — Deeper, ship in a follow-up

| # | Location | Friction | Fix shape |
|---|---|---|---|
| F1.1 | Wizard form fields | Many optional fields (8+). User abandonment risk if mobile (form long). | UX iter: progressive disclosure (collapse optional advanced fields under "More details"). Requires JS or `<details>`; not in scope today. |
| F1.2 | Contact form GDPR | Two consent checkboxes — required for legal reasons but cognitively heavy. | Cannot simplify (legal requirement). Could improve copy clarity, but that's a Studio-signed text change → out of scope. |
| F1.3 | Result page (review-gated) | Today only FR `/wizard/fr/` falls here. CTA labels come from `public_message` so they're already status-aware. | No quick win; this is correctly review-gated. |
| F1.4 | Contact form `country` field | `ModelChoiceField` over all `is_active=True` countries — could pre-select user's GeoIP country. | Out of scope (needs GeoIP infra). |

### P2 — Aesthetic / nice-to-have

| # | Location | Friction | Fix shape |
|---|---|---|---|
| F2.1 | Email response time | 3–5 working days is honest but slow. Studio could publish a WhatsApp / phone channel for urgent matters. | Requires Studio decision on channels. Out of scope. |
| F2.2 | Honeypot detection | If a bot fills the honeypot, user is redirected to thank-you (silent drop). Good against bots, but if a real user accidentally fills it (unlikely with `aria-hidden + .is-honeypot` CSS), they get a silent failure. | Acceptable risk given current design. |
| F2.3 | Contact form `message` field | 20-character minimum. Could be too short to write a meaningful brief, but also blocks easy submissions like "please call me". | Out of scope. |

## 5. Deontological risks (current state — clean)

The funnel today is correctly cautious:

- **No promise of recovery** anywhere in the copy. Wizard, result, contact, thank-you all carry "indicative" / "not a guarantee" / "not legal advice".
- **No "pay only if you win"** wording. Mandate notice (partial) is rendered on result + thank-you.
- **No France amount published**. Review-gated. Test pinned (`apps/cases/test_product_1_france_signoff_pack.py`).
- **No automatic acceptance of mandate**. Both contact form and thank-you state explicitly "submitting does not create a professional engagement".
- **No third-party reply** ("a lawyer of the Studio reads your message manually — no automated reply, no third party").

## 6. GDPR risks (current state — clean)

- Double consent (art. 6 + art. 9) enforced on both wizard and contact form.
- Versioned consent + timestamps + audit ledger.
- Failure-soft email/webhook (cannot break the funnel if SMTP/broker down).
- No PII in logs (only `public_id` + counts).
- No raw sensitive data in webhook payload (the payload schema uses `build_lead_payload()` which sanitizes; full audit in `apps/crm/webhooks.py`).
- Privacy notice + special-categories notice versions stored on every consent record.
- Robots.txt respects noindex on transactional pages.

## 7. Recommended UX implementations (phase 2)

Only the **P0 quick-wins** identified in §4 will be implemented in this iter:

1. **F0.1 + F0.2** — contact form prefill from linked simulation + visible confirmation banner. (Backend: small view change in `crm.views.contact`. Template: short banner block.)
2. **F0.3** — thank-you "while you wait" block. (Template-only.)
3. **F0.4** — result page "documents to prepare" hint, linked to the same checklist on thank-you. (Template-only; share content via partial.)

P1 and P2 are documented here and **not implemented** — they belong to follow-up product iters (or require Studio/policy decisions that this batch is not the right scope for).

## 8. What this iter will NOT touch

- No model changes.
- No new fields on `Simulation` / `Lead`.
- No France activation (4 Studio sign-offs still pending — see `docs/studio/`).
- No CRM webhook payload changes.
- No CSP / robots / consent / mandate-notice copy changes (all signed).
- No new automations (WhatsApp API, GeoIP, calendar booking, etc.).
- No new languages (current set IT/FR/EN/AR remains).
- No France numbers, no new formulas.

## 9. Phase 2 acceptance criteria

A targeted improvement is **good to ship** if:

1. It does not require any model / migration / settings change.
2. It does not change any text that was previously Studio-signed (mandate notice, disclaimer, French disclaimer placeholder).
3. It is fully reversible (`git revert` of a single commit restores the prior funnel without DB rollback).
4. The full test suite stays green.
5. The audit `audit_non_it_readiness.py` continues to report `APPROVED-PARTIAL × 4` (France stays review-gated).
6. The audit `audit_legal_content_hygiene.py --strict` reports zero findings.
7. Mobile Lighthouse on the touched pages does not regress (`/contact/`, `/wizard/result/...`).

## 10. References

- `docs/product/FRANCE_ACTIVATION_SIGNOFF_PACK.md` — France activation (parallel work, gated by Studio).
- `docs/studio/FRANCE_REVIEW_MEETING_AGENDA.md` — Studio session for France sign-off.
- `apps/cases/views.py:259` — contact_url construction with `?sim=<uuid>`.
- `apps/crm/views.py:77-79` — contact view picks up `?sim`.
- `apps/crm/services.py:93-99` — Simulation resolution from `simulation_public_id`.
- `apps/crm/forms.py:96` — hidden `simulation_public_id` field.
- `templates/public/wizard_result.html` — result page.
- `templates/public/contact.html` — contact form.
- `templates/public/contact_thank_you.html` — thank-you.
