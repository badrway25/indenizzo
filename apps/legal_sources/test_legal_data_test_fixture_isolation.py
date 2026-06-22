"""F-legal-data-test-fixture-isolation-pass1 — guard tests.

Make a regression of the original bug impossible:

1. ``settings.LEGAL_DATA_ROOT`` is overridden during pytest (the
   repo-root ``conftest._isolate_legal_data_root`` fixture is the
   one source of truth here).
2. The override is *outside* the real ``legal_data/`` directory in
   the repo, so even if a test forgot to use ``tmp_path`` directly
   the bytes still cannot land on the real tree.
3. ``sync_official_sources`` reads its base directory from
   ``settings.LEGAL_DATA_ROOT`` — verified by patching the
   network fetch and asserting the file lands under the override
   path.
4. Same for ``attach_official_source_file``.
5. Same for ``download_international_legal_sources``.
6. The 227-byte synthetic stub bytes (``%PDF-1.4 fake test payload …``)
   never reach ``legal_data/sources/morocco/official_downloaded/``
   even when the production ``sync_official_sources`` test fakes
   succeed.
7. Repo grep: ``"fake test payload"`` only appears in test source
   code, never inside ``legal_data/sources/`` or other shipped
   directories. (This catches a future regression where someone
   commits a stub into the real tree.)
8. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
"""

from __future__ import annotations

import hashlib
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.management import call_command

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_LEGAL_DATA_ROOT = (REPO_ROOT / "legal_data").resolve()


# ---------------------------------------------------------------------------
# 1 + 2 — settings.LEGAL_DATA_ROOT is overridden away from the real tree
# ---------------------------------------------------------------------------


def test_legal_data_root_is_overridden_during_pytest():
    overridden = Path(settings.LEGAL_DATA_ROOT).resolve()
    assert overridden != REAL_LEGAL_DATA_ROOT, (
        f"settings.LEGAL_DATA_ROOT must be redirected to a tmp dir during "
        f"pytest. Got the real repo path: {overridden!r}"
    )


def test_legal_data_root_is_outside_real_tree():
    overridden = Path(settings.LEGAL_DATA_ROOT).resolve()
    try:
        overridden.relative_to(REAL_LEGAL_DATA_ROOT)
    except ValueError:
        return
    pytest.fail(
        f"settings.LEGAL_DATA_ROOT must NOT be a subdirectory of the real "
        f"legal_data/ tree. Got: {overridden!r}"
    )


# ---------------------------------------------------------------------------
# 3 — sync_official_sources writes under settings.LEGAL_DATA_ROOT
# ---------------------------------------------------------------------------


def _fake_pdf(url, timeout=30):
    body = b"%PDF-1.4 fake test payload " + b"x" * 200
    return ("https://example.org/", 200, "application/pdf", body)


@pytest.mark.django_db
def test_sync_official_sources_writes_under_override(tmp_path):
    isolated = Path(settings.LEGAL_DATA_ROOT).resolve()
    target = isolated / "sources" / "morocco" / "official_downloaded"
    target.mkdir(parents=True, exist_ok=True)
    real_pdf_before = (
        REAL_LEGAL_DATA_ROOT
        / "sources"
        / "morocco"
        / "official_downloaded"
        / "ma-code-famille-moudawana-fr-pdf.pdf"
    )
    sha_before = (
        hashlib.sha256(real_pdf_before.read_bytes()).hexdigest()
        if real_pdf_before.is_file()
        else None
    )

    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_pdf,
    ):
        call_command(
            "sync_official_sources",
            "--country",
            "MA",
            "--slug",
            "ma-code-famille-moudawana-fr-pdf",
            stdout=StringIO(),
        )

    written = list(target.glob("ma-code-famille-moudawana-fr-pdf.*"))
    assert written, f"no file written under override path {target!r}"

    if real_pdf_before.is_file():
        sha_after = hashlib.sha256(real_pdf_before.read_bytes()).hexdigest()
        assert sha_before == sha_after, (
            "sync_official_sources mutated the real Moudawana PDF on disk "
            "even though LEGAL_DATA_ROOT was overridden — isolation broken."
        )


# ---------------------------------------------------------------------------
# 4 — attach_official_source_file writes under settings.LEGAL_DATA_ROOT
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_attach_official_source_file_writes_under_override(tmp_path):
    from datetime import date

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    LegalSource.objects.create(
        slug="fr-loi-badinter-1985",
        title="Loi Badinter",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(1985, 7, 5),
        effective_date=date(1986, 1, 1),
        official_url="https://example.org/badinter",
    )

    src_pdf = tmp_path / "badinter_input.pdf"
    src_pdf.write_bytes(
        b"%PDF-1.4\nLoi n. 85-677 du 5 juillet 1985 victimes d'accidents "
        b"de la circulation indemnisation faute inexcusable\n" + b"x" * 800
    )

    isolated = Path(settings.LEGAL_DATA_ROOT).resolve()
    target = isolated / "sources" / "france" / "manual_attached"

    call_command(
        "attach_official_source_file",
        "--slug",
        "fr-loi-badinter-1985",
        "--file",
        str(src_pdf),
        stdout=StringIO(),
    )

    written = list(target.glob("fr-loi-badinter-1985.*")) if target.is_dir() else []
    assert written, f"manual_attach did not write under override path {target!r}"


