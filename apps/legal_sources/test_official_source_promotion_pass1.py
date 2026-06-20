"""F-legal-sources-approved-status-promotion-pass1.

Cover the ``promote_official_legal_sources`` management command:

1. ``--reviewer-username`` is required (CommandError otherwise).
2. Missing reviewer → CommandError, no DB write.
3. Non-staff reviewer → CommandError.
4. Inactive reviewer → CommandError.
5. Allow-list slug + passing validation block → promotion (with
   real LegalReview row + LegalSource.status=approved +
   legal_reviewer FK set).
6. Deny-list slug never promoted, even with a spoofed validation
   block.
7. Slug outside the allow-list never promoted.
8. Source without a passing ``[official_source_validation]`` block
   never promoted.
9. Idempotent: re-run does not duplicate the LegalReview row.
10. ``--dry-run`` (default) does not write anything.
11. No CompensationDataset / CalculationFormula /
    CompensationTableRow row is created or updated by the command.
12. FR / BE / MA / TN public calculators stay unavailable after
    promotion.
13. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
14. IT PDF still serves ``%PDF``.
15. The validate-then-promote pipeline can run end-to-end on a
    seeded fixture.
"""

from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import Client

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_BEGIN = "[official_source_validation] BEGIN"
VALIDATION_END = "[official_source_validation] END"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_validation_block(*, status: str = "passed", **overrides) -> str:
    payload = {
        "validation_status": status,
        "validated_at": "2026-05-06T12:00:00+00:00",
        "source_slug": overrides.pop("source_slug", "fr-loi-badinter-1985"),
        "sha256": "abc123",
        "sha256_verified": True,
        "marker_check_passed": True,
        "file_exists": True,
        "local_path": "legal_data/sources/fixture.pdf",
        "size_bytes": 100,
        "official_source_verified": True,
        "legal_calculator_activation": False,
        "dataset_activation": False,
        "candidate_for_manual_status_approval": True,
        "registry_markers": [],
        "classification_source": "manual_attach",
        "reason": "official source verified",
        "no_legal_review_created": True,
        "no_status_change": True,
        "no_dataset_or_formula_write": True,
    }
    payload.update(overrides)
    body = json.dumps(payload, indent=2)
    return f"{VALIDATION_BEGIN}\n{body}\n{VALIDATION_END}\n"


def _seed_legal_source(slug: str, *, country_code: str, validation_block: str | None):
    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    country = Country.objects.filter(code=country_code).first()
    if not country:
        country = Country.objects.create(
            code=country_code,
            code_alpha3=country_code + "X",
            name=country_code,
        )
    lang = Language.objects.filter(code="fr").first() or Language.objects.create(
        code="fr", name="Français"
    )
    juris_code = f"{country_code}-NATIONAL"
    juris = Jurisdiction.objects.filter(code=juris_code).first()
    if not juris:
        juris = Jurisdiction.objects.create(
            country=country,
            code=juris_code,
            name=country_code,
            legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        )
    return LegalSource.objects.create(
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
        official_url="https://example.org/" + slug,
        notes=validation_block or "",
    )


def _make_staff_reviewer(username: str = "staff_reviewer"):
    User = get_user_model()
    return User.objects.create_user(
        username=username,
        email=username + "@example.org",
        password="x",
        is_staff=True,
    )


# Markers present in config/official_source_registry.json for the Badinter
# law (``content_must_contain``); a file containing one of them passes the
# in-process marker check.
_BADINTER_MARKER = "5 juillet 1985 — accidents de la circulation"


