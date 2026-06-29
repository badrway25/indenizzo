# P40 — Typography & Palette

_Date: 2026-06-29 · Phase P40, Fase B/C._

## Decision: refine, do not replace

`CLAUDE.md` fixes the brand palette (blu notte, oro sobrio, bianco caldo, grigio
pietra) and the platform already ships a self-hosted, CDN-free type system. P40
therefore **refines component usage and extends coverage** rather than swapping
the identity — a palette/font rip-out would break visual consistency and the
mandated requirements for no measurable benefit.

## Palette (existing, canonical — `static/css/design-system.css`)

| Role (P40 brief) | Existing token | Use |
|---|---|---|
| Navy profondo | `--ds-navy`, `--ds-navy-soft` | headings, header shell, dark CTA bands |
| Blu petrolio | `--ds-teal` | secondary accents / "offer" chips |
| Avorio caldo / bianco caldo | `--ds-sand` | page background, soft surfaces |
| Champagne / oro sobrio | `--ds-gold`, `--ds-gold-soft`, `--ds-gold-strong`, `--ds-gold-ring` | eyebrows, links, gold CTAs, focus rings |
| Rame tenue | `--ds-warning`, `--ds-warning-soft` | "documents / needs table" states, icon medallions |
| Verde fiducia | `--ds-success`, `--ds-success-soft` | "estimate available" chips, positive states |
| Rosso (solo errori) | error tokens / form-error classes | validation errors only |
| Grigio pietra | `--ds-stone*`, `--ds-slate`, `--ds-ink`, `--ds-border-soft` | body text, borders, muted states |

The eight P40 "definitive palette" roles all map onto existing tokens — no new
brand colours were needed. New P40 components (`.doc-card`, `.explainer-*`,
`.result-report`, `.source-read-row`, `.premium-figure`) consume these tokens so
the system stays coherent.

## Typography (existing, self-hosted — no Google Fonts CDN)

- **Headings:** Cormorant Garamond (serif, authoritative) — `--ds-font-serif`.
- **Body / UI / forms:** Inter (legible at small sizes).
- **Arabic (RTL):** Amiri + Tajawal, self-hosted, so `/ar/` keeps a real type
  system and is never broken by a Latin-only fallback.
- All fonts live in `static/fonts/` with `LICENSES`; the hero subset is
  preloaded in `base.html`. **No external CDN** (verified: 0 matches for
  googleapis/unpkg/jsdelivr/cdnjs/tailwindcss in templates + CSS).

## P40 refinements
- Extended the line-icon set (`_icon.html`) with `upload`, `file-text`,
  `printer`, `send`, `play-circle`, `book-open`, `folder`, `map-pin`,
  `sparkles` — coherent Lucide line icons, never emoji, sized via `icon_class`,
  `aria-hidden` when decorative.
- New premium components reuse the radius/shadow/spacing scale
  (`--ds-radius-xl`, `--ds-shadow-sm/md`) for airier, non-compressed cards.
- Motion is consistently gated on `prefers-reduced-motion`.

## What was deliberately NOT done
- No font-family swap and no new web-font download (the current pairing is
  already premium and licence-clean).
- No palette replacement (mandated + already covers all eight requested roles).
