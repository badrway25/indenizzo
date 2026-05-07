"""Capture screenshots for F-inheritance-wizard-spouse-gender-pass2.

Verifies the public surface after the MA / TN inheritance wizard
gained a ``surviving_spouse_gender`` field gated behind the spouse
checkbox. The calculator stays
``unavailable_requires_legal_validation`` and no automatic shares
surface. Tailwind CDN is route-aborted to enforce the
local-CSS-only baseline.

Capture matrix:

* Desktop, IT/FR/AR locales
  - 01 wizard MA, spouse not ticked → gender block hidden
  - 02 wizard MA, spouse ticked + wife selected → gender block visible
  - 03 wizard MA, spouse ticked + no gender selected → POST → form
       error visible
  - 04 wizard TN equivalent
  - 05 result MA unavailable (POST with valid gender)

* Mobile (iPhone-ish viewport), one IT pass through the wizard +
  result for layout regression.
"""

from __future__ import annotations

import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:48109"
OUTDIR = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "inheritance_wizard_spouse_gender_pass2"


VALID_PAYLOAD = {
    "deceased_country_of_last_residence": "MA",
    "nationality": "MA",
    "spouse_present": "on",
    "surviving_spouse_gender": "wife",
    "sons_count": "1",
    "daughters_count": "1",
    "estate_value": "800000",
    "consent_simulation": "on",
    "website": "",
}

INVALID_PAYLOAD_NO_GENDER = {
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
    ("01_wizard_ma_no_spouse", "", "/wizard/ma/inheritance/", None, None),
    (
        "02_wizard_ma_spouse_wife",
        "",
        "/wizard/ma/inheritance/",
        None,
        {"check_spouse": True, "select_gender": "wife"},
    ),
    (
        "03_wizard_ma_post_missing_gender",
        "",
        "/wizard/ma/inheritance/",
        INVALID_PAYLOAD_NO_GENDER,
        None,
    ),
    (
        "04_result_ma_unavailable_with_gender",
        "",
        "/wizard/ma/inheritance/",
        VALID_PAYLOAD,
        None,
    ),
    ("05_wizard_tn_no_spouse", "", "/wizard/tn/inheritance/", None, None),
    (
        "06_wizard_tn_spouse_husband",
        "",
        "/wizard/tn/inheritance/",
        None,
        {"check_spouse": True, "select_gender": "husband"},
    ),
    ("07_wizard_ma_no_spouse_fr", "/fr", "/wizard/ma/inheritance/", None, None),
    (
        "08_wizard_ma_spouse_wife_fr",
        "/fr",
        "/wizard/ma/inheritance/",
        None,
        {"check_spouse": True, "select_gender": "wife"},
    ),
    ("09_wizard_ma_no_spouse_ar", "/ar", "/wizard/ma/inheritance/", None, None),
    (
        "10_wizard_ma_spouse_wife_ar",
        "/ar",
        "/wizard/ma/inheritance/",
        None,
        {"check_spouse": True, "select_gender": "wife"},
    ),
]


MOBILE = [
    ("m01_wizard_ma_no_spouse", "", "/wizard/ma/inheritance/", None, None),
    (
        "m02_wizard_ma_spouse_wife",
        "",
        "/wizard/ma/inheritance/",
        None,
        {"check_spouse": True, "select_gender": "wife"},
    ),
    (
        "m03_result_ma_unavailable_with_gender",
        "",
        "/wizard/ma/inheritance/",
        VALID_PAYLOAD,
        None,
    ),
]


def _shoot(page, target: str, payload: dict | None, interact: dict | None, out_path: Path) -> str:
    page.goto(target, wait_until="networkidle", timeout=30_000)
    if interact:
        if interact.get("check_spouse"):
            page.evaluate("""() => {
                    const el = document.querySelector('input[name="spouse_present"]');
                    if (el) {
                        el.checked = true;
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }""")
        gender = interact.get("select_gender")
        if gender:
            page.evaluate(
                """(g) => {
                    const el = document.querySelector(
                        'input[name="surviving_spouse_gender"][value="' + g + '"]'
                    );
                    if (el) {
                        el.checked = true;
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }""",
                gender,
            )
        time.sleep(0.4)
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
    mobile_dir = OUTDIR / "after" / "mobile"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    mobile_dir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for label, locale_prefix, path, payload, interact in DESKTOP:
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            ctx.route("**/cdn.tailwindcss.com/**", lambda route: route.abort())
            page = ctx.new_page()
            target = BASE_URL + locale_prefix + path
            try:
                out_path = desktop_dir / f"{label}.png"
                _shoot(page, target, payload, interact, out_path)
                print(f"[ok] desktop/{label} -> {out_path.relative_to(REPO_ROOT)}")
            except Exception as exc:  # noqa: BLE001
                failures.append(f"desktop/{label}: {exc}")
                print(f"[FAIL] desktop/{label}: {exc}", file=sys.stderr)
            finally:
                ctx.close()

        for label, locale_prefix, path, payload, interact in MOBILE:
            ctx = browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=2,
            )
            ctx.route("**/cdn.tailwindcss.com/**", lambda route: route.abort())
            page = ctx.new_page()
            target = BASE_URL + locale_prefix + path
            try:
                out_path = mobile_dir / f"{label}.png"
                _shoot(page, target, payload, interact, out_path)
                print(f"[ok] mobile/{label} -> {out_path.relative_to(REPO_ROOT)}")
            except Exception as exc:  # noqa: BLE001
                failures.append(f"mobile/{label}: {exc}")
                print(f"[FAIL] mobile/{label}: {exc}", file=sys.stderr)
            finally:
                ctx.close()
        browser.close()
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
