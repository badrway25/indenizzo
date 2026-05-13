# Case-type landing audit — 2026-05-12

**Iter**: `PRODUCT-4-case-type-landing-pages`
**Branch**: `product/case-type-landing-pages`
**Scope**: read-only audit of the case-type landing surface that
currently exists, mapped to the 8 landings PRODUCT-4 will add.
Drives phase 2 implementation. Companion of
`LEAD_FUNNEL_AUDIT_2026-05-12.md` and `WIZARD_MOBILE_UX_AUDIT_2026-05-12.md`.

## 1. What exists today

| URL | View | Template | Purpose |
|---|---|---|---|
| `/` | `core.views.home` | `public/home.html` | homepage |
| `/countries/` | `core.views.countries` | `public/countries.html` | per-country hub (5 countries) |
| `/countries/{italy,france,belgium,morocco,tunisia}/` | `core.views._render_country_landing` | `public/country_*.html` | one landing per country |
| **`/case-types/`** | `core.views.case_types` | `public/case_types.html` | **hub of case types** — already lists the 9 CaseType enum entries with status badges. No sub-pages today. |
| `/wizard/` | `cases.views.wizard_start` | `public/wizard_start.html` | wizard hub |
| `/wizard/it/road-accident/` (+ FR / BE / MA / TN equivalents) | per-wizard views | per-wizard templates | active wizards |

So the **country axis is fully built out** (countries hub + 5 country
landings). The **case-type axis is half-built** — there's a hub at
`/case-types/` but no per-case-type sub-pages. PRODUCT-4 fills this gap.

## 2. `CaseType` enum — 9 values

From `apps/calculators/enums.py:18-38`:

| Enum value | Label | Has wizard? |
|---|---|---|
| `road_accident_bodily_injury` | Road accident — bodily injury | yes (IT live, FR/BE review-gated) |
| `medical_malpractice` | Medical malpractice | no — review only via /contact/ |
| `work_injury` | Work injury | no — review only via /contact/ |
| `death_compensation` | Death compensation | no — review only via /contact/ |
| `parental_loss` | Parental loss | no — review only via /contact/ |
| `patrimonial_damage` | Patrimonial damage | no — review only via /contact/ |
| `inheritance_basic` | Inheritance — basic | no — review only via /contact/ |
| `international_inheritance` | Inheritance — international | yes (MA / TN review-gated) |
| `generic_legal_assessment` | Generic legal assessment | no — review only via /contact/ |

## 3. The 8 PRODUCT-4 landings

User-listed targets, mapped to enum codes + CTA strategy:

| # | User-facing topic | Slug (English) | CaseType code | Primary CTA | Secondary CTA |
|---|---|---|---|---|---|
| 1 | Incidenti stradali | `road-accident` | `road_accident_bodily_injury` | `/wizard/it/road-accident/` | `/contact/?case_type=road_accident_bodily_injury` |
| 2 | Danno biologico | `bodily-injury` | n/a (a component of road accident) | `/wizard/it/road-accident/` | `/contact/?case_type=road_accident_bodily_injury` |
| 3 | Offerta assicurativa insufficiente | `insurance-offer-review` | n/a (a procedural stage) | `/contact/?case_type=generic_legal_assessment` | `/wizard/` |
| 4 | Infortunio sul lavoro | `work-injury` | `work_injury` | `/contact/?case_type=work_injury` | `/wizard/` |
| 5 | Responsabilità medica | `medical-malpractice` | `medical_malpractice` | `/contact/?case_type=medical_malpractice` | `/wizard/` |
| 6 | Decesso di un familiare | `death-of-relative` | `death_compensation` | `/contact/?case_type=death_compensation` | `/wizard/` |
| 7 | Stranieri vittime in Italia | `foreigners-in-italy` | n/a (a victim profile) | `/contact/?case_type=generic_legal_assessment` | `/wizard/` |
| 8 | Casi internazionali | `cross-border-cases` | n/a (a circumstance) | `/contact/?case_type=international_inheritance` | `/wizard/` |

## 4. Naming convention decision

The repo uses **English snake-case** for every URL slug today
(`/case-types/`, `/wizard/it/road-accident/`, `/wizard/ma/inheritance/`).
The CaseType enum is English (`road_accident_bodily_injury`). The
template labels are translated via `{% translate %}` / `{% blocktranslate %}`.

PRODUCT-4 keeps this convention: **URL slugs in English, page copy
fully translated to IT/FR/EN/AR** via the standard i18n pipeline.

The user prompt suggested Italian slugs ("/case-types/incidenti-stradali/")
but explicitly said: *"Se il progetto usa slug inglesi, scegli naming
coerente col repo, ma documenta la decisione."* — that's what we do.

Documented here so the choice is visible. If Studio later wants
Italian-canonical URLs for the IT market, that's a follow-up
content/SEO iter (and would need 301 redirects from the English
slugs).

## 5. Banned-phrase guardrails to respect

