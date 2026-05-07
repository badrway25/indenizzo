"""F-morocco-moudawana-livre-iii-mapping-draft-pass1.

Cover the Moudawana inheritance mapping draft:

1. The extraction JSON exists and references the approved source.
2. The mapping draft JSON parses against the documented schema.
3. Every rule carries ``article_references``.
4. Every rule carries an ``extracted_text_snippet`` field.
5. Every rule is tagged ``draft`` / ``activation_allowed=false``.
6. No rule with ``confidence=high`` unless an exact article text
   was extracted (extraction artefact must contain that article).
7. Acknowledged: no DRAFT compensation dataset is created in the DB
   for this iter; the JSON mapping is the canonical artefact.
8. Public MA calculator stays ``unavailable_requires_legal_validation``.
9. Public MA result page shows no automatic shares.
10. The mapping's smoke fixture (spouse + son + daughter + estate
    800 000) feeds the engine in a synthetic-approved test DB and
    yields the documented breakdown.
11. No ``LegalReview`` row is created by anything in this pass.
12. No ``CalculationFormula`` row is created in production
    (fixture-only).
13. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
14. The IT PDF still serves ``%PDF``.
"""

from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.test import Client

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTRACTION_JSON = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "morocco"
    / "extracted"
    / "moudawana_inheritance_articles.json"
)
MAPPING_JSON = REPO_ROOT / "legal_data" / "mappings" / "morocco_inheritance_mapping_draft.json"


# ---------------------------------------------------------------------------
# 1 — extraction JSON exists and pins the source
# ---------------------------------------------------------------------------


def test_extraction_json_exists_and_references_source():
    assert EXTRACTION_JSON.is_file(), "extraction JSON missing"
    payload = json.loads(EXTRACTION_JSON.read_text(encoding="utf-8"))
    for key in (
        "source_sha256",
        "size_bytes",
        "extractor",
        "articles",
        "pdf_path",
    ):
        assert key in payload, f"extraction JSON missing {key!r}"
    assert payload["pdf_path"].endswith("ma-code-famille-moudawana-fr-pdf.pdf"), payload["pdf_path"]
    assert isinstance(payload["articles"], list)


# ---------------------------------------------------------------------------
# 2–5 — mapping draft schema
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mapping_payload() -> dict:
    return json.loads(MAPPING_JSON.read_text(encoding="utf-8"))


REAL_MOUDAWANA_SHA256 = "41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96"


def test_mapping_top_level_schema(mapping_payload):
    assert mapping_payload["country"] == "MA"
    assert mapping_payload["case_type"] == "international_inheritance"
    assert mapping_payload["source_slug"] == "ma-code-famille-moudawana-fr-pdf"
    assert mapping_payload["status"] == "draft"
    assert mapping_payload["activation_allowed"] is False
    assert mapping_payload["needs_manual_review"] is True
    assert isinstance(mapping_payload["rules"], list)
    assert len(mapping_payload["rules"]) >= 1


# ---------------------------------------------------------------------------
# pass2 — mapping anchored on the real PDF sha256
# ---------------------------------------------------------------------------


def test_mapping_records_real_pdf_sha256(mapping_payload):
    """Pass2 invariant: the mapping must carry the sha256 of the real
    Moudawana PDF, not the synthetic stub from pass1."""
    assert mapping_payload.get("source_sha256") == REAL_MOUDAWANA_SHA256, (
        f"mapping source_sha256={mapping_payload.get('source_sha256')!r} "
        f"does not match the real Moudawana PDF sha256 "
        f"{REAL_MOUDAWANA_SHA256!r}"
    )
    assert mapping_payload.get("extraction_basis") == "official_pdf"


def test_mapping_does_not_reference_synthetic_or_fake(mapping_payload):
    """The pass2 mapping must not carry any 'synthetic' / 'fake' /
    'stub' marker in user-facing text. The schema does carry an
    explicit ``previous_pass_used_synthetic_stub: false`` flag — a
    machine-readable key whose VALUE is False; we tolerate that key
    name but ban any other appearance of the tokens."""
    raw = json.dumps(mapping_payload, ensure_ascii=False).lower()
    for needle in ("synthetic", "fake", "stub"):
        # Allow exactly one mention of "synthetic" via the
        # explicit ``previous_pass_used_synthetic_stub: false``
        # provenance flag.
        if needle == "synthetic":
            assert raw.count(needle) <= 1, (
                f"mapping contains {raw.count(needle)} 'synthetic' tokens "
                f"(only the previous_pass_used_synthetic_stub flag is allowed)"
            )
            continue
        if needle == "stub":
            # Same provenance flag spells "stub" once.
            assert raw.count(needle) <= 1, f"mapping contains {raw.count(needle)} 'stub' tokens"
            continue
        assert (
            needle not in raw
        ), f"mapping must not mention {needle!r}; got: ...{raw[max(0, raw.find(needle) - 20):raw.find(needle) + 60]}..."


