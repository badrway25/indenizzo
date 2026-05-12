"""Playwright capture — PRODUCT-2 lead funnel improvements.

Walks the end-to-end public funnel (homepage → wizard → result →
contact prefilled → thank-you) in headless Chromium, plus a couple
of AR / FR snapshots, and saves PNGs into
`docs/screenshots/delta_audit_2026-05-10/after/product-lead-funnel-improvements/`.

Usage:

    .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
    # then:
    .venv/Scripts/python.exe scripts/capture_product_2_lead_funnel.py
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
    / "product-lead-funnel-improvements"
)

BASE_URL = "http://127.0.0.1:8000"

VIEWPORTS = [
    ("desktop-1280", 1280, 900),
    ("mobile-390", 390, 844),
]

# Plain GETs per locale.
GETS = [
    ("home-it", "/"),
    ("wizard-it", "/wizard/it/road-accident/"),
    ("contact-empty", "/contact/"),
    ("thank-you", "/contact/thank-you/"),
    ("home-ar", "/ar/"),
    ("contact-ar", "/ar/contact/"),
    ("wizard-fr-review-gated", "/wizard/fr/road-accident/"),
]


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
                for label, path in GETS:
                    page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
                    page.evaluate("document.fonts.ready")
                    outpath = OUT_DIR / f"{label}-{vp_label}.png"
                    page.screenshot(path=str(outpath), full_page=True)
                    size_kb = outpath.stat().st_size / 1024
                    print(f"  saved {outpath.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")

                # 2) Wizard IT → result page (so we capture the
                # new "Documents to prepare" block in context).
                page.goto(
                    f"{BASE_URL}/wizard/it/road-accident/",
                    wait_until="networkidle",
                )
                page.fill("#id_victim_age", "35")
                page.fill("#id_permanent_disability_percentage", "10")
                page.fill("#id_fault_percentage", "0")
                # Tick GDPR consent checkboxes.
                page.check("#id_consent_simulation")
                page.check("#id_special_categories_consent")
                page.click("button[type=submit]")
                page.wait_for_load_state("networkidle")
                page.evaluate("document.fonts.ready")
                outpath = OUT_DIR / f"result-it-{vp_label}.png"
                page.screenshot(path=str(outpath), full_page=True)
                size_kb = outpath.stat().st_size / 1024
                print(f"  saved {outpath.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")

                # 3) Result page CTA → contact form with `?sim=`
                # so we see the linked-simulation confirmation banner.
                current_url = page.url
                m = re.search(r"/wizard/result/([0-9a-f-]+)/", current_url)
                if m:
                    sim_uuid = m.group(1)
                    page.goto(
                        f"{BASE_URL}/contact/?sim={sim_uuid}",
                        wait_until="networkidle",
                    )
                    page.evaluate("document.fonts.ready")
                    outpath = OUT_DIR / f"contact-with-sim-{vp_label}.png"
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
