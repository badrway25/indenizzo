# Inheritance wizard — input completeness, pass 1

**Iter:** `F-inheritance-wizard-input-completeness-visual-pass1`.

This pass extends the public wizard for international inheritance
(MA + TN) so that the form collects the heir structure the future
inheritance engines (`morocco_inheritance_v1`,
`tunisia_inheritance_v1`) will need: spouse / sons / daughters /
father / mother / siblings, plus an optional `estate_value`. The
public calculator stays inactive — both engines remain
`unavailable_requires_legal_validation` on the public DB. No legal
data was added or promoted.

The pass also fixes a long-standing UX bug: the section legend
"Heirs" was hard-coded English and rendered untranslated in IT / FR /
AR. After this pass every visible string on the wizard is fully
translated across the four locales.

---

## Visual baseline

Before / after screenshots live under
`docs/screenshots/live_qa/inheritance_wizard_input_completeness_pass1/`.

```
before/
  desktop/
    wizard_ma_inheritance_it.png
    wizard_ma_inheritance_fr.png
    wizard_ma_inheritance_ar.png
    wizard_tn_inheritance_it.png
    countries_morocco_it.png
    countries_tunisia_it.png
  mobile/
    wizard_ma_inheritance_it.png
    wizard_ma_inheritance_ar.png
    wizard_tn_inheritance_it.png
after/
  desktop/
    wizard_ma_inheritance_it.png
    wizard_ma_inheritance_fr.png
    wizard_ma_inheritance_ar.png
    wizard_tn_inheritance_it.png
    countries_morocco_it.png
    countries_tunisia_it.png
    result_ma_post_unavailable.png
    result_tn_post_unavailable.png
  mobile/
    wizard_ma_inheritance_it.png
    wizard_ma_inheritance_ar.png
    wizard_tn_inheritance_it.png
    result_ma_post_unavailable.png
```

### Visual review notes

**Desktop 1440 × 900.** The wizard now renders three legibly-named
fieldsets — *Informazioni sul defunto* / *Situazione famigliare* /
*Patrimonio e contesto* — with a short helper paragraph at the top
of each. The Family-situation section uses three checkbox cards
(spouse / father / mother) on a 3-column grid for the boolean heirs
and three numeric inputs (sons / daughters / siblings) on a second
3-column grid. Spacing, typography and the gold-ink palette match
the existing wizard family. The CTA is now `Submit the case to the
Studio` (translated) instead of the previous `Run simulation` /
`Esegui simulazione`, since no automatic computation is produced.

**Mobile 375 × 800.** Both checkbox cards and numeric fields collapse
to single-column on `sm:` boundaries. No horizontal overflow, no
clipped helper text. The premium look (rounded card, soft shadow,
sand background) is preserved.

**RTL / Arabic.** The Arabic page renders right-to-left correctly;
checkbox cards stay aligned to the writing direction without manual
overrides because the partial uses logical Tailwind classes
(`flex items-start gap-3`, no left/right specific paddings). Every
new label, helper and section heading is fully Arabic; `Family
situation`, `Patrimony and context`, `Submit the case to the Studio`
do not appear anywhere in the Arabic page source.

**Premium fixes applied.**

- Replaced the section legend "Heirs" (hard-coded English) with the
  i18n-aware "Family situation" → IT *Situazione famigliare* / FR
  *Situation familiale* / AR *الوضع العائلي*.
- Removed the `children_count` / `parents_alive` fields (which lumped
  sons + daughters together and could not feed an inheritance engine)
  and replaced them with the real heir taxonomy.
- Renamed the CTA from "Run simulation" to "Submit the case to the
  Studio" — the wizard does not run a calculation today (status stays
  `unavailable`), so the previous wording was misleading.
- Cleared 30+ stale `#, fuzzy` headers across the four locales that
  were causing intermittent EN fallback on previously-translated
  strings.

### Result page

The MA and TN POSTs continue to land on the same `wizard_result.html`
page with no monetary fields populated. The page reads "Risultato
preliminare — Il tuo caso è stato ricevuto …" and exposes the
centralised public-status panel, the legal disclaimer and the
contact CTA. No `estimated_min/mid/max`, no breakdown, no inferred
shares.

---

## UX changes

### Form fields — `apps/cases/forms.py`

Old fields **removed**:

