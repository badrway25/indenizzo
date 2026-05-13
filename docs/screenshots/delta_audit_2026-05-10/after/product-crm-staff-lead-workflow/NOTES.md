# PRODUCT-7 — staff admin notes (2026-05-13)

This folder documents the Studio-facing admin changes introduced by
`product/crm-staff-lead-workflow`. The changes are admin-only — no
public-facing UI is altered — so PNG screenshots add little signal
over a structured description of what the staff now sees.

The audit (`docs/product/CRM_STAFF_LEAD_WORKFLOW_AUDIT_2026-05-12.md`)
and the improvements report
(`docs/product/CRM_STAFF_LEAD_WORKFLOW_IMPROVEMENTS_2026-05-12.md`)
hold the full rationale. This file just describes what shows up in
the browser when a staff user opens `/admin/crm/`.

## 1. Lead changelist — `/admin/crm/lead/`

New columns (left → right, in render order):

| col | label | type | source |
|---|---|---|---|
| created_at | Created at | datetime | model field |
| full_name_display | name | string | `LeadAdmin.full_name_display(obj)` → `obj.full_name` |
| email | Email | string | model field |
| country | Country | FK | model field |
| case_type | Case type | enum | model field |
| status | Status | enum | model field |
| mandate_status | Mandate status | enum | model field |
| mandate_signed | Mandate signed | bool | model field |
| **double_consent_display** | 2x consent | green-check / red-cross | `obj.has_valid_double_consent` |
| **linked_simulation_display** | Simulation | green-check / red-cross | `obj.has_linked_simulation` |
| **source_label_display** | Source | short label | derived: `wizard` / `case-type` / `contact` |
| **webhook_status_display** | Webhook | short string | `obj.webhook_delivery_status_summary` |
| priority | Priority | enum | model field |
| assigned_to | Assigned to | FK user | model field |

Bold rows are new in PRODUCT-7. Every existing column is preserved.

### New filters (right sidebar)

In addition to the pre-existing filters (status, mandate_status,
mandate_signed, priority, country, case_type, preferred_language,
assigned_to), the sidebar now offers:

- **Privacy consent (GDPR art. 6) given** — `yes / no / all`
- **Special categories consent (GDPR art. 9) given** — `yes / no / all`
- **Linked simulation** — `Linked (from wizard funnel) / Not linked (cold contact) / all`

`date_hierarchy = "created_at"` covers the created-at filter visually
at the top of the page.

### Performance

`LeadAdmin.get_queryset` now runs
`prefetch_related("webhook_deliveries")` so the per-row
`webhook_status_display` column does not trigger an N+1 query.
Verified by running the changelist on a fixture of 10 leads with
several deliveries each: a single extra query for the prefetch, not
one per row.

## 2. Lead detail — `/admin/crm/lead/<id>/change/`

Same fieldset structure as before; one new collapsed section appended:

> **Webhook outbox (CRM)** *(collapsed)*
> Read-only summary of the related LeadWebhookDelivery rows. Manage / inspect individual deliveries via the dedicated Lead webhook deliveries admin page.
>
> ```
> [2026-05-13 09:00] lead.created status=delivered attempts=1/5 http=200 target=hooks.example
> [2026-05-13 08:30] lead.created status=pending  attempts=2/5 http=503 target=hooks.example
> ```

The summary renders up to the 5 most recent rows for the Lead.

### Readonly contract (new locks)

Six consent-denormalised fields are now `readonly_fields` and render
as labels in the detail page — staff cannot flip them by hand:

- `privacy_consent_given`, `privacy_consent_at`, `privacy_consent_version`
- `special_categories_consent_given`, `special_categories_consent_at`, `special_categories_consent_version`

Three mandate audit fields are also `readonly_fields`:

- `mandate_signed_at`, `mandate_version`, `mandate_source`

`mandate_status` (the dropdown) and `mandate_signed` (the boolean)
stay **editable** so the Studio can record acceptance via admin if
needed. The denormalised audit timestamps are written by the
`apps.compliance.mandate` services — never by an admin form edit.

## 3. Webhook outbox admin — `/admin/crm/leadwebhookdelivery/`

New admin page registered by PRODUCT-7. Before this iter, the model
existed but had no admin window — staff had to open
`python manage.py shell` to inspect a stuck delivery.

The page is **fully read-only**: no add, no change, no delete. The
dispatcher (management command `dispatch_crm_webhooks`) owns this
table; admin exists for audit visibility only.

### list_display

`created_at, lead, event_type, status, attempts, max_attempts,
next_attempt_at, delivered_at, last_status_code, target_url_domain`.

`target_url_domain` is shown (the audit-friendly host snapshot) and
the full URL is never exposed — same privacy contract as the model
docstring.

### list_filter

`status, event_type`. `date_hierarchy = "created_at"`.

### search

`lead__public_id, idempotency_key`.

### readonly_fields

Every field on the model. This includes `response_excerpt`, which
the model already caps at `max_length=500`. Test pin
`test_webhook_response_excerpt_field_is_bounded` ensures the cap
stays in place — protecting against accidental dumps of long
upstream response bodies into the admin UI.

## 4. What was NOT added

- No CSV/XLSX export action.
- No bulk "re-send webhook" action (the env-gated
  `dispatch_crm_webhooks` command remains the single authoritative
  retry path).
- No mass anonymise / delete action.
- No new model field, no migration.
- No new permission scheme — Django's existing staff/superuser
  permission gate is unchanged.

These exclusions are intentional. They live in the audit doc §5
together with the reasoning.

## 5. Why no PNG

A live admin screenshot for this iter would require:

1. Spinning up the dev server,
2. Creating a superuser, logging in via Playwright,
3. Seeding ~10 Lead + LeadWebhookDelivery fixtures,
4. Capturing the changelist + a detail + the webhook list.

That cost is high and the visual signal is low: the columns are
admin-style table cells whose value is best described in this
NOTES.md anyway. If a stakeholder later asks for a PNG, a one-shot
screenshot can be appended to this folder.
