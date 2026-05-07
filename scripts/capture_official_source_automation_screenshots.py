"""Screenshot batch per F-product-official-source-automation-and-full-site-functional-upgrade.

Output:
    docs/screenshots/live_qa/official_source_automation_and_full_site_upgrade/

Coverage:
- /
- /countries/
- /case-types/
- /methodology/
- /wizard/
- /wizard/it/road-accident/  (con il nuovo Module status panel)
- /countries/france/  /countries/belgium/  /countries/morocco/  /countries/tunisia/
- /contact/  (con il nuovo "What happens next")

Lo script richiede un runserver già attivo (default :48106).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DESKTOP_PAGES = [
    ("01_home_desktop.png", "/"),
    ("02_countries_desktop.png", "/countries/"),
    ("03_case_types_desktop.png", "/case-types/"),
    ("04_methodology_desktop.png", "/methodology/"),
    ("05_wizard_start_desktop.png", "/wizard/"),
    ("06_wizard_it_with_module_status_desktop.png", "/wizard/it/road-accident/"),
    ("07_country_france_desktop.png", "/countries/france/"),
    ("08_country_belgium_desktop.png", "/countries/belgium/"),
    ("09_country_morocco_desktop.png", "/countries/morocco/"),
    ("10_country_tunisia_desktop.png", "/countries/tunisia/"),
    ("11_contact_with_what_happens_next_desktop.png", "/contact/"),
    ("12_country_italy_desktop.png", "/countries/italy/"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=48106)
    parser.add_argument(
        "--out",
        default="docs/screenshots/live_qa/official_source_automation_and_full_site_upgrade",
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
            print(f"[official-automation] desktop {url} -> {out_dir / filename}")
            page.close()
        ctx.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
