"""
Rate-limit cache-based per endpoint POST pubblici.

Iter: F-local-product-hardening-pass1.

Disegno:
- Chiave cache = (IP normalizzato, path, metodo POST).
- Window scorrevole semplice: contatore incrementale con TTL pari alla
  finestra. Quando il TTL scade, il contatore reparte da zero. Non è
  un vero "sliding window" ma è sufficiente come prima linea contro
  flooding banale.
- Backend: `django.core.cache.cache` (default LocMemCache in dev). In
  produzione si configurerà Redis tramite CACHES.
- Niente PII nei log: il logger emette solo IP normalizzato + path +
  contatore, non email/messaggi/payload.

Limiti noti (vedi `LOCAL_PRODUCT_HARDENING_PASS1.md`):
- LocMemCache è per-process. In multi-worker (gunicorn) il limite diventa
  più morbido (un attaccante può contare N volte). Per produzione: Redis.
- IP-based: clientela dietro NAT/CDN può condividere IP. Nessun bypass via
  X-Forwarded-For per evitare spoofing — usiamo solo `REMOTE_ADDR`.
- Non protegge GET (per scelta: i GET sono idempotenti, e penalizzare
  monitoring legittimo è peggio del rischio).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods  # noqa: F401  (re-export utility)

logger = logging.getLogger(__name__)


CACHE_KEY_PREFIX = "rl:public_post"


def _client_ip(request: HttpRequest) -> str:
    """
    Restituisce l'IP del client normalizzato.

    Usa solo `REMOTE_ADDR`: ignora `X-Forwarded-For` per evitare spoofing
    (un attaccante potrebbe iniettare un IP arbitrario nell'header). In
    produzione, se l'app è dietro reverse proxy fidato, sarà il proxy
    a settare `REMOTE_ADDR` correttamente.
    """
    raw = (request.META.get("REMOTE_ADDR") or "").strip()
    # IPv6 zone id eventuale (es. fe80::1%eth0): tagliamo per stabilità.
    if "%" in raw:
        raw = raw.split("%", 1)[0]
    return raw or "unknown"


def _cache_key(ip: str, path: str) -> str:
    return f"{CACHE_KEY_PREFIX}:{ip}:{path}"


def _is_enabled() -> bool:
    return bool(getattr(settings, "PUBLIC_POST_RATE_LIMIT_ENABLED", True))


def _window_seconds() -> int:
    return int(getattr(settings, "PUBLIC_POST_RATE_LIMIT_WINDOW_SECONDS", 3600))


def _max_attempts() -> int:
    return int(getattr(settings, "PUBLIC_POST_RATE_LIMIT_MAX_ATTEMPTS", 20))


def _too_many_response(request: HttpRequest) -> HttpResponse:
    """Risposta 429. Privilegia template HTML; fallback a testo."""
    try:
        response = render(request, "public/rate_limited.html", status=429)
    except Exception:  # pragma: no cover — fallback estremo
        response = HttpResponse(
            "Too many requests. Please try again later.",
            status=429,
            content_type="text/plain; charset=utf-8",
        )
    response["Retry-After"] = str(_window_seconds())
    return response


def public_post_rate_limit(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """
    Decoratore per view che accettano POST pubblici.

    Comportamento:
    - GET (e altri metodi non-POST): pass-through. Nessun contatore.
    - POST con rate-limit disabilitato (settings flag False): pass-through.
    - POST con contatore <= max_attempts: incrementa e prosegue.
    - POST con contatore > max_attempts: risponde 429 SENZA chiamare la
      view. Niente Lead/Simulation/ConsentRecord creati.

    Nota: il contatore aumenta SUL POST, anche se la view a valle decide
    di rifiutare il payload (form invalido). Questo è voluto: un
    attaccante non deve poter eludere il rate-limit sbagliando di
    proposito il form.
    """

    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.method != "POST" or not _is_enabled():
            return view_func(request, *args, **kwargs)

        ip = _client_ip(request)
        path = request.path
        key = _cache_key(ip, path)
        window = _window_seconds()
        max_attempts = _max_attempts()

        # Contatore atomico: cache.add() crea la chiave a 1 se assente
        # (con TTL=window); in caso contrario incrementiamo.
        if cache.add(key, 1, timeout=window):
            count = 1
        else:
            try:
                count = cache.incr(key)
            except ValueError:
                # Chiave scaduta tra add() e incr(): ricrea.
                cache.set(key, 1, timeout=window)
                count = 1

        if count > max_attempts:
            # Niente PII: ip parziale + path + contatore. L'IP completo non
            # è sensibile ma comunque mascheriamo l'ultimo octet IPv4 per
            # ridurre la traceability nei log condivisi.
            logger.warning(
                "rate_limit.exceeded ip=%s path=%s count=%d max=%d",
                _mask_ip_for_log(ip),
                path,
                count,
                max_attempts,
            )
            return _too_many_response(request)

        return view_func(request, *args, **kwargs)

    return _wrapped


def _mask_ip_for_log(ip: str) -> str:
    """Maschera l'ultimo octet IPv4 / l'ultimo gruppo IPv6 per i log."""
    if "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            parts[-1] = "x"
            return ".".join(parts)
    if ":" in ip:
        parts = ip.split(":")
        if len(parts) > 1:
            parts[-1] = "x"
            return ":".join(parts)
    return ip
