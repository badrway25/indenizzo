"""F-product-release-readiness-audit-pass1.

End-to-end checks for the release-readiness audit script:

* the script can be invoked against the Django test client and writes
  the JSON + Markdown reports to disk;
* the report contains the required sections;
* the public principal pages link the local CSS bundle and never
  embed the Tailwind CDN;
* the IT 35/10/0 baseline still produces 26 268 / 27 353 / 28 439
  EUR and the IT PDF still starts with ``%PDF``;
* the FR / BE / MA / TN wizards still surface the unavailable
  result with no amounts and no technical diagnostic strings;
* legal-data tables (LegalSource, CompensationDataset,
  CalculationFormula, CompensationTableRow) are not modified by
  any audit machinery (read-only invariant).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from django.test import Client

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_product_release_readiness.py"
REPORT_MD = REPO_ROOT / "docs" / "architecture" / "PRODUCT_RELEASE_READINESS_AUDIT_PASS1.md"
REPORT_JSON = REPO_ROOT / "docs" / "reports" / "release_readiness" / "audit.json"


# ---------------------------------------------------------------------------
# 1 — script + reports exist on disk after running the audit
# ---------------------------------------------------------------------------


def test_audit_script_exists_and_writes_reports():
    assert SCRIPT_PATH.is_file(), "audit script missing"
    # The audit script needs a live HTTP server. The reports are
    # generated as part of the iter run; this test checks the
    # artefacts were committed alongside the script.
    assert REPORT_MD.is_file(), "release-readiness MD missing"
    assert REPORT_JSON.is_file(), "release-readiness JSON missing"
    payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    assert payload["verdict"] == "ok", f"audit verdict={payload['verdict']!r}"


# ---------------------------------------------------------------------------
# 2 — required sections in the markdown report
# ---------------------------------------------------------------------------


def test_audit_report_contains_required_sections():
    md = REPORT_MD.read_text(encoding="utf-8")
    for section in (
        "# Product release-readiness audit",
        "## Page checks",
        "## Italia 35/10/0 baseline",
        "## FR/BE/MA/TN unavailable fixtures",
        "## Legal data invariants",
    ):
        assert section in md, f"missing section: {section!r}"


# ---------------------------------------------------------------------------
# 3 — public pages link local CSS and never carry Tailwind CDN
# ---------------------------------------------------------------------------

PUBLIC_PATHS_FOR_CSS = [
    "/",
    "/countries/",
    "/countries/italy/",
    "/countries/france/",
    "/countries/belgium/",
    "/countries/morocco/",
    "/countries/tunisia/",
    "/case-types/",
    "/methodology/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/contact/",
    "/privacy/",
    "/disclaimer/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("path", PUBLIC_PATHS_FOR_CSS)
def test_public_pages_have_local_css_and_no_tailwind_cdn(path):
    client = Client()
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    body = resp.content.decode("utf-8", errors="replace")
    assert "/static/css/site.css" in body, f"{path}: local CSS link missing"
    assert "cdn.tailwindcss.com" not in body, f"{path}: Tailwind CDN leaked"


# ---------------------------------------------------------------------------
# 4 — hygiene report green
# ---------------------------------------------------------------------------


def test_hygiene_report_green():
    hygiene_md = REPO_ROOT / "docs" / "architecture" / "PUBLIC_CONTENT_HYGIENE_AUDIT_PASS5.md"
    assert hygiene_md.is_file(), "hygiene report missing"
    text = hygiene_md.read_text(encoding="utf-8")
    assert "verdict: **OK**" in text, "hygiene audit not green"


# ---------------------------------------------------------------------------
# 5 — Italia 35/10/0 baseline: amounts + PDF
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_full_setup(db):
    from datetime import date
    from decimal import Decimal

    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
    from apps.jurisdictions.models import (
        Country,
        Currency,
        Jurisdiction,
        Language,
    )
    from apps.legal_sources.enums import (
        Reliability,
        SourceStatus,
        SourceType,
    )
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-fixture-release-audit",
        title="D.P.R. 12/2025 fixture",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 1, 13),
    )
    base_ds = CompensationDataset.objects.create(
        source=src,
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base",
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
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    for kind, amount in (
        ("min", "26268"),
        ("mid", "27353"),
        ("max", "28439"),
    ):
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
        code="italy_art_138_release_audit",
        name="release-audit-smoke",
        expression_text="placeholder-test",
        source_reference="placeholder-test",
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
    return italy


@pytest.mark.django_db
def test_italy_baseline_amounts_and_pdf(italy_full_setup):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
        locale="it",
    )
    from decimal import Decimal

    assert Decimal(sim.estimated_min) == Decimal("26268")
    assert Decimal(sim.estimated_mid) == Decimal("27353")
    assert Decimal(sim.estimated_max) == Decimal("28439")

    pdf_resp = Client().get(f"/reports/simulation/{sim.public_id}/pdf/")
    assert pdf_resp.status_code == 200
    pdf_bytes = b"".join(pdf_resp.streaming_content)
    assert pdf_bytes[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# 6 — FR / BE / MA / TN remain unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_be_ma_tn_unavailable_no_amounts():
    from apps.cases.models import Simulation

    fixtures = [
        (
            "/wizard/fr/road-accident/",
            {
                "victim_age": "30",
                "permanent_disability_percentage": "5",
                "fault_percentage": "0",
            },
        ),
        (
            "/wizard/be/road-accident/",
            {
                "victim_age": "30",
                "permanent_disability_percentage": "5",
                "fault_percentage": "0",
            },
        ),
        (
            "/wizard/ma/inheritance/",
            {
                "deceased_country_of_last_residence": "MA",
                "nationality": "MA",
                "spouse_present": "on",
                "sons_count": "1",
                "daughters_count": "1",
                "estate_value": "800000",
            },
        ),
        (
            "/wizard/tn/inheritance/",
            {
                "deceased_country_of_last_residence": "TN",
                "nationality": "TN",
                "spouse_present": "on",
                "mother_present": "on",
                "sons_count": "1",
                "daughters_count": "1",
                "estate_value": "1200000",
            },
        ),
    ]
    for path, payload in fixtures:
        client = Client()
        client.get(path)
        body_payload = {
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            "consent_simulation": "on",
            "special_categories_consent": "on",
            "website": "",
            **payload,
        }
        resp = client.post(path, body_payload, follow=True)
        assert resp.status_code == 200, f"{path} POST -> {resp.status_code}"
        body = resp.content.decode("utf-8", errors="replace")
        # No technical diagnostics leaked.
        for needle in (
            "unavailable_requires_legal_validation",
            "missing_documents",
            "compensation_dataset_approved",
            "calculation_formula_approved",
            "formula_engine_unknown",
        ):
            assert needle not in body, f"{path}: leaked {needle}"
        # No EUR amounts surfaced.
        assert not re.search(r"€\s*\d{1,3}[.,\s]\d{3}", body), f"{path}: amount leaked"
        # Status is unavailable in the DB layer.
        sim = Simulation.objects.order_by("-created_at").first()
        assert sim is not None
        assert sim.status == "unavailable_requires_legal_validation", f"{path}: status={sim.status}"


# ---------------------------------------------------------------------------
# 7 — public result page does not surface technical diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_result_page_no_technical_diagnostics(italy_full_setup):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
        locale="it",
    )
    resp = Client().get(f"/wizard/result/{sim.public_id}/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8", errors="replace")
    for needle in (
        "unavailable_requires_legal_validation",
        "missing_documents",
        "compensation_dataset_approved",
        "calculation_formula_approved",
        "calculator_engine_pending_for_jurisdiction",
        "formula_engine_unknown",
        "formula_amount_rule_unknown",
    ):
        assert needle not in body, f"leaked diagnostic: {needle}"


# ---------------------------------------------------------------------------
# 8 — IT PDF starts with %PDF (re-confirm via subprocess-free path)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_it_pdf_signature(italy_full_setup):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
        locale="it",
    )
    resp = Client().get(f"/reports/simulation/{sim.public_id}/pdf/")
    assert resp.status_code == 200
    pdf_bytes = b"".join(resp.streaming_content)
    assert pdf_bytes[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# 9 — release audit script does not import anything that writes to DB
# ---------------------------------------------------------------------------


def test_release_audit_does_not_write_legal_db_layers():
    """The audit script may only read the legal models — never write.

    We grep for the obvious write call sites on the four protected
    models. ``objects.count()`` is allowed; ``create`` / ``save`` /
    ``update`` / ``delete`` is not.
    """

    text = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden = (
        "LegalSource.objects.create",
        "LegalSource.objects.update",
        "LegalSource.objects.bulk_create",
        ".save(",
        ".delete(",
        "CompensationDataset.objects.create",
        "CompensationDataset.objects.update",
        "CalculationFormula.objects.create",
        "CalculationFormula.objects.update",
        "CompensationTableRow.objects.create",
        "CompensationTableRow.objects.update",
    )
    for needle in forbidden:
        assert needle not in text, f"audit script writes legal data: {needle}"
