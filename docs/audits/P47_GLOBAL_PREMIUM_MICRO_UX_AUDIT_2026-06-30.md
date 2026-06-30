# P47 — Global Premium Micro-UX Audit

_Date: 2026-06-30 · Phase P47, Fase B. Browser audit (desktop 1280 / mobile 390 /
RTL), then fixes. Each fix re-verified in the browser._

## The headline fix: accessible custom select
Native `<select>` open menus are browser-rendered and cannot be made premium. P47
ships an **accessible custom select** (progressive enhancement, `initCustomSelect`):

- The native `<select>` stays in the DOM and remains the **form's source of truth**
  (verified: the sources filter serialises `country=IT` after a custom pick).
- A styled ARIA `role="listbox"` is built on top: rounded menu, premium shadow,
  per-option hover, a gold **checkmark** on the selected option, a champagne caret.
- **Keyboard:** ArrowUp/Down open + move, Enter/Space select, Escape closes, Home/End
  jump; click-outside closes (all verified in the browser).
- **Value sync:** choosing dispatches `change` on the native select, so dependent
  behaviours still react (verified: the guided path studio recommends "estimate"
  after IT is picked through the custom select).
- **Without JS:** the native select works unchanged (the P46 champagne-caret trigger).
- **RTL + mobile 390:** menu opens in-viewport, no overflow (verified).

Applied to every `.premium-select` / `.field-select` (guided path studio, source
filters, document category/country/language, precheck, contact).

## Per-page audit (premium / fluid / hover / focus / dropdown / select / button / card / badge / source / spacing / mobile / RTL)
| Page | State | P47 action |
|---|---|---|
| home | strong (bespoke hero, intent, matrix) | matrix now carries the honest "why no amount" callout |
| guided | strong (full-bleed hero, cockpit, path studio) | **custom select** on the country picker; time label has a clock icon (P46) |
| documents / upload / result | strong (explainer, report header) | **custom select** on country/category/language |
| sources / source detail | strong (library, document sheet) | **custom select** on the four filters; source markers are book icons (P46) |
| documentation | strong (start-here, glossary, FAQ, by-category) | already explains "why no amount" in the mini-FAQ |
| services / countries / case-types / search | premium | unchanged; selects enhanced where present |
| precheck / estimate forms / offer | premium | **custom select** on the country/case selectors |
| matrix | truthful | **+ "why no amount" callout** under every matrix (home/services/guided/countries) |
| mobile drawer / RTL | mirrored, no overflow | re-verified |

## Conservative passes (rule 14 — do not reduce clarity)
- **Buttons / hover / focus** (Fase D): `.premium-btn*` variants already carry
  hover / `focus-visible` / active + `cta-arrow` motion (P32–P46); no Bootstrap feel.
  No redesign — verified, not churned.
- **Cards** (Fase E): premium-card / doc-card / matrix-card / source cards already
  have radius + shadow + hover-lift; verified.
- **Icons** (Fase G): the Lucide set already covers clock / book-open / file-text /
  globe / shield-check / etc. (P46 + earlier); used consistently.
- **Motion** (Fase I): reveal / slow-zoom / mega-menu scale-in / custom-select +
  accordion transitions, all gated on `prefers-reduced-motion`.
- **Copy** (Fase J): already plain-language (P39–P45); the new callout adds the
  honest "why no amount" wording.

## Honesty
The missing official sources for every country × category are mapped in
`P47_MISSING_OFFICIAL_SOURCES_FOR_ESTIMATES_2026-06-30.md`. **No estimate is
activated** (none reaches `ready_for_engine`); the public callout explains, in
plain words, why some sections show no number.