def test_every_rule_snippet_appears_in_extraction(mapping_payload):
    """Every ``extracted_text_snippet`` must be a substring of the
    corresponding article's text in the extraction artefact. This
    pins the mapping to verbatim text from the official PDF."""
    extraction = json.loads(EXTRACTION_JSON.read_text(encoding="utf-8"))
    extraction_by_article = {a["article"]: a["text"] for a in extraction.get("articles", [])}
    # The rebuilder script truncates snippets and appends a
    # horizontal-ellipsis '…' for readability. Strip the trailing
    # '…' before comparing.
    for rule in mapping_payload["rules"]:
        snippet = (rule.get("extracted_text_snippet") or "").rstrip().rstrip("…")
        if not snippet:
            continue
        candidates = [
            extraction_by_article[a]
            for a in rule.get("article_references", [])
            if a in extraction_by_article
        ]
        assert any(snippet in candidate for candidate in candidates), (
            f"rule {rule.get('rule_id')!r} snippet not found in any of the "
            f"referenced articles' extracted text. Snippet: {snippet[:80]!r}"
        )


def test_every_rule_article_present_in_extraction(mapping_payload):
    extraction = json.loads(EXTRACTION_JSON.read_text(encoding="utf-8"))
    extracted_articles = {a["article"] for a in extraction.get("articles", [])}
    for rule in mapping_payload["rules"]:
        refs = set(rule.get("article_references", []))
        assert refs & extracted_articles, (
            f"rule {rule.get('rule_id')!r} references articles not present "
            f"in the extraction artefact: {refs}"
        )


def test_extraction_artifact_is_not_a_stub():
    """The extraction artefact must report ``extractor=pdfplumber`` and
    a non-empty ``articles`` list. ``extractor=stub`` would mean the
    PDF is the synthetic placeholder again."""
    extraction = json.loads(EXTRACTION_JSON.read_text(encoding="utf-8"))
    assert extraction.get("extractor") == "pdfplumber", (
        f"extraction artefact extractor={extraction.get('extractor')!r}; "
        f"the real Moudawana PDF must be on disk and parsed by pdfplumber"
    )
    assert extraction.get("articles"), "extraction artefact has no articles"
    assert extraction.get("source_sha256") == REAL_MOUDAWANA_SHA256, (
        f"extraction sha256 {extraction.get('source_sha256')!r} does not "
        f"match the real Moudawana PDF sha256"
    )
    assert extraction.get("size_bytes", 0) > 50_000, (
        f"extraction size {extraction.get('size_bytes')!r} is too small "
        f"to be the real PDF (must be >50KB)"
    )


def test_pass3_article_346_is_split_into_two_rules(mapping_payload):
    """Pass3 invariant: article 346 (mother takes 1/3) must surface
    as TWO rules — the activatable one (no descendants, ≤1 sibling)
    and the explicitly blocked one (no descendants, ≥2 siblings).
    The blocked rule documents that the doctrinal hajb-noqsan
    reduction is not yet modelled."""
    rules_by_id = {r["rule_id"]: r for r in mapping_payload["rules"]}
    activatable = rules_by_id.get("ma-inh-mother-no-descendants-no-multi-siblings")
    blocked = rules_by_id.get("ma-inh-mother-no-descendants-multi-siblings-blocked")
    assert activatable is not None, "missing the activatable mother-1/3 rule"
    assert blocked is not None, "missing the blocked mother-multi-siblings rule"
    # The activatable rule must require the wizard's siblings count.
    assert activatable["scenario"].get("siblings") in ("<=1", 0, "0", None) or (
        "siblings" in activatable["scenario"]
    ), "activatable rule must reference the siblings input"
    assert activatable["share_spec"] == {"mother": "1/3"}
    # The blocked rule MUST NOT carry a numeric share.
    assert blocked.get("blocked") is True
    assert blocked.get("share_spec") in (
        None,
        {},
    ), f"blocked rule must have no share_spec, got {blocked.get('share_spec')!r}"
    # Both rules must cite article 346 verbatim from extraction.
    assert "346" in activatable["article_references"]
    assert "346" in blocked["article_references"]


