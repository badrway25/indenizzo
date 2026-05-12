"""
Public views CRM (F6).

`/contact/` GET → form
`/contact/` POST → valida + crea Lead via service → redirect thank-you
`/contact/thank-you/` GET → conferma

Il honeypot `website` è gestito a livello di view: se è compilato, il
form passa la validazione (per non dare segnali al bot) ma il Lead
non viene creato — e l'utente vede comunque la thank-you page.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.rate_limit import public_post_rate_limit

from .email_notifications import send_lead_notification
from .forms import ContactForm
from .services import create_lead_from_form

logger = logging.getLogger(__name__)


def _dispatch_lead_notification(lead, *, request) -> None:
    """
    Dispatch della notifica email Lead.

    - Se `LEAD_NOTIFICATION_ASYNC_ENABLED=True`: prova `delay()` sul
      task Celery. Se il broker è down (qualunque eccezione), fa
      fallback al send sincrono. Né l'enqueue né il send sincrono
      possono rompere il funnel utente: tutte le eccezioni sono
      assorbite e loggate senza PII.
    - Se `LEAD_NOTIFICATION_ASYNC_ENABLED=False` (default): comportamento
      pass 2, sincrono in-request.
    """
    use_async = bool(getattr(settings, "LEAD_NOTIFICATION_ASYNC_ENABLED", False))
    if use_async:
        try:
            # Lazy import: il modulo `tasks` importa Celery, e vogliamo
            # che il path sync resti completamente indipendente da Celery.
            from .tasks import send_lead_notification_task

            send_lead_notification_task.delay(lead.pk)
            return
        except Exception as exc:
            # Broker down (es. Redis non raggiungibile) o errore di
            # serializzazione. Fallback sicuro a invio sincrono. Mai
            # propagare: la thank-you page deve essere raggiungibile.
            logger.warning(
                "crm.lead.notification.delay_failed pk=%s error=%s — fallback sync",
                lead.pk,
                exc.__class__.__name__,
            )
    # Sync path (default o fallback).
    try:
        send_lead_notification(lead, request=request)
    except Exception as exc:  # pragma: no cover — send_lead_notification
        # è già failure-soft. Difensivo per assoluto non-rotture.
        logger.warning(
            "crm.lead.notification.sync_failed pk=%s error=%s",
            lead.pk,
            exc.__class__.__name__,
        )


@public_post_rate_limit
@require_http_methods(["GET", "POST"])
def contact(request):
    initial = {}
    linked_simulation = None
    sim_id = request.GET.get("sim")
    if sim_id:
        initial["simulation_public_id"] = sim_id
        # F-product-2-funnel: when the contact form is opened from a
        # specific result page (`/wizard/result/<uuid>/` → `/contact/?sim=<uuid>`),
        # prefill `country` and `case_type` from the linked Simulation
        # so the user doesn't re-pick what they just selected in the
        # wizard. Failure-soft: malformed UUID (ValidationError),
        # unknown UUID (no row), or any DB hiccup must NOT break the
        # contact form — it opens blank instead.
        from apps.cases.models import Simulation
        from django.core.exceptions import ValidationError

        try:
            linked_simulation = (
                Simulation.objects.filter(public_id=sim_id)
                .select_related("country")
                .first()
            )
        except (ValidationError, ValueError):
            linked_simulation = None
        if linked_simulation is not None:
            if linked_simulation.country_id:
                initial["country"] = linked_simulation.country
            if linked_simulation.case_type:
                initial["case_type"] = linked_simulation.case_type

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            if form.is_likely_bot:
                # Il bot ha compilato il honeypot. Niente Lead, ma redirect
                # alla thank-you per non rivelare la trappola.
                logger.info("crm.lead.dropped reason=honeypot path=%s", request.path)
                return redirect(reverse("crm:contact_thank_you"))

            lead = create_lead_from_form(
                form_kwargs=form.to_lead_kwargs(),
                simulation_public_id=form.cleaned_data.get("simulation_public_id") or "",
                request=request,
            )
            # Notifica transazionale allo Studio. Failure-soft a tutti i
            # livelli: né Celery né SMTP possono rompere il redirect
            # thank-you (vedi `_dispatch_lead_notification`).
            _dispatch_lead_notification(lead, request=request)
            return redirect(reverse("crm:contact_thank_you"))
    else:
        form = ContactForm(initial=initial)

    from apps.core.views import _pexels_hero

    return render(
        request,
        "public/contact.html",
        {
            "form": form,
            "linked_simulation": linked_simulation,
            "pexels_image": _pexels_hero(request, "contact_hero"),
        },
    )


@require_GET
def contact_thank_you(request):
    return render(request, "public/contact_thank_you.html")
