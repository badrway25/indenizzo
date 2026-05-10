"""
Django system checks per `apps.core`.

Iter:
- F-p0-codice-3-footer-pass1 (`core.E001`/`core.W001`):
  identificazione professionale obbligatoria.
- F-p0-codice-4-csp (`core.E002`, `core.E003`):
  Content-Security-Policy enforcing in produzione.

Scopo: bloccare `manage.py check` (e quindi il deploy in produzione)
quando la configurazione di sicurezza/deontologia minima non e'
soddisfatta:
- footer professionale: art. 17-bis Cod. deont. + D.Lgs. 70/2003 art. 7;
- CSP enforcing: chiude P0-SEC-1 in `docs/SECURITY_INDEX.md`.

Logica:
- attivi solo in scenario *production-like* (`DEBUG=False`);
- in dev (`DEBUG=True`) i check footer emettono Warning, i check CSP
  sono silenti (default sicuro: CSP_ENABLED=True).
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, Warning, register


# Campi obbligatori per la conformita' deontologica P0:
#   - chi e' l'avvocato responsabile;
#   - dove e' iscritto;
#   - come si paga (P.IVA);
#   - dove riceve PEC;
#   - dove ha lo studio fisico;
#   - chi assicura la sua responsabilita' professionale;
#   - n. polizza professionale.
#
# Esclusi dai minimi P0 (raccomandati ma non bloccanti):
#   - STUDIO_BAR_REGISTRATION_NUMBER (solo se richiesto da Foro);
#   - STUDIO_TAX_CODE (alcuni Foro non lo richiedono nel footer);
#   - STUDIO_PROFESSIONAL_INSURANCE_CEILING (massimale).
_REQUIRED_FIELDS = (
    "STUDIO_LEAD_LAWYER_NAME",
    "STUDIO_BAR_ASSOCIATION",
    "STUDIO_VAT_NUMBER",
    "STUDIO_PEC_EMAIL",
    "STUDIO_PHYSICAL_ADDRESS",
    "STUDIO_PROFESSIONAL_INSURANCE_INSURER",
    "STUDIO_PROFESSIONAL_INSURANCE_POLICY",
)


@register("core")
def check_studio_professional_identification(app_configs, **kwargs):
    """
    `core.E001` (prod) / `core.W001` (dev) — verifica che i campi
    obbligatori dell'identificativo professionale siano valorizzati.

    Production-like (`DEBUG=False`):
        Error per ogni campo mancante. `manage.py check` ritorna
        non-zero, blocca il deploy.

    Dev (`DEBUG=True`):
        Warning unico (riepilogo) per ricordare allo sviluppatore
        che prima del go-live i campi vanno configurati. Non rompe
        il flusso locale.
    """
    is_prod_like = not getattr(settings, "DEBUG", False)
    missing = [
        field
        for field in _REQUIRED_FIELDS
        if not str(getattr(settings, field, "") or "").strip()
    ]

    if not missing:
        return []

    if is_prod_like:
        # In prod: un Error per campo. Massimizza il segnale all'ops.
        return [
            Error(
                f"{field} is empty. The professional identification footer "
                "must expose this value before go-live (deontology + "
                "D.Lgs. 70/2003 art. 7).",
                hint=(
                    f"Set {field} via env var (DJANGO_{field}=...) in the "
                    "production environment, or disable the production "
                    "scenario (DEBUG=True) to keep iterating locally."
                ),
                id="core.E001",
            )
            for field in missing
        ]

    # Dev: un solo Warning consolidato (non spam).
    return [
        Warning(
            "Professional identification fields are empty: "
            f"{', '.join(missing)}. The footer renders "
            "[da configurare prima del go-live] placeholders. Required "
            "before production deploy.",
            hint=(
                "Configure the missing STUDIO_* env vars before go-live. "
                "In dev this is a Warning; in prod (DEBUG=False) it becomes "
                "an Error and blocks `manage.py check`."
            ),
            id="core.W001",
        )
    ]


@register("core")
def check_csp_enabled_in_production(app_configs, **kwargs):
    """
    `core.E002` — fail in produzione se CSP non e' attivo.

    Chiude P0-SEC-1 (`docs/SECURITY_INDEX.md`): il deploy in
    produzione deve emettere `Content-Security-Policy`. Se
    `CSP_ENABLED=False` con `DEBUG=False`, blocchiamo.

    In dev (`DEBUG=True`) il check e' silenzioso: lo sviluppatore
    puo' disattivare CSP per debug locale senza fastidi.
    """
    if getattr(settings, "DEBUG", False):
        return []
    if not getattr(settings, "CSP_ENABLED", True):
        return [
            Error(
                "CSP_ENABLED=False in production-like scenario. The site "
                "would deploy without a Content-Security-Policy header, "
                "leaving XSS/clickjacking mitigations entirely to the "
                "reverse proxy (no Django-side guarantee).",
                hint=(
                    "Set CSP_ENABLED=True before deploy. To dry-run the "
                    "policy without enforcing, use CSP_REPORT_ONLY=True "
                    "(but consider that production scenarios also fail "
                    "core.E003 in that case)."
                ),
                id="core.E002",
            )
        ]
    return []


_CONSENT_VERSION_DRAFT_MARKERS = ("working-copy", "draft")


@register("core")
def check_consent_versions_signed_in_production(app_configs, **kwargs):
    """
    `core.E004` — fail in produzione se le versioni dei consensi
    GDPR (privacy art. 6 + special categories art. 9) non sono
    firmate.

    Iter F-p0-leg-3-consent. Il deploy in produzione richiede che
    PRIVACY_NOTICE_VERSION e SPECIAL_CATEGORIES_NOTICE_VERSION
    siano valori firmati dallo Studio (es. "2026-09-15-final"),
    non placeholder come `working-copy-...` o `draft-...`. Senza
    versione firmata il consenso raccolto e' un consenso a un
    testo che potrebbe ancora cambiare.

    In dev (`DEBUG=True`) il check e' silenzioso.
    """
    if getattr(settings, "DEBUG", False):
        return []

    issues: list[Error] = []
    pairs = (
        ("PRIVACY_NOTICE_VERSION", "GDPR art. 6 base privacy notice"),
        ("SPECIAL_CATEGORIES_NOTICE_VERSION", "GDPR art. 9 special categories notice"),
    )
    for setting_name, label in pairs:
        value = (getattr(settings, setting_name, "") or "").strip()
        if not value:
            issues.append(
                Error(
                    f"{setting_name} is empty. Cannot record signed "
                    f"consent for {label} — every submit would persist "
                    "an empty version field on Lead/Simulation.",
                    hint=(
                        f"Set {setting_name} via env var to the version "
                        "string the Studio has signed (e.g. "
                        "'2026-09-15-final')."
                    ),
                    id="core.E004",
                )
            )
            continue
        lowered = value.lower()
        if any(marker in lowered for marker in _CONSENT_VERSION_DRAFT_MARKERS):
            issues.append(
                Error(
                    f"{setting_name}={value!r} is a working-copy / draft "
                    f"version. Cannot deploy to production: the Studio "
                    "must sign the final wording first.",
                    hint=(
                        f"Replace {setting_name} with the signed version "
                        "string (no 'working-copy' / 'draft' substring) "
                        "before deploy."
                    ),
                    id="core.E004",
                )
            )
    return issues


@register("core")
def check_csp_enforcing_in_production(app_configs, **kwargs):
    """
    `core.E003` — fail in produzione se CSP gira solo in
    Report-Only.

    Report-Only e' utile per dry-run su staging, ma non offre
    protezione attiva. Per chiudere P0-SEC-1 vogliamo enforcing.

    In dev (`DEBUG=True`) il check e' silenzioso.
    """
    if getattr(settings, "DEBUG", False):
        return []
    csp_enabled = getattr(settings, "CSP_ENABLED", True)
    if not csp_enabled:
        # Caso gia' coperto da core.E002, evita doppio segnale.
        return []
    if getattr(settings, "CSP_REPORT_ONLY", False):
        return [
            Error(
                "CSP_REPORT_ONLY=True in production-like scenario. The "
                "browser would only report violations, not block them. "
                "P0-SEC-1 (closing CSP gap) requires enforcing.",
                hint=(
                    "Set CSP_REPORT_ONLY=False before deploy. To run "
                    "report-only in parallel with enforcing (advanced), "
                    "use a custom CONTENT_SECURITY_POLICY_REPORT_ONLY "
                    "setting alongside enforcing."
                ),
                id="core.E003",
            )
        ]
    return []
