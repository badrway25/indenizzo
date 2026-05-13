# CRM / staff lead workflow — improvements — 2026-05-12

**Iter**: `PRODUCT-7-crm-staff-lead-workflow`
**Branch**: `product/crm-staff-lead-workflow`
**Companion of**: `docs/product/CRM_STAFF_LEAD_WORKFLOW_AUDIT_2026-05-12.md` (phase 1 audit).
**Verdict**: shipped — extended Lead admin, new LeadWebhookDelivery admin, three derived helpers on `Lead`, no model migration, no France activation.

## 1. Before vs after — what the Studio sees

### Before

| Surface | What the Studio had |
|---|---|
| `/admin/crm/lead/` list | created_at, name, email, phone, country, case_type, status, mandate_status, mandate_signed, priority, assigned_to. |
| Lead list filters | status, mandate_status, mandate_signed, priority, country, case_type, preferred_language, assigned_to. |
| Lead detail | Identity / Case / Workflow / Mandate / Privacy / Request metadata / Audit fieldsets. Consent denormalised fields **editable** (audit-bypass risk). Mandate audit timestamps **editable**. |
| `/admin/crm/leadwebhookdelivery/` | **Did not exist.** No way to inspect pending / failed / dead deliveries from the admin. |
| Stuck webhook on a Lead | Invisible until someone re-read `dispatch_crm_webhooks` output. |
| Pre-engagement questions | "Did this Lead give double consent?", "Did it come from the wizard funnel?", "Is the CRM webhook firing?" — required opening the row + a shell session. |

### After

| Surface | What the Studio sees now |
|---|---|
| `/admin/crm/lead/` list | All previous columns + **2x consent** (green/red), **Simulation** (green/red), **Source** (`wizard` / `case-type` / `contact`), **Webhook** (`delivered` / `pending(2/5)` / `dead` / `-`). |
| Lead list filters | Previous filters + **Privacy consent given**, **Special-categories consent given**, **Linked simulation** (custom `SimpleListFilter`). |
| Lead detail | Same fieldsets + new collapsed **Webhook outbox (CRM)** section with a 5-row summary. Consent denormalised fields are now **readonly** (audit snapshot, source-of-truth is `ConsentRecord`). Mandate audit timestamps + version + source are **readonly** (written by `apps.compliance.mandate` services). `mandate_status` + `mandate_signed` stay editable. |
| `/admin/crm/leadwebhookdelivery/` | **New, fully read-only.** list_display covers status / attempts / next_attempt_at / delivered_at / last_status_code / target_url_domain. Filters on status + event_type. Search on lead__public_id + idempotency_key. |
| Stuck webhook on a Lead | Visible at the changelist (column) AND on the row detail (collapsed section) AND in the dedicated delivery admin (filter on `status=dead`). |
| Pre-engagement questions | All three answered at the changelist line without opening the row. |

## 2. Files modified / created

| File | Change |
|---|---|
| `apps/crm/models.py` | Added 3 `@property` on `Lead`: `has_valid_double_consent`, `has_linked_simulation`, `webhook_delivery_status_summary`. No model field change, no migration. |
| `apps/crm/admin.py` | Extended `LeadAdmin.list_display` / `list_filter` / `readonly_fields` / `fieldsets`; added `get_queryset` with `prefetch_related("webhook_deliveries")`; tightened `mark_as_contacted` to use `LeadStatus.CONTACTED` instead of brittle index lookup; added `HasLinkedSimulationFilter`; registered `LeadWebhookDeliveryAdmin` (fully read-only). |
| `apps/crm/test_product_7_admin_workflow.py` *(new)* | 17 tests: audit doc + LeadAdmin contract (list_display, list_filter, search, readonly) + consent + mandate readonly locks + LeadWebhookDelivery admin registered + fully read-only + readonly fields cover audit + list_display / filters + 3 helpers + response_excerpt bounded + source label branches. |
| `docs/product/CRM_STAFF_LEAD_WORKFLOW_AUDIT_2026-05-12.md` *(new)* | Phase 1 audit. |
| `docs/product/CRM_STAFF_LEAD_WORKFLOW_IMPROVEMENTS_2026-05-12.md` *(new)* | This file. |
| `docs/screenshots/.../after/product-crm-staff-lead-workflow/NOTES.md` *(new)* | Structured description of the admin changes. No PNGs — admin-only changes; cost/benefit favours a readable notes file. |

No model migration. No new form. No France activation. No CRM/webhook/email change. No new automation. No new permission scheme.

## 3. What's locked vs what stays editable

Documenting the readonly contract explicitly, because it's the
load-bearing change for compliance.

**Readonly (PRODUCT-7 locks these):**

- `privacy_consent_given`, `privacy_consent_at`, `privacy_consent_version`
- `special_categories_consent_given`, `special_categories_consent_at`, `special_categories_consent_version`
- `mandate_signed_at`, `mandate_version`, `mandate_source`

**Pre-existing readonly (unchanged):**

- `public_id`, `user`, `session_key`, `consent_record`, `simulation`, `ip_address`, `user_agent`, `source_path`, `utm_*`, `created_at`, `updated_at`.

**Editable (deliberately kept editable):**

- `mandate_status`, `mandate_signed` — the Studio records acceptance through these.
- `status`, `priority`, `assigned_to`, `contacted_at`, `converted_at`, `internal_notes` — pure workflow.
- `first_name`, `last_name`, `email`, `phone_number`, `preferred_language`, `country`, `case_type`, `message` — staff may need to correct an obvious typo from the form.

## 4. How to handle webhook failures (operational note)

Three escalation tiers for a stuck Lead → CRM webhook:

1. **Pending with attempts > 0**: the dispatcher will retry on its
   next schedule. No staff action needed. Visible at the Lead list
   as `pending(N/5)` in the **Webhook** column.
