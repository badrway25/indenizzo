# Public funnels — UX audit (pass 3)

**Iter:** `F-product-public-funnels-polish-pass3`.

Read-only audit of the public funnel pages: wizard start, per-country
wizards (IT, FR, BE, MA, TN), result, contact, contact thank-you. The
audit follows the pass-2 template structure but goes deeper on
microcopy, CTA placement, and legal-wording risks. No code changes are
made by this document — only by the templates updated in the same
iter.

The conventions used in this audit:

- **PASS** — already correct.
- **POLISH** — minor copy/UX adjustment recommended in this iter.
- **OUT-OF-SCOPE** — recognised gap, deferred to a later iter.

---

## /wizard/ (`templates/public/wizard_start.html`)

| Aspect | Status | Notes |
|---|---|---|
| User goal | PASS | Pick country + case type; understand which modules are calculator-ready vs in legal validation. |
| Clarity of `Module ready` vs `Legal sources under review` | PASS | Two-state badge already present; tone clear. |
| Cards per option | POLISH | Good baseline; add a 3-step "How it works" panel under the cards so first-time visitors see the path before clicking. |
| CTA wording | POLISH | "Open scaffold wizard" reads engineering-flavoured. Switch to "Open validation wizard" — same meaning, friendlier. |
| Coming soon block | PASS | Honest, no implied promises. |
| Legal risk | PASS | The disclaimer "A simulation is not legal advice" is present at the bottom. |

## /wizard/it/road-accident/ (`wizard_italy_road_accident.html`)

| Aspect | Status | Notes |
|---|---|---|
| User goal | PASS | Submit a road-accident case, get an indicative TUN 2025 range. |
| TUN 2025 wording | PASS | Already mentioned in meta description, status card, and inline. |
| min/mid/max pre-submit explainer | POLISH | The result page explains min/mid/max well; the wizard page does not preview that contract before the user types. Add a small "What you'll see after submitting" panel before the form. |
| Field microcopy | PASS | Field labels and helps come from the form layer; no template-level fix needed here. |
| Consent box | PASS | Privacy notice link + scope of consent. |
| Legal risk | PASS | "indicative", "not legal advice", "no guarantee" all present. |

## /wizard/fr/road-accident/ (`wizard_france_road_accident.html`)

| Aspect | Status | Notes |
|---|---|---|
| User goal | PASS | Submit a France road-accident case for Studio review (no auto-numbers). |
| Module-under-validation banner | POLISH | Banner present but visually similar to the IT page. Add an explicit "no automatic estimate" line + a secondary CTA pointing to `/contact/` so users who don't want to fill the wizard can ping the Studio directly. |
| Engine wording | PASS | "scaffold mode" + Loi Badinter + Mornet + capitalisation are named. |
| Submit button | POLISH | Currently labelled "Run simulation", which on a scaffold wizard sounds calculator-ready. Soften to "Submit for legal review". |
| Legal risk | PASS | "indicative", "no guarantee", "not legal advice" present. |

## /wizard/be/road-accident/ (`wizard_belgium_road_accident.html`)

Mirrors FR — same audit applies.

| Aspect | Status |
|---|---|
| Banner clarity | POLISH (mirror FR) |
| Submit button label | POLISH (mirror FR — "Submit for legal review") |
| Secondary CTA | POLISH — add link to `/contact/` |

## /wizard/ma/inheritance/ (`wizard_morocco_inheritance.html`)

| Aspect | Status | Notes |
|---|---|---|
| User goal | PASS | Submit a cross-border inheritance case for Studio review. |
| Banner | POLISH | Mirror FR pattern (explicit "no shares computed", secondary CTA to contact). |
| Submit-button copy | POLISH | Currently the form is included from `_inheritance_wizard_fields.html` partial; the partial owns the button. No template-level change needed for MA/TN here — handled at the partial. |

## /wizard/tn/inheritance/ (`wizard_tunisia_inheritance.html`)

Mirrors MA — same audit applies.

## /wizard/result/<uuid>/ (`wizard_result.html`)

| Aspect | Status | Notes |
|---|---|---|
| Calculated state | POLISH | Range card + Calculation basis already present. Add: (i) a "What this means" plain-language paragraph (range = bargaining anchor, not a guaranteed payout); (ii) a "Next steps" list (review the PDF, request a Studio review, save the simulation ID). The "Download PDF report" CTA is already prominent — keep it. |
| Unavailable state | POLISH | Current copy is already friendly. Add a CTA to `/contact/` directly inside the unavailable card so the user has a one-click path forward. |
| Sources display | PASS | Cited legal sources rendered with title, citation, country/jurisdiction badges. |
| Disclaimer | PASS | Bottom black box, gold accent. |
| Simulation ID + created_at | PASS | Mono font + visible. |
| Legal risk | PASS | "indicative", "not legal advice" repeated in the disclaimer. |

## /contact/ (`contact.html`)

| Aspect | Status | Notes |
|---|---|---|
| What-happens-next aside | PASS | Already a 4-step ordered list. |
| Microcopy of message field | PASS | "Briefly describe what happened, when, where. Avoid sensitive medical details now." |
| Privacy box | PASS | Privacy + disclaimer links + consent scope. |
| Return paths | POLISH | Add a small footer-strip below the form linking back to `/wizard/`, `/methodology/`, `/disclaimer/` so users who landed here without a simulation can navigate. |
| Submit-button copy | PASS | "Send my request". |
| Legal risk | PASS | "Submitting this form does not create a professional engagement." |

## /contact/thank-you/ (`contact_thank_you.html`)

| Aspect | Status | Notes |
|---|---|---|
| Confirmation tone | PASS | Big check, gold subtitle. |
| Timing language | POLISH | "may take a few working days" is honest but vague — align with the contact page's "3–5 working days" so the two pages don't disagree. |
| Privacy reassurance | POLISH | Add a one-liner: "Your data is processed only to reply to this request, per the privacy notice." |
| Return CTAs | POLISH | Add a third CTA "Back to the wizard" — the user might want to start a different country/case after submitting. |

---

## Out-of-scope for this iter

- Pexels integration / hero image rotations (covered by separate iter).
- Form layer microcopy (labels/help) — touched only at the template
  level here, the form itself is untouched to avoid Italy regressions.
- A11y deep dive — pass 2 already landed the focus rings, aria-labels,
  contrast checks. Pass 3 keeps them intact.

## What this iter must NOT touch

- Any template binding to `LegalSource`, `CompensationDataset`,
  `CompensationTableRow`, `CalculationFormula`, the engine, or the
  Italy TUN smoke contract.
- Any form layer / view layer logic. Polish is markup + copy + i18n
  only.
- The `partials/_module_status_card.html` partial: pass-2 contract.
