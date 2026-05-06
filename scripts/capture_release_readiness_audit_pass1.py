"""Capture release-readiness screenshots — F-product-release-readiness-audit-pass1.

Drives a real Chromium against a running dev server and grabs every
principal page in three viewports (desktop, mobile, RTL/locale) so a
human reviewer can verify the public surface looks premium and
correctly localised before shipping. Tailwind CDN is route-aborted
to enforce the local-CSS-only baseline.

Outputs land in ``docs/screenshots/live_qa/release_readiness_audit_pass1/``.
"""

from __future__ import annotations

import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:48107"
OUTDIR = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "release_readiness_audit_pass1"


IT_PAYLOAD = {
    "victim_age": "35",
    "permanent_disability_percentage": "10",
    "fault_percentage": "0",
    "consent_simulation": "on",
    "website": "",
}
FR_PAYLOAD = {
    "victim_age": "30",
    "permanent_disability_percentage": "5",
    "fault_percentage": "0",
    "consent_simulation": "on",
    "website": "",
}
BE_PAYLOAD = dict(FR_PAYLOAD)
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
TN_PAYLOAD = {
    "deceased_country_of_last_residence": "TN",
    "nationality": "TN",
    "spouse_present": "on",
    "mother_present": "on",
    "sons_count": "1",
    "daughters_count": "1",
    "estate_value": "1200000",
    "consent_simulation": "on",
    "website": "",
}


# (label, locale_prefix, path, payload-or-None)
DESKTOP = [
    ("01_home_it", "", "/", None),
    ("02_countries_it", "", "/countries/", None),
    ("03_case_types_it", "", "/case-types/", None),
    ("04_methodology_it", "", "/methodology/", None),
    ("05_country_italy", "", "/countries/italy/", None),
    ("06_country_france", "", "/countries/france/", None),
    ("07_country_belgium", "", "/countries/belgium/", None),
    ("08_country_morocco", "", "/countries/morocco/", None),
    ("09_country_tunisia", "", "/countries/tunisia/", None),
    ("10_wizard_landing_it", "", "/wizard/", None),
    ("11_wizard_it_road", "", "/wizard/it/road-accident/", None),
    ("12_wizard_fr_road", "", "/wizard/fr/road-accident/", None),
    ("13_wizard_be_road", "", "/wizard/be/road-accident/", None),
    ("14_wizard_ma_inheritance", "", "/wizard/ma/inheritance/", None),
    ("15_wizard_tn_inheritance", "", "/wizard/tn/inheritance/", None),
    ("16_result_it_calculated", "", "/wizard/it/road-accident/", IT_PAYLOAD),
    ("17_result_fr_unavailable", "", "/wizard/fr/road-accident/", FR_PAYLOAD),
    ("18_result_be_unavailable", "", "/wizard/be/road-accident/", BE_PAYLOAD),
    ("19_result_ma_unavailable", "", "/wizard/ma/inheritance/", MA_PAYLOAD),
    ("20_result_tn_unavailable", "", "/wizard/tn/inheritance/", TN_PAYLOAD),
    ("21_contact", "", "/contact/", None),
    ("22_privacy", "", "/privacy/", None),
    ("23_disclaimer", "", "/disclaimer/", None),
]

MOBILE = [
    ("01_home_it", "", "/", None),
    ("02_countries_it", "", "/countries/", None),
    ("03_wizard_landing", "", "/wizard/", None),
    ("04_wizard_it_road", "", "/wizard/it/road-accident/", None),
    ("05_wizard_ma_inheritance", "", "/wizard/ma/inheritance/", None),
    ("06_result_it_calculated", "", "/wizard/it/road-accident/", IT_PAYLOAD),
    ("07_result_ma_unavailable", "", "/wizard/ma/inheritance/", MA_PAYLOAD),
    ("08_contact", "", "/contact/", None),
]

RTL_LOCALE = [
    ("01_home_fr", "/fr", "/", None),
    ("02_country_france_fr", "/fr", "/countries/france/", None),
    ("03_wizard_it_road_fr", "/fr", "/wizard/it/road-accident/", None),
    ("04_home_ar", "/ar", "/", None),
    ("05_country_morocco_ar", "/ar", "/countries/morocco/", None),
    ("06_wizard_ma_inheritance_ar", "/ar", "/wizard/ma/inheritance/", None),
    ("07_result_ma_unavailable_ar", "/ar", "/wizard/ma/inheritance/", MA_PAYLOAD),
]


def _shoot(page, target: str, payload: dict | None, out_path: Path) -> str:
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
        page.goto(result_url, wait_until="domcontentloaded", timeout=20_000)
    else:
        result_url = target
    time.sleep(0.6)
    page.screenshot(path=str(out_path), full_page=True)
    return result_url


def main() -> int:
    from playwright.sync_api import sync_playwright

    desktop_dir = OUTDIR / "after" / "desktop"
    mobile_dir = OUTDIR / "after" / "mobile"
    rtl_dir = OUTDIR / "after" / "rtl_locale"
    for d in (desktop_dir, mobile_dir, rtl_dir):
        d.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for variant, viewport, fixtures, out_dir in (
            ("desktop", {"width": 1440, "height": 900}, DESKTOP, desktop_dir),
            ("mobile", {"width": 375, "height": 800}, MOBILE, mobile_dir),
            ("rtl_locale", {"width": 1280, "height": 900}, RTL_LOCALE, rtl_dir),
        ):
            for label, locale_prefix, path, payload in fixtures:
                ctx = browser.new_context(viewport=viewport)
                ctx.route("**/cdn.tailwindcss.com/**", lambda route: route.abort())
                page = ctx.new_page()
                target = BASE_URL + locale_prefix + path
                try:
                    out_path = out_dir / f"{label}.png"
                    _shoot(page, target, payload, out_path)
                    print(f"[ok] {variant}/{label} -> " f"{out_path.relative_to(REPO_ROOT)}")
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{variant}/{label}: {exc}")
                    print(f"[FAIL] {variant}/{label}: {exc}", file=sys.stderr)
                finally:
                    ctx.close()
        browser.close()
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
