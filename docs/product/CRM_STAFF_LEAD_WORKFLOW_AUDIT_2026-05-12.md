# CRM / staff lead workflow — audit (phase 1) — 2026-05-12

**Iter**: `PRODUCT-7-crm-staff-lead-workflow`
**Branch**: `product/crm-staff-lead-workflow`
**Companion of**: `docs/product/CRM_STAFF_LEAD_WORKFLOW_IMPROVEMENTS_2026-05-12.md` (phase 6 report — written after implementation).
**Predecessors**: PRODUCT-2 (lead funnel — `docs/product/LEAD_FUNNEL_*.md`), F-p1-crm-1-webhook-dispatcher (webhook outbox model), F-p0-leg-2-mandate, F-p0-leg-3-consent.

This document is **descriptive**. It maps how a Lead is born, what the Studio sees in Django admin today, and where Studio loses time. Phase 2-3 of this iter implement targeted admin/data improvements; this phase only audits.

## 1. Funnel touchpoints that produce a Lead

| Source | URL → effect | Persists |
|---|---|---|
| Contact form (top-of-funnel) | `/contact/` GET → `/contact/` POST | `Lead` (no `simulation` FK) + 2× `ConsentRecord` + `LeadEvent(CREATED)` + `PrivacyAuditEvent` + `LeadWebhookDelivery` (PENDING, env-gated) |
| Wizard result CTA | `/wizard/result/<uuid>/` → `/contact/?sim=<uuid>` | Same as contact form, plus `Lead.simulation` FK populated when `?sim` resolves |
| Case-type landing CTA | `/case-types/<slug>/` → `/contact/?case_type=<code>` | Same as contact form, with `case_type` field pre-selected by querystring (anti-injection enum whitelist on POST) |
| Country landing CTA *(future)* | `/countries/<slug>/` → `/contact/?country=<code>` | Same flow; no FK to country page itself, only via the form's `country` field. |
| Wizard form (IT calc + FR review-gated) | `/wizard/<lang>/<case>/` POST | Persists a `Simulation` — **not** a `Lead`. The Lead is only produced once the user follows the result-page CTA. |

A Lead therefore always carries: contact identity, ≥1 consent record, lifecycle events, optionally a `simulation` FK, optionally a `country` FK + `case_type` enum, optionally a webhook outbox row.

## 2. `Lead` schema today — what the Studio has to work with

From `apps/crm/models.py:Lead`:

| Group | Fields |
|---|---|
| Identity / public | `public_id` (UUID), `first_name`, `last_name`, `email`, `phone_number`, `preferred_language` |
| Case classification | `country` FK, `case_type` enum, `message` (free text), `simulation` FK (optional) |
| Workflow | `status`, `priority`, `assigned_to` FK, `contacted_at`, `converted_at`, `internal_notes` |
| Consent (denormalised — source-of-truth is `ConsentRecord`) | `consent_record` FK + 6 denormalised fields: `privacy_consent_given/_at/_version`, `special_categories_consent_given/_at/_version` |
| Mandate | `mandate_status` (required/sent/signed/declined), `mandate_signed`, `mandate_signed_at`, `mandate_version`, `mandate_source` |
| Request metadata | `ip_address`, `user_agent`, `source_path`, `utm_source/medium/campaign`, `session_key`, `user` FK |
| Audit | `created_at`, `updated_at`, `anonymized`, `anonymized_at` |

Indexes already cover the workflow queries: `(status, created_at)`, `(priority, status)`, `(assigned_to, status)`, `(country, case_type)`.

Related models:

- `LeadEvent` — append-only lifecycle (created / contacted / qualified / converted / rejected / archived / note / other).
- `LeadWebhookDelivery` — outbox per `(lead, event_type)` with `status ∈ {pending, sending, delivered, failed, dead}` + attempts, next_attempt_at, last_status_code, last_error, response_excerpt, target_url_domain, idempotency_key, payload_version.

## 3. What the staff sees in Django admin today

From `apps/crm/admin.py`:

