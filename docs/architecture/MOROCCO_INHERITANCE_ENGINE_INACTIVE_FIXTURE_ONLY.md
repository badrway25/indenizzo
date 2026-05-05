# Morocco inheritance engine — inactive scaffold, fixture-only

**Iter:** `F-morocco-inheritance-engine-inactive-fixture-only`.

This document describes the state of the Morocco international
inheritance calculator after this iter: the engine code path is fully
wired and tested for one fixture-only amount rule
(`morocco_inheritance_fixed_share_direct`), but the public DB has zero
APPROVED MA sources/datasets/formulas, so a
`run_simulation(MA-NATIONAL, international_inheritance)` keeps
returning `unavailable_requires_legal_validation`.

The engine is intentionally inactive on the public path. Only test
fixtures in
`apps/calculators/test_morocco_inheritance_engine_inactive.py`
exercise the executable branch, with a synthetic share spec that
**does not** codify the real Moudawana Livre III in full.

---

## What's ready

### `apps/compensation/services.py`

A new dispatch family is introduced for inheritance-share rules that
consume the formula's parameters directly rather than a matched table
row:

- `SUPPORTED_ENGINES += {"morocco_inheritance_v1"}`
- `SUPPORTED_AMOUNT_RULES += {"morocco_inheritance_fixed_share_direct"}`
- `INHERITANCE_SHARE_AMOUNT_RULES = {"morocco_inheritance_fixed_share_direct"}`
  — a new sibling category to `RANGE_AMOUNT_RULES` and
  `SINGLE_ROW_RANGE_AMOUNT_RULES`.
- `is_inheritance_share_rule(rule)` → True for the family.
- `apply_amount_inheritance_share_rule(rule, *, formula_params,
  input_data)` → `InheritanceShareResult`. Currently dispatches only
  the Morocco rule.
- `_rule_morocco_inheritance_fixed_share_direct(...)` — the rule
  itself: rational arithmetic via `fractions.Fraction` to avoid
  decimal drift, fixed-fraction shares applied first, residual split
  between `sons_group` and `daughters_group` under the classic 2:1
  ratio, optional `estate_value` to convert each fraction into a
  `Decimal` amount.

Output dataclasses:

- `InheritanceAllocation(heir_class, label, share_numerator,
  share_denominator, amount, head_count)` — one entry per heir class
  that received a positive allocation.
- `InheritanceShareResult(estate_total, allocations,
  residual_numerator, residual_denominator)` — the full result. The
  residual is normally zero when the spec covers all classes; it's
  surfaced as a warning by the engine when not.

### `apps/calculators/engines/morocco.py`

The placeholder `MoroccoInternationalInheritanceCalculator` is now a
real engine that mirrors the France/Belgium gating sequence and
dispatches into the inheritance-share family. Order of evaluation:

1. no APPROVED legal source for MA → `UNAVAILABLE`
2. no APPROVED dataset linked → `UNAVAILABLE` (`compensation_dataset_approved`)
3. no APPROVED formula → `UNAVAILABLE` (`calculation_formula_approved`)
4. unknown `engine` → `UNAVAILABLE` (`formula_engine_unknown`)
5. unknown `amount_rule` → `UNAVAILABLE` (`formula_amount_rule_unknown`)
6. rule is not inheritance-share → `UNAVAILABLE`
   (`formula_amount_rule_not_inheritance_share`)
7. required input missing → `INSUFFICIENT_INPUT`
8. `estate_value` invalid (negative / non-numeric) → `INSUFFICIENT_INPUT`
9. zero allocations (no heir class with positive head count) →
   `INSUFFICIENT_INPUT`
10. all gates pass → `CALCULATED`

The engine returns:

- `estimated_min/mid/max` = total allocated estate when
  `estate_value` is provided (otherwise `None`).
- `breakdown` = one `BreakdownItem` per heir class, label includes
  the fraction (e.g. `"Surviving spouse (1/8)"`), `amount_mid`
  carries the per-class amount.
- `assumptions` lists the formula code, the dataset name, and the
  per-class fractions.
- `warnings` flag any non-zero residual fraction or absence of
  `estate_value`.

Public DB outcome (today): step 1 fails because no MA `LegalSource`
is `APPROVED`. The engine never reaches the dispatch branches.

The public status surface is **unchanged**: the MA row of
`apps/core/public_status.py::_RULES` stays at
`("MA", "international_inheritance", _INHERITANCE_REVIEW)`, so the
`/wizard/ma/inheritance/` panel still reads "International inheritance
review" with the no-amounts disclaimer.

---

## What's deliberately fixture-only

This engine is **not** a complete codification of Moudawana Livre III.
The `_rule_morocco_inheritance_fixed_share_direct` rule covers a
narrow shape: fixed fractions for spouse / father / mother and a 2:1
residual split between sons and daughters. Real `faraïd` involve:

