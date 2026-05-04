"""Capture full-page screenshots of the polished public site (pass 5).

Iter: F-product-public-site-release-polish-pass5-premium-content-cleanup.

Output: docs/screenshots/live_qa/public_release_polish_pass5/

Captures three sets:

- Desktop 1440 × 900: home, countries, country FR, country MA,
  wizard start, wizard IT, wizard FR, contact.
- Mobile 375 × 800: home, countries, wizard start, wizard IT,
  wizard FR, contact.
- Locale variants: /fr/, /fr/countries/france/, /fr/wizard/, /ar/,
  /ar/countries/morocco/, /ar/wizard/.

Read-only — only HTTP GETs, no DB writes.
"""

from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "public_release_polish_pass5"
BASE_URL = "http://127.0.0.1:48107"


DESKTOP_PAGES = [
    "/",
    "/countries/",
    "/countries/france/",
    "/countries/morocco/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/contact/",
]

MOBILE_PAGES = [
    "/",
    "/countries/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/contact/",
]

LOCALE_PAGES = [
    "/fr/",
    "/fr/countries/france/",
    "/fr/wizard/",
    "/ar/",
    "/ar/countries/morocco/",
    "/ar/wizard/",
]


def _slug(path: str) -> str:
    return (path.strip("/").replace("/", "_") or "home").replace("__", "_")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Desktop 1440 × 900.
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        for path in DESKTOP_PAGES:
            try:
                page.goto(BASE_URL + path, wait_until="networkidle", timeout=20_000)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {path} desktop: {exc}")
                continue
            out = OUTPUT_DIR / f"desktop__{_slug(path)}.png"
            page.screenshot(path=str(out), full_page=True)
            saved.append(out.name)
            print(f"  saved {out.relative_to(REPO_ROOT).as_posix()}")
        ctx.close()

        # Mobile 375 × 800.
        ctx = browser.new_context(viewport={"width": 375, "height": 800})
        page = ctx.new_page()
        for path in MOBILE_PAGES:
            try:
                page.goto(BASE_URL + path, wait_until="networkidle", timeout=20_000)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {path} mobile: {exc}")
                continue
            out = OUTPUT_DIR / f"mobile__{_slug(path)}.png"
            page.screenshot(path=str(out), full_page=True)
            saved.append(out.name)
            print(f"  saved {out.relative_to(REPO_ROOT).as_posix()}")
        ctx.close()

        # Locale variants on desktop 1280 × 900.
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        for path in LOCALE_PAGES:
            try:
                page.goto(BASE_URL + path, wait_until="networkidle", timeout=20_000)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {path} locale: {exc}")
                continue
            out = OUTPUT_DIR / f"locale__{_slug(path)}.png"
            page.screenshot(path=str(out), full_page=True)
            saved.append(out.name)
            print(f"  saved {out.relative_to(REPO_ROOT).as_posix()}")
        ctx.close()

        browser.close()

    print(f"\n[summary] saved {len(saved)} artefact(s) to {OUTPUT_DIR.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
