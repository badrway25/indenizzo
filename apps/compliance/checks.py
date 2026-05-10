"""
Django system checks per `apps.compliance`.

Iter:
- F-p0-leg-4-retention (`compliance.E001`):
  retention policy firmata + RETENTION_MODE valido.

Scopo: bloccare `manage.py check` (e quindi il deploy in produzione)
quando la retention policy della piattaforma e' ancora in stato
working-copy/draft o quando `RETENTION_MODE` ha un valore non
ammesso. Senza una policy firmata, far girare anonymize/delete in
prod e' un atto privo di base legale documentata.

Logica:
- attivi solo in scenario *production-like* (`DEBUG=False`);
- in dev (`DEBUG=True`) i check sono silenti (default sicuro);
- copre 4 casi:
  * `RETENTION_POLICY_VERSION` vuota,
  * `RETENTION_POLICY_VERSION` contiene `working-copy` / `draft`,
  * `RETENTION_MODE` non in `dry_run|anonymize|delete`,
  * `RETENTION_ENABLED=True` con `RETENTION_MODE=dry_run` —
    blocca: dichiarare la retention attiva e poi non fare niente
    e' rumore di compliance, da chiarire a livello di policy.
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, register

from .retention import DRAFT_MARKERS, RETENTION_MODES


@register("compliance")
def check_retention_policy_signed_in_production(app_configs, **kwargs):
    """
    `compliance.E001` — fail in produzione se la retention policy
    non e' firmata o `RETENTION_MODE` e' invalido.
    """
    if getattr(settings, "DEBUG", False):
        return []

    if not getattr(settings, "RETENTION_REQUIRE_SIGNED_VERSION", True):
        # Lo Studio ha esplicitamente accettato di girare senza una
        # policy firmata (caso di test/staging). Skip silenzioso.
        return []

    issues: list[Error] = []

    version = (getattr(settings, "RETENTION_POLICY_VERSION", "") or "").strip()
    if not version:
        issues.append(
            Error(
                "RETENTION_POLICY_VERSION is empty. The platform cannot "
                "anonymize or delete user data in production without a "
                "signed retention policy version (audit trail breaks).",
                hint=(
                    "Set RETENTION_POLICY_VERSION via env var to the version "
                    "string the Studio has signed (e.g. '2026-09-15-final')."
                ),
                id="compliance.E001",
            )
        )
    else:
        lowered = version.lower()
        if any(marker in lowered for marker in DRAFT_MARKERS):
            issues.append(
                Error(
                    f"RETENTION_POLICY_VERSION={version!r} is a working-copy / draft "
                    "version. Cannot deploy retention-active in production: the "
                    "Studio must sign the retention policy first.",
                    hint=(
                        "Replace RETENTION_POLICY_VERSION with the signed version "
                        "string (no 'working-copy' / 'draft' substring) before deploy."
                    ),
                    id="compliance.E001",
                )
            )

    mode = (getattr(settings, "RETENTION_MODE", "") or "").strip()
    if mode and mode not in RETENTION_MODES:
        issues.append(
            Error(
                f"RETENTION_MODE={mode!r} is not a valid value. "
                f"Allowed: {', '.join(RETENTION_MODES)}.",
                hint=(
                    "Set RETENTION_MODE to one of: dry_run, anonymize, delete. "
                    "Default 'dry_run' is the safe option for first deploy."
                ),
                id="compliance.E001",
            )
        )

    enabled = bool(getattr(settings, "RETENTION_ENABLED", False))
    if enabled and mode == "dry_run":
        issues.append(
            Error(
                "RETENTION_ENABLED=True with RETENTION_MODE=dry_run is "
                "ambiguous in production: declares the retention active "
                "but performs no action. Either disable retention or "
                "switch to mode=anonymize.",
                hint=(
                    "Either set RETENTION_ENABLED=False (retention scaffold "
                    "only, no action) or set RETENTION_MODE=anonymize "
                    "(active retention with anonymization)."
                ),
                id="compliance.E001",
            )
        )

    return issues