| Admin | Registered? | list_display | list_filter | search | Notes |
|---|---|---|---|---|---|
| `LeadAdmin` | yes | created_at, full_name, email, phone, country, case_type, status, mandate_status, mandate_signed, priority, assigned_to | status, mandate_status, mandate_signed, priority, country, case_type, preferred_language, assigned_to | public_id, first_name, last_name, email, phone | Fieldsets, inlines (LeadEvent), 3 bulk actions (contacted / qualified / archive), `has_add_permission=False`. |
| `LeadEventAdmin` | yes | created_at, lead, event_type, message | event_type | lead__public_id, message | Fully read-only (CRUD all denied). |
| `LeadWebhookDeliveryAdmin` | **NO — gap** | n/a | n/a | n/a | The model exists, gets rows on every Lead create (when env-gated dispatcher is on), and the management command `dispatch_crm_webhooks` processes them. But the Studio has **no admin window** into pending / failed / dead deliveries. Today the only way to inspect is `python manage.py shell` or the DB directly. |

## 4. Friction points (what slows the Studio down today)

Observed by reading the code as a Studio user would walk through it:

1. **No double-consent visibility on the Lead list.** The list shows `mandate_status` and `mandate_signed`, which is fine — but a Studio user cannot answer at a glance "did this Lead give both GDPR consents?" without opening the row. With both consents being a prerequisite for any contact, surfacing them on the list is high-value.
2. **No linked-simulation visibility on the Lead list.** Knowing whether the Lead arrived from the funnel (`simulation` FK present) or from a cold contact form changes how the Studio prioritises the contact. Currently the row has to be opened to find out.
3. **No webhook-delivery visibility anywhere.** When the n8n / CRM webhook fails on a Lead, the Studio doesn't see it — the failure is logged, but the staff inbox doesn't surface "this Lead's CRM sync is failing". Even worse: no admin page lists pending / failed / dead deliveries, so a stuck webhook is invisible until someone re-reads `dispatch_crm_webhooks` output.
4. **No filter on consent flags or created-at range.** Today the Studio can filter by status / case_type / mandate but not by privacy consent — useful for compliance audits ("show me all Leads with `privacy_consent_given=False`" — should always be empty, but the moment you can't filter you can't audit).
5. **Brittle bulk-action code in `mark_as_contacted`.** Uses `Lead._meta.get_field("status").choices[1][0]` to resolve the literal "contacted" — order-dependent and silently wrong if the enum order changes. The other two actions hard-code the string. Inconsistent. Low-risk, easy to fix.
6. **No model-level helpers.** Common Studio questions ("does this Lead have a valid double consent?", "does it have a linked simulation?", "what's the webhook delivery summary?") have to be re-derived in templates / shells. Three small properties on `Lead` would centralise the answer.
7. **No CSV/XLSX export route from admin.** Out of scope for this iter (explicitly listed in §5 as something we will NOT add — premature for the current Studio volume). Documented as a follow-up only.
8. **The `source_path` field exists but doesn't surface a friendly source label.** A short derived label ("contact-form", "from-result-page", "from-case-type-landing") is more useful at a glance than a raw URL. Computed cheaply from `simulation_id` + `source_path` querystring — no DB migration.

## 5. What we will NOT do in this iter

These are explicitly out of scope to keep the iter focused and reversible:

- **No new model fields.** No migration. The improvements ride on what's already in the schema.
- **No bulk manual webhook re-send from admin.** Re-firing a webhook touches a third-party system; the env-gated `dispatch_crm_webhooks` command is the single authoritative path. If a delivery is stuck, the operator triggers retries via the command, not via admin clicks. Documented as a follow-up *only if and when* the Studio actually asks for it.
- **No CSV / XLSX export of leads from admin.** Premature for the current volume + leak risk for sensitive categories (`message`, consent versions). Documented as a separate compliance-reviewed follow-up.
- **No new automation.** No new email, no new webhook event types, no new Celery task, no new signal. The iter only changes how staff sees existing rows.
- **No France activation.** France remains review-gated; nothing in this iter touches calculation or sources.
- **No CRM rewrite.** We extend Django admin. We do not introduce a separate admin UI.
- **No mass deletion / anonymisation action.** Lead anonymisation is governed by `apps.compliance.retention` and the audit ledger; admin actions that delete or anonymise are out of scope for this iter.
- **No new permission scheme.** We use Django's existing staff/superuser permissions. Per-role granularity is a separate compliance iter.

## 6. Quick wins (phase 2-3 implementation plan)

### 6.1 Lead admin list — add columns

