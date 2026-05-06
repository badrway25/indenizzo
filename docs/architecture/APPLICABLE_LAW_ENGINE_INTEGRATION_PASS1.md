# Applicable-law skeleton — engine integration, pass 1

**Iter:** `F-applicable-law-skeleton-engine-integration-pass1`.

This pass connects the applicable-law decision skeleton (introduced
in `EU_650_APPLICABLE_LAW_DECISION_ENGINE_SKELETON.md`) to the MA / TN
inheritance engines. Even with an APPROVED source / dataset / formula
in the test DB, the engine now refuses to compute shares whenever
the decision flags manual review, insufficient context, low
confidence or a missing preliminary law country. Public DB stays
unavailable for FR / BE / MA / TN; this iter only changes the
fixture-only path.

---

## Service contract

`apps/calculators/inheritance_applicable_law.py` exposes two new
helpers:

```python
def can_run_inheritance_share_engine(
    decision: ApplicableLawDecision | None,
) -> bool: ...

def inheritance_engine_block_reason(
    decision: ApplicableLawDecision | None,
) -> str: ...
```

`can_run_inheritance_share_engine` is **strict**: it returns `True`
only when

- `decision_key == "habitual_residence_default"` (no professio juris
  candidate, no cross-border fragmentation, no insufficient context),
- `requires_manual_review is False`,
- `preliminary_law_country` is non-empty,
- `confidence in {"medium", "high"}`.

Any other shape (including `decision is None`) returns `False`.

`inheritance_engine_block_reason` returns a stable internal slug
that the engine surfaces under `output_data["missing_documents"]`
(audit-only — the public template never iterates it):

| Decision shape                                  | Slug                                       |
|-------------------------------------------------|--------------------------------------------|
| `decision is None`                              | `applicable_law_decision_missing`          |
| `decision_key == insufficient_context`          | `applicable_law_insufficient_context`      |
| `requires_manual_review is True`                | `applicable_law_manual_review_required`    |
| `preliminary_law_country` empty                 | `applicable_law_missing_law_country`       |
| `confidence` low                                | `applicable_law_low_confidence`            |
| Otherwise (gate passes)                         | `""`                                       |

---

## Cases that block

The gate blocks the share engine in **every** non-trivial case:

- **Has will = True** → professio juris candidate; manual review
  required.
- **Assets in 2+ countries** → cross-border fragmentation flag.
- **Nationality differs from last residence** → renvoi /
  national-vs-residence law choice; manual review.
- **Three+ countries** → `cross_border_fragmentation` decision_key,
  also blocked.
- **Missing last residence** → `insufficient_context`; the engine
  cannot tell which jurisdiction's law applies.
- **No applicable_law_decision attached at all** → the engine
  refuses to guess.

The only path that runs the share engine is the simplest possible:
last-residence provided, single-asset country matching residence,
nationality matching residence (or omitted), no will.

---

## Why it is not automatic legal advice

The skeleton, even with this gate, never asserts "the applicable law
is X". It produces a *preliminary working hypothesis* with a stable
checklist of fired heuristics. The gate's role is purely to prevent
the engine from publishing an indicative quote when the case has any
cross-border / will / nationality nuance that the Studio must read
manually first.

The contract "*meglio nessun calcolo che un calcolo falso*" applies:
the engine's default stance is now "do nothing without Studio
review", and only the simplest fixture-only path lifts that stance.

The decision payload + block reason live under
`output_data["internal"]["applicable_law_decision"]` and
`output_data["missing_documents"]` — both are server-side only. The
public template renders the curated `PublicResultMessage` plus the
applicable-law hint added in the previous iter:

> *Lo Studio esaminerà la legge applicabile e gli elementi
> transfrontalieri prima che vengano calcolate quote ereditarie.*

---

## Run-simulation flow refactor

`apps/cases/services.py::run_simulation` now:

