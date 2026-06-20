"""
Service layer per `apps.reports`.

Punto d'ingresso unico:
    `generate_simulation_report(simulation, language=None, request=None, user=None)`

Garanzie:

- NON ricalcola: legge esclusivamente `simulation.output_data`,
  `simulation.sources_snapshot`, `simulation.input_data` come persistiti.
- NON modifica la `Simulation`.
- Filtra i campi di `input_data` con una whitelist (mai honeypot,
  consenso, flag interni).
- Calcola SHA-256 del file generato e lo salva in `SimulationReport`.
- Registra `PrivacyAuditEvent` (`DATA_EXPORTED`) per audit GDPR.
- Non logga input utente né messaggi: solo metadata tecnici.

Per dettagli sul rendering PDF, vedi `pdf_renderer.py`.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction

from apps.cases.models import Simulation
from apps.compliance.enums import PrivacyEventType
from apps.compliance.services import log_privacy_event

from .labels import DEFAULT_LANGUAGE, is_rtl
from .models import SimulationReport
from .pdf_renderer import render_simulation_pdf_bytes

logger = logging.getLogger(__name__)


@transaction.atomic
def generate_simulation_report(
    simulation: Simulation,
    *,
    language: str | None = None,
    request: Any | None = None,
    user: Any | None = None,
) -> SimulationReport:
    """
    Genera un PDF a partire da una `Simulation` e persiste un
    `SimulationReport`. Ritorna sempre un report (anche su errore di
    rendering: in quel caso `status=FAILED`, file vuoto, error_message
    valorizzato).

    `language`: se omessa, usa `simulation.locale`. Se la lingua è RTL
    (arabo) e reportlab non rende correttamente il bidi, il fallback è
    LTR e viene annotato in `metadata.rtl_fallback=True`.
    """
    lang = (language or simulation.locale or DEFAULT_LANGUAGE).lower()
    rtl_fallback_used = False

    metadata: dict[str, Any] = {
        "simulation_status": simulation.status,
        "simulation_currency": simulation.currency or "",
        "language_requested": lang,
    }
    if is_rtl(lang):
        # Documentiamo esplicitamente che il rendering RTL è limitato.
        # Il PDF viene comunque prodotto (LTR + etichette in inglese,
        # vedi `labels.py`), il flag finisce in metadata.
        rtl_fallback_used = True
        metadata["rtl_fallback"] = True

    try:
        pdf_bytes = render_simulation_pdf_bytes(simulation, language=lang)
    except Exception as exc:  # rendering errors must NEVER 500 the user
        # PII-safe logging: NON usare `logger.exception`/`exc_info` qui. Il
        # traceback di `render_simulation_pdf_bytes` cammina i frame con i
        # dati sensibili della Simulation (età, % invalidità, reddito, dati
        # di decesso) e il `RedactPIIFilter` NON scruba l'`exc_info` (filtra
        # solo `getMessage()`). Logghiamo quindi soltanto la classe
        # dell'eccezione: il dettaglio tecnico completo resta in
        # `SimulationReport.error_message` (DB access-controllato, auditlog).
        logger.error(
            "reports.simulation_report.render_failed sim=%s error=%s",
            simulation.public_id,
            exc.__class__.__name__,
        )
        report = SimulationReport.objects.create(
            simulation=simulation,
            language=lang,
            status=SimulationReport.Status.FAILED,
            error_message=f"{type(exc).__name__}: {exc}"[:2000],
            metadata=metadata,
            generated_by=_resolve_user(user, request),
        )
        return report

    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    filename = f"simulation_{simulation.public_id}_{lang}.pdf"

    report = SimulationReport(
        simulation=simulation,
        language=lang,
        status=SimulationReport.Status.GENERATED,
        file_hash=file_hash,
        file_size_bytes=len(pdf_bytes),
        metadata=metadata,
        generated_by=_resolve_user(user, request),
    )
    report.file.save(filename, ContentFile(pdf_bytes), save=False)
    report.save()

    # Audit privacy: il PDF è un'esportazione di dati personali (input_data
    # filtrato). Registriamo come DATA_EXPORTED. Mai loggare input/output
    # nei metadata: solo flag tecnici.
    log_privacy_event(
        event_type=PrivacyEventType.DATA_EXPORTED,
        request=request,
        actor=report.generated_by,
        target_model="reports.SimulationReport",
        target_object_id=report.pk,
        metadata={
            "simulation_public_id": str(simulation.public_id),
            "language": lang,
            "rtl_fallback": rtl_fallback_used,
        },
    )

    logger.info(
        "reports.simulation_report.generated public_id=%s sim=%s status=%s",
        report.public_id,
        simulation.public_id,
        report.status,
    )
    return report


def _resolve_user(user: Any | None, request: Any | None):
    """Stesso pattern di `cases.services._resolve_user`."""
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    if request is not None:
        candidate = getattr(request, "user", None)
        if candidate is not None and getattr(candidate, "is_authenticated", False):
            return candidate
    return None
