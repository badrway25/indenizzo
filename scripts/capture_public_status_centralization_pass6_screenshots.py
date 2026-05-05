"""Capture screenshots of the public site after public_status centralization.

Iter: F-product-public-status-centralization-pass6.

Output: docs/screenshots/live_qa/public_status_centralization_pass6/
"""

from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "public_status_centralization_pass6"
BASE_URL = "http://127.0.0.1:48107"

PAGES = [
    "/",
    "/countries/",
    "/countries/italy/",
    "/countries/france/",
    "/countries/belgium/",
    "/countries/morocco/",
    "/countries/tunisia/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/contact/",
]


def _slug(path: str) -> str:
    return (path.strip("/").replace("/", "_") or "home").replace("__", "_")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        for path in PAGES:
            try:
                page.goto(BASE_URL + path, wait_until="networkidle", timeout=20_000)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {path}: {exc}")
                continue
            out = OUTPUT_DIR / f"{_slug(path)}.png"
            page.screenshot(path=str(out), full_page=True)
            saved.append(out.name)
            print(f"  saved {out.relative_to(REPO_ROOT).as_posix()}")
        browser.close()

    print(f"\n[summary] saved {len(saved)} artefact(s) to {OUTPUT_DIR.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
