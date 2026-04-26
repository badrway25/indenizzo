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

from django.db import transaction

from apps.cases.models import Simulation
from apps.compliance.enums import PrivacyEventType
from apps.compliance.models import ConsentPurpose
from apps.compliance.services import (
    get_request_meta,
    log_privacy_event,
    record_consent,
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
    - registra `ConsentRecord(accepted=True)` per `lead_contact`;
    - crea `LeadEvent(type=CREATED)`;
    - registra `PrivacyAuditEvent(type=CONSENT_GIVEN)` con target=cases.Simulation
      se collegata, altrimenti target=crm.Lead.

    Niente `message` nei log (privacy by default): logghiamo solo public_id.
    """
    purpose = get_or_create_lead_contact_purpose()

    resolved_user = _resolve_user(user, request)

    consent = record_consent(
        purpose=purpose,
        accepted=True,
        request=request,
        user=resolved_user,
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

    lead = Lead.objects.create(
        simulation=simulation,
        user=resolved_user,
        session_key=meta.session_key,
        consent_record=consent,
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
        source_path=meta.path,
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
        metadata={"purpose": purpose.code},
    )

    logger.info(
        "crm.lead.created public_id=%s status=%s linked_simulation=%s",
        lead.public_id,
        lead.status,
        simulation is not None,
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