- **hajb** (exclusion): a closer heir excludes a more distant one
  (e.g. a son excludes the deceased's brother). The current rule does
  not model exclusion: every heir class with a positive head count
  receives its allocation independently.
- **'awl** (proportional reduction): when the sum of fixed shares
  exceeds unity, all shares are reduced proportionally. The current
  rule rejects `used > 1` by clamping the residual to zero, but does
  not implement 'awl.
- **radd** (return of residual): when fixed shares do not consume
  the estate and no residuary heir is present, the residual returns
  to the fixed-share heirs in proportion to their original shares.
  The current rule surfaces the residual as a warning rather than
  returning it.
- **status taxonomy**: cohabitant / non-cohabitant, agnatic vs.
  cognatic kinship, halfsibling-via-mother vs. halfsibling-via-father,
  grandparents, etc. The current spec admits only spouse / father /
  mother / sons / daughters.

A future iter that wires legal-reviewed Moudawana tables would extend
`shares_spec` (or migrate to a different rule key) to encode these
mechanisms. None of the above is in scope for this iter.

---

## Why no real Moudawana article numbers

The project's contract is "*meglio nessun calcolo che un calcolo
falso*". The synthetic share spec uses heir-class names that are
generic legal institutes (spouse, father, mother, sons, daughters);
it does not cite Moudawana article numbers as numeric thresholds, and
the test file deliberately uses round synthetic estate values
(`800 000`, `240 000`) that are not Moudawana-specific.

A real activation will require not just a share spec but also:

- **Moudawana Livre III mapping** — the Studio reads the Code de la
  famille articles (~Articles 321-395 of the 2004 codification) and
  emits a tabular `shares_spec` per heir-class combination. This is
  legal review, not engineering.
- **EU Regulation 650/2012 decision** — Article 22 lets the testator
  choose national law; Articles 23-25 spell out renvoi, public-order
  exceptions, fragmentation. The Studio decides per case whether the
  Moroccan share spec applies, or whether a different applicable law
  (French, Belgian, Italian) governs. The engine cannot make that
  decision today.

---

## Future formula `parameters` schema

When Studio promotes the Moroccan source to APPROVED, the
`CalculationFormula` for the international-inheritance scope will
declare:

```json
{
  "engine": "morocco_inheritance_v1",
  "amount_rule": "morocco_inheritance_fixed_share_direct",
  "requires": ["heirs"],
  "shares": {
    "spouse":          "1/8",
    "father":          "1/6",
    "mother":          "1/6",
    "sons_group":      "remainder_2_to_1",
    "daughters_group": "remainder_2_to_1"
  }
}
```

The engine reads this and dispatches into
`apply_amount_inheritance_share_rule`. The `shares` mapping is the
single source of truth for the rule; changing it changes the
allocation without code changes.

This iter does **not** create such a formula in the DB. Any future
iter that does will be subject to a `LegalReview` from a Studio
reviewer before promotion.

---

## What's required to activate Morocco on the public path

Each step is a separate iter. Until all six land, MA stays
`unavailable` and the public status panel keeps reading
"International inheritance review".

1. **Moudawana Livre III mapping** — Studio produces a tabular
   `shares_spec` that covers the realistic heir combinations the
   firm sees in practice. The output is a JSON document that the
   `parameters["shares"]` field can host directly, plus a written
   note explaining what the spec does not cover (hajb, 'awl, radd,
   etc.).
2. **EU Regulation 650/2012 decision** — Studio writes a per-case
   decision tree: when Moroccan law applies, when French / Belgian
   / Italian law applies via renvoi, and when public-order
   exceptions kick in. This is not encoded in the engine; it
   determines whether the calculator runs the Moroccan share spec at
   all for a given case.
3. **Studio legal review** of the Moroccan source →
   `LegalReview.decision=approve` → `LegalSource(slug='ma-...').status
   = APPROVED`.
4. **Promote / create the dataset** — a `CompensationDataset` keyed
   to MA international inheritance with `status=APPROVED`.
5. **Create the MA `CalculationFormula`** with the schema above and
   `status=APPROVED`. Same gating: only an APPROVED formula on an
   APPROVED dataset on an APPROVED source can run.
6. **Wizard input completeness** — the public
   `/wizard/ma/inheritance/` form must collect the heirs structure
   (spouse / father / mother / sons / daughters counts plus an
   optional `estate_value`) in a way the form's `to_input_data()`
   maps to the engine's expected keys. The current form collects
   `children_count` etc. but does not split into sons / daughters;
   wiring that gender split is a UX iter, not a calculator iter.
7. **Smoke test** — at least one canonical heirs × estate_value
   tuple committed in `apps/calculators/test_*.py`. The smoke
   values must come from the legal-reviewed Moudawana tables and be
   cited explicitly, not invented.

After step 7, flip the public status: change
`("MA", "international_inheritance", _INHERITANCE_REVIEW)` →
`_AVAILABLE` in `apps/core/public_status.py`.

---

## Cross-references

- Engine: `apps/calculators/engines/morocco.py`
- Service helpers: `apps/compensation/services.py`
- Tests: `apps/calculators/test_morocco_inheritance_engine_inactive.py`
- Public status surface: `apps/core/public_status.py`
- Wizard view: `apps/cases/views.py::wizard_morocco_inheritance`
- Wizard template: `templates/public/wizard_morocco_inheritance.html`
- Legal review package: `docs/legal_sources/MOROCCO_LEGAL_REVIEW_PACKAGE.md`
