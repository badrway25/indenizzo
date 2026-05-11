"""
Tests F-p2-seo-1-lighthouse-mobile-baseline.

Static-side smoke tests for the mobile Lighthouse baseline. These
tests explicitly do NOT execute Lighthouse, do NOT spawn `npx`, and
do NOT hit the network. They pin the contract that the mobile
preset, runners, baseline and runbook all line up:

 1. lighthouserc.mobile.json exists and carries the mobile preset;
 2. the gated URL set matches the desktop preset (same indexable
    surface) and excludes the noindex wizards;
 3. mobile thresholds match what the runbook claims;
 4. both runner scripts exist (bash + PowerShell);
 5. each runner exposes the --update-baseline / -UpdateBaseline flag;
 6. each runner targets only the local dev server;
 7. each runner's URL list mirrors the JSON config;
 8. the consolidated quality gate exposes the --mobile-lighthouse
    opt-in (bash) and -MobileLighthouse (PowerShell);
 9. the baseline dir is populated with one JSON per URL + SUMMARY.md;
10. each baseline JSON carries a mobile configSettings.formFactor;
11. the runbook exists and references every moving piece;
12. .gitignore excludes the gitignored mobile scratch dirs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MOBILE_CONFIG = REPO_ROOT / "lighthouserc.mobile.json"
RUNNER_BASH = REPO_ROOT / "scripts" / "run_lighthouse_mobile_local.sh"
RUNNER_PS1 = REPO_ROOT / "scripts" / "run_lighthouse_mobile_local.ps1"
GATE_BASH = REPO_ROOT / "scripts" / "run_quality_gate.sh"
GATE_PS1 = REPO_ROOT / "scripts" / "run_quality_gate.ps1"
BASELINE_DIR = REPO_ROOT / "docs" / "qa" / "lighthouse-mobile-baseline"
BASELINE_SUMMARY = BASELINE_DIR / "SUMMARY.md"
RUNBOOK = REPO_ROOT / "docs" / "qa" / "LIGHTHOUSE_MOBILE_BASELINE.md"
GITIGNORE = REPO_ROOT / ".gitignore"

EXPECTED_PATHS = [
    "/",
    "/contact/",
    "/wizard/",
    "/privacy/",
    "/disclaimer/",
    "/countries/",
    "/case-types/",
    "/ar/",
]

EXPECTED_LABELS = {
    "home-it",
    "contact",
    "wizard",
    "privacy",
    "disclaimer",
    "countries",
    "case-types",
    "ar-home",
}


# ---------------------------------------------------------------------------
# 1. lighthouserc.mobile.json — preset + URLs + thresholds
# ---------------------------------------------------------------------------


def _config() -> dict:
    return json.loads(MOBILE_CONFIG.read_text(encoding="utf-8"))


def test_mobile_config_exists():
    assert MOBILE_CONFIG.exists()
    assert MOBILE_CONFIG.stat().st_size > 200


def test_mobile_config_uses_mobile_preset():
    settings = _config()["ci"]["collect"]["settings"]
    assert settings["formFactor"] == "mobile"
    assert settings["screenEmulation"]["mobile"] is True
    assert settings["screenEmulation"]["width"] == 390
    assert settings["screenEmulation"]["height"] == 844
    assert settings["throttling"]["cpuSlowdownMultiplier"] == 4


def test_mobile_config_gates_the_indexable_surface():
    urls = _config()["ci"]["collect"]["url"]
    paths = sorted(u.removeprefix("http://127.0.0.1:8000") for u in urls)
    assert paths == sorted(EXPECTED_PATHS)


def test_mobile_config_excludes_noindex_wizards():
    urls = _config()["ci"]["collect"]["url"]
    forbidden = ["/wizard/it/", "/wizard/fr/", "/wizard/result/", "/contact/thank-you"]
    for f in forbidden:
        assert not any(f in u for u in urls), f"noindex surface {f} in mobile gate"


def test_mobile_config_thresholds_match_runbook():
    assertions = _config()["ci"]["assert"]["assertions"]
    assert assertions["categories:performance"][1]["minScore"] == 0.75
    assert assertions["categories:accessibility"][1]["minScore"] == 0.90
    assert assertions["categories:best-practices"][1]["minScore"] == 0.90
    assert assertions["categories:seo"][1]["minScore"] == 0.90


def test_mobile_config_upload_dir_is_gitignored_scratch():
    upload = _config()["ci"]["upload"]
    assert upload["target"] == "filesystem"
    assert upload["outputDir"] == "./.lighthouseci-mobile"


# ---------------------------------------------------------------------------
# 2. Bash runner — exists, --update-baseline, only local URLs
# ---------------------------------------------------------------------------


def _bash_text() -> str:
    return RUNNER_BASH.read_text(encoding="utf-8")


def test_bash_runner_exists():
    assert RUNNER_BASH.exists()
    assert RUNNER_BASH.stat().st_size > 500


def test_bash_runner_exposes_update_baseline():
    text = _bash_text()
    assert "--update-baseline" in text
    assert "docs/qa/lighthouse-mobile-baseline" in text
    assert "artifacts/lighthouse-mobile/latest" in text


def test_bash_runner_carries_all_target_labels():
    text = _bash_text()
    for label in EXPECTED_LABELS:
        assert f'"{label}:' in text, f"label {label} missing from bash runner"


def test_bash_runner_mobile_emulation_flags_present():
    text = _bash_text()
    assert "--form-factor=mobile" in text
    assert "--screenEmulation.mobile=true" in text
    assert "--screenEmulation.width=390" in text
    assert "--screenEmulation.height=844" in text
    assert "--throttling.cpuSlowdownMultiplier=4" in text


# ---------------------------------------------------------------------------
# 3. PowerShell runner — exists, -UpdateBaseline switch
# ---------------------------------------------------------------------------


def _ps_text() -> str:
    return RUNNER_PS1.read_text(encoding="utf-8")


def test_ps_runner_exists():
    assert RUNNER_PS1.exists()
    assert RUNNER_PS1.stat().st_size > 500


def test_ps_runner_exposes_update_baseline_switch():
    text = _ps_text()
    assert "UpdateBaseline" in text
    assert "docs/qa/lighthouse-mobile-baseline" in text
    assert "artifacts/lighthouse-mobile/latest" in text


def test_ps_runner_mobile_emulation_flags_present():
    text = _ps_text()
    assert "--form-factor=mobile" in text
    assert "--screenEmulation.mobile=true" in text
    assert "--screenEmulation.width=390" in text
    assert "--screenEmulation.height=844" in text
    assert "--throttling.cpuSlowdownMultiplier=4" in text


# ---------------------------------------------------------------------------
# 4. No external URLs in either runner
# ---------------------------------------------------------------------------


_LOCAL_OK = re.compile(r"^https?://127\.0\.0\.1(?:[:/]|$)")
_ANY_HTTP = re.compile(r"https?://[\w.\-:]+")


def _http_targets(text: str) -> list[str]:
    return [m.group(0) for m in _ANY_HTTP.finditer(text)]


def test_bash_runner_has_no_external_http_targets():
    for url in _http_targets(_bash_text()):
        assert _LOCAL_OK.match(url), f"bash runner points at external URL: {url}"


def test_ps_runner_has_no_external_http_targets():
    for url in _http_targets(_ps_text()):
        assert _LOCAL_OK.match(url), f"ps1 runner points at external URL: {url}"


# ---------------------------------------------------------------------------
# 5. Consolidated quality gate exposes the opt-in mobile stage
# ---------------------------------------------------------------------------


def test_gate_bash_wires_mobile_lighthouse_flag():
    text = GATE_BASH.read_text(encoding="utf-8")
    assert "--mobile-lighthouse" in text
    assert "run_lighthouse_mobile_local.sh" in text


def test_gate_ps_wires_mobile_lighthouse_switch():
    text = GATE_PS1.read_text(encoding="utf-8")
    assert "MobileLighthouse" in text
    assert "run_lighthouse_mobile_local.ps1" in text


def test_gate_mobile_stage_is_optional_not_forced():
    bash_text = GATE_BASH.read_text(encoding="utf-8")
    ps_text = GATE_PS1.read_text(encoding="utf-8")
    assert "MOBILE_LIGHTHOUSE=0" in bash_text, (
        "mobile stage must default to off in bash gate"
    )
    assert re.search(r"\[switch\]\$MobileLighthouse", ps_text), (
        "mobile stage must be a [switch] (default off) in PowerShell gate"
    )


# ---------------------------------------------------------------------------
# 6. Baseline dir is populated
# ---------------------------------------------------------------------------


def test_baseline_dir_has_one_json_per_url():
    files = {p.name for p in BASELINE_DIR.glob("*-mobile.json")}
    expected = {f"{label}-mobile.json" for label in EXPECTED_LABELS}
    assert files == expected, f"baseline file set mismatch: {files} vs {expected}"


def test_baseline_summary_exists_and_lists_every_url():
    text = BASELINE_SUMMARY.read_text(encoding="utf-8")
    for path in EXPECTED_PATHS:
        assert f"`{path}`" in text, f"SUMMARY.md does not mention {path}"


def test_each_baseline_json_carries_mobile_form_factor():
    for path in BASELINE_DIR.glob("*-mobile.json"):
        report = json.loads(path.read_text(encoding="utf-8"))
        cfg = report.get("configSettings") or {}
        assert cfg.get("formFactor") == "mobile", (
            f"{path.name} configSettings.formFactor != 'mobile'"
        )


def test_each_baseline_json_clears_the_floor():
    """Sanity-check: the committed baseline itself respects the budget
    we just defined. If somebody commits a sub-floor JSON the gate is
    a lie."""
    assertions = _config()["ci"]["assert"]["assertions"]
    floors = {
        "performance": assertions["categories:performance"][1]["minScore"],
        "accessibility": assertions["categories:accessibility"][1]["minScore"],
        "best-practices": assertions["categories:best-practices"][1]["minScore"],
        "seo": assertions["categories:seo"][1]["minScore"],
    }
    for path in BASELINE_DIR.glob("*-mobile.json"):
        report = json.loads(path.read_text(encoding="utf-8"))
        cats = report.get("categories") or {}
        for name, floor in floors.items():
            score = (cats.get(name) or {}).get("score") or 0.0
            assert score >= floor, (
                f"{path.name} {name}={score:.2f} below committed floor {floor}"
            )


# ---------------------------------------------------------------------------
# 7. Runbook + .gitignore
# ---------------------------------------------------------------------------


def test_runbook_exists_and_references_every_moving_piece():
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "lighthouserc.mobile.json" in text
    assert "run_lighthouse_mobile_local.sh" in text
    assert "run_lighthouse_mobile_local.ps1" in text
    assert "docs/qa/lighthouse-mobile-baseline/" in text
    assert "--mobile-lighthouse" in text
    assert "MobileLighthouse" in text
    assert "--update-baseline" in text


def test_gitignore_excludes_mobile_scratch_dirs():
    text = GITIGNORE.read_text(encoding="utf-8")
    assert ".lighthouseci-mobile/" in text
    assert "artifacts/" in text
