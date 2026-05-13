# CRM lead activity timeline — audit (phase 1) — 2026-05-12

**Iter**: `PRODUCT-8-studio-lead-activity-timeline`
**Branch**: `product/studio-lead-activity-timeline`
**Companion of**: `docs/product/CRM_LEAD_ACTIVITY_TIMELINE_IMPROVEMENTS_2026-05-12.md` (phase 7 report — written after implementation).
**Predecessors**: PRODUCT-7 (CRM staff workflow — `docs/product/CRM_STAFF_LEAD_WORKFLOW_*.md`), F-p1-crm-1-webhook-dispatcher (LeadWebhookDelivery), F-p0-leg-2-mandate, F-p0-leg-3-consent.

This iter does **not** add new tracking. It aggregates timestamps already present across CRM / cases / compliance into a single read-only chronological view that the Studio can scan on the Lead admin detail page.

## 1. What's tracked today (and where)

| Event | Source row | Timestamp field | Notes |
|---|---|---|---|
| Lead created | `crm.Lead` | `created_at` | Always present. |
| Linked simulation existed | `cases.Simulation` (via `Lead.simulation` FK) | `simulation.created_at` | Optional. When the user came from the wizard funnel. |
| Privacy consent (GDPR art. 6) given | `crm.Lead` denormalised | `privacy_consent_at` | Always present at Lead create (the contact form requires it). Source-of-truth is `compliance.ConsentRecord` keyed by `purpose=lead_contact`, but the denormalised field is sufficient for a timeline entry. |
| Special-categories consent (GDPR art. 9) given | `crm.Lead` denormalised | `special_categories_consent_at` | Same as above (purpose=`special_categories_processing`). |
| LeadEvent (lifecycle) | `crm.LeadEvent` | `created_at`, `event_type` | Append-only. Populated by `create_lead_from_form` (`CREATED`) and by `LeadAdmin` actions (`CONTACTED`, `QUALIFIED`, `ARCHIVED`). Other admin-form edits to `status` do **not** auto-create a LeadEvent — documented gap. |
| Webhook enqueued | `crm.LeadWebhookDelivery` | `created_at` | One row per `(lead, event_type)` when `CRM_WEBHOOK_ENABLED=True`. |
| Webhook attempts | `crm.LeadWebhookDelivery` | `last_attempt_at`, `attempts` | Updated by the dispatcher each try. No per-attempt row — only the latest attempt timestamp is kept. |
| Webhook delivered | `crm.LeadWebhookDelivery` | `delivered_at`, `status=delivered` | Terminal success. |
| Webhook failed / dead | `crm.LeadWebhookDelivery` | `last_attempt_at`, `status ∈ {failed, dead}` | Terminal failure states. |
| Lead contacted | `crm.Lead` | `contacted_at` | Set by the `mark_as_contacted` admin action; pairs with a LeadEvent. |
| Lead converted | `crm.Lead` | `converted_at` | Set by `apps.compliance.mandate.mark_mandate_signed` (flips Lead status to `CONVERTED`). |
| Mandate required (default) | `crm.Lead` | (no own timestamp — fall back to `Lead.created_at`) | `MandateStatus.REQUIRED` is the default for every new Lead. |
| Mandate signed | `crm.Lead` + `compliance.MandateAcceptance` | `mandate_signed_at`, `signed_at` | The denormalised flag on `Lead` is the audit snapshot; the append-only `MandateAcceptance` is the source-of-truth. |
| PrivacyAuditEvent (CONSENT_GIVEN / WITHDRAWN / DELETION_*) | `compliance.PrivacyAuditEvent` | `created_at` | Cross-cuts users + simulations + leads; linked via `(target_model, target_object_id)`. Out of scope for the lead-centric timeline in *this* iter — the relevant transitions for a lead already appear via Lead / Mandate / Webhook above. Documented as a possible follow-up. |

## 2. Events that exist but are *not* in scope for this iter

- **`compliance.PrivacyAuditEvent` rows** — useful for a compliance officer's view, but the per-Lead timeline is for the Studio's day-to-day. Adding a row per privacy event creates noise (consent given is already implicit in the Lead consent timestamps). Documented as PRODUCT-? follow-up.
- **Anonymisation events (`Lead.anonymized_at`)** — if/when retention fires. Currently no row in scope; the field exists, the timeline reads it if non-null but adds the entry only when set.
- **`SimulationEvent`** — append-only per-simulation events. Useful when looking at a simulation, but redundant on the Lead timeline (the Lead-level "linked simulation" entry is sufficient).

## 3. Events that would require a new model (NOT implemented)

- **Lead status transition history** — today only the current `status` column exists. Past transitions are only recoverable when a LeadEvent was created at the moment of the change (admin actions). A truly authoritative history would need a `LeadStatusHistory` table (one row per transition) with `from_status`, `to_status`, `changed_at`, `changed_by`. **Out of scope** for this iter — the LeadEvent rows we already have cover the lifecycle transitions the Studio actually triggers (contacted / qualified / archived); the missing case is hand-edits on the admin form, which is acceptable until volume demands more.
- **Webhook attempt history** — today only the latest attempt is on the row. Per-attempt detail would need a `LeadWebhookAttempt` child table. **Out of scope** — the latest-attempt summary covers operational needs ("is it stuck and why").
- **Mandate state-machine history** — `MandateAcceptance` rows are already append-only; what we don't have is "MandateStatus changed to SENT at time T". Out of scope; the Mandate signed event is the load-bearing transition.

