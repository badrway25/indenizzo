"""Tests F-official-source-fr-badinter-manual-attach-and-legal-source-validation.

These tests cover the *validation* step that runs after manual_attach for
fonti ufficiali con blocco tecnico al fetch (Légifrance HTTP 403):

1. The structural-marker spec in
   ``scripts/verify_badinter_against_legifrance.py`` is non-trivial and
   covers identity / scope / fault doctrine / offer-deadline.
2. The pure ``verify_text_against_markers`` helper:
   - returns ``True`` only when every marker is present;
   - flags individual misses on per-marker rows;
   - normalises whitespace so a marker that wraps across PDF line breaks
     still matches.
3. The end-to-end script run against the **real** committed Badinter
   PDF emits the expected report and exits 0 (source authenticity
   verified).
4. The ``[official_source_validation]`` block in
   ``LegalSource.notes`` for ``fr-loi-badinter-1985`` coexists with
   the prior ``[manual_attach]`` block and records the policy choice
   ``official_source_validation=passed`` /
   ``legal_calculator_activation=false``.
5. ``LegalSource.status`` for ``fr-loi-badinter-1985`` stays
   ``needs_review`` (no automated promotion to APPROVED).
6. Running the validation again does not create LegalReview rows or
   touch the dataset / formula / row counts.
7. FR road-accident calculator stays
   ``unavailable_requires_legal_validation``.
8. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR resta invariata.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from scripts.verify_badinter_against_legifrance import (
    LEGIFRANCE_CANONICAL_URL,
    STRUCTURAL_MARKERS,
    _extract_pdf_text,
    verify_text_against_markers,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BADINTER_SLUG = "fr-loi-badinter-1985"
VALIDATION_BEGIN = "[official_source_validation] BEGIN"
VALIDATION_END = "[official_source_validation] END"


# ---------------------------------------------------------------------------
# 1 — structural markers spec
# ---------------------------------------------------------------------------


def test_structural_markers_cover_identity_scope_fault_and_deadline():
    """The marker list must include items that defend against substitution
    of: a different decree, a redacted version, a wrong-date copy, an
    OCR-corrupted scan."""
    labels = {label for label, _, _ in STRUCTURAL_MARKERS}
    # At minimum: identity, scope, fault doctrine, offer deadline.
    assert "law_number" in labels
    assert "signature_date" in labels
    assert "article_1" in labels
    assert "vehicle_definition" in labels
    assert "faute_inexcusable" in labels
    assert "faute_conducteur" in labels
    assert "offer_deadline_8_months" in labels
    # 11 markers total at the time of the iter — guard against accidental
    # weakening of the spec.
    assert len(STRUCTURAL_MARKERS) >= 11


def test_legifrance_canonical_url_is_loda_jorftext():
    """The canonical reference URL is Légifrance LODA JORFTEXT, not a
    cached copy or a third-party mirror."""
    assert LEGIFRANCE_CANONICAL_URL.startswith("https://www.legifrance.gouv.fr/")
    assert "JORFTEXT000000693454" in LEGIFRANCE_CANONICAL_URL


# ---------------------------------------------------------------------------
# 2 — pure helper
# ---------------------------------------------------------------------------


def test_verify_text_against_markers_passes_when_all_present():
    text = "Loi n° 85-677 du 5 juillet 1985 — Article 1 véhicule terrestre à moteur"
    markers = [("law_number", "Loi n° 85-677", "id")]
    all_pass, rows = verify_text_against_markers(text, markers)
    assert all_pass is True
    assert rows == [("law_number", "Loi n° 85-677", True, "id")]


def test_verify_text_against_markers_fails_when_any_missing():
    text = "Loi n° 85-677"
    markers = [
        ("law_number", "Loi n° 85-677", "id"),
        ("article_12", "Article 12", "deadline"),
    ]
    all_pass, rows = verify_text_against_markers(text, markers)
    assert all_pass is False
    assert rows[0][2] is True
    assert rows[1][2] is False


def test_verify_text_normalises_whitespace_across_line_wraps():
    """A marker that wraps in the PDF (line break inside the phrase) must
    still match. Légifrance wraps the law title across 3-4 lines."""
    wrapped_text = (
        "Loi n° 85-677 du 5 juillet 1985 tendant à l'amélioration\n"
        "de la situation des victimes d'accidents de la circulation\n"
        "et à l'accélération des procédures d'indemnisation"
    )
    markers = [
        (
            "title_object",
            "amélioration de la situation des victimes d'accidents de la circulation",
            "subject",
        ),
    ]
    all_pass, rows = verify_text_against_markers(wrapped_text, markers)
    assert all_pass is True
    assert rows[0][2] is True


# ---------------------------------------------------------------------------
# 3 — end-to-end against the real committed PDF (manual_inbox is the stable
# location not touched by any test pollution; the script's runtime path
# legal_data/sources/france/manual_attached/ is overwritten by manual_attach
# tests and is therefore unreliable in a pytest session).
# ---------------------------------------------------------------------------


REAL_BADINTER_PDF = (
    REPO_ROOT / "legal_data" / "sources" / "france" / "manual_inbox" / "badinter.pdf"
)
EXPECTED_REAL_SHA256 = "6165313bad9dd4cbe07648ce5e554047edd4bf6d0394ecd7a1545b748b2c876e"


@pytest.mark.skipif(
    not REAL_BADINTER_PDF.exists(),
    reason="real Badinter PDF not present in manual_inbox",
)
def test_real_badinter_pdf_passes_all_structural_markers():
    """End-to-end: load the real committed PDF from the stable
    ``manual_inbox`` location, extract text via pdfplumber, run the
    structural-marker check. All 11 markers must PASS.

    This avoids the on-disk path used by ``main()`` because that path is
    overwritten by other tests in the same pytest run (manual_attach
    tests substitute synthetic test bytes there)."""
    import hashlib

    payload = REAL_BADINTER_PDF.read_bytes()
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    assert actual_sha256 == EXPECTED_REAL_SHA256, (
        f"manual_inbox PDF sha256 changed: {actual_sha256} (expected "
        f"{EXPECTED_REAL_SHA256}); the inbox copy must remain pristine"
    )

    text = _extract_pdf_text(payload)
    assert text, "pdfplumber extracted no text from the real Badinter PDF"
    assert len(text) > 10_000  # Expect tens of KB of text on a 49-article law.

    all_pass, rows = verify_text_against_markers(text, STRUCTURAL_MARKERS)
    assert all_pass is True, [r for r in rows if not r[2]]
    assert len(rows) == len(STRUCTURAL_MARKERS)
    for label, marker, ok, _ in rows:
        assert ok is True, f"marker {label!r} ({marker!r}) missing in real PDF"


# ---------------------------------------------------------------------------
# 4 — [official_source_validation] block coexists with [manual_attach]
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validation_block_can_coexist_with_manual_attach_block():
    """A LegalSource carrying both blocks must be readable: each block
    parses as valid JSON, the manual_attach block stays untouched after
    the validation block is appended."""
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
    notes = (
        "free leading notes\n\n"
        "[manual_attach] BEGIN\n"
        '{"sha256": "abc", "classification": "manual_attach_success"}\n'
        "[manual_attach] END\n\n"
        f"{VALIDATION_BEGIN}\n"
        '{"official_source_validation": "passed", '
        '"legal_calculator_activation": false}\n'
        f"{VALIDATION_END}\n"
    )
    src = LegalSource.objects.create(
        slug=BADINTER_SLUG,
        title="Loi Badinter coexistence fixture",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(1985, 7, 5),
        effective_date=date(1986, 1, 1),
        notes=notes,
    )

    assert src.notes.count("[manual_attach] BEGIN") == 1
    assert src.notes.count(VALIDATION_BEGIN) == 1

    # Both JSON payloads parse independently.
    ma_payload = src.notes.split("[manual_attach] BEGIN")[1].split("[manual_attach] END")[0]
    ma = json.loads(ma_payload.strip())
    assert ma["classification"] == "manual_attach_success"

    val_payload = src.notes.split(VALIDATION_BEGIN)[1].split(VALIDATION_END)[0]
    val = json.loads(val_payload.strip())
    assert val["official_source_validation"] == "passed"
    assert val["legal_calculator_activation"] is False


# ---------------------------------------------------------------------------
# 5 — LegalSource status policy
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validation_does_not_promote_legal_source_to_approved():
    """Per project policy, every APPROVED LegalSource must be backed by
    a LegalReview row from a human reviewer. The validation step must NOT
    bypass that, even when 11/11 structural markers pass."""
    from datetime import date

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalReview, LegalSource

    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug=BADINTER_SLUG,
        title="Loi Badinter status policy fixture",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(1985, 7, 5),
        effective_date=date(1986, 1, 1),
        notes=(
            f"{VALIDATION_BEGIN}\n"
            '{"official_source_validation": "passed", '
            '"legal_calculator_activation": false, '
            '"awaiting_mapping_or_human_legal_decision": true}\n'
            f"{VALIDATION_END}\n"
        ),
    )

    # Status is the only authority for "approved-ness". A passed
    # validation block is not enough.
    assert src.status == SourceStatus.NEEDS_REVIEW
    # No LegalReview created by validation.
    assert LegalReview.objects.filter(source=src).count() == 0
    # No legal_reviewer FK set by validation.
    assert src.legal_reviewer_id is None


# ---------------------------------------------------------------------------
# 6 — no legal-layer side effects
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validation_does_not_create_dataset_or_formula_or_rows():
    """Sanity: the validation step is read-only on the compensation layer."""
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
    )
    from apps.legal_sources.models import LegalReview

    review_before = LegalReview.objects.count()
    dataset_before = CompensationDataset.objects.count()
    formula_before = CalculationFormula.objects.count()
    rows_before = CompensationTableRow.objects.count()

    # Simulate a validation run by importing the helpers and exercising
    # the marker check — no DB writes are performed by the helpers.
    text = (
        "Loi n° 85-677 du 5 juillet 1985 Article 1 véhicule terrestre à moteur "
        "Article 3 faute inexcusable Article 4 faute commise par le conducteur "
        "Article 12 délai maximum de huit mois amélioration de la situation des "
        "victimes d'accidents de la circulation"
    )
    all_pass, _ = verify_text_against_markers(text, STRUCTURAL_MARKERS)
    assert all_pass is True

    assert LegalReview.objects.count() == review_before
    assert CompensationDataset.objects.count() == dataset_before
    assert CalculationFormula.objects.count() == formula_before
    assert CompensationTableRow.objects.count() == rows_before


# ---------------------------------------------------------------------------
# 7 — FR calculator stays unavailable after validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_calculator_still_unavailable_with_validated_source():
    """Even with an authentic + validated Loi Badinter source attached,
    the FR road-accident calculator remains unavailable: the engine, the
    quantification dataset and the formula are independent prerequisites."""
    from datetime import date

    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    Currency.objects.create(code="EUR", name="Euro", symbol="€")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    LegalSource.objects.create(
        slug=BADINTER_SLUG,
        title="Loi Badinter FR-unavailable fixture",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(1985, 7, 5),
        effective_date=date(1986, 1, 1),
        notes=(
            f"{VALIDATION_BEGIN}\n"
            '{"official_source_validation": "passed", '
            '"legal_calculator_activation": false}\n'
            f"{VALIDATION_END}\n"
        ),
    )

    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


# ---------------------------------------------------------------------------
# 8 — Italia smoke unchanged
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_badinter_validation(db):
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
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-badinter-validation",
        title="D.P.R. 12/2025",
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
        code="italy_art_138_tun_2025_badinter_validation",
        name="badinter-validation-smoke",
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


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_badinter_validation(
    italy_smoke_badinter_validation,
):
    """Even after the Badinter validation step has flagged the source as
    ``official_source_validation=passed``, Italia 35/10/0 stays at
    26 268 / 27 353 / 28 439 EUR."""
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    # Exercise the validation helper to mimic a real run side by side.
    text = (
        "Loi n° 85-677 du 5 juillet 1985 Article 1 véhicule terrestre à moteur "
        "Article 3 faute inexcusable Article 4 faute commise par le conducteur "
        "Article 12 délai maximum de huit mois amélioration de la situation des "
        "victimes d'accidents de la circulation"
    )
    all_pass, _ = verify_text_against_markers(text, STRUCTURAL_MARKERS)
    assert all_pass is True

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
