"""Capture browser screenshots for P0-MVP-1 non-IT readiness audit.

Iter: F-p0-mvp-1-non-it-readiness.

Captures the public surface that the readiness doc references:

- /                          (homepage, for context)
- /countries/                (country hub)
- /countries/france/         (France landing — `legal_assessment` panel)
- /wizard/fr/road-accident/  (France wizard form)
- post-submit result page    (must surface review-pending, no EUR amount)
- /contact/                  (fallback CTA)
- /ar/                       (Arabic homepage — RTL regression)

Usage:

    python manage.py runserver 127.0.0.1:8000     # terminal A
    python scripts/capture_p0_non_it_mvp_readiness.py   # terminal B

The dev server must be reachable on 127.0.0.1:8000. Output lands in
``docs/screenshots/delta_audit_2026-05-10/after/p0-non-it-mvp-readiness/``.
"""

from __future__ import annotations

import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8000"
OUT_DIR = (
    REPO_ROOT
    / "docs"
    / "screenshots"
    / "delta_audit_2026-05-10"
    / "after"
    / "p0-non-it-mvp-readiness"
)

# (label, viewport_label, target_path, post_payload_or_None)
TARGETS = [
    ("home_it_desktop", "desktop", "/", None),
    ("countries_hub_desktop", "desktop", "/countries/", None),
    ("country_france_landing_desktop", "desktop", "/countries/france/", None),
    ("wizard_fr_road_accident_desktop", "desktop", "/wizard/fr/road-accident/", None),
    (
        "wizard_fr_post_review_gated_desktop",
        "desktop",
        "/wizard/fr/road-accident/",
        {
            "accident_country": "FR",
            "victim_age": "35",
            "permanent_disability_percentage": "10",
            "fault_percentage": "0",
            "consent_simulation": "on",
            "special_categories_consent": "on",
            "website": "",
        },
    ),
    ("contact_desktop", "desktop", "/contact/", None),
    ("ar_home_desktop", "desktop", "/ar/", None),
    ("wizard_fr_road_accident_mobile", "mobile", "/wizard/fr/road-accident/", None),
    ("country_france_landing_mobile", "mobile", "/countries/france/", None),
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
        for label, viewport_label, path, payload in TARGETS:
            ctx = browser.new_context(viewport=VIEWPORTS[viewport_label])
            page = ctx.new_page()
            target = BASE_URL + path
            try:
                page.goto(target, wait_until="domcontentloaded", timeout=20_000)
                if payload is not None:
                    csrf = page.evaluate(
                        """() => {
                            const forms = document.querySelectorAll('form[method="post"]');
                            for (const f of forms) {
                                if (f.action.includes('/i18n/')) continue;
                                const t = f.querySelector('input[name="csrfmiddlewaretoken"]');
                                if (t) return t.value;
                            }
                            return null;
                        }"""
                    )
                    if not csrf:
                        raise RuntimeError(f"no CSRF on {target}")
                    body = "&".join(
                        f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}"
                        for k, v in [("csrfmiddlewaretoken", csrf), *payload.items()]
                    )
                    result_url = page.evaluate(
                        """async (args) => {
                            const r = await fetch(args.url, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                                body: args.body,
                                credentials: 'include',
                                redirect: 'follow',
                            });
                            return r.url;
                        }""",
                        {"url": target, "body": body},
                    )
                    page.goto(result_url, wait_until="networkidle", timeout=20_000)
                else:
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
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
