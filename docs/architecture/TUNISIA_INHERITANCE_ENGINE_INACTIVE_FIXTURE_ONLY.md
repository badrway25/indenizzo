# Tunisia inheritance engine — inactive scaffold, fixture-only

**Iter:** `F-tunisia-inheritance-engine-inactive-fixture-only`.

This document describes the state of the Tunisia international
inheritance calculator after this iter: the engine code path is fully
wired and tested for one fixture-only amount rule
(`tunisia_inheritance_fixed_share_direct`), but the public DB has
zero APPROVED TN sources/datasets/formulas, so a
`run_simulation(TN-NATIONAL, international_inheritance)` keeps
returning `unavailable_requires_legal_validation`.

The engine is intentionally inactive on the public path. Only test
fixtures in
`apps/calculators/test_tunisia_inheritance_engine_inactive.py`
exercise the executable branch, with a synthetic share spec that
**does not** codify the real Code du statut personnel Livre IX in
full.

This is the twin of the Morocco iter
(`docs/architecture/MOROCCO_INHERITANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md`).
Wherever the two engines could share more code than they already do
through the `INHERITANCE_SHARE_AMOUNT_RULES` family in
`apps.compensation.services`, the country-specific entry points are
deliberate: each jurisdiction must have its own activation gate
(source / dataset / formula) so that promoting one country's data
never silently activates the other.

---

## What's ready

### `apps/compensation/services.py`

The dispatch family `INHERITANCE_SHARE_AMOUNT_RULES` introduced for
Morocco is extended to host the Tunisia rule:

- `SUPPORTED_ENGINES += {"tunisia_inheritance_v1"}`
- `SUPPORTED_AMOUNT_RULES += {"tunisia_inheritance_fixed_share_direct"}`
- `INHERITANCE_SHARE_AMOUNT_RULES += {"tunisia_inheritance_fixed_share_direct"}`
- `apply_amount_inheritance_share_rule(...)` now dispatches both MA
  and TN rules.
- New `_rule_tunisia_inheritance_fixed_share_direct(...)` mirrors
  the MA rule's shape but with two deliberate differences:
  1. **Strict over-allocation handling.** When the sum of fixed-
     fraction shares declared in `parameters["shares"]` exceeds 1,
     the rule raises `InvalidInheritanceShareSpec`. Real Tunisian
     inheritance applies 'awl (proportional reduction); the fixture
     rule does not, so the engine surfaces the misconfiguration
     instead of masking it.
  2. **No residual heirs ⇒ residual stays explicit.** When fixed
     shares allocate < 1 and no class is wired to
     `remainder_2_to_1` (or residual classes have zero head_count),
     the residual fraction is reported verbatim rather than absorbed
     silently. Real `radd` belongs to the Studio mapping iter, not
     this scaffold.
- New exported exception `InvalidInheritanceShareSpec` (subclass of
  `ValueError`) — caught by the TN engine to route to `UNAVAILABLE`
  with a `shares_spec_invalid` diagnostic.

The output dataclasses (`InheritanceAllocation`,
`InheritanceShareResult`) are unchanged: this iter reuses them
verbatim.

### `apps/calculators/engines/tunisia.py`

The placeholder `TunisiaInternationalInheritanceCalculator` is now a
real engine that mirrors France/Belgium/Morocco gating and dispatches
into the inheritance-share family. Order of evaluation:

1. no APPROVED legal source for TN → `UNAVAILABLE`
2. no APPROVED dataset linked → `UNAVAILABLE` (`compensation_dataset_approved`)
3. no APPROVED formula → `UNAVAILABLE` (`calculation_formula_approved`)
4. unknown `engine` → `UNAVAILABLE` (`formula_engine_unknown`)
5. unknown `amount_rule` → `UNAVAILABLE` (`formula_amount_rule_unknown`)
6. rule is not inheritance-share → `UNAVAILABLE`
   (`formula_amount_rule_not_inheritance_share`)
7. required input missing → `INSUFFICIENT_INPUT`
8. `estate_value` invalid (negative / non-numeric) → `INSUFFICIENT_INPUT`
9. share spec structurally invalid (sum > 1) → `UNAVAILABLE`
   (`shares_spec_invalid`)
10. zero allocations (no heir class with positive head count) →
    `INSUFFICIENT_INPUT`
11. all gates pass → `CALCULATED`

The engine returns the same shape as Morocco:

- `estimated_min/mid/max` = total allocated estate when
  `estate_value` is provided (otherwise `None`).
- `breakdown` = one `BreakdownItem` per heir class, label includes
  the fraction (e.g. `"Surviving spouse (1/8)"`), `amount_mid`
  carries the per-class amount.
- `assumptions` lists the formula code, the dataset name, and the
  per-class fractions.
- `warnings` flag any non-zero residual fraction or absence of
  `estate_value`.

Public DB outcome (today): step 1 fails because no TN `LegalSource`
is `APPROVED`. The engine never reaches the dispatch branches.

The public status surface is **unchanged**: the TN row of
`apps/core/public_status.py::_RULES` stays at
`("TN", "international_inheritance", _INHERITANCE_REVIEW)`, so the
`/wizard/tn/inheritance/` panel still reads "International
inheritance review" with the no-amounts disclaimer.

---

## What's deliberately fixture-only

This engine is **not** a complete codification of CSP Livre IX. The
`_rule_tunisia_inheritance_fixed_share_direct` rule covers a narrow
shape: fixed fractions for spouse / mother / father and a 2:1
residual split between sons and daughters. Real Tunisian inheritance
involves:

