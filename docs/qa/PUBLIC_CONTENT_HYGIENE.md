# Public content hygiene — runbook

**Iter**: F-p1-leg-2-legal-content-hygiene
**Date**: 2026-05-11

This runbook documents the deontological audit script
`scripts/audit_legal_content_hygiene.py`. The script is a **static
analyzer**: it walks template / markdown sources on disk and flags
phrases that break the deontology a law firm's public site must
maintain.

The companion script `scripts/audit_public_content_hygiene.py`
already covers translation regressions, image-alt, Pexels
attribution and key leaks; it is HTTP-based (drives a running
server). These are complementary: run both before any release.

---

## 1. Why it exists

Italian forensic deontology (and the equivalent rules in the other
jurisdictions the platform addresses) forbid:

- promising a guaranteed outcome of a legal case;
- presenting a calculator output as a definitive legal opinion;
- aggressive economic claims ("paghi solo se vinci", "100% gratis");
- unsupported comparatives ("numero uno", "leader assoluto");
- exposing case histories or liquidated amounts without a
  clear-and-loud "esemplificativo" disclaimer;
- collecting health / family / judicial data without an explicit
  GDPR art. 9 consent block on the same page.

The script encodes those constraints as regex rules and runs in
under a second across the templates. The intent is **prevention,
not punishment**: every finding has a `hint` that suggests a safe
rewrite.

---

## 2. Six categories

| ID | Category | Severity | Example match |
|---|---|---|---|
| A | promise_of_result | error | "risarcimento garantito", "vinceremo" |
| B | automated_legal_advice | error | "calcolo definitivo", "parere legale automatico" |
| C | aggressive_economic_claim | error | "paghi solo se vinci", "100% gratis" |
| D | unsupported_comparative | error | "numero uno in italia", "leader assoluto" |
| E | risky_case_history | warning | "caso reale" without disclaimer, "EUR 50.000 liquidati" |
| F | gdpr_sensitivity | warning | "dati al sicuro" (decontextualized), "completamente anonimo" |

Severity = `error` exits non-zero and blocks CI. Severity =
`warning` requires `--strict` to fail; otherwise it's a heads-up
for the operator.

The full pattern list is in `scripts/audit_legal_content_hygiene.py::RULES`.
Each rule has multiple patterns; matching is case-insensitive and
anchored on word boundaries (`\b`) where appropriate so substrings
don't trigger false positives.

---

## 3. How to run

```bash
# Default: scan templates/public/ + templates/partials/
python scripts/audit_legal_content_hygiene.py

# JSON report alongside console output
python scripts/audit_legal_content_hygiene.py --json artifacts/content_hygiene/report.json

# Treat warnings as errors (recommended before release)
python scripts/audit_legal_content_hygiene.py --strict

# Scan a custom root (e.g. a new CMS dir)
python scripts/audit_legal_content_hygiene.py --root templates/public --root apps/cms_content/fixtures
```

Exit codes:

- `0` — no errors. Warnings may still be present (see `--strict`).
- `1` — at least one error matched, or `--strict` and any warning.

The script does not start a server, hit the network, or write to
the DB. It is fast and reproducible enough to wire to a pre-commit
hook if the team wants.

---

## 4. How to add a banned phrase

Open `scripts/audit_legal_content_hygiene.py`. Find the existing
`Rule(...)` for the category you want to extend. Add a regex to
the `patterns` tuple:

```python
Rule(
    category="A.promise_of_result",
    severity="error",
    patterns=(
        r"\brisarcimento\s+garantito\b",
        # ... existing patterns ...
        r"\bla\s+(causa|pratica)\s+(è|e')\s+vinta\s+sicuramente\b",  # ← new
    ),
    hint=...
)
```

A new test in `apps/core/test_legal_content_hygiene_p1_leg_2.py`
covering the new phrase keeps it from regressing.

If the phrase warrants its own category, append a whole new
`Rule(...)` instead.

---

## 5. How to add an allowlist entry

Allowlist entries protect phrases that LOOK risky but are
themselves the disclaimer (e.g. `nessuna garanzia di risultato`).
The whole line containing the match is whitelisted if any
`ALLOWLIST_PATTERNS` regex matches it.

```python
ALLOWLIST_PATTERNS: tuple[str, ...] = (
    # ... existing patterns ...
    r"\bnon\s+è\s+possibile\s+garantire\b",  # ← new safe phrase
)
```

Examples already in place:

- `r"\bno\s+automated\s+legal\s+advice\b"` lets the disclaimer
  page say "No automated legal advice" without triggering rule B.
- `r"\bnessuna\s+garanzia\s+di\s+risultato\b"` is the safe Italian
  phrasing.

When in doubt, **prefer adding the negated form to the allowlist
over weakening a rule pattern**.

---

## 6. Inline ignore marker

If a one-off occurrence is legitimate but not generic enough for
the allowlist, suppress it on the same line:

```django
<!-- hygiene-ignore: A.promise_of_result -->
<p>... legitimate but locally context-dependent phrasing ...</p>
```

or

```django
<p>... phrasing ... {# hygiene-ignore: A.promise_of_result #}</p>
```

The marker silences ONLY the named category on that line. Other
categories still apply. Every occurrence of the marker SHOULD be
accompanied by a comment explaining why it's safe; the script does
not enforce the justification, but code review must.

---

## 7. Fixing a false positive

Most false positives fall into one of three buckets:

| Bucket | Fix |
|---|---|
| Disclaimer text negates the prohibited phrase | Add the negated form to `ALLOWLIST_PATTERNS`. |
| One-off legitimate context | Use the inline `hygiene-ignore:` marker + comment. |
| Rule pattern too broad | Tighten the regex (add a lookbehind / lookahead). Open a PR; add a test. |

Do NOT silence a finding by deleting the rule pattern. Do NOT
short-circuit the script with `# noqa`-style markers — the script
intentionally does not honour Python lint markers.

---

## 8. Use before deploy

The pre-deploy checklist (`docs/GO_LIVE_GATE_CHECKLIST.md`) lists
the audits to run. The recommended order is:

1. `python manage.py check` (production-like env).
2. `pytest -q` (full suite).
3. `python scripts/audit_legal_content_hygiene.py --strict`.
4. `bash scripts/run_lighthouse_local.sh`.
5. `python scripts/audit_public_content_hygiene.py` (runs against
   the live server, covers different surfaces).

If any of the four returns non-zero, fix before deploy.

---

## 9. What the Studio still has to validate

The script is a **floor**, not a ceiling. It catches the most
common deontology mistakes, but a fresh page or a marketing copy
change still requires human review. The Studio must, before
go-live, manually read:

- the home page,
- every country landing,
- every wizard intro screen,
- the privacy / disclaimer pages,
- the contact form,
- the thank-you page,
- the wizard result page.

Particular attention to:

- consistency of "valutazione preliminare" framing (preliminary
  legal review, never "consulenza");
- consistency of "mandato professionale separato" language on
  every funnel exit;
- absence of any case-history-style anecdote that could be read as
  a guarantee of similar outcome.

When the Studio approves a particular new phrasing, encode it as
either an allowlist entry (if reusable) or an inline ignore (if
one-off) so future regressions can't reintroduce the risk.
