# CRM lead activity timeline — improvements — 2026-05-12

**Iter**: `PRODUCT-8-studio-lead-activity-timeline`
**Branch**: `product/studio-lead-activity-timeline`
**Companion of**: `docs/product/CRM_LEAD_ACTIVITY_TIMELINE_AUDIT_2026-05-12.md` (phase 1 audit).
**Verdict**: shipped — read-only chronological timeline aggregated from existing rows + a conservative `next_staff_action` operational hint. No new model, no migration, no France activation.

## 1. Before vs after — what the Studio sees on one Lead

### Before (post-PRODUCT-7)

On `/admin/crm/lead/<id>/change/`:

- Identity / Case classification / Workflow / Mandate / Privacy / Request metadata.
- New columns in the changelist made the *list* useful, but on a single row the Studio still had to mentally stitch together:
  - "*Was the simulation linked? When?*" — open the FK.
  - "*When were the consents recorded?*" — read 6 separate denormalised fields.
  - "*Did the webhook fire? Is it stuck?*" — open the dedicated webhook admin.
  - "*What should I do next on this lead?*" — figure it out from the column values.
- No single panel showed the chronological sequence of what happened to *this* Lead.

### After

A new fieldset **"Activity timeline"** between the Mandate and Webhook outbox sections, with two readonly entries:

1. **Next staff action** — one-line operational hint derived purely from workflow flags. Examples:
   - `Review new lead and decide next step`
   - `Review linked simulation and contact client`
   - `Webhook delivery failed - check integration`
   - `Mandate not signed - prepare engagement letter`
   - `Engagement active - manage the case offline`
2. **Activity timeline** — vertical list of timestamped entries, one per event, ordered chronologically ascending. Each entry carries a coloured left border by severity (info/success/warning/error), a category tag, a short label, a one-line description, and the source row id.

## 2. Events surfaced

| # | Category | When it appears | Severity rule |
|---|---|---|---|
| 1 | `simulation` | `Lead.simulation_id is not None` | info |
| 2 | `consent` (privacy) | `Lead.privacy_consent_at` not null | success |
| 3 | `consent` (special-categories) | `Lead.special_categories_consent_at` not null | success |
| 4 | `lead` (created) | always | info |
| 5 | `lifecycle` | one per `LeadEvent` row | created/contacted/note/other = info; qualified/converted = success; rejected/archived = warning |
| 6 | `webhook` (enqueued) | one per `LeadWebhookDelivery` row, at `created_at` | info |
| 7 | `webhook` (terminal) | one per `LeadWebhookDelivery`: delivered (success) / failed / dead (error) | derived from `status` |
| 8 | `webhook` (pending) | only when status=pending/sending AND attempts>0 — at `last_attempt_at` | warning |
| 9 | `mandate` (required default) | always, at `Lead.created_at` | info |
| 10 | `mandate` (signed) | when `mandate_signed=True` and `mandate_signed_at` set | success |

The aggregator skips the `LeadEvent(CREATED)` row when its timestamp matches `Lead.created_at` exactly — avoids two adjacent rows for the same instant.

Ordering: by `timestamp` ascending. Ties broken by category priority (simulation → consent → lead → lifecycle → webhook → mandate) then by source row pk — deterministic.

## 3. `next_staff_action` — branches

Conservative operational hint. Returns one of a fixed set of short English strings. **Never derives a legal opinion.** Order of precedence (most-critical condition wins):

| Condition | Returned action |
|---|---|
| `status=archived` or `status=rejected` | `Archived - no further action` |
| webhook summary = `dead` | `Webhook delivery failed - check integration` |
| `status=converted` and `mandate_signed=True` | `Engagement active - manage the case offline` |
| webhook summary starts with `pending(` | `Webhook still retrying - monitor delivery` |
| `status=received` and `has_linked_simulation` | `Review linked simulation and contact client` |
| `status=received` and not `has_linked_simulation` | `Review new lead and decide next step` |
| `status=qualified` and not `mandate_signed` | `Mandate not signed - prepare engagement letter` |
| `status=contacted` | `Waiting for Studio review` |
| fallback | `Ready for manual follow-up` |

## 4. Implementation choice — aggregate, do not persist

The audit (§5) lays out the alternatives. Conclusion: aggregate existing rows on the fly via a pure helper (`apps/crm/timeline.py:build_lead_timeline`). No new model, no migration, no new write path. The helper is one function that reads:

- the Lead row,
- `lead.simulation` (select_related-friendly),
- `lead.events.all()` (prefetch-friendly),
- `lead.webhook_deliveries.all()` (prefetch-friendly).

`LeadAdmin.get_queryset` was extended to `select_related("simulation").prefetch_related("webhook_deliveries", "events")` so opening a Lead detail page costs a bounded number of SQL statements regardless of the number of webhook deliveries / lifecycle events.

## 5. Privacy guardrails (pinned by tests)

| Rule | Test pin |
|---|---|
| No HMAC secret in any timeline string | `test_timeline_does_not_leak_secret_url_or_pii` — sets `settings.CRM_WEBHOOK_SECRET = "SENTINEL-..."` and asserts the sentinel does not appear in any item's label/description/source/metadata. |
| No full webhook URL | Same test pins the sentinel URL `/v1/very/secret/path?token=abc` — the aggregator only reads the persisted `target_url_domain` (host snapshot), never settings. |
| No PII in the timeline | `Lead.message`, `Lead.email`, `Lead.phone_number`, `Lead.first_name`, `Lead.last_name` are all asserted absent from the rendered timeline string. |
| No `<script>` execution from a hostile LeadEvent message | `test_admin_activity_timeline_render_has_no_js` feeds `<script>alert(1)</script> javascript:alert(2)` into a LeadEvent message, renders the timeline, asserts no `<script` tag, no `href="javascript:..."` attribute, no inline event-handler attribute. |
| No legal-advisory phrasing in `next_staff_action` | `test_next_staff_action_strings_have_no_banned_phrases` scans every branch's output for the 8-phrase banned list. Zero matches. |
| No retry button / link from the admin timeline | The rendered HTML is `<ul>` of `<li>` rows. No `<form>`, no `<button>`, no `<a href=>`. Re-fire remains CLI-only. |

