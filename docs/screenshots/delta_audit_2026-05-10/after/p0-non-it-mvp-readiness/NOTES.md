# P0-MVP-1 — non-IT MVP readiness gate

**Date**: 2026-05-11
**Iter**: `F-p0-mvp-1-non-it-readiness`
**Branch**: `p0/non-it-mvp-readiness`
**Tag baseline P2-SEO-1**: `p2-seo-1-lighthouse-mobile-baseline-2026-05-10`.

## Scope

Pick the first non-IT country to bring end-to-end *review-gated*
(NOT publicly active as "valid calculator"), document what the
Studio must sign to flip the gate, and add guardrails so the chain
cannot be accidentally promoted without an audit trail.

**Decision**: **France** is the candidate. It has the deepest
quantification corpus (Mornet 191 rows + Gazette du Palais 4 189 rows,
26× the Belgium volume), the cleanest scaffold (single case_type,
no unsupported doctrinal mechanisms), and all 6 blockers documented
in `FRANCE_ACTIVATION_READINESS_AUDIT.md` are Studio-resolvable —
zero remaining engineering work before the gate can be flipped.

**Verdict**: **NO-GO for public activation today. READY for Studio review.**
The wizard renders, the form validates, the result page surfaces the
review-pending semantics, and no EUR amount is published. Once the
Studio signs Mornet + Gazette + Dintilhac LegalReviews, a single
follow-up batch (P0-MVP-1-ACTIVATE) can promote the chain.

## Files modified / new

**New**:
- `docs/NON_IT_MVP_READINESS_2026-05-10.md` — comparative FR/BE/MA/TN,
  recommendation, chain map (LegalSource → LegalReview → Dataset →
  Formula → calculator), Studio + dev checklists, guardrail
  description, go/no-go verdict.
- `apps/jurisdictions/checks.py` — Django system check
  `jurisdictions.E001`: in production, every APPROVED LegalSource
  must have a matching APPROVE LegalReview row + non-null
  `legal_reviewer`. Silent in dev. Opt-out via
  `settings.JURISDICTIONS_REQUIRE_LEGAL_REVIEW_AUDIT_TRAIL=False`.
- `scripts/legal_data/audit_non_it_readiness.py` — read-only audit
  script. Prints per-country chain state + verdict
  (`SCAFFOLD-ONLY` / `READY-FOR-REVIEW` / `APPROVED-INCONSISTENT` /
  `APPROVED-PARTIAL` / `APPROVED-CONSISTENT`). Returns exit code 1 if
  any country is `APPROVED-INCONSISTENT`.
- `apps/jurisdictions/test_non_it_readiness_guardrails_p0_mvp_1.py` —
  11 tests pinning the system check + audit script contract.
- `apps/cases/test_france_review_gated_e2e_p0_mvp_1.py` — 5 black-box
  HTTP tests pinning the public FR funnel stays review-gated.
- `scripts/capture_p0_non_it_mvp_readiness.py` — playwright
  screenshot runner.
- 9 screenshots in this directory.

**Modified**:
- `apps/jurisdictions/apps.py` — wires the `ready()` hook that
  imports `apps.jurisdictions.checks` to register the system check.

## Reality check from the local DB

The dev DB has 5 APPROVED non-IT LegalSources today (verified by
`scripts/legal_data/audit_non_it_readiness.py`):

| Country | Slug | Audit trail |
|---|---|---|
| FR | `fr-loi-badinter-1985` | APPROVE LegalReview + reviewer FK set |
| BE | `be-loi-1989-11-21-rc-auto` | same |
| MA | `ma-code-famille-moudawana-fr-pdf` | same |
| TN | `tn-code-statut-personnel-livre-ix-succession` | same |
| TN | `tn-code-dip-loi-98-97` | same |
| EU | `eu-regulation-650-2012-successions` | same |

These are all **official law/regulation texts** — the cornice
normativa. The quantification sources (Mornet, Gazette, Tableau
Indicatif 2020/2024) and the share mappings (Moudawana, CSP) remain
`needs_review`. None of the countries has an APPROVED
CompensationDataset or CalculationFormula → every calculator stays
`unavailable_requires_legal_validation` on the public path.

