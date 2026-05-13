"""
Staging-readiness browser QA — Playwright Chromium real browser.

Runs the 12-page smoke from `docs/go_live/STAGING_DEPLOY_GATE_2026-05-13.md`
section 9 against a running Django dev server (default
http://127.0.0.1:8777). Captures:

- Status code for each URL (via response listener).
- Page title.
- Console errors (filtered: severity >= "warning").
- Failed network requests (4xx/5xx, with focus on static assets).
- 6 mandatory screenshots: home desktop, wizard-IT desktop, wizard-IT
  mobile, result desktop, result mobile, /ar/ RTL desktop.
- Full E2E canary submission of /wizard/it/road-accident/ with the
  35/10/0 canary input and the two GDPR consents.
- Assertion that the result page renders 26268, 27353, 28439.

Usage:
    python scripts/staging_readiness_browser_qa.py [--base-url http://127.0.0.1:8777]
                                                   [--out docs/go_live/evidence/staging_readiness_2026-05-13]

Exit code 0 if every assertion passes; 1 otherwise. Writes a JSON
summary `results.json` plus the screenshots in the output directory.

Privacy:
- No personally identifiable real data is entered. Test values only.
- No secrets, cookies, or session IDs printed to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import (
    ConsoleMessage,
    Page,
    Request,
    Response,
    sync_playwright,
)

DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
MOBILE_VIEWPORT = {"width": 390, "height": 844}  # iPhone-ish


@dataclass
class PageResult:
    url: str
    label: str
    viewport: str
    status: int | None = None
    title: str = ""
    console_errors: list[str] = field(default_factory=list)
    failed_requests: list[dict] = field(default_factory=list)
    screenshot: str | None = None
    notes: list[str] = field(default_factory=list)
    ok: bool = True


def _attach_listeners(page: Page, result: PageResult) -> None:
    def _console(msg: ConsoleMessage) -> None:
        if msg.type in {"error", "warning"}:
            text = msg.text
            # Filter known noisy dev-only warnings we cannot fix here.
            if "Permissions-Policy" in text or "DevTools" in text:
                return
            result.console_errors.append(f"[{msg.type}] {text[:300]}")

    def _request_failed(req: Request) -> None:
        result.failed_requests.append(
            {
                "url": req.url,
                "method": req.method,
                "failure": (req.failure or "")[:200],
                "resource_type": req.resource_type,
            }
        )

    def _response(resp: Response) -> None:
        if 400 <= resp.status < 600:
            result.failed_requests.append(
                {
                    "url": resp.url,
                    "method": resp.request.method,
                    "status": resp.status,
                    "resource_type": resp.request.resource_type,
                }
            )

    page.on("console", _console)
    page.on("requestfailed", _request_failed)
    page.on("response", _response)


def visit(
    page: Page,
    url: str,
    label: str,
    viewport: str,
    screenshot_path: Path | None = None,
) -> PageResult:
    result = PageResult(url=url, label=label, viewport=viewport)
    _attach_listeners(page, result)
    try:
        response = page.goto(url, wait_until="networkidle", timeout=20000)
        result.status = response.status if response else None
        result.title = page.title()
        if screenshot_path:
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_path), full_page=True)
            result.screenshot = str(
                screenshot_path.relative_to(screenshot_path.parent.parent)
            )
    except Exception as exc:
        result.ok = False
        result.notes.append(f"navigation error: {exc}")
    if result.status != 200:
        result.ok = False
        result.notes.append(f"status {result.status} != 200")
    return result


def run_canary_e2e(page: Page, base_url: str, out_dir: Path) -> dict:
    """Submit the wizard with the 35/10/0 canary input and verify
    the result page shows 26268/27353/28439. Returns a dict with the
    result-page URL, the visible amounts, and pass/fail flags."""
    result: dict = {
        "step": "canary_e2e",
        "input": {
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
        "expected": {"min": 26268, "mid": 27353, "max": 28439},
        "result_url": None,
        "body_contains": {},
        "console_errors": [],
        "ok": True,
        "notes": [],
    }
    console_errors: list[str] = []

    def _console(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            console_errors.append(msg.text[:300])

    page.on("console", _console)
    try:
        page.goto(
            f"{base_url}/wizard/it/road-accident/",
            wait_until="networkidle",
            timeout=20000,
        )
        # Optional "Additional details" fields live inside <details>
        # (collapsed by default per F-product-3-wizard-mobile-ux). Open
        # the disclosure so Playwright sees fault_percentage as visible.
        page.evaluate(
            "document.querySelectorAll('details[data-product-3-optional-details]').forEach(d => d.open = true);"
        )
        # Locate input fields by name= attribute.
        page.fill('input[name="victim_age"]', "35")
        page.fill('input[name="permanent_disability_percentage"]', "10")
        page.fill('input[name="fault_percentage"]', "0")
        # Two GDPR checkboxes (consent art. 6 + art. 9).
        page.check('input[name="consent_simulation"]')
        page.check('input[name="special_categories_consent"]')
        # Honeypot stays empty (default).

        # Submit. Use the form's submit button — the wizard page renders
        # a single primary CTA. Wait for the result URL.
        page.click('button[type="submit"]')
        page.wait_for_url("**/wizard/result/**", timeout=20000)

        result["result_url"] = page.url
        body = page.content()
        for key, value in result["expected"].items():
            result["body_contains"][key] = str(value) in body
            if str(value) not in body:
                result["ok"] = False
                result["notes"].append(f"expected {value} not found in result body")

        # Screenshots desktop + mobile.
        desktop_path = out_dir / "05_result_desktop_canary.png"
        page.screenshot(path=str(desktop_path), full_page=True)

        page.set_viewport_size(MOBILE_VIEWPORT)
        mobile_path = out_dir / "06_result_mobile_canary.png"
        page.screenshot(path=str(mobile_path), full_page=True)

        result["screenshots"] = [str(desktop_path.name), str(mobile_path.name)]

    except Exception as exc:
        result["ok"] = False
        result["notes"].append(f"e2e error: {exc}")

    result["console_errors"] = console_errors
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8777")
    parser.add_argument(
        "--out",
        default="docs/go_live/evidence/staging_readiness_2026-05-13",
    )
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")

    # 12-page smoke matrix. Screenshots tagged with prefix 01..N so that
    # `ls -1` returns them in the right reading order.
    smoke = [
        ("01_home_desktop", "/", DESKTOP_VIEWPORT),
        (None, "/countries/", DESKTOP_VIEWPORT),
        (None, "/countries/italy/", DESKTOP_VIEWPORT),
        (None, "/wizard/", DESKTOP_VIEWPORT),
        ("02_wizard_it_desktop", "/wizard/it/road-accident/", DESKTOP_VIEWPORT),
        ("03_wizard_it_mobile", "/wizard/it/road-accident/", MOBILE_VIEWPORT),
        (None, "/contact/", DESKTOP_VIEWPORT),
        (None, "/privacy/", DESKTOP_VIEWPORT),
        (None, "/disclaimer/", DESKTOP_VIEWPORT),
        (None, "/fr/", DESKTOP_VIEWPORT),
        ("04_ar_rtl_desktop", "/ar/", DESKTOP_VIEWPORT),
        (None, "/healthz/", DESKTOP_VIEWPORT),
    ]

    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=DESKTOP_VIEWPORT,
            locale="it-IT",
            ignore_https_errors=True,
        )

        # 12-URL smoke.
        for shot_label, path, viewport in smoke:
            context.set_default_navigation_timeout(20000)
            page = context.new_page()
            page.set_viewport_size(viewport)
            shot_path = out_dir / f"{shot_label}.png" if shot_label else None
            r = visit(
                page,
                f"{base}{path}",
                label=shot_label or path,
                viewport=f"{viewport['width']}x{viewport['height']}",
                screenshot_path=shot_path,
            )
            results.append(r.__dict__)
            page.close()

        # Canary E2E on a fresh context (clean cookies).
        canary_context = browser.new_context(
            viewport=DESKTOP_VIEWPORT,
            locale="it-IT",
        )
        canary_page = canary_context.new_page()
        canary_result = run_canary_e2e(canary_page, base, out_dir)
        canary_page.close()
        canary_context.close()

        browser.close()

    summary = {
        "base_url": base,
        "out_dir": str(out_dir),
        "smoke": results,
        "canary": canary_result,
        "screenshots": sorted(p.name for p in out_dir.glob("*.png")),
    }

    summary_path = out_dir / "results.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Console output: short, no PII, no secrets.
    print(f"[OK] base={base}")
    print(f"[OK] out={out_dir}")
    print(f"[OK] smoke pages: {len(results)}")
    failed_smoke = [r for r in results if not r["ok"]]
    print(f"[{'OK' if not failed_smoke else 'FAIL'}] smoke failures: {len(failed_smoke)}")
    print(f"[{'OK' if canary_result['ok'] else 'FAIL'}] canary E2E")
    print(f"     canary result_url: {canary_result.get('result_url')}")
    print(f"     canary body contains: {canary_result.get('body_contains')}")
    print(f"[OK] screenshots: {len(summary['screenshots'])}")
    for shot in summary["screenshots"]:
        print(f"     {shot}")
    print(f"[OK] summary written to: {summary_path}")

    return 0 if (not failed_smoke and canary_result["ok"]) else 1


if __name__ == "__main__":
    sys.exit(main())
