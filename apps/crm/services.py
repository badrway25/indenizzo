"""
Service layer CRM.

`create_lead_from_form` orchestra:
- validazione consenso (`ConsentPurpose.lead_contact`);
- registrazione `ConsentRecord` (compliance);
- creazione `Lead` + `LeadEvent`;
- log `PrivacyAuditEvent` per audit ledger.

Idempotente sul `purpose` lead_contact: se non esiste viene creato al volo
con default sicuri (`required_for_contact=True`). Il seed dedicato
`seed_compliance_basics` resta consigliato per produzione (con i testi
versionati per lingua), ma il service non si rompe se eseguito a freddo.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db import transaction

from apps.cases.models import Simulation
from apps.compliance.enums import PrivacyEventType
from apps.compliance.models import ConsentPurpose
from apps.compliance.services import (
    get_request_meta,
    log_privacy_event,
    record_double_consent,
)

from .models import Lead, LeadEvent

logger = logging.getLogger(__name__)


def get_or_create_lead_contact_purpose() -> ConsentPurpose:
    """Recupera (o crea) il `ConsentPurpose` per il contatto Studio."""
    purpose, _ = ConsentPurpose.objects.get_or_create(
        code="lead_contact",
        defaults={
            "name": "Lead contact request",
            "description": (
                "Consent to process contact data submitted via the public "
                "/contact/ form so the Studio can reply."
            ),
            "required_for_contact": True,
        },
    )
    return purpose


@transaction.atomic
def create_lead_from_form(
    *,
    form_kwargs: dict,
    simulation_public_id: str = "",
    request: Any | None = None,
    user: Any | None = None,
) -> Lead:
    """
    Crea un `Lead` dal payload pulito di `ContactForm`.

    Side-effects:
    - registra DUE `ConsentRecord` (accepted=True) per
      `lead_contact` (GDPR art. 6) e `special_categories_processing`
      (GDPR art. 9). F-p0-leg-3-consent;
    - salva i campi denormalizzati `privacy_consent_*` /
      `special_categories_consent_*` sul `Lead`;
    - crea `LeadEvent(type=CREATED)`;
    - registra `PrivacyAuditEvent(type=CONSENT_GIVEN)` con target=cases.Simulation
      se collegata, altrimenti target=crm.Lead.

    Niente `message` nei log (privacy by default): logghiamo solo public_id.
    """
    resolved_user = _resolve_user(user, request)

    privacy_record, _special_record = record_double_consent(
        request=request,
        user=resolved_user,
        privacy_purpose_code="lead_contact",
        privacy_purpose_label="Lead contact request",
        privacy_version=settings.PRIVACY_NOTICE_VERSION,
        special_categories_version=settings.SPECIAL_CATEGORIES_NOTICE_VERSION,
        metadata={"trigger": "contact_form"},
    )

    meta = get_request_meta(request)

    simulation: Simulation | None = None
    if simulation_public_id:
        simulation = (
            Simulation.objects.filter(public_id=simulation_public_id)
            .select_related("country")
            .first()
        )

    from django.utils import timezone as _tz

    now = _tz.now()
    lead = Lead.objects.create(
        simulation=simulation,
        user=resolved_user,
        session_key=meta.session_key,
        consent_record=privacy_record,
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
        source_path=meta.path,
        privacy_consent_given=True,
        privacy_consent_at=now,
        privacy_consent_version=settings.PRIVACY_NOTICE_VERSION,
        special_categories_consent_given=True,
        special_categories_consent_at=now,
        special_categories_consent_version=settings.SPECIAL_CATEGORIES_NOTICE_VERSION,
        **form_kwargs,
    )

    LeadEvent.objects.create(
        lead=lead,
        event_type=LeadEvent.EventType.CREATED,
        message="Lead received via /contact/ form.",
        metadata={
            "has_simulation": simulation is not None,
            "country_code": (lead.country.code if lead.country_id else ""),
            "case_type": lead.case_type,
        },
    )

    log_privacy_event(
        event_type=PrivacyEventType.CONSENT_GIVEN,
        request=request,
        actor=resolved_user,
        target_model="crm.Lead",
        target_object_id=lead.pk,
        # Doppio consenso: vedi `record_double_consent` chiamato sopra
        # per i `ConsentRecord` separati (lead_contact + special_categories_processing).
        metadata={"purposes": ["lead_contact", "special_categories_processing"]},
    )

    logger.info(
        "crm.lead.created public_id=%s status=%s linked_simulation=%s",
        lead.public_id,
        lead.status,
        simulation is not None,
    )

    # F-p1-crm-1-webhook-dispatcher — enqueue CRM webhook delivery if
    # the dispatcher is enabled. Failure-soft: a webhook enqueue error
    # never breaks the Lead creation flow (the Studio still has the
    # email + the DB row + the audit ledger).
    try:
        from .webhooks import enqueue_lead_webhook

        enqueue_lead_webhook(lead, event_type="lead.created")
    except Exception as exc:  # pragma: no cover — defensive only
        logger.warning(
            "crm.webhook.enqueue.failed lead_public_id=%s error=%s",
            lead.public_id,
            exc.__class__.__name__,
        )

    return lead


def _resolve_user(user: Any | None, request: Any | None) -> Any | None:
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    if request is not None:
        candidate = getattr(request, "user", None)
        if candidate is not None and getattr(candidate, "is_authenticated", False):
            return candidate
    return None