Verdict per country today (`audit_non_it_readiness.py` output):

| Country | Verdict |
|---|---|
| FR | `APPROVED-PARTIAL` (1 official source approved, 0 dataset/formula) |
| BE | `APPROVED-PARTIAL` |
| MA | `APPROVED-PARTIAL` |
| TN | `APPROVED-PARTIAL` |

The `APPROVED-INCONSISTENT` verdict — which would fire
`jurisdictions.E001` in production — is **not** triggered on any
country. The audit trail is intact.

## What the system check catches

`jurisdictions.E001` fires in production-like settings
(`DEBUG=False`) when:

1. A LegalSource has `status=APPROVED` but no matching `LegalReview(decision=APPROVE)` row, OR
2. A LegalSource has `status=APPROVED` + APPROVE review row but `legal_reviewer` FK is null on the source itself.

It does **not** check Dataset / Formula status — the calculator-code
gating already prevents output if either is missing, and adding a
DB check that those exist would be redundant.

The check is read-only, queries the DB once per `manage.py check`,
and returns a structured `Error` per inconsistent row with a clear
fix hint.

## Guardrails NOT added (and why)

- **No new field on Country.** The user spec ("Non introdurre database
  complexity se esiste già un meccanismo") is honoured. The existing
  pattern is layered: `LegalSource.status` + `LegalReview` audit row
  + `CompensationDataset.status` + `CalculationFormula.status` +
  calculator code guard. Each link defends independently.
- **No per-country `*_VERSION` settings.** Would duplicate what
  `LegalReview` already records (reviewer + decision date).
- **No template changes.** `apps/core/public_status.py` already
  enforces premium copy discipline (banned-wording list) and the
  4-country wizards already render the correct
  `legal_assessment`/`inheritance_review` panels.

## Public surface evidence

9 screenshots in this directory document the current state. The key
one — `wizard_fr_post_review_gated_desktop.png` — shows a POST with
valid inputs (`age=35, disability=10%, fault=0%`) + both GDPR
consents lands on a result page that:

- Title: "Risultato preliminare" (Preliminary result) — premium copy.
- Status banner: "VALUTAZIONE LEGALE PRELIMINARE".
- Body: "Il caso è stato ricevuto per una valutazione legale preliminare da parte dello Studio."
- Explanatory paragraph: "The Studio reviews the case manually, on the basis of the verified quantification sources for the relevant jurisdiction. No automatic amount is published before the case has been examined by a lawyer."
- Legal sources cited: **only `Loi n°85-677 du 5 juillet 1985 dite Loi Badinter`** (the APPROVED source). No Mornet, no Gazette.
- No EUR amount anywhere in the page body.
- CTAs: "Richiedi una revisione dello Studio" (primary), "Scarica report PDF" (secondary).
- Disclaimer block: present.
- `noindex, nofollow`: present in `<meta>`.

The funnel is honest end-to-end: the form collects, the calculator
refuses to publish, the result page asks the Studio to take over.

## Tests added (16)

`apps/jurisdictions/test_non_it_readiness_guardrails_p0_mvp_1.py` (11):

1. system check module is importable.
2. check is registered under the `jurisdictions` tag.
3. check is silent in `DEBUG=True`.
4. check is silent when the opt-out flag is False.
5. check passes when every APPROVED source has full audit trail.
6. check fails when an APPROVED source has no APPROVE review row.
7. check fails when source has APPROVE review row (a LegalReview row without `reviewer` cannot exist — FK is non-null PROTECT — so this case is unreachable and treated by the "no review row" path).
8. check fails when source is APPROVED + audit row exists but `legal_reviewer` FK is null on the source.
9. check passes when no APPROVED sources exist at all.
10. audit script exists and is loadable.
11. audit script's `_verdict()` helper returns the expected verdict for each of 5 input shapes (`SCAFFOLD-ONLY`, `READY-FOR-REVIEW`, `APPROVED-INCONSISTENT`, `APPROVED-PARTIAL`, `APPROVED-CONSISTENT`).

`apps/cases/test_france_review_gated_e2e_p0_mvp_1.py` (5):

1. `GET /countries/france/` returns 200; no EUR amount, no banned wording.
2. `GET /wizard/fr/road-accident/` returns 200 with `noindex, nofollow`; no EUR amount, no banned wording.
3. POST without GDPR consents is rejected; consent error surfaces.
4. POST with valid input + both consents redirects to a result page; persisted `Simulation.status == unavailable_requires_legal_validation`; result page carries `noindex, nofollow`, no EUR amount, no banned wording, the review-pending semantics, and the disclaimer.
5. `/disclaimer/` and `/privacy/` are reachable from the FR funnel.

## Verifications

| Command | Result |
|---|---|
| `python manage.py check` | clean (only the expected `core.W001` STUDIO_* dev warning). The new `jurisdictions.E001` check passes — current dev DB has audit-trailed APPROVED sources. |
| `pytest apps/jurisdictions apps/calculators apps/compensation apps/cases apps/legal_sources -q` | **748 passed** in 86 s |
| `pytest apps/jurisdictions/test_non_it_readiness_guardrails_p0_mvp_1.py -q` | **11 passed** in 6.8 s |
| `pytest apps/cases/test_france_review_gated_e2e_p0_mvp_1.py -q` | **5 passed** in 2.8 s |
| `pytest -q` (full) | **1846 passed, 1 skipped** (+16 from P2-SEO-1 baseline 1830, zero regressions) |
| `python scripts/legal_data/audit_non_it_readiness.py` | exit 0; FR/BE/MA/TN all `APPROVED-PARTIAL` (the safe state) |
| `bash scripts/run_quality_gate.sh --no-pytest` | will run as the final verification (see commit log) |
| `git status` after the batch | clean (apart from the explicit P0-MVP-1 diff) |

## What the Studio must sign to flip the gate

Listed in full in `docs/NON_IT_MVP_READINESS_2026-05-10.md` §4. The
short version, for France:

| # | Sign-off | State today | Why it matters |
|---|---|---|---|
| 1 | Loi Badinter LegalReview | **DONE** in dev DB | Cornice normativa — the indivisible legal basis. |
| 2 | Référentiel Mornet 2024 LegalReview | needs_review | Quantification source. Without this, no amount is computable. **Gating sign-off.** |
| 3 | Gazette du Palais 2022 LegalReview | needs_review | Capitalisation table — needed for projected income / future damages. |
| 4 | Nomenclature Dintilhac LegalReview | needs_review | Postes-de-pregiudizio mapping — needed so the PDF report uses the names users expect. |
| 5 | France-specific disclaimer review | (generic disclaimer applies) | Studio confirms the project's generic disclaimer is adequate for France or drafts an addendum. |

Once 2/3/4 are signed in admin and the LegalReview rows recorded
(via the existing admin workflow that the `jurisdictions.E001`
check now enforces audit-trail integrity for), a single follow-up PR
(P0-MVP-1-ACTIVATE) can:

- promote the DRAFT datasets `FR-MORNET-2024-DRAFT` + `FR-GAZETTE-PALAIS-2022-DRAFT`
  to non-DRAFT `status=APPROVED`,
- create the `CalculationFormula(jurisdiction=FR-NATIONAL,
  status=APPROVED)` pointing at engine `france_road_accident_v1` and
  amount_rule `france_dfp_point_value_direct`,
- commit a canonical FR smoke test (mirror the IT 35/10/0 contract),
- pytest green.

The calculator code path is **already wired** — no engine code change
needed. The `_FrancePlaceholderCalculator.compute()` fall-through
disappears the moment the chain is APPROVED end-to-end, and
`FranceRoadAccidentBodilyInjuryCalculator._compute_with_sources` (the
full 12-gate logic that already exists in `apps/calculators/engines/france.py`)
takes over.

## Next batches

1. **P0-MVP-1-ACTIVATE (post-Studio sign-off)** — flip the FR gate.
2. **P0-MVP-2** — Belgium activation, contingent on TI 2020 + OCR for TI 2024.
3. **P0-MVP-3 / P0-MVP-4** — Morocco / Tunisia, contingent on numeric share transcription + (for TN) the dual conflict-of-laws decision.
4. **P1-SEC-3** — WAF/CDN edge security (deferred from previous suggestions).
5. **CI wiring** — port the quality gate + mobile lighthouse to GitHub Actions.
