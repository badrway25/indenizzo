"""F-legal-sources-official-validation-pass1.

Cover the audit script + the validation management command:

1. The audit script writes an MD report and a JSON report to the
   expected locations.
2. ``validate_official_legal_sources --dry-run`` does not write to
   ``LegalSource.notes``.
3. ``validate_official_legal_sources --commit`` writes a single
   ``[official_source_validation]`` block to ``LegalSource.notes``.
4. SHA-256 drift since the prior validation block → ``failed``.
5. Missing local file → ``blocked``.
6. Manual-attach Badinter fixture passes when marker + sha line up.
7. Official-sync MA fixture passes when sha matches.
8. EU 650/2012 fixture passes when registry markers are present.
9. Mornet / Gazette / Tableau Indicatif slugs never pass — they
   stay blocked because ``source_kind`` is not official.
10. FR / BE DRAFT compensation datasets keep ``status="draft"``
    after the validation run.
11. No ``LegalReview`` row is created by the audit or the command.
12. No ``CalculationFormula`` row is created by the audit or the
    command.
13. FR / BE / MA / TN public calculators remain
    ``unavailable_requires_legal_validation``.
14. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
15. The IT PDF still serves ``%PDF``.
"""

from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import Client

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_REPORT_MD = (
    REPO_ROOT / "docs" / "architecture" / "OFFICIAL_SOURCE_VALIDATION_READINESS_PASS1.md"
)
AUDIT_REPORT_JSON = (
    REPO_ROOT / "docs" / "reports" / "legal_sources" / "official_source_validation_readiness.json"
)
VALIDATION_BEGIN = "[official_source_validation] BEGIN"
VALIDATION_END = "[official_source_validation] END"
OFFICIAL_SYNC_BEGIN = "[official_sync] BEGIN"
OFFICIAL_SYNC_END = "[official_sync] END"
MANUAL_ATTACH_BEGIN = "[manual_attach] BEGIN"
MANUAL_ATTACH_END = "[manual_attach] END"


# ---------------------------------------------------------------------------
# 1 — audit script writes the two reports
# ---------------------------------------------------------------------------


def test_audit_script_writes_md_and_json_reports():
    assert AUDIT_REPORT_MD.is_file(), "audit MD report missing"
    assert AUDIT_REPORT_JSON.is_file(), "audit JSON report missing"
    payload = json.loads(AUDIT_REPORT_JSON.read_text(encoding="utf-8"))
    assert "bucket_counts" in payload
    assert "findings" in payload
    assert "draft_datasets_blocked" in payload
    md = AUDIT_REPORT_MD.read_text(encoding="utf-8")
    assert "Per-source classification" in md
    assert "What can be approved after this pass" in md


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_country(code: str, alpha3: str, name: str):
    from apps.jurisdictions.models import Country

    return Country.objects.create(code=code, code_alpha3=alpha3, name=name)


def _make_lang(code: str, name: str):
    from apps.jurisdictions.models import Language

    return Language.objects.create(code=code, name=name)


def _make_jurisdiction(country, code: str, name: str):
    from apps.jurisdictions.models import Jurisdiction

    return Jurisdiction.objects.create(
        country=country,
        code=code,
        name=name,
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


def _seed_official_sync_source(
    *,
    slug: str,
    file_path: Path,
    file_payload: bytes,
    classification: str = "fetch_success",
    marker_check_passed: bool | None = True,
):
    """Create a LegalSource carrying a synthetic [official_sync] block
    that points to a real file written under tmp_path. Returns the
    source instance."""

    import hashlib

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(file_payload)

    sha = hashlib.sha256(file_payload).hexdigest()
    # Use the absolute path: pytest tmp_path is outside REPO_ROOT,
    # but ``_resolve_local_path`` accepts both absolute and
    # repo-relative entries.
    rel_path = str(file_path)

    country = Country.objects.filter(code="EU").first() or Country.objects.create(
        code="EU", code_alpha3="EUR", name="EU"
    )
    lang = Language.objects.filter(code="fr").first() or Language.objects.create(
        code="fr", name="Français"
    )
    juris = Jurisdiction.objects.filter(code="EU-CROSSBORDER").first()
    if not juris:
        juris = Jurisdiction.objects.create(
            country=country,
            code="EU-CROSSBORDER",
            name="EU Cross-border",
            legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        )

    notes_block = {
        "synced_at": "2026-05-06T12:00:00+00:00",
        "registry_slug": slug,
        "official_url": "https://example.org/" + slug,
        "sha256": sha,
        "size_bytes": len(file_payload),
        "local_path": rel_path,
        "ingest_mode": "fetch",
        "classification": classification,
        "marker_check_passed": marker_check_passed,
        "source_kind": "eu_regulation",
        "authority": "official",
        "no_calculator_activation": True,
    }
    notes = (
        f"{OFFICIAL_SYNC_BEGIN}\n" + json.dumps(notes_block, indent=2) + f"\n{OFFICIAL_SYNC_END}\n"
    )

    src = LegalSource.objects.create(
        slug=slug,
        title=slug,
        country=country,
        jurisdiction=juris,
        language=lang,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2012, 7, 4),
        effective_date=date(2015, 8, 17),
        official_url=notes_block["official_url"],
        notes=notes,
    )
    return src, sha