2. **Failed (permanent 4xx)**: the receiver rejected the payload —
   the URL/secret is right but the payload was malformed for the
   receiver. Open the row in `/admin/crm/leadwebhookdelivery/` to
   see the `last_status_code` + `response_excerpt`. Coordinate
   with the receiver's owner; the dispatcher will not retry.
3. **Dead (max_attempts hit)**: the dispatcher exhausted its retry
   budget on retriable errors (5xx / network). Verify
   connectivity, then trigger a re-run by ID via the env-gated
   `dispatch_crm_webhooks` management command. The Studio does
   **not** re-send via admin clicks — that path was deliberately
   not added (see §5 of the audit).

## 5. Tests

| Suite | Before | After |
|---|---|---|
| Full `pytest -q` | 2114 passed, 1 skipped (PRODUCT-6 baseline) | **2131 passed, 1 skipped** (+17 PRODUCT-7) |
| `apps/crm/test_product_7_admin_workflow.py` | n/a | 17/17 passed |
| `apps/compliance/test_mandate_scaffold.py` | 17 passed | 17 passed (pre-existing contract preserved — `mandate_signed` kept in list_display) |
| `python manage.py check` | clean (only W001 STUDIO_* dev) | unchanged |
| `python scripts/audit_legal_content_hygiene.py --strict` | no findings | no findings |
| `python scripts/legal_data/audit_non_it_readiness.py` | APPROVED-PARTIAL × 4 | APPROVED-PARTIAL × 4 (unchanged) |

## 6. Risks and mitigations actually addressed

| Risk | How addressed |
|---|---|
| Audit-bypass via admin edit of consent denormalised fields | Six consent fields now in `readonly_fields`. Test pin: `test_lead_admin_consent_denormalised_fields_are_readonly`. |
| Audit-bypass via admin edit of mandate timestamp / version / source | Three mandate audit fields now in `readonly_fields`. Test pin: `test_lead_admin_mandate_audit_fields_are_readonly_but_status_stays_editable`. |
| N+1 query on the Lead list because of the new webhook column | `LeadAdmin.get_queryset` now `prefetch_related("webhook_deliveries")`. |
| Full webhook URL leaked to admin | Never displayed. Only `target_url_domain` (host snapshot) shown. HMAC secret is read from settings at dispatch time and never persisted. |
| Long upstream HTTP response body dumped into admin via `response_excerpt` | Model `max_length=500`. Test pin: `test_webhook_response_excerpt_field_is_bounded`. |
| Brittle hard-coded index `mark_as_contacted` action breaking if enum order shifts | Now uses `LeadStatus.CONTACTED`. |
| `webhook_delivery_status_summary` doing N+1 on per-row admin call | Property iterates `self.webhook_deliveries.all()`; the `prefetch_related` on `LeadAdmin.get_queryset` ensures only one extra query overall. |
| LeadWebhookDelivery admin allowing manual changes that contradict the dispatcher state machine | `LeadWebhookDeliveryAdmin` extends `_ReadOnlyAdminMixin`; all three CRUD permissions deny. Test pin: `test_webhook_admin_is_fully_readonly`. |

## 7. Residual limits

| Limit | Severity | Path forward |
|---|---|---|
| No "re-send webhook from admin" action | low | Intentional. The env-gated `dispatch_crm_webhooks` command is the single retry path; an admin click bypasses the safety wrapper. Re-evaluate only if the Studio asks. |
| No CSV / XLSX export of leads from admin | low | Premature for current volume. Sensitive categories (`message`, consent versions) would require an export-specific permission + audit ledger entry. Documented as a separate compliance-reviewed follow-up. |
| No per-role granularity (lead-reader vs lead-editor) | medium | Uses Django's existing staff/superuser permission gate. A dedicated permission scheme is a separate iter; for current Studio size, superuser-only access is acceptable. |
| `source_label_display` is a heuristic (presence of FK + `source_path` substring) | low | Would be more robust as an explicit `source_form` field on `Lead` — but that requires a migration + backfill. PRODUCT-7 deliberately avoids the migration; the heuristic covers every existing entry point. |
| No webhook delivery delete / archive policy in admin | low | The audit ledger keeps all rows. Retention is the separate `compliance.retention` concern. If volume grows, a periodic compaction task is the right answer, not an admin delete button. |

## 8. Next improvements

In order of value:

1. **Sessione Studio Francia** — unchanged from PRODUCT-5 / PRODUCT-6 next-steps. The CRM workflow now surfaces consent + funnel origin clearly, which makes a France-specific Studio onboarding lighter when the calculation activation finally happens.
2. **PRODUCT-8 — webhook re-fire CLI helper** — small management command that re-enqueues a specific `LeadWebhookDelivery` by id (only when CRM_WEBHOOK_ENABLED). Useful when a transient receiver bug knocks a row to `dead` before the receiver's owner has had time to fix it. No admin button; CLI-only, so the safety wrapper stays in place.
3. **PRODUCT-9 — Studio activity ledger** — a single admin page that joins LeadEvent + LeadWebhookDelivery into one chronological feed per lead. Removes the last "I have to look in three places" friction.
4. **PRODUCT-10 — staff role split** — `lead_reader` vs `lead_caseworker` permissions; gated mandate field editing; audit log for who changed status. Compliance-led, deserves its own iter.

## 9. Rollback

A single `git revert` of the PRODUCT-7 commit:

- removes the three `@property` from `Lead`;
- removes the `HasLinkedSimulationFilter` + the extensions on `LeadAdmin`;
- removes the `LeadWebhookDeliveryAdmin` registration;
- removes the new test file + this report + the audit + the NOTES.md.

No DB rollback needed (no migration). The admin returns identical bytes after revert.
