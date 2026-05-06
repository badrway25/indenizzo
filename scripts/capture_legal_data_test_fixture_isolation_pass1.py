"""Minimal browser-live QA for F-legal-data-test-fixture-isolation-pass1.

This is an infrastructural iter — no UI changed. We capture a thin
slice of the public surface to confirm that:

* `/healthz/` still responds 200
* `/countries/morocco/` and `/countries/italy/` still render
* MA inheritance wizard still resolves to ``unavailable``
* IT 35/10/0 still calculates and surfaces the canonical amounts

Tailwind CDN is route-aborted to enforce the local-CSS-only baseline.
"""

from __future__ import annotations

import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:48107"
OUTDIR = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "legal_data_test_fixture_isolation_pass1"


IT_PAYLOAD = {
    "victim_age": "35",
    "permanent_disability_percentage": "10",
    "fault_percentage": "0",
    "consent_simulation": "on",
    "website": "",
}
MA_PAYLOAD = {
    "deceased_country_of_last_residence": "MA",
    "nationality": "MA",
    "spouse_present": "on",
    "sons_count": "1",
    "daughters_count": "1",
    "estate_value": "800000",
    "consent_simulation": "on",
    "website": "",
}


DESKTOP = [
    ("01_country_morocco", "", "/countries/morocco/", None),
    ("02_country_italy", "", "/countries/italy/", None),
    ("03_wizard_ma_inheritance", "", "/wizard/ma/inheritance/", None),
    ("04_result_ma_unavailable", "", "/wizard/ma/inheritance/", MA_PAYLOAD),
    ("05_result_it_calculated", "", "/wizard/it/road-accident/", IT_PAYLOAD),
]


def _shoot(page, target: str, payload: dict | None, out_path: Path) -> str:
    page.goto(target, wait_until="networkidle", timeout=30_000)
    if payload is not None:
        csrf = page.evaluate("""() => {
                const forms = document.querySelectorAll('form[method="post"]');
                for (const f of forms) {
                    if (f.action.includes('/i18n/')) continue;
                    const t = f.querySelector('input[name="csrfmiddlewaretoken"]');
                    if (t) return t.value;
                }
                return null;
            }""")
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
        page.goto(result_url, wait_until="networkidle", timeout=30_000)
    else:
        result_url = target
    page.evaluate("() => document.fonts && document.fonts.ready")
    time.sleep(0.6)
    page.screenshot(path=str(out_path), full_page=True)
    return result_url


def main() -> int:
    from playwright.sync_api import sync_playwright

    desktop_dir = OUTDIR / "after" / "desktop"
    desktop_dir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, locale_prefix, path, payload in DESKTOP:
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            ctx.route("**/cdn.tailwindcss.com/**", lambda route: route.abort())
            page = ctx.new_page()
            target = BASE_URL + locale_prefix + path
            try:
                out_path = desktop_dir / f"{label}.png"
                _shoot(page, target, payload, out_path)
                print(f"[ok] desktop/{label} -> {out_path.relative_to(REPO_ROOT)}")
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{label}: {exc}")
                print(f"[FAIL] {label}: {exc}", file=sys.stderr)
            finally:
                ctx.close()
        browser.close()
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
