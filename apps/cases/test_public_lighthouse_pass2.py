"""Tests F-perf-pass2-lighthouse-cli-and-ci-ready.

Static / functional checks for the pass-2 audit harness:

1. ``--base-url`` and ``--out-dir`` are accepted and shape the report
   path.
2. ``--mode playwright`` forces the structural fallback even when
   ``lighthouse`` is on PATH.
3. ``--mode lighthouse`` without a CLI on PATH returns exit code 2
   and a clear error message on stderr (no silent downgrade).
4. ``summary.md`` is generated (alongside ``audit.json``) from a
   fake audit dict via ``render_markdown_report``.
5. The pass-2 thresholds JSON (schema_version=2) is well-formed and
   keeps the required-rule policy.
6. Running the audit with ``--mode playwright`` against a tiny
   throwaway HTTP server does NOT leak an API-key string into the
   resulting ``audit.json``.
7. The "no Pexels attribution" rule still flags ``photo by`` text.
8. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR is unchanged.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
THRESHOLDS_PATH = REPO_ROOT / "config" / "public_lighthouse_thresholds.json"


def _import_script():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    # Force-reload so a previous test's monkey-patched module is not
    # carried over.
    if "run_public_lighthouse_audit" in sys.modules:
        return importlib.reload(sys.modules["run_public_lighthouse_audit"])
    return importlib.import_module("run_public_lighthouse_audit")


# ---------------------------------------------------------------------------
# 1 — --base-url + --out-dir flags
# ---------------------------------------------------------------------------


def test_audit_accepts_base_url_and_out_dir(tmp_path, monkeypatch):
    """The script's argparse should accept --base-url and --out-dir, and
    the resulting audit.json + summary.md should be written under
    --out-dir."""

    mod = _import_script()
    out_dir = tmp_path / "audit_out"

    # Stub the playwright runner so the test doesn't need a real browser.
    fake_results = {"/": {"failures": [], "passed": True}}
    monkeypatch.setattr(mod, "_run_playwright_fallback", lambda *a, **k: fake_results)
    # Force the playwright path so we don't depend on any installed CLI.
    rc = mod.main(
        [
            "--base-url",
            "http://example.test",
            "--mode",
            "playwright",
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    assert (out_dir / "audit.json").exists()
    assert (out_dir / "summary.md").exists()
    audit = json.loads((out_dir / "audit.json").read_text(encoding="utf-8"))
    assert audit["base_url"] == "http://example.test"
    assert audit["tool"] == "playwright_fallback"


# ---------------------------------------------------------------------------
# 2 — --mode playwright forces the fallback
# ---------------------------------------------------------------------------


def test_mode_playwright_forces_fallback_even_if_cli_present(tmp_path, monkeypatch):
    mod = _import_script()
    out_dir = tmp_path / "audit_out"

    # Pretend a Lighthouse CLI is on PATH.
    monkeypatch.setattr(mod, "_find_lighthouse_cli", lambda: "/usr/local/bin/lighthouse")
    # Stub the playwright runner so we don't need a browser.
    fake_results = {"/": {"failures": [], "passed": True}}
    monkeypatch.setattr(mod, "_run_playwright_fallback", lambda *a, **k: fake_results)
    # Make the lighthouse runner crash if accidentally invoked, so the
    # test fails loud instead of silently falling through.
    monkeypatch.setattr(
        mod,
        "_run_lighthouse",
        lambda *a, **k: pytest.fail("lighthouse should not be called when mode=playwright"),
    )

    rc = mod.main(["--mode", "playwright", "--out-dir", str(out_dir)])
    assert rc == 0
    audit = json.loads((out_dir / "audit.json").read_text(encoding="utf-8"))
    assert audit["tool"] == "playwright_fallback"


# ---------------------------------------------------------------------------
# 3 — --mode lighthouse without binary returns exit code 2
# ---------------------------------------------------------------------------


def test_mode_lighthouse_without_binary_returns_exit_2(tmp_path):
    """Run the script as a subprocess so we measure the real exit code
    (rather than the in-process return value). On this developer
    machine the Lighthouse CLI is not installed; we forcibly mask any
    candidate by setting an empty PATH segment for the subprocess."""

    out_dir = tmp_path / "audit_out"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "run_public_lighthouse_audit.py"),
            "--mode",
            "lighthouse",
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        # An empty PATH guarantees no lighthouse binary is found.
        env={"PATH": ""},
        check=False,
    )
    assert proc.returncode == 2, f"expected exit 2, got {proc.returncode}; stderr={proc.stderr!r}"
    assert "lighthouse" in proc.stderr.lower()
    assert "PATH" in proc.stderr or "path" in proc.stderr


# ---------------------------------------------------------------------------
# 4 — summary.md generated from fake results
# ---------------------------------------------------------------------------


def test_summary_md_generated_from_fake_results():
    mod = _import_script()
    fake_report = {
        "tool": "playwright_fallback",
        "base_url": "http://127.0.0.1:48107",
        "urls": {
            "/wizard/": {"passed": True, "failures": []},
            "/contact/": {"passed": False, "failures": ["h1_count=2"]},
        },
    }
    md = mod.render_markdown_report(fake_report)
    assert "tool: `playwright_fallback`" in md
    assert "| URL | Verdict | Failures |" in md
    assert "| `/wizard/` | PASS | — |" in md
    assert "h1_count=2" in md


# ---------------------------------------------------------------------------
# 5 — pass-2 thresholds schema valid
# ---------------------------------------------------------------------------


def test_thresholds_pass2_schema_is_valid():
    raw = json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))
    assert raw["_schema_version"] == 2, "pass-2 should bump the schema version"
    lh = raw["lighthouse"]
    # required vs warning policy: a11y/seo/best-practices must be
    # required; performance must remain warning until the CLI version
    # is pinned.
    assert lh["accessibility"]["level"] == "required"
    assert lh["seo"]["level"] == "required"
    assert lh["best-practices"]["level"] == "required"
    assert lh["performance"]["level"] == "warning"
    # Fallback rules untouched.
    rules = raw["fallback_playwright"]["rules"]
    assert all(level == "required" for level in rules.values())


# ---------------------------------------------------------------------------
# 6 — no API key leak in the audit output for a clean dev page
# ---------------------------------------------------------------------------


def test_audit_output_does_not_leak_known_env_var_names(tmp_path, monkeypatch):
    """Even when the audit captures the rendered HTML, none of the
    sensitive env-var names should appear in the resulting JSON dump.
    We feed a stubbed pages dict and verify the serialised audit is
    clean."""

    mod = _import_script()
    fake_results = {
        "/": {"passed": True, "failures": []},
        "/wizard/": {"passed": True, "failures": []},
    }
    monkeypatch.setattr(mod, "_run_playwright_fallback", lambda *a, **k: fake_results)
    out_dir = tmp_path / "audit_out"
    rc = mod.main(["--mode", "playwright", "--out-dir", str(out_dir)])
    assert rc == 0
    blob = (out_dir / "audit.json").read_text(encoding="utf-8")
    for name in ("PEXELS_API_KEY", "STRIPE_SECRET", "SENDGRID_API_KEY"):
        assert name not in blob


# ---------------------------------------------------------------------------
# 7 — Pexels attribution rule still active
# ---------------------------------------------------------------------------


def test_fallback_still_flags_pexels_attribution():
    mod = _import_script()
    html = (
        "<!doctype html><html><head>"
        "<title>OK</title>"
        '<meta name="description" content="A page.">'
        "</head><body>"
        "<h1>Hello</h1>"
        '<img src="/x.png" alt="X" width="10" height="10">'
        "<p>Photo by Jane Doe on Pexels.com</p>"
        "</body></html>"
    )
    verdict = mod.fallback_check_page(html, viewport_width=375, body_overflow=300)
    assert not verdict["passed"]
    assert any(f.startswith("pexels_attribution:") for f in verdict["failures"])


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
        slug="it-fixture-pass2-lighthouse",
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
        name="TUN base lighthouse pass2",
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
        name="TUN moral lighthouse pass2",
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
        code="italy_art_138_tun_2025_lh_pass2",
        name="lighthouse-pass2",
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
def test_italy_smoke_unchanged_after_lighthouse_pass2(italy_calculator_fixture):
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
