"""Capture before/after screenshots for the applicable-law skeleton iter.

Mirrors ``capture_result_page_localization_pass1.py`` but covers the
routes / payloads requested by F-eu-650-2012-applicable-law-decision-engine-skeleton.

Usage::

    python scripts/capture_applicable_law_skeleton_pass1.py before
    python scripts/capture_applicable_law_skeleton_pass1.py after
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:48107"
OUTDIR_ROOT = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "applicable_law_skeleton_pass1"


# (label, locale_prefix, target_path, optional_post_payload).
# When payload is None, just GET the page; when provided, POST then
# follow the redirect to the result page.
DESKTOP = [
    ("wizard_ma_inheritance_it", "", "/wizard/ma/inheritance/", None),
    ("wizard_tn_inheritance_it", "", "/wizard/tn/inheritance/", None),
    (
        "result_ma_post_unavailable",
        "",
        "/wizard/ma/inheritance/",
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "FR",
            "spouse_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "estate_value": "800000",
            "assets_countries": "MA, FR",
            "consent_simulation": "on",
            "website": "",
        },
    ),
    (
        "result_tn_post_unavailable",
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
            "consent_simulation": "on",
            "website": "",
        },
    ),
    ("wizard_ma_inheritance_ar", "/ar", "/wizard/ma/inheritance/", None),
    (
        "result_ma_post_unavailable_AR",
        "/ar",
        "/wizard/ma/inheritance/",
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "estate_value": "800000",
            "consent_simulation": "on",
            "website": "",
        },
    ),
]

MOBILE = [
    ("wizard_ma_inheritance_it", "", "/wizard/ma/inheritance/", None),
    ("wizard_ma_inheritance_ar", "/ar", "/wizard/ma/inheritance/", None),
    (
        "result_ma_post_unavailable",
        "",
        "/wizard/ma/inheritance/",
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "FR",
            "spouse_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "estate_value": "800000",
            "assets_countries": "MA, FR",
            "consent_simulation": "on",
            "website": "",
        },
    ),
]


def run(phase: str) -> int:
    from playwright.sync_api import sync_playwright

    desktop_dir = OUTDIR_ROOT / phase / "desktop"
    mobile_dir = OUTDIR_ROOT / phase / "mobile"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    mobile_dir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for variant, viewport, fixtures, out_dir in (
            ("desktop", {"width": 1440, "height": 900}, DESKTOP, desktop_dir),
            ("mobile", {"width": 375, "height": 800}, MOBILE, mobile_dir),
        ):
            for label, locale_prefix, path, payload in fixtures:
                ctx = browser.new_context(viewport=viewport)
                page = ctx.new_page()
                target = BASE_URL + locale_prefix + path
                try:
                    page.goto(target, wait_until="domcontentloaded", timeout=20_000)
                    if payload is not None:
                        csrf = page.evaluate("""() => {
                                const forms = document.querySelectorAll('form[method="post"]');
                                for (const f of forms) {
                                    if (f.action.includes('/i18n/')) continue;
                                    const t = f.querySelector('input[name="csrfmiddlewaretoken"]');
                                    if (t) return t.value;
                                }
                                return null;
                            }""")
                        if not csrf:
                            raise RuntimeError(f"no CSRF on {target}")
                        body = "&".join(
                            f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}"
                            for k, v in [("csrfmiddlewaretoken", csrf), *payload.items()]
                        )
                        result_url = page.evaluate(
                            """async (args) => {
                                const r = await fetch(args.url, {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                                    body: args.body,
                                    credentials: 'include',
                                    redirect: 'follow',
                                });
                                return r.url;
                            }""",
                            {"url": target, "body": body},
                        )
                        page.goto(result_url, wait_until="networkidle", timeout=20_000)
                    else:
                        page.goto(target, wait_until="networkidle", timeout=20_000)
                    time.sleep(1.0)
                    out_path = out_dir / f"{label}.png"
                    page.screenshot(path=str(out_path), full_page=True)
                    print(f"[ok] {variant}/{label} -> {out_path.relative_to(REPO_ROOT)}")
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{variant}/{label}: {exc}")
                    print(f"[FAIL] {variant}/{label}: {exc}", file=sys.stderr)
                finally:
                    ctx.close()

        browser.close()

    if failures:
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("before", "after"))
    args = parser.parse_args()
    return run(args.phase)


if __name__ == "__main__":
    sys.exit(main())
