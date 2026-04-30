"""
Admin MFA guard — locale-first, opt-in via env.

Iter: F-local-product-hardening-pass5-mfa-admin.

Disegno:
- **Default off**: `ADMIN_MFA_REQUIRED=False` ⇒ il middleware è
  un no-op. Il flusso `/admin/login/` standard di Django resta
  invariato.
- **Opt-in**: `ADMIN_MFA_REQUIRED=True` ⇒ il middleware blocca
  l'accesso a `/admin/...` per staff/superuser senza OTP
  verificato, mostrando una pagina di enforcement HTTP 403.
- **Hook duck-typed**: la verifica MFA è delegata a
  `is_user_mfa_verified(user, request)`. Sequenza di check:
    1. `user.is_verified()` (esposto da
       `django_otp.middleware.OTPMiddleware` quando django-otp
       è installato e configurato).
    2. `request.session["mfa_verified"] is True` (utile in
       test e per un eventuale flusso custom Studio).
    3. altrimenti False.
- **Path bypass**: `/healthz/`, pagine pubbliche e
  `/admin/login/` / `/admin/logout/` NON sono protetti — le
  prime perché non sono admin, gli ultimi due per evitare
  loop di redirect.

Note:
- Il middleware non importa `django_otp`. Funziona anche se il
  pacchetto non è installato: il fallback session-based copre i
  test locali.
- Niente PII nei log: si emette solo `path` + `is_staff`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def is_user_mfa_verified(user: Any, request: HttpRequest | None) -> bool:
    """
    Ritorna True se l'utente ha completato l'MFA per questa sessione.

    Hook pubblico: estendibile/sostituibile da test o da future
    integrazioni custom.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    # 1. django-otp: se il middleware OTPMiddleware ha avvolto user,
    # `is_verified()` è disponibile e ritorna True solo se almeno un
    # device OTP è stato verificato in questa sessione.
    is_verified_callable = getattr(user, "is_verified", None)
    if callable(is_verified_callable):
        try:
            if is_verified_callable():
                return True
        except Exception:  # difensivo: mai sollevare nel middleware
            logger.warning("admin_mfa.user_is_verified_raised path=%s", "")

    # 2. Session flag: utile per test e per un flusso custom Studio.
    if request is not None:
        try:
            if request.session.get("mfa_verified") is True:
                return True
        except Exception:  # session non disponibile per qualche motivo
            return False

    return False


class AdminMFAMiddleware:
    """
    Middleware leggero per gating del Django admin.

    Posizionato dopo `AuthenticationMiddleware` per avere
    `request.user` popolato. Quando `ADMIN_MFA_REQUIRED=False`
    è effettivamente un pass-through.
    """

    # Path che non vanno protetti dal guard MFA, anche con flag attivo.
    # I login/logout admin sono esclusi per evitare loop di redirect:
    # un utente che deve completare la verifica MFA deve poter
    # comunque arrivare al form login per autenticarsi prima.
    _ADMIN_BYPASS_PREFIXES = ("/admin/login/", "/admin/logout/")

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not getattr(settings, "ADMIN_MFA_REQUIRED", False):
            return self.get_response(request)

        path = request.path
        if not path.startswith("/admin/"):
            return self.get_response(request)
        if any(path.startswith(p) for p in self._ADMIN_BYPASS_PREFIXES):
            return self.get_response(request)

        user = getattr(request, "user", None)
        # Anonymous: lascia che Django admin reindirizzi a /admin/login/.
        if user is None or not getattr(user, "is_authenticated", False):
            return self.get_response(request)
        # Non-staff: il LoginRequiredMixin / admin_view già blocca con
        # 403; non aggiungiamo carico cognitivo.
        if not getattr(user, "is_staff", False):
            return self.get_response(request)

        if is_user_mfa_verified(user, request):
            return self.get_response(request)

        # Staff senza MFA verificato: blocca con pagina chiara.
        logger.info(
            "admin_mfa.blocked path=%s is_staff=%s",
            path,
            getattr(user, "is_staff", False),
        )
        return render(request, "admin/mfa_required.html", status=403)