- **'awl** (proportional reduction): when the sum of fixed shares
  exceeds unity, all shares are reduced proportionally. The current
  rule raises `InvalidInheritanceShareSpec` and the engine routes to
  `UNAVAILABLE` instead of silently applying 'awl.
- **radd** (return of residual): when fixed shares do not consume
  the estate and no residuary heir is present, the residual returns
  to the fixed-share heirs in proportion to their original shares.
  The current rule surfaces the residual as a warning rather than
  returning it.
- **hajb** (exclusion): a closer heir excludes a more distant one.
  The current rule does not model exclusion: every heir class with a
  positive head count receives its allocation independently.
- **status taxonomy**: cohabitant / non-cohabitant, agnatic vs.
  cognatic kinship, halfsibling-via-mother vs.
  halfsibling-via-father, grandparents, and the specific Tunisian
  modernisations introduced after 1956. The current spec admits only
  spouse / father / mother / sons / daughters.

A future iter that wires legal-reviewed CSP tables would extend
`shares_spec` (or migrate to a different rule key) to encode these
mechanisms. None of the above is in scope for this iter.

---

## Why no real CSP / Loi 98-97 article numbers

The project's contract is "*meglio nessun calcolo che un calcolo
falso*". The synthetic share spec uses heir-class names that are
generic legal institutes (spouse, father, mother, sons, daughters);
it does not cite CSP Livre IX article numbers as numeric thresholds,
and the test file deliberately uses round synthetic estate values
(`1 200 000`) that are not CSP-specific.

A real activation will require not just a share spec but also:

- **CSP Livre IX mapping** — the Studio reads the Code du statut
  personnel (Loi n° 56-1 du 13 août 1956 et modifications) and emits
  a tabular `shares_spec` per heir-class combination. This is legal
  review, not engineering.
- **Loi n° 98-97 mapping** — the Code de droit international privé
  rules on conflict of laws for cross-border inheritance. The Studio
  decides per case whether Tunisian law applies or whether a
  European applicable law (French / Belgian / Italian) governs.
- **EU Regulation 650/2012 coordination** — Article 22 lets the
  testator choose national law; Articles 23-25 spell out renvoi,
  public-order exceptions, fragmentation. The Studio decides per
  case whether the Tunisian share spec applies, or whether a
  different applicable law governs. The engine cannot make that
  decision today.

---

## Future formula `parameters` schema

When Studio promotes the Tunisian source to APPROVED, the
`CalculationFormula` for the international-inheritance scope will
declare:

```json
{
  "engine": "tunisia_inheritance_v1",
  "amount_rule": "tunisia_inheritance_fixed_share_direct",
  "requires": ["heirs"],
  "shares": {
    "spouse":          "1/8",
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

## What's required to activate Tunisia on the public path

Each step is a separate iter. Until all seven land, TN stays
`unavailable` and the public status panel keeps reading
"International inheritance review".

1. **CSP Livre IX mapping** — Studio produces a tabular
   `shares_spec` that covers the realistic heir combinations the
   firm sees in practice. The output is a JSON document that the
   `parameters["shares"]` field can host directly, plus a written
   note explaining what the spec does not cover ('awl, radd, hajb,
   etc.).
2. **Loi n° 98-97 mapping** — Studio writes a per-case decision
   tree on conflict of laws: when Tunisian law applies, when a
   European law applies via renvoi, when public-order exceptions
   kick in.
3. **EU Regulation 650/2012 coordination** — same exercise viewed
   from the European side; the cross-border decision tree must
   converge with the Loi n° 98-97 mapping.
4. **Studio legal review** of the Tunisian source →
   `LegalReview.decision=approve` →
   `LegalSource(slug='tn-...').status = APPROVED`.
5. **Promote / create the dataset** — a `CompensationDataset` keyed
   to TN international inheritance with `status=APPROVED`.
6. **Create the TN `CalculationFormula`** with the schema above and
   `status=APPROVED`. Same gating: only an APPROVED formula on an
   APPROVED dataset on an APPROVED source can run.
7. **Wizard input completeness** — the public
   `/wizard/tn/inheritance/` form must collect the heirs structure
   (spouse / father / mother / sons / daughters counts plus an
   optional `estate_value`) in a way the form's `to_input_data()`
   maps to the engine's expected keys. The current form collects
   `children_count` etc. but does not split into sons / daughters;
   wiring that gender split is a UX iter, not a calculator iter
   (and is shared with Morocco).
8. **Smoke test** — at least one canonical heirs × estate_value
   tuple committed in `apps/calculators/test_*.py`. The smoke
   values must come from the legal-reviewed CSP tables and be cited
   explicitly, not invented.

After step 8, flip the public status: change
`("TN", "international_inheritance", _INHERITANCE_REVIEW)` →
`_AVAILABLE` in `apps/core/public_status.py`.

---

## Cross-references

- Engine: `apps/calculators/engines/tunisia.py`
- Service helpers: `apps/compensation/services.py`
- Tests: `apps/calculators/test_tunisia_inheritance_engine_inactive.py`
- Public status surface: `apps/core/public_status.py`
- Wizard view: `apps/cases/views.py::wizard_tunisia_inheritance`
- Wizard template: `templates/public/wizard_tunisia_inheritance.html`
- Sibling iter (Morocco):
  `docs/architecture/MOROCCO_INHERITANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md`