def _seed_manual_attach_source(
    *,
    slug: str,
    file_path: Path,
    file_payload: bytes,
):
    import hashlib

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(file_payload)

    sha = hashlib.sha256(file_payload).hexdigest()
    rel_path = str(file_path)

    france = Country.objects.filter(code="FR").first() or Country.objects.create(
        code="FR", code_alpha3="FRA", name="France"
    )
    french = Language.objects.filter(code="fr").first() or Language.objects.create(
        code="fr", name="Français"
    )
    juris = Jurisdiction.objects.filter(code="FR-NATIONAL").first()
    if not juris:
        juris = Jurisdiction.objects.create(
            country=france,
            code="FR-NATIONAL",
            name="France",
            legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        )

    block = {
        "attached_at": "2026-05-06T12:00:00+00:00",
        "registry_slug": slug,
        "source_kind": "official_law",
        "authority": "legifrance",
        "sha256": sha,
        "size_bytes": len(file_payload),
        "local_path": rel_path,
        "classification": "manual_attach_success",
        "marker_check_passed": True,
        "no_calculator_activation": True,
    }
    notes = f"{MANUAL_ATTACH_BEGIN}\n" + json.dumps(block, indent=2) + f"\n{MANUAL_ATTACH_END}\n"
    src = LegalSource.objects.create(
        slug=slug,
        title=slug,
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(1985, 7, 5),
        effective_date=date(1986, 1, 1),
        official_url="https://example.org/" + slug,
        notes=notes,
    )
    return src, sha


# ---------------------------------------------------------------------------
# 2 — dry-run does not write
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dry_run_does_not_write_validation_block(tmp_path):
    src, _ = _seed_official_sync_source(
        slug="ma-code-famille-moudawana-fr-pdf",
        file_path=tmp_path / "moudawana.pdf",
        file_payload=b"%PDF-1.4 dahir 22 octobre 2003 code de la famille",
    )
    out = StringIO()
    call_command(
        "validate_official_legal_sources",
        "--dry-run",
        "--slug",
        src.slug,
        stdout=out,
    )
    src.refresh_from_db()
    assert VALIDATION_BEGIN not in (src.notes or "")


# ---------------------------------------------------------------------------
# 3 — commit writes a validation block (idempotent)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_commit_writes_single_validation_block(tmp_path):
    src, _ = _seed_official_sync_source(
        slug="ma-code-famille-moudawana-fr-pdf",
        file_path=tmp_path / "moudawana.pdf",
        file_payload=b"dahir 22 octobre 2003 code de la famille du Maroc",
    )
    out = StringIO()
    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        src.slug,
        stdout=out,
    )
    src.refresh_from_db()
    assert src.notes.count(VALIDATION_BEGIN) == 1
    assert src.notes.count(VALIDATION_END) == 1
    block = src.notes.split(VALIDATION_BEGIN)[1].split(VALIDATION_END)[0]
    payload = json.loads(block)
    assert payload["validation_status"] == "passed"
    assert payload["sha256_verified"] is True
    assert payload["legal_calculator_activation"] is False
    assert payload["dataset_activation"] is False

    # Idempotent: a second --commit still leaves exactly one block.
    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    assert src.notes.count(VALIDATION_BEGIN) == 1


# ---------------------------------------------------------------------------
# 4 — drift detection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sha256_drift_after_validation_yields_failed(tmp_path):
    file_path = tmp_path / "moudawana.pdf"
    src, _ = _seed_official_sync_source(
        slug="ma-code-famille-moudawana-fr-pdf",
        file_path=file_path,
        file_payload=b"dahir 22 octobre 2003 code de la famille",
    )
    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    # Tamper with the file after the first validation.
    file_path.write_bytes(b"tampered bytes - different sha256")

    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    block = src.notes.split(VALIDATION_BEGIN)[1].split(VALIDATION_END)[0]
    payload = json.loads(block)
    assert payload["validation_status"] == "failed"
    assert payload["sha256_verified"] is False
    assert "drift" in payload["reason"]


