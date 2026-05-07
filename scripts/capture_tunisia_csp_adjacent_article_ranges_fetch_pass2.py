"""Capture screenshots for F-tunisia-csp-adjacent-article-ranges-fetch-pass2.

Verifies the public surface after the 6 adjacent CSP Livre IX pages
were fetched and the mapping draft was extended to 61 blocked rules.
TN public funnel must still produce
``unavailable_requires_legal_validation``; the result page must not
surface the new article snippets or the diagnostic. Tailwind CDN is
route-aborted to enforce the local-CSS-only baseline.
"""

from __future__ import annotations

import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:48113"
OUTDIR = (
    REPO_ROOT
    / "docs"
    / "screenshots"
    / "live_qa"
    / "tunisia_csp_adjacent_article_ranges_fetch_pass2"
)


TN_PAYLOAD = {
    "deceased_country_of_last_residence": "TN",
    "nationality": "TN",
    "spouse_present": "on",
    "surviving_spouse_gender": "wife",
    "sons_count": "1",
    "daughters_count": "1",
    "estate_value": "500000",
    "consent_simulation": "on",
    "website": "",
}


DESKTOP = [
    ("01_country_tunisia", "", "/countries/tunisia/", None),
    ("02_wizard_tn_inheritance", "", "/wizard/tn/inheritance/", None),
    ("03_result_tn_unavailable", "", "/wizard/tn/inheritance/", TN_PAYLOAD),
    ("04_wizard_tn_inheritance_ar", "/ar", "/wizard/tn/inheritance/", None),
    ("05_result_tn_unavailable_ar", "/ar", "/wizard/tn/inheritance/", TN_PAYLOAD),
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
                failures.append(f"desktop/{label}: {exc}")
                print(f"[FAIL] desktop/{label}: {exc}", file=sys.stderr)
            finally:
                ctx.close()
        browser.close()
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
