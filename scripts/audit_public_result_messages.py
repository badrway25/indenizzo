"""Audit the public wizard-result page for technical-message leaks.

Iter: ``F-inheritance-wizard-result-page-localization-pass1``.

Drives a real wizard submission for FR / BE / MA / TN against a
running server (default ``http://127.0.0.1:48107``), follows the
redirect to the result page, and asserts that the rendered body does
**not** surface any backend diagnostic strings that should stay
internal — slug-style status codes, raw warning sentences, or
internal field names that crept in through a template glitch.

Read-only on the public surface: the only writes the script does are
the wizard POSTs themselves, which the project already considers
public submission (and which run the calculator gating chain
end-to-end). No DB tables are seeded or promoted.

Exits 0 if every fixture page is clean, 1 otherwise. Writes a JSON
report to ``docs/reports/result_message_audit/`` for traceability.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:48107"
DEFAULT_REPORT_DIR = REPO_ROOT / "docs" / "reports" / "result_message_audit"

# Phrases / slugs that must NEVER reach the public result page.
BANNED_SUBSTRINGS = (
    "unavailable_requires_legal_validation",
    "No approved legal sources are available",
    "missing_documents",
    "compensation_dataset_approved",
    "calculation_formula_approved",
    "calculator_engine_pending_for_jurisdiction",
    "formula_engine_unknown",
    "formula_amount_rule_unknown",
    "formula_amount_rule_not_inheritance_share",
    "formula_amount_rule_not_single_row_range",
    "formula_row_type_missing",
    "compensation_row_match",
    "compensation_row_disambiguation",
    "compensation_range_inconsistent",
    "shares_spec_invalid",
    "source unavailable",
    "legal_sources_approved",
    "Approved legal sources are present",
    "Approved formula declares amount_rule",
    "An approved formula exists",
    "An approved formula is present",
)

# Fixtures: (label, locale_prefix, wizard_path, payload).
FIXTURES = [
    (
        "fr_road_accident_unavailable",
        "",
        "/wizard/fr/road-accident/",
        {
            "victim_age": "30",
            "permanent_disability_percentage": "5",
            "fault_percentage": "0",
        },
    ),
    (
        "be_road_accident_unavailable",
        "",
        "/wizard/be/road-accident/",
        {
            "victim_age": "30",
            "permanent_disability_percentage": "5",
            "fault_percentage": "0",
        },
    ),
    (
        "ma_inheritance_unavailable",
        "",
        "/wizard/ma/inheritance/",
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "estate_value": "800000",
        },
    ),
    (
        "tn_inheritance_unavailable",
        "",
        "/wizard/tn/inheritance/",
        {
            "deceased_country_of_last_residence": "TN",
            "nationality": "TN",
            "spouse_present": "on",
            "mother_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "estate_value": "1200000",
        },
    ),
    (
        "fr_road_accident_unavailable_FR",
        "/fr",
        "/wizard/fr/road-accident/",
        {
            "victim_age": "30",
            "permanent_disability_percentage": "5",
            "fault_percentage": "0",
        },
    ),
    (
        "ma_inheritance_unavailable_AR",
        "/ar",
        "/wizard/ma/inheritance/",
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "estate_value": "800000",
        },
    ),
]


def _csrf_from(html: str) -> str | None:
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    return m.group(1) if m else None


def _fetch_get(url: str, cookies: dict[str, str]) -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(url)
    if cookies:
        req.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()))
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            new_cookies = dict(cookies)
            for header in resp.getheader("Set-Cookie", "").split(", "):
                if "=" in header:
                    name, _, rest = header.partition("=")
                    value = rest.split(";")[0]
                    new_cookies[name.strip()] = value
            return resp.status, body, new_cookies
    except urllib.error.HTTPError as exc:
        return exc.code, "", cookies


def _fetch_post(
    url: str,
    payload: dict[str, str],
    cookies: dict[str, str],
    referer: str,
) -> tuple[int, str, str]:
    body = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Referer", referer)
    if cookies:
        req.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()))
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return resp.status, text, resp.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, "", url


def audit_fixture(base_url: str, label: str, locale_prefix: str, path: str, payload: dict) -> dict:
    wizard_url = base_url + locale_prefix + path
    status_get, html_get, cookies = _fetch_get(wizard_url, {})
    if status_get != 200:
        return {"label": label, "passed": False, "error": f"GET {wizard_url} -> {status_get}"}
    csrf = _csrf_from(html_get)
    if not csrf:
        return {"label": label, "passed": False, "error": f"no CSRF on {wizard_url}"}
    full_payload = {
        "csrfmiddlewaretoken": csrf,
        "consent_simulation": "on",
        "website": "",
        **payload,
    }
    status_post, body_post, final_url = _fetch_post(
        wizard_url, full_payload, cookies, referer=wizard_url
    )
    if status_post != 200:
        return {"label": label, "passed": False, "error": f"POST -> {status_post}"}
    leaks = [needle for needle in BANNED_SUBSTRINGS if needle in body_post]
    return {
        "label": label,
        "wizard_url": wizard_url,
        "result_url": final_url,
        "passed": not leaks,
        "leaks": leaks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--out-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {"base_url": base_url, "fixtures": []}
    failures = 0
    for label, locale_prefix, path, payload in FIXTURES:
        result = audit_fixture(base_url, label, locale_prefix, path, dict(payload))
        if not result["passed"]:
            failures += 1
            details = result.get("leaks") or result.get("error", "?")
            print(f"[FAIL] {label}: {details}", file=sys.stderr)
        else:
            print(f"[ok]   {label} -> {result['result_url']}")
        report["fixtures"].append(result)

    out_path = out_dir / "audit.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[report] {out_path}")
    if failures:
        print(f"[verdict] {failures} fixtures leaked technical strings", file=sys.stderr)
        return 1
    print("[verdict] OK — every fixture stays free of technical strings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
