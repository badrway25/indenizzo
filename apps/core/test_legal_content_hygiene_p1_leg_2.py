"""
Tests F-p1-leg-2-legal-content-hygiene.

Coprono lo script `scripts/audit_legal_content_hygiene.py` — il
guardiano deontologico dei contenuti pubblici.

1.  intercetta promessa di risultato ("risarcimento garantito");
2.  intercetta consulenza legale automatica ("calcolo definitivo");
3.  intercetta claim economico aggressivo ("paghi solo se vinci");
4.  intercetta comparativo non provato ("numero uno in italia");
5.  intercetta uso rischioso di casi pratici ("caso reale") come warning;
6.  intercetta riferimento a importo liquidato senza contesto;
7.  allowlist non genera falso positivo sui disclaimer negativi
    ("No automated legal advice");
8.  allowlist non genera falso positivo su "nessuna garanzia di risultato";
9.  inline marker `hygiene-ignore: <category>` sopprime una specifica linea;
10. output Finding include file/line/snippet/category/severity;
11. exit code 1 su error;
12. exit code 0 con solo warning;
13. exit code 1 con --strict + warning;
14. lo script passa sul contenuto reale (templates/public + partials)
    nel repository.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_legal_content_hygiene.py"


def _load_module():
    """Import the hygiene script as a module without invoking the CLI.

    Register the module in ``sys.modules`` BEFORE ``exec_module``: the
    ``@dataclass`` decorator with ``from __future__ import annotations``
    resolves string annotations by looking the module up in
    ``sys.modules``, and a missing registration raises AttributeError.
    """
    module_name = "audit_legal_content_hygiene"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _scan_text(tmp_path, text: str, *, suffix: str = ".html"):
    """Write `text` to a temp file and return findings for it."""
    module = _load_module()
    f = tmp_path / f"sample{suffix}"
    f.write_text(text, encoding="utf-8")
    return module.scan(roots=[tmp_path])


# ---------------------------------------------------------------------------
# 1-6: category coverage
# ---------------------------------------------------------------------------


def test_catches_promise_of_result(tmp_path):
    findings = _scan_text(
        tmp_path,
        "<p>Il tuo risarcimento garantito anche se non ricordi nulla.</p>",
    )
    assert any(f.category == "A.promise_of_result" for f in findings)
    assert all(f.severity == "error" for f in findings if f.category == "A.promise_of_result")


def test_catches_automated_legal_advice(tmp_path):
    findings = _scan_text(
        tmp_path,
        "<p>Forniamo un calcolo definitivo del danno biologico.</p>",
    )
    assert any(f.category == "B.automated_legal_advice" for f in findings)


def test_catches_aggressive_economic_claim(tmp_path):
    findings = _scan_text(
        tmp_path,
        "<p>Paghi solo se vinci, senza alcun rischio.</p>",
    )
    cats = {f.category for f in findings}
    assert "C.aggressive_economic_claim" in cats


def test_catches_unsupported_comparative(tmp_path):
    findings = _scan_text(
        tmp_path,
        "<p>Siamo numero uno in italia, leader assoluto.</p>",
    )
    cats = {f.category for f in findings}
    assert "D.unsupported_comparative" in cats


def test_catches_risky_case_history_as_warning(tmp_path):
    findings = _scan_text(
        tmp_path,
        "<p>Vi raccontiamo un caso reale che abbiamo seguito.</p>",
    )
    matched = [f for f in findings if f.category == "E.risky_case_history"]
    assert matched
    assert all(f.severity == "warning" for f in matched)


def test_catches_liquidated_amount_without_context(tmp_path):
    findings = _scan_text(
        tmp_path,
        "<p>Abbiamo ottenuto EUR 50.000 liquidati per un cliente.</p>",
    )
    assert any(f.category == "E.risky_case_history" for f in findings)


# ---------------------------------------------------------------------------
# 7-8: allowlist
# ---------------------------------------------------------------------------


def test_allowlist_negated_disclaimer_phrases(tmp_path):
    """Disclaimer pages that NEGATE the prohibited phrase must pass."""
    findings = _scan_text(
        tmp_path,
        '<h2 class="font-serif">2. No automated legal advice</h2>',
    )
    assert findings == []


def test_allowlist_italian_disclaimer(tmp_path):
    findings = _scan_text(
        tmp_path,
        "<p>La simulazione non costituisce consulenza: nessuna garanzia di risultato.</p>",
    )
    assert findings == []


# ---------------------------------------------------------------------------
# 9: inline ignore marker
# ---------------------------------------------------------------------------


def test_inline_ignore_marker_suppresses_only_named_category(tmp_path):
    # The violation IS present, but the inline marker silences it.
    findings = _scan_text(
        tmp_path,
        "<p>Risarcimento garantito {# hygiene-ignore: A.promise_of_result #}</p>",
    )
    assert findings == []

    # If the marker names a DIFFERENT category, the rule still fires.
    findings = _scan_text(
        tmp_path,
        "<p>Risarcimento garantito {# hygiene-ignore: B.automated_legal_advice #}</p>",
    )
    assert any(f.category == "A.promise_of_result" for f in findings)


# ---------------------------------------------------------------------------
# 10: Finding shape
# ---------------------------------------------------------------------------


def test_finding_payload_shape(tmp_path):
    findings = _scan_text(
        tmp_path,
        "Pagina di test.\nRisarcimento garantito qui.\nFooter.\n",
    )
    promo = next(f for f in findings if f.category == "A.promise_of_result")
    assert promo.line == 2
    assert "risarcimento garantito" in promo.snippet.lower()
    assert promo.severity == "error"
    assert promo.hint
    payload = promo.to_dict()
    for key in ("file", "line", "snippet", "category", "severity", "hint"):
        assert key in payload


# ---------------------------------------------------------------------------
# 11-13: exit codes
# ---------------------------------------------------------------------------


def _run_cli(*extra_args, cwd=None, env=None):
    cmd = [sys.executable, str(SCRIPT_PATH), *extra_args]
    return subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False,
    )


def test_cli_exit_1_on_error(tmp_path):
    f = tmp_path / "bad.html"
    f.write_text("<p>Risarcimento garantito.</p>", encoding="utf-8")
    proc = _run_cli("--root", str(tmp_path))
    assert proc.returncode == 1
    assert "ERROR" in proc.stdout


def test_cli_exit_0_with_only_warnings(tmp_path):
    f = tmp_path / "warn.html"
    f.write_text("<p>Caso reale di successo.</p>", encoding="utf-8")
    proc = _run_cli("--root", str(tmp_path))
    assert proc.returncode == 0
    assert "warning" in proc.stdout.lower()


def test_cli_strict_promotes_warning_to_failure(tmp_path):
    f = tmp_path / "warn.html"
    f.write_text("<p>Caso reale di successo.</p>", encoding="utf-8")
    proc = _run_cli("--root", str(tmp_path), "--strict")
    assert proc.returncode == 1


# ---------------------------------------------------------------------------
# 14: real content stays clean
# ---------------------------------------------------------------------------


def test_real_repo_templates_pass_default_run():
    """The committed template surface must always pass with exit code 0."""
    proc = _run_cli(cwd=str(REPO_ROOT))
    assert proc.returncode == 0, (
        "audit_legal_content_hygiene flagged real content:\n" + proc.stdout
    )


def test_json_report_payload_structure(tmp_path):
    f = tmp_path / "bad.html"
    f.write_text("<p>Risarcimento garantito qui.</p>", encoding="utf-8")
    out = tmp_path / "report.json"
    proc = _run_cli("--root", str(tmp_path), "--json", str(out))
    assert proc.returncode == 1
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["tool"] == "audit_legal_content_hygiene.py"
    assert data["summary"]["error_count"] >= 1
    assert data["findings"]
    first = data["findings"][0]
    for key in ("file", "line", "snippet", "category", "severity", "hint"):
        assert key in first
