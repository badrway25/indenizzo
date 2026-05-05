"""
Tests F-ma-tn-international-inheritance-bootstrap — scaffold MA/TN.

REGOLA D'ORO: nessuna quota ereditaria reale, nessun valore monetario.
I calculator MA/TN sono placeholder che restituiscono sempre
``unavailable_requires_legal_validation`` finché lo Studio non avrà
promosso a ``approved`` fonti/dataset/formula.

Cosa verifichiamo:
- registry contiene le coppie MA/TN × international_inheritance;
- i calculator senza fonti approved → unavailable;
- i calculator con fonti approved restano unavailable con missing-document
  ``calculator_engine_pending_for_jurisdiction``;
- nessun importo / quota viene mai prodotto;
- Italy / France / Belgium calculators non vengono rotti (regressione);
- seed_morocco_inheritance_legal_sources crea fonti needs_review;
- seed_tunisia_inheritance_legal_sources crea fonti needs_review;
- seed idempotente, no downgrade da approved.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.core.management import call_command

from apps.calculators.enums import CalculationStatus, CaseType
from apps.calculators.registry import get_calculator, list_available_calculators
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_contains_morocco_inheritance_pair():
    pairs = set(list_available_calculators())
    assert ("MA-NATIONAL", CaseType.INTERNATIONAL_INHERITANCE.value) in pairs


def test_registry_contains_tunisia_inheritance_pair():
    pairs = set(list_available_calculators())
    assert ("TN-NATIONAL", CaseType.INTERNATIONAL_INHERITANCE.value) in pairs


def test_morocco_calculator_class_imports():
    from apps.calculators.engines.base import BaseCalculator
    from apps.calculators.engines.morocco import MoroccoInternationalInheritanceCalculator

    assert issubclass(MoroccoInternationalInheritanceCalculator, BaseCalculator)
    assert MoroccoInternationalInheritanceCalculator.jurisdiction_code == "MA-NATIONAL"
    assert (
        MoroccoInternationalInheritanceCalculator.case_type
        == CaseType.INTERNATIONAL_INHERITANCE.value
    )


def test_tunisia_calculator_class_imports():
    from apps.calculators.engines.base import BaseCalculator
    from apps.calculators.engines.tunisia import TunisiaInternationalInheritanceCalculator

    assert issubclass(TunisiaInternationalInheritanceCalculator, BaseCalculator)
    assert TunisiaInternationalInheritanceCalculator.jurisdiction_code == "TN-NATIONAL"
    assert (
        TunisiaInternationalInheritanceCalculator.case_type
        == CaseType.INTERNATIONAL_INHERITANCE.value
    )


def test_registry_lookup_returns_morocco_class():
    from apps.calculators.engines.morocco import MoroccoInternationalInheritanceCalculator

    cls = get_calculator("MA-NATIONAL", CaseType.INTERNATIONAL_INHERITANCE.value)
    assert cls is MoroccoInternationalInheritanceCalculator


def test_registry_lookup_returns_tunisia_class():
    from apps.calculators.engines.tunisia import TunisiaInternationalInheritanceCalculator

    cls = get_calculator("TN-NATIONAL", CaseType.INTERNATIONAL_INHERITANCE.value)
    assert cls is TunisiaInternationalInheritanceCalculator


# ---------------------------------------------------------------------------
# Calculator: senza fonti / con fonti approved → unavailable
# ---------------------------------------------------------------------------


@pytest.fixture
def morocco(db) -> Country:
    return Country.objects.create(code="MA", code_alpha3="MAR", name="Maroc")


@pytest.fixture
def tunisia(db) -> Country:
    return Country.objects.create(code="TN", code_alpha3="TUN", name="Tunisie")


@pytest.fixture
def morocco_jurisdiction(morocco: Country) -> Jurisdiction:
    return Jurisdiction.objects.create(
        country=morocco,
        code="MA-NATIONAL",
        name="Maroc (niveau national)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


@pytest.fixture
def tunisia_jurisdiction(tunisia: Country) -> Jurisdiction:
    return Jurisdiction.objects.create(
        country=tunisia,
        code="TN-NATIONAL",
        name="Tunisie (niveau national)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


@pytest.fixture
def arabic(db) -> Language:
    return Language.objects.create(code="ar", name="العربية")


@pytest.mark.django_db
def test_morocco_calculator_unavailable_when_no_sources(morocco_jurisdiction, arabic):
    from apps.calculators.engines.morocco import MoroccoInternationalInheritanceCalculator

    calc = MoroccoInternationalInheritanceCalculator(language="ar")
    r = calc.compute({"deceased_country": "MA", "spouse_exists": True, "children_count": 2})
    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert r.estimated_min is None
    assert r.estimated_mid is None
    assert r.estimated_max is None


@pytest.mark.django_db
def test_morocco_calculator_unavailable_even_with_approved_source(
    morocco, morocco_jurisdiction, arabic
):
    from apps.calculators.engines.morocco import MoroccoInternationalInheritanceCalculator

    LegalSource.objects.create(
        slug="ma-fake-source-for-test",
        title="Fake MA source (test stub, never real values)",
        country=morocco,
        jurisdiction=morocco_jurisdiction,
        language=arabic,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 1, 1),
    )

    calc = MoroccoInternationalInheritanceCalculator(language="ar")
    r = calc.compute({"deceased_country": "MA", "spouse_exists": True})
    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert r.estimated_min is None
    assert r.estimated_mid is None
    assert r.estimated_max is None
    assert len(r.sources) >= 1
    assert any(s.country == "MA" for s in r.sources)
    # F-morocco-inheritance-engine-inactive-fixture-only wired the MA
    # engine with the full gating chain. With an APPROVED source but no
    # APPROVED dataset attached, the engine now reports the more specific
    # ``compensation_dataset_approved`` diagnostic instead of the legacy
    # placeholder ``calculator_engine_pending_for_jurisdiction``. Both are
    # accepted to keep this regression test stable across the transition.
    assert (
        "calculator_engine_pending_for_jurisdiction" in r.missing_documents
        or "compensation_dataset_approved" in r.missing_documents
    )


@pytest.mark.django_db
def test_tunisia_calculator_unavailable_when_no_sources(tunisia_jurisdiction, arabic):
    from apps.calculators.engines.tunisia import TunisiaInternationalInheritanceCalculator

    calc = TunisiaInternationalInheritanceCalculator(language="ar")
    r = calc.compute({"deceased_country": "TN"})
    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert r.estimated_min is None
    assert r.estimated_mid is None
    assert r.estimated_max is None


@pytest.mark.django_db
def test_tunisia_calculator_unavailable_even_with_approved_source(
    tunisia, tunisia_jurisdiction, arabic
):
    from apps.calculators.engines.tunisia import TunisiaInternationalInheritanceCalculator

    LegalSource.objects.create(
        slug="tn-fake-source-for-test",
        title="Fake TN source (test stub, never real values)",
        country=tunisia,
        jurisdiction=tunisia_jurisdiction,
        language=arabic,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 1, 1),
    )

    calc = TunisiaInternationalInheritanceCalculator(language="ar")
    r = calc.compute({"deceased_country": "TN"})
    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert r.estimated_min is None
    assert r.estimated_mid is None
    assert r.estimated_max is None
    assert len(r.sources) >= 1
    assert any(s.country == "TN" for s in r.sources)
    # F-tunisia-inheritance-engine-inactive-fixture-only wired the TN
    # engine with the full gating chain. With an APPROVED source but no
    # APPROVED dataset attached, the engine now reports the more
    # specific ``compensation_dataset_approved`` diagnostic instead of
    # the legacy placeholder ``calculator_engine_pending_for_jurisdiction``.
    # Both are accepted to keep this regression test stable across the
    # transition.
    assert (
        "calculator_engine_pending_for_jurisdiction" in r.missing_documents
        or "compensation_dataset_approved" in r.missing_documents
    )


# ---------------------------------------------------------------------------
# Regressione: Italy + France + Belgium calculators non rotti
# ---------------------------------------------------------------------------


def test_italy_calculator_still_registered_after_ma_tn_scaffold():
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    cls = get_calculator("IT-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert cls is ItalyRoadAccidentBodilyInjuryCalculator


def test_france_calculator_still_registered_after_ma_tn_scaffold():
    from apps.calculators.engines.france import FranceRoadAccidentBodilyInjuryCalculator

    cls = get_calculator("FR-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert cls is FranceRoadAccidentBodilyInjuryCalculator


def test_belgium_calculator_still_registered_after_ma_tn_scaffold():
    from apps.calculators.engines.belgium import BelgiumRoadAccidentBodilyInjuryCalculator

    cls = get_calculator("BE-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert cls is BelgiumRoadAccidentBodilyInjuryCalculator


# ---------------------------------------------------------------------------
# Seed Morocco / Tunisia: needs_review only, idempotent
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_morocco_inheritance_legal_sources_creates_needs_review_only():
    from io import StringIO

    call_command("seed_morocco_inheritance_legal_sources", "--quiet", stdout=StringIO())

    ma_sources = LegalSource.objects.filter(country__code="MA")
    assert ma_sources.exists()
    assert not ma_sources.filter(status=SourceStatus.APPROVED).exists()
    assert ma_sources.filter(status=SourceStatus.NEEDS_REVIEW).exists()
    expected = {
        "ma-moudawana-code-famille-livre-3-successions",
        "ma-doc-obligations-contrats",
        "ma-code-procedure-civile",
        "ma-international-private-law-comparative-reference",
    }
    assert expected.issubset(set(ma_sources.values_list("slug", flat=True)))


@pytest.mark.django_db
def test_seed_morocco_idempotent_does_not_downgrade_approved():
    from io import StringIO

    call_command("seed_morocco_inheritance_legal_sources", "--quiet", stdout=StringIO())
    src = LegalSource.objects.get(slug="ma-moudawana-code-famille-livre-3-successions")
    src.status = SourceStatus.APPROVED
    src.save(update_fields=["status"])

    call_command("seed_morocco_inheritance_legal_sources", "--quiet", stdout=StringIO())
    src.refresh_from_db()
    assert src.status == SourceStatus.APPROVED


@pytest.mark.django_db
def test_seed_tunisia_inheritance_legal_sources_creates_needs_review_only():
    from io import StringIO

    call_command("seed_tunisia_inheritance_legal_sources", "--quiet", stdout=StringIO())

    tn_sources = LegalSource.objects.filter(country__code="TN")
    assert tn_sources.exists()
    assert not tn_sources.filter(status=SourceStatus.APPROVED).exists()
    assert tn_sources.filter(status=SourceStatus.NEEDS_REVIEW).exists()
    expected = {
        "tn-code-statut-personnel-livre-9-successions",
        "tn-coc-obligations-contrats",
        "tn-code-droit-international-prive-1998",
        "tn-international-private-law-comparative-reference",
    }
    assert expected.issubset(set(tn_sources.values_list("slug", flat=True)))


@pytest.mark.django_db
def test_seed_tunisia_idempotent_does_not_downgrade_approved():
    from io import StringIO

    call_command("seed_tunisia_inheritance_legal_sources", "--quiet", stdout=StringIO())
    src = LegalSource.objects.get(slug="tn-code-statut-personnel-livre-9-successions")
    src.status = SourceStatus.APPROVED
    src.save(update_fields=["status"])

    call_command("seed_tunisia_inheritance_legal_sources", "--quiet", stdout=StringIO())
    src.refresh_from_db()
    assert src.status == SourceStatus.APPROVED
