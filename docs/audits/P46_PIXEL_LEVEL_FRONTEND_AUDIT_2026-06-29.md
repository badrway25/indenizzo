# P46 — Pixel-Level Frontend Audit

_Date: 2026-06-29 · Phase P46. Found in a real browser (Chromium, desktop 1440 /
mobile 390 / RTL), then fixed. Each fix was re-verified in the browser._

## Defects found → fixes shipped

| # | Defect (where) | Fix |
|---|----------------|-----|
| 1 | **Every `.premium-badge` rendered a `●` font glyph** (`::before { content: "●" }`) — reads as a low-quality dot; plus inline `●` glyphs in status chips (guided, precheck, countries, country landing, public status panel). | Replaced the glyph with a **crisp CSS-drawn dot** (`content:""` + `border-radius`), and the inline `●` with a `.badge-dot` span. No `●` left in public templates. Added `.premium-badge--has-icon` to suppress the dot when an icon is present, and semantic variants `--source/--time/--status/--country/--document`. |
| 2 | **Hero was a small contained banner** (`max-w-7xl` + rounded), making the site feel small. | New **full-bleed hero** (`.premium-hero-fullbleed` / `.premium-hero-media` / `.premium-hero-inner`): the photo spans edge-to-edge behind the navy→bronze overlay; copy stays constrained. Min-height 16rem→26rem; verified 1425×416 desktop, 256 mobile, 416 RTL. |
| 3 | **Navbar items had no icons** (only a chevron). | Added a leading champagne icon to each top item (Estimates=scale, Documents=document, Countries=globe, Sources=book-open, Method=list-checks) via `.nav-link__ico`. |
| 4 | **Source marker was the `§` section sign** (and `◫` for file kind) — typographic, not premium. | Replaced `§` with a `book-open` icon and the file-kind glyphs with `image`/`file-text` icons across guided, precheck, dossier panel, document upload, home, countries, country landing, case-type landing. |
| 5 | **Form selects showed the default grey browser arrow** (no `appearance`), looking like a default control. | `appearance: none` + a **champagne chevron caret** on `.premium-select`/`.field-select`, RTL-aware (caret moves to the left in `[dir="rtl"]`). _Limit: the open native option list is browser-rendered and cannot be styled without a full custom-select (out of scope; rule "no big new feature") — the closed trigger is now premium._ |
| 6 | **Time labels had no icon.** | Added a `clock` line icon to the guided route "Time" label (and the icon set now has `clock` + `calendar-check`). |
| 7 | **Mega-menu entrance felt flat.** | Rounder panel (`radius-xl`), deeper layered shadow, a subtle scale-in entrance (reduced-motion safe). |

## Pages checked (real browser)
home · mega-menu · guided (+ path studio) · documents · source library · source
detail · documentation · services · countries · case-types · result (document) ·
mobile drawer · Arabic RTL. **0 site console errors**; no horizontal overflow at
390px; badges carry no `●`; sources show a book icon; the select trigger shows a
champagne caret; the hero is full-width.

## Note (QA process)
The browser aggressively cached `design-system.css`; the first hero measurement
read a stale rule (74px). Cache-busted reloads (`?v=N`) confirmed the live CSS
(416px full-bleed). The pre-compressed `.css.gz` was regenerated after each CSS
edit (`precompress_static`).
