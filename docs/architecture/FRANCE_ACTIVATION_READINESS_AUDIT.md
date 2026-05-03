# FR road-accident — activation readiness audit

**Iter:** `F-france-activation-readiness-audit`.

**Generated:** `2026-05-03T17:40:52+00:00`.

Read-only audit of the FR road-accident pipeline. The script that
produced this file (`scripts/legal_data/audit_france_activation_readiness.py`)
makes **no DB writes** and never invokes `run_simulation`. It only
inspects model state, the engine registry, and the wizard URL surface.

## 1. Executive summary

**Verdict:** `OFFICIAL-ONLY`.

Badinter validated as official source; Mornet/Gazette stay needs_review -> calculator stays unavailable. Activating anything beyond the source validation is NO-GO until a Studio LegalReview promotes Mornet or Gazette.

## 2. Current status

The current state is the conservative one:

- Loi Badinter (the *cornice normativa*) is mechanically authenticated
  via manual attach + 11/11 structural markers vs Légifrance — it is
  the file the report layer can already cite with a sha256 and a
  Légifrance canonical URL.
- The two *quantification* sources (Mornet 2024, Gazette du Palais 2022)
  remain in `needs_review`. Their candidate datasets exist in DB as
  `DRAFT` only and never feed the calculator.
- The FR calculator class is registered and the engine + amount_rule
  are wired in `apps.compensation.services`, but the gating refuses to
  produce a number while no APPROVED FR `CalculationFormula` exists.
- The public wizard renders without calling the calculator.

## 3. Sources

| Check | Status | Details |
|---|---|---|
| Badinter — official legal basis | **PASS** | status=needs_review \| manual_attach_block=present \| official_source_validation_block=present \| manual_attach.sha256=6165313bad9d \| manual_attach.marker_check_passed=True \| official_source_validation.structural_markers=11/11 |
| fr-referentiel-mornet-2024 — quantification source | **BLOCKED** | status=needs_review \| reliability=high \| 1 attachment(s) \| legal_reviewer=unset |
| fr-bareme-capitalisation-gazette-palais-2022 — quantification source | **BLOCKED** | status=needs_review \| reliability=high \| 1 attachment(s) \| legal_reviewer=unset |

## 4. Candidate datasets

| Check | Status | Details |
|---|---|---|
| Dataset FR-MORNET-2024-DRAFT | **PASS** | status=draft \| is_usable_for_calculations=False \| fr_dfp_per_age_disability_amount_per_point=180/180 [OK]; fr_prejudice_affection_per_relation_amount=11/11 [OK] |
| Dataset FR-GAZETTE-PALAIS-2022-DRAFT | **PASS** | status=draft \| is_usable_for_calculations=False \| fr_capitalisation_viagere_per_age_sex_rate_coefficient=416/416 [OK]; fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient=3752/3752 [OK]; fr_anticipated_payment_years_per_age_sex_rate_years=20/20 [OK] |

## 5. Engine

| Check | Status | Details |
|---|---|---|
| FR calculator class registered | **PASS** | class=FranceRoadAccidentBodilyInjuryCalculator |
| france_road_accident_v1 in SUPPORTED_ENGINES | **PASS** | registered=True |
| france_dfp_point_value_direct in SUPPORTED_AMOUNT_RULES | **PASS** | registered=True \| is_single_row_range=True |

## 6. Formula status

| Check | Status | Details |
|---|---|---|
| CalculationFormula(FR) count | **PASS** | count=0; expected 0 — no FR formula must exist on the public path until Studio approves Mornet/Gazette. |

## 7. Wizard / public UX

| Check | Status | Details |
|---|---|---|
| GET /healthz/ | **PASS** | http_status=200 |
| GET /countries/france/ | **PASS** | http_status=200 |
| GET /wizard/fr/road-accident/ | **PASS** | http_status=200 |
| GET /contact/ | **PASS** | http_status=200 |

The wizard URLs are probed via Django's test client `GET` — no
Simulation row is persisted on a GET; only a POST would. The audit
deliberately never POSTs to avoid leaving a calculator-pending audit
trail in the DB.

## 8. Activation blockers

The blockers below must each be resolved before the FR calculator can
publish numbers on the public path. Each blocker is independently
necessary; no shortcut exists.

1. **Mornet 2024 legal review.** `LegalSource(slug='fr-referentiel-mornet-2024')`
   stays `needs_review`. Promotion requires a `LegalReview.decision=approve`
   from a Studio reviewer + `legal_reviewer` FK valorised. Mornet is a
   *barème privato* (not state-published) — the reviewer must explicitly
   accept the consequences.
2. **Gazette du Palais 2022 legal review.** Same as above for
   `fr-bareme-capitalisation-gazette-palais-2022`. Gazette is a
   jurisprudence-derived capitalisation table; its use as an official
   quantification basis is an editorial decision Studio must sign.
