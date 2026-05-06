# EU Reg. 650/2012 — applicable-law decision engine, skeleton pass 1

**Iter:** `F-eu-650-2012-applicable-law-decision-engine-skeleton`.

This pass introduces a structured, audit-friendly skeleton that
turns the wizard's qualitative inheritance inputs into a
**preliminary** applicable-law assessment. The skeleton is
intentionally narrow: it never claims a final legal conclusion, it
never performs renvoi, public-policy exceptions, or ``ordre public``
overrides automatically, and its output is **never rendered
verbatim on the public surface**. It is meant as a structured
checklist that a Studio reviewer reads alongside the case before
deciding the actual applicable law.

The pass also surfaces a single, premium, translatable hint on the
public result page for inheritance cases:

> *The Studio will review the applicable law and cross-border
> elements before any shares are calculated.*

That hint is the only user-facing outcome of the skeleton. Every
other output (decision_key, applied_rules, warnings, reasons) is
stashed under `Simulation.output_data["internal"]["applicable_law_decision"]`
for audit / Studio review and is suppressed on the public template.

---

## What the skeleton does

`apps/calculators/inheritance_applicable_law.py` exposes:

```python
@dataclass(frozen=True)
class ApplicableLawInput:
    deceased_country_of_last_residence: str | None
    nationality: str | None
    has_will: bool | None
    assets_countries: tuple[str, ...]
    forum_country: str | None

@dataclass(frozen=True)
class ApplicableLawDecision:
    decision_key: str  # one of four narrow stable keys
    preliminary_law_country: str | None
    confidence: "low" | "medium" | "high"
    requires_manual_review: bool
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    applied_rules: tuple[str, ...]

evaluate_inheritance_applicable_law(payload) -> ApplicableLawDecision
```

The narrow vocabulary (`decision_key`):

- `insufficient_context` — no last residence provided; the skeleton
  cannot proceed at the heuristic level.
- `habitual_residence_default` — last residence provided; that
  jurisdiction becomes the *preliminary working hypothesis*. Mirrors
  Article 21 of EU Reg. 650/2012 as a default rule.
- `professio_juris_candidate` — `has_will=True` flagged; a
  professio juris clause may apply (Article 22). Manual review is
  required and the assignment of any specific national law is
  deferred to the Studio.
- `cross_border_fragmentation` — assets span three or more
  countries; even with a default residence rule, the case carries
  enough cross-border weight to require coordinated review.

The order of fired heuristics is preserved in `applied_rules` so a
reviewer reads it like a checklist:

```
rule_habitual_residence_default
rule_has_will_present
rule_assets_multi_country
rule_nationality_differs_from_residence
```

When the skeleton fires anything beyond the default, `confidence`
drops to `low` and `requires_manual_review` becomes `True`.

---

## What the skeleton does **NOT** do

This is the explicit boundary the iter draws around itself:

- **No legal advice.** The skeleton never asserts "the applicable
  law is X". Reasons and warnings deliberately use language like
  "preliminary working hypothesis", "may apply", "must be considered
  by a Studio lawyer". The test suite (`test_no_legal_certainty_wording`)
  enforces a forbidden-wording list.
- **No renvoi.** When nationality differs from residence, the skeleton
  flags the case for review but does not pick between national and
  residence law.
- **No ``ordre public``.** Public-policy exceptions are out of scope.
- **No professio juris parsing.** The skeleton flags `has_will=True`
  but does not attempt to extract or interpret the will's text.
- **No automatic public output.** The full decision payload lives
  under `output_data["internal"]["applicable_law_decision"]`; the
  template never iterates the `internal` key.
- **No DB writes** (other than the unchanged `Simulation` row that
  was going to be saved anyway). No `LegalSource`,
  `CompensationDataset`, `CalculationFormula` are created or
  promoted by the skeleton.

The contract "*meglio nessun calcolo che un calcolo falso*" applies:
the skeleton refuses to claim certainty.

---

## How it connects to MA / TN