Extend `LeadAdmin.list_display` to surface what's currently a "open the row to check":

- `has_valid_double_consent` — green check / red cross derived from both denormalised consent flags + their timestamps.
- `has_linked_simulation` — yes/no derived from `simulation_id`.
- `source_label` — derived short label: `wizard` (simulation present), `case-type` (`source_path` contains `/case-types/`), `contact` (default).
- `webhook_status_summary` — one-line summary derived from the row's `webhook_deliveries` (e.g. `delivered` / `pending(1/5)` / `dead(2025-…)` / `—`).

Reorder so that the most-scanned columns sit first: `created_at`, `full_name`, `email`, `country`, `case_type`, `status`, `mandate_status`, `has_valid_double_consent`, `has_linked_simulation`, `source_label`, `webhook_status_summary`, `priority`, `assigned_to`.

### 6.2 Lead admin filters

Add to `LeadAdmin.list_filter`:

- `privacy_consent_given`
- `special_categories_consent_given`
- `simulation` presence (custom `SimpleListFilter` — "linked / unlinked")
- `created_at` already covered by `date_hierarchy`; keep it.

Keep all existing filters.

### 6.3 Lead admin search

Already covers `public_id`, `first_name`, `last_name`, `email`, `phone_number`. **Sufficient. No change.**

### 6.4 Lead admin readonly fields

Already readonly: `public_id`, `user`, `session_key`, `consent_record`, `simulation`, `ip_address`, `user_agent`, `source_path`, `utm_*`, `created_at`, `updated_at`. **Extend to also lock**:

- consent denormalised fields (`privacy_consent_given/_at/_version` + `special_categories_consent_given/_at/_version`) — the source-of-truth is `ConsentRecord`, the Lead row is the audit snapshot; staff must not be able to flip them by hand.
- mandate timestamp + version + source (`mandate_signed_at`, `mandate_version`, `mandate_source`) — set by `apps.compliance.mandate` services, not by hand-editing the row.

The two booleans `mandate_signed` and `mandate_status` stay editable — the Studio has to be able to record signature acceptance through admin if needed.

### 6.5 Lead admin fieldsets

Keep the existing fieldset structure. Add a single new collapsed section: **"Webhook outbox (CRM)"** — read-only summary of the related `LeadWebhookDelivery` rows + a link to the dedicated webhook admin (see §6.7).

### 6.6 Bulk action cleanup

Tighten `mark_as_contacted` to use `LeadStatus.CONTACTED` directly instead of `Lead._meta.get_field(...).choices[1][0]`. Symmetric to the other two actions. No behaviour change.

### 6.7 Webhook admin — register `LeadWebhookDelivery`

New `LeadWebhookDeliveryAdmin` (currently missing entirely):

