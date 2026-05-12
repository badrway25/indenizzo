# Wizard mobile UX audit — 2026-05-12

**Iter**: `PRODUCT-3-wizard-mobile-ux`
**Branch**: `product/wizard-mobile-ux`
**Scope**: read-only audit of the public wizard forms, focused on
mobile completion friction. Companion of `LEAD_FUNNEL_AUDIT_2026-05-12.md`
(funnel-level audit). Drives the targeted improvements in phase 2.

## 1. Wizards in scope

| Wizard | URL | Template | Form class |
|---|---|---|---|
| Italy road accident | `/wizard/it/road-accident/` | `wizard_italy_road_accident.html` (163 LOC) | `ItalyRoadAccidentWizardForm` |
| France road accident | `/wizard/fr/road-accident/` | `wizard_france_road_accident.html` | `FranceRoadAccidentWizardForm(Italy…)` |
| Belgium road accident | `/wizard/be/road-accident/` | `wizard_belgium_road_accident.html` | `BelgiumRoadAccidentWizardForm(Italy…)` |
| Morocco inheritance | `/wizard/ma/inheritance/` | `wizard_morocco_inheritance.html` (42 LOC) → `_inheritance_wizard_fields.html` (179 LOC) | inheritance-specific |
| Tunisia inheritance | `/wizard/tn/inheritance/` | `wizard_tunisia_inheritance.html` (42 LOC) → same partial | inheritance-specific |

### Status quo on duplication

- The **three road-accident wizards** (IT / FR / BE) inline the **identical** 3-fieldset structure (about / injury / economic impact) — ~80 lines of HTML copy-pasted across 3 files. Today any UX change requires editing 3 files.
- The **two inheritance wizards** (MA / TN) already use a shared partial `_inheritance_wizard_fields.html`. Good pattern — the road-accident wizards should adopt the same shape.

## 2. Field map

### Road-accident form (`ItalyRoadAccidentWizardForm` and subclasses)

Reading `apps/cases/forms.py:51-203`, all eight domain fields are
`required=False`. The two consent fields are `required=True`.

| Field | Required? | Drives the calculator? | Mobile-friendly? |
|---|---|---|---|
| `accident_date` | no | no (informational) | yes — `<input type="date">` opens native picker |
| `victim_age` | no | **yes (TUN row lookup + Mornet)** | yes — single integer |
| `permanent_disability_percentage` | no | **yes (TUN row lookup + Mornet)** | yes — single decimal |
| `total_temporary_disability_days` (ITT) | no | no (v1 IT/FR/BE) | yes — single integer |
| `partial_temporary_disability_days` (ITP) | no | no (v1) | yes — single integer |
| `medical_expenses` | no | no (v1) | yes — single decimal, but requires knowing the figure |
| `lost_income` | no | no (v1) | yes — single decimal, but requires payslips |
| `fault_percentage` | no | **yes (linear reduction of output)** | yes — single percentage, but conceptually unclear ("am I at fault?") |
| `accident_country` | hidden | n/a | n/a (locked per wizard) |
| `consent_simulation` | **yes** | n/a (legal gate) | yes — checkbox |
| `special_categories_consent` | **yes** | n/a (legal gate) | yes — checkbox |
| `website` | n/a | n/a (honeypot) | n/a (hidden) |

So 3 fields drive the calculator output (`victim_age`,
`permanent_disability_percentage`, `fault_percentage`). The other 5
domain fields are informational — captured for the Studio's manual
review but not aggregated in v1.

### Inheritance form (Morocco / Tunisia)

Already uses a shared partial. Fields are structurally different (heirs as checkbox cards, conditional spouse-gender, counted sons/daughters/siblings). The partial is already mobile-friendly (checkbox cards, RTL-safe with logical properties). Not a scope target for this iter.

## 3. What the user sees on mobile (390 viewport)

Captured in screenshots from previous iters (`docs/screenshots/.../after/product-lead-funnel-improvements/wizard-it-mobile-390.png`):

