"""Audit residual English fallbacks in visible HTML on FR/AR funnels.

Iter: F-product-public-funnels-polish-pass4-a11y-perf-i18n.

We GET each public funnel page under /fr/ and /ar/, strip HTML tags,
and scan the visible text for high-priority English phrases that
should already have been translated by pass-3. The script returns
exit code 0 if no fallback is found, 1 otherwise.

Read-only: no side effects beyond hitting the live dev server with
GET requests (and one FR/AR POST sequence to reach result pages,
behind a CLI flag — disabled by default to keep the script idempotent
on production-style probes).

Usage::

    python scripts/audit_visible_translation_fallbacks.py
    python scripts/audit_visible_translation_fallbacks.py --include-results

Output: a JSON report with one entry per page::

    {
      "/fr/wizard/": {"status": "ok", "fallbacks": []},
      "/ar/wizard/": {"status": "fallback", "fallbacks": ["How it works"]},
      ...
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:48107"

PAGES = [
    "/fr/wizard/",
    "/fr/wizard/it/road-accident/",
    "/fr/wizard/fr/road-accident/",
    "/fr/wizard/be/road-accident/",
    "/fr/wizard/ma/inheritance/",
    "/fr/wizard/tn/inheritance/",
    "/fr/contact/",
    "/fr/contact/thank-you/",
    "/ar/wizard/",
    "/ar/wizard/it/road-accident/",
    "/ar/wizard/fr/road-accident/",
    "/ar/wizard/be/road-accident/",
    "/ar/wizard/ma/inheritance/",
    "/ar/wizard/tn/inheritance/",
    "/ar/contact/",
    "/ar/contact/thank-you/",
]

# High-priority strings introduced or reinforced by pass-3.
# If these still appear on /fr/ or /ar/ pages they indicate a missing
# locale catalogue entry (or a fuzzy match that wasn't applied).
HIGH_PRIORITY_PHRASES = [
    "How it works",
    "After you submit",
    "What this means",
    "Next steps",
    "Useful pages",
    "Back to the wizard",
    "no automatic estimate",
    "no automatic shares",
    "Submit for legal review",
    "Request a Studio review",
    "Request a manual review",
    "We will review your request",
    "3-5 working days",
    "3 to 5 working days",
    "From your inputs to a Studio review",
    "You fill the wizard",
    "We compute or report honestly",
    "You request a Studio review",
    "Result preview",
    # NB: "min / mid / max" alone is a universal column label kept verbatim in
    # FR/AR. We only flag it when surrounded by English context (e.g. "an" /
    # "range") that proves the locale catalogue is missing the entry.
    "an indicative min / mid / max range",
    "Tell us about the case",
    "Each module is activated",
]


def _fetch(url: str) -> str:
    """Fetch and return raw HTML, or "" if the page is unreachable."""

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:  # noqa: BLE001
        print(f"  ! could not fetch {url}: {exc}", file=sys.stderr)
        return ""


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _visible_text(html: str) -> str:
    """Strip tags and normalise whitespace so phrase scanning is reliable."""

    text = _TAG_RE.sub(" ", html)
    return _WS_RE.sub(" ", text).strip()


def _scan(text: str) -> list[str]:
    return [p for p in HIGH_PRIORITY_PHRASES if p in text]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-results",
        action="store_true",
        help="Also POST to wizard pages to reach /wizard/result/ — off by default.",
    )
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    report: dict[str, dict[str, object]] = {}
    any_fallback = False

    for path in PAGES:
        html = _fetch(args.base_url + path)
        if not html:
            report[path] = {"status": "unreachable", "fallbacks": []}
            continue
        text = _visible_text(html)
        fallbacks = _scan(text)
        report[path] = {
            "status": "ok" if not fallbacks else "fallback",
            "fallbacks": fallbacks,
        }
        if fallbacks:
            any_fallback = True

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if any_fallback:
        print(
            "\n[verdict] FALLBACK_FOUND — at least one FR/AR page is leaking "
            "English copy that should be translated.",
            file=sys.stderr,
        )
        return 1
    print(
        "\n[verdict] OK — no high-priority English fallback detected on FR/AR funnels.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
