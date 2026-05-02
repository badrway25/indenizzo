"""Capture screenshots for F-product-public-site-qa-polish-pass1.

Salva screenshot desktop (1280x900) e mobile (390x844) in
`docs/screenshots/live_qa/public_site_qa_polish_pass1/` su un runserver
gia' attivo (default porta 31452). Headless chromium via Playwright.

Output minimo richiesto:
- home desktop/mobile
- countries desktop/mobile
- Italy landing (desktop)
- France FR (desktop)
- Morocco AR RTL (desktop)
- wizard start (desktop)
- wizard Italy form (desktop)
- Italy result (post-submit)
- contact (desktop)
- thank-you (post-submit)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DESKTOP_PAGES = [
    ("01_home_it_desktop.png", "/"),
    ("02_home_fr_desktop.png", "/fr/"),
    ("03_home_ar_desktop.png", "/ar/"),
    ("04_countries_desktop.png", "/countries/"),
    ("05_country_italy_desktop.png", "/countries/italy/"),
    ("06_country_france_fr_desktop.png", "/fr/countries/france/"),
    ("07_country_morocco_ar_desktop.png", "/ar/countries/morocco/"),
    ("08_wizard_start_desktop.png", "/wizard/"),
    ("09_wizard_italy_form_desktop.png", "/wizard/it/road-accident/"),
    ("10_wizard_fr_road_desktop.png", "/wizard/fr/road-accident/"),
    ("11_wizard_ma_inheritance_desktop.png", "/wizard/ma/inheritance/"),
    ("12_methodology_desktop.png", "/methodology/"),
    ("13_contact_desktop.png", "/contact/"),
    ("14_disclaimer_desktop.png", "/disclaimer/"),
]


MOBILE_PAGES = [
    ("m01_home_mobile.png", "/"),
    ("m02_countries_mobile.png", "/countries/"),
    ("m03_country_italy_mobile.png", "/countries/italy/"),
    ("m04_wizard_mobile.png", "/wizard/"),
    ("m05_contact_mobile.png", "/contact/"),
    ("m06_country_morocco_ar_mobile.png", "/ar/countries/morocco/"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=31452)
    parser.add_argument(
        "--out",
        default="docs/screenshots/live_qa/public_site_qa_polish_pass1",
    )
    args = parser.parse_args()

    base = f"http://127.0.0.1:{args.port}"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Desktop
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        for filename, path in DESKTOP_PAGES:
            page = ctx.new_page()
            url = base + path
            page.goto(url, wait_until="networkidle", timeout=20000)
            page.screenshot(path=str(out_dir / filename), full_page=True)
            print(f"[qa-pass1] desktop {url} -> {out_dir / filename}")
            page.close()
        ctx.close()

        # Mobile (iPhone-ish)
        mctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
        )
        for filename, path in MOBILE_PAGES:
            page = mctx.new_page()
            url = base + path
            page.goto(url, wait_until="networkidle", timeout=20000)
            page.screenshot(path=str(out_dir / filename), full_page=True)
            print(f"[qa-pass1] mobile {url} -> {out_dir / filename}")
            page.close()
        mctx.close()

        # Italy result + thank-you (require POST flows)
        ctx2 = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx2.new_page()
        page.goto(f"{base}/wizard/it/road-accident/", wait_until="networkidle")
        page.fill("#id_victim_age", "35")
        page.fill("#id_permanent_disability_percentage", "10")
        page.fill("#id_fault_percentage", "0")
        page.check("#id_consent_simulation")
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        target = out_dir / "15_italy_result_desktop.png"
        page.screenshot(path=str(target), full_page=True)
        print(f"[qa-pass1] desktop result -> {target}")
        page.close()

        page = ctx2.new_page()
        page.goto(f"{base}/contact/", wait_until="networkidle")
        page.fill("#id_first_name", "QA")
        page.fill("#id_last_name", "Pass1")
        page.fill("#id_email", "qa+local@example.test")
        page.select_option("#id_preferred_language", "it")
        page.fill("#id_message", "QA pass1 test (do not reply). Lorem ipsum dolor.")
        page.check("#id_privacy_accepted")
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        target = out_dir / "16_contact_thank_you_desktop.png"
        page.screenshot(path=str(target), full_page=True)
        print(f"[qa-pass1] desktop thank-you -> {target}")
        page.close()

        ctx2.close()
        browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