Lint rules from `scripts/audit_legal_content_hygiene.py` + the
`BANNED_PROMISE_PHRASES` list in `apps/cases/test_product_3_wizard_mobile_ux.py:175-185`.

Categories enforced on every new landing:

- **No promise of result**: never "risarcimento garantito",
  "vinceremo", "garantiamo il risultato", "diritto certo".
- **No automated-advice claim**: never "calcolo definitivo",
  "parere legale automatico".
- **No aggressive economic offer**: never "paghi solo se vinci",
  "pay only if you win", "no win no fee", "zero costi sempre".
- **No unsupported comparative**: never "i migliori avvocati",
  "numero uno in italia", "leader assoluto".
- **No raw EUR amounts as expectations**: every numerical example
  must be tied to a validated source or marked as illustrative
  with explicit disclaimer adjacency.
- **No "scopri quanto ti spetta"** marketing — replaced by
  "request a preliminary legal assessment".

PRODUCT-4's tests will add a per-landing lint of these phrases.

## 6. Existing partials to reuse

- `partials/_premium_hero_image.html` — Pexels hero on each landing.
- `partials/mandate_notice.html` — separation between simulation and engagement, near CTAs.
- `partials/cta_consultation.html` — CTA block toward `/contact/`.
- `partials/_documents_to_prepare.html` — shared with PRODUCT-2; can be reused on landings to surface the documents the Studio will need.
- `partials/disclaimer_banner.html` — sitewide.
- `partials/footer.html`, `partials/header.html` — via `base.html`.

No new partials are required, but a small new piece — a "when this applies" / "what the Studio does" section — will live inside the landing template.

## 7. Hreflang allowlist

From the audit response, the global hreflang context processor's
allowlist (`apps/core/context_processors.py:_GLOBAL_HREFLANG_VIEW_NAMES`) includes:

- `core:home`, `core:methodology`, `core:disclaimer`, `core:privacy`
- `core:countries`, `core:case_types`
- per-country landings
- `cases:wizard_start`, `crm:contact`

Each PRODUCT-4 sub-page (`/case-types/<slug>/`) will need to be
added to this allowlist — the view name in URLconf will be
`core:case_type_landing`. Passing the same name with different
slug-derived kwargs is the right pattern.

## 8. noindex / robots

`/case-types/` is `index, follow` today. PRODUCT-4 landings inherit
the same default — public, indexable, SEO-targeted. No `noindex`
override anywhere on the new pages.

## 9. CTA strategy + ?case_type= prefill

The `/contact/` view currently accepts `?sim=<uuid>` (PRODUCT-2)
and prefills `country` + `case_type` from the linked Simulation.
PRODUCT-4 extends this to also accept `?case_type=<code>` directly
(no Simulation required), so landings without a direct wizard
can pre-populate the contact form's case-type dropdown.

The extension is:
- ~10-line addition in `crm.views.contact` to honour
  `request.GET.get("case_type")` as `initial["case_type"]` when no
  `?sim=` resolved.
- The set of accepted values is whitelisted against the existing
  `CaseType` enum to prevent injection.

## 10. Phase 2 acceptance criteria

A landing is good to ship if:

1. URL pattern `/case-types/<slug>/` returns 200.
2. The page has a single `<h1>`, a prudent intro, a "when this applies" section, a "documents to prepare" reuse of the existing partial, a "what the Studio does" section, primary + secondary CTA, mandate notice + disclaimer near CTA.
3. No banned phrase lint findings (`audit_legal_content_hygiene.py --strict` returns no findings).
4. The page is `index, follow` (not noindex).
5. The page has a `<meta name="description">` and `<title>` from the data module.
6. The page renders correctly in AR / RTL (the new content does not break RTL flow).
7. Linked wizard / contact URLs return 200 + carry forward the `?case_type=` when intended.
8. The hub `/case-types/` links to each new sub-page.
9. The full test suite stays green.
10. France stays review-gated.

## 11. What this iter will NOT do

- No new formulas, no new datasets, no France activation.
- No model migration.
- No copy that's case-specific in a way that would need Studio
  sign-off (we stay at the "what kind of cases the Studio handles
  and what to bring for a preliminary review" level — informational,
  not advisory).
- No EUR amounts in landing copy.
- No new languages.
- No JS beyond what's already there.
- No GeoIP / personalisation.
- No A/B testing infra.

## 12. References

- `apps/core/urls.py:21` — `/case-types/` route.
- `apps/core/views.py:568-611` — `case_types` view.
- `apps/calculators/enums.py:18-38` — `CaseType` enum.
- `apps/core/context_processors.py:154-195` — `seo_global_hreflang`.
- `scripts/audit_legal_content_hygiene.py` — banned-phrase lint.
- `templates/public/case_types.html` — current hub.
- `templates/partials/_documents_to_prepare.html` — shared partial (PRODUCT-2).
- `apps/crm/views.py` — contact view (extended in phase 2 to accept `?case_type=`).
- `docs/SEO_AUDIT_AND_CONTENT_ARCHITECTURE.md` — SEO baseline.