# ---------------------------------------------------------------------------
# 5 — download_international_legal_sources writes under override
# ---------------------------------------------------------------------------


def test_download_command_uses_legal_data_root_setting():
    """Static check: the download command derives its base dir from
    ``settings.LEGAL_DATA_ROOT``, not directly from ``BASE_DIR``."""
    cmd_path = (
        REPO_ROOT
        / "apps"
        / "legal_sources"
        / "management"
        / "commands"
        / "download_international_legal_sources.py"
    )
    text = cmd_path.read_text(encoding="utf-8")
    assert "settings.LEGAL_DATA_ROOT" in text, (
        "download_international_legal_sources.py must read its base "
        "directory from settings.LEGAL_DATA_ROOT (regression guard)."
    )
    # And no longer hard-codes the previous BASE_DIR / 'legal_data'
    # pattern in the per-country branch.
    assert (
        'Path(settings.BASE_DIR) / "legal_data" / "sources"' not in text
    ), "download_international_legal_sources.py still hard-codes the old path."


def test_sync_command_uses_legal_data_root_setting():
    cmd_path = (
        REPO_ROOT
        / "apps"
        / "legal_sources"
        / "management"
        / "commands"
        / "sync_official_sources.py"
    )
    text = cmd_path.read_text(encoding="utf-8")
    assert "settings.LEGAL_DATA_ROOT" in text
    assert (
        'Path(settings.BASE_DIR) / "legal_data" / "sources"' not in text
    ), "sync_official_sources.py still hard-codes the old path."


def test_attach_command_uses_legal_data_root_setting():
    cmd_path = (
        REPO_ROOT
        / "apps"
        / "legal_sources"
        / "management"
        / "commands"
        / "attach_official_source_file.py"
    )
    text = cmd_path.read_text(encoding="utf-8")
    assert "settings.LEGAL_DATA_ROOT" in text
    assert (
        'Path(settings.BASE_DIR) / "legal_data" / "sources"' not in text
    ), "attach_official_source_file.py still hard-codes the old path."


# ---------------------------------------------------------------------------
# 6 — synthetic stub bytes never reach legal_data/sources/
# ---------------------------------------------------------------------------


def test_synthetic_stub_bytes_not_in_real_legal_data():
    """Walk the real ``legal_data/`` tree on disk and confirm the
    227-byte synthetic stub fingerprint is not present in any file
    other than the test fixtures that explicitly produce it."""
    needle = b"%PDF-1.4 fake test payload"
    contaminated: list[str] = []
    for path in (REAL_LEGAL_DATA_ROOT.rglob("*") if REAL_LEGAL_DATA_ROOT.is_dir() else []):
        if not path.is_file():
            continue
        # We tolerate the existing Moudawana file — it carries the
        # synthetic stub *because* of the historical bug. The user
        # is restoring the real PDF in a follow-up step. The point
        # of this test is to flag any *future* contamination of
        # OTHER files in the real tree.
        if path.name == "ma-code-famille-moudawana-fr-pdf.pdf":
            continue
        try:
            head = path.read_bytes()[:200]
        except OSError:
            continue
        if needle in head:
            contaminated.append(str(path.relative_to(REPO_ROOT)))
    assert not contaminated, (
        "Synthetic stub fingerprint leaked into the real legal_data/ " f"tree: {contaminated}"
    )


# ---------------------------------------------------------------------------
# 7 — `fake test payload` only inside test source code
# ---------------------------------------------------------------------------


def test_fake_test_payload_only_in_test_files():
    needle = "fake test payload"
    offending: list[str] = []
    # Walk the repo, but skip directories that are expected to
    # contain test sources.
    skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__"}
    test_path_markers = ("test_", "tests/", "fixtures/", "conftest")
    for path in REPO_ROOT.rglob("*.py"):
        rel = path.relative_to(REPO_ROOT)
        parts = set(rel.parts)
        if parts & skip_dirs:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if needle in text and not any(m in str(rel) for m in test_path_markers):
            offending.append(str(rel))
    assert not offending, (
        f"'{needle}' must only appear inside test source files; " f"found in: {offending}"
    )


# ---------------------------------------------------------------------------
# 8 — Italia smoke unchanged
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
        slug="it-fixture-isolation-pass1",
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
    src_version = approved_source_version(src)
    base_ds = CompensationDataset.objects.create(
        source=src,
        source_version=src_version,
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
        source_version=src_version,
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
        code="italy_isolation_pass1",
        name="isolation-pass1-it-smoke",
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
def test_italy_smoke_unchanged_under_isolation(italy_full_setup):
    from decimal import Decimal

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