1. **Pre-attaches** the applicable-law decision to the payload via
   `_preattach_applicable_law_decision_to_payload(payload, case_type=...)`
   — only for inheritance case types. The decision dict ends up
   under `payload["applicable_law_decision"]` so the engine can read
   it during compute.
2. Calls the calculator as before.
3. **Post-attaches** the same decision under
   `output_data["internal"]["applicable_law_decision"]` for audit.
   Reuses the dict already in the payload (no second evaluation).

Road-accident case types are skipped on both attach paths — their
`output_data` shape stays byte-identical.

---

## Engine wiring (MA / TN)

Both `apps/calculators/engines/morocco.py` and
`apps/calculators/engines/tunisia.py` add a new gate immediately
before their share-rule dispatch:

```python
block = _gate_inheritance_engine_on_applicable_law(input_data)
if block is not None:
    return self._build_result(
        status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
        sources=source_refs,
        warnings=[
            "Applicable-law context requires Studio review before "
            "any inheritance shares can be produced. The engine "
            "refuses to compute on the fixture-only path until a "
            "legal reviewer reads the family / cross-border "
            "elements of the case."
        ],
        missing_documents=[block],
    )
```

The helper rebuilds an `ApplicableLawDecision` from the dict in
`input_data["applicable_law_decision"]` and feeds it to
`can_run_inheritance_share_engine`. When the gate blocks, it returns
the corresponding slug from `inheritance_engine_block_reason`.

The TN engine keeps its existing `shares_spec_invalid` gate (the
strict over-allocation check); the new gate sits before it so a case
that needs manual review never even reaches the spec check.

---

## Tests

`apps/calculators/test_applicable_law_engine_integration.py` covers
the spec + a few regression nets:

1. MA simple context → engine computes shares (`CALCULATED`).
2. MA + `has_will=True` → unavailable, `missing_documents` carries
   `applicable_law_manual_review_required`.
3. MA + multi-country assets → unavailable.
4. MA + nationality mismatch → unavailable.
5. MA missing residence → unavailable, slug
   `applicable_law_insufficient_context`.
6. TN simple context → engine computes shares.
7. TN cross-border → unavailable.
8. `output_data["internal"]["applicable_law_decision"]` populated
   with the full decision payload.
9. Public result HTML contains **none** of the technical decision
   strings (decision_key, applied_rules, requires_manual_review,
   any rule slug, any block_reason slug, any decision-key slug).
10. `public_status` for MA / TN remains
    `STATUS_INHERITANCE_REVIEW`.
11. Italia 35 / 10 / 0 → 26 268 / 27 353 / 28 439 EUR; road-accident
    `output_data["internal"]` is not populated.

Plus two regression nets:

- `test_can_run_helper_smoke` — direct unit test of the helper.
- `test_inheritance_result_renders_single_h1_after_gate` — H1 net.

The existing inheritance fixture-only tests in
`test_morocco_inheritance_engine_inactive.py` and
`test_tunisia_inheritance_engine_inactive.py` were updated to
include `deceased_country_of_last_residence` so the gate passes for
their happy paths.

---

## Public result confirmation

The result page never surfaces:

- `applicable_law_decision`
- `decision_key`, `preliminary_law_country`, `applied_rules`,
  `requires_manual_review`, `confidence`
- Any rule slug (`rule_habitual_residence_default`,
  `rule_has_will_present`, `rule_assets_multi_country`,
  `rule_nationality_differs_from_residence`)
- Any decision-key slug (`habitual_residence_default`,
  `professio_juris_candidate`, `cross_border_fragmentation`,
  `insufficient_context`)
- Any block-reason slug
  (`applicable_law_decision_missing`,
  `applicable_law_insufficient_context`,
  `applicable_law_manual_review_required`,
  `applicable_law_low_confidence`,
  `applicable_law_missing_law_country`)

Verified by tests + the
`scripts/audit_public_result_messages.py` audit (verdict OK, 6/6
fixtures clean).

---

## Visual review notes

