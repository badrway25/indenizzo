"""
Tests F-p1-qa-1-quality-gate.

These are *static-side* smoke tests for the consolidated gate
wrapper. They explicitly do NOT execute pytest-inside-pytest, do
NOT start Lighthouse, and do NOT hit the network. They just pin
the contract:

1. both wrapper scripts exist (bash + PowerShell);
2. the bash wrapper references all four expected stages;
3. the bash wrapper auto-activates the project venv;
4. the bash wrapper exposes the documented flags;
5. the PowerShell wrapper references all four stages;
6. the PowerShell wrapper exposes the documented switches;
7. the runbook references both wrappers;
8. the runbook references each underlying tool;
9. neither wrapper points at an external URL (the only HTTP target
   is `127.0.0.1:8000`, the local Django dev server).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_BASH = REPO_ROOT / "scripts" / "run_quality_gate.sh"
GATE_PS1 = REPO_ROOT / "scripts" / "run_quality_gate.ps1"
RUNBOOK = REPO_ROOT / "docs" / "qa" / "LOCAL_QUALITY_GATE.md"


# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------


def test_gate_bash_wrapper_exists():
    assert GATE_BASH.exists()
    assert GATE_BASH.stat().st_size > 200


def test_gate_powershell_wrapper_exists():
    assert GATE_PS1.exists()
    assert GATE_PS1.stat().st_size > 200


# ---------------------------------------------------------------------------
# Bash wrapper: stages + venv auto-activation + flags
# ---------------------------------------------------------------------------


def _bash_text() -> str:
    return GATE_BASH.read_text(encoding="utf-8")


def test_bash_runs_all_four_stages():
    text = _bash_text()
    assert "manage.py check" in text
    assert "pytest -q" in text
    assert "audit_legal_content_hygiene.py --strict" in text
    assert "run_lighthouse_local.sh" in text


def test_bash_auto_activates_venv():
    text = _bash_text()
    assert ".venv/Scripts/activate" in text or ".venv/bin/activate" in text
    assert "VIRTUAL_ENV" in text


def test_bash_exposes_documented_flags():
    text = _bash_text()
    assert "--no-lighthouse" in text
    assert "--no-pytest" in text
    assert "--help" in text


# ---------------------------------------------------------------------------
# PowerShell wrapper: stages + switches
# ---------------------------------------------------------------------------


def _ps_text() -> str:
    return GATE_PS1.read_text(encoding="utf-8")


def test_ps_runs_all_four_stages():
    text = _ps_text()
    assert "manage.py check" in text
    assert "pytest -q" in text
    assert "audit_legal_content_hygiene.py --strict" in text
    assert "run_lighthouse_local.ps1" in text


def test_ps_exposes_documented_switches():
    text = _ps_text()
    assert "NoLighthouse" in text
    assert "NoPytest" in text


# ---------------------------------------------------------------------------
# Runbook references each wrapper + each underlying tool
# ---------------------------------------------------------------------------


def test_runbook_references_both_wrappers():
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "run_quality_gate.sh" in text
    assert "run_quality_gate.ps1" in text


def test_runbook_references_each_underlying_tool():
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "manage.py check" in text
    assert "pytest" in text
    assert "audit_legal_content_hygiene.py" in text
    assert "run_lighthouse_local" in text


# ---------------------------------------------------------------------------
# No external URLs in either wrapper (the only HTTP target is
# 127.0.0.1:8000, the local dev server).
# ---------------------------------------------------------------------------


_LOCAL_OK = re.compile(r"^https?://127\.0\.0\.1(?:[:/]|$)")
_ANY_HTTP = re.compile(r"https?://[\w.\-:]+")


def _http_targets(text: str) -> list[str]:
    return [m.group(0) for m in _ANY_HTTP.finditer(text)]


def test_bash_has_no_external_http_targets():
    text = _bash_text()
    for url in _http_targets(text):
        assert _LOCAL_OK.match(url), f"bash wrapper points at external URL: {url}"


def test_ps_has_no_external_http_targets():
    text = _ps_text()
    for url in _http_targets(text):
        assert _LOCAL_OK.match(url), f"ps1 wrapper points at external URL: {url}"