def _seed_with_verified_file(slug: str, *, country_code: str, tmp_path, marker_text: str):
    """Seed a LegalSource with a REAL local file + an ``[official_sync]``-style
    ``[manual_attach]`` provenance block, so that promote's in-process
    re-validation (file SHA-256 + registry markers) actually passes.

    This is the SECURE contract H-1 item 4 enforces: promotion re-derives the
    verdict from the file, so a notes-only block is no longer enough.
    """
    import hashlib

    file_path = tmp_path / f"{slug}.bin"
    payload = (marker_text + " — fixture official document body").encode("utf-8")
    file_path.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()
    block = {
        "synced_at": "2026-05-06T12:00:00+00:00",
        "registry_slug": slug,
        "official_url": "https://example.org/" + slug,
        "sha256": sha,
        "size_bytes": len(payload),
        "local_path": str(file_path),
        "ingest_mode": "manual_attach",
        "classification": "manual_attach_success",
        "marker_check_passed": None,
        "source_kind": "official_law",
        "authority": "official",
        "no_calculator_activation": True,
    }
    notes = "[manual_attach] BEGIN\n" + json.dumps(block, indent=2) + "\n[manual_attach] END\n"
    return _seed_legal_source(slug, country_code=country_code, validation_block=notes)


# ---------------------------------------------------------------------------
# 1 — --reviewer-username required
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reviewer_username_is_required():
    with pytest.raises(CommandError):
        call_command("promote_official_legal_sources", stdout=StringIO())


# ---------------------------------------------------------------------------
# 2 — missing reviewer fails loudly
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_missing_reviewer_username_fails():
    with pytest.raises(CommandError, match="does not exist"):
        call_command(
            "promote_official_legal_sources",
            "--reviewer-username",
            "ghost_user_does_not_exist",
            stdout=StringIO(),
        )


# ---------------------------------------------------------------------------
# 3 — non-staff reviewer fails
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_non_staff_reviewer_fails():
    User = get_user_model()
    User.objects.create_user(username="not_staff", email="x@x.org", password="x", is_staff=False)
    with pytest.raises(CommandError, match="not a staff user"):
        call_command(
            "promote_official_legal_sources",
            "--reviewer-username",
            "not_staff",
            stdout=StringIO(),
        )


# ---------------------------------------------------------------------------
# 4 — inactive reviewer fails
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_inactive_reviewer_fails():
    User = get_user_model()
    user = User.objects.create_user(
        username="dormant",
        email="x@x.org",
        password="x",
        is_staff=True,
    )
    user.is_active = False
    user.save(update_fields=["is_active"])
    with pytest.raises(CommandError, match="not active"):
        call_command(
            "promote_official_legal_sources",
            "--reviewer-username",
            "dormant",
            stdout=StringIO(),
        )


# ---------------------------------------------------------------------------
# 5 — allow-list slug + passed validation → promoted
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_allow_list_slug_with_passed_validation_promotes(tmp_path):
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview

    reviewer = _make_staff_reviewer()
    # SECURE contract: a real file + provenance block, re-validated in-process.
    src = _seed_with_verified_file(
        "fr-loi-badinter-1985",
        country_code="FR",
        tmp_path=tmp_path,
        marker_text=_BADINTER_MARKER,
    )
    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    assert src.status == SourceStatus.APPROVED
    assert src.legal_reviewer_id == reviewer.id
    review = LegalReview.objects.get(source=src)
    assert review.reviewer_id == reviewer.id
    assert review.decision == LegalReview.Decision.APPROVE
    assert review.new_status == SourceStatus.APPROVED
    assert review.previous_status == SourceStatus.NEEDS_REVIEW


@pytest.mark.django_db
def test_spoofed_validation_block_without_file_does_not_promote():
    """H-1 item 4: a hand-forged ``[official_source_validation]`` 'passed'
    block in the notes, with NO real verifiable file, is no longer enough to
    promote. The verdict is recomputed in-process from the file, so the
    notes-only spoof is refused (fail-closed)."""
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview

    reviewer = _make_staff_reviewer()
    src = _seed_legal_source(
        "fr-loi-badinter-1985",
        country_code="FR",
        # Notes-only spoof: 'passed' block but local_path points to a file
        # that does not exist -> in-process re-validation returns 'blocked'.
        validation_block=_make_validation_block(),
    )
    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    assert src.status == SourceStatus.NEEDS_REVIEW
    assert src.legal_reviewer_id is None
    assert LegalReview.objects.filter(source=src).count() == 0