Screenshots live under
`docs/screenshots/live_qa/applicable_law_engine_integration_pass1/after/`.
The capture script blocks the Tailwind CDN to prove the local
`static/css/site.css` carries the layout; every shot is styled.

**Desktop 1440 × 900.**

- `wizard_ma_inheritance.png`, `wizard_tn_inheritance.png` — sand
  background, hero, premium card with the three sections (about /
  family / patrimony) + ink CTA.
- `result_ma_simple_post.png` — public message + hint card; no
  technical leaks. Status `unavailable` because the live DB has no
  APPROVED source.
- `result_ma_cross_border_post.png` — same public layout. The gate
  would have fired even if the source had been APPROVED, but the
  user-visible page is identical: the curated public message keeps
  the experience stable across decision shapes.
- `result_tn_simple_post.png` — same chrome, TN copy.
- `wizard_ma_inheritance_ar.png` — full RTL Arabic, hero, status
  panel, premium card. CTAs and field cards mirror correctly.

**Mobile 375 × 800.**

- `wizard_ma_inheritance.png` — single-column stack, no horizontal
  overflow, the family-situation 3-column grid collapses to a
  vertical list.
- `result_ma_post.png` — premium narrow result page, hint card
  visible, three CTAs stack.
- `wizard_ma_inheritance_ar.png` — RTL stack, helper text wraps
  correctly.

**Local CSS confirmation.** Every shot was captured with
`cdn.tailwindcss.com` blocked at the network layer. The pages still
render with the project's full premium chrome (sand background,
ink/gold palette, rounded-3xl cards, shadow-card, serif headings,
RTL helpers). This proves the iter does not regress the local-CSS
work from `F-frontend-local-css-premium-visual-qa-pass1`.

---

## No DB / legal changes

No migration, no model edit, no `LegalSource`, `LegalReview`,
`CompensationDataset`, `CompensationTableRow`, `CalculationFormula`
created or promoted by this iter.

## MA / TN still no automatic public shares

`public_status` for MA / TN remains `STATUS_INHERITANCE_REVIEW`. POST
on the public DB still returns
`unavailable_requires_legal_validation` because no APPROVED source
exists. The new gate only changes the fixture-only path inside the
test DB — which is exactly where manual review needs the strictest
behaviour.

## Italia preserved

`test_italy_smoke_unchanged_with_applaw_integration`:
35 / 10 / 0 → 26 268 / 27 353 / 28 439 EUR. Road-accident
simulations don't get the inheritance enrichment.

---

## Hygiene + audits + lint

- `audit_public_content_hygiene.py`: **ok**, 0 issues, 6/6 rules.
- `audit_public_result_messages.py`: **OK**, 6/6 fixtures clean.
- `run_public_lighthouse_audit.py --mode playwright`: **OK**, 8/8
  routes pass.
- `manage.py makemigrations --check`: No changes detected.
- `manage.py check`: 0 issues.
- `compilemessages`: OK.
- `pytest -q`: 1272 passed, 1 skipped (1259 prior + 13 new).
- `ruff check .`: All checks passed.
- `black --check .`: 272 files, 0 to reformat.

---

## Cross-references

- Helpers: `apps/calculators/inheritance_applicable_law.py`
  - `can_run_inheritance_share_engine`
  - `inheritance_engine_block_reason`
  - `BLOCK_REASON_*` slugs
- Service: `apps/cases/services.py`
  - `_preattach_applicable_law_decision_to_payload`
  - `_attach_applicable_law_decision`
- Engines:
  - `apps/calculators/engines/morocco.py`
  - `apps/calculators/engines/tunisia.py`
- Tests: `apps/calculators/test_applicable_law_engine_integration.py`
- Capture script: `scripts/capture_applicable_law_engine_integration_pass1.py`
- Sibling iters:
  - `docs/architecture/EU_650_APPLICABLE_LAW_DECISION_ENGINE_SKELETON.md`
  - `docs/architecture/FRONTEND_LOCAL_CSS_PREMIUM_VISUAL_QA_PASS1.md`
