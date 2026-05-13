"""Playwright capture — PRODUCT-6 case-type landing FAQs.

Captures four landings on IT (road-accident, insurance-offer-review,
medical-malpractice, death-of-relative) at desktop + mobile, with the
FAQ accordion opened so the section is visible in the screenshot. Also
captures the road-accident landing on AR to verify RTL rendering of
the `<details>/<summary>` widget.

Output: docs/screenshots/delta_audit_2026-05-10/after/product-case-type-faqs/

Usage:

    .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
    # in another shell:
    .venv/Scripts/python.exe scripts/capture_product_6_case_type_faqs.py
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
    / "product-case-type-faqs"
)

BASE_URL = "http://127.0.0.1:8000"

VIEWPORTS = [
    ("desktop-1280", 1280, 900),
    ("mobile-390", 390, 844),
]

# IT slugs to capture — the legally-sensitive set: bodily-injury offer
# review, medical malpractice, the death-of-relative landing, and the
# road-accident funnel entry.
IT_SLUGS = (
    "road-accident",
    "insurance-offer-review",
    "medical-malpractice",
    "death-of-relative",
)


def _open_all_faqs(page) -> None:
    """Set `open` on every `<details>` so the FAQ block is fully
    visible in the screenshot — captures the post-click state without
    needing per-element clicks."""
    page.evaluate(
        "document.querySelectorAll('details').forEach(d => d.open = true)"
    )


def _capture(page, url: str, out_path: Path) -> None:
    page.goto(url, wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    _open_all_faqs(page)
    page.wait_for_timeout(150)
    page.screenshot(path=str(out_path), full_page=True)
    size_kb = out_path.stat().st_size / 1024
    print(f"  saved {out_path.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")


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

                for slug in IT_SLUGS:
                    _capture(
                        page,
                        f"{BASE_URL}/case-types/{slug}/",
                        OUT_DIR / f"{slug}-it-{vp_label}.png",
                    )

                # AR/RTL — pin one landing to verify the disclosure
                # widget marker switches sides natively.
                _capture(
                    page,
                    f"{BASE_URL}/ar/case-types/road-accident/",
                    OUT_DIR / f"road-accident-ar-rtl-{vp_label}.png",
                )

                context.close()
        finally:
            browser.close()

    print(f"\n[OK] screenshots in {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
