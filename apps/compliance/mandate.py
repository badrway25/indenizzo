"""
Mandate professional engagement service (F-p0-leg-2-mandate).

API minima:

- ``mark_mandate_signed(lead, *, version, signed_at, source, ...)``:
  esegue la transizione `mandate_signed=True` su un `Lead`, crea il
  `MandateAcceptance` di prova, sincronizza i campi denormalizzati e
  registra un `PrivacyAuditEvent`.

- ``assert_mandate_signed_for_case_activation(lead)``: guard pure
  function. Solleva `MandateNotSignedError` se il setting
  ``REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=True`` (default) e il lead
  non ha `mandate_signed=True`. Ogni futuro flow di promozione lead
  → pratica DEVE chiamarla prima di marcare un lead come pratica
  attiva.

Filosofia:
- niente cancellazione: il toggle e' sempre append (nuova
  ``MandateAcceptance``);
- niente PII oltre lo `snapshot` opzionale del nome cliente
  (la richiesta GDPR di anonymize azzera anche quello via la
  retention policy P0-LEG-4 sulla parent Lead);
- determinismo nei test: `signed_at` e' sempre un parametro esplicito
  (mai `timezone.now()` interno).

Niente flow di promozione lead → pratica esiste oggi nel codebase
(verificato via `git grep`). Quando arriva, la guard e' gia' in
linea: aggiungere all'inizio della funzione di attivazione
``assert_mandate_signed_for_case_activation(lead)``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from django.conf import settings
from django.db import transaction

from apps.compliance.enums import PrivacyEventType
from apps.compliance.services import get_request_meta, log_privacy_event

logger = logging.getLogger(__name__)


class MandateNotSignedError(RuntimeError):
    """Sollevata quando una funzione tenta di promuovere a pratica un
    lead senza ``mandate_signed=True`` mentre
    ``REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=True``.
    """


@transaction.atomic
def mark_mandate_signed(
    lead,
    *,
    version: str,
    signed_at: datetime,
    source: str = "staff",
    client_name_snapshot: str = "",
    locale: str = "",
    metadata: dict[str, Any] | None = None,
    request: Any | None = None,
    actor: Any | None = None,
) -> Any:
    """
    Marca il `lead` come `mandate_signed=True`.

    Side effects:
    - aggiorna `lead.mandate_signed`, `mandate_signed_at`,
      `mandate_version`, `mandate_status`, `mandate_source`;
    - aggiorna `lead.status` da `LeadStatus.QUALIFIED` (o lasciato
      invariato) verso `CONVERTED` se non gia' rejected/archived;
    - crea un `MandateAcceptance` (append-only ledger);
    - logga `PrivacyAuditEvent(CONSENT_GIVEN)` con
      `target_model="crm.Lead"` e
      ``metadata={"mandate_version": version, "source": source}``.

    Idempotente: se il lead ha gia' `mandate_signed=True` con la stessa
    versione, ritorna il `MandateAcceptance` piu' recente senza creare
    duplicati.
    """
    from apps.crm.models import LeadStatus, MandateStatus

    from .models import MandateAcceptance

    if lead.mandate_signed and lead.mandate_version == version:
        existing = (
            MandateAcceptance.objects.filter(
                lead=lead, mandate_version=version, accepted=True
            )
            .order_by("-signed_at")
            .first()
        )
        if existing is not None:
            return existing

    acceptance = MandateAcceptance.objects.create(
        lead=lead,
        simulation=lead.simulation,
        mandate_version=version,
        accepted=True,
        signed_at=signed_at,
        client_name_snapshot=client_name_snapshot[:160],
        source=source,
        locale=locale,
        metadata=dict(metadata or {}),
    )

    lead.mandate_signed = True
    lead.mandate_signed_at = signed_at
    lead.mandate_version = version
    lead.mandate_status = MandateStatus.SIGNED
    lead.mandate_source = source
    update_fields = [
        "mandate_signed",
        "mandate_signed_at",
        "mandate_version",
        "mandate_status",
        "mandate_source",
    ]
    # Promuovi lo status del lead a CONVERTED solo se non e' in uno
    # stato terminale (rejected/archived). Convertito qui significa:
    # "il rapporto pre-contrattuale si e' tradotto in un mandato",
    # non "praticabile" — la praticabilita' richiede ulteriori passi
    # operativi gestiti dallo Studio offline.
    if lead.status not in (LeadStatus.REJECTED, LeadStatus.ARCHIVED):
        lead.status = LeadStatus.CONVERTED
        update_fields.append("status")
        if not lead.converted_at:
            lead.converted_at = signed_at
            update_fields.append("converted_at")

    lead.save(update_fields=update_fields)

    log_privacy_event(
        event_type=PrivacyEventType.CONSENT_GIVEN,
        request=request,
        actor=actor,
        target_model="crm.Lead",
        target_object_id=lead.pk,
        metadata={
            "mandate_version": version,
            "source": source,
            "trigger": "mandate_signed",
        },
    )
    logger.info(
        "compliance.mandate.signed lead_public_id=%s version=%s source=%s",
        lead.public_id,
        version,
        source,
    )
    return acceptance


def assert_mandate_signed_for_case_activation(lead) -> None:
    """
    Guard. Da chiamare all'inizio di qualsiasi futura funzione che
    attivi un lead come pratica.

    Comportamento:
    - se `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=False` -> no-op;
    - se `lead.mandate_signed=True` -> no-op;
    - altrimenti solleva `MandateNotSignedError`.

    Esempio (per quando arrivera' il flow di promozione):

        from apps.compliance.mandate import (
            assert_mandate_signed_for_case_activation,
        )

        def activate_case(lead):
            assert_mandate_signed_for_case_activation(lead)
            ...
    """
    if not getattr(settings, "REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION", True):
        return
    if getattr(lead, "mandate_signed", False):
        return
    public_id = getattr(lead, "public_id", "<unknown>")
    raise MandateNotSignedError(
        f"Cannot activate a case for lead {public_id}: mandate_signed=False. "
        "A signed professional mandate is required before any internal flow "
        "can treat a contact request as an active case."
    )
