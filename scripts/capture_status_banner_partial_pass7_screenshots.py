"""Capture screenshots after the FR/BE/MA/TN status-banner partial wiring.

Iter origin: F-product-status-banner-partial-pass7.

Output: ``docs/screenshots/live_qa/status_banner_partial_pass7/``.

Captures:

- FR/BE/MA/TN wizards in default locale (IT) and i18n variants.
- Result-unavailable page reached via a real POST submission, for both
  France (road accident) and Morocco (international inheritance), so we
  can show that the unavailable card on the result page now uses the
  centralised ``public_status`` panel.
"""

from __future__ import annotations

import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "status_banner_partial_pass7"
BASE_URL = "http://127.0.0.1:48107"

# GET pages — landing forms.
GET_PAGES = [
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/fr/wizard/fr/road-accident/",
    "/ar/wizard/ma/inheritance/",
]

# POST submissions — capture the resulting "unavailable" page.
POST_FLOWS = [
    {
        "slug": "post_fr_result_unavailable",
        "form_url": "/wizard/fr/road-accident/",
        "fields": {
            "accident_country": "FR",
            "accident_date": "2024-06-15",
            "victim_age": "40",
            "permanent_disability_percentage": "12",
            "total_temporary_disability_days": "30",
            "partial_temporary_disability_days": "15",
            "medical_expenses": "1500",
            "lost_income": "3000",
            "fault_percentage": "0",
        },
        "consent_field": "consent_simulation",
    },
    {
        "slug": "post_ma_result_unavailable",
        "form_url": "/wizard/ma/inheritance/",
        "fields": {
            "deceased_country": "MA",
            "habitual_residence_country": "FR",
            "nationality": "MA",
            "has_will": "false",
            "spouse_exists": "true",
            "children_count": "2",
            "parents_alive": "1",
            "assets_countries": "MA, FR",
            "message": "Pass-7 screenshot fixture, not a real case.",
        },
        "consent_field": "consent_simulation",
    },
]


def _slug(path: str) -> str:
    return (path.strip("/").replace("/", "_") or "home").replace("__", "_")


def _csrf_from_html(html: str) -> str | None:
    m = re.search(
        r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']',
        html,
    )
    return m.group(1) if m else None


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # GET pages.
        for path in GET_PAGES:
            try:
                page.goto(BASE_URL + path, wait_until="networkidle", timeout=20_000)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {path}: {exc}")
                continue
            out = OUTPUT_DIR / f"{_slug(path)}.png"
            page.screenshot(path=str(out), full_page=True)
            saved.append(out.name)
            print(f"  saved {out.relative_to(REPO_ROOT).as_posix()}")

        # POST flows — submit the form and capture the resulting page.
        for flow in POST_FLOWS:
            url = BASE_URL + flow["form_url"]
            try:
                page.goto(url, wait_until="networkidle", timeout=20_000)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! GET {url}: {exc}")
                continue

            # Fill scalar fields that exist on the page.
            for name, value in flow["fields"].items():
                locator = page.locator(f'[name="{name}"]')
                if locator.count() == 0:
                    continue
                tag = locator.first.evaluate("el => el.tagName")
                if tag == "SELECT":
                    locator.first.select_option(value)
                else:
                    try:
                        locator.first.fill(value)
                    except Exception:  # noqa: BLE001
                        # CharField hidden input → use input_value.
                        locator.first.evaluate(f'el => {{ el.value = "{value}"; }}')

            # Always tick the consent box.
            consent = page.locator(f'[name="{flow["consent_field"]}"]')
            if consent.count() and consent.first.is_visible():
                consent.first.check()

            try:
                page.evaluate(
                    "() => {const b = document.querySelector('form button[type=submit]');"
                    " if (b) b.click();}"
                )
                page.wait_for_load_state("networkidle", timeout=20_000)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! POST {url}: {exc}")
                continue

            out = OUTPUT_DIR / f"{flow['slug']}.png"
            page.screenshot(path=str(out), full_page=True)
            saved.append(out.name)
            print(f"  saved {out.relative_to(REPO_ROOT).as_posix()}")

        browser.close()

    print(f"\n[summary] saved {len(saved)} artefact(s) to {OUTPUT_DIR.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