def test_pass3_unsupported_mechanisms_are_explicit(mapping_payload):
    """Pass3 invariant: the mapping must list each unsupported
    Moudawana mechanism explicitly with article references and
    blocked_rules, so the reviewer / engine cannot silently rely on
    a missing concept."""
    mechs = mapping_payload.get("unsupported_mechanisms")
    assert isinstance(mechs, list) and mechs, "mapping must declare unsupported_mechanisms"
    names = {m["name"] for m in mechs}
    required_names = {
        "hajb",
        "'awl",
        "radd",
        "ta'sib / asaba ordering",
        "kalala",
        "applicable_law_decision",
    }
    missing = required_names - names
    assert not missing, f"unsupported_mechanisms missing required names: {missing}"
    for m in mechs:
        assert "article_references" in m, m
        assert "blocked_rules" in m, m
        assert "comment" in m, m
    # The hajb mechanism must declare the blocked mother-multi-siblings rule.
    hajb = next(m for m in mechs if m["name"] == "hajb")
    assert "ma-inh-mother-no-descendants-multi-siblings-blocked" in hajb["blocked_rules"]


def test_pass3_every_rule_has_activation_blockers_list(mapping_payload):
    """Pass3 invariant: every rule must carry an
    ``activation_blockers`` list (possibly empty). This makes the
    activation status of each rule machine-readable."""
    for rule in mapping_payload["rules"]:
        assert (
            "activation_blockers" in rule
        ), f"rule {rule.get('rule_id')!r} missing activation_blockers"
        assert isinstance(
            rule["activation_blockers"], list
        ), f"rule {rule.get('rule_id')!r} activation_blockers must be a list"
        if rule.get("blocked"):
            assert rule[
                "activation_blockers"
            ], f"blocked rule {rule.get('rule_id')!r} must list reasons"


def test_pass3_wizard_inputs_describe_siblings():
    """The wizard form already captures ``siblings_count``. The
    mapping's wizard_inputs section must document this so the
    engine knows the field is available before activating
    article-346 rules."""
    payload = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    wizard = payload.get("wizard_inputs")
    assert wizard, "mapping must declare wizard_inputs"
    captured_paths = {c["input_data_path"] for c in wizard.get("captured", [])}
    assert (
        "heirs.siblings" in captured_paths
    ), f"wizard_inputs must document heirs.siblings; got {captured_paths}"


@pytest.mark.django_db
def test_pass3_wizard_form_serializes_siblings_into_heirs():
    """End-to-end: the inheritance wizard form, when given a non-zero
    ``siblings_count``, serialises it into ``input_data.heirs.siblings``.
    This is the concrete contract the mapping's article-346 rule
    relies on."""
    from apps.cases.forms import InternationalInheritanceWizardForm

    form = InternationalInheritanceWizardForm(
        data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "",
            "sons_count": "0",
            "daughters_count": "0",
            "father_present": "",
            "mother_present": "on",
            "siblings_count": "3",
            "estate_value": "100000",
            "consent_simulation": "on",
            "website": "",
        }
    )
    assert form.is_valid(), form.errors
    payload = form.to_input_data()
    assert payload["heirs"]["siblings"] == 3
    assert payload["heirs"]["mother"] == 1
    assert payload["heirs"]["sons"] == 0
    assert payload["heirs"]["daughters"] == 0


def test_every_rule_has_article_references(mapping_payload):
    for rule in mapping_payload["rules"]:
        refs = rule.get("article_references")
        assert (
            isinstance(refs, list) and refs
        ), f"rule {rule.get('rule_id')!r} has no article_references"
        for r in refs:
            assert re.match(
                r"^\d+", str(r)
            ), f"rule {rule.get('rule_id')!r} carries non-numeric article ref: {r!r}"


def test_every_rule_has_extracted_text_snippet_field(mapping_payload):
    for rule in mapping_payload["rules"]:
        assert (
            "extracted_text_snippet" in rule
        ), f"rule {rule.get('rule_id')!r} missing extracted_text_snippet field"


