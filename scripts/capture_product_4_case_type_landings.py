"""Playwright capture — PRODUCT-4 case-type landings.

Captures the new /case-types/ hub and the 8 per-case-type landings
at desktop (1280) and mobile (390), plus AR/RTL on hub +
incident-stradale to verify RTL flow.

Output: docs/screenshots/delta_audit_2026-05-10/after/product-case-type-landings/

Usage:

    .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
    # in another shell:
    .venv/Scripts/python.exe scripts/capture_product_4_case_type_landings.py
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
    / "product-case-type-landings"
)

BASE_URL = "http://127.0.0.1:8000"

VIEWPORTS = [
    ("desktop-1280", 1280, 900),
    ("mobile-390", 390, 844),
]

# Plain GETs per viewport.
GETS = [
    ("hub", "/case-types/"),
    ("road-accident", "/case-types/road-accident/"),
    ("bodily-injury", "/case-types/bodily-injury/"),
    ("insurance-offer-review", "/case-types/insurance-offer-review/"),
    ("work-injury", "/case-types/work-injury/"),
    ("medical-malpractice", "/case-types/medical-malpractice/"),
    ("death-of-relative", "/case-types/death-of-relative/"),
    ("foreigners-in-italy", "/case-types/foreigners-in-italy/"),
    ("cross-border-cases", "/case-types/cross-border-cases/"),
    # AR RTL coverage on hub + one landing.
    ("hub-ar", "/ar/case-types/"),
    ("road-accident-ar", "/ar/case-types/road-accident/"),
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

                for label, path in GETS:
                    page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
                    page.evaluate("document.fonts.ready")
                    outpath = OUT_DIR / f"{label}-{vp_label}.png"
                    page.screenshot(path=str(outpath), full_page=True)
                    size_kb = outpath.stat().st_size / 1024
                    print(f"  saved {outpath.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")

                # Contact form with `?case_type=` prefill (post-PRODUCT-4
                # extension). Capture once per viewport to show the
                # case-type select is preselected.
                page.goto(
                    f"{BASE_URL}/contact/?case_type=medical_malpractice",
                    wait_until="networkidle",
                )
                page.evaluate("document.fonts.ready")
                outpath = OUT_DIR / f"contact-with-case-type-{vp_label}.png"
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
