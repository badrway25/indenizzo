"""
Tests F-p2-ci-2-branch-protection.

Static-side smoke tests for the branch-protection documentation +
dry-run scripts. They do NOT call `gh`, do NOT hit GitHub, and do
NOT execute the scripts in apply mode. They pin the contract that:

 1. docs/qa/GITHUB_BRANCH_PROTECTION.md exists and references
    every moving piece (branches, required checks, both scripts);
 2. dry-run scripts exist for bash + PowerShell;
 3. scripts refuse to apply without both --apply / -Apply AND
    --yes-i-understand / -YesIUnderstand;
 4. scripts contain no real tokens / no real webhook URLs;
 5. GO_LIVE_GATE_CHECKLIST.md has a branch-protection section;
 6. CI_QUALITY_GATE.md cross-references the new runbook.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = REPO_ROOT / "docs" / "qa" / "GITHUB_BRANCH_PROTECTION.md"
SCRIPT_BASH = REPO_ROOT / "scripts" / "github" / "branch_protection_plan.sh"
SCRIPT_PS1 = REPO_ROOT / "scripts" / "github" / "branch_protection_plan.ps1"
GO_LIVE = REPO_ROOT / "docs" / "GO_LIVE_GATE_CHECKLIST.md"
CI_RUNBOOK = REPO_ROOT / "docs" / "qa" / "CI_QUALITY_GATE.md"


# ---------------------------------------------------------------------------
# 1. Runbook exists and references every moving piece
# ---------------------------------------------------------------------------


def _runbook() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def test_runbook_exists():
    assert RUNBOOK.exists()
    assert RUNBOOK.stat().st_size > 1000


def test_runbook_names_both_protected_branches():
    text = _runbook()
    assert "main" in text
    assert "audit/indennizzati-platform" in text


def test_runbook_lists_every_required_check():
    text = _runbook()
    assert "python-tests" in text
    assert "production-checks" in text
    assert "lighthouse-desktop" in text
    # Mobile is explicitly NOT required and must be called out as such.
    assert "lighthouse-mobile" in text


def test_runbook_documents_both_rule_modes():
    text = _runbook()
    assert "Branch Protection" in text
    assert "Ruleset" in text


def test_runbook_documents_no_ff_vs_linear_history_decision():
    text = _runbook()
    # The project uses --no-ff merges. The runbook must explain why
    # `linear history` is OFF.
    assert "linear history" in text.lower()
    assert "--no-ff" in text


def test_runbook_documents_local_only_caveat():
    text = _runbook()
    # The runbook must acknowledge the repo is local-only at the
    # time of writing.
    assert "git remote" in text.lower()


# ---------------------------------------------------------------------------
# 2. Dry-run scripts exist
# ---------------------------------------------------------------------------


def _bash() -> str:
    return SCRIPT_BASH.read_text(encoding="utf-8")


def _ps() -> str:
    return SCRIPT_PS1.read_text(encoding="utf-8")


def test_bash_script_exists():
    assert SCRIPT_BASH.exists()
    assert SCRIPT_BASH.stat().st_size > 500


def test_ps_script_exists():
    assert SCRIPT_PS1.exists()
    assert SCRIPT_PS1.stat().st_size > 500


# ---------------------------------------------------------------------------
# 3. Both scripts require --apply AND --yes-i-understand to apply
# ---------------------------------------------------------------------------


def test_bash_script_requires_both_flags_to_apply():
    text = _bash()
    assert "--apply" in text
    assert "--yes-i-understand" in text


def test_ps_script_requires_both_switches_to_apply():
    text = _ps()
    assert "-Apply" in text or "Apply" in text
    assert "YesIUnderstand" in text


def test_bash_script_refuses_to_apply_without_yes_i_understand():
    """Live smoke: run with --apply only, expect exit code 3
    (refused) and no remote calls. The script must not call any
    remote API even with --apply alone."""
    result = subprocess.run(
        ["bash", "scripts/github/branch_protection_plan.sh", "--apply"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 3, (
        f"bash script returned {result.returncode}, expected 3 (refused). "
        f"stdout: {result.stdout!r}"
    )
    assert "Refusing to apply" in result.stdout


def test_bash_script_dry_run_is_safe_default():
    """Calling without any flag must print the plan and exit 0
    without any remote calls."""
    result = subprocess.run(
        ["bash", "scripts/github/branch_protection_plan.sh"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0
    assert "DRY RUN" in result.stdout


# ---------------------------------------------------------------------------
# 4. No secrets, no real URLs in either script
# ---------------------------------------------------------------------------


_FORBIDDEN_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),  # GitHub PAT
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),  # GitHub fine-grained PAT
    re.compile(r"xox[abprs]-[A-Za-z0-9-]+"),  # Slack
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style
)


def test_no_secrets_in_bash_script():
    text = _bash()
    for rx in _FORBIDDEN_PATTERNS:
        m = rx.search(text)
        assert m is None, f"bash script may contain a secret: {m.group(0)[:8]}…"


def test_no_secrets_in_ps_script():
    text = _ps()
    for rx in _FORBIDDEN_PATTERNS:
        m = rx.search(text)
        assert m is None, f"ps1 script may contain a secret: {m.group(0)[:8]}…"


# An HTTPS URL pointing somewhere other than github.com / githubstatus.com
# / cli.github.com / example placeholder is suspicious in a script that
# is supposed to be apply-by-flag.
_ANY_HTTPS = re.compile(r"https?://[\w.\-]+")
_ALLOWED_HOSTS = (
    "cli.github.com",
    "github.com",
    "githubstatus.com",
    "127.0.0.1",
    "example.com",
)


def test_no_unexpected_urls_in_bash_script():
    text = _bash()
    for m in _ANY_HTTPS.finditer(text):
        url = m.group(0)
        if any(h in url for h in _ALLOWED_HOSTS):
            continue
        raise AssertionError(f"bash script unexpected URL: {url}")


def test_no_unexpected_urls_in_ps_script():
    text = _ps()
    for m in _ANY_HTTPS.finditer(text):
        url = m.group(0)
        if any(h in url for h in _ALLOWED_HOSTS):
            continue
        raise AssertionError(f"ps1 script unexpected URL: {url}")


# ---------------------------------------------------------------------------
# 5. GO_LIVE checklist updated
# ---------------------------------------------------------------------------


def test_go_live_checklist_has_branch_protection_section():
    text = GO_LIVE.read_text(encoding="utf-8")
    assert "branch protection" in text.lower()
    assert "GITHUB_BRANCH_PROTECTION.md" in text


def test_go_live_checklist_names_required_checks():
    text = GO_LIVE.read_text(encoding="utf-8")
    # Display names — not job ids — must appear, because that is
    # what an operator must paste into the GitHub protection rule.
    assert "Python tests + content hygiene + non-IT readiness" in text
    assert "Production-like system checks (DEBUG=false)" in text
    assert "Lighthouse desktop (perf / a11y / best / seo budgets)" in text


# ---------------------------------------------------------------------------
# 6. CI_QUALITY_GATE.md cross-references the new runbook
# ---------------------------------------------------------------------------


def test_ci_quality_gate_links_to_branch_protection_runbook():
    text = CI_RUNBOOK.read_text(encoding="utf-8")
    assert "GITHUB_BRANCH_PROTECTION.md" in text


def test_ci_quality_gate_lists_required_check_display_names():
    text = CI_RUNBOOK.read_text(encoding="utf-8")
    # Job ids -> display names mapping must be in the runbook.
    assert "Python tests + content hygiene + non-IT readiness" in text
    assert "Production-like system checks (DEBUG=false)" in text
    assert "Lighthouse desktop (perf / a11y / best / seo budgets)" in text
