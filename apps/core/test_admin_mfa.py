"""
Tests F-local-product-hardening-pass5-mfa-admin.

Coprono:
- ADMIN_MFA_REQUIRED=False → admin login flow non rotto;
- /healthz/ non protetto;
- pagina pubblica (home) non protetta;
- ADMIN_MFA_REQUIRED=True + anonymous su /admin/ → redirect login;
- ADMIN_MFA_REQUIRED=True + staff senza MFA → 403 con pagina dedicata;
- ADMIN_MFA_REQUIRED=True + staff con session mfa_verified → admin OK;
- Italia smoke 35/10/0 invariato.

Tutti i test sono pure-Python: NON richiedono `django-otp` installato.
Il fallback session-based sostituisce `user.is_verified()` di
django-otp ai fini del gating logic.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def staff_user(db):
    """Crea un utente staff senza superuser. Password nota per login."""
    return User.objects.create_user(
        username="staffer",
        email="staffer@example.test",
        password="testpass123!",
        is_staff=True,
        is_superuser=False,
    )


@pytest.fixture
def italy_smoke_stack(db):
    """Pipeline minima IT che produce 26268/27353/28439 per (35,10,0)."""
    from datetime import date

    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-danno-biologico",
        title="D.P.R. 12/2025 (smoke stub)",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 1, 13),
    )
    base_ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base smoke",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    CompensationTableRow.objects.create(
        dataset=base_ds,
        row_type="tun_biological_total_amount",
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("1"),
    )
    moral_ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral smoke",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    for kind, amount in (("min", "26268"), ("mid", "27353"), ("max", "28439")):
        CompensationTableRow.objects.create(
            dataset=moral_ds,
            row_type=f"tun_biological_moral_{kind}_total_amount",
            age_min=35,
            age_max=35,
            disability_min=10,
            disability_max=10,
            point_value=Decimal(amount),
        )
    CalculationFormula.objects.create(
        dataset=base_ds,
        code="italy_art_138_tun_2025_base",
        name="Smoke range formula",
        expression_text="placeholder",
        source_reference="placeholder",
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_range_direct",
            "fault_reduction": True,
            "range_dataset_version_label": "DPR-12-2025-MORAL",
            "min_row_type": "tun_biological_moral_min_total_amount",
            "mid_row_type": "tun_biological_moral_mid_total_amount",
            "max_row_type": "tun_biological_moral_max_total_amount",
        },
        status=DatasetStatus.APPROVED,
    )
    return {"country": italy}


# ---------------------------------------------------------------------------
# Task E.1 — Flag OFF: admin login flow invariato
# ---------------------------------------------------------------------------


@override_settings(ADMIN_MFA_REQUIRED=False)
@pytest.mark.django_db
def test_admin_login_flow_normal_when_mfa_disabled():
    """Con flag off, /admin/login/ risponde 200 (form Django standard).
    Anonymous su /admin/ è redirect a login (comportamento default Django)."""
    client = Client()
    resp_login = client.get("/admin/login/")
    assert resp_login.status_code == 200
    resp_root = client.get("/admin/")
    # Django redirige anonymous su login con next=/admin/.
    assert resp_root.status_code == 302
    assert "/admin/login/" in resp_root["Location"]


# ---------------------------------------------------------------------------
# Task E.2 — /healthz/ non protetto
# ---------------------------------------------------------------------------


@override_settings(ADMIN_MFA_REQUIRED=True)
def test_healthz_is_not_gated_by_admin_mfa():
    """/healthz/ deve restare 200 anche con il guard MFA attivo."""
    client = Client()
    resp = client.get("/healthz/")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Task E.3 — Pagina pubblica non protetta
# ---------------------------------------------------------------------------


@override_settings(ADMIN_MFA_REQUIRED=True)
def test_public_home_is_not_gated_by_admin_mfa():
    """La home pubblica resta accessibile (200) anche con guard MFA on."""
    client = Client()
    resp = client.get(reverse("core:home"))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Task E.4 — Anonymous su /admin/ con flag ON: redirect login (no 403)
# ---------------------------------------------------------------------------


@override_settings(ADMIN_MFA_REQUIRED=True)
@pytest.mark.django_db
def test_anonymous_on_admin_redirects_to_login_when_mfa_required():
    """Anonymous user → redirect al form login (loop-safe)."""
    client = Client()
    resp = client.get("/admin/")
    # Django admin redirige anonymous su /admin/login/?next=/admin/.
    # Il guard NON blocca l'anonymous con 403 (il form login deve
    # restare raggiungibile per non bloccare il flusso).
    assert resp.status_code == 302
    assert "/admin/login/" in resp["Location"]


# ---------------------------------------------------------------------------
# Task E.5 — Staff senza MFA verificato: 403 con pagina dedicata
# ---------------------------------------------------------------------------


@override_settings(ADMIN_MFA_REQUIRED=True)
@pytest.mark.django_db
def test_staff_without_verified_mfa_is_blocked(staff_user):
    """Staff loggato ma senza MFA → 403 con pagina di enforcement."""
    client = Client()
    client.force_login(staff_user)
    resp = client.get("/admin/")
    assert resp.status_code == 403
    body = resp.content.decode("utf-8")
    assert "Multi-factor authentication required" in body
    assert "/admin/logout/" in body


# ---------------------------------------------------------------------------
# Task E.6 — Staff con session mfa_verified: admin OK
# ---------------------------------------------------------------------------


@override_settings(ADMIN_MFA_REQUIRED=True)
@pytest.mark.django_db
def test_staff_with_session_mfa_verified_passes_through(staff_user):
    """Con `request.session['mfa_verified']=True`, il guard fa pass-through."""
    client = Client()
    client.force_login(staff_user)
    # Imposta il flag MFA come verificato per questa sessione (mock).
    session = client.session
    session["mfa_verified"] = True
    session.save()

    resp = client.get("/admin/")
    # Staff verificato: il guard passa. Django admin accetta lo staff
    # e renderizza l'index admin (200) o redirige se il template manca.
    # Importa che NON sia 403 dal guard MFA.
    assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Task E.7 — Italia smoke contract invariato
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_smoke_run_simulation_35_10_0(italy_smoke_stack):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == Decimal("26268")
    assert sim.estimated_mid == Decimal("27353")
    assert sim.estimated_max == Decimal("28439")