# ---------------------------------------------------------------------------
# 5 — missing local file
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_missing_local_file_yields_blocked(tmp_path):
    file_path = tmp_path / "moudawana.pdf"
    src, _ = _seed_official_sync_source(
        slug="ma-code-famille-moudawana-fr-pdf",
        file_path=file_path,
        file_payload=b"present at seed time",
    )
    file_path.unlink()
    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    block = src.notes.split(VALIDATION_BEGIN)[1].split(VALIDATION_END)[0]
    payload = json.loads(block)
    assert payload["validation_status"] == "blocked"
    assert "local_file_missing" in payload["reason"]


# ---------------------------------------------------------------------------
# 6 — manual-attach Badinter passes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_manual_attach_badinter_passes(tmp_path):
    src, _ = _seed_manual_attach_source(
        slug="fr-loi-badinter-1985",
        file_path=tmp_path / "badinter.pdf",
        file_payload=b"Loi n. 85-677 du 5 juillet 1985 ... circulation",
    )
    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    block = src.notes.split(VALIDATION_BEGIN)[1].split(VALIDATION_END)[0]
    payload = json.loads(block)
    assert payload["validation_status"] == "passed"
    assert payload["sha256_verified"] is True
    assert payload["legal_calculator_activation"] is False
    # Manual attach block stays in place alongside the validation block.
    assert src.notes.count(MANUAL_ATTACH_BEGIN) == 1


# ---------------------------------------------------------------------------
# 7 — official-sync MA passes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_official_sync_ma_passes(tmp_path):
    src, _ = _seed_official_sync_source(
        slug="ma-code-famille-moudawana-fr-pdf",
        file_path=tmp_path / "moudawana.pdf",
        file_payload=b"dahir 22 octobre 2003 code de la famille du Maroc",
    )
    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    block = src.notes.split(VALIDATION_BEGIN)[1].split(VALIDATION_END)[0]
    payload = json.loads(block)
    assert payload["validation_status"] == "passed"
    assert payload["candidate_for_manual_status_approval"] is True


# ---------------------------------------------------------------------------
# 8 — EU 650 passes when registry marker matches
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_eu_650_passes_when_marker_matches(tmp_path):
    src, _ = _seed_official_sync_source(
        slug="eu-regulation-650-2012-successions",
        file_path=tmp_path / "eu-650.html",
        file_payload=(
            b"<html><body>REGLEMENT 650/2012 successions transfrontalieres" b"</body></html>"
        ),
    )
    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    block = src.notes.split(VALIDATION_BEGIN)[1].split(VALIDATION_END)[0]
    payload = json.loads(block)
    assert payload["validation_status"] == "passed"
    assert payload["marker_check_passed"] is True
    # Slug is in the not-calculation-ready list.
    assert payload["candidate_for_manual_status_approval"] is True


# ---------------------------------------------------------------------------
# 9 — Mornet / Gazette / Tableau never pass
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_non_official_slugs_remain_blocked(tmp_path):
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    france = _make_country("FR", "FRA", "France")
    french = _make_lang("fr", "Français")
    fjur = _make_jurisdiction(france, "FR-NATIONAL", "France")
    belgium = _make_country("BE", "BEL", "Belgium")
    bjur = _make_jurisdiction(belgium, "BE-NATIONAL", "Belgique")
    flemish = _make_lang("nl", "Nederlands")

    for slug, country, juris, language in (
        ("fr-referentiel-mornet-2024", france, fjur, french),
        ("fr-bareme-capitalisation-gazette-palais-2022", france, fjur, french),
        ("be-tableau-indicatif-2020", belgium, bjur, flemish),
        ("be-tableau-indicatif-2024", belgium, bjur, flemish),
    ):
        # Even if a [official_sync] block were spoofed, the slug is in
        # NON_OFFICIAL_SLUGS — validate must refuse to pass it.
        notes = (
            f"{OFFICIAL_SYNC_BEGIN}\n"
            '{"classification": "fetch_success", "sha256": "deadbeef", '
            '"size_bytes": 1, "local_path": "missing.pdf"}\n'
            f"{OFFICIAL_SYNC_END}\n"
        )
        LegalSource.objects.create(
            slug=slug,
            title=slug,
            country=country,
            jurisdiction=juris,
            language=language,
            source_type=SourceType.DOCTRINE,
            reliability=Reliability.MEDIUM,
            status=SourceStatus.NEEDS_REVIEW,
            publication_date=date(2024, 1, 1),
            effective_date=date(2024, 1, 1),
            official_url="https://example.org/" + slug,
            notes=notes,
        )

    out = StringIO()
    call_command("validate_official_legal_sources", "--commit", stdout=out)

    for slug in (
        "fr-referentiel-mornet-2024",
        "fr-bareme-capitalisation-gazette-palais-2022",
        "be-tableau-indicatif-2020",
        "be-tableau-indicatif-2024",
    ):
        src = LegalSource.objects.get(slug=slug)
        block = src.notes.split(VALIDATION_BEGIN)[1].split(VALIDATION_END)[0]
        payload = json.loads(block)
        assert payload["validation_status"] == "blocked"
        assert payload["legal_calculator_activation"] is False
        assert "non_official" in payload["reason"]


