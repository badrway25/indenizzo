# PRODUCT-8 — staff lead activity timeline (2026-05-13)

This folder documents what the Studio sees on a single Lead admin
detail page after `product/studio-lead-activity-timeline` lands. The
change is admin-only (no public-facing UI); a structured description
adds more signal than a screenshot would.

The audit + improvements report carry the full rationale:

- `docs/product/CRM_LEAD_ACTIVITY_TIMELINE_AUDIT_2026-05-12.md`
- `docs/product/CRM_LEAD_ACTIVITY_TIMELINE_IMPROVEMENTS_2026-05-12.md`

## 1. Where the timeline lives — `/admin/crm/lead/<id>/change/`

A new fieldset titled **"Activity timeline"** is added between the
mandate section and the existing "Webhook outbox (CRM)" section.
The fieldset is **not collapsed** because the Studio opens this row
specifically to see what's been happening on it.

The fieldset shows two readonly entries:

### 1.1 Next staff action

A short, one-line operational hint derived purely from workflow
flags:

```
Next staff action:   Review linked simulation and contact client
```

Examples by branch:

| Lead state | next_staff_action |
|---|---|
| `status=received`, no linked simulation | `Review new lead and decide next step` |
| `status=received`, linked simulation | `Review linked simulation and contact client` |
| any status, webhook `dead` | `Webhook delivery failed - check integration` |
| `status=qualified`, mandate not signed | `Mandate not signed - prepare engagement letter` |
| `status=contacted` | `Waiting for Studio review` |
| `status=converted` + `mandate_signed=True` | `Engagement active - manage the case offline` |
| `status=archived` / `status=rejected` | `Archived - no further action` |
| webhook still retrying | `Webhook still retrying - monitor delivery` |
| fallback | `Ready for manual follow-up` |

These strings are deliberately operational. They describe **what to
do next on the workflow**, not **what the case is worth**. The
Studio decides the merit; the helper only summarises *where in the
funnel* the Lead currently sits. Banned-promise phrases are
scanned out in tests (`test_next_staff_action_strings_have_no_banned_phrases`).

### 1.2 Activity timeline

A vertical list of timestamped entries, one per event, ordered
chronologically ascending. Each entry has:

- a coloured left border (severity: info / success / warning / error);
- a small first line: `YYYY-MM-DD HH:MM · <category>`;
- a bold second line: the label;
- a third line: a short description;
- a monospace fourth line: the source row identifier
  (e.g. `crm.LeadWebhookDelivery#42`).

Example for a Lead that came from the wizard funnel, gave both
consents, and whose webhook successfully delivered to a CRM:

```
| (info)    | 2026-05-13 09:55 · simulation
|           |  Simulation linked
|           |  Lead arrived via the wizard funnel.
|           |  cases.Simulation#1a2b...
|
| (success) | 2026-05-13 10:00 · consent
|           |  Privacy consent recorded
|           |  GDPR art. 6 consent given at contact form submit.
|           |  crm.Lead#5f9e...
|
| (success) | 2026-05-13 10:00 · consent
|           |  Special-categories consent recorded
|           |  GDPR art. 9 consent given at contact form submit.
|           |  crm.Lead#5f9e...
|
| (info)    | 2026-05-13 10:00 · lead
|           |  Lead created
|           |  New contact request received.
|           |  crm.Lead#5f9e...
|
| (info)    | 2026-05-13 10:00 · webhook
|           |  Webhook enqueued
|           |  Outbox row created for CRM delivery to hooks.example.
|           |  crm.LeadWebhookDelivery#42
|
| (success) | 2026-05-13 10:02 · webhook
|           |  Webhook delivered
|           |  CRM receiver returned 2xx for delivery to hooks.example.
|           |  crm.LeadWebhookDelivery#42
|
| (info)    | 2026-05-13 10:00 · mandate
|           |  Mandate required (default)
|           |  Lead starts as a pre-contractual contact.
|           |  An engagement requires a separate written mandate.
|           |  crm.Lead#5f9e...
```

For a Lead with a failed CRM integration the webhook entry shows as
`(error) — Webhook dead — max attempts reached` with `target=hooks.example`
and the last HTTP status code in its metadata.

For a Lead that has signed a mandate, a `(success) — Mandate signed`
entry appears at `mandate_signed_at` carrying the version + source.

## 2. What is NOT in the timeline

By design, the following pieces of data never appear:

- `Lead.message` — the contact form free text. The aggregator reads
  no field that could carry user-supplied PII into the rendered
  string.
- `Lead.email`, `Lead.phone_number`, `Lead.first_name`, `Lead.last_name`.
- The HMAC secret (read from `settings.CRM_WEBHOOK_SECRET` at
  dispatch time only — never persisted, never read by the timeline).
- The full webhook URL — only the `target_url_domain` host snapshot
  is included.
- The raw webhook payload — never persisted; rebuilt on demand.
- Special-categories detail (health / family / judicial). The
  special-categories consent entry reports "given at T (version V)"
  and nothing else.

These exclusions are pinned by `test_timeline_does_not_leak_secret_url_or_pii`.

## 3. Safety contract of the rendered HTML

The admin readonly field uses `django.utils.html.format_html` +
`format_html_join`. Every interpolated value passes through
`conditional_escape`. The only "trusted" string in the template is
the severity colour, which comes from a fixed dict
(`_SEVERITY_COLORS`) keyed by a static enum value — never by user
input. This is pinned by `test_admin_activity_timeline_render_has_no_js`
which feeds a hostile `<script>alert(1)</script> javascript:alert(2)`
string into a LeadEvent message, renders the timeline, and asserts:

- no `<script` tag appears in the output (escaped to `&lt;script&gt;`);
- no `href="javascript:..."` attribute is produced;
- no `on...` event-handler attribute is produced.

## 4. Performance

`LeadAdmin.get_queryset` already prefetched `webhook_deliveries`
(PRODUCT-7). PRODUCT-8 adds `select_related("simulation")` and
`prefetch_related("events")`. Opening a Lead detail page with a
linked simulation + 3 lifecycle events + 5 webhook deliveries
triggers a single batch of SQL queries — no N+1 across the timeline.

## 5. What is NOT added by this iter

- No "retry webhook" button or admin action. The retry path remains
  the env-gated `dispatch_crm_webhooks` management command. This is
  intentional — webhook re-fire CLI is a candidate for PRODUCT-9.
- No new model, no new table, no migration.
- No new automation, no email, no signal handler.
- No public-facing UI change.
- No France activation.

## 6. Why no PNG

A live admin screenshot would require:

1. Spinning up the dev server,
2. Creating a superuser, logging in via Playwright,
3. Seeding a Lead with a linked Simulation + a LeadEvent + several
   LeadWebhookDelivery rows in different states,
4. Capturing the detail page.

The visual signal (a list of timestamped rows in admin form fields)
is what the structured example above already conveys. Test pins
verify the rendered HTML stays escape-safe and PII-free. If a
stakeholder later asks for a PNG, this folder is the place to add
it.
