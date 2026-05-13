"""Capture screenshots for F-product-public-site-qa-polish-pass2-a11y-seo.

Salva screenshot desktop (1280x900) e mobile (390x844) in
`docs/screenshots/live_qa/public_site_qa_polish_pass2/` su un runserver
gia' attivo (default porta 31452). Headless chromium via Playwright.

Output minimo richiesto dal brief pass2:
- home desktop
- countries desktop
- Italy landing mobile
- France FR
- Morocco AR (RTL)
- wizard IT form
- contact
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DESKTOP_PAGES = [
    ("01_home_it_desktop.png", "/"),
    ("02_countries_desktop.png", "/countries/"),
    ("03_country_france_fr_desktop.png", "/fr/countries/france/"),
    ("04_country_morocco_ar_desktop.png", "/ar/countries/morocco/"),
    ("05_wizard_it_form_desktop.png", "/wizard/it/road-accident/"),
    ("06_wizard_start_desktop.png", "/wizard/"),
    ("07_contact_desktop.png", "/contact/"),
    ("08_methodology_desktop.png", "/methodology/"),
    ("09_country_italy_desktop.png", "/countries/italy/"),
]

MOBILE_PAGES = [
    ("m01_country_italy_mobile.png", "/countries/italy/"),
    ("m02_home_mobile.png", "/"),
    ("m03_countries_mobile.png", "/countries/"),
    ("m04_country_morocco_ar_mobile.png", "/ar/countries/morocco/"),
    ("m05_wizard_it_form_mobile.png", "/wizard/it/road-accident/"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=31452)
    parser.add_argument(
        "--out",
        default="docs/screenshots/live_qa/public_site_qa_polish_pass2",
    )
    args = parser.parse_args()

    base = f"http://127.0.0.1:{args.port}"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        for filename, path in DESKTOP_PAGES:
            page = ctx.new_page()
            url = base + path
            page.goto(url, wait_until="networkidle", timeout=20000)
            page.screenshot(path=str(out_dir / filename), full_page=True)
            print(f"[qa-pass2] desktop {url} -> {out_dir / filename}")
            page.close()
        ctx.close()

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
            print(f"[qa-pass2] mobile {url} -> {out_dir / filename}")
            page.close()
        mctx.close()

        browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