# ---------------------------------------------------------------------------
# 6 — deny-list slug never promoted even with spoofed validation block
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_deny_list_slug_never_promoted():
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview

    reviewer = _make_staff_reviewer()
    src = _seed_legal_source(
        "fr-referentiel-mornet-2024",
        country_code="FR",
        validation_block=_make_validation_block(source_slug="fr-referentiel-mornet-2024"),
    )
    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    assert src.status == SourceStatus.NEEDS_REVIEW
    assert src.legal_reviewer_id is None
    assert LegalReview.objects.filter(source=src).count() == 0


# ---------------------------------------------------------------------------
# 7 — slug outside allow-list never promoted
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unknown_slug_never_promoted():
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview

    reviewer = _make_staff_reviewer()
    src = _seed_legal_source(
        "ma-code-droits-reels-loi-39-08",
        country_code="MA",
        validation_block=_make_validation_block(source_slug="ma-code-droits-reels-loi-39-08"),
    )
    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    assert src.status == SourceStatus.NEEDS_REVIEW
    assert LegalReview.objects.filter(source=src).count() == 0


# ---------------------------------------------------------------------------
# 8 — missing / failed validation block blocks promotion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_passing_validation_blocks_promotion():
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview

    reviewer = _make_staff_reviewer()
    # Slug is in the allow-list but no validation block yet.
    src = _seed_legal_source(
        "tn-code-dip-loi-98-97",
        country_code="TN",
        validation_block=None,
    )
    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    assert src.status == SourceStatus.NEEDS_REVIEW
    assert LegalReview.objects.filter(source=src).count() == 0

    # Now add a FAILED validation block — still must not promote.
    src.notes = _make_validation_block(source_slug=src.slug, status="failed")
    src.save(update_fields=["notes"])
    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    assert src.status == SourceStatus.NEEDS_REVIEW
    assert LegalReview.objects.filter(source=src).count() == 0


# ---------------------------------------------------------------------------
# 9 — idempotent re-run
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_idempotent_rerun_does_not_duplicate_reviews(tmp_path):
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview

    reviewer = _make_staff_reviewer()
    src = _seed_with_verified_file(
        "fr-loi-badinter-1985",
        country_code="FR",
        tmp_path=tmp_path,
        marker_text=_BADINTER_MARKER,
    )
    for _ in range(3):
        call_command(
            "promote_official_legal_sources",
            "--reviewer-username",
            reviewer.username,
            "--commit",
            "--slug",
            src.slug,
            stdout=StringIO(),
        )
    src.refresh_from_db()
    assert src.status == SourceStatus.APPROVED
    assert LegalReview.objects.filter(source=src).count() == 1


# ---------------------------------------------------------------------------
# 10 — dry-run does not write
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dry_run_does_not_write():
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview

    reviewer = _make_staff_reviewer()
    src = _seed_legal_source(
        "fr-loi-badinter-1985",
        country_code="FR",
        validation_block=_make_validation_block(),
    )
    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--slug",
        src.slug,
        stdout=StringIO(),
    )
    src.refresh_from_db()
    assert src.status == SourceStatus.NEEDS_REVIEW
    assert LegalReview.objects.filter(source=src).count() == 0


# ---------------------------------------------------------------------------
# 11 — no compensation-layer side effects
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_compensation_side_effects_on_promotion():
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
    )

    reviewer = _make_staff_reviewer()
    src = _seed_legal_source(
        "fr-loi-badinter-1985",
        country_code="FR",
        validation_block=_make_validation_block(),
    )
    ds_before = CompensationDataset.objects.count()
    formula_before = CalculationFormula.objects.count()
    rows_before = CompensationTableRow.objects.count()

    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--commit",
        "--slug",
        src.slug,
        stdout=StringIO(),
    )

    assert CompensationDataset.objects.count() == ds_before
    assert CalculationFormula.objects.count() == formula_before
    assert CompensationTableRow.objects.count() == rows_before