Inheritance simulations on `/wizard/ma/inheritance/` and
`/wizard/tn/inheritance/` continue to return
`unavailable_requires_legal_validation`: no legal source is
APPROVED, no formula runs, no shares are produced. The skeleton sits
*alongside* that flow, not inside it:

1. The wizard form (`InternationalInheritanceWizardForm`) builds
   `applicable_law_context` from the user inputs and emits it under
   `input_data["applicable_law_context"]`.
2. `apps/cases/services.py::run_simulation` calls
   `_attach_applicable_law_decision` after the calculator produced
   its (currently always-unavailable) result. The decision is
   stashed under `output_data["internal"]["applicable_law_decision"]`.
3. The result template renders the curated `PublicResultMessage`
   plus the new `applicable_law_hint` callout. Internal decision
   details remain hidden.

When MA / TN are eventually wired (real Moudawana / CSP mapping
iters, separate from this one), the engines will be able to read
the decision payload to short-circuit gating: e.g., refuse to
produce shares when `requires_manual_review` is True. This iter
does not perform any such short-circuit yet — it only prepares the
data.

---

## Wizard fields used

The skeleton consumes four signals collected by
`apps/cases/forms.py::InternationalInheritanceWizardForm`:

| Wizard field                              | Skeleton use                                    |
|-------------------------------------------|-------------------------------------------------|
| `deceased_country_of_last_residence`      | Default applicable-law country (Art. 21)        |
| `nationality`                             | Renvoi flag (Art. 22 + national-law channel)    |
| `has_will`                                | Professio juris candidate flag                  |
| `assets_countries` (free-text → ISO list) | Cross-border fragmentation flag                 |

`assets_countries` is normalised by
`normalise_assets_countries(...)`: the wizard accepts comma-separated
free text ("MA, FR, IT"), the helper trims, uppercases, deduplicates
and filters non-ISO entries. The normalised list is what lands in
`applicable_law_context["assets_countries"]`.

---

## Fixture examples

```python
# 1. Just last residence — preliminary, no manual review.
evaluate(ApplicableLawInput(deceased_country_of_last_residence="MA"))
# → decision_key="habitual_residence_default"
#   preliminary_law_country="MA"
#   confidence="medium"
#   requires_manual_review=False

# 2. Has will → professio juris candidate.
evaluate(ApplicableLawInput(deceased_country_of_last_residence="MA", has_will=True))
# → decision_key="professio_juris_candidate"
#   confidence="low"
#   requires_manual_review=True

# 3. Multi-country assets.
evaluate(ApplicableLawInput(
    deceased_country_of_last_residence="MA",
    assets_countries=("MA", "FR"),
))
# → requires_manual_review=True
#   applied_rules contains "rule_assets_multi_country"

# 4. Three+ countries → fragmentation.
evaluate(ApplicableLawInput(
    deceased_country_of_last_residence="MA",
    assets_countries=("MA", "FR", "IT"),
))
# → decision_key="cross_border_fragmentation"

# 5. Insufficient context.
evaluate(ApplicableLawInput())
# → decision_key="insufficient_context"
#   preliminary_law_country=None
```

---

## Public result confirmation

Every fixture exercised on the live server (FR / BE / MA / TN, plus
FR-locale and AR-locale for MA) renders **zero technical decision
details** on the rendered HTML. Verified by:

- `apps/cases/test_result_page_localization_pass1.py::test_*` (still passing).
- `apps/calculators/test_inheritance_applicable_law.py::test_public_result_does_not_surface_decision_details`.
- `scripts/audit_public_result_messages.py` (verdict OK, 6/6 fixtures clean).

The user-visible addition is a single line, translated across IT /
FR / EN / AR:

```
IT: Lo Studio esaminerà la legge applicabile e gli elementi
    transfrontalieri prima che vengano calcolate quote ereditarie.
FR: Le Cabinet examinera la loi applicable et les éléments
    transfrontaliers avant tout calcul de parts successorales.
EN: The Studio will review the applicable law and cross-border
    elements before any shares are calculated.
AR: سيراجع المكتب القانون المطبّق والعناصر العابرة للحدود قبل
    حساب أي أنصبة إرثية.
```

