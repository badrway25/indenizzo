"""H1-10: static guards for the Lighthouse runner hardening + ops workflow.

These assert the CI hardening stays in place (so it can't silently regress)
WITHOUT running Lighthouse/Chrome:

- the desktop and mobile runners keep the bounded retry around report
  collection + the `--disable-dev-shm-usage` CI-stability flag;
- the score GATE stays single-shot (retry the flake, never the verdict);
- the Lighthouse gate stays blocking (no `continue-on-error`, not skipped);
- the manual provenance ops workflow is `workflow_dispatch`-only, read-only,
  PII-safe and never migrates a real DB.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DESKTOP = REPO_ROOT / "scripts" / "run_lighthouse_local.sh"
MOBILE = REPO_ROOT / "scripts" / "run_lighthouse_mobile_local.sh"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
OPS_WF = REPO_ROOT / ".github" / "workflows" / "provenance-ops-drift-check.yml"


@pytest.mark.parametrize("script", [DESKTOP, MOBILE])
def test_runner_has_retry_and_stability_flag(script):
    text = script.read_text(encoding="utf-8")
    # Key CI-stability flag for headless Chrome on small /dev/shm runners.
    assert "--disable-dev-shm-usage" in text
    # Bounded retry (max 2 attempts) around report collection.
    assert "for attempt in 1 2" in text
    assert "[retry]" in text
    # Leftover Chrome processes are cleaned between attempts.
    assert "pkill -f chrome" in text


@pytest.mark.parametrize("script", [DESKTOP, MOBILE])
def test_score_gate_stays_single_shot(script):
    text = script.read_text(encoding="utf-8")
    # The verdict (score gate) must be evaluated exactly once — never inside the
    # retry loop, so a real budget miss still fails.
    assert text.count("global_failed=1") == 1


def test_lighthouse_gate_stays_blocking():
    text = CI_YML.read_text(encoding="utf-8")
    assert "continue-on-error" not in text, "the Lighthouse gate must stay blocking"
    assert "run_lighthouse_local.sh" in text, "the desktop gate must still run the runner"


def test_ops_workflow_is_manual_readonly_and_safe():
    text = OPS_WF.read_text(encoding="utf-8")
    assert "workflow_dispatch" in text
    # Must NOT auto-trigger.
    assert "pull_request" not in text
    assert "\n  push:" not in text and "on: push" not in text
    # Runs the read-only, fail-closed drift check.
    assert "verify_calculation_provenance" in text
    assert "--all-calculated" in text and "--fail-on-drift" in text
    # Never migrates a real DB (migrate only on the empty-DB fallback branch).
    assert "NOT migrating it" in text
    # References the secret indirectly; never echoes its value.
    assert "secrets.OPS_DATABASE_URL" in text
    assert 'echo "$OPS_DATABASE_URL"' not in text and "echo ${DATABASE_URL}" not in text
