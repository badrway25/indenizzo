#!/usr/bin/env python3
"""Lighthouse report verdict guard (H1-10.1).

Classifies a single Lighthouse JSON report so the runner can tell a *corrupted
metric-zero* collection (retry it once) apart from a *real* budget miss (let the
gate fail) and from *no report at all* (the H1-10 Chrome/artifact case).

Stdlib only, PII-safe (reads scores/audit status, never page content), and
testable with tiny synthetic fixtures via :func:`classify_report`.

Verdicts (printed to stdout, one word):

- ``retry``   — performance score is 0/None while the core performance-metric
  audits are errored/missing AND at least one other category is healthy. That is
  a corrupt trace (the page loaded — a11y/seo measured fine — but the perf
  metrics could not be computed), not a real 0% performance. Re-collect once.
- ``accept``  — any other usable report: a normal score, OR a genuine low/zero
  performance whose audits WERE computed. The single-shot gate judges it (and
  fails it if it is below budget). Never retried.
- ``invalid`` — file missing / not JSON / no ``categories``. Same handling as the
  H1-10 "no valid JSON" path.

The retry condition is deliberately conservative: a real performance regression
is a *plausible* non-zero score (e.g. 0.40) with computed audits, never an exact
0.00 with errored perf metrics while accessibility/SEO stayed high.
"""

from __future__ import annotations

import json
import sys

# Core performance-metric audits. If these are all errored/missing the
# performance trace is corrupt, not merely "slow".
_PERF_METRIC_AUDITS = (
    "first-contentful-paint",
    "largest-contentful-paint",
    "speed-index",
    "total-blocking-time",
    "cumulative-layout-shift",
)
_OTHER_CATEGORIES = ("accessibility", "best-practices", "seo")
_HEALTHY = 0.5  # an "other" category counts as healthy (page loaded) at >= 0.5


def _cat_score(report: dict, name: str):
    cat = (report.get("categories") or {}).get(name) or {}
    return cat.get("score")


def _audit_is_errored_or_missing(audits: dict, key: str) -> bool:
    a = audits.get(key)
    if a is None:
        return True
    # numericValue / score absent, or an explicit error display mode.
    if a.get("errorMessage"):
        return True
    if a.get("scoreDisplayMode") == "error":
        return True
    # No score AND no numericValue → the metric was not computed.
    return a.get("score") is None and a.get("numericValue") is None


def classify_report(report: dict, perf_floor: float = 0.80) -> str:
    """Return ``"retry"`` / ``"accept"`` / ``"invalid"`` for a report dict."""
    if not isinstance(report, dict) or not report.get("categories"):
        return "invalid"

    perf = _cat_score(report, "performance")
    # A non-zero performance score (good or bad) is a genuine measurement.
    if perf not in (None, 0):
        return "accept"

    # perf is 0 or None: decide corrupt-trace vs genuine-zero.
    audits = report.get("audits") or {}
    errored = sum(1 for k in _PERF_METRIC_AUDITS if _audit_is_errored_or_missing(audits, k))
    others = [_cat_score(report, c) for c in _OTHER_CATEGORIES]
    others_healthy = any(s is not None and s >= _HEALTHY for s in others)

    # Corrupt trace: most perf metrics not computed, yet the page clearly loaded
    # (another category measured healthy). Re-collect once.
    if errored >= 3 and others_healthy:
        return "retry"
    # Otherwise the zero is real (audits were computed, or the page is broken
    # across the board). Let the gate fail honestly — never retry.
    return "accept"


def classify_path(path: str, perf_floor: float = 0.80) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            report = json.load(fh)
    except (OSError, ValueError):
        return "invalid"
    return classify_report(report, perf_floor=perf_floor)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("invalid")
        return 0
    floor = float(argv[2]) if len(argv) > 2 else 0.80
    print(classify_path(argv[1], perf_floor=floor))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