- `list_display`: `created_at`, `lead`, `event_type`, `status`, `attempts`, `next_attempt_at`, `delivered_at`, `last_status_code`, `target_url_domain`.
- `list_filter`: `status`, `event_type`.
- `search_fields`: `lead__public_id`, `idempotency_key`.
- `readonly_fields`: every field. The dispatcher owns this table; admin is read-only audit.
- `date_hierarchy`: `created_at`.
- No CRUD: `has_add_permission` and `has_delete_permission` both `False`; `has_change_permission` `False` too (it's pure audit).
- **Important sanity**: `response_excerpt` is explicitly capped to the model field's `max_length=500` and is admin-rendered as-is — we do not add any expansion that would risk dumping the full HTTP response body. Tested.

### 6.8 Model helpers (phase 3)

Three `@property` methods on `Lead`:

- `has_valid_double_consent` → both `privacy_consent_given=True` and `special_categories_consent_given=True` AND both timestamps non-null AND both versions non-empty.
- `has_linked_simulation` → `simulation_id is not None`.
- `webhook_delivery_status_summary` → short label derived from related `webhook_deliveries`:
  - no row → `"—"`
  - any `delivered` → `"delivered"`
  - any `dead` → `"dead"`
  - any `failed` → `"failed"`
  - any `pending` / `sending` → `"pending(attempts/max)"` using the most-recent row
  - everything else → `"—"`

All three are pure — no new query when prefetched. They are useful in admin (the new columns reuse them) and in tests + future templates.

## 7. Acceptance criteria (gate phase 6)

1. **Audit doc + improvements doc both present** (this file + phase 6 report).
2. **`LeadAdmin` list_display** contains the four new derived columns + the existing essential columns.
3. **`LeadAdmin` list_filter** contains `privacy_consent_given`, `special_categories_consent_given`, plus the existing filters.
4. **`LeadAdmin` search_fields** unchanged (already sufficient).
5. **`LeadAdmin` readonly_fields** locks all consent denormalised fields + mandate timestamps / version / source. `mandate_signed` and `mandate_status` remain editable.
6. **`LeadWebhookDeliveryAdmin`** is registered with the spec in §6.7, fully read-only.
7. **Three `Lead` properties** implemented as described, with tests.
8. **Bulk action** `mark_as_contacted` uses the enum value, not list indexing.
9. **No model changes** (no migration created or applied during this iter).
10. **Test green**: `pytest -q` continues to pass (≥2114 + the new PRODUCT-7 tests).
11. **Hygiene strict green**: no findings.
12. **Non-IT readiness unchanged**: APPROVED-PARTIAL × 4.
13. **No PII or webhook secret leaks in admin** — explicit test pin: `response_excerpt` is capped to its model `max_length` and never expanded; HMAC secret never read into a template; full webhook URL never displayed (only `target_url_domain`).

## 8. Risks and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Admin change touches a column that's part of a sorted query and breaks pagination | low | All new columns are derived (no DB sort). `list_display` order changes only — no `ordering` change on the admin. |
| New property does an N+1 query on the admin list (`webhook_delivery_status_summary` iterates `lead.webhook_deliveries`) | medium | Add `get_queryset(self, request)` on `LeadAdmin` that does `prefetch_related("webhook_deliveries")`. Tested. |
| `response_excerpt` accidentally leaks a long HTTP response when admin renders it | medium | The model already caps at `max_length=500`. The admin renders it through Django's default text-area widget which truncates by CSS. Plus a test pin scans the admin rendered HTML and asserts the rendered text ≤ 500 chars. |
| Staff with admin access could flip a consent flag by hand and break the audit ledger | high | Phase 2 moves all consent denormalised fields + mandate timestamps to readonly_fields. Test pin asserts they appear in `readonly_fields`. |
| Bulk action regression on `mark_as_contacted` | low | Phase 2 replaces the brittle indexing with `LeadStatus.CONTACTED`. Existing PRODUCT-2 / F6 tests still cover the action; new test pins the exact value set. |
| Brittle dependency on prefetch in webhook summary | low | The property is defensive: it gracefully handles `webhook_deliveries.all()` being empty. Test pin covers the no-rows case + the delivered + the dead case. |

## 9. Implementation plan (phases 2-6)

1. **Phase 2** — admin: edit `apps/crm/admin.py` to extend `LeadAdmin.list_display`, `list_filter`, `readonly_fields`, tighten `mark_as_contacted`, and add `LeadWebhookDeliveryAdmin`.
2. **Phase 3** — helpers: add three `@property` methods on `Lead`, plus a custom `SimpleListFilter` for "has linked simulation" used in §6.2.
3. **Phase 4** — tests: new `apps/crm/test_product_7_admin_workflow.py` with the 12 pins enumerated in §7.
4. **Phase 5** — notes/screenshots: write `docs/screenshots/.../after/product-crm-staff-lead-workflow/NOTES.md`. Browser login via Playwright is heavyweight for an admin-only change; the NOTES.md documents what a Studio user sees and is sufficient as a record. (If the screenshots fit budget at end-of-iter, append a single PNG of the Lead admin list with the new columns.)
5. **Phase 6** — improvements report: `docs/product/CRM_STAFF_LEAD_WORKFLOW_IMPROVEMENTS_2026-05-12.md` (same shape as PRODUCT-5 / PRODUCT-6 reports).
6. **Commit**: `product-7: improve crm staff lead workflow visibility`. Single commit, no push.

## 10. Rollback

A single `git revert` of the PRODUCT-7 commit removes: the admin extensions, the `LeadWebhookDeliveryAdmin` registration, the three model properties, the custom list filter, the new test file, this audit, the improvements report, the notes. No DB rollback needed — no migration. The pre-PRODUCT-7 admin returns identical bytes after revert.
