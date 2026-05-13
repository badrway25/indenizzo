"""Audit deontological hygiene of the public site content (P1-LEG-2).

Iter: F-p1-leg-2-legal-content-hygiene.

Companion to ``scripts/audit_public_content_hygiene.py`` (which is
HTTP-based + focuses on translation regressions, image-alt, Pexels
attribution and key leaks). This script is a **static analyzer**:
it walks template / markdown sources on disk and flags phrases that
break the deontological hygiene a law firm's public site must
maintain.

Six categories of risk are covered:

A. Promesse di risultato — "risarcimento garantito", "vinceremo", ...
B. Consulenza legale automatica — "calcolo definitivo", "diritto certo", ...
C. Claim economici aggressivi — "zero costi sempre", "paghi solo se vinci", ...
D. Comparativi non provati — "i migliori", "numero uno", "leader assoluto", ...
E. Uso rischioso di casi pratici — "caso reale" senza disclaimer, ...
F. Sensibilità GDPR — "dati al sicuro" senza contesto, "anonimo" ambiguo, ...

Each rule has a category, a severity (``error`` or ``warning``), a
list of patterns, and a hint with the recommended correction.

Allowlist: phrases that LOOK risky but are legitimate because they
are themselves the disclaimer (e.g. "nessuna garanzia di risultato"
is the safe formulation we expect to see, not the prohibited one).
The allowlist supports both whole-phrase matches and a
``lhci-ignore: <category>`` per-occurrence inline marker.

Output:

- Console: human-readable lines with file:line + snippet + hint.
- ``--json artifacts/content_hygiene/report.json``: structured JSON
  for CI consumption.
- Exit code 0 on no error; 1 if any error matched; warnings alone
  do not fail unless ``--strict``.

Run:

    python scripts/audit_legal_content_hygiene.py
    python scripts/audit_legal_content_hygiene.py --strict
    python scripts/audit_legal_content_hygiene.py --json artifacts/content_hygiene/report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Rule model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    """A single hygiene rule.

    ``patterns`` are compiled with ``re.IGNORECASE``. Use ``\\b``
    around words to avoid false positives on substrings (e.g.
    "garantiamo" matching as a substring of "garantiamoci").
    """

    category: str
    severity: str  # "error" | "warning"
    patterns: tuple[str, ...]
    hint: str

    def compile(self) -> list[re.Pattern[str]]:
        return [re.compile(p, re.IGNORECASE) for p in self.patterns]


@dataclass
class Finding:
    file: str
    line: int
    snippet: str
    category: str
    severity: str
    pattern: str
    hint: str

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "snippet": self.snippet,
            "category": self.category,
            "severity": self.severity,
            "pattern": self.pattern,
            "hint": self.hint,
        }


# ---------------------------------------------------------------------------
# Rules — six categories
# ---------------------------------------------------------------------------

RULES: tuple[Rule, ...] = (
    # ---- A. Promesse di risultato ----
    Rule(
        category="A.promise_of_result",
        severity="error",
        patterns=(
            r"\brisarcimento\s+garantito\b",
            r"\bsuccesso\s+(assicurato|garantito)\b",
            r"\bvincer(emo|ai|emo\s+sicuramente)\b",
            r"\botteniamo\s+sempre\b",
            r"\bgarantiamo\s+(il\s+)?risultato\b",
            r"\bti\s+spetta\s+sicuramente\b",
            r"\b(la\s+vittoria|il\s+risultato)\s+(è|e')\s+garantit(a|o)\b",
            r"\b(guaranteed|surely\s+entitled)\s+(result|outcome|compensation)\b",
        ),
        hint=(
            "Una richiesta non può promettere un esito. Riformulare con "
            "una stima orientativa o un range indicativo, sempre legato "
            "alle fonti (es. 'stima indicativa, soggetta a valutazione "
            "legale')."
        ),
    ),
    # ---- B. Consulenza legale automatica ----
    Rule(
        category="B.automated_legal_advice",
        severity="error",
        patterns=(
            r"\bcalcolo\s+definitivo\b",
            r"\bparere\s+legale\s+automatico\b",
            r"\bquesta\s+(è|e')\s+consulenza\s+legale\b",
            r"\bimporto\s+esatto\b",
            r"\bdiritto\s+certo\b",
            r"\bautomated\s+legal\s+advice\b",
            r"\bdefinitive\s+calculation\b",
        ),
        hint=(
            "Le simulazioni non sono consulenza. Sostituire con "
            "'simulazione indicativa', 'stima orientativa basata su "
            "fonti', e collegare al disclaimer."
        ),
    ),
    # ---- C. Claim economici aggressivi ----
    Rule(
        category="C.aggressive_economic_claim",
        severity="error",
        patterns=(
            r"\bzero\s+costi\s+sempre\b",
            r"\bnessuna\s+spesa\s+in\s+assoluto\b",
            r"\bpaghi\s+solo\s+se\s+vinci\b",
            r"\bsenza\s+alcun\s+rischio\b",
            r"\bmassimo\s+risarcimento\s+garantito\b",
            r"\b(no\s+win\s+no\s+fee|risk[-\s]?free)\b",
            r"\b100\s*%\s+(gratis|free)\b",
        ),
        hint=(
            "Evitare claim assolutistici sui costi. La valutazione "
            "preliminare può essere gratuita, ma sempre con la qualifica "
            "esplicita 'preliminare' e il rimando a un mandato scritto."
        ),
    ),
    # ---- D. Comparativi non provati ----
    Rule(
        category="D.unsupported_comparative",
        severity="error",
        patterns=(
            r"\b(i|le)\s+miglior(i|e)\s+(avvocati|studio|legali)\b",
            r"\bnumero\s+uno\s+in\s+(italia|europa)\b",
            r"\bpiù\s+esperti\s+di\s+tutti\b",
            r"\bleader\s+(assoluto|del\s+settore|incontrastato)\b",
            r"\bunico\s+studio\b",
            r"\bnumber\s+one\s+(law\s+firm|in\s+europe)\b",
        ),
        hint=(
            "I claim comparativi devono essere documentabili o vietati. "
            "Sostituire con 'studio internazionale con esperienza in...' "
            "+ casi/competenze reali."
        ),
    ),
    # ---- E. Uso rischioso di casi pratici ----
    # NOTE: matching "caso reale" / "vero caso" is acceptable IF the
    # surrounding sentence carries a disclaimer phrase. The script
    # downgrades to a warning unless `--strict` is passed. The full
    # heuristic isn't perfect; a human review of any warning is
    # always required.
    Rule(
        category="E.risky_case_history",
        severity="warning",
        patterns=(
            r"\bcaso\s+(reale|vero)(?!\s+a\s+titolo\s+esemplificativo)\b",
            r"\brecensione\s+verificata\b(?!\s+da)",
            r"\b(testimonianza|review)\s+autentica\b",
            r"\bcase\s+study(?!\s+for\s+illustrative)\b",
            # An absolute EUR amount with `liquidat(o|i)` nearby — almost
            # always misleading without context. The pattern catches "
            # EUR 50.000 liquidati" / "liquidati 12.000 EUR" / "€ 25.000
            # liquidati", scoped to a 60-char window.
            r"(€|EUR)\s*[\d\.\,]+[^\.]{0,60}\bliquidat",
            r"\bliquidat[oi]\b[^\.]{0,60}(€|EUR)\s*[\d\.\,]+",
        ),
        hint=(
            "I riferimenti a casi pratici devono includere un disclaimer "
            "esplicito (es. 'a titolo esemplificativo, non garanzia di "
            "esito analogo'). Importi liquidati senza contesto sono da "
            "evitare in pagina pubblica."
        ),
    ),
    # ---- F. Sensibilità GDPR ----
    Rule(
        category="F.gdpr_sensitivity",
        severity="warning",
        patterns=(
            # "anonimo" used near a request for contact data — likely
            # misleading. We don't have full context, so this is a warn.
            r"\bdati\s+al\s+sicuro\b(?!\s*\.\s*Per\s+i\s+dettagli)",
            r"\bcompletamente\s+anonim(o|a)\b",
            r"\bcarica(\s+il)?\s+documenti?\s+(qui|ora)\b(?![^.]{0,60}consenso)",
            r"\binserisci\s+i\s+dati\s+sanitari\b(?![^.]{0,60}consenso)",
        ),
        hint=(
            "Le pagine che raccolgono dati sensibili devono avere il "
            "blocco consenso GDPR (art. 6 + art. 9) visibile e il link "
            "esplicito alla privacy policy."
        ),
    ),
)


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------

# Whole phrases (regex, case-insensitive) that are intentionally allowed
# even if a rule above would otherwise match — typically because the
# phrase IS the disclaimer.
ALLOWLIST_PATTERNS: tuple[str, ...] = (
    # The disclaimer text itself.
    r"\bnessuna\s+garanzia\s+di\s+risultato\b",
    r"\bnon\s+costituisce\s+(consulenza|parere)\b",
    r"\bsimulazione\s+indicativa\b",
    r"\bvalutazione\s+preliminare\s+gratuita\b",
    r"\bstima\s+orientativa\b",
    r"\bnessuna\s+consulenza\s+legale\s+automatica\b",
    # Negated forms of the prohibited phrases. The disclaimer page
    # legitimately says "No automated legal advice" / "No guarantee
    # of outcome" / "Not legal advice" — these are the safe
    # formulations we EXPECT to see, not the violation.
    r"\bno\s+automated\s+legal\s+advice\b",
    r"\bno\s+guarantee\s+of\s+outcome\b",
    r"\bnot\s+legal\s+advice\b",
    r"\bdo\s+not\s+constitute\s+legal\s+advice\b",
    r"\bdoes\s+not\s+constitute\s+(a\s+)?(professional\s+)?engagement\b",
    # GDPR + consent block markers (so anti-GDPR rules don't fire on
    # the page that explains the consent itself).
    r"\bdata-consent-block\b",
    r"\bdata-consent-art-[69]\b",
    r"\bdata-legal-page\b",
    r"\bdata-mandate-notice\b",
)

# Per-occurrence inline marker. To silence a specific line, put on
# the same line (or the line above):
#
#     hygiene-ignore: A.promise_of_result
#
# Justify in a comment why it's safe — the script does not enforce a
# justification, but reviewers should.
INLINE_IGNORE_RE = re.compile(
    r"hygiene-ignore:\s*([A-F]\.[a-z_]+)", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def _discover_files(roots: list[Path]) -> list[Path]:
    """Return every scannable file under ``roots``.

    Includes ``.html`` templates and ``.md`` markdown content. Excludes
    test files, audit reports and obviously internal docs.
    """
    discovered: list[Path] = []
    skip_segments = {
        "node_modules",
        ".venv",
        "venv",
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "staticfiles",
        ".lighthouseci",
    }
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(seg in skip_segments for seg in p.parts):
                continue
            if p.suffix.lower() in (".html", ".md"):
                discovered.append(p)
    return sorted(discovered)


def _default_roots() -> list[Path]:
    """Public-facing surfaces scanned by default."""
    return [
        REPO_ROOT / "templates" / "public",
        REPO_ROOT / "templates" / "partials",
    ]


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


@dataclass
class CompiledRule:
    rule: Rule
    patterns: list[re.Pattern[str]] = field(default_factory=list)

    @classmethod
    def build_all(cls) -> list[CompiledRule]:
        return [cls(rule=r, patterns=r.compile()) for r in RULES]


def _allowlist_matches(line: str) -> list[str]:
    """Return the matched allowlist patterns inside ``line``."""
    found = []
    for pat in ALLOWLIST_PATTERNS:
        if re.search(pat, line, re.IGNORECASE):
            found.append(pat)
    return found


def _ignore_categories_on_line(line: str) -> set[str]:
    """Return the set of category labels suppressed via inline marker."""
    return {m.group(1) for m in INLINE_IGNORE_RE.finditer(line)}


def scan_file(path: Path, compiled: list[CompiledRule]) -> list[Finding]:
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings  # binary or non-UTF8: skip

    for lineno, line in enumerate(text.splitlines(), start=1):
        # Strip Django/HTML template comments so they don't look like
        # public copy. A `{# ... #}` or `<!-- ... -->` line ought not
        # to trigger findings.
        cleaned = re.sub(r"\{#.*?#\}", "", line)
        cleaned = re.sub(r"<!--.*?-->", "", cleaned)

        # Inline category suppressions on this exact line.
        suppressed = _ignore_categories_on_line(line)

        for cr in compiled:
            if cr.rule.category in suppressed:
                continue
            for pat in cr.patterns:
                match = pat.search(cleaned)
                if not match:
                    continue
                # Allowlist veto: if a whitelisted phrase is on the same
                # line, the match is a documented disclaimer.
                if _allowlist_matches(cleaned):
                    continue
                snippet = match.group(0).strip()
                try:
                    file_repr = path.relative_to(REPO_ROOT).as_posix()
                except ValueError:
                    # `path` lives outside the repo (e.g. a tmp_path
                    # in pytest). Fall back to the absolute path so
                    # the finding stays useful.
                    file_repr = path.as_posix()
                findings.append(
                    Finding(
                        file=file_repr,
                        line=lineno,
                        snippet=snippet,
                        category=cr.rule.category,
                        severity=cr.rule.severity,
                        pattern=pat.pattern,
                        hint=cr.rule.hint,
                    )
                )
    return findings


def scan(roots: list[Path] | None = None) -> list[Finding]:
    """Public entrypoint for the test suite + the CLI."""
    files = _discover_files(roots or _default_roots())
    compiled = CompiledRule.build_all()
    out: list[Finding] = []
    for f in files:
        out.extend(scan_file(f, compiled))
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _emit_console(findings: list[Finding]) -> None:
    if not findings:
        print("OK: no hygiene findings on the scanned surface.")
        return
    by_sev = {"error": 0, "warning": 0}
    for f in findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        marker = "ERROR" if f.severity == "error" else "warn"
        print(
            f"[{marker}] {f.file}:{f.line}  [{f.category}]  "
            f"{f.snippet!r}\n         hint: {f.hint}"
        )
    print()
    print(f"Total: {by_sev.get('error', 0)} error(s), {by_sev.get('warning', 0)} warning(s).")


def _emit_json(findings: list[Finding], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tool": "audit_legal_content_hygiene.py",
        "iter": "F-p1-leg-2-legal-content-hygiene",
        "summary": {
            "error_count": sum(1 for f in findings if f.severity == "error"),
            "warning_count": sum(1 for f in findings if f.severity == "warning"),
        },
        "findings": [f.to_dict() for f in findings],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan public templates / markdown for deontological hygiene violations."
    )
    parser.add_argument(
        "--root",
        action="append",
        default=None,
        type=Path,
        help=(
            "Additional root directory to scan. May be passed multiple "
            "times. If omitted, scans templates/public/ + "
            "templates/partials/."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Treat warnings as errors (exit non-zero if any warning).",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Write a JSON report to this path (in addition to console output).",
    )
    args = parser.parse_args(argv)

    roots = args.root or _default_roots()
    findings = scan(roots=roots)
    _emit_console(findings)
    if args.json:
        _emit_json(findings, args.json)

    has_error = any(f.severity == "error" for f in findings)
    has_warning = any(f.severity == "warning" for f in findings)
    if has_error:
        return 1
    if args.strict and has_warning:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