## 6. Files modified / created

| File | Change |
|---|---|
| `apps/crm/timeline.py` *(new)* | `LeadTimelineItem` frozen dataclass + `build_lead_timeline(lead)` aggregator + fixed-string `ACTION_*` constants + `compute_next_staff_action(lead)`. ~280 LOC, pure-function, no DB writes. |
| `apps/crm/models.py` | Added `Lead.next_staff_action` property as a thin delegation to `compute_next_staff_action`. No model field. |
| `apps/crm/admin.py` | Extended `LeadAdmin.get_queryset` with `select_related("simulation")` + `prefetch_related("events")`. Added two readonly displays: `next_staff_action_display`, `activity_timeline` (rendered via `format_html` + `format_html_join`, fixed-key severity colours). Added an "Activity timeline" fieldset before the existing webhook outbox fieldset. |
| `apps/crm/test_product_8_lead_activity_timeline.py` *(new)* | 17 tests: audit doc + Lead created anchor + simulation link + both consent entries + webhook variants + mandate signed conditional + chronological ordering + secret/URL/PII leak scan + admin readonly contract + 6 `next_staff_action` branches + banned-phrase scan + escape-safety on hostile message. |
| `docs/product/CRM_LEAD_ACTIVITY_TIMELINE_AUDIT_2026-05-12.md` *(new)* | Phase 1 audit. |
| `docs/product/CRM_LEAD_ACTIVITY_TIMELINE_IMPROVEMENTS_2026-05-12.md` *(new)* | This file. |
| `docs/screenshots/.../after/product-studio-lead-activity-timeline/NOTES.md` *(new)* | Structured description of the admin detail-page rendering. No PNG (admin-only change; the structured example carries the visual signal). |

No model migration. No new form. No France activation. No CRM/webhook/email change. No new automation. No new permission scheme.

## 7. Tests

| Suite | Before | After |
|---|---|---|
| Full `pytest -q` | 2131 passed, 1 skipped (PRODUCT-7 baseline) | **2148 passed, 1 skipped** (+17 PRODUCT-8) |
| `apps/crm/test_product_8_lead_activity_timeline.py` | n/a | 17/17 passed |
| `python manage.py check` | clean (only W001 STUDIO_* dev) | unchanged |
| `python scripts/audit_legal_content_hygiene.py --strict` | no findings | no findings |
| `python scripts/legal_data/audit_non_it_readiness.py` | APPROVED-PARTIAL × 4 | APPROVED-PARTIAL × 4 (unchanged) |

## 8. Residual limits

| Limit | Severity | Path forward |
|---|---|---|
| Status hand-edits on the admin form do not produce a LeadEvent | low | A model signal could auto-create a LeadEvent on `Lead.status` change. Out of scope for this iter to keep it side-effect-free; documented as a separate small follow-up. |
| Per-attempt webhook history is not visible (only the latest attempt) | low | Would require a `LeadWebhookAttempt` child table — out of scope. Latest-attempt summary is sufficient operationally. |
| No JSON export of the timeline | low | Could be added as a small read-only endpoint if the Studio needs it for offline analysis. Not requested. |
| Timeline shape is fixed in code; cannot be reconfigured per user | low | Acceptable for a single-tenant Studio admin. If multi-Studio rolls in, per-staff preferences become its own iter. |
| `next_staff_action` is rule-based, not learned | low | Deliberate. A learned recommendation would require labelled training data and an audit trail of *why* the recommendation was made — out of scope for this iter and arguably forever for this product. |
| FAQ "should the Studio re-fire a dead webhook?" answer (CLI vs admin) | low | The audit + this report both say the re-fire path remains CLI-only. PRODUCT-9 candidate: a `python manage.py refire_webhook_delivery <id>` management command (idempotent, env-gated). |

## 9. Next improvements

In order of value:

1. **PRODUCT-9 — webhook re-fire CLI helper** — small management command that re-enqueues a single `LeadWebhookDelivery` by id. Env-gated on `CRM_WEBHOOK_ENABLED=True`. No admin button. Reuses the existing dispatcher state machine. Makes the timeline's "dead" annotation actionable without bypassing the safety wrapper.
2. **PRODUCT-10 — Studio role split** — `lead_reader` vs `lead_caseworker` permissions; consent / mandate field gates per role. Compliance-led; deserves its own audit.
3. **Sessione Studio Francia** — unchanged from PRODUCT-5/6/7. The activity timeline now makes FR onboarding lighter: a France-specific lead would surface its review-gated status + the webhook delivery state in one panel, without needing France-specific tooling.

## 10. Rollback

A single `git revert` of the PRODUCT-8 commit:

- removes `apps/crm/timeline.py`;
- removes the `Lead.next_staff_action` property;
- removes the LeadAdmin extensions (queryset prefetch, the two readonly displays, the new fieldset);
- removes the new test file + this report + the audit + the NOTES.md.

No DB rollback needed (no migration). The pre-PRODUCT-8 admin returns identical bytes after revert.