- `deceased_country` (renamed)
- `habitual_residence_country` (out of MVP scope, the field was
  duplicating `nationality` for users who don't know the distinction)
- `spouse_exists` (replaced by `spouse_present` boolean checkbox)
- `children_count` (replaced by `sons_count` + `daughters_count`)
- `parents_alive` (replaced by `father_present` + `mother_present`)

New fields **added**:

| Field name                            | Type            | Notes                                      |
|---------------------------------------|-----------------|--------------------------------------------|
| `deceased_country_of_last_residence`  | CharField (2)   | optional, ISO 3166-1 alpha-2               |
| `nationality`                         | CharField (2)   | optional                                   |
| `has_will`                            | NullBoolean     | optional                                   |
| `spouse_present`                      | Boolean         | checkbox card                              |
| `sons_count`                          | Integer ≥ 0     | optional                                   |
| `daughters_count`                     | Integer ≥ 0     | optional                                   |
| `father_present`                      | Boolean         | checkbox card                              |
| `mother_present`                      | Boolean         | checkbox card                              |
| `siblings_count`                      | Integer ≥ 0     | optional                                   |
| `estate_value`                        | Decimal ≥ 0     | optional, EUR, 14×2                        |
| `assets_countries`                    | CharField (120) | optional, comma-separated ISO codes        |
| `message`                             | Textarea (2000) | optional                                   |
| `consent_simulation`                  | Boolean         | required (GDPR)                            |
| `website`                             | CharField       | hidden honeypot                            |

The new fields are all opt-in and have no required-by-default
behaviour. The form's `is_valid()` does not change — the only
required field remains the GDPR `consent_simulation`.

### Template partial — `templates/public/_inheritance_wizard_fields.html`

Rewritten end-to-end. Three sections now drive the layout:

1. **About the deceased** — country of last residence, nationality,
   has_will. Two-column grid on desktop; single column on mobile.
2. **Family situation** — three checkbox cards (spouse / father /
   mother) on a 3-column grid; three numeric inputs (sons / daughters
   / siblings) on a second 3-column grid. Each card has its own help
   text under the label.
3. **Patrimony and context** — estate_value, asset countries, free
   message.

The submit CTA reads "Submit the case to the Studio" / "Invia il caso
allo Studio" / "Soumettre le dossier au Cabinet" / "أرسل الملف إلى
المكتب".

The `wizard_morocco_inheritance.html` and `wizard_tunisia_inheritance.html`
shells (hero image, public-status panel, disclaimer footer) are
unchanged — the iter only swapped the form partial behind them.

---

## Input data mapping

`form.to_input_data()` now produces:

```python
{
    "deceased_country_of_last_residence": "MA" | None,
    "nationality": "MA" | None,
    "has_will": True | False | None,
    "heirs": {
        "spouse":    0 | 1,
        "sons":      <int >= 0>,
        "daughters": <int >= 0>,
        "father":    0 | 1,
        "mother":    0 | 1,
        "siblings":  <int >= 0>,
    },
    "estate_value":      "<decimal>" | None,
    "assets_countries":  "MA, FR" | None,
    "message":           "..." | None,
}
```

The keys under `heirs` match exactly what the existing
`morocco_inheritance_fixed_share_direct` and
`tunisia_inheritance_fixed_share_direct` rules expect via
`apps.compensation.services.apply_amount_inheritance_share_rule`.
Until the corresponding `LegalSource` / `CompensationDataset` /
`CalculationFormula` are promoted to APPROVED for MA / TN, the
calculator gating still returns `unavailable` and the wizard never
shows shares — but the input shape is now ready for that activation
to flip a single status flag and start producing indicative quotes.

---

## i18n

`makemessages -l it -l fr -l en -l ar` regenerated four `django.po`
files. Two helper scripts (deleted at end of iter) walked the four
locales:

1. Added the correct translations for all 18 new msgids introduced
   by this pass and stripped the auto-applied `#, fuzzy` headers /
   `#| msgid` reference lines.
2. Cleared every other stale `#, fuzzy` header whose msgstr was
   already populated — those entries were translated correctly in a
   prior iter but `gettext` had auto-flagged them as fuzzy because of
   minor source-string drift, causing intermittent EN fallback.

After `compilemessages`, every locale serves the inheritance wizard
in its native language with no English leakage.

---

## Live verification

```
http://127.0.0.1:48107/
  /wizard/ma/inheritance/         200, IT
  /wizard/tn/inheritance/         200, IT
  /fr/wizard/ma/inheritance/      200, FR
  /ar/wizard/ma/inheritance/      200, AR (RTL)
  /countries/morocco/             200
  /countries/tunisia/             200
```

POST submissions

```
POST /wizard/ma/inheritance/
  spouse_present=on, sons_count=1, daughters_count=1, estate_value=800000,
  consent_simulation=on
→ 302 → /wizard/result/<uuid>/   (status=unavailable, no amounts)

POST /wizard/tn/inheritance/
  spouse_present=on, mother_present=on, sons_count=1, daughters_count=1,
  estate_value=1200000, consent_simulation=on
→ 302 → /wizard/result/<uuid>/   (status=unavailable, no amounts)
```

Hygiene + lighthouse

```
audit_public_content_hygiene.py     verdict=ok
                                    pages_with_issues=0
                                    by_rule={banned_words=0, en_fallback=0,
                                             h1=0, img=0, pexels=0,
                                             api_key_leak=0}

run_public_lighthouse_audit.py      verdict=OK, 8/8 routes pass
                                    docs/reports/lighthouse/inheritance_wizard_input_completeness_pass1/
```

---

## What remains

Things this iter explicitly did **not** do, and which are tracked for
later iters:

- **Calculator activation.** MA and TN still return `unavailable`
  because no `LegalSource` is APPROVED. Activation requires Studio
  legal review of Moudawana Livre III and CSP Livre IX, plus the EU
  Reg. 650/2012 + Loi 98-97 applicable-law decision tree.
- **Result-page localisation.** The result page surfaces a
  calculator-emitted warning string ("No approved legal sources are
  available …") that is still English in the IT page. That string is
  emitted by `apps.calculators.engines` and was out of scope for this
  iter; it will be addressed when the calculator status-label layer
  gets a translation pass.
- **Field-level inline validation.** The form rejects negative
  `sons_count` / `daughters_count` server-side; client-side `min="0"`
  hints are not yet wired. A future polish iter could add HTMX or
  vanilla JS validation to surface errors before submit.

---

## Cross-references

- Form: `apps/cases/forms.py::InternationalInheritanceWizardForm`
- View dispatcher: `apps/cases/views.py::_wizard_inheritance_view`
- Template partial: `templates/public/_inheritance_wizard_fields.html`
- Wizard shells:
  - `templates/public/wizard_morocco_inheritance.html`
  - `templates/public/wizard_tunisia_inheritance.html`
- Tests: `apps/cases/test_inheritance_wizard_input_completeness_pass1.py`
- Engine docs (twins):
  - `docs/architecture/MOROCCO_INHERITANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md`
  - `docs/architecture/TUNISIA_INHERITANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md`
