# P28 — Lead / CRM payload contract (dossier-origin)

Date: 2026-06-28. How a public result becomes a structured, privacy-safe lead
payload for the Studio (email) and an external CRM (webhook). Nothing here sends
in dev/test unless the gating settings are configured; no health detail or
document contents leave the platform.

## Where the data lives

A lead is created by `apps/crm/services.py::create_lead_from_form()` from the
existing `ContactForm`. The **dossier origin** (which result produced the lead)
travels in the send-CTA query string — `/contact/?flow=…&result_kind=…&readiness=…`
(plus `?sim=<uuid>` for estimates, `?country=&category=` to prefill) — and is
whitelisted + bounded by `_sanitize_origin()` before being merged into the
`LeadEvent(CREATED).metadata` JSON. **No migration**: the metadata is a JSONField.

## Captured per lead (no migration)

| Field | Source | On `Lead` / `LeadEvent` |
|-------|--------|--------------------------|
| first/last name, email, phone | contact form | `Lead` |
| preferred_language (lingua) | contact form | `Lead.preferred_language` |
| country | form (prefilled from `?country` / linked sim) | `Lead.country` |
| category (case_type) | form (prefilled from `?category` / linked sim) | `Lead.case_type` |
| message | contact form | `Lead.message` |
| source_path (URL provenance) | request | `Lead.source_path` |
| linked simulation | `?sim=<uuid>` | `Lead.simulation` |
| **flow_type** | `?flow` | `LeadEvent.metadata.flow` |
| **result_kind** | `?result_kind` | `LeadEvent.metadata.result_kind` |
| **readiness_level** | `?readiness` | `LeadEvent.metadata.readiness` |
| consent (privacy + art. 9) | form checkboxes | `Lead.privacy_consent_*` / `special_categories_consent_*` + 2 `ConsentRecord` |

Intentionally **NOT** captured into the payload: the user's specific health
answers, the full document list contents, IP/user-agent (kept on the Lead for
audit but excluded from the email body and webhook), the calculated amount.

## Email to the Studio

`apps/crm/email_notifications.py::send_lead_notification()` — gated by
`LEAD_NOTIFICATION_ENABLED` **and** a non-empty `LEAD_NOTIFICATION_TO_EMAILS`.
Dev backend is console; tests use locmem; **no real email is sent unless both
settings are configured**. Body is privacy-minimised: public_id, timestamp,
name, email, phone, country, case_type, language, linked-simulation public_id.
Excludes ip_address, user_agent, session_key, internal_notes. Failure-soft.

## External CRM webhook (n8n / HubSpot / …)

`apps/crm/webhooks.py` — gated by `CRM_WEBHOOK_ENABLED` (default **False**), so
nothing is dispatched until a URL + secret are configured. Signed HMAC outbox
with idempotency + retry. Recommended dossier-aware payload mapping (v1):

```jsonc
{
  "event": "lead.created",
  "lead_public_id": "<uuid>",
  "created_at": "<iso8601>",
  "source_channel": "public_result",          // from LeadEvent context
  "source_page": "<Lead.source_path>",         // URL provenance
  "country": "<Lead.country.code>",
  "category": "<Lead.case_type>",              // case type
  "flow_type": "<metadata.flow>",              // inail | road_estimate | …
  "result_kind": "<metadata.result_kind>",     // pre_check | estimate | comparison | applicable_law
  "readiness": "<metadata.readiness>",         // ready | consolidating | initial | calculated
  "has_simulation": true,
  "lead_message": "<Lead.message>",
  "consent": { "privacy": true, "special_categories": true,
               "privacy_version": "…", "special_categories_version": "…" },
  "language": "<Lead.preferred_language>"
  // never: amount, health answers, document contents, ip, user_agent
}
```

`CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY` (default False) controls whether a
coarse special-category flag is included. The amount is **never** sent.

## Status

Capture + email + (gated) webhook outbox are live and test-covered. The
external CRM endpoint is not configured in this environment, so this file is the
contract to wire when an endpoint exists — no production dispatch happens now.
