"""
Privacy helpers per `StaffAccessEvent` (e altri audit log).

Iter: F-local-product-hardening-pass8-audit-log-staff-access.

Funzioni pure (no DB, no I/O):
- `mask_ip(ip)` — maschera l'ultimo octet IPv4 / l'ultimo gruppo
  IPv6. Riduce la traceability nei log condivisi senza rendere
  inutile l'audit (i primi 3 octet permettono comunque di
  identificare la subnet).
- `hash_text(value)` — SHA-256 hex troncato. Stabile (lo stesso
  input produce sempre lo stesso hash) e non reversibile (il
  testo originale non è recuperabile dal solo hash).
- `build_staff_access_event_kwargs(...)` — compone i kwargs per
  `StaffAccessEvent.objects.create(**kwargs)` partendo da
  `request`/`user`/`username`. Non scrive su DB.
"""

from __future__ import annotations

import hashlib
from typing import Any

# Lunghezza hex troncata. SHA-256 produce 64 hex char; 24 bastano
# per ridurre collisioni a livelli inutili pratici (16^24 ≈ 10^28)
# senza spreco di spazio.
_HASH_LEN = 24


def mask_ip(ip: str | None) -> str:
    """
    Maschera l'ultimo octet IPv4 / l'ultimo gruppo IPv6.

    >>> mask_ip("203.0.113.42")
    '203.0.113.x'
    >>> mask_ip("2001:db8::1")
    '2001:db8::x'
    >>> mask_ip(None)
    ''
    >>> mask_ip("")
    ''
    """
    if not ip:
        return ""
    raw = ip.strip()
    # IPv6 zone id (es. fe80::1%eth0): tagliamo per stabilità.
    if "%" in raw:
        raw = raw.split("%", 1)[0]
    if "." in raw:
        parts = raw.split(".")
        if len(parts) == 4:
            parts[-1] = "x"
            return ".".join(parts)
    if ":" in raw:
        parts = raw.split(":")
        if len(parts) >= 2:
            parts[-1] = "x"
            return ":".join(parts)
    return raw


def hash_text(value: str | None) -> str:
    """
    SHA-256 hex troncato a 24 caratteri.

    Stabile: `hash_text("alice") == hash_text("alice")`.
    Non reversibile: dal solo hash non si recupera il testo.
    Una stringa vuota o None ritorna stringa vuota (no hash di
    niente: distinguere "non disponibile" da "stringa vuota
    hashata" non aggiungerebbe valore audit).
    """
    if not value:
        return ""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:_HASH_LEN]


def _client_ip_from_request(request: Any) -> str:
    """
    IP del client da `REMOTE_ADDR`, raw (non mascherato).

    Coerente col rate-limit (pass 1): NON usa `X-Forwarded-For` per
    evitare spoofing. Il caller mascherer con `mask_ip()`.
    """
    if request is None:
        return ""
    meta = getattr(request, "META", {}) or {}
    return (meta.get("REMOTE_ADDR") or "").strip()


def build_staff_access_event_kwargs(
    *,
    event_type: str,
    request: Any | None = None,
    user: Any | None = None,
    username: str | None = None,
    extra_metadata: dict | None = None,
) -> dict:
    """
    Costruisce i kwargs per `StaffAccessEvent.objects.create(...)`.

    Non scrive su DB: ritorna un dict pronto per `.create()`. Questo
    rende la funzione facilmente testabile e riusabile da view custom.

    Argomenti:
    - event_type: stringa coerente con `StaffAccessEvent.EventType`
      (`login_success`, `login_failed`, `logout`).
    - request: HttpRequest opzionale (per IP/UA/path).
    - user: oggetto User opzionale (login_success/logout). Per
      login_failed di solito è None.
    - username: username tentato/loggato. Per login_failed è il
      tentativo (verrà solo hashato, mai salvato in chiaro). Per
      login_success/logout è derivato da `user.get_username()` se
      `user` è valorizzato e `username` è None.
    - extra_metadata: dict opzionale aggiunto alla colonna
      `metadata` (JSONField). Niente PII.

    Privacy:
    - `username_hash`: SHA-256 troncato; mai username in chiaro.
    - `ip_address_masked`: mask_ip su REMOTE_ADDR.
    - `user_agent_hash`: SHA-256 troncato dell'UA.
    - `path`: presa da request.path (es. "/admin/login/"); è una
      info path, non PII.
    """
    if username is None and user is not None:
        try:
            username = user.get_username()
        except Exception:
            username = None

    raw_ip = _client_ip_from_request(request)
    raw_ua = ""
    raw_path = ""
    if request is not None:
        meta = getattr(request, "META", {}) or {}
        raw_ua = (meta.get("HTTP_USER_AGENT") or "").strip()
        raw_path = getattr(request, "path", "") or ""

    kwargs: dict[str, Any] = {
        "event_type": event_type,
        "username_hash": hash_text(username) if username else "",
        "ip_address_masked": mask_ip(raw_ip),
        "user_agent_hash": hash_text(raw_ua) if raw_ua else "",
        "path": raw_path[:512],
        "metadata": dict(extra_metadata or {}),
    }
    if user is not None and getattr(user, "pk", None) is not None:
        kwargs["user"] = user
    return kwargs