---

## Visual review notes

Screenshots live under
`docs/screenshots/live_qa/applicable_law_skeleton_pass1/after/`.

**Note on styling.** During the capture run for this iter the
Tailwind CDN was unreachable from the Playwright sandbox, so the
shots render unstyled HTML. The structural / textual content is
correct: every section heading, the new hint card position above
the next-steps list, the localised CTA labels and the public-status
badge are all present. The previous iter
(`result_page_localization_pass1/after/`) shows the same template
with Tailwind loaded — that is the visual reference for the styled
appearance; this iter only adds the hint paragraph above the
numbered steps.

**Desktop 1440 × 900.** Result page MA:

- H2 "Risultato preliminare"
- Premium summary "Il tuo caso successorio è stato ricevuto …"
- Public-status badge "Analisi successoria internazionale"
- "Cosa succede ora" card with the multi-line explanation, **the
  new applicable-law hint paragraph**, and the numbered next-steps.
- CTAs: "Richiedi una revisione dello Studio" + "Scarica report
  PDF" + "Torna alla procedura guidata".

**Mobile 375 × 800.** Same structure, single-column. Hint text wraps
inside the sand-toned callout without overflow.

**RTL Arabic.** The hint reads naturally right-to-left; the callout
border + sand-100 background work without manual mirroring.

**Zero technical leaks confirmed:** no `applicable_law_decision`,
`decision_key`, `preliminary_law_country`, `applied_rules`, or any
of the rule slugs (`rule_habitual_residence_default`, etc.) appears
anywhere in the rendered HTML.

---

## Italia preserved

`test_italy_smoke_unchanged_with_applicable_law_skeleton`:

- 35 / 10 / 0 → 26 268 / 27 353 / 28 439 EUR.
- `internal` is not populated for road-accident simulations: the
  enrichment helper short-circuits when `case_type` is not
  `inheritance`-shaped, so road-accident `output_data` shapes stay
  byte-identical.

---

## Prerequisites for a future real engine

Before this skeleton can grow into anything resembling production
applicable-law reasoning, the project needs:

1. **Studio mapping of Reg. 650/2012 + Loi 98-97 + Moudawana
   coordination.** A per-case decision tree, written by a Studio
   lawyer, that determines when the residence default holds, when
   national law applies via professio juris, when public-policy
   exceptions kick in, and when fragmentation across fora must be
   coordinated.
2. **Approved legal sources for each branch the engine references.**
   The current MA / TN sources are still `needs_review`; promotion
   is gated by `LegalReview`.
3. **Applicable-law-aware engines.** Once approved, the
   `morocco_inheritance_v1` and `tunisia_inheritance_v1` engines
   need to read the skeleton's decision payload and refuse to
   produce shares when `requires_manual_review` is True (or when
   the decision_key is anything other than
   `habitual_residence_default` with high confidence).
4. **A wider taxonomy.** The skeleton today handles four signals.
   A real engine would also need to reason about marriage regimes,
   property location vs. residence, succession lex situs for
   immovables, etc. None of that is in scope here.

Each of those is a separate iter; this one only prepares the
structural ground.

---

## Cross-references

- Service: `apps/calculators/inheritance_applicable_law.py`
- Form integration: `apps/cases/forms.py::InternationalInheritanceWizardForm.to_input_data`
- Service hook: `apps/cases/services.py::_attach_applicable_law_decision`
- Public hint: `apps/cases/public_result_messages.py::_INHERITANCE_REVIEW.applicable_law_hint`
- Template: `templates/public/wizard_result.html`
- Tests: `apps/calculators/test_inheritance_applicable_law.py`
- Audit: `scripts/audit_public_result_messages.py`
- Capture: `scripts/capture_applicable_law_skeleton_pass1.py`
- Sibling iter: `docs/architecture/RESULT_PAGE_LOCALIZATION_PASS1.md`
