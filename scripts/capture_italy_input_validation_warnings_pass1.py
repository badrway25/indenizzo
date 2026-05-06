"""Capture screenshots for F-italy-input-validation-warnings-pass1.

Exercises two diagnostic-routed input-validation paths:

* Required input missing (no ``victim_age`` in payload)
* Out-of-range fault percentage (``fault_percentage=150``)

For each path we render the result page in IT/FR/AR via the locale
prefix, plus the IT-only "calculated" 35/10/0 baseline as a sanity
check that no estimate-side regression slipped in.

Blocks ``cdn.tailwindcss.com`` to verify the local CSS still carries
the layout. The PDF probe re-confirms the 35/10/0 result still serves
``%PDF``.
"""

from __future__ import annotations

import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:48107"
OUTDIR_ROOT = (
    REPO_ROOT / "docs" / "screenshots" / "live_qa" / "italy_input_validation_warnings_pass1"
)


# 35 / 10 / 0 baseline — must keep producing 26 268 / 27 353 / 28 439 EUR.
IT_BASELINE_PAYLOAD = {
    "victim_age": "35",
    "permanent_disability_percentage": "10",
    "fault_percentage": "0",
    "consent_simulation": "on",
    "website": "",
}

# Required input missing: omit victim_age.
IT_MISSING_INPUT_PAYLOAD = {
    "permanent_disability_percentage": "10",
    "fault_percentage": "0",
    "consent_simulation": "on",
    "website": "",
}

# Fault percentage out of range.
IT_FAULT_OUT_OF_RANGE_PAYLOAD = {
    "victim_age": "35",
    "permanent_disability_percentage": "10",
    "fault_percentage": "150",
    "consent_simulation": "on",
    "website": "",
}

DESKTOP = [
    ("01_wizard_it_road_accident", "", "/wizard/it/road-accident/", None),
    ("02_wizard_fr_road_accident", "/fr", "/wizard/it/road-accident/", None),
    ("03_wizard_ar_road_accident", "/ar", "/wizard/it/road-accident/", None),
    ("04_result_it_baseline_calculated", "", "/wizard/it/road-accident/", IT_BASELINE_PAYLOAD),
    (
        "05_result_it_missing_input",
        "",
        "/wizard/it/road-accident/",
        IT_MISSING_INPUT_PAYLOAD,
    ),
    (
        "06_result_fr_missing_input",
        "/fr",
        "/wizard/it/road-accident/",
        IT_MISSING_INPUT_PAYLOAD,
    ),
    (
        "07_result_ar_missing_input",
        "/ar",
        "/wizard/it/road-accident/",
        IT_MISSING_INPUT_PAYLOAD,
    ),
    (
        "08_result_it_fault_out_of_range",
        "",
        "/wizard/it/road-accident/",
        IT_FAULT_OUT_OF_RANGE_PAYLOAD,
    ),
]

MOBILE = [
    ("01_wizard_it_road_accident", "", "/wizard/it/road-accident/", None),
    (
        "02_result_it_missing_input",
        "",
        "/wizard/it/road-accident/",
        IT_MISSING_INPUT_PAYLOAD,
    ),
    (
        "03_result_fr_missing_input",
        "/fr",
        "/wizard/it/road-accident/",
        IT_MISSING_INPUT_PAYLOAD,
    ),
    (
        "04_result_it_fault_out_of_range",
        "",
        "/wizard/it/road-accident/",
        IT_FAULT_OUT_OF_RANGE_PAYLOAD,
    ),
]


def _shoot(page, target: str, payload: dict | None, out_path: Path) -> str:
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
    else:
        result_url = target
    time.sleep(0.6)
    page.screenshot(path=str(out_path), full_page=True)
    return result_url


def main() -> int:
    from playwright.sync_api import sync_playwright

    desktop_dir = OUTDIR_ROOT / "after" / "desktop"
    mobile_dir = OUTDIR_ROOT / "after" / "mobile"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    mobile_dir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    baseline_result_url: str | None = None
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
                    final_url = _shoot(page, target, payload, out_path)
                    if variant == "desktop" and label == "04_result_it_baseline_calculated":
                        baseline_result_url = final_url
                    print(f"[ok] {variant}/{label} -> {out_path.relative_to(REPO_ROOT)}")
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{variant}/{label}: {exc}")
                    print(f"[FAIL] {variant}/{label}: {exc}", file=sys.stderr)
                finally:
                    ctx.close()

        # PDF probe — re-confirm 35/10/0 IT baseline still serves %PDF.
        if baseline_result_url and "/wizard/result/" in baseline_result_url:
            sim_uuid = baseline_result_url.rstrip("/").split("/")[-1]
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            try:
                pdf_url = BASE_URL + f"/reports/simulation/{sim_uuid}/pdf/"
                resp = page.goto(pdf_url)
                if resp and resp.status == 200:
                    raw = resp.body()
                    pdf_probe = OUTDIR_ROOT / "after" / "it_baseline_pdf_probe.bin"
                    pdf_probe.parent.mkdir(parents=True, exist_ok=True)
                    pdf_probe.write_bytes(raw[:4096])
                    print(
                        f"[ok] pdf-probe -> {pdf_probe.relative_to(REPO_ROOT)} "
                        f"(first 4 bytes: {raw[:4]!r})"
                    )
                else:
                    print(f"[warn] PDF probe status: " f"{resp.status if resp else 'no response'}")
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] PDF probe failed: {exc}", file=sys.stderr)
            finally:
                ctx.close()
        browser.close()
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
