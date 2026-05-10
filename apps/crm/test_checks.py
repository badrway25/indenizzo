"""
Tests F-p0-codice-1-crm-system-check.

Coprono il Django system check `crm.E001`:
- non scatta in dev (DEBUG=True);
- non scatta in prod-like se LEAD_NOTIFICATION_ENABLED=False;
- non scatta in prod-like se LEAD_NOTIFICATION_TO_EMAILS e' valorizzato;
- scatta in prod-like (DEBUG=False) con notifica abilitata e lista
  destinatari vuota.

Il check e' un guard contro deploy "silenziosamente rotti": un Lead
verrebbe persistito in DB ma nessuna email raggiungerebbe lo Studio.
"""

from __future__ import annotations

from django.test import override_settings

from apps.crm.checks import check_lead_notification_recipients


# ---------------------------------------------------------------------------
# Scenario dev: DEBUG=True non disturba mai lo sviluppatore.
# ---------------------------------------------------------------------------


@override_settings(
    DEBUG=True,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=[],
)
def test_check_passes_in_dev_even_when_recipients_empty():
    """In DEBUG=True il check non emette errori."""
    errors = check_lead_notification_recipients(app_configs=None)
    assert errors == []


# ---------------------------------------------------------------------------
# Scenario prod-like: DEBUG=False.
# ---------------------------------------------------------------------------


@override_settings(
    DEBUG=False,
    LEAD_NOTIFICATION_ENABLED=False,
    LEAD_NOTIFICATION_TO_EMAILS=[],
)
def test_check_passes_in_prod_when_notification_disabled():
    """Notifica off: il check e' silente anche in prod."""
    errors = check_lead_notification_recipients(app_configs=None)
    assert errors == []


@override_settings(
    DEBUG=False,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["lead@studiolegalebadrane.local"],
)
def test_check_passes_in_prod_when_recipients_configured():
    """Notifica on + recipients valorizzati: nessun errore."""
    errors = check_lead_notification_recipients(app_configs=None)
    assert errors == []


@override_settings(
    DEBUG=False,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=[],
)
def test_check_fails_in_prod_when_recipients_empty():
    """Notifica on + recipients vuoti in prod: emit crm.E001."""
    errors = check_lead_notification_recipients(app_configs=None)
    assert len(errors) == 1
    err = errors[0]
    assert err.id == "crm.E001"
    # Il messaggio deve menzionare entrambe le settings (orientamento dev).
    assert "LEAD_NOTIFICATION_ENABLED" in err.msg
    assert "LEAD_NOTIFICATION_TO_EMAILS" in err.msg
    # L'hint deve indicare come correggere.
    assert err.hint is not None
    assert (
        "LEAD_NOTIFICATION_TO_EMAILS" in err.hint
        or "LEAD_NOTIFICATION_ENABLED" in err.hint
    )


@override_settings(
    DEBUG=False,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=None,
)
def test_check_fails_in_prod_when_recipients_none():
    """`None` viene normalizzato a lista vuota e fa scattare crm.E001."""
    errors = check_lead_notification_recipients(app_configs=None)
    assert len(errors) == 1
    assert errors[0].id == "crm.E001"
