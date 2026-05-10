"""
Django system checks per `apps.core`.

Iter: F-p0-codice-3-footer-pass1 (audit/indennizzati-platform).

Scopo: bloccare `manage.py check` (e quindi il deploy in produzione)
quando gli identificativi professionali obbligatori dello Studio non
sono configurati nel footer. Senza questi dati la piattaforma viola
gli obblighi deontologici (art. 17-bis Cod. deont. + D.Lgs. 70/2003
art. 7 + L. 247/2012 art. 12).

Logica:
- attivo solo in scenario *production-like* (`DEBUG=False`);
- in dev (`DEBUG=True`) emette al massimo un Warning, non un Error,
  cosi' lo sviluppatore non e' bloccato durante il lavoro normale;
- i campi minimi obbligatori sono concordati nel batch P0-CODICE-3:
  vedi documentazione `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 1.2.
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
