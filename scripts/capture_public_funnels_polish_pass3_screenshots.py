"""Capture screenshots of the public funnels for pass-3 polish.

Iter: F-product-public-funnels-polish-pass3.

Steps captured (1 png per step, full page):

1. /wizard/ — start page with the new "How it works" 3-step section.
2. /wizard/it/road-accident/ — IT wizard with the new "After you submit"
   preview block.
3. POST IT 35/10/0 → /wizard/result/<uuid>/ — calculated result with
   the new "What this means" + "Next steps" sections.
4. PDF download URL — verified via HTTP fetch (saved as a small txt
   stub since the runtime browser doesn't directly screenshot PDFs).
5. /wizard/fr/road-accident/ — FR scaffold with the new banner.
6. POST FR (no estimate path) → /wizard/result/<uuid>/ — unavailable
   result with the new contact CTA.
7. /contact/ — contact form with the new return-paths nav.
8. POST contact valid → /contact/thank-you/ — thank-you page with the
   new "Back to the wizard" CTA.

Output: docs/screenshots/live_qa/public_funnels_polish_pass3/<step>.png

The script assumes ``http://127.0.0.1:48107/`` is live. It is read-only
on the legal/calculator layer (it submits real wizard forms which create
``Simulation`` rows; that is the only side effect, identical to a normal
site visit).
"""

from __future__ import annotations

import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "public_funnels_polish_pass3"
BASE_URL = "http://127.0.0.1:48107"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        def shoot(name: str) -> None:
            target = OUTPUT_DIR / f"{name}.png"
            page.screenshot(path=str(target), full_page=True)
            saved.append(name)
            print(f"  saved {target.relative_to(REPO_ROOT).as_posix()}")

        # Step 1: /wizard/
        page.goto(f"{BASE_URL}/wizard/", wait_until="networkidle")
        shoot("01_wizard_start")

        # Step 2: /wizard/it/road-accident/
        page.goto(f"{BASE_URL}/wizard/it/road-accident/", wait_until="networkidle")
        shoot("02_wizard_italy_form")

        # Step 3: POST IT 35/10/0
        page.fill('input[name="victim_age"]', "35")
        page.fill('input[name="permanent_disability_percentage"]', "10")
        page.fill('input[name="fault_percentage"]', "0")
        page.check('input[name="consent_simulation"]')
        page.click('button[type="submit"]')
        page.wait_for_url("**/wizard/result/**", timeout=30_000)
        page.wait_for_load_state("networkidle")
        shoot("03_wizard_italy_result")
        # Capture pdf URL from the page (button link is on the result page).
        pdf_link = page.locator("a[href*='/pdf']").first
        pdf_href = pdf_link.get_attribute("href") if pdf_link.count() else ""

        # Step 4: PDF — fetch via urllib so the test doesn't need a PDF
        # viewer; save first 4096 bytes as a sanity probe.
        if pdf_href:
            pdf_url = pdf_href if pdf_href.startswith("http") else f"{BASE_URL}{pdf_href}"
            try:
                with urllib.request.urlopen(pdf_url, timeout=30) as resp:
                    head = resp.read(4096)
                (OUTPUT_DIR / "04_wizard_italy_pdf.bin").write_bytes(head)
                magic = head[:5]
                print(f"  saved 04_wizard_italy_pdf.bin (head 4096B; magic={magic!r})")
                saved.append("04_wizard_italy_pdf")
            except Exception as exc:  # noqa: BLE001
                print(f"  pdf fetch failed: {exc}")

        # Step 5: /wizard/fr/road-accident/
        page.goto(f"{BASE_URL}/wizard/fr/road-accident/", wait_until="networkidle")
        shoot("05_wizard_france_form")

        # Step 6: POST FR
        page.fill('input[name="victim_age"]', "30")
        page.fill('input[name="permanent_disability_percentage"]', "5")
        page.fill('input[name="fault_percentage"]', "0")
        page.check('input[name="consent_simulation"]')
        page.click('button[type="submit"]')
        page.wait_for_url("**/wizard/result/**", timeout=30_000)
        page.wait_for_load_state("networkidle")
        shoot("06_wizard_france_result_unavailable")

        # Step 7: /contact/
        page.goto(f"{BASE_URL}/contact/", wait_until="networkidle")
        shoot("07_contact_form")

        # Step 8: POST contact valid
        page.fill('input[name="first_name"]', "Test")
        page.fill('input[name="last_name"]', "User")
        page.fill('input[name="email"]', "tester@example.com")
        # Country/case_type are optional ModelChoice fields — leave default
        # to avoid coupling the screenshot script to the FK/value mapping.
        page.select_option('select[name="case_type"]', "road_accident_bodily_injury")
        page.fill(
            'textarea[name="message"]',
            "This is a synthetic test message at least twenty characters long.",
        )
        page.check('input[name="privacy_accepted"]')
        page.click('button[type="submit"]')
        page.wait_for_url("**/contact/thank-you/**", timeout=30_000)
        page.wait_for_load_state("networkidle")
        shoot("08_contact_thank_you")

        browser.close()

    print(f"\n[summary] saved {len(saved)} artefact(s) to {OUTPUT_DIR.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
