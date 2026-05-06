"""Product release-readiness audit — F-product-release-readiness-audit-pass1.

Drives a running dev server and verifies the public surface is ready
to ship: every principal page returns 200, the local CSS bundle is
linked, no Tailwind CDN remains, no banned words leak, single ``<h1>``
on the principal pages, every page exposes ``<title>`` and
``<meta name="description">``, the IT wizard still calculates
35/10/0, the IT PDF still serves ``%PDF``, and the FR/BE/MA/TN
wizards still resolve to the ``unavailable_requires_legal_validation``
status without leaking technical diagnostics or surfacing amounts.

Read-only on the public surface. The wizard POSTs run the calculator
gating chain end-to-end but do not seed or promote any
``LegalSource`` / ``CompensationDataset`` / ``CalculationFormula``
/ ``CompensationTableRow`` rows — counts are snapshot before & after
to enforce the invariant.

Outputs:

* ``docs/reports/release_readiness/audit_report.md`` — machine-
  generated companion to the curated architecture doc.
* ``docs/reports/release_readiness/audit.json``

The hand-curated visual-QA notes live in
``docs/architecture/PRODUCT_RELEASE_READINESS_AUDIT_PASS1.md``;
the audit script never overwrites that file.

Exit codes:

* ``0`` — every required check passes.
* ``1`` — at least one required check failed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:48107"
DEFAULT_REPORT_MD = REPO_ROOT / "docs" / "reports" / "release_readiness" / "audit_report.md"
DEFAULT_REPORT_JSON = REPO_ROOT / "docs" / "reports" / "release_readiness" / "audit.json"

LOCAL_CSS_HREF = "/static/css/site.css"
TAILWIND_CDN_NEEDLES = (
    "cdn.tailwindcss.com",
    "https://cdn.tailwind",
    "tailwindcss-cdn",
)

PRINCIPAL_PATHS = [
    "/",
    "/countries/",
    "/countries/italy/",
    "/countries/france/",
    "/countries/belgium/",
    "/countries/morocco/",
    "/countries/tunisia/",
    "/case-types/",
    "/methodology/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/contact/",
    "/contact/thank-you/",
    "/privacy/",
    "/disclaimer/",
    "/sitemap.xml",
    "/healthz/",
]

LOCALE_PREFIXES = {"it": "", "fr": "/fr", "ar": "/ar", "en": "/en"}

# Pages where exactly one ``<h1>`` is required.
H1_PATHS = {
    "/",
    "/countries/",
    "/countries/italy/",
    "/countries/france/",
    "/countries/belgium/",
    "/countries/morocco/",
    "/countries/tunisia/",
    "/case-types/",
    "/methodology/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/contact/",
    "/contact/thank-you/",
    "/privacy/",
    "/disclaimer/",
}

# Pages required to expose <title> + <meta name="description">.
META_PATHS = H1_PATHS

BANNED_PUBLIC_WORDS = (
    "scaffold",
    "placeholder",
    "under validation",
    "in preparation",
    "coming soon",
    "work in progress",
    "modulo non operativo",
    "legal validation wizard",
    "module pending",
    "engine pending",
    "missing_documents",
    "unavailable_requires_legal_validation",
    "compensation_dataset_approved",
    "calculation_formula_approved",
    "calculator_engine_pending_for_jurisdiction",
    "formula_engine_unknown",
    "formula_amount_rule_unknown",
)

PEXELS_NEEDLES = ("photo by ", "pexels.com")
LEAK_NAMES = ("PEXELS_API_KEY", "STRIPE_SECRET", "SENDGRID_API_KEY")
LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9]{40,}")
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_OR_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
WS_RE = re.compile(r"\s+")
HIGH_PRIORITY_EN_PHRASES = (
    "How it works",
    "What this means",
    "Next steps",
    "Useful pages",
    "Request legal review",
    "Submit for legal review",
    "no automatic estimate",
    "No automatic estimate",
)

# IT wizard payload — the canonical 35/10/0 → 26 268 / 27 353 / 28 439 EUR.
IT_BASELINE_PAYLOAD = {
    "victim_age": "35",
    "permanent_disability_percentage": "10",
    "fault_percentage": "0",
    "consent_simulation": "on",
    "website": "",
}
IT_BASELINE_AMOUNTS = ("26268", "27353", "28439")

UNAVAILABLE_FIXTURES = [
    (
        "fr_road_accident",
        "/wizard/fr/road-accident/",
        {
            "victim_age": "30",
            "permanent_disability_percentage": "5",
            "fault_percentage": "0",
        },
    ),
    (
        "be_road_accident",
        "/wizard/be/road-accident/",
        {
            "victim_age": "30",
            "permanent_disability_percentage": "5",
            "fault_percentage": "0",
        },
    ),
    (
        "ma_inheritance",
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
        "tn_inheritance",
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
]

TECHNICAL_DIAGNOSTIC_NEEDLES = (
    "unavailable_requires_legal_validation",
    "missing_documents",
    "compensation_dataset_approved",
    "calculation_formula_approved",
    "calculator_engine_pending_for_jurisdiction",
    "formula_engine_unknown",
    "formula_amount_rule_unknown",
)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get(url: str, cookies: dict[str, str] | None = None) -> tuple[int, str, dict[str, str]]:
    cookies = dict(cookies or {})
    req = urllib.request.Request(url)
    if cookies:
        req.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()))
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            for header in resp.getheader("Set-Cookie", "").split(", "):
                if "=" in header:
                    name, _, rest = header.partition("=")
                    cookies[name.strip()] = rest.split(";")[0]
            return resp.status, body, cookies
    except urllib.error.HTTPError as exc:
        return exc.code, "", cookies
    except urllib.error.URLError as exc:  # noqa: BLE001
        print(f"  ! could not fetch {url}: {exc}", file=sys.stderr)
        return 0, "", cookies


def _post(
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
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return resp.status, text, resp.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, "", url


def _csrf(html: str) -> str | None:
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    return m.group(1) if m else None


def _visible_text(html: str) -> str:
    cleaned = SCRIPT_OR_STYLE_RE.sub(" ", html)
    return WS_RE.sub(" ", TAG_RE.sub(" ", cleaned)).strip()


# ---------------------------------------------------------------------------
# Page-level checks
# ---------------------------------------------------------------------------


def _check_page(*, locale: str, path: str, html: str, status: int) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {
        "http": [],
        "css_local": [],
        "tailwind_cdn": [],
        "banned_words": [],
        "en_fallback": [],
        "h1": [],
        "meta": [],
        "pexels": [],
        "api_key_leak": [],
    }
    if status != 200:
        issues["http"].append(f"http_status={status}")
        return issues
    if not html:
        issues["http"].append("empty_body")
        return issues

    if not path.endswith(".xml") and not path.startswith("/healthz"):
        if LOCAL_CSS_HREF not in html:
            issues["css_local"].append("missing_local_css_link")
        for needle in TAILWIND_CDN_NEEDLES:
            if needle in html:
                issues["tailwind_cdn"].append(needle)

    visible = _visible_text(html)
    visible_lower = visible.lower()
    for word in BANNED_PUBLIC_WORDS:
        if word in visible_lower:
            issues["banned_words"].append(word)

    if locale in {"fr", "ar"}:
        for phrase in HIGH_PRIORITY_EN_PHRASES:
            if phrase in visible:
                issues["en_fallback"].append(phrase)

    if path in H1_PATHS:
        h1_count = len(re.findall(r"<h1[\s>]", html))
        if h1_count != 1:
            issues["h1"].append(f"h1_count={h1_count}")

    if path in META_PATHS:
        if "<title>" not in html or "</title>" not in html:
            issues["meta"].append("missing_title")
        if not re.search(r'<meta\s+name="description"', html, flags=re.IGNORECASE):
            issues["meta"].append("missing_description")

    lower_html = html.lower()
    for needle in PEXELS_NEEDLES:
        if needle in lower_html:
            issues["pexels"].append(needle.strip())

    for name in LEAK_NAMES:
        if name in html:
            issues["api_key_leak"].append(name)
    for match in LONG_TOKEN_RE.findall(html):
        for prefix in ("key=", "token=", "secret="):
            if prefix + match in html:
                issues["api_key_leak"].append(f"after:{prefix}")
                break

    return issues


# ---------------------------------------------------------------------------
# Wizard probes
# ---------------------------------------------------------------------------


def _italy_baseline(base_url: str) -> dict:
    wizard_url = base_url + "/wizard/it/road-accident/"
    status_get, html_get, cookies = _get(wizard_url)
    if status_get != 200:
        return {"label": "it_baseline", "passed": False, "error": f"GET {status_get}"}
    csrf = _csrf(html_get)
    if not csrf:
        return {"label": "it_baseline", "passed": False, "error": "no_csrf"}
    payload = {"csrfmiddlewaretoken": csrf, **IT_BASELINE_PAYLOAD}
    status_post, body, final_url = _post(wizard_url, payload, cookies, wizard_url)
    if status_post != 200:
        return {"label": "it_baseline", "passed": False, "error": f"POST {status_post}"}
    amounts_present = all(amt in body for amt in IT_BASELINE_AMOUNTS)
    # The "calculated" container uses the OK token classes. ``text-ok-600``
    # is rendered only on the calculated state and is locale-independent.
    public_status_calculated = "text-ok-600" in body
    sim_id = final_url.rstrip("/").split("/")[-1]
    pdf_url = base_url + f"/reports/simulation/{sim_id}/pdf/"
    pdf_status, pdf_body_text, _ = _get(pdf_url, cookies)
    pdf_first4 = ""
    if pdf_status == 200:
        try:
            req = urllib.request.Request(pdf_url)
            req.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()))
            with urllib.request.urlopen(req, timeout=15) as resp:
                pdf_first4 = resp.read(4).decode("latin-1")
        except Exception:  # noqa: BLE001
            pdf_first4 = pdf_body_text[:4]
    return {
        "label": "it_baseline",
        "result_url": final_url,
        "amounts_present": amounts_present,
        "expected_amounts": list(IT_BASELINE_AMOUNTS),
        "public_status_calculated": public_status_calculated,
        "pdf_status": pdf_status,
        "pdf_first4": pdf_first4,
        "passed": (
            amounts_present
            and public_status_calculated
            and pdf_status == 200
            and pdf_first4 == "%PDF"
        ),
    }


def _unavailable(base_url: str, label: str, path: str, payload: dict) -> dict:
    wizard_url = base_url + path
    status_get, html_get, cookies = _get(wizard_url)
    if status_get != 200:
        return {"label": label, "passed": False, "error": f"GET {status_get}"}
    csrf = _csrf(html_get)
    if not csrf:
        return {"label": label, "passed": False, "error": "no_csrf"}
    full = {
        "csrfmiddlewaretoken": csrf,
        "consent_simulation": "on",
        "website": "",
        **payload,
    }
    status_post, body, final_url = _post(wizard_url, full, cookies, wizard_url)
    if status_post != 200:
        return {"label": label, "passed": False, "error": f"POST {status_post}"}
    leaks = [n for n in TECHNICAL_DIAGNOSTIC_NEEDLES if n in body]
    # Unavailable panel uses badge_variant="gold" or "sand". The
    # calculated container ships ``text-ok-600`` — its absence on a
    # successful 200 result page is the stable cross-locale signal.
    public_status_unavailable = "text-ok-600" not in body
    has_amounts = bool(
        re.search(r"€\s*[0-9][0-9.,\s]{2,}", body) or re.search(r"\bEUR\s*[0-9]", body)
    )
    return {
        "label": label,
        "result_url": final_url,
        "leaks": leaks,
        "public_status_unavailable": public_status_unavailable,
        "has_amounts": has_amounts,
        "passed": (not leaks and public_status_unavailable and not has_amounts),
    }


# ---------------------------------------------------------------------------
# DB invariants
# ---------------------------------------------------------------------------


def _legal_counts() -> dict[str, int]:
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import django

    django.setup()
    from apps.compensation.models import (  # noqa: WPS433
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
    )
    from apps.legal_sources.models import LegalSource  # noqa: WPS433

    return {
        "legal_sources": LegalSource.objects.count(),
        "datasets": CompensationDataset.objects.count(),
        "formulas": CalculationFormula.objects.count(),
        "rows": CompensationTableRow.objects.count(),
    }


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


def _verdict(report: dict) -> str:
    if report["pages_with_issues"] > 0:
        return "issues_found"
    if not report["it_baseline"]["passed"]:
        return "issues_found"
    if any(not f["passed"] for f in report["unavailable"]):
        return "issues_found"
    if report["counts_before"] != report["counts_after"]:
        return "issues_found"
    return "ok"


def render_markdown(report: dict, base_url: str) -> str:
    lines = [
        "# Product release-readiness audit — pass 1",
        "",
        f"- base URL: `{base_url}`",
        f"- pages probed: {report['pages_probed']}",
        f"- pages with issues: {report['pages_with_issues']}",
        f"- IT baseline 35/10/0: "
        f"**{'OK' if report['it_baseline']['passed'] else 'FAILED'}** "
        f"(amounts={report['it_baseline']['amounts_present']}, "
        f"PDF first-4={report['it_baseline']['pdf_first4']!r})",
        f"- FR/BE/MA/TN unavailable fixtures: "
        f"**{sum(1 for f in report['unavailable'] if f['passed'])}/"
        f"{len(report['unavailable'])} pass**",
        f"- Legal DB counts unchanged: " f"**{report['counts_before'] == report['counts_after']}**",
        f"- VERDICT: **{report['verdict'].upper()}**",
        "",
        "## Page checks",
        "",
        "| Locale | Path | HTTP | Local CSS | Tailwind CDN | Banned | EN fallback | H1 | Meta | Pexels | API leak |",
        "| --- | --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |",
    ]

    def cell(items: list[str]) -> str:
        return "—" if not items else "⚠ " + ", ".join(sorted(set(items)))

    for entry in report["pages"]:
        flags = entry["issues"]
        lines.append(
            f"| `{entry['locale']}` | `{entry['path']}` "
            f"| {cell(flags['http'])} "
            f"| {cell(flags['css_local'])} "
            f"| {cell(flags['tailwind_cdn'])} "
            f"| {cell(flags['banned_words'])} "
            f"| {cell(flags['en_fallback'])} "
            f"| {cell(flags['h1'])} "
            f"| {cell(flags['meta'])} "
            f"| {cell(flags['pexels'])} "
            f"| {cell(flags['api_key_leak'])} |"
        )

    lines.extend(
        [
            "",
            "## Italia 35/10/0 baseline",
            "",
            f"- result URL: `{report['it_baseline'].get('result_url', '')}`",
            f"- amounts present (`{', '.join(IT_BASELINE_AMOUNTS)}` EUR): "
            f"`{report['it_baseline']['amounts_present']}`",
            f"- public status calculated: "
            f"`{report['it_baseline']['public_status_calculated']}`",
            f"- PDF status: `{report['it_baseline']['pdf_status']}`",
            f"- PDF first 4 bytes: `{report['it_baseline']['pdf_first4']!r}`",
            "",
            "## FR/BE/MA/TN unavailable fixtures",
            "",
            "| Label | Result URL | Status | Leaks | Has amounts |",
            "| --- | --- | :-: | --- | :-: |",
        ]
    )
    for f in report["unavailable"]:
        leaks = ", ".join(f.get("leaks") or []) or "—"
        lines.append(
            f"| `{f['label']}` | `{f.get('result_url', '')}` "
            f"| {'OK' if f['passed'] else 'FAIL'} "
            f"| {leaks} "
            f"| {'YES' if f.get('has_amounts') else '—'} |"
        )

    lines.extend(
        [
            "",
            "## Legal data invariants",
            "",
            f"- before: `{report['counts_before']}`",
            f"- after:  `{report['counts_after']}`",
            f"- unchanged: `{report['counts_before'] == report['counts_after']}`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--report", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    counts_before = _legal_counts()

    pages: list[dict] = []
    pages_with_issues = 0
    for locale, prefix in LOCALE_PREFIXES.items():
        for path in PRINCIPAL_PATHS:
            if path == "/sitemap.xml" and locale != "it":
                # sitemap has no locale prefix
                continue
            if path == "/healthz/" and locale != "it":
                continue
            url = base_url + prefix + path
            status, html, _ = _get(url)
            issues = _check_page(locale=locale, path=path, html=html, status=status)
            entry = {
                "locale": locale,
                "path": path,
                "url": url,
                "status": status,
                "issues": issues,
            }
            if any(v for v in issues.values()):
                pages_with_issues += 1
            pages.append(entry)

    it_baseline = _italy_baseline(base_url)
    unavailable = [
        _unavailable(base_url, label, path, dict(payload))
        for (label, path, payload) in UNAVAILABLE_FIXTURES
    ]

    counts_after = _legal_counts()

    report = {
        "base_url": base_url,
        "pages": pages,
        "pages_probed": len(pages),
        "pages_with_issues": pages_with_issues,
        "it_baseline": it_baseline,
        "unavailable": unavailable,
        "counts_before": counts_before,
        "counts_after": counts_after,
    }
    report["verdict"] = _verdict(report)

    md_path = Path(args.report)
    if not md_path.is_absolute():
        md_path = (REPO_ROOT / md_path).resolve()
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(report, base_url), encoding="utf-8")

    json_path = Path(args.report_json)
    if not json_path.is_absolute():
        json_path = (REPO_ROOT / json_path).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"[report-md]   {md_path}")
    print(f"[report-json] {json_path}")
    print(
        f"[verdict] {report['verdict']} "
        f"(pages_with_issues={pages_with_issues}, "
        f"it_baseline={'OK' if it_baseline['passed'] else 'FAIL'}, "
        f"unavailable_pass={sum(1 for f in unavailable if f['passed'])}/"
        f"{len(unavailable)}, "
        f"counts_unchanged={counts_before == counts_after})"
    )

    return 0 if report["verdict"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
