"""H1-10.1: tests for the Lighthouse metric-zero retry guard.

Pure unit tests with tiny synthetic Lighthouse JSON — no Chrome, no real
artifacts. They lock the conservative discriminator: retry ONLY a corrupted
metric-zero report, never a real budget miss.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.lighthouse_score_guard import classify_path, classify_report

# Reusable healthy "other" categories (page clearly loaded).
_HEALTHY_OTHERS = {
    "accessibility": {"score": 0.96},
    "best-practices": {"score": 1.0},
    "seo": {"score": 1.0},
}
_COMPUTED_PERF_AUDITS = {
    "first-contentful-paint": {"score": 0.2, "numericValue": 4200},
    "largest-contentful-paint": {"score": 0.1, "numericValue": 9000},
    "speed-index": {"score": 0.3, "numericValue": 7000},
    "total-blocking-time": {"score": 0.0, "numericValue": 1200},
    "cumulative-layout-shift": {"score": 0.4, "numericValue": 0.2},
}
_ERRORED_PERF_AUDITS = {
    "first-contentful-paint": {"score": None, "scoreDisplayMode": "error", "errorMessage": "x"},
    "largest-contentful-paint": {"score": None, "scoreDisplayMode": "error"},
    "speed-index": {"score": None},
    "total-blocking-time": {"score": None},
    "cumulative-layout-shift": {"score": None},
}


def _report(perf, *, others=None, audits=None):
    cats = {"performance": ({} if perf is None else {"score": perf})}
    if perf is not None:
        cats["performance"] = {"score": perf}
    cats.update(others if others is not None else _HEALTHY_OTHERS)
    return {"categories": cats, "audits": audits or {}}


def test_healthy_report_is_accepted():
    assert classify_report(_report(0.96, audits=_COMPUTED_PERF_AUDITS)) == "accept"


def test_corrupt_metric_zero_is_retried():
    # perf=0.00, other categories high, perf audits errored/missing → corrupt trace
    assert classify_report(_report(0.0, audits=_ERRORED_PERF_AUDITS)) == "retry"


def test_perf_none_with_errored_audits_is_retried():
    assert classify_report(_report(None, audits=_ERRORED_PERF_AUDITS)) == "retry"


def test_real_low_perf_is_not_retried():
    # plausible non-zero low score → real budget miss, gate must fail (accept)
    assert classify_report(_report(0.40, audits=_COMPUTED_PERF_AUDITS)) == "accept"


def test_genuine_zero_with_computed_audits_is_not_retried():
    # perf=0 but the metrics WERE computed (genuinely terrible) → not a flake
    assert classify_report(_report(0.0, audits=_COMPUTED_PERF_AUDITS)) == "accept"


def test_low_other_category_is_not_treated_as_flake():
    # perf fine, a11y low → real a11y failure, gate must fail (accept, no retry)
    others = {
        "accessibility": {"score": 0.40},
        "best-practices": {"score": 1.0},
        "seo": {"score": 1.0},
    }
    assert classify_report(_report(0.95, others=others)) == "accept"


def test_perf_zero_but_page_broken_everywhere_is_not_retried():
    # perf=0 AND all other categories low → page genuinely broken, not a flake
    others = {
        "accessibility": {"score": 0.1},
        "best-practices": {"score": 0.2},
        "seo": {"score": 0.0},
    }
    assert classify_report(_report(0.0, others=others, audits=_ERRORED_PERF_AUDITS)) == "accept"


def test_missing_categories_is_invalid():
    assert classify_report({}) == "invalid"
    assert classify_report({"audits": {}}) == "invalid"


def test_classify_path_missing_file_is_invalid(tmp_path):
    assert classify_path(str(tmp_path / "nope.json")) == "invalid"


def test_classify_path_reads_corrupt_report(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps(_report(0.0, audits=_ERRORED_PERF_AUDITS)), encoding="utf-8")
    assert classify_path(str(p)) == "retry"


def test_classify_path_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert classify_path(str(p)) == "invalid"


def test_guard_script_file_exists():
    assert (Path(__file__).resolve().parents[2] / "scripts" / "lighthouse_score_guard.py").is_file()


@pytest.mark.parametrize("perf", [0.81, 0.90, 1.0])
def test_passing_perf_scores_accepted(perf):
    assert classify_report(_report(perf, audits=_COMPUTED_PERF_AUDITS)) == "accept"


@pytest.mark.parametrize(
    "script",
    ["scripts/run_lighthouse_local.sh", "scripts/run_lighthouse_mobile_local.sh"],
)
def test_runners_wire_the_guard_and_keep_gate_single_shot(script):
    """The runners must call the guard, retry on its 'retry' verdict, let a
    persistent corrupt report fall through to the gate, and keep the score gate
    single-shot (so a real budget miss still fails)."""
    text = (Path(__file__).resolve().parents[2] / script).read_text(encoding="utf-8")
    assert "lighthouse_score_guard.py" in text
    assert "verdict" in text and '= "accept"' in text and '= "retry"' in text
    # persistent corrupt report is judged by the gate, not silently aborted
    assert "letting the gate judge it" in text
    # the score gate stays single-shot (one global_failed assignment)
    assert text.count("global_failed=1") == 1
    # never made non-blocking
    assert "continue-on-error" not in text