## 4. Privacy / GDPR guardrails

Hard rules enforced by tests in phase 5:

| Rule | Test pin |
|---|---|
| **No HMAC secret in the timeline.** | The webhook secret is read from settings at dispatch time and never persisted; the timeline never reaches for `settings.CRM_WEBHOOK_SECRET`. Test pin: scan the rendered timeline for the configured secret token — zero matches. |
| **No full webhook URL in the timeline.** | Only `target_url_domain` (host snapshot) is included in timeline metadata when relevant. Test pin: regex `https?://` is absent from any timeline item's description / metadata. |
| **No raw webhook payload in the timeline.** | The dispatcher already does not persist the payload (rebuilt on demand). The timeline never calls `build_lead_payload`. Test pin: `lead.first_name` / `lead.email` does not appear inside webhook timeline items (only their existence is reported, not their contents). |
| **No special-categories detail in the timeline.** | The special-categories consent timeline entry reports "given at T (version V)" — never any health/judicial/family detail. The detail lives only in the encrypted-at-rest Lead row + audit ledger. Test pin: timeline strings do not contain `Lead.message`. |
| **No legal-advisory phrasing.** | `next_staff_action` is conservative: it describes *what to do operationally* (check integration / contact client / verify mandate), never *what the case is worth*. Banned-phrase scan re-uses the PRODUCT-2/3/4/6 list. |
| **No bottoni di retry webhook nel timeline.** | The timeline is read-only HTML. No `<form>`, no `<button>`, no `<a href>` to a retry endpoint. Webhook re-fire remains CLI-only (out of scope; PRODUCT-9 candidate). |

## 5. Implementation choice — aggregate, do not persist

There are two ways to ship a timeline:

1. **New `LeadTimelineEntry` table** — written by signals/services as transitions happen. Pros: cheap reads, immutable history. Cons: requires migration, duplicates data already stored elsewhere, introduces a write path the receivers don't own, and locks the data shape early.
2. **Aggregator over existing rows** — read the Lead + its related rows (Simulation, LeadEvent, LeadWebhookDelivery, MandateAcceptance) and build the timeline on the fly. Pros: no migration, no duplication, evolves with the upstream data. Cons: O(n_related) per render; on a heavy admin list this would need prefetch.

The conservative choice is **#2 — aggregator**. The Lead admin detail view is opened one Lead at a time; even with all four child relations prefetched the query budget is < 10 SQL statements per render. The timeline shape can change in code without a data migration, and there is no risk of the new write path silently diverging from the existing audit ledger.

**Decision**: ship `apps/crm/timeline.py:build_lead_timeline(lead)` as a pure function that aggregates existing rows. No new model. No new migration. No new write path.

## 6. Data structure

The aggregator returns a list of immutable `LeadTimelineItem` instances (frozen dataclass):

```python
@dataclass(frozen=True)
class LeadTimelineItem:
    timestamp: datetime          # ordering key — UTC, source-aware
    category: str                # "lead" | "simulation" | "consent" | "webhook" | "mandate" | "lifecycle"
    severity: str                # "info" | "success" | "warning" | "error"
    label: str                   # short title (translatable)
    description: str             # human-readable detail (translatable)
    source: str                  # the model row this came from, e.g. "crm.Lead#42"
    metadata: dict[str, str]     # short, safe tech tags (never PII / secrets / amounts)
```

`category` and `severity` are short string enums (not Django enums) so the helper is independent of any DB type.

## 7. Events the timeline will surface (this iter)

Ordered by likely chronological appearance:

1. **`simulation`** — "Simulation linked" *(severity: info)*. Present only when `Lead.simulation_id is not None`. Timestamp = `simulation.created_at`. Source = `cases.Simulation#<public_id>`.
2. **`consent`** — "Privacy consent recorded" *(severity: success)*. Timestamp = `Lead.privacy_consent_at`. Metadata: version.
3. **`consent`** — "Special-categories consent recorded" *(severity: success)*. Timestamp = `Lead.special_categories_consent_at`. Metadata: version.
4. **`lead`** — "Lead created" *(severity: info)*. Timestamp = `Lead.created_at`. Metadata: country, case_type, source-label heuristic (PRODUCT-7).
5. **`lifecycle`** — one entry per `LeadEvent` *(severity from a map: CREATED=info, CONTACTED=info, QUALIFIED=success, CONVERTED=success, REJECTED=warning, ARCHIVED=warning, NOTE=info, OTHER=info)*.
6. **`webhook`** — per `LeadWebhookDelivery`, two possible entries:
   - "Webhook enqueued" *(severity: info)* at `created_at`. Metadata: event_type, target_url_domain (no full URL).
   - "Webhook delivered / failed / dead" *(severity: success / error / error)* at `delivered_at` (or `last_attempt_at` for failures), only if `status ∈ {delivered, failed, dead}`. Metadata: status code, attempts/max, target_url_domain.
   - "Webhook pending" *(severity: warning)* at the most recent `last_attempt_at` (if any) when the row is still pending — annotation only, not a separate row; merged with the enqueued entry if no attempt happened yet.
