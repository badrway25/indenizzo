"""Playwright capture — PRODUCT-1 France signoff pack.

Renders the public France path in headless Chromium at desktop
(1280) and mobile (390) viewports, captures full-page PNGs into
`docs/screenshots/delta_audit_2026-05-10/after/product-france-signoff-pack/`,
and additionally takes a POST-screenshot showing the
review-gated result (no EUR amount).

Pages covered:

 - `/countries/france/` — country landing page;
 - `/wizard/fr/road-accident/` — wizard FR (form);
 - `/wizard/fr/road-accident/` after POST (smoke 35×5×0) — result
   page, must say "preliminary legal assessment", no amount;
 - `/contact/` — Studio contact CTA target.

Usage:

    # Start runserver in another shell:
    .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000

    # Then:
    .venv/Scripts/python.exe scripts/capture_product_1_france_signoff_pack.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = (
    REPO_ROOT
    / "docs"
    / "screenshots"
    / "delta_audit_2026-05-10"
    / "after"
    / "product-france-signoff-pack"
)

GETS = [
    ("france-landing", "/countries/france/"),
    ("france-wizard-form", "/wizard/fr/road-accident/"),
    ("contact", "/contact/"),
]

VIEWPORTS = [
    ("desktop-1280", 1280, 900),
    ("mobile-390", 390, 844),
]

BASE_URL = "http://127.0.0.1:8000"


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for vp_label, vw, vh in VIEWPORTS:
                context = browser.new_context(
                    viewport={"width": vw, "height": vh},
                    device_scale_factor=2,
                )
                page = context.new_page()

                # 1) Plain GETs
                for page_label, path in GETS:
                    url = f"{BASE_URL}{path}"
                    page.goto(url, wait_until="networkidle")
                    page.evaluate("document.fonts.ready")
                    outpath = OUT_DIR / f"{page_label}-{vp_label}.png"
                    page.screenshot(path=str(outpath), full_page=True)
                    size_kb = outpath.stat().st_size / 1024
                    print(f"  saved {outpath.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")

                # 2) POST the smoke 35×5×0 to capture the review-gated
                # result page (no amount, "preliminary legal assessment").
                page.goto(
                    f"{BASE_URL}/wizard/fr/road-accident/",
                    wait_until="networkidle",
                )
                page.fill("#id_victim_age", "35")
                page.fill("#id_permanent_disability_percentage", "5")
                page.fill("#id_fault_percentage", "0")
                # Submit. The form has a CTA button.
                page.click("button[type=submit]", timeout=5000)
                page.wait_for_load_state("networkidle")
                page.evaluate("document.fonts.ready")
                outpath = OUT_DIR / f"france-result-review-gated-{vp_label}.png"
                page.screenshot(path=str(outpath), full_page=True)
                size_kb = outpath.stat().st_size / 1024
                print(f"  saved {outpath.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")

                context.close()
        finally:
            browser.close()

    print(
        f"\n[OK] {(len(GETS) + 1) * len(VIEWPORTS)} screenshots in "
        f"{OUT_DIR.relative_to(REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