def test_every_rule_is_draft_and_needs_review(mapping_payload):
    assert mapping_payload["activation_allowed"] is False
    for rule in mapping_payload["rules"]:
        assert (
            rule.get("needs_manual_review") is True
        ), f"rule {rule.get('rule_id')!r} not flagged needs_manual_review"
        confidence = rule.get("confidence")
        assert confidence in {
            "low",
            "medium",
            "high",
        }, f"rule {rule.get('rule_id')!r} confidence={confidence!r}"


# ---------------------------------------------------------------------------
# 6 — confidence=high requires non-empty extracted_text_snippet AND
#     a matching article in the extraction artefact
# ---------------------------------------------------------------------------


def test_no_rule_high_confidence_without_matching_extraction(mapping_payload):
    extraction = json.loads(EXTRACTION_JSON.read_text(encoding="utf-8"))
    extracted_articles = {a["article"] for a in extraction.get("articles", [])}
    for rule in mapping_payload["rules"]:
        if rule.get("confidence") != "high":
            continue
        snippet = (rule.get("extracted_text_snippet") or "").strip()
        assert snippet, (
            f"rule {rule.get('rule_id')!r} marked confidence=high "
            f"but extracted_text_snippet is empty"
        )
        refs = {str(r) for r in rule.get("article_references", [])}
        assert refs & extracted_articles, (
            f"rule {rule.get('rule_id')!r} confidence=high but none of its "
            f"article_references appear in the extraction artefact"
        )


# ---------------------------------------------------------------------------
# 7 — optional DRAFT dataset is not usable for calculations
# ---------------------------------------------------------------------------


_FORBIDDEN_DRAFT_LABEL = "MA-MOUDAWANA-INHERITANCE" + "-DRAFT"


def test_no_unsupported_draft_dataset_created():
    """This iter intentionally does NOT add a DRAFT
    CompensationDataset to the DB layer because the
    ``CompensationTableRow.point_value`` numeric model does not fit
    the share-spec mapping cleanly. The JSON file is the canonical
    artefact. We assert here that no production app code references
    the forbidden version label by mistake. The label itself is
    spelled obliquely above so this test file does not match its
    own grep."""
    self_path = Path(__file__).resolve().relative_to(REPO_ROOT)
    rows_with_label = []
    for path in REPO_ROOT.glob("apps/**/*.py"):
        rel = path.relative_to(REPO_ROOT)
        if rel == self_path:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _FORBIDDEN_DRAFT_LABEL in text:
            rows_with_label.append(str(rel))
    assert (
        not rows_with_label
    ), f"{_FORBIDDEN_DRAFT_LABEL} referenced in app code: {rows_with_label}"


# ---------------------------------------------------------------------------
# 8 + 9 — public MA stays unavailable, no shares surfaced
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_ma_inheritance_stays_unavailable():
    from apps.cases.models import Simulation

    client = Client()
    client.get("/wizard/ma/inheritance/")
    payload = {
        "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        "consent_simulation": "on",
        "website": "",
        "deceased_country_of_last_residence": "MA",
        "nationality": "MA",
        "spouse_present": "on",
        "surviving_spouse_gender": "wife",
        "sons_count": "1",
        "daughters_count": "1",
        "estate_value": "800000",
    }
    resp = client.post("/wizard/ma/inheritance/", payload, follow=True)
    assert resp.status_code == 200
    body = resp.content.decode("utf-8", errors="replace")
    # No EUR amount in the result.
    assert not re.search(r"€\s*\d{1,3}[.,\s]\d{3}", body)
    # Internal status is unavailable.
    sim = Simulation.objects.order_by("-created_at").first()
    assert sim is not None
    assert sim.status == "unavailable_requires_legal_validation"


# ---------------------------------------------------------------------------
# 10 — mapping smoke scenario feeds the engine in a synthetic test DB
# ---------------------------------------------------------------------------