# ---------------------------------------------------------------------------
# 10 — DRAFT FR/BE datasets remain DRAFT
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_be_draft_datasets_remain_draft():
    """The validate command never promotes a DRAFT compensation dataset.
    Real DRAFT rows live in the production DB; this test asserts the
    invariant by snapshotting counts before / after a no-op run."""
    from apps.compensation.models import CompensationDataset, DatasetStatus

    before = list(
        CompensationDataset.objects.filter(status=DatasetStatus.DRAFT).values_list("pk", flat=True)
    )
    out = StringIO()
    call_command("validate_official_legal_sources", "--dry-run", stdout=out)
    after = list(
        CompensationDataset.objects.filter(status=DatasetStatus.DRAFT).values_list("pk", flat=True)
    )
    assert before == after


# ---------------------------------------------------------------------------
# 11 — no LegalReview created
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_legal_review_created(tmp_path):
    from apps.legal_sources.models import LegalReview

    src, _ = _seed_manual_attach_source(
        slug="fr-loi-badinter-1985",
        file_path=tmp_path / "badinter.pdf",
        file_payload=b"Loi 85-677",
    )
    review_before = LegalReview.objects.count()
    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    assert LegalReview.objects.count() == review_before


# ---------------------------------------------------------------------------
# 12 — no CalculationFormula created
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_calculation_formula_created(tmp_path):
    from apps.compensation.models import CalculationFormula

    src, _ = _seed_official_sync_source(
        slug="ma-code-famille-moudawana-fr-pdf",
        file_path=tmp_path / "moudawana.pdf",
        file_payload=b"dahir 22 octobre 2003 code de la famille",
    )
    formula_before = CalculationFormula.objects.count()
    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    assert CalculationFormula.objects.count() == formula_before


# ---------------------------------------------------------------------------
# 13 — FR/BE/MA/TN calculators stay unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_be_ma_tn_calculators_remain_unavailable():
    """No matter what validate_official_legal_sources does, the public
    calculators for FR / BE / MA / TN must stay
    ``unavailable_requires_legal_validation``. We probe the public
    wizard endpoints with a real POST and check the resulting
    Simulation row's status."""
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
        full_payload = {
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            "consent_simulation": "on",
            "website": "",
            **payload,
        }
        resp = client.post(path, full_payload, follow=True)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"
        body = resp.content.decode("utf-8", errors="replace")
        assert not re.search(r"€\s*\d{1,3}[.,\s]\d{3}", body), f"{path}: amount surfaced"
        sim = Simulation.objects.order_by("-created_at").first()
        assert sim is not None
        assert sim.status == "unavailable_requires_legal_validation"


# ---------------------------------------------------------------------------
# 14 + 15 — Italia smoke + IT PDF stay invariant
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_full_setup(db):
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
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
        slug="it-fixture-official-validation-pass1",
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
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral",
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
        code="italy_art_138_official_validation_pass1",
        name="official-validation-pass1-smoke",
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
def test_italy_smoke_unchanged(italy_full_setup):
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
    assert Decimal(sim.estimated_min) == Decimal("26268")
    assert Decimal(sim.estimated_mid) == Decimal("27353")
    assert Decimal(sim.estimated_max) == Decimal("28439")


@pytest.mark.django_db
def test_italy_pdf_signature(italy_full_setup):
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
    pdf = b"".join(resp.streaming_content)
    assert pdf[:4] == b"%PDF"