1. Hero image (premium).
2. Section uppercase tag + serif `<h1>` "Indicative simulation wizard".
3. Intro paragraph: "All fields below are optional…".
4. Gold-bordered "Important" callout (no documents, no medical-legal report).
5. **Module status card** (IT only — TUN 2025 available).
6. **Result preview aside** (IT only — explains min/mid/max meaning).
7. **Form `<form>` starts:**
   - Fieldset "About the accident" — 2 fields side-by-side on desktop, stacked on mobile.
   - Fieldset "Injury and disability" — 3 fields side-by-side on desktop, stacked on mobile.
   - Fieldset "Documented economic impact" — 2 + 1 fields.
   - GDPR consent (2 checkboxes).
   - Submit "Run simulation" + small "does not create a professional engagement" line.
8. Closing disclaimer paragraph.

The total scroll-length on mobile is **~5-6 viewport heights** of form + intro. The "Run simulation" submit is far below the fold.

## 4. Probable abandonment points (mobile)

Ranked P0 (high impact, low cost) → P2 (low impact / out of scope).

### P0 — Quick wins, ship in this iter

| # | Friction | Fix shape |
|---|---|---|
| W0.1 | **Form length intimidates** non-technical users on mobile. 8 input fields + 2 checkboxes feels like a tax return, not a triage. Many users will leave before reaching submit. | Progressive disclosure: keep the 3 calculator-driving fields visible (`accident_date`, `victim_age`, `permanent_disability_percentage`); collapse the 5 informational fields (`ITT days`, `ITP days`, `medical_expenses`, `lost_income`, `fault_percentage`) under a `<details>` "Additional details (optional)" toggle. Native HTML, no JS, accessible. Consents stay above submit, fully visible. |
| W0.2 | **No microcopy** explaining "you don't need to fill everything". The page-level intro says it once but the user has scrolled past it by the time they reach the form. | Small reassurance line at the top of the form: "Compila i dati essenziali per ottenere una prima stima. Potrai aggiungere altri dettagli sotto, se li conosci." Per-form copy, translated. |
| W0.3 | **Generic CTA "Run simulation"** for IT. Could be more committal / informative. | Change IT submit label to "Calculate indicative estimate" — keeps the "indicative" guardrail explicit. FR/BE keep "Submit for legal review" (correct for review-gated). |
| W0.4 | **Three road-accident templates duplicate** the same 80-line block of HTML — any UX change requires editing 3 files in lockstep. | Extract to a shared partial `_road_accident_wizard_form_fields.html` (mirroring `_inheritance_wizard_fields.html`'s pattern). Include it in IT, FR, BE templates. |

### P1 — Deeper / requires UX iter

| # | Friction | Fix shape |
|---|---|---|
| W1.1 | **`fault_percentage` is conceptually unclear** for the average user — "estimated own fault" can sound legally loaded. | Microcopy clarification in the help_text, e.g. "Leave empty if you believe you bear no responsibility. The Studio will reassess this manually." Out of scope (needs Studio-signed wording). |
| W1.2 | **No client-side validation feedback** beyond Django form errors. A user that types "abc" in the age field sees the error only after submit. | HTML5 `type="number" min="0" max="120"` already restricts native input. Could add JS for inline feedback, but not in scope. |
| W1.3 | **Date picker UX** varies per browser (Safari iOS / Chrome Android). Today: `<input type="date">` opens the native picker. Accept this — third-party datepickers add JS weight. | Keep as-is. |
| W1.4 | **`max-w-3xl` container** on mobile is fine. No friction. | No fix needed. |

### P2 — Aesthetic / out of scope

| # | Friction | Fix shape |
|---|---|---|
| W2.1 | "Result preview" aside (IT only) takes vertical space above the form. Could be after the form for impatient users. | Could test in future, but it sets correct expectations before the user invests in filling the form. Leave as-is. |
| W2.2 | The "Important" callout box (IT only) is decorative. Could fold into the module status card. | Cosmetic, out of scope. |
| W2.3 | RTL/Arabic — wizards are NOT linked from the AR homepage today (the AR home does not surface wizard CTAs). When a user lands on `/ar/wizard/it/road-accident/` directly, the form still renders, but the `<details>` element may look subtly different in RTL (rotation of the disclosure triangle). | Verify in Playwright capture; if broken, fix; else leave as-is. |

## 5. Deontological + GDPR risks (current state — clean, and stays clean)

The wizards today are correctly cautious — none of these change in PRODUCT-3:

- **No promise of recovery** anywhere. "indicative", "preliminary", "the simulation will not invent numbers".
- **Double consent (art. 6 + art. 9)** is enforced via `consent_simulation` and `special_categories_consent`, both `required=True`.
- **Hidden honeypot** (`website` field) drops bot submissions silently.
- **Module status card** (IT) and **public status panel** (FR / BE) carry the legal-tone copy, signed.
- **France stays review-gated**: the Mornet / Gazette / Dintilhac signatures are pending. Even after PRODUCT-3 the FR wizard does not publish numbers (the calculator class refuses without the approved chain).
- **No data field in the form requires** sensitive medical data to be typed verbatim — fields are numeric only (days, percentages, EUR).

### What PRODUCT-3 must not break

- Consent checkboxes **must stay outside** the progressive-disclosure block — they cannot be hidden behind a `<details>` toggle. The submit button must remain disabled until they're checked (Django form-level validation handles this server-side; the UI already shows them above the submit).
- The submit copy on FR / BE wizards must stay "Submit for legal review" — changing it to "Calculate indicative estimate" would mislead the user on a review-gated page.
- The progressive-disclosure block must remain accessible: `<details>` is native, screen-reader-friendly, and works without JS.
- The TUN 2025 calculation flow for IT must remain unchanged — same inputs, same output.

## 6. Recommended improvements (phase 2)

Only the P0 items will be implemented in this iter. Specifically:

1. **W0.4** — extract a shared partial `_road_accident_wizard_form_fields.html` (DRY across IT / FR / BE).
2. **W0.1** — inside that partial, split the fieldsets into:
   - **Essential** (always visible): `accident_date`, `victim_age`, `permanent_disability_percentage`.
   - **`<details>` collapsed "Additional details — optional"**: `total_temporary_disability_days`, `partial_temporary_disability_days`, `medical_expenses`, `lost_income`, `fault_percentage`.
3. **W0.2** — add reassurance microcopy at the top of the form (inside the partial).
4. **W0.3** — change IT submit label from "Run simulation" to "Calculate indicative estimate". FR / BE unchanged.

All four items are template-side only. No model change, no form-field change, no migration, no view change, no settings change.

## 7. What this iter will NOT touch

- No new form fields. No removed form fields.
- No model migration.
- No view change.
- No France activation. The FR wizard remains review-gated, the calculator remains gated.
- No CSP / robots / consent / mandate-notice / disclaimer copy change.
- No CRM / webhook / email change.
- No inheritance wizard change (already uses a partial, already shorter).
- No new languages. No new locales.
- No JavaScript beyond what's already there for the date picker styling.

## 8. Phase 2 acceptance criteria

A change in phase 2 is **good to ship** if:

1. The shared partial renders the same set of fields IT/FR/BE rendered before.
2. The `<details>` block is closed by default but opens via native click/keyboard interaction without JS.
3. The consent checkboxes remain visible above the submit on every page; they are NOT inside the `<details>` block.
4. Submitting the form with only the 2 consents (and zero domain fields) still succeeds — the wizard pattern of "all domain fields optional" is preserved.
5. Submitting the form with all 8 domain fields still succeeds.
6. The full test suite stays green.
7. France stays review-gated; the audit `audit_non_it_readiness.py` continues to report `APPROVED-PARTIAL × 4`.
8. The audit `audit_legal_content_hygiene.py --strict` reports zero findings.
9. AR/RTL renders the form without obvious regressions on the `<details>` element.

## 9. References

- `templates/public/wizard_italy_road_accident.html` — IT wizard, 163 LOC.
- `templates/public/wizard_france_road_accident.html` — FR wizard.
- `templates/public/wizard_belgium_road_accident.html` — BE wizard.
- `templates/public/_inheritance_wizard_fields.html` — inheritance partial (pattern to mirror for road-accident).
- `apps/cases/forms.py:51-203` — `ItalyRoadAccidentWizardForm` and subclasses.
- `docs/product/LEAD_FUNNEL_AUDIT_2026-05-12.md` — phase-1 audit of the funnel that contains this wizard.
- `docs/product/LEAD_FUNNEL_IMPROVEMENTS_2026-05-12.md` — phase-5 report of PRODUCT-2 (preceding iter).
