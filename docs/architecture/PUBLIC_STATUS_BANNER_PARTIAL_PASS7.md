# Public status banner partial — pass 7

Iter: `F-product-status-banner-partial-pass7`.

## What was centralised

Pass-6 moved badge labels and short descriptions into
`apps/core/public_status.py`. Pass-7 takes the next step: the inline
sand/gold "no automatic amount" banner and the
`partials/_module_status_card.html` block were duplicated across the
four FR / BE / MA / TN wizards. Pass-7 collapses both into a single
panel partial that reads everything from the `PublicStatus`
dataclass:

- `templates/partials/_public_status_panel.html` — new partial.
- accepts: `public_status` (required), `country_name`,
  `legal_basis`, `show_no_amounts_message`, `variant`,
  `contact_url`.
- renders: badge, long description, optional country-specific legal
  basis line, optional no-amounts disclaimer, primary CTA.

Now there is one place to update the FR / BE / MA / TN status copy:
`_RULES` in `apps/core/public_status.py`. Future activations (e.g.
flipping FR from `_LEGAL_ASSESSMENT` to `_AVAILABLE` once the
Référentiel Mornet 2024 dataset lands as `APPROVED`) is a single-line
change.

## Templates updated

- `templates/public/wizard_france_road_accident.html` — banner +
  module status card replaced with the new partial. Country-specific
  legal basis line surfaces "Loi Badinter, Référentiel Mornet,
  Gazette du Palais".
- `templates/public/wizard_belgium_road_accident.html` — same, with
  "Loi du 21 novembre 1989, Tableau Indicatif, Tables Schryvers".
- `templates/public/wizard_morocco_inheritance.html` — same, with
  "Moudawana (Code de la famille), Code des droits réels, EU
  Regulation 650/2012".
- `templates/public/wizard_tunisia_inheritance.html` — same, with
  "Code du statut personnel (Loi 98-97), Code de droit international
  privé, EU Regulation 650/2012".
- `templates/public/wizard_result.html` — the unavailable card now
  reads from `public_status` (long description, primary CTA,
  no-amounts message), so the result page wording stays in sync with
  the wizards automatically.

`apps/cases/views.py` already provided `public_status` to all four
wizards plus `wizard_result` (added in pass-6) — no view changes were
needed in pass-7.

## i18n

`makemessages -l it -l fr -l en -l ar` extracted six new strings
(four legal-basis lines plus the inheritance long description and
the inheritance no-amounts disclaimer). Translations were applied in
all four locales with sensitive legal terms kept verbatim:

- Loi Badinter, Référentiel Mornet, Gazette du Palais
- Loi du 21 novembre 1989, Tableau Indicatif, Tables Schryvers
- Moudawana, Code de la famille, Code des droits réels
- Code du statut personnel, Loi 98-97, Code de droit international privé
- Reg. UE 650/2012 / Règlement UE 650/2012 / لائحة الاتحاد الأوروبي
  650/2012

`makemessages` had marked the new entries as `#, fuzzy` against
nearest pass-6 neighbours. Django's `compilemessages` drops fuzzy
entries by default, which leaked an EN fallback on `/fr/` and `/ar/`
on the inheritance wizards. The fuzzy hint and stale continuation
lines were rewritten cleanly so the .mo now carries the
translations.

## Banned-word audit

Re-ran `scripts/audit_public_content_hygiene.py --base-url
http://127.0.0.1:48107`:

- `banned_words`: 0
- `en_fallback`: 0
- `h1`: 0
- `img`: 0
- `pexels`: 0
- `api_key_leak`: 0
- verdict: **OK**

72 pages probed (IT / FR / AR / EN × 18 paths).

## Screenshots

Saved 8 PNG artefacts under
`docs/screenshots/live_qa/status_banner_partial_pass7/`:

- `wizard_fr_road-accident.png`
- `wizard_be_road-accident.png`
- `wizard_ma_inheritance.png`
- `wizard_tn_inheritance.png`
- `fr_wizard_fr_road-accident.png`
- `ar_wizard_ma_inheritance.png`
- `post_fr_result_unavailable.png`
- `post_ma_result_unavailable.png`

The two POST artefacts show that the result-unavailable card now
renders the centralised `public_status.long_description` and the
`primary_cta_label`, with no `unavailable_requires_legal_validation`
or `missing_documents` raw token leaking.

## What remains

The inline `partials/_module_status_card.html` partial is now only
used by the Italian wizard (which has a calculator and a different,
"what this does / does not / next step" framing). FR / BE / MA / TN
no longer reference it. We can keep it as-is until Italy rewords its
banner — there is no banned wording or duplication issue today.

## How to change a status in one place

To flip a country's public status in the future (e.g. activate the
French calculator), edit the `_RULES` tuple in
`apps/core/public_status.py`:

```python
_RULES = (
    ("IT", "road_accident", _AVAILABLE),
    ("FR", "road_accident", _AVAILABLE),  # was _LEGAL_ASSESSMENT
    ("BE", "road_accident", _LEGAL_ASSESSMENT),
    ("MA", "international_inheritance", _INHERITANCE_REVIEW),
    ("MA", "inheritance", _INHERITANCE_REVIEW),
    ("TN", "international_inheritance", _INHERITANCE_REVIEW),
    ("TN", "inheritance", _INHERITANCE_REVIEW),
)
```

The four wizard pages, the result page, the `/countries/` index, the
`/countries/<slug>/` landings, the `/case-types/` index and the
`/wizard/` start page all rerender from this object — no template
edits needed.

## Italia smoke contract

`test_italy_smoke_unchanged_after_pass7` confirms that with
`victim_age=35, permanent_disability_percentage=10,
fault_percentage=0` the Italian TUN 2025 pipeline still emits
`estimated_min=26 268`, `estimated_mid=27 353`,
`estimated_max=28 439` EUR. No engine, formula, dataset, table row,
or legal source was modified by pass-7.
