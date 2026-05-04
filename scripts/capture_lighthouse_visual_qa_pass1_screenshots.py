"""Capture desktop + mobile full-page PNGs for the pass-1 lighthouse audit.

Iter: F-product-lighthouse-visual-qa-pass1.

Captures the 8 audited public URLs at:

- Desktop: 1280 × 900
- Mobile: 375 × 800

Output: docs/screenshots/live_qa/lighthouse_visual_qa_pass1/<slug>__<viewport>.png
"""

from __future__ import annotations

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
THRESHOLDS_PATH = REPO_ROOT / "config" / "public_lighthouse_thresholds.json"
OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "lighthouse_visual_qa_pass1"
BASE_URL = "http://127.0.0.1:48107"


def _slug(path: str) -> str:
    s = path.strip("/").replace("/", "_")
    return s or "home"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    urls = json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))["audited_urls"]
    saved: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        for viewport_name, vp in (
            ("desktop", {"width": 1280, "height": 900}),
            ("mobile", {"width": 375, "height": 800}),
        ):
            context = browser.new_context(viewport=vp)
            page = context.new_page()
            for path in urls:
                target = BASE_URL.rstrip("/") + path
                try:
                    page.goto(target, wait_until="networkidle", timeout=20_000)
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! {path} ({viewport_name}): {exc}")
                    continue
                out = OUTPUT_DIR / f"{_slug(path)}__{viewport_name}.png"
                page.screenshot(path=str(out), full_page=True)
                saved.append(out.name)
                print(f"  saved {out.relative_to(REPO_ROOT).as_posix()}")
            context.close()

        browser.close()

    print(f"\n[summary] saved {len(saved)} artefact(s) to {OUTPUT_DIR.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
