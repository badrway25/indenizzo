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

from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.rate_limit import public_post_rate_limit

from .forms import ContactForm
from .services import create_lead_from_form

logger = logging.getLogger(__name__)


@public_post_rate_limit
@require_http_methods(["GET", "POST"])
def contact(request):
    initial = {}
    sim_id = request.GET.get("sim")
    if sim_id:
        initial["simulation_public_id"] = sim_id

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            if form.is_likely_bot:
                # Il bot ha compilato il honeypot. Niente Lead, ma redirect
                # alla thank-you per non rivelare la trappola.
                logger.info("crm.lead.dropped reason=honeypot path=%s", request.path)
                return redirect(reverse("crm:contact_thank_you"))

            create_lead_from_form(
                form_kwargs=form.to_lead_kwargs(),
                simulation_public_id=form.cleaned_data.get("simulation_public_id") or "",
                request=request,
            )
            return redirect(reverse("crm:contact_thank_you"))
    else:
        form = ContactForm(initial=initial)

    return render(
        request,
        "public/contact.html",
        {"form": form},
    )


@require_GET
def contact_thank_you(request):
    return render(request, "public/contact_thank_you.html")
