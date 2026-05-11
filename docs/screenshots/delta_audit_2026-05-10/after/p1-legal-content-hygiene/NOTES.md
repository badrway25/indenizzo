# P1-LEG-2 — deontological content hygiene audit

**Date**: 2026-05-11
**Iter**: `F-p1-leg-2-legal-content-hygiene`
**Branch**: `p1/legal-content-hygiene`
**Tag baseline P1-SEO-2**: `p1-seo-2-lighthouse-ci-2026-05-10`.

## Scope

This batch ships a **deontology-focused static analyzer**, distinct
from the pre-existing `scripts/audit_public_content_hygiene.py`
(which is HTTP-based + focused on translation regressions, image-
alt, Pexels attribution and key leaks).

The new script —
`scripts/audit_legal_content_hygiene.py` — walks template / markdown
sources on disk and flags six categories of risk a law firm's
public site must not contain:

A. promise_of_result (error)
B. automated_legal_advice (error)
C. aggressive_economic_claim (error)
D. unsupported_comparative (error)
E. risky_case_history (warning)
F. gdpr_sensitivity (warning)

Each rule has multiple regex patterns + a per-finding `hint` with
the recommended rewrite.

## Output on the real repo

```
$ python scripts/audit_legal_content_hygiene.py
OK: no hygiene findings on the scanned surface.
```

The committed `templates/public/` + `templates/partials/` surface is
clean. Exit code 0. One pre-existing false positive ("No automated
legal advice" on `disclaimer.html`) was resolved by adding the
negated forms to the allowlist, not by weakening the rules.

## Files modified / new

**Modified**: `.gitignore` — `artifacts/` excluded (per-run JSON reports).

**New**:
- `scripts/audit_legal_content_hygiene.py` — the analyzer (~340 lines).
- `apps/core/test_legal_content_hygiene_p1_leg_2.py` — 15 tests.
- `docs/qa/PUBLIC_CONTENT_HYGIENE.md` — runbook.
- `docs/screenshots/delta_audit_2026-05-10/after/p1-legal-content-hygiene/NOTES.md` (this).

No template / markdown source was modified — the real public content
is already deontology-clean.

## Categories implemented

| ID | Category | Severity | Sample patterns |
|---|---|---|---|
| A | promise_of_result | error | `risarcimento garantito`, `vinceremo`, `successo assicurato`, `ti spetta sicuramente` |
| B | automated_legal_advice | error | `calcolo definitivo`, `parere legale automatico`, `importo esatto`, `diritto certo` |
| C | aggressive_economic_claim | error | `paghi solo se vinci`, `senza alcun rischio`, `no win no fee`, `100% gratis` |
| D | unsupported_comparative | error | `numero uno`, `leader assoluto`, `i migliori`, `unico studio` |
| E | risky_case_history | warning | `caso reale` (senza disclaimer), `EUR XXX liquidati`, `recensione verificata` |
| F | gdpr_sensitivity | warning | `dati al sicuro` decontestualizzato, `completamente anonimo`, upload form senza link consenso |

## Allowlist

Whole-phrase regex matches that whitelist the entire line. Most
important entries:

- `nessuna garanzia di risultato` — the safe Italian phrasing.
- `non costituisce consulenza` — the disclaimer phrasing.
- `simulazione indicativa` / `stima orientativa` — neutral language.
- `no automated legal advice` / `no guarantee of outcome` /
  `not legal advice` — English disclaimer phrasings.
- `data-consent-block` / `data-legal-page` / `data-mandate-notice` —
  HTML markers on pages that legitimately discuss those concepts.

## Inline override

`{# hygiene-ignore: A.promise_of_result #}` or
`<!-- hygiene-ignore: A.promise_of_result -->` on the same line
silences the named category for that line only. The script does
not enforce a justifying comment; reviewers must.

## Tests (`apps/core/test_legal_content_hygiene_p1_leg_2.py`)

15 tests, all green:

- 6 category coverage tests (one per rule);
- 2 allowlist tests (Italian + English disclaimer forms);
- 1 inline-ignore-marker test (suppresses named category only);
- 1 Finding payload shape test;
- 3 CLI exit code tests (error → 1, warning → 0, `--strict` → 1);
- 1 JSON report payload test;
- 1 real-repo test (the committed surface always exits 0).

| Run | Result |
|-----|--------|
| `pytest apps/core/test_legal_content_hygiene_p1_leg_2.py -q` | **15 passed** |
| `pytest apps/core apps/compliance apps/crm apps/cases -q` | 1242 passed, 1 skipped |
| `pytest -q` (full) | **1795 passed, 1 skipped** (zero regressions, +15 from P1-SEO-2 baseline) |
| `python manage.py check` | clean (only the expected `core.W001` STUDIO_* dev warning) |
| `python scripts/audit_legal_content_hygiene.py` | OK: no hygiene findings |
| `python scripts/audit_legal_content_hygiene.py --strict` | OK: no hygiene findings, exit 0 |

## Browser live

No template was modified, so no UI surface changed. Browser-live
checks from P1-SEO-2 baseline (favicon clean console, CSP enforced,
no Google Fonts) remain valid.

## Why a new script instead of extending the existing one

`scripts/audit_public_content_hygiene.py` is HTTP-based: it spins
up a `urllib` request against a runserver instance and inspects the
rendered HTML for layout regressions (image alt, Pexels attribution,
English fallback on translated routes). Mixing the deontology
analyzer into the same script would:

- couple deontology checks to a live server,
- duplicate the file-walking logic the deontology pass needs,
- make the analyzer slow (10+ HTTP round-trips per run).

Keeping them split lets the deontology pass run in <1s on raw
templates, with no Django bootstrap, no DB, no port collision.

## Next batch suggested

In order of expected value:

1. **P1-SEC-3** — WAF/CDN edge security (Cloudflare / Caddy +
   CrowdSec) once production-style staging is up.
2. **P0-MVP-1** — first non-IT country green end-to-end
   (FR/BE/MA/TN). Unblocks the cardinal constraint of
   `LOCAL_NEXT_STEPS.md` Sec. 0.
3. **Tunisia/EU650 review + merge** — branch
   `work/tunisia-csp-eu650-restore` (`b44a5c2`) waits for Studio
   review.
4. **P2-SEO-1** — Lighthouse mobile preset baseline + budget.
5. **P1-LEG-2 follow-up** — wire the deontology audit into a
   pre-commit hook OR CI step once the team commits to a CI
   provider.
