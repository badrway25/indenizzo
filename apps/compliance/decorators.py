"""
Decoratore `requires_consent` per view function-based.

Esempio d'uso (in F4+):

    from apps.compliance.decorators import requires_consent

    @requires_consent("simulation_processing")
    def wizard_step(request):
        ...

Se il consenso non è registrato, la view non viene eseguita: si redirige
a `COMPLIANCE_CONSENT_REDIRECT_URL` (default: '/') passando `next`.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.conf import settings
from django.shortcuts import redirect

from .services import has_consent


def requires_consent(purpose_code: str) -> Callable:
    """Blocca la view finché non è stato registrato un consenso positivo."""

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            session_key = ""
            session = getattr(request, "session", None)
            if session is not None:
                session_key = getattr(session, "session_key", "") or ""

            ok = has_consent(
                purpose_code=purpose_code,
                user=getattr(request, "user", None),
                session_key=session_key,
            )
            if ok:
                return view_func(request, *args, **kwargs)

            redirect_url = getattr(settings, "COMPLIANCE_CONSENT_REDIRECT_URL", "/")
            try:
                return redirect(f"{redirect_url}?next={request.path}")
            except Exception:
                return redirect(redirect_url)

        return _wrapped

    return decorator