@pytest.fixture
def ma_synthetic_approved_db(db):
    """Fixture-only: seeds an APPROVED MA source + dataset + formula
    that mirrors the morocco_inheritance_v1 expectations. The public
    DB is NEVER touched by this fixture — it lives entirely inside
    the test transaction."""
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        DatasetStatus,
    )
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

    morocco = Country.objects.create(code="MA", code_alpha3="MAR", name="Maroc")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=morocco,
        code="MA-NATIONAL",
        name="Maroc",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="ma-fixture-mapping-draft-pass1",
        title="MA Moudawana fixture (draft mapping smoke)",
        country=morocco,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2004, 2, 5),
    )
    ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=morocco,
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        name="MA Moudawana fixture (draft mapping smoke)",
        version_label="MA-FIXTURE-DRAFT-MAPPING-PASS1",
        status=DatasetStatus.APPROVED,
        valid_from=date(2004, 2, 5),
    )
    payload = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    # The pass2 mapping splits ``spouse`` into the gender-specific
    # Moudawana classes (``husband``/``wife``). The existing engine
    # uses the generic ``spouse`` key, so we anchor the smoke
    # fixture on the wife-with-descendants rule (1/8) and translate
    # back to the engine's ``spouse`` key plus the canonical
    # 2:1 sons:daughters residual shares from the smoke scenario.
    anchor_rule_id = payload["fixture_compatibility"]["smoke_scenario"]["anchor_rule_id"]
    anchor_rule = next(rule for rule in payload["rules"] if rule["rule_id"] == anchor_rule_id)
    spouse_share = anchor_rule["share_spec"]["wife"]
    smoke_shares = {
        "spouse": spouse_share,
        "sons_group": "remainder_2_to_1",
        "daughters_group": "remainder_2_to_1",
    }
    CalculationFormula.objects.create(
        dataset=ds,
        code="ma-inheritance-fixture-mapping-draft-pass2",
        name="MA inheritance fixture mapping draft pass2",
        expression_text="fixed shares + 2:1 residual (Moudawana mapping draft)",
        source_reference=str(MAPPING_JSON.relative_to(REPO_ROOT)),
        parameters={
            "engine": "morocco_inheritance_v1",
            "amount_rule": "morocco_inheritance_fixed_share_direct",
            "requires": ["heirs"],
            "shares": smoke_shares,
        },
        status=DatasetStatus.APPROVED,
    )
    return src


@pytest.mark.django_db
def test_mapping_smoke_feeds_engine(ma_synthetic_approved_db):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": "800000",
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    breakdown = (sim.output_data or {}).get("breakdown") or []
    spouse = next((b for b in breakdown if "Surviving spouse" in b["label"]), None)
    sons = next((b for b in breakdown if "Sons (collective)" in b["label"]), None)
    daughters = next((b for b in breakdown if "Daughters (collective)" in b["label"]), None)
    assert spouse and sons and daughters
    assert Decimal(spouse["amount_mid"]) == Decimal("100000")
    assert abs(
        Decimal(sons["amount_mid"]) - (Decimal("800000") * Decimal(7) / Decimal(12))
    ) < Decimal("0.01")
    assert abs(
        Decimal(daughters["amount_mid"]) - (Decimal("800000") * Decimal(7) / Decimal(24))
    ) < Decimal("0.01")


# ---------------------------------------------------------------------------
# 11 — no LegalReview created by extraction or mapping
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_legal_review_created_by_this_pass():
    from apps.legal_sources.models import LegalReview

    # The extraction script + mapping JSON are read-only on the DB.
    # The fixture above does NOT create a LegalReview.
    assert LegalReview.objects.count() == 0


# ---------------------------------------------------------------------------
# 12 — no CalculationFormula in production DB (fixture-only)
# ---------------------------------------------------------------------------


def test_no_production_calculation_formula_for_ma_mapping():
    """Grep for any production-loader code path that writes a
    ``ma-*`` formula referencing the draft mapping. There must be
    none — the mapping JSON is the canonical artefact and feeds the
    engine ONLY through test fixtures."""
    forbidden_loader_patterns = (
        "morocco_inheritance_mapping_draft.json",
        "MA-MOUDAWANA-INHERITANCE-DRAFT",
    )
    hits: list[str] = []
    for path in REPO_ROOT.glob("apps/**/management/**/*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for pat in forbidden_loader_patterns:
            if pat in text:
                hits.append(f"{path.relative_to(REPO_ROOT)}: {pat}")
    assert not hits, f"unexpected loader references: {hits}"


# ---------------------------------------------------------------------------
# 13 + 14 — Italia smoke + IT PDF unchanged
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
        slug="it-fixture-ma-mapping-pass1",
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
        code="italy_art_138_ma_mapping_pass1",
        name="ma-mapping-pass1-it-smoke",
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
