"""Capture before/after screenshots for the local-CSS premium iter.

The "before" pass blocks the Tailwind CDN at the network level so the
shots reflect the broken-offline state the previous iters suffered.
The "after" pass blocks the same domain too — proving the local
stylesheet is enough to render the site without the CDN.

Usage::

    python scripts/capture_frontend_local_css_pass1.py before
    python scripts/capture_frontend_local_css_pass1.py after
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:48107"
OUTDIR_ROOT = (
    REPO_ROOT / "docs" / "screenshots" / "live_qa" / "frontend_local_css_premium_visual_qa_pass1"
)


# (label, locale_prefix, target_path, optional_post_payload)
DESKTOP = [
    ("home", "", "/", None),
    ("countries", "", "/countries/", None),
    ("countries_italy", "", "/countries/italy/", None),
    ("countries_morocco", "", "/countries/morocco/", None),
    ("wizard_start", "", "/wizard/", None),
    ("wizard_it_road_accident", "", "/wizard/it/road-accident/", None),
    ("wizard_ma_inheritance", "", "/wizard/ma/inheritance/", None),
    ("wizard_tn_inheritance", "", "/wizard/tn/inheritance/", None),
    ("contact", "", "/contact/", None),
    (
        "result_it_calculated",
        "",
        "/wizard/it/road-accident/",
        {
            "victim_age": "35",
            "permanent_disability_percentage": "10",
            "fault_percentage": "0",
            "consent_simulation": "on",
            "website": "",
        },
    ),
    (
        "result_ma_unavailable",
        "",
        "/wizard/ma/inheritance/",
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
            "estate_value": "800000",
            "consent_simulation": "on",
            "website": "",
        },
    ),
]

MOBILE = [
    ("home", "", "/", None),
    ("countries", "", "/countries/", None),
    ("wizard_start", "", "/wizard/", None),
    ("wizard_ma_inheritance", "", "/wizard/ma/inheritance/", None),
    (
        "result_ma_unavailable",
        "",
        "/wizard/ma/inheritance/",
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "sons_count": "1",
            "daughters_count": "1",
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


def run(phase: str) -> int:
    from playwright.sync_api import sync_playwright

    desktop_dir = OUTDIR_ROOT / phase / "desktop"
    mobile_dir = OUTDIR_ROOT / phase / "mobile"
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
                # Always block the CDN: we want the test to verify the
                # local CSS carries the layout in both phases. The
                # difference between phases is which `static/css/site.css`
                # is on disk (the "before" phase of this iter is the
                # repo state captured via git stash before authoring the
                # stylesheet — done out-of-band).
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

    if failures:
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("before", "after"))
    args = parser.parse_args()
    return run(args.phase)


if __name__ == "__main__":
    sys.exit(main())
