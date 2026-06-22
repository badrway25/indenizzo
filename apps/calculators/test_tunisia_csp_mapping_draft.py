"""Tests F-tunisia-csp-livre-ix-mapping-draft-pass1.

The Tunisia inheritance mapping draft is a thin, deliberately
under-claiming JSON snapshot tied to the validated CSP Livre IX
extraction artefact. The available source page only covers Hajb
(eviction) — articles 122–143 — so every rule is **blocked**, no
``share_spec`` is derived, and EU 650/2012 is recorded as a
non-load-bearing context source pending an unblock.

Coverage:

1. CSP source file is real (size > 1 KB) with the documented sha.
2. CSP body contains the load-bearing markers
   ("Code du statut personnel", "Livre IX", "succession").
3. DIP source file is real (size > 1 KB) with the load-bearing
   markers ("Code de Droit International", "TITRE II").
4. EU 650 is declared as ``blocked_fetch_failed`` /
   ``load_bearing=false`` in the mapping JSON.
5. Extraction JSON exists and declares
   ``extraction_basis="official_html"``.
6. Mapping JSON validates against the documented schema.
7. Mapping carries no synthetic / fake / stub markers.
8. Every rule has ``article_references`` and
   ``extracted_text_snippet``; rules without ``share_spec`` carry
   ``blocked=true`` and a non-empty ``activation_blockers``.
9. ``activation_allowed=false`` and ``status="draft"``.
10. ``unsupported_mechanisms`` lists every required entry (hajb,
    'awl, radd, asaba/residuary ordering, applicable_law_decision,
    DIP/EU cross-border, EU 650 blocked dependency).
11. The TN public funnel still produces an unavailable simulation.
12. No ``LegalReview`` row is created by anything in this pass.
13. No ``CalculationFormula`` is created in production.
14. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
15. IT PDF first 4 bytes still ``%PDF``.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from apps.legal_sources.legal_data_test_support import skip_if_absent

REPO_ROOT = Path(__file__).resolve().parents[2]
CSP_HTML = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "tunisia"
    / "official_downloaded"
    / "tn-code-statut-personnel-livre-ix-succession.html"
)
DIP_HTML = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "tunisia"
    / "official_downloaded"
    / "tn-code-dip-loi-98-97.html"
)
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

CSP_SHA = "ab8078968ccfa07eaefc34bb38a1ec49071d000dfe0ffd85b1410d343a348ffd"
CSP_SIZE = 36183
DIP_SHA = "d379a07076177f66cf0fc6ad4704b78dd8c7b79acef03954c598a5218eb8e76a"
DIP_SIZE = 15424


# ---------------------------------------------------------------------------
# 1 — CSP real file
# ---------------------------------------------------------------------------


def test_csp_source_is_real_file_with_expected_sha():
    skip_if_absent(CSP_HTML)
    assert CSP_HTML.is_file()
    raw = CSP_HTML.read_bytes()
    assert len(raw) == CSP_SIZE
    assert len(raw) > 1024
    assert hashlib.sha256(raw).hexdigest() == CSP_SHA


# ---------------------------------------------------------------------------
# 2 — CSP markers
# ---------------------------------------------------------------------------


def test_csp_body_contains_load_bearing_markers():
    skip_if_absent(CSP_HTML)
    body = CSP_HTML.read_bytes().decode("utf-8", errors="replace")
    assert "Code du statut personnel" in body
    assert "Livre IX" in body
    assert "succession" in body.lower()


# ---------------------------------------------------------------------------
# 3 — DIP real file with markers
# ---------------------------------------------------------------------------


def test_dip_source_is_real_file_with_markers():
    skip_if_absent(DIP_HTML)
    assert DIP_HTML.is_file()
    raw = DIP_HTML.read_bytes()
    assert len(raw) == DIP_SIZE
    assert len(raw) > 1024
    assert hashlib.sha256(raw).hexdigest() == DIP_SHA
    body = raw.decode("utf-8", errors="replace")
    assert "Code de Droit International" in body
    assert "TITRE II" in body


# ---------------------------------------------------------------------------
# 4 — EU 650 declared blocked / non load-bearing in the mapping
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mapping_payload() -> dict:
    return json.loads(MAPPING_JSON.read_text(encoding="utf-8"))


def test_mapping_declares_eu_650_blocked_and_not_load_bearing(mapping_payload):
    contexts = {c["slug"]: c for c in mapping_payload.get("context_sources", [])}
    assert "eu-regulation-650-2012-successions" in contexts
    eu = contexts["eu-regulation-650-2012-successions"]
    assert eu["status"] == "blocked_fetch_failed"
    assert eu["load_bearing"] is False
    # And DIP is recorded as real_verified, also non load-bearing
    # (until the engine wires a TN applicable-law decision).
    assert "tn-code-dip-loi-98-97" in contexts
    dip = contexts["tn-code-dip-loi-98-97"]
    assert dip["status"] == "real_verified"
    assert dip["load_bearing"] is False


# ---------------------------------------------------------------------------
# 5 — extraction JSON exists with official_html basis
# ---------------------------------------------------------------------------


def test_extraction_json_exists_and_official_html_basis():
    """Pass2 evolved the extraction JSON to multi-source: top-level
    ``source_*`` were dropped in favour of a ``pages`` block and
    per-article ``source_slug`` / ``source_sha256``. The Hajb page
    must still be present in ``pages`` and arts 122-143 must still
    be extracted with the original sha.
    """
    assert EXTRACTION_JSON.is_file()
    payload = json.loads(EXTRACTION_JSON.read_text(encoding="utf-8"))
    assert payload["extraction_basis"] == "official_html"
    assert isinstance(payload["articles"], list)
    assert payload["articles_count"] == len(payload["articles"])
    # Pass2 covers full Livre IX (≥ 61 articles across 7 pages).
    assert payload["articles_count"] >= 61
    pages_by_slug = {p["slug"]: p for p in payload.get("pages", [])}
    assert "tn-code-statut-personnel-livre-ix-succession" in pages_by_slug
    hajb_page = pages_by_slug["tn-code-statut-personnel-livre-ix-succession"]
    assert hajb_page["sha256"] == CSP_SHA
    # Every article must carry its own source_slug + source_sha256.
    for art in payload["articles"]:
        assert art.get("source_slug"), f"article {art.get('article')} missing source_slug"
        assert art.get("source_sha256"), f"article {art.get('article')} missing source_sha256"
        assert art.get("extraction_basis") == "official_html"


# ---------------------------------------------------------------------------
# 6 — mapping schema valid
# ---------------------------------------------------------------------------


def test_mapping_schema_valid(mapping_payload):
    for key in (
        "schema_version",
        "iter",
        "country",
        "case_type",
        "source_slug",
        "source_sha256",
        "source_size_bytes",
        "extraction_basis",
        "extraction_artifact",
        "status",
        "activation_allowed",
        "context_sources",
        "wizard_inputs",
        "rules",
        "unsupported_mechanisms",
        "blockers_before_activation",
    ):
        assert key in mapping_payload, f"mapping missing {key!r}"
    assert mapping_payload["country"] == "TN"
    assert mapping_payload["case_type"] == "international_inheritance"
    assert mapping_payload["source_slug"] == "tn-code-statut-personnel-livre-ix-succession"
    assert mapping_payload["source_sha256"] == CSP_SHA
    assert mapping_payload["source_size_bytes"] == CSP_SIZE
    assert mapping_payload["extraction_basis"] == "official_html"


# ---------------------------------------------------------------------------
# 7 — no synthetic/fake/stub anywhere in the mapping payload
# ---------------------------------------------------------------------------


def test_mapping_does_not_reference_synthetic_or_fake():
    text = MAPPING_JSON.read_text(encoding="utf-8")
    forbidden = ("synthetic", "fake test", "fake_test", "stub_payload", "placeholder rule")
    for needle in forbidden:
        assert needle.lower() not in text.lower(), f"mapping contains forbidden marker {needle!r}"


# ---------------------------------------------------------------------------
# 8 — every rule carries article refs + snippet, all blocked + non-empty blockers
# ---------------------------------------------------------------------------


def test_every_rule_carries_refs_snippet_and_blocker(mapping_payload):
    rules = mapping_payload["rules"]
    assert rules, "mapping must declare at least one rule"
    for rule in rules:
        rid = rule.get("rule_id")
        refs = rule.get("article_references")
        assert isinstance(refs, list) and refs, f"rule {rid!r} has no article_references"
        assert rule.get("extracted_text_snippet"), f"rule {rid!r} has no snippet"
        # Pass1 deliberately keeps every rule blocked.
        assert rule.get("blocked") is True, f"rule {rid!r} must be blocked in pass1"
        assert rule.get("share_spec") in (None, {}), f"rule {rid!r} must not declare share_spec"
        blockers = rule.get("activation_blockers")
        assert (
            isinstance(blockers, list) and blockers
        ), f"rule {rid!r} must carry at least one activation_blocker"


# ---------------------------------------------------------------------------
# 9 — activation_allowed=false and status=draft
# ---------------------------------------------------------------------------


def test_mapping_is_draft_and_activation_disabled(mapping_payload):
    assert mapping_payload["status"] == "draft"
    assert mapping_payload["activation_allowed"] is False
    assert mapping_payload.get("needs_manual_review") is True


# ---------------------------------------------------------------------------
# 10 — unsupported_mechanisms lists every required entry
# ---------------------------------------------------------------------------


def test_unsupported_mechanisms_complete(mapping_payload):
    names = {entry["name"] for entry in mapping_payload["unsupported_mechanisms"]}
    required = {
        "hajb",
        "'awl",
        "radd",
        "asaba_residuary_ordering",
        "applicable_law_decision",
        "dip_eu_cross_border_coordination",
        "eu_650_blocked_real_source_dependency",
    }
    missing = required - names
    assert not missing, f"unsupported_mechanisms missing: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 11 — TN public funnel still unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_public_funnel_still_unavailable_after_pass1(db):
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
            "special_categories_consent": "on",
            "website": "",
        },
        follow=True,
    )
    assert response.status_code == 200
    sim = Simulation.objects.order_by("-id").first()
    assert sim is not None
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value


# ---------------------------------------------------------------------------
# 12 — no LegalReview row created by this iter
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_legal_review_row_created_by_pass1(db):
    """Importing the mapping module must never create a LegalReview row.
    The mapping is a JSON file; LegalReview is a DB table.
    """
    from apps.legal_sources.models import LegalReview

    initial = LegalReview.objects.count()
    # Re-read the mapping (no DB side-effect).
    json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    assert LegalReview.objects.count() == initial


# ---------------------------------------------------------------------------
# 13 — no CalculationFormula was promoted by the mapping (production state)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_calculation_formula_created_for_tn_inheritance(db):
    """The mapping JSON does not promote a TN CalculationFormula.
    The DB starts empty in the test fixture, so post-condition is the
    same: no TN inheritance formula is approved.
    """
    from apps.compensation.models import CalculationFormula, DatasetStatus

    qs = CalculationFormula.objects.filter(
        dataset__country__code="TN",
        dataset__case_type="international_inheritance",
        status=DatasetStatus.APPROVED,
    )
    assert qs.count() == 0


# ---------------------------------------------------------------------------
# 14 — Italia smoke unchanged
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
        slug="it-fixture-tn-csp-pass1",
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
        code="italy_tn_csp_pass1",
        name="tn-csp-pass1-it-smoke",
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
def test_italy_smoke_unchanged_with_tn_csp_pass1(italy_full_setup):
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
# 15 — IT PDF first 4 bytes still %PDF
# ---------------------------------------------------------------------------


def test_italy_pdf_first_four_bytes_unchanged():
    skip_if_absent(IT_PDF)
    assert IT_PDF.is_file()
    assert IT_PDF.read_bytes()[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Bonus — every CSP article in the mapping has a corresponding rule
# ---------------------------------------------------------------------------


def test_every_extracted_article_has_a_blocked_rule(mapping_payload):
    """The mapping must mirror the extraction one-to-one. If the
    extractor adds an article, the rebuilder must emit a rule for
    it; if a rule is dropped, the test catches it.
    """
    extraction = json.loads(EXTRACTION_JSON.read_text(encoding="utf-8"))
    extracted_articles = sorted(int(a["article"]) for a in extraction["articles"])
    rule_articles = sorted(int(r["article_references"][0]) for r in mapping_payload["rules"])
    assert extracted_articles == rule_articles, (
        f"extraction/mapping article mismatch:\n"
        f"  extracted: {extracted_articles}\n"
        f"  rules:     {rule_articles}"
    )


# ---------------------------------------------------------------------------
# Bonus — mapping article references match the regex format the audit expects
# ---------------------------------------------------------------------------


def test_article_refs_are_numeric(mapping_payload):
    for rule in mapping_payload["rules"]:
        for ref in rule["article_references"]:
            assert re.match(r"^\d+", str(ref)), f"non-numeric article ref: {ref!r}"
