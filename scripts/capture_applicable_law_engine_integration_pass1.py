"""Capture AFTER screenshots for the applicable-law engine-integration iter.

Blocks ``cdn.tailwindcss.com`` so the shots prove the local
``static/css/site.css`` carries the layout. Both wizard fixtures and
post-redirect result pages are covered. The fixtures cover three POST
shapes:

- MA simple context (last residence MA, single-asset MA, no will) →
  result is still ``unavailable`` on the public DB (no APPROVED MA
  source) but the page renders the public message.
- MA cross-border context (assets MA + FR + IT) → result also
  unavailable; the public page is identical because the engine never
  ran.
- TN simple context (TN residence + TN assets) → same.

The script always blocks the CDN to verify offline rendering.
"""

from __future__ import annotations

import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:48107"
OUTDIR_ROOT = (
    REPO_ROOT / "docs" / "screenshots" / "live_qa" / "applicable_law_engine_integration_pass1"
)


DESKTOP = [
    ("wizard_ma_inheritance", "", "/wizard/ma/inheritance/", None),
    ("wizard_tn_inheritance", "", "/wizard/tn/inheritance/", None),
    (
        "result_ma_simple_post",
        "",
        "/wizard/ma/inheritance/",
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "assets_countries": "MA",
            "estate_value": "800000",
            "consent_simulation": "on",
            "website": "",
        },
    ),
    (
        "result_ma_cross_border_post",
        "",
        "/wizard/ma/inheritance/",
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "FR",
            "spouse_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "assets_countries": "MA, FR, IT",
            "estate_value": "800000",
            "consent_simulation": "on",
            "website": "",
        },
    ),
    (
        "result_tn_simple_post",
        "",
        "/wizard/tn/inheritance/",
        {
            "deceased_country_of_last_residence": "TN",
            "nationality": "TN",
            "spouse_present": "on",
            "mother_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "assets_countries": "TN",
            "estate_value": "1200000",
            "consent_simulation": "on",
            "website": "",
        },
    ),
    ("wizard_ma_inheritance_ar", "/ar", "/wizard/ma/inheritance/", None),
]

MOBILE = [
    ("wizard_ma_inheritance", "", "/wizard/ma/inheritance/", None),
    (
        "result_ma_post",
        "",
        "/wizard/ma/inheritance/",
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "FR",
            "spouse_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "assets_countries": "MA, FR",
            "estate_value": "800000",
            "consent_simulation": "on",
            "website": "",
        },
    ),
    ("wizard_ma_inheritance_ar", "/ar", "/wizard/ma/inheritance/", None),
]


def _shoot(page, target: str, payload: dict | None, out_path: Path) -> None:
    page.goto(target, wait_until="domcontentloaded", timeout=20_000)
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
        page.goto(result_url, wait_until="domcontentloaded", timeout=20_000)
    time.sleep(0.6)
    page.screenshot(path=str(out_path), full_page=True)


def main() -> int:
    from playwright.sync_api import sync_playwright

    desktop_dir = OUTDIR_ROOT / "after" / "desktop"
    mobile_dir = OUTDIR_ROOT / "after" / "mobile"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    mobile_dir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for variant, viewport, fixtures, out_dir in (
            ("desktop", {"width": 1440, "height": 900}, DESKTOP, desktop_dir),
            ("mobile", {"width": 375, "height": 800}, MOBILE, mobile_dir),
        ):
            for label, locale_prefix, path, payload in fixtures:
                ctx = browser.new_context(viewport=viewport)
                ctx.route("**/cdn.tailwindcss.com/**", lambda route: route.abort())
                page = ctx.new_page()
                target = BASE_URL + locale_prefix + path
                try:
                    out_path = out_dir / f"{label}.png"
                    _shoot(page, target, payload, out_path)
                    print(f"[ok] {variant}/{label} -> {out_path.relative_to(REPO_ROOT)}")
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{variant}/{label}: {exc}")
                    print(f"[FAIL] {variant}/{label}: {exc}", file=sys.stderr)
                finally:
                    ctx.close()
        browser.close()
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
