"""Tests F-product-lighthouse-visual-qa-pass1.

Static + functional checks for the public-funnel audit harness:

1. ``config/public_lighthouse_thresholds.json`` parses and exposes the
   expected schema.
2. ``scripts/run_public_lighthouse_audit.py`` is importable as a
   module (no syntax error, no top-level side effects).
3. ``render_markdown_report`` produces a markdown URL table from a
   fake report.
4. ``fallback_check_page`` flags a page that is missing its ``<h1>``.
5. ``fallback_check_page`` flags a page where an ``<img>`` lacks
   ``alt``.
6. ``fallback_check_page`` flags a page that surfaces a Pexels
   "Photo by …" attribution.
7. ``fallback_check_page`` flags a page that leaks an env var name.
8. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR is unchanged.
"""

from __future__ import annotations

import importlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS_PATH = REPO_ROOT / "config" / "public_lighthouse_thresholds.json"


# ---------------------------------------------------------------------------
# 1 — thresholds JSON shape
# ---------------------------------------------------------------------------


def test_thresholds_json_is_valid_and_well_formed():
    raw = json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))
    # Schema is forward-compatible: pass-1 only checks the floor (>= 1).
    # Pass-2 bumped to 2 — that bump is asserted by the pass-2 test
    # ``test_thresholds_pass2_schema_is_valid``.
    assert raw["_schema_version"] >= 1
    lh = raw["lighthouse"]
    for key in ("performance", "accessibility", "best-practices", "seo"):
        assert key in lh, f"missing lighthouse threshold: {key}"
        assert 0.0 <= lh[key]["min"] <= 1.0
        assert lh[key]["level"] in {"required", "warning"}
    fallback_rules = raw["fallback_playwright"]["rules"]
    for required in (
        "http_status_200",
        "title_present",
        "meta_description_present",
        "exactly_one_h1",
        "no_horizontal_overflow_mobile",
        "all_images_have_alt",
        "all_images_have_dimensions",
        "no_pexels_attribution",
        "no_api_key_leak",
    ):
        assert (
            fallback_rules.get(required) == "required"
        ), f"fallback rule {required!r} should be required"
    urls = raw["audited_urls"]
    assert "/" in urls and "/wizard/" in urls
    assert len(urls) == 8


# ---------------------------------------------------------------------------
# 2 — script is importable
# ---------------------------------------------------------------------------


def _import_script():
    """Helper: import scripts/run_public_lighthouse_audit.py as a module."""

    import sys

    scripts_dir = REPO_ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    return importlib.import_module("run_public_lighthouse_audit")


def test_audit_script_is_importable():
    mod = _import_script()
    assert callable(mod.main)
    assert callable(mod.fallback_check_page)
    assert callable(mod.render_markdown_report)


# ---------------------------------------------------------------------------
# 3 — markdown report generator
# ---------------------------------------------------------------------------


def test_render_markdown_report_lighthouse_shape():
    mod = _import_script()
    report = {
        "tool": "lighthouse",
        "base_url": "http://127.0.0.1:48107",
        "urls": {
            "/": {
                "performance": 0.92,
                "accessibility": 0.97,
                "best-practices": 1.00,
                "seo": 0.91,
                "passed": True,
            },
            "/wizard/": {
                "performance": 0.65,
                "accessibility": 0.95,
                "best-practices": 0.93,
                "seo": 0.92,
                "passed": False,
            },
        },
    }
    md = mod.render_markdown_report(report)
    assert "# Public funnel audit" in md
    assert "| URL | perf | a11y | best-pract. | SEO | Verdict |" in md
    assert "| `/` |" in md
    assert "0.92" in md
    assert "PASS" in md and "FAIL" in md


def test_render_markdown_report_fallback_shape():
    mod = _import_script()
    report = {
        "tool": "playwright_fallback",
        "base_url": "http://127.0.0.1:48107",
        "urls": {
            "/wizard/": {"passed": True, "failures": []},
            "/contact/": {"passed": False, "failures": ["h1_count=2"]},
        },
    }
    md = mod.render_markdown_report(report)
    assert "tool: `playwright_fallback`" in md
    assert "| URL | Verdict | Failures |" in md
    assert "h1_count=2" in md


# ---------------------------------------------------------------------------
# 4–7 — fallback_check_page rules
# ---------------------------------------------------------------------------


def _ok_page() -> str:
    """A minimal HTML body that satisfies all fallback rules."""

    return (
        "<!doctype html><html><head>"
        "<title>OK</title>"
        '<meta name="description" content="A page.">'
        "</head><body>"
        "<h1>Hello</h1>"
        '<img src="/x.png" alt="X" width="10" height="10">'
        "</body></html>"
    )


def test_fallback_detects_missing_h1():
    mod = _import_script()
    html = _ok_page().replace("<h1>Hello</h1>", "")
    verdict = mod.fallback_check_page(html, viewport_width=375, body_overflow=300)
    assert not verdict["passed"]
    assert any(f.startswith("h1_count=") for f in verdict["failures"])


def test_fallback_detects_missing_alt():
    mod = _import_script()
    html = _ok_page().replace('alt="X" ', "")
    verdict = mod.fallback_check_page(html, viewport_width=375, body_overflow=300)
    assert not verdict["passed"]
    assert "img_missing_alt" in verdict["failures"]


def test_fallback_detects_pexels_attribution():
    mod = _import_script()
    html = _ok_page().replace("<h1>Hello</h1>", "<h1>Hello</h1><p>Photo by Jane Doe</p>")
    verdict = mod.fallback_check_page(html, viewport_width=375, body_overflow=300)
    assert not verdict["passed"]
    assert any(f.startswith("pexels_attribution:") for f in verdict["failures"])


def test_fallback_detects_api_key_leak():
    mod = _import_script()
    html = _ok_page().replace(
        "<h1>Hello</h1>",
        "<h1>Hello</h1><p>PEXELS_API_KEY=abc</p>",
    )
    verdict = mod.fallback_check_page(html, viewport_width=375, body_overflow=300)
    assert not verdict["passed"]
    assert any(f.startswith("env_var_leak:PEXELS_API_KEY") for f in verdict["failures"])


def test_fallback_detects_horizontal_overflow():
    mod = _import_script()
    verdict = mod.fallback_check_page(_ok_page(), viewport_width=375, body_overflow=500)
    assert not verdict["passed"]
    assert any(f.startswith("horizontal_overflow:") for f in verdict["failures"])


def test_fallback_passes_a_clean_page():
    mod = _import_script()
    verdict = mod.fallback_check_page(_ok_page(), viewport_width=375, body_overflow=300)
    assert verdict["passed"], verdict["failures"]


# ---------------------------------------------------------------------------
# 8 — Italia smoke unchanged
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_calculator_fixture(db):
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-fixture-pass1-lighthouse",
        title="D.P.R. 12/2025 fixture",
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
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base lighthouse",
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
        name="TUN moral lighthouse",
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
        code="italy_art_138_tun_2025_lighthouse",
        name="lighthouse-pass1",
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
    return italy


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_lighthouse_pass1(italy_calculator_fixture):
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
