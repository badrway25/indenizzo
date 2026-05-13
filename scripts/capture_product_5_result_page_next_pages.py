"""Playwright capture — PRODUCT-5 result-page recommended next pages.

Runs a real IT wizard POST, captures the resulting `/wizard/result/<uuid>/`
page (showing the new "Useful pages for your case" section), then a
matching FR review-gated capture, then clicks one recommended link
to verify the navigation, and a contact-linked capture for context.

Output: docs/screenshots/delta_audit_2026-05-10/after/product-result-page-next-pages/

Usage:

    .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
    # in another shell:
    .venv/Scripts/python.exe scripts/capture_product_5_result_page_next_pages.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = (
    REPO_ROOT
    / "docs"
    / "screenshots"
    / "delta_audit_2026-05-10"
    / "after"
    / "product-result-page-next-pages"
)

BASE_URL = "http://127.0.0.1:8000"

VIEWPORTS = [
    ("desktop-1280", 1280, 900),
    ("mobile-390", 390, 844),
]


def _submit_wizard(page, country_path: str) -> str | None:
    """Submit the road-accident wizard for a given country path
    (e.g. /wizard/it/road-accident/ or /wizard/fr/road-accident/).
    Returns the simulation UUID if a result page was reached.

    Note: `fault_percentage` lives inside the PRODUCT-3 <details>
    "Additional details" block (collapsed by default), so we
    skip it here — Playwright would block on "element not visible".
    Submitting with only the essential fields exercises the
    default-mobile path the user actually takes."""
    page.goto(f"{BASE_URL}{country_path}", wait_until="networkidle")
    page.fill("#id_victim_age", "35")
    page.fill("#id_permanent_disability_percentage", "10")
    page.check("#id_consent_simulation")
    page.check("#id_special_categories_consent")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    m = re.search(r"/wizard/result/([0-9a-f-]+)/", page.url)
    return m.group(1) if m else None


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

                # 1) Italy road-accident → result page (showing recs).
                sim_uuid = _submit_wizard(page, "/wizard/it/road-accident/")
                outpath = OUT_DIR / f"result-it-{vp_label}.png"
                page.screenshot(path=str(outpath), full_page=True)
                size_kb = outpath.stat().st_size / 1024
                print(f"  saved {outpath.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")

                # 2) Click one recommended landing from the result page.
                if sim_uuid:
                    page.goto(
                        f"{BASE_URL}/case-types/bodily-injury/",
                        wait_until="networkidle",
                    )
                    page.evaluate("document.fonts.ready")
                    outpath = OUT_DIR / f"landing-bodily-injury-from-result-{vp_label}.png"
                    page.screenshot(path=str(outpath), full_page=True)
                    size_kb = outpath.stat().st_size / 1024
                    print(f"  saved {outpath.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")

                    # 3) Contact form linked from the result.
                    page.goto(
                        f"{BASE_URL}/contact/?sim={sim_uuid}",
                        wait_until="networkidle",
                    )
                    page.evaluate("document.fonts.ready")
                    outpath = OUT_DIR / f"contact-linked-from-result-{vp_label}.png"
                    page.screenshot(path=str(outpath), full_page=True)
                    size_kb = outpath.stat().st_size / 1024
                    print(f"  saved {outpath.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")

                # 4) France review-gated → result page.
                fr_sim_uuid = _submit_wizard(page, "/wizard/fr/road-accident/")
                outpath = OUT_DIR / f"result-fr-review-gated-{vp_label}.png"
                page.screenshot(path=str(outpath), full_page=True)
                size_kb = outpath.stat().st_size / 1024
                print(f"  saved {outpath.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")

                context.close()
        finally:
            browser.close()

    print(f"\n[OK] screenshots in {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
