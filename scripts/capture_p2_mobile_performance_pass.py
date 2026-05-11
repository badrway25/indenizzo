"""Capture browser screenshots for P2-PERF-1 mobile performance pass.

Iter: F-p2-perf-1-mobile-performance-pass.

Six captures — three viewport pairs (desktop + mobile) for the
URLs whose mobile perf moved the most:

- `/`           (LTR home, hero image, +0.06)
- `/ar/`        (RTL home, hero image, +0.01 — the bottleneck)
- `/countries/` (hub, +0.07)

Usage:

    python manage.py runserver 127.0.0.1:8000     # terminal A
    python scripts/capture_p2_mobile_performance_pass.py   # terminal B

Output lands in
``docs/screenshots/delta_audit_2026-05-10/after/p2-mobile-performance-pass/``.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8000"
OUT_DIR = (
    REPO_ROOT
    / "docs"
    / "screenshots"
    / "delta_audit_2026-05-10"
    / "after"
    / "p2-mobile-performance-pass"
)

TARGETS = [
    ("home_it_desktop", "desktop", "/"),
    ("home_it_mobile", "mobile", "/"),
    ("ar_home_desktop", "desktop", "/ar/"),
    ("ar_home_mobile", "mobile", "/ar/"),
    ("countries_desktop", "desktop", "/countries/"),
    ("countries_mobile", "mobile", "/countries/"),
]

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844},
}


def run() -> int:
    from playwright.sync_api import sync_playwright

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, viewport_label, path in TARGETS:
            ctx = browser.new_context(viewport=VIEWPORTS[viewport_label])
            page = ctx.new_page()
            target = BASE_URL + path
            try:
                page.goto(target, wait_until="networkidle", timeout=20_000)
                time.sleep(0.8)
                out_path = OUT_DIR / f"{label}.png"
                page.screenshot(path=str(out_path), full_page=True)
                print(f"[ok] {label} -> {out_path.relative_to(REPO_ROOT)}")
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{label}: {exc}")
                print(f"[FAIL] {label}: {exc}", file=sys.stderr)
            finally:
                ctx.close()
        browser.close()
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
