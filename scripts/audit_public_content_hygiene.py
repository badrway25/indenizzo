"""Audit hygiene of the public site copy across IT/FR/AR/EN.

Iter: F-product-public-site-release-polish-pass5-premium-content-cleanup.

Walks every principal public page in the four MVP languages and
flags:

1. **Banned public words** — wording that should never reach end users
   (scaffold, placeholder, under validation, in preparation, coming
   soon, work in progress, in corso, modulo non operativo, legal
   validation wizard).
2. **English fallbacks on FR / AR** — high-priority strings that
   indicate a missing locale catalogue entry on a translated route
   (How it works, What this means, Next steps, etc.).
3. **Heading regressions** — duplicate or missing ``<h1>``.
4. **Image regressions** — every ``<img>`` must carry ``alt`` and
   ``width`` / ``height``.
5. **Pexels attribution** — must never surface in visible HTML.
6. **API key leaks** — env var names or long opaque tokens.

The script writes a markdown report to
``docs/architecture/PUBLIC_CONTENT_HYGIENE_AUDIT_PASS5.md`` and exits
0 if no issue is found, 1 otherwise.

Read-only (HTTP GETs only) — no DB writes, no external services.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:48107"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "architecture" / "PUBLIC_CONTENT_HYGIENE_AUDIT_PASS5.md"

# Pages by language.  We use the same set in every locale so the diff
# is symmetric.  The default-language path is no-prefix (Italian).
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
    "/privacy/",
    "/disclaimer/",
]

LOCALE_PREFIXES = {"it": "", "fr": "/fr", "ar": "/ar", "en": "/en"}

BANNED_PUBLIC_WORDS = (
    "scaffold",
    "placeholder",
    "under validation",
    "in preparation",
    "coming soon",
    "work in progress",
    "in corso",
    "modulo non operativo",
    "legal validation wizard",
    "module pending",
    "engine pending",
    "missing_documents",
    "unavailable_requires_legal_validation",
)

# High-priority phrases that should never appear in visible body text
# of a /fr/ or /ar/ page — they signal a missing translation.
HIGH_PRIORITY_EN_PHRASES = (
    "How it works",
    "What this means",
    "Next steps",
    "Useful pages",
    "Request legal review",
    "Start simulation",
    "No automatic estimate",
    "no automatic estimate",
    "no automatic shares",
    "Submit for legal review",
    "Back to the wizard",
    # Pass-5 introduced premium copy whose English source must not leak
    # on /fr/ or /ar/ once the catalogues are updated:
    "indicative calculation is available",
    "Preliminary legal assessment",
    "Manual legal review",
    "International inheritance review",
    "no automatic amount is published",
    "Studio reviews each",
    "Submit the case to the Studio",
    "Studio offers a preliminary",
    "applicable-law mapping",
)

PEXELS_NEEDLES = ("photo by ", "pexels.com")
LEAK_NAMES = ("PEXELS_API_KEY", "STRIPE_SECRET", "SENDGRID_API_KEY")
LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9]{40,}")
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
SCRIPT_OR_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def _fetch(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except urllib.error.URLError as exc:  # noqa: BLE001
        print(f"  ! could not fetch {url}: {exc}", file=sys.stderr)
        return 0, ""


def _visible_text(html: str) -> str:
    """Strip <script>/<style> blocks then HTML tags. Returns visible
    body text only — used for copy hygiene scans."""

    cleaned = SCRIPT_OR_STYLE_RE.sub(" ", html)
    return WS_RE.sub(" ", TAG_RE.sub(" ", cleaned)).strip()


def check_page(html: str, *, locale: str) -> dict[str, list[str]]:
    """Apply all hygiene rules to a single page. Returns a dict of
    rule → list of failure detail strings (empty list = rule passed)."""

    issues: dict[str, list[str]] = {
        "banned_words": [],
        "en_fallback": [],
        "h1": [],
        "img": [],
        "pexels": [],
        "api_key_leak": [],
    }

    visible = _visible_text(html)
    visible_lower = visible.lower()

    for word in BANNED_PUBLIC_WORDS:
        if word in visible_lower:
            issues["banned_words"].append(word)

    if locale in {"fr", "ar"}:
        for phrase in HIGH_PRIORITY_EN_PHRASES:
            if phrase in visible:
                issues["en_fallback"].append(phrase)

    h1_count = len(re.findall(r"<h1[\s>]", html))
    if h1_count != 1:
        issues["h1"].append(f"h1_count={h1_count}")

    for img in re.findall(r"<img\b[^>]*>", html, flags=re.IGNORECASE):
        if not re.search(r'\balt\s*=\s*["\']', img, flags=re.IGNORECASE):
            issues["img"].append("missing_alt")
            break
    for img in re.findall(r"<img\b[^>]*>", html, flags=re.IGNORECASE):
        has_w = re.search(r'\bwidth\s*=\s*["\']?\d', img, flags=re.IGNORECASE)
        has_h = re.search(r'\bheight\s*=\s*["\']?\d', img, flags=re.IGNORECASE)
        if not (has_w and has_h):
            issues["img"].append("missing_dimensions")
            break

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


def render_markdown(report: dict, base_url: str) -> str:
    lines = [
        "# Public content hygiene audit — pass 5",
        "",
        "Iter: F-product-public-site-release-polish-pass5-premium-content-cleanup.",
        f"- base URL: `{base_url}`",
        f"- pages probed: {len(report['pages'])}",
        f"- pages with issues: {report['summary']['pages_with_issues']}",
        f"- verdict: **{'OK' if report['summary']['verdict'] == 'ok' else 'ISSUES_FOUND'}**",
        "",
        "## Per-page report",
        "",
        "| Locale | Path | Banned | EN fallback | H1 | Img | Pexels | API leak |",
        "| --- | --- | :-: | :-: | :-: | :-: | :-: | :-: |",
    ]
    for entry in report["pages"]:
        flags = entry["issues"]

        def cell(items: list[str]) -> str:
            return "—" if not items else f"⚠ {', '.join(sorted(set(items)))}"

        lines.append(
            f"| `{entry['locale']}` | `{entry['path']}` "
            f"| {cell(flags['banned_words'])} "
            f"| {cell(flags['en_fallback'])} "
            f"| {cell(flags['h1'])} "
            f"| {cell(flags['img'])} "
            f"| {cell(flags['pexels'])} "
            f"| {cell(flags['api_key_leak'])} |"
        )

    lines.extend(["", "## Summary by rule", ""])
    for rule, count in report["summary"]["by_rule"].items():
        lines.append(f"- `{rule}`: {count} page(s) affected")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON to stdout instead of pretty text."
    )
    args = parser.parse_args()

    pages: list[dict] = []
    by_rule: dict[str, int] = {
        "banned_words": 0,
        "en_fallback": 0,
        "h1": 0,
        "img": 0,
        "pexels": 0,
        "api_key_leak": 0,
    }
    pages_with_issues = 0

    for locale, prefix in LOCALE_PREFIXES.items():
        for path in PRINCIPAL_PATHS:
            target = args.base_url.rstrip("/") + prefix + path
            status, html = _fetch(target)
            entry = {
                "locale": locale,
                "path": path,
                "status": status,
                "issues": {
                    "banned_words": [],
                    "en_fallback": [],
                    "h1": [],
                    "img": [],
                    "pexels": [],
                    "api_key_leak": [],
                },
            }
            if status == 200 and html:
                entry["issues"] = check_page(html, locale=locale)
            elif status != 200:
                entry["issues"]["h1"].append(f"http_status={status}")
            any_issue = any(v for v in entry["issues"].values())
            if any_issue:
                pages_with_issues += 1
                for rule, items in entry["issues"].items():
                    if items:
                        by_rule[rule] += 1
            pages.append(entry)

    summary = {
        "pages_with_issues": pages_with_issues,
        "by_rule": by_rule,
        "verdict": "ok" if pages_with_issues == 0 else "issues_found",
    }
    report = {"base_url": args.base_url, "pages": pages, "summary": summary}

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (REPO_ROOT / report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(report, args.base_url), encoding="utf-8")
    print(f"[report] {report_path}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(
            f"[verdict] {summary['verdict']} "
            f"(pages_with_issues={pages_with_issues}, by_rule={by_rule})",
        )

    return 0 if summary["verdict"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
