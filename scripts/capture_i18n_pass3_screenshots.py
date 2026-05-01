"""
Capture live screenshots for F-product-i18n-translations-pass3-visible-copy.

Usa Playwright (chromium headless) per fotografare 8 pagine pubbliche
sul server di sviluppo locale e salvarle in
`docs/screenshots/live_qa/i18n_translations_pass3/`.

Esegui DOPO che il server `manage.py runserver` è attivo sulla porta
indicata da --port (default 31448).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGES = [
    ("01_fr_home.png", "/fr/"),
    ("02_fr_france.png", "/fr/countries/france/"),
    ("03_fr_wizard.png", "/fr/wizard/"),
    ("04_fr_contact.png", "/fr/contact/"),
    ("05_ar_home_rtl.png", "/ar/"),
    ("06_ar_morocco_rtl.png", "/ar/countries/morocco/"),
    ("07_ar_wizard_rtl.png", "/ar/wizard/"),
    ("08_ar_contact_rtl.png", "/ar/contact/"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=31448)
    parser.add_argument(
        "--out",
        default="docs/screenshots/live_qa/i18n_translations_pass3",
    )
    args = parser.parse_args()

    base = f"http://127.0.0.1:{args.port}"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        for filename, path in PAGES:
            page = context.new_page()
            url = base + path
            page.goto(url, wait_until="networkidle", timeout=20000)
            target = out_dir / filename
            page.screenshot(path=str(target), full_page=True)
            print(f"[i18n-pass3-shots] {url} -> {target}")
            page.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
