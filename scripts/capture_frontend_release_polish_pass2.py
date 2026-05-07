"""Capture before/after screenshots for F-frontend-release-polish-pass2.

Each invocation captures into ``before/`` or ``after/`` (controlled
by ``--phase``). The set focuses on the three polish items:

1. Mobile <sm IT-result spacing vs the floating cookie banner.
2. MA + TN country-landing hero crop.
3. AR typography (Arabic headings + body) on the home, country
   landing, and unavailable result page.

Tailwind CDN is route-aborted to enforce the local-CSS-only
baseline.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:48107"
OUTDIR_ROOT = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "frontend_release_polish_pass2"


IT_PAYLOAD = {
    "victim_age": "35",
    "permanent_disability_percentage": "10",
    "fault_percentage": "0",
    "consent_simulation": "on",
    "website": "",
}
MA_PAYLOAD = {
    "deceased_country_of_last_residence": "MA",
    "nationality": "MA",
    "spouse_present": "on",
    "sons_count": "1",
    "daughters_count": "1",
    "estate_value": "800000",
    "consent_simulation": "on",
    "website": "",
}


# (label, locale_prefix, path, payload-or-None)
DESKTOP = [
    ("01_country_morocco", "", "/countries/morocco/", None),
    ("02_country_tunisia", "", "/countries/tunisia/", None),
    ("03_result_it_calculated", "", "/wizard/it/road-accident/", IT_PAYLOAD),
]

MOBILE = [
    ("01_country_morocco", "", "/countries/morocco/", None),
    ("02_country_tunisia", "", "/countries/tunisia/", None),
    ("03_result_it_calculated", "", "/wizard/it/road-accident/", IT_PAYLOAD),
]

RTL_LOCALE = [
    ("01_home_ar", "/ar", "/", None),
    ("02_country_morocco_ar", "/ar", "/countries/morocco/", None),
    ("03_wizard_ma_inheritance_ar", "/ar", "/wizard/ma/inheritance/", None),
    ("04_result_ma_unavailable_ar", "/ar", "/wizard/ma/inheritance/", MA_PAYLOAD),
]


def _shoot(page, target: str, payload: dict | None, out_path: Path) -> str:
    page.goto(target, wait_until="networkidle", timeout=30_000)
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
        page.goto(result_url, wait_until="networkidle", timeout=30_000)
    else:
        result_url = target
    # Wait for webfonts to download so AR/Amiri/Tajawal text renders.
    page.evaluate("() => document.fonts && document.fonts.ready")
    time.sleep(1.2)
    page.screenshot(path=str(out_path), full_page=True)
    return result_url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=("before", "after"),
        required=True,
        help="Output subdirectory selector.",
    )
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    desktop_dir = OUTDIR_ROOT / args.phase / "desktop"
    mobile_dir = OUTDIR_ROOT / args.phase / "mobile"
    rtl_dir = OUTDIR_ROOT / args.phase / "rtl_locale"
    for d in (desktop_dir, mobile_dir, rtl_dir):
        d.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for variant, viewport, fixtures, out_dir in (
            ("desktop", {"width": 1440, "height": 900}, DESKTOP, desktop_dir),
            ("mobile", {"width": 375, "height": 800}, MOBILE, mobile_dir),
            (
                "rtl_locale",
                {"width": 1280, "height": 900},
                RTL_LOCALE,
                rtl_dir,
            ),
        ):
            for label, locale_prefix, path, payload in fixtures:
                ctx = browser.new_context(viewport=viewport)
                ctx.route("**/cdn.tailwindcss.com/**", lambda route: route.abort())
                page = ctx.new_page()
                target = BASE_URL + locale_prefix + path
                try:
                    out_path = out_dir / f"{label}.png"
                    _shoot(page, target, payload, out_path)
                    print(f"[ok] {variant}/{label} -> {out_path.relative_to(REPO_ROOT)}")
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{variant}/{label}: {exc}")
                    print(f"[FAIL] {variant}/{label}: {exc}", file=sys.stderr)
                finally:
                    ctx.close()
        browser.close()
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
