"""
Tests F-p1-ci-1-ci-quality-gate (+ P1-CI-1A micro-fix).

Static-side smoke tests for the CI quality gate workflow. They do
NOT run GitHub Actions locally, do NOT spawn `gh` or `act`, and do
NOT execute Lighthouse. They pin the contract that the committed
workflow:

 1. lives at .github/workflows/ci.yml;
 2. carries the four expected jobs (python-tests, production-checks,
    lighthouse-desktop, lighthouse-mobile);
 3. runs every command the runbook documents (manage.py check,
    pytest -q, content hygiene --strict, non-IT readiness audit,
    desktop lighthouse runner, mobile lighthouse runner);
 4. exposes the mobile job as workflow_dispatch-only (opt-in);
 5. uses safe dummy env vars only — no real secrets, no real API
    keys, no real webhook URLs;
 6. points only at the local dev server (127.0.0.1) — no external
    HTTP targets;
 7. uploads Lighthouse artefacts on every run (always() clause);
 8. the companion runbook docs/qa/CI_QUALITY_GATE.md exists and
    references every job + every command;
 9. (P1-CI-1A) production-checks job runs with DEBUG=false +
    simulated signed env vars; no real secrets present; documents
    intent in the runbook.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
RUNBOOK = REPO_ROOT / "docs" / "qa" / "CI_QUALITY_GATE.md"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _runbook_text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Existence
# ---------------------------------------------------------------------------


def test_workflow_file_exists():
    assert WORKFLOW.exists()
    assert WORKFLOW.stat().st_size > 500


def test_runbook_file_exists():
    assert RUNBOOK.exists()
    assert RUNBOOK.stat().st_size > 500


# ---------------------------------------------------------------------------
# 2. Three expected jobs
# ---------------------------------------------------------------------------


def test_workflow_has_python_tests_job():
    text = _workflow_text()
    assert "python-tests:" in text


def test_workflow_has_production_checks_job():
    text = _workflow_text()
    assert "production-checks:" in text


def test_workflow_has_lighthouse_desktop_job():
    text = _workflow_text()
    assert "lighthouse-desktop:" in text


def test_workflow_has_lighthouse_mobile_job():
    text = _workflow_text()
    assert "lighthouse-mobile:" in text


# ---------------------------------------------------------------------------
# 3. Every commanded step is present
# ---------------------------------------------------------------------------


def test_workflow_runs_django_check():
    text = _workflow_text()
    assert "python manage.py check" in text


def test_workflow_runs_pytest():
    text = _workflow_text()
    assert "pytest -q" in text


def test_workflow_runs_content_hygiene_strict():
    text = _workflow_text()
    assert "audit_legal_content_hygiene.py --strict" in text


def test_workflow_runs_non_it_readiness_audit():
    text = _workflow_text()
    assert "audit_non_it_readiness.py" in text


def test_workflow_runs_lighthouse_desktop_script():
    text = _workflow_text()
    assert "scripts/run_lighthouse_local.sh" in text


def test_workflow_runs_lighthouse_mobile_script():
    text = _workflow_text()
    assert "scripts/run_lighthouse_mobile_local.sh" in text


# ---------------------------------------------------------------------------
# 4. Mobile job is opt-in (workflow_dispatch only)
# ---------------------------------------------------------------------------


def test_mobile_job_is_workflow_dispatch_only():
    text = _workflow_text()
    # The mobile job header is the only place where the dispatch
    # guard appears in this workflow.
    assert "github.event_name == 'workflow_dispatch'" in text


def test_workflow_triggers_include_pull_request_and_push():
    text = _workflow_text()
    assert "pull_request:" in text
    assert "push:" in text
    assert "workflow_dispatch:" in text


# ---------------------------------------------------------------------------
# 5. Safety env: no real secrets, no real API keys
# ---------------------------------------------------------------------------


def test_workflow_uses_dummy_secret_key():
    text = _workflow_text()
    assert 'django-insecure-' in text


def test_workflow_disables_pexels():
    text = _workflow_text()
    assert 'PEXELS_ENABLED: "false"' in text


def test_workflow_disables_lead_notification():
    text = _workflow_text()
    assert 'LEAD_NOTIFICATION_ENABLED: "false"' in text


def test_workflow_sentry_dsn_is_empty():
    text = _workflow_text()
    assert 'SENTRY_DSN: ""' in text


# Forbidden patterns: real prod-looking secrets or webhook URLs.
_FORBIDDEN_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),  # GitHub PAT
    re.compile(r"xox[abprs]-[A-Za-z0-9-]+"),  # Slack tokens
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style
)


def test_workflow_has_no_real_looking_secrets():
    text = _workflow_text()
    for rx in _FORBIDDEN_PATTERNS:
        m = rx.search(text)
        assert m is None, f"workflow may contain a real secret: {m.group(0)[:8]}…"


# ---------------------------------------------------------------------------
# 6. No external HTTP targets
# ---------------------------------------------------------------------------


_LOCAL_OK = re.compile(r"^https?://127\.0\.0\.1(?:[:/]|$)")
_ANY_HTTP = re.compile(r"https?://[\w.\-:/]+")
# Allow-list for HTTP URLs that legitimately appear in YAML comments
# or doc references and are not actual targets.
_ALLOWED_EXTERNAL_HOSTS = (
    "127.0.0.1",
)


def test_workflow_has_no_external_http_targets():
    text = _workflow_text()
    for m in _ANY_HTTP.finditer(text):
        url = m.group(0)
        if any(h in url for h in _ALLOWED_EXTERNAL_HOSTS):
            continue
        raise AssertionError(f"workflow points at an external URL: {url}")


# ---------------------------------------------------------------------------
# 7. Artefacts uploaded on every run (always())
# ---------------------------------------------------------------------------


def test_lighthouse_artefacts_are_uploaded_on_any_outcome():
    text = _workflow_text()
    # Both Lighthouse jobs upload artefacts under `if: always()`.
    # Spot-check: at least 2 occurrences of `if: always()` paired with
    # an upload-artifact step.
    assert text.count("if: always()") >= 2
    assert "actions/upload-artifact@v4" in text
    assert "artifacts/lighthouse/latest/" in text
    assert "artifacts/lighthouse-mobile/latest/" in text


# ---------------------------------------------------------------------------
# 8. Runbook references every moving piece
# ---------------------------------------------------------------------------


def test_runbook_references_every_job():
    text = _runbook_text()
    assert "python-tests" in text
    assert "lighthouse-desktop" in text
    assert "lighthouse-mobile" in text


def test_runbook_references_every_command():
    text = _runbook_text()
    assert "manage.py check" in text
    assert "pytest" in text
    assert "audit_legal_content_hygiene.py" in text
    assert "audit_non_it_readiness.py" in text
    assert "run_lighthouse_local.sh" in text
    assert "run_lighthouse_mobile_local.sh" in text


def test_runbook_documents_local_reproduction():
    text = _runbook_text()
    assert "run_quality_gate.sh" in text
    assert "Reproducing failures locally" in text or "reproduction" in text.lower()


def test_runbook_documents_why_mobile_is_opt_in():
    text = _runbook_text()
    assert "opt-in" in text.lower()
    assert "workflow_dispatch" in text


# ---------------------------------------------------------------------------
# 9. P1-CI-1A — production-checks job
# ---------------------------------------------------------------------------


def test_production_checks_runs_django_check():
    text = _workflow_text()
    # The production-checks job must run `python manage.py check`.
    # Two occurrences of that command in the workflow are expected:
    # one in python-tests (DEBUG=true) and one here (DEBUG=false).
    assert text.count("python manage.py check") >= 2


def test_production_checks_sets_django_debug_false():
    text = _workflow_text()
    assert 'DJANGO_DEBUG: "false"' in text


def test_production_checks_simulates_signed_studio_identity():
    text = _workflow_text()
    # The 7 STUDIO_* env vars that core.E001 enforces.
    for var in (
        "STUDIO_LEAD_LAWYER_NAME",
        "STUDIO_BAR_ASSOCIATION",
        "STUDIO_VAT_NUMBER",
        "STUDIO_PEC_EMAIL",
        "STUDIO_PHYSICAL_ADDRESS",
        "STUDIO_PROFESSIONAL_INSURANCE_INSURER",
        "STUDIO_PROFESSIONAL_INSURANCE_POLICY",
    ):
        assert var in text, f"production-checks missing {var}"


def test_production_checks_simulates_signed_policy_versions():
    text = _workflow_text()
    # Each policy version block: VERSION + STATUS=signed + SIGNED_AT.
    for var in (
        "PRIVACY_NOTICE_VERSION",
        "SPECIAL_CATEGORIES_NOTICE_VERSION",
        "PRIVACY_POLICY_VERSION",
        "PRIVACY_POLICY_STATUS",
        "PRIVACY_POLICY_SIGNED_AT",
        "DISCLAIMER_VERSION",
        "DISCLAIMER_STATUS",
        "DISCLAIMER_SIGNED_AT",
        "MANDATE_TEMPLATE_VERSION",
        "MANDATE_TEMPLATE_STATUS",
        "MANDATE_TEMPLATE_SIGNED_AT",
        "RETENTION_POLICY_VERSION",
    ):
        assert var in text, f"production-checks missing {var}"


def test_production_checks_keeps_external_services_off():
    text = _workflow_text()
    # Even when DEBUG=false, external services must stay off in CI.
    assert 'CRM_WEBHOOK_ENABLED: "false"' in text
    assert 'PEXELS_ENABLED: "false"' in text
    assert 'SENTRY_DSN: ""' in text


def test_production_checks_uses_invalid_tld_for_emails():
    text = _workflow_text()
    # `.invalid` (RFC 6761) never resolves to a real mailbox.
    assert "ci@example.invalid" in text


def test_production_checks_secret_key_is_not_django_insecure_prefix():
    text = _workflow_text()
    # In DEBUG=false the project refuses to start with a
    # `django-insecure-` prefixed key. The CI value must be neither
    # that prefix nor a real-shaped secret.
    # Read the production-checks DJANGO_SECRET_KEY assignment.
    m = re.search(
        r"production-checks:.*?DJANGO_SECRET_KEY:\s*\"([^\"]+)\"",
        text,
        re.DOTALL,
    )
    assert m is not None, "production-checks DJANGO_SECRET_KEY block not found"
    secret = m.group(1)
    assert not secret.startswith("django-insecure-"), (
        "production-checks key must not start with django-insecure- "
        "(prod refuses to start with that prefix)"
    )
    # Belt-and-braces: the value contains the literal "ci-not-real"
    # marker so a casual reader cannot mistake it for a real secret.
    assert "ci-not-real" in secret


def test_runbook_documents_production_checks_job():
    text = _runbook_text()
    assert "production-checks" in text
    assert "DEBUG=false" in text


def test_runbook_does_not_invent_external_dependencies():
    text = _runbook_text()
    for m in _ANY_HTTP.finditer(text):
        url = m.group(0)
        if any(h in url for h in _ALLOWED_EXTERNAL_HOSTS):
            continue
        # Runbook may reference some docs URLs in a generic way — but
        # any URL that looks like a real production / CRM / webhook
        # endpoint would be a problem.
        if "example.com" in url:
            continue
        if "github.com" in url:
            # Allow GitHub doc links if any.
            continue
        raise AssertionError(
            f"runbook points at an unexpected external URL: {url}"
        )
