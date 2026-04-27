"""
Public view per il download del PDF di una `Simulation`.

Endpoint: `GET /reports/simulation/<uuid:public_id>/pdf/`

Comportamento:
- 404 se la `Simulation` non esiste;
- altrimenti chiama il service `generate_simulation_report`, che crea
  un nuovo `SimulationReport`, registra `PrivacyAuditEvent` e ritorna
  l'oggetto;
- restituisce `FileResponse` con `application/pdf` e
  `Content-Disposition: inline` così che il browser lo apra in tab.

Nota di sicurezza: l'endpoint non richiede autenticazione perché il
`public_id` UUID è già un capability token (sostanzialmente
imprevedibile a meno di forza bruta su 122 bit). Per uno stage successivo
si può aggiungere un token firmato con scadenza corta. Vedi rischi noti.
"""

from __future__ import annotations

import logging
import uuid

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import translation
from django.views.decorators.http import require_GET

from apps.cases.models import Simulation

from .models import SimulationReport
from .services import generate_simulation_report

logger = logging.getLogger(__name__)


@require_GET
def simulation_pdf_download(request, public_id: uuid.UUID):
    simulation = get_object_or_404(
        Simulation.objects.select_related("jurisdiction", "country"),
        public_id=public_id,
    )

    # La lingua del report segue il locale attivo della request, con
    # fallback su `simulation.locale`. Il service applica un fallback
    # ulteriore su DEFAULT_LANGUAGE.
    request_lang = (translation.get_language() or "").split("-", 1)[0].lower()
    lang = request_lang or simulation.locale or "it"

    report = generate_simulation_report(
        simulation,
        language=lang,
        request=request,
        user=request.user if request.user.is_authenticated else None,
    )

    if report.status != SimulationReport.Status.GENERATED or not report.file:
        # Difensivo: il service NON solleva su errori di rendering, ma
        # restituisce un report `FAILED` per audit. La view trasforma
        # quel caso in 404 visibile all'utente (l'errore tecnico resta
        # in DB per il triage).
        logger.warning(
            "reports.simulation_pdf_download.report_not_ready public_id=%s sim=%s",
            report.public_id,
            simulation.public_id,
        )
        raise Http404("Report not available")

    response = FileResponse(
        report.file.open("rb"),
        as_attachment=False,
        filename=f"simulation_{simulation.public_id}.pdf",
        content_type="application/pdf",
    )
    return response
