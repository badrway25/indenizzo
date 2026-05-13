"""
Lead activity timeline aggregator (F-product-8-studio-lead-activity-timeline).

Pure read-only helper: walks a `Lead` plus its already-prefetched
related rows (`simulation`, `events`, `webhook_deliveries`,
`mandate_acceptances`) and returns a chronological list of
`LeadTimelineItem` entries.

Design choices documented in
`docs/product/CRM_LEAD_ACTIVITY_TIMELINE_AUDIT_2026-05-12.md`:

- **No new DB table.** The timeline is computed from existing rows.
- **No PII / secrets in the output.** No `Lead.message`, no email, no
  phone, no HMAC secret, no full webhook URL — only timestamps,
  enum values, version strings and audit-friendly tags.
- **No legal-advisory phrasing.** All strings are operational
  ("Privacy consent recorded", "Webhook delivered to <domain>").
- **Pure function.** No side effects, no DB writes, no I/O beyond
  reading already-prefetched relations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from django.utils.translation import gettext_lazy as _


# Short-string severity / category enums — kept as plain strings so
# the dataclass is not coupled to a Django enum that might be removed.
SEVERITY_INFO = "info"
SEVERITY_SUCCESS = "success"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"

CATEGORY_LEAD = "lead"
CATEGORY_SIMULATION = "simulation"
CATEGORY_CONSENT = "consent"
CATEGORY_LIFECYCLE = "lifecycle"
CATEGORY_WEBHOOK = "webhook"
CATEGORY_MANDATE = "mandate"

# Priority used to break ties when multiple events share the same
# timestamp. Lower number = earlier in the ordering. Lifecycle /
# mandate transitions appear close to lead-creation events.
_CATEGORY_PRIORITY: dict[str, int] = {
    CATEGORY_SIMULATION: 1,
    CATEGORY_CONSENT: 2,
    CATEGORY_LEAD: 3,
    CATEGORY_LIFECYCLE: 4,
    CATEGORY_WEBHOOK: 5,
    CATEGORY_MANDATE: 6,
}


@dataclass(frozen=True)
class LeadTimelineItem:
    """One row in the per-Lead activity timeline.

    Attributes are all safe for admin rendering — no field contains
    user-supplied PII (the aggregator does not touch `Lead.message`,
    `Lead.first_name`, `Lead.email`, `Lead.phone_number`).
    """

    timestamp: datetime
    category: str
    severity: str
    label: str
    description: str
    source: str
    metadata: dict = field(default_factory=dict)


# LeadEvent.EventType → severity mapping. Kept here (not on the
# enum) so the timeline aggregator owns the presentation rule.
_LIFECYCLE_SEVERITY: dict[str, str] = {
    "created": SEVERITY_INFO,
    "contacted": SEVERITY_INFO,
    "qualified": SEVERITY_SUCCESS,
    "converted": SEVERITY_SUCCESS,
    "rejected": SEVERITY_WARNING,
    "archived": SEVERITY_WARNING,
    "note": SEVERITY_INFO,
    "other": SEVERITY_INFO,
}


def _domain_label(domain: str) -> str:
    """Return a safe, single-line representation of the target
    webhook host. Empty string → '-'. Never echoes a full URL."""
    domain = (domain or "").strip()
    return domain if domain else "-"


def _simulation_item(lead) -> LeadTimelineItem | None:
    sim = getattr(lead, "simulation", None)
    if sim is None or getattr(sim, "created_at", None) is None:
        return None
    return LeadTimelineItem(
        timestamp=sim.created_at,
        category=CATEGORY_SIMULATION,
        severity=SEVERITY_INFO,
        label=str(_("Simulation linked")),
        description=str(_("Lead arrived via the wizard funnel.")),
        source=f"cases.Simulation#{sim.public_id}",
        metadata={
            "case_type": sim.case_type or "",
            "country_code": (sim.country.code if sim.country_id else ""),
            "status": sim.status or "",
        },
    )


def _consent_items(lead) -> Iterable[LeadTimelineItem]:
    if lead.privacy_consent_at:
        yield LeadTimelineItem(
            timestamp=lead.privacy_consent_at,
            category=CATEGORY_CONSENT,
            severity=SEVERITY_SUCCESS,
            label=str(_("Privacy consent recorded")),
            description=str(_("GDPR art. 6 consent given at contact form submit.")),
            source=f"crm.Lead#{lead.public_id}",
            metadata={"version": lead.privacy_consent_version or ""},
        )
    if lead.special_categories_consent_at:
        yield LeadTimelineItem(
            timestamp=lead.special_categories_consent_at,
            category=CATEGORY_CONSENT,
            severity=SEVERITY_SUCCESS,
            label=str(_("Special-categories consent recorded")),
            description=str(_("GDPR art. 9 consent given at contact form submit.")),
            source=f"crm.Lead#{lead.public_id}",
            metadata={"version": lead.special_categories_consent_version or ""},
        )


def _lead_created_item(lead) -> LeadTimelineItem:
    """Always present — the canonical anchor entry."""
    return LeadTimelineItem(
        timestamp=lead.created_at,
        category=CATEGORY_LEAD,
        severity=SEVERITY_INFO,
        label=str(_("Lead created")),
        description=str(_("New contact request received.")),
        source=f"crm.Lead#{lead.public_id}",
        metadata={
            "country_code": (lead.country.code if lead.country_id else ""),
            "case_type": lead.case_type or "",
            "language": lead.preferred_language or "",
        },
    )


def _lifecycle_items(lead) -> Iterable[LeadTimelineItem]:
    """One item per LeadEvent row, with severity from the static map.
    The CREATED event is suppressed when its timestamp matches
    `Lead.created_at` exactly — avoids two adjacent rows for the same
    moment in time."""
    lead_created = lead.created_at
    for ev in lead.events.all():
        if ev.event_type == "created" and ev.created_at == lead_created:
            continue
        severity = _LIFECYCLE_SEVERITY.get(ev.event_type, SEVERITY_INFO)
        # NOTE: ev.message is internal-staff text typed by Studio
        # users in admin actions; never user-supplied PII. Safe to
        # surface as the description.
        description = ev.message or str(_("Lifecycle transition recorded."))
        yield LeadTimelineItem(
            timestamp=ev.created_at,
            category=CATEGORY_LIFECYCLE,
            severity=severity,
            label=str(_("Lifecycle: %(event_type)s")) % {"event_type": ev.event_type},
            description=description,
            source=f"crm.LeadEvent#{ev.pk}",
            metadata={"event_type": ev.event_type},
        )


def _webhook_items(lead) -> Iterable[LeadTimelineItem]:
    """For each LeadWebhookDelivery row emit:

    - an "enqueued" entry at `created_at`;
    - if delivered/failed/dead, a terminal entry at the relevant
      timestamp (delivered_at or last_attempt_at);
    - if pending and attempts > 0, a "pending" annotation entry at
      the last_attempt_at (so the Studio sees the retry history).

    NEVER reads the HMAC secret. NEVER includes the full URL — only
    `target_url_domain`.
    """
    for d in lead.webhook_deliveries.all():
        target = _domain_label(d.target_url_domain)
        base_meta = {
            "event_type": d.event_type or "",
            "target_url_domain": target,
            "attempts": str(d.attempts),
            "max_attempts": str(d.max_attempts),
        }

        # Enqueued.
        yield LeadTimelineItem(
            timestamp=d.created_at,
            category=CATEGORY_WEBHOOK,
            severity=SEVERITY_INFO,
            label=str(_("Webhook enqueued")),
            description=str(_("Outbox row created for CRM delivery to %(target)s.")) % {"target": target},
            source=f"crm.LeadWebhookDelivery#{d.pk}",
            metadata=base_meta,
        )

        status = d.status
        if status == "delivered" and d.delivered_at:
            yield LeadTimelineItem(
                timestamp=d.delivered_at,
                category=CATEGORY_WEBHOOK,
                severity=SEVERITY_SUCCESS,
                label=str(_("Webhook delivered")),
                description=str(_("CRM receiver returned 2xx for delivery to %(target)s.")) % {"target": target},
                source=f"crm.LeadWebhookDelivery#{d.pk}",
                metadata={
                    **base_meta,
                    "http_status": str(d.last_status_code or ""),
                },
            )
        elif status in ("failed", "dead") and d.last_attempt_at:
            severity = SEVERITY_ERROR
            if status == "dead":
                label_str = str(_("Webhook dead — max attempts reached"))
            else:
                label_str = str(_("Webhook failed (permanent)"))
            yield LeadTimelineItem(
                timestamp=d.last_attempt_at,
                category=CATEGORY_WEBHOOK,
                severity=severity,
                label=label_str,
                description=str(_("CRM delivery to %(target)s stopped retrying.")) % {"target": target},
                source=f"crm.LeadWebhookDelivery#{d.pk}",
                metadata={
                    **base_meta,
                    "http_status": str(d.last_status_code or ""),
                    "status": status,
                },
            )
        elif status in ("pending", "sending") and d.last_attempt_at and d.attempts > 0:
            yield LeadTimelineItem(
                timestamp=d.last_attempt_at,
                category=CATEGORY_WEBHOOK,
                severity=SEVERITY_WARNING,
                label=str(_("Webhook pending (retrying)")),
                description=str(_("CRM delivery to %(target)s scheduled to retry.")) % {"target": target},
                source=f"crm.LeadWebhookDelivery#{d.pk}",
                metadata={
                    **base_meta,
                    "http_status": str(d.last_status_code or ""),
                    "status": status,
                },
            )


def _mandate_items(lead) -> Iterable[LeadTimelineItem]:
    """Always emits the "Mandate required (default)" entry at Lead
    creation; emits "Mandate signed" when the flag is set."""
    yield LeadTimelineItem(
        timestamp=lead.created_at,
        category=CATEGORY_MANDATE,
        severity=SEVERITY_INFO,
        label=str(_("Mandate required (default)")),
        description=str(_("Lead starts as a pre-contractual contact. An engagement requires a separate written mandate.")),
        source=f"crm.Lead#{lead.public_id}",
        metadata={"mandate_status": "mandate_required"},
    )

    if lead.mandate_signed and lead.mandate_signed_at:
        yield LeadTimelineItem(
            timestamp=lead.mandate_signed_at,
            category=CATEGORY_MANDATE,
            severity=SEVERITY_SUCCESS,
            label=str(_("Mandate signed")),
            description=str(_("Lead promoted to an active engagement after the signed mandate.")),
            source=f"crm.Lead#{lead.public_id}",
            metadata={
                "mandate_version": lead.mandate_version or "",
                "mandate_source": lead.mandate_source or "",
            },
        )


def build_lead_timeline(lead) -> list[LeadTimelineItem]:
    """Return the chronologically-ordered activity timeline for the
    given `Lead`.

    Ordering: by `timestamp` ascending. Ties are broken first by
    category priority (simulation → consent → lead → lifecycle →
    webhook → mandate), then by source row pk — deterministic.

    The function is pure and does not write to the DB. It reads
    `lead.events.all()`, `lead.webhook_deliveries.all()` and
    `lead.simulation` — callers that render the timeline on a list
    view should use `prefetch_related` to avoid N+1.
    """
    items: list[LeadTimelineItem] = []

    sim_item = _simulation_item(lead)
    if sim_item is not None:
        items.append(sim_item)

    items.extend(_consent_items(lead))
    items.append(_lead_created_item(lead))
    items.extend(_lifecycle_items(lead))
    items.extend(_webhook_items(lead))
    items.extend(_mandate_items(lead))

    items.sort(
        key=lambda it: (
            it.timestamp,
            _CATEGORY_PRIORITY.get(it.category, 99),
            it.source,
        )
    )
    return items


# ---------------------------------------------------------------------------
# Phase 4 — next_staff_action helper
# ---------------------------------------------------------------------------


# Strings deliberately operational (what to do) — never legal
# (what the case is worth). The Studio decides the merit; this
# helper only summarises where in the workflow the Lead sits.
ACTION_WEBHOOK_INTEGRATION_FAILED = "Webhook delivery failed - check integration"
ACTION_WEBHOOK_RETRYING = "Webhook still retrying - monitor delivery"
ACTION_CONTACT_CLIENT = "Review linked simulation and contact client"
ACTION_REVIEW_NEW_LEAD = "Review new lead and decide next step"
ACTION_MANDATE_NOT_SIGNED = "Mandate not signed - prepare engagement letter"
ACTION_READY_FOR_FOLLOWUP = "Ready for manual follow-up"
ACTION_WAITING_STUDIO_REVIEW = "Waiting for Studio review"
ACTION_ENGAGEMENT_ACTIVE = "Engagement active - manage the case offline"
ACTION_ARCHIVED = "Archived - no further action"


def compute_next_staff_action(lead) -> str:
    """Return a short conservative operational hint for the Studio.

    The function never derives a legal opinion. It only inspects
    workflow flags (status, mandate, webhook) and returns one of a
    small set of fixed English strings (translation handled at the
    presentation layer if/when needed).

    Order of precedence (more critical conditions first):

    1. `archived` / `rejected` — terminal status.
    2. webhook integration failed (dead) — operational blocker.
    3. lead status = converted AND mandate signed — engagement live.
    4. webhook still retrying — wait + monitor.
    5. status = received + linked simulation — funnel lead, contact client.
    6. status = received without linked simulation — cold lead, review then act.
    7. status = qualified without signed mandate — mandate is the next step.
    8. status = contacted — waiting for Studio review.
    9. fallback — ready for manual follow-up.
    """
    from .models import LeadStatus

    status = lead.status

    if status == LeadStatus.ARCHIVED:
        return ACTION_ARCHIVED
    if status == LeadStatus.REJECTED:
        return ACTION_ARCHIVED

    webhook_summary = lead.webhook_delivery_status_summary
    if webhook_summary == "dead":
        return ACTION_WEBHOOK_INTEGRATION_FAILED

    if status == LeadStatus.CONVERTED and lead.mandate_signed:
        return ACTION_ENGAGEMENT_ACTIVE

    if webhook_summary.startswith("pending("):
        return ACTION_WEBHOOK_RETRYING

    if status == LeadStatus.RECEIVED:
        if lead.has_linked_simulation:
            return ACTION_CONTACT_CLIENT
        return ACTION_REVIEW_NEW_LEAD

    if status == LeadStatus.QUALIFIED and not lead.mandate_signed:
        return ACTION_MANDATE_NOT_SIGNED

    if status == LeadStatus.CONTACTED:
        return ACTION_WAITING_STUDIO_REVIEW

    return ACTION_READY_FOR_FOLLOWUP