3. **Dataset promotion.** `FR-MORNET-2024-DRAFT` and
   `FR-GAZETTE-PALAIS-2022-DRAFT` must be relabelled to non-DRAFT
   (e.g. `FR-MORNET-2024`) and `status=APPROVED`. The DRAFT label is
   load-bearing: `import_france_candidate_datasets` refuses to write
   into a non-DRAFT dataset, and `verify_france_candidate_import.py`
   asserts the DRAFT one stays DRAFT.
4. **Formula creation.** A `CalculationFormula(status=APPROVED)` must
   point at the engine `france_road_accident_v1` + amount_rule
   `france_dfp_point_value_direct`, declaring `row_type`, `row_match`,
   `requires`, `fault_reduction`. Currently zero FR formulas exist.
5. **Smoke test calculator FR.** A canonical (age × disability ×
   fault) tuple must be committed in `apps/calculators/test_*.py`,
   matching the IT 35/10/0 = 26 268 / 27 353 / 28 439 EUR contract.
6. **Mapping Dintilhac.** The poste-di-pregiudizio nomenclature
   (`fr-nomenclature-dintilhac-2005`) is in DB as `needs_review`.
   It is needed for the report layer to translate engine output
   into the postes the user expects to see.

## 9. Safe activation paths

Three options, presented in increasing aggression. Path C is **not**
pursued in this iter; it is documented for completeness.

### Path A — Conservative (current default)

- Keep FR road-accident `unavailable_requires_legal_validation`.
- Continue work on Belgium / Morocco / Tunisia in parallel.
- No FR formula creation, no calculator activation.
- Recommended until Mornet/Gazette legal reviews land.

### Path B — Official-only

- Promote Loi Badinter `LegalSource.status=APPROVED` (LegalReview
  signed by Studio) — this records that the *cornice normativa* is
  validated.
- Calculator stays `unavailable` because no quantification dataset is
  APPROVED yet. The wizard explicitly says "le quantification reste
  pendante" instead of just "validation pending".
- Allows the report layer to cite Loi Badinter without numbers.
- Does NOT activate the calculator.

### Path C — Explicit indicative-mode (NOT pursued in this iter)

- Treats Mornet 2024 / Gazette 2022 as *indicative* private barèmes
  rather than official quantification sources.
- Public UI must show prominently: "Estimation indicative — barème
  Mornet/Gazette du Palais — non opposable, non normatif, non avis
  juridique."
- Requires a config flag `FRANCE_ENABLE_INDICATIVE_CALCULATOR=false`
  by default, plus a separate iter to wire the disclaimer copy and
  ensure the report PDF carries the same disclaimer prominently.
- Activation requires explicit Studio sign-off in writing on a per-
  release basis.
- **This iter does not implement Path C.** It is documented so the
  next contributor knows the option exists and the constraints around
  it.

## 10. What must NOT happen

- No automated promotion of Mornet/Gazette to APPROVED. Promotion is
  a human decision tracked via `LegalReview`.
- No backdoor formula creation that bypasses the engine + rule
  registries in `apps.compensation.services`.
- No partial activation that surfaces numbers while disclaiming them
  in fine print: either the calculator returns numbers fully or it
  returns `unavailable`.
- No removal of the DRAFT dataset rows. They are the upstream
  extractor's traceability: deleting them breaks audit forensics.
- No promotion that copies real Mornet/Gazette amounts into the test
  fixtures. The static guard in
  `apps/calculators/test_france_engine_inactive.py` is precisely there
  to prevent this drift.

## 11. Rollback plan

If a future iter prematurely activates the FR calculator and the
result needs to be undone:

1. Set the offending `CalculationFormula.status` back to `DRAFT` (do
   not delete: keep the audit trail).
2. Set the offending `CompensationDataset.status` back to `DRAFT`
   (do not delete; do not re-run `import_france_candidate_datasets`).
3. Set the offending `LegalSource.status` back to `needs_review`
   (do not delete; keep `LegalReview` rows for audit).
4. Run `python scripts/legal_data/verify_france_candidate_import.py`
   to confirm DRAFT counts are intact.
5. Run `pytest -q` and `python scripts/live_simulation_matrix.py` to
   confirm Italia 35/10/0 = 26 268 / 27 353 / 28 439 EUR is still
   green and FR is `unavailable_requires_legal_validation` again.

## 12. Next tasks

1. Studio session to schedule the Mornet 2024 + Gazette 2022 legal
   reviews. Output: signed `LegalReview` rows.
2. Iter `F-france-formula-bootstrap` (proposed): once both sources
   are APPROVED, create the FR `CalculationFormula` + locked smoke
   test. This iter is BLOCKED until step 1 lands.
3. Iter `F-france-dintilhac-mapping` (proposed): map calculator
   outputs to Dintilhac postes for the report layer.

---

*This file is regenerated by
`python scripts/legal_data/audit_france_activation_readiness.py`. Do
not edit by hand — re-run the script and commit the diff.*
