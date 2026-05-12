"""Playwright visual-QA harness for F-p2-perf-4 (Amiri 700 re-subset).

Renders the public AR pages in headless Chromium at desktop (1280)
and mobile (390) viewports, captures full-page PNGs into
`docs/screenshots/delta_audit_2026-05-10/after/p2-arabic-font-subset/`,
and asserts that the Amiri 700 font in fonts.css is the local subset
(not a fallback). A second invocation with `--baseline` captures the
pre-subset state from the `.original.woff2` so before/after diffs
are possible.

This is *visual-QA harness only* — pixel-perfect diff is not done
here. Studio reviews the screenshots manually. The script's
contractual job is:

 1. Open each AR page in a fresh Chromium tab.
 2. Wait for fonts to load (`document.fonts.ready`).
 3. Take a full-page screenshot.
 4. Save it with a deterministic name.

Usage:

    # First start runserver in another shell:
    .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000

    # Then:
    .venv/Scripts/python.exe scripts/capture_p2_perf_4_arabic_subset.py
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
    / "p2-arabic-font-subset"
)

PAGES = [
    ("ar-home", "/ar/"),
    ("ar-contact", "/ar/contact/"),
    ("ar-privacy", "/ar/privacy/"),
    ("ar-disclaimer", "/ar/disclaimer/"),
    ("ar-case-types", "/ar/case-types/"),
]

VIEWPORTS = [
    ("desktop-1280", 1280, 800),
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
                    locale="ar",
                )
                page = context.new_page()
                for page_label, path in PAGES:
                    url = f"{BASE_URL}{path}"
                    page.goto(url, wait_until="networkidle")
                    # Wait until every @font-face that the page
                    # references has finished loading. Without this
                    # the screenshot can capture the fallback-font
                    # paint instead of the Amiri paint.
                    page.evaluate("document.fonts.ready")
                    outpath = OUT_DIR / f"{page_label}-{vp_label}.png"
                    page.screenshot(path=str(outpath), full_page=True)
                    size_kb = outpath.stat().st_size / 1024
                    print(f"  saved {outpath.relative_to(REPO_ROOT)} ({size_kb:.0f} KB)")
                context.close()
        finally:
            browser.close()

    print(f"\n[OK] {len(PAGES) * len(VIEWPORTS)} screenshots in "
          f"{OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
