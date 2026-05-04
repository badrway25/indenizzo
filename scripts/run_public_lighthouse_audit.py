"""Run a public-funnel performance / a11y / SEO audit.

Iter origin: F-product-lighthouse-visual-qa-pass1.
Extended in: F-perf-pass2-lighthouse-cli-and-ci-ready.

Strategy:

1. ``--mode auto`` (default): if a Lighthouse CLI is on PATH
   (``lighthouse`` or ``lhci``), use it; otherwise fall back to a
   structural Playwright probe.

2. ``--mode lighthouse``: force the lighthouse path. If the CLI is
   not on PATH, exit with code ``2`` and a clear error message rather
   than silently downgrading.

3. ``--mode playwright``: force the structural fallback even if the
   CLI is available (useful in CI where determinism matters more
   than full perf metrics).

The structural fallback enforces the rules from
``config/public_lighthouse_thresholds.json`` (HTTP 200, ``<title>``,
``<meta name="description">``, single ``<h1>``, no horizontal overflow
on a 375 × 800 mobile viewport, every ``<img>`` carries ``alt`` and
``width`` / ``height``, no Pexels-style "Photo by …" caption, no
API-key / token leak).

Output:

- ``<out-dir>/audit.json`` — raw audit (always written).
- ``<out-dir>/summary.md`` — markdown table (always written).
- ``<out-dir>/lighthouse/<slug>.{json,html}`` — per-URL lighthouse
  reports, only when the lighthouse path runs.

Default ``--out-dir`` is
``docs/reports/lighthouse/public_site_pass1`` to keep backward
compatibility with the pass-1 paths; pass-2 callers should specify
``--out-dir docs/reports/lighthouse/public_site_pass2``.

Exit codes:

- ``0`` — every required rule passes.
- ``1`` — at least one required rule failed (a11y/SEO/best-practices
  below threshold, or a structural fallback failure).
- ``2`` — configuration error (missing thresholds file, missing
  audited URLs, ``--mode lighthouse`` with no CLI on PATH, Playwright
  not installed).

The script is read-only on the legal / calculator layer (HTTP GETs
only) and never installs anything from the network.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
THRESHOLDS_PATH = REPO_ROOT / "config" / "public_lighthouse_thresholds.json"
DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "reports" / "lighthouse" / "public_site_pass1"
DEFAULT_BASE_URL = "http://127.0.0.1:48107"


# ---------------------------------------------------------------------------
# Lighthouse CLI path
# ---------------------------------------------------------------------------


def _find_lighthouse_cli() -> str | None:
    """Return a Lighthouse-compatible CLI command, or None if absent."""

    for candidate in ("lighthouse", "lhci"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def _run_lighthouse(
    cli: str, base_url: str, urls: list[str], out_dir: pathlib.Path
) -> dict[str, Any]:
    """Run the Lighthouse CLI for each URL.

    Returns a dict mapping URL → score dict. Failures (e.g. missing
    Chrome) are reported as ``{"error": "..."}`` rather than crashing
    the whole audit.
    """

    lh_dir = out_dir / "lighthouse"
    lh_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}
    for path in urls:
        target = base_url.rstrip("/") + path
        slug = path.strip("/").replace("/", "_") or "home"
        json_out = lh_dir / f"{slug}.json"
        html_out = lh_dir / f"{slug}.html"
        cmd = [
            cli,
            target,
            "--quiet",
            "--chrome-flags=--headless --no-sandbox",
            "--preset=desktop",
            "--output=json",
            "--output=html",
            f"--output-path={json_out.with_suffix('').as_posix()}",
            "--only-categories=performance,accessibility,best-practices,seo",
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            results[path] = {"error": str(exc)}
            continue
        if proc.returncode != 0 and not json_out.exists():
            results[path] = {
                "error": f"lighthouse exit={proc.returncode} stderr={proc.stderr[:200]}",
            }
            continue
        if json_out.exists():
            try:
                doc = json.loads(json_out.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                results[path] = {"error": f"could not parse {json_out.name}: {exc}"}
                continue
            cats = doc.get("categories", {})
            results[path] = {
                "performance": (cats.get("performance") or {}).get("score"),
                "accessibility": (cats.get("accessibility") or {}).get("score"),
                "best-practices": (cats.get("best-practices") or {}).get("score"),
                "seo": (cats.get("seo") or {}).get("score"),
                "json_report": json_out.relative_to(REPO_ROOT).as_posix(),
                "html_report": (
                    html_out.relative_to(REPO_ROOT).as_posix() if html_out.exists() else None
                ),
            }
        else:
            results[path] = {"error": "lighthouse produced no JSON output"}
    return results


# ---------------------------------------------------------------------------
# Playwright fallback (structural audit)
# ---------------------------------------------------------------------------


_PEXELS_NEEDLES = ("photo by ", "pexels.com")
_LEAK_NAMES = ("PEXELS_API_KEY", "STRIPE_SECRET", "SENDGRID_API_KEY")
_LONG_TOKEN = re.compile(r"[A-Za-z0-9]{40,}")


def fallback_check_page(html: str, viewport_width: int, body_overflow: int) -> dict[str, Any]:
    """Apply structural rules to a single page. Pure function, easy to test.

    ``body_overflow`` is the document's ``scrollWidth`` collected by
    Playwright; if it's > viewport_width we flag horizontal overflow.
    """

    failures: list[str] = []

    # 1. <title>
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not title_match or not title_match.group(1).strip():
        failures.append("title_missing_or_empty")

    # 2. <meta name="description">
    if not re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'][^"\']+["\']',
        html,
        flags=re.IGNORECASE,
    ):
        failures.append("meta_description_missing")

    # 3. exactly one <h1>
    h1_count = len(re.findall(r"<h1[\s>]", html))
    if h1_count != 1:
        failures.append(f"h1_count={h1_count}")

    # 4. images: alt + width/height
    for img in re.findall(r"<img\b[^>]*>", html, flags=re.IGNORECASE):
        # The decorative-image escape hatch: alt="" is OK as long as the
        # attribute is present.
        if not re.search(r'\balt\s*=\s*["\']', img, flags=re.IGNORECASE):
            failures.append("img_missing_alt")
            break
    for img in re.findall(r"<img\b[^>]*>", html, flags=re.IGNORECASE):
        has_w = re.search(r'\bwidth\s*=\s*["\']?\d', img, flags=re.IGNORECASE)
        has_h = re.search(r'\bheight\s*=\s*["\']?\d', img, flags=re.IGNORECASE)
        if not (has_w and has_h):
            failures.append("img_missing_dimensions")
            break

    # 5. no Pexels attribution
    lower = html.lower()
    for needle in _PEXELS_NEEDLES:
        if needle in lower:
            failures.append(f"pexels_attribution:{needle.strip()}")

    # 6. no API key / token leak
    for name in _LEAK_NAMES:
        if name in html:
            failures.append(f"env_var_leak:{name}")
    for match in _LONG_TOKEN.findall(html):
        for prefix in ("key=", "token=", "secret="):
            if prefix + match in html:
                failures.append(f"token_leak_after:{prefix}")
                break

    # 7. no horizontal overflow on mobile
    if body_overflow > viewport_width + 1:  # +1 px slack for sub-pixel rounding
        failures.append(f"horizontal_overflow:{body_overflow}>{viewport_width}")

    return {"failures": failures, "passed": not failures}


def _run_playwright_fallback(base_url: str, urls: list[str]) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "playwright not installed; cannot run fallback audit"}

    results: dict[str, Any] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Mobile viewport (iPhone 12 Pro logical width is 390; we use 375
        # to match the conservative "iPhone SE" lower bound).
        context = browser.new_context(viewport={"width": 375, "height": 800})
        page = context.new_page()

        for path in urls:
            target = base_url.rstrip("/") + path
            try:
                resp = page.goto(target, wait_until="networkidle", timeout=20_000)
            except Exception as exc:  # noqa: BLE001
                results[path] = {"failures": [f"navigation_error:{exc}"], "passed": False}
                continue

            status = resp.status if resp else 0
            if status != 200:
                results[path] = {"failures": [f"http_status:{status}"], "passed": False}
                continue

            html = page.content()
            body_overflow = int(page.evaluate("() => document.documentElement.scrollWidth"))
            verdict = fallback_check_page(html, viewport_width=375, body_overflow=body_overflow)
            results[path] = verdict

        browser.close()

    return results


# ---------------------------------------------------------------------------
# Verdict + report
# ---------------------------------------------------------------------------


def evaluate_lighthouse(scores: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    """Compare raw scores against thresholds; return a verdict dict."""

    failures: list[str] = []
    warnings: list[str] = []
    for category, rule in thresholds.get("lighthouse", {}).items():
        if category.startswith("_"):
            continue  # _doc keys etc.
        if not isinstance(rule, dict):
            continue
        score = scores.get(category)
        if score is None:
            warnings.append(f"{category}:missing")
            continue
        if score < rule["min"]:
            msg = f"{category}={score:.2f}<{rule['min']:.2f}"
            if rule.get("level") == "required":
                failures.append(msg)
            else:
                warnings.append(msg)
    return {"failures": failures, "warnings": warnings, "passed": not failures}


# ---------------------------------------------------------------------------
# Markdown report generator (used by the live run + by tests)
# ---------------------------------------------------------------------------


def render_markdown_report(report: dict[str, Any]) -> str:
    """Turn an audit JSON dict into a markdown table.

    Pure function — used from the live audit and from tests. Accepts
    both the lighthouse and the playwright_fallback shape.
    """

    lines = [
        "# Public funnel audit — pass 1",
        "",
        f"- tool: `{report.get('tool')}`",
        f"- base URL: `{report.get('base_url')}`",
        "",
    ]

    if report.get("tool") == "lighthouse":
        lines.extend(
            [
                "| URL | perf | a11y | best-pract. | SEO | Verdict |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for path, data in (report.get("urls") or {}).items():
            if "error" in data:
                lines.append(f"| `{path}` | — | — | — | — | error: {data['error']} |")
                continue
            lines.append(
                f"| `{path}` "
                f"| {_fmt(data.get('performance'))} "
                f"| {_fmt(data.get('accessibility'))} "
                f"| {_fmt(data.get('best-practices'))} "
                f"| {_fmt(data.get('seo'))} "
                f"| {'PASS' if data.get('passed') else 'FAIL'} |"
            )
    else:
        lines.extend(
            [
                "| URL | Verdict | Failures |",
                "| --- | --- | --- |",
            ]
        )
        for path, data in (report.get("urls") or {}).items():
            verdict = "PASS" if data.get("passed") else "FAIL"
            failures = ", ".join(data.get("failures") or []) or "—"
            lines.append(f"| `{path}` | {verdict} | {failures} |")

    if any(
        (data.get("warnings"))
        for data in (report.get("urls") or {}).values()
        if isinstance(data, dict)
    ):
        lines.append("")
        lines.append("## Warnings (informational, do not gate the audit)")
        lines.append("")
        for path, data in (report.get("urls") or {}).items():
            if not isinstance(data, dict):
                continue
            warnings = data.get("warnings") or []
            if warnings:
                lines.append(f"- `{path}`: {', '.join(warnings)}")

    return "\n".join(lines)


def _fmt(score: float | None) -> str:
    return "—" if score is None else f"{score:.2f}"


def _rel(path: pathlib.Path) -> str:
    """Best-effort relative-to-repo posix string; absolute fallback."""

    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help=(
            "Directory where audit.json + summary.md (and per-URL "
            "lighthouse reports) are written."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "lighthouse", "playwright"),
        default="auto",
        help=(
            "auto: lighthouse if available, else playwright fallback. "
            "lighthouse: require lighthouse on PATH (exit 2 otherwise). "
            "playwright: force the structural fallback."
        ),
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help=(
            "Promote warning-level threshold violations to failures. "
            "Off by default — performance scores are too host-dependent "
            "to gate CI on until the Lighthouse CLI version is pinned."
        ),
    )
    parser.add_argument(
        "--force-fallback",
        action="store_true",
        help="Deprecated alias for --mode playwright. Kept for pass-1 compatibility.",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help=(
            "Deprecated. Use --out-dir; this flag still works and writes a "
            "second copy of audit.json at the requested path."
        ),
    )
    args = parser.parse_args(argv)

    if not THRESHOLDS_PATH.exists():
        print(f"ERROR: thresholds file missing at {THRESHOLDS_PATH}", file=sys.stderr)
        return 2
    thresholds = json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))
    urls = thresholds.get("audited_urls", [])
    if not urls:
        print("ERROR: thresholds file has no audited_urls", file=sys.stderr)
        return 2

    out_dir = pathlib.Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (REPO_ROOT / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve mode.
    mode = "playwright" if args.force_fallback else args.mode
    cli: str | None = None
    if mode in {"auto", "lighthouse"}:
        cli = _find_lighthouse_cli()
    if mode == "lighthouse" and cli is None:
        print(
            "ERROR: --mode lighthouse requires a 'lighthouse' or 'lhci' binary on PATH; "
            "none was found. Install one or use --mode auto / playwright.",
            file=sys.stderr,
        )
        return 2

    if cli and mode != "playwright":
        print(f"[mode] lighthouse CLI at {cli}", file=sys.stderr)
        raw = _run_lighthouse(cli, args.base_url, urls, out_dir)
        per_url: dict[str, Any] = {}
        any_required_failure = False
        any_warning = False
        for path, scores in raw.items():
            if "error" in scores:
                per_url[path] = scores
                any_required_failure = True
                continue
            verdict = evaluate_lighthouse(scores, thresholds)
            per_url[path] = {**scores, **verdict}
            if not verdict["passed"]:
                any_required_failure = True
            if verdict.get("warnings"):
                any_warning = True
        report = {
            "tool": "lighthouse",
            "base_url": args.base_url,
            "urls": per_url,
            "report_dir": (out_dir / "lighthouse").relative_to(REPO_ROOT).as_posix(),
        }
    else:
        if mode == "auto":
            print(
                "[mode] lighthouse CLI not on PATH — running Playwright fallback audit",
                file=sys.stderr,
            )
        else:
            print("[mode] Playwright fallback audit (forced)", file=sys.stderr)
        raw = _run_playwright_fallback(args.base_url, urls)
        if "error" in raw:
            print(f"ERROR: {raw['error']}", file=sys.stderr)
            return 2
        any_required_failure = any(not v.get("passed", False) for v in raw.values())
        any_warning = False
        report = {
            "tool": "playwright_fallback",
            "base_url": args.base_url,
            "urls": raw,
        }

    # Persist audit.json + summary.md (always).
    audit_json_path = out_dir / "audit.json"
    summary_md_path = out_dir / "summary.md"
    audit_json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_md_path.write_text(render_markdown_report(report), encoding="utf-8")
    print(f"[report] {_rel(audit_json_path)}", file=sys.stderr)
    print(f"[summary] {_rel(summary_md_path)}", file=sys.stderr)

    # Backward compat: legacy --report-json copy.
    if args.report_json:
        legacy = pathlib.Path(args.report_json)
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[legacy-report] {legacy}", file=sys.stderr)

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if any_required_failure:
        print("\n[verdict] FAIL — at least one required rule failed.", file=sys.stderr)
        return 1
    if any_warning and args.fail_on_warning:
        print(
            "\n[verdict] FAIL (--fail-on-warning) — required rules pass but warnings present.",
            file=sys.stderr,
        )
        return 1
    print("\n[verdict] OK — every required rule passes.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