7. **`mandate`** — "Mandate required (default)" *(severity: info)* at `Lead.created_at` (no own timestamp). Always present.
8. **`mandate`** — "Mandate signed" *(severity: success)* at `Lead.mandate_signed_at` when `mandate_signed=True`. Metadata: version, source.

Ordering: by `timestamp` ascending. Ties broken by category priority then by source row pk — deterministic.

## 8. Acceptance criteria (gate phase 7)

1. Audit doc + improvements doc both present.
2. `apps.crm.timeline.build_lead_timeline(lead)` exists, returns a list of `LeadTimelineItem`, ordered chronologically.
3. The aggregator surfaces: Lead created, Simulation linked (when present), both consent entries, every LeadEvent, every LeadWebhookDelivery state, Mandate required (default), Mandate signed (when present).
4. `Lead.next_staff_action` property returns a conservative non-legal short string. Branches tested.
5. `LeadAdmin` detail page exposes the timeline as a **readonly** field rendered with `format_html` (no JS, no buttons, no raw unsafe).
6. No HMAC secret, no full webhook URL, no PII (no `Lead.message` text, no email, no phone) appears in timeline strings.
7. No banned-promise phrase in any `next_staff_action` string (scan reuses PRODUCT-2/3 list).
8. Tests added: at least 12 pins covering items 1-7 + the readonly admin contract.
9. Full pytest green ≥ 2131 + the new PRODUCT-8 tests. Hygiene strict clean. Non-IT readiness APPROVED-PARTIAL × 4 unchanged.
10. No model migration created or applied.
11. No France activation.

## 9. Risks and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Timeline aggregator triggers N+1 on admin render | medium | `build_lead_timeline` accepts a `Lead` instance; the LeadAdmin override prefetches `simulation`, `events`, `webhook_deliveries`. Test pin counts queries on a Lead with 5 deliveries + 3 events to enforce a cap. |
| Naive `format_html` accidentally interpolates user-supplied text and breaks safety | high | All user-supplied strings (first_name / message) are excluded from the timeline by construction — the aggregator only touches model timestamps, enum values and version strings. The `format_html` call uses positional placeholders for trusted enum values only. Test pin: scan rendered HTML for `<script` and `javascript:`. |
| Webhook secret leaks into the timeline metadata | high | The aggregator never reads `settings.CRM_WEBHOOK_SECRET`. Test pin: configure a sentinel secret in test settings, render a timeline, assert the sentinel does not appear anywhere in the output. |
| `next_staff_action` strays into legal advice | high | The property returns one of a small fixed set of short operational strings. Test pin: scan each branch's output for banned-promise phrases. |
| Timeline shows past mandate version once a new one supersedes it | low | `MandateAcceptance` rows are append-only; if both old + new are present the timeline shows both, ordered by `signed_at`. Documented behaviour. |
| Timeline broken when CRM_WEBHOOK_ENABLED is False (no rows) | low | Aggregator yields nothing from the webhook branch when there are zero rows. Test pin: zero deliveries → no webhook entries, no error. |
| HTML rendering breaks under AR/RTL because of fixed left-padding | low | We do NOT add new templates. The admin readonly field renders into the existing form layout which already respects `dir`. No change to public templates. |

## 10. Implementation plan (phases 2-7)

1. **Phase 2** — `apps/crm/timeline.py`: `LeadTimelineItem` frozen dataclass + `build_lead_timeline(lead)` aggregator. Pure, side-effect-free, no DB writes.
2. **Phase 3** — admin: extend `LeadAdmin` with `activity_timeline` readonly callable, rendered via `format_html`. Add it to `readonly_fields` + to a new collapsed fieldset "Activity timeline" between Workflow and Webhook outbox.
3. **Phase 4** — `Lead.next_staff_action` property on the model. Pure, computed from existing fields.
4. **Phase 5** — tests: `apps/crm/test_product_8_lead_activity_timeline.py`. Cover the 12 pins enumerated in §8.
5. **Phase 6** — notes: `docs/screenshots/.../after/product-studio-lead-activity-timeline/NOTES.md`. Description of what staff sees on the admin detail page, including the timeline rendering shape and `next_staff_action` location.
6. **Phase 7** — report: `docs/product/CRM_LEAD_ACTIVITY_TIMELINE_IMPROVEMENTS_2026-05-12.md`.
7. **Commit**: `product-8: add staff lead activity timeline`. Single commit, no push.

## 11. Rollback

A single `git revert` of the PRODUCT-8 commit removes: `apps/crm/timeline.py`, the new `Lead.next_staff_action` property, the LeadAdmin extensions, the new test file, this audit, the improvements report, the notes. No DB rollback needed — no migration. The pre-PRODUCT-8 admin returns identical bytes after revert.
