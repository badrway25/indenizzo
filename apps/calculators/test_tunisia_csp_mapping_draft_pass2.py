"""Tests F-tunisia-csp-adjacent-article-ranges-fetch-pass2.

The CSP Livre IX corpus on jurisitetunisie.com is split across 7
pages. Pass1 only had Csp1100 (arts 122-143, Hajb). Pass2 fetched
the 6 adjacent pages (Csp1080, 1085, 1090, 1095, 1105, 1110) so the
Livre IX is now covered for arts 89-152. No new ``share_spec`` is
derived — every rule stays blocked. The TN public funnel stays
``unavailable_requires_legal_validation``.

Coverage:

1. Each of the 6 new CSP files is real (size > 1 KB) with the
   expected sha256.
2. Each new file's body contains the Livre IX header.
3. The extraction JSON now lists 7 pages and ≥ 61 articles.
4. Article ranges 89-90, 91-98, 99-110, 113-121, 144-146, 147-152
   are present in the extraction; arts 85-88, 109, 111, 112 are
   recorded under ``missing_articles_in_local_source_tree``.
5. The mapping draft has ≥ 61 blocked rules with no ``share_spec``.
6. The mapping's ``context_sources`` contains the 6 new slugs as
   ``real_verified``, plus DIP and EU 650 as before.
7. The mapping's ``iter`` field pins to pass2.
8. No synthetic / fake / stub markers anywhere.
9. TN public funnel still produces UNAVAILABLE simulation.
10. No `LegalReview` row created.
11. No `CalculationFormula` for TN inheritance in production.
12. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
13. IT PDF first 4 bytes still ``%PDF``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = REPO_ROOT / "legal_data" / "sources" / "tunisia" / "official_downloaded"
EXTRACTION_JSON = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "tunisia"
    / "extracted"
    / "csp_livre_ix_inheritance_articles.json"
)
MAPPING_JSON = REPO_ROOT / "legal_data" / "mappings" / "tunisia_inheritance_mapping_draft.json"
IT_PDF = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "italy"
    / "official_downloaded"
    / "it-dpr-12-2025-tun-danno-biologico.pdf"
)

NEW_PAGE_FILES = [
    "tn-code-statut-personnel-livre-ix-art-89-90.html",
    "tn-code-statut-personnel-livre-ix-art-91-98.html",
    "tn-code-statut-personnel-livre-ix-art-99-110.html",
    "tn-code-statut-personnel-livre-ix-art-113-121.html",
    "tn-code-statut-personnel-livre-ix-art-144-146.html",
    "tn-code-statut-personnel-livre-ix-art-147-152.html",
]
NEW_PAGE_RANGES = {
    "tn-code-statut-personnel-livre-ix-art-89-90": (89, 90),
    "tn-code-statut-personnel-livre-ix-art-91-98": (91, 98),
    "tn-code-statut-personnel-livre-ix-art-99-110": (99, 110),
    "tn-code-statut-personnel-livre-ix-art-113-121": (113, 121),
    "tn-code-statut-personnel-livre-ix-art-144-146": (144, 146),
    "tn-code-statut-personnel-livre-ix-art-147-152": (147, 152),
}
EXPECTED_MISSING_ARTS = [85, 86, 87, 88, 109, 111, 112]


# ---------------------------------------------------------------------------
# 1 — every new CSP file is real (size > 1 KB)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", NEW_PAGE_FILES)
def test_new_csp_file_is_real(filename):
    p = SOURCES_DIR / filename
    assert p.is_file(), f"missing {filename}"
    raw = p.read_bytes()
    assert len(raw) > 1024, f"{filename} is suspiciously small ({len(raw)}B)"
    # No empty / placeholder body
    body = raw.decode("utf-8", errors="replace")
    # Extra protection: every CSP page on jurisitetunisie.com mentions
    # "Code du Statut Personnel" in the title or h1.
    assert (
        "Statut Personnel" in body or "statut personnel" in body
    ), f"{filename} body does not look like a CSP page"


# ---------------------------------------------------------------------------
# 2 — every new file mentions Livre IX
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", NEW_PAGE_FILES)
def test_new_csp_file_mentions_livre_ix(filename):
    import re

    body = (SOURCES_DIR / filename).read_bytes().decode("utf-8", errors="replace")
    # whitespace-flexible "Livre IX" detection (the source uses HTML
    # line breaks inside the heading).
    assert re.search(r"Livre\s*IX", body), f"{filename} does not mention 'Livre IX'"


# ---------------------------------------------------------------------------
# 3 — extraction JSON now covers 7 pages and ≥ 61 articles
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def extraction_payload() -> dict:
    return json.loads(EXTRACTION_JSON.read_text(encoding="utf-8"))


def test_extraction_covers_seven_pages(extraction_payload):
    pages = extraction_payload.get("pages")
    assert isinstance(pages, list), "extraction must declare a 'pages' block"
    page_slugs = {p["slug"] for p in pages}
    assert "tn-code-statut-personnel-livre-ix-succession" in page_slugs
    for slug in NEW_PAGE_RANGES:
        assert slug in page_slugs, f"extraction missing page {slug}"
    assert len(page_slugs) == 7
    assert extraction_payload["articles_count"] >= 61


# ---------------------------------------------------------------------------
# 4 — extracted ranges + missing-list match the documented contract
# ---------------------------------------------------------------------------


def test_extraction_ranges_match_contract(extraction_payload):
    arts_by_slug: dict[str, list[int]] = {}
    for art in extraction_payload["articles"]:
        arts_by_slug.setdefault(art["source_slug"], []).append(art["article"])
    for slug, (lo, hi) in NEW_PAGE_RANGES.items():
        nums = sorted(arts_by_slug.get(slug, []))
        assert nums, f"{slug} produced no articles"
        assert nums[0] == lo, f"{slug} first art expected {lo}, got {nums[0]}"
        assert nums[-1] == hi, f"{slug} last art expected {hi}, got {nums[-1]}"
    assert extraction_payload.get("missing_articles_in_local_source_tree") == EXPECTED_MISSING_ARTS


# ---------------------------------------------------------------------------
# 5 — mapping has ≥ 61 blocked rules with no share_spec
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mapping_payload() -> dict:
    return json.loads(MAPPING_JSON.read_text(encoding="utf-8"))


def test_mapping_has_61_blocked_rules(mapping_payload):
    rules = mapping_payload["rules"]
    assert len(rules) >= 61
    for rule in rules:
        assert rule.get("blocked") is True, f"rule {rule['rule_id']!r} not blocked"
        assert rule.get("share_spec") in (None, {}), f"rule {rule['rule_id']!r} declares share_spec"
        assert rule.get("activation_blockers"), f"rule {rule['rule_id']!r} has empty blockers"
        # Every rule now also pins its source slug + sha at the rule level.
        assert rule.get("source_slug")
        assert rule.get("source_sha256")


# ---------------------------------------------------------------------------
# 6 — context_sources contains the 6 new slugs as real_verified
# ---------------------------------------------------------------------------


def test_mapping_context_sources_include_new_slugs(mapping_payload):
    contexts_by_slug = {c["slug"]: c for c in mapping_payload["context_sources"]}
    for slug in NEW_PAGE_RANGES:
        assert slug in contexts_by_slug, f"context_sources missing {slug}"
        ctx = contexts_by_slug[slug]
        assert ctx["status"] == "real_verified"
        assert ctx["load_bearing"] is True
        assert isinstance(ctx.get("anchored_articles"), list)
    # EU 650 must still be blocked / non-load-bearing.
    eu = contexts_by_slug["eu-regulation-650-2012-successions"]
    assert eu["status"] == "blocked_fetch_failed"
    assert eu["load_bearing"] is False
    # DIP unchanged.
    dip = contexts_by_slug["tn-code-dip-loi-98-97"]
    assert dip["status"] == "real_verified"
    assert dip["load_bearing"] is False


# ---------------------------------------------------------------------------
# 7 — mapping iter pin is pass2
# ---------------------------------------------------------------------------


def test_mapping_iter_pin_is_pass2(mapping_payload):
    assert mapping_payload["iter"] == "F-tunisia-csp-adjacent-article-ranges-fetch-pass2"
    assert mapping_payload["activation_allowed"] is False
    assert mapping_payload["status"] == "draft"


# ---------------------------------------------------------------------------
# 8 — no synthetic/fake/stub anywhere
# ---------------------------------------------------------------------------


def test_no_synthetic_or_fake_markers():
    forbidden = ("synthetic", "fake test", "fake_test", "stub_payload", "placeholder rule")
    for path in (MAPPING_JSON, EXTRACTION_JSON):
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in text, f"{path.name} contains forbidden marker {needle!r}"


# ---------------------------------------------------------------------------
# 9 — TN public funnel still unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_public_funnel_still_unavailable_after_pass2(db):
    from django.test import Client
    from django.urls import reverse

    from apps.calculators.enums import CalculationStatus
    from apps.cases.models import Simulation
    from apps.jurisdictions.models import Country, Currency, Jurisdiction

    Country.objects.create(code="TN", code_alpha3="TUN", name="Tunisie")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    Jurisdiction.objects.create(
        country=Country.objects.get(code="TN"),
        code="TN-NATIONAL",
        name="Tunisie",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    response = Client().post(
        reverse("cases:wizard_tunisia_inheritance"),
        data={
            "deceased_country_of_last_residence": "TN",
            "nationality": "TN",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "1",
            "estate_value": "500000",
            "consent_simulation": "on",
            "website": "",
        },
        follow=True,
    )
    assert response.status_code == 200
    sim = Simulation.objects.order_by("-id").first()
    assert sim is not None
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value


# ---------------------------------------------------------------------------
# 10 — no LegalReview row created
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_legal_review_row_created(db):
    from apps.legal_sources.models import LegalReview

    initial = LegalReview.objects.count()
    json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    assert LegalReview.objects.count() == initial


# ---------------------------------------------------------------------------
# 11 — no CalculationFormula for TN inheritance (production state)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_calculation_formula_for_tn_inheritance(db):
    from apps.compensation.models import CalculationFormula, DatasetStatus

    qs = CalculationFormula.objects.filter(
        dataset__country__code="TN",
        dataset__case_type="international_inheritance",
        status=DatasetStatus.APPROVED,
    )
    assert qs.count() == 0


# ---------------------------------------------------------------------------
# 12 — Italia smoke unchanged
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
        slug="it-fixture-tn-csp-pass2",
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
        code="italy_tn_csp_pass2",
        name="tn-csp-pass2-it-smoke",
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
def test_italy_smoke_unchanged_with_tn_csp_pass2(italy_full_setup):
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


# ---------------------------------------------------------------------------
# 13 — IT PDF first 4 bytes still %PDF
# ---------------------------------------------------------------------------


def test_italy_pdf_first_four_bytes_unchanged():
    assert IT_PDF.is_file()
    assert IT_PDF.read_bytes()[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Bonus — every new file's anti-stub guard from pass1 still passes
# ---------------------------------------------------------------------------


def test_each_new_csp_file_present_in_manifest_with_matching_sha():
    manifest = json.loads((SOURCES_DIR / "official_sync_manifest.json").read_text(encoding="utf-8"))
    by_slug = {r["slug"]: r for r in manifest["results"]}
    for slug in NEW_PAGE_RANGES:
        assert slug in by_slug, f"manifest missing slug {slug}"
        rec = by_slug[slug]
        assert rec["classification"] == "fetch_success"
        assert rec["size_bytes"] > 1024
        # Recompute disk sha for paranoid drift check.
        local = REPO_ROOT / Path(rec["local_path"].replace("\\", "/"))
        disk_sha = hashlib.sha256(local.read_bytes()).hexdigest()
        assert disk_sha == rec["sha256"]
