"""Capture screenshots of the public funnels for pass-4 polish (a11y/perf/i18n).

Iter: F-product-public-funnels-polish-pass4-a11y-perf-i18n.

Steps captured (1 png per step, full page):

1. /wizard/ — EN start page (baseline).
2. /fr/wizard/ — FR start page with translated "Comment ça marche".
3. /ar/wizard/ — AR start page (RTL) with translated headers.
4. /wizard/it/road-accident/ — EN IT wizard with the "After you submit" preview.
5. /fr/wizard/fr/road-accident/ — FR scaffold (no automatic estimate banner).
6. /ar/wizard/ma/inheritance/ — AR Morocco scaffold (no automatic shares).
7. /contact/ — EN contact form with "Useful pages" footer nav.
8. /fr/contact/ — FR contact form with translated "What happens next".
9. /ar/contact/ — AR contact form with translated multiline blocktranslates.

Output: docs/screenshots/live_qa/public_funnels_polish_pass4/<step>.png

Read-only on the legal/calculator layer (HTTP GETs only).
"""

from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "public_funnels_polish_pass4"
BASE_URL = "http://127.0.0.1:48107"


PAGES = [
    ("01_wizard_start_en", "/wizard/"),
    ("02_wizard_start_fr", "/fr/wizard/"),
    ("03_wizard_start_ar", "/ar/wizard/"),
    ("04_wizard_italy_form_en", "/wizard/it/road-accident/"),
    ("05_wizard_france_form_fr", "/fr/wizard/fr/road-accident/"),
    ("06_wizard_morocco_form_ar", "/ar/wizard/ma/inheritance/"),
    ("07_contact_en", "/contact/"),
    ("08_contact_fr", "/fr/contact/"),
    ("09_contact_ar", "/ar/contact/"),
]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        for name, path in PAGES:
            url = BASE_URL + path
            try:
                page.goto(url, wait_until="networkidle", timeout=30_000)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {name}: navigation failed: {exc}")
                continue
            target = OUTPUT_DIR / f"{name}.png"
            page.screenshot(path=str(target), full_page=True)
            saved.append(name)
            print(f"  saved {target.relative_to(REPO_ROOT).as_posix()}")

        browser.close()

    print(f"\n[summary] saved {len(saved)} artefact(s) to {OUTPUT_DIR.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