# ---------------------------------------------------------------------------
# 12 — FR/BE/MA/TN calculators stay unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_be_ma_tn_calculators_unavailable_after_promotion():
    from apps.cases.models import Simulation

    reviewer = _make_staff_reviewer()
    for slug, country in (
        ("fr-loi-badinter-1985", "FR"),
        ("be-loi-1989-11-21-rc-auto", "BE"),
        ("ma-code-famille-moudawana-fr-pdf", "MA"),
        ("tn-code-dip-loi-98-97", "TN"),
    ):
        _seed_legal_source(
            slug,
            country_code=country,
            validation_block=_make_validation_block(source_slug=slug),
        )
    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--commit",
        stdout=StringIO(),
    )

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
        body = {
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            "consent_simulation": "on",
            "special_categories_consent": "on",
            "website": "",
            **payload,
        }
        resp = client.post(path, body, follow=True)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"
        html = resp.content.decode("utf-8", errors="replace")
        assert not re.search(r"€\s*\d{1,3}[.,\s]\d{3}", html), f"{path}: amount surfaced"
        sim = Simulation.objects.order_by("-created_at").first()
        assert sim is not None
        assert sim.status == "unavailable_requires_legal_validation", f"{path}: status={sim.status}"


# ---------------------------------------------------------------------------
# 13 + 14 — Italia smoke + PDF unchanged
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
        slug="it-fixture-promotion-pass1",
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
        code="italy_art_138_promotion_pass1",
        name="promotion-pass1-smoke",
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
def test_italy_smoke_after_promotion(italy_full_setup):
    """Run the promotion command and assert IT 35/10/0 still computes."""
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    reviewer = _make_staff_reviewer()
    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--commit",
        stdout=StringIO(),
    )
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
def test_italy_pdf_signature_after_promotion(italy_full_setup):
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


# ---------------------------------------------------------------------------
# 15 — validate-then-promote pipeline
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validate_then_promote_pipeline(tmp_path):
    """The two commands chain cleanly: validate writes the block,
    promote reads it and approves the source."""
    import hashlib

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    file_path = tmp_path / "moudawana.pdf"
    payload = b"dahir 22 octobre 2003 code de la famille du Maroc"
    file_path.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()

    morocco = Country.objects.create(code="MA", code_alpha3="MAR", name="Maroc")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=morocco,
        code="MA-NATIONAL",
        name="Maroc",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    sync_block = {
        "synced_at": "2026-05-06T12:00:00+00:00",
        "registry_slug": "ma-code-famille-moudawana-fr-pdf",
        "official_url": "https://example.org/moudawana",
        "sha256": sha,
        "size_bytes": len(payload),
        "local_path": str(file_path),
        "ingest_mode": "fetch",
        "classification": "fetch_success",
        "marker_check_passed": None,
        "source_kind": "official_law",
        "authority": "official",
        "no_calculator_activation": True,
    }
    LegalSource.objects.create(
        slug="ma-code-famille-moudawana-fr-pdf",
        title="Code de la famille",
        country=morocco,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2004, 2, 5),
        effective_date=date(2004, 2, 5),
        official_url="https://example.org/moudawana",
        notes=(
            "[official_sync] BEGIN\n" + json.dumps(sync_block, indent=2) + "\n[official_sync] END\n"
        ),
    )

    reviewer = _make_staff_reviewer()

    call_command(
        "validate_official_legal_sources",
        "--commit",
        "--slug",
        "ma-code-famille-moudawana-fr-pdf",
        stdout=StringIO(),
    )
    call_command(
        "promote_official_legal_sources",
        "--reviewer-username",
        reviewer.username,
        "--commit",
        "--slug",
        "ma-code-famille-moudawana-fr-pdf",
        stdout=StringIO(),
    )

    src = LegalSource.objects.get(slug="ma-code-famille-moudawana-fr-pdf")
    assert src.status == SourceStatus.APPROVED
    assert src.legal_reviewer_id == reviewer.id
