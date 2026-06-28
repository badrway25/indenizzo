# P35 — Human-First Visual UX Audit (2026-06-28)

Method: browsed the live site as an ordinary client (not a developer) on the
P32-green build. Ratings 1–5 (5 = excellent). Focus: would a normal person
instantly understand what to do, and does it look premium?

## Cross-cutting findings (apply everywhere)

1. **Navbar blends into the page.** It uses `bg-sand-50/90` — the same ivory as the
   content — so it has no distinct "platform shell". When you scroll, content bleeds
   through. → Give it a deep-navy glass shell with a hairline + soft shadow so it pops.
2. **Forms read as developer-made, not designer-made.** Default browser checkbox
   (tiny square), flat selects, submit button close to help text, cramped vertical
   rhythm. → A `.premium-form*` system: generous spacing, premium checkbox/radio cards,
   styled selects, a separated `.premium-form-actions` row (button always has top margin).
3. **Copy is occasionally abstract.** "percorso consigliato", "readiness", "pre-check
   documentale" mean little to a normal person. → Plain language: "cosa puoi fare ora",
   short sentences, one idea per line.
4. **Motion is present but subtle.** Heroes/stats animate; forms/results are static. →
   Add gentle reveal on form sections and result blocks.

## Per-page scores (key pages)

| Page | Beauty | Clarity | Forms | Buttons | Navbar | Images | Type | Copy | Motion | Trust | Mobile | RTL |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Home | 4 | 3 | – | 4 | 3 | 4 | 4 | 3 | 3 | 4 | 4 | 4 |
| Documents upload | 4 | 4 | 2 | 3 | 3 | 5 | 4 | 4 | 2 | 4 | 4 | 4 |
| Guided | 3 | 3 | 2 | 3 | 3 | 4 | 4 | 3 | 2 | 4 | 3 | 4 |
| Precheck (form) | 3 | 3 | 2 | 3 | 3 | 4 | 4 | 3 | 2 | 4 | 3 | 4 |
| Result/dossier | 4 | 3 | – | 4 | 3 | 4 | 4 | 3 | 3 | 4 | 4 | 4 |
| Sources | 4 | 3 | 3 | 4 | 3 | 4 | 4 | 3 | 3 | 4 | 4 | 4 |
| Contact/lead | 3 | 4 | 2 | 3 | 3 | 4 | 4 | 4 | 2 | 4 | 3 | 4 |

**Lowest scores → priorities: forms (2) and navbar distinctiveness (3).**

## What I fix now (this phase)

- **Navbar**: deep-navy glass shell, hairline + soft shadow, lighter link/CTA on dark,
  refined brand, premium search pill — distinct from content the moment the home opens.
- **Premium form system** (`.premium-form`, `-section`, `-field`, `-label`, `-input`,
  `-select`, `-checkbox-card`, `-radio-card`, `-actions`, `-help`, `-error`): generous
  vertical rhythm, premium consent checkbox, button always separated with top margin,
  mobile full-width — applied to documents-upload, precheck, contact, guided, search.
- **Simpler copy**: home hero + "Cosa vuoi fare?" intent grid, documents steps, result
  human phrasing ("Hai indicato… / Manca… / Puoi fare ora…"), no banned tech words.
- **Typography**: tighter heading rhythm, comfortable body line-height, delicate
  eyebrow tracking, larger mobile body — within the existing self-hosted Inter +
  Cormorant stack (no CDN fonts).
- **Motion**: reveal on form sections + result blocks; CTA arrow movement everywhere.
- **Color**: keep navy/gold/ivory; add a deep petrol-navy for the navbar shell and
  warmer focus rings; red reserved for errors only.

## Out of scope (kept honest)
No new functional features, no engine changes, no invented figures, no money on
engine-less pages. Section-level Pexels imagery beyond existing heroes only if it stays
light and non-kitsch; otherwise documented as not done.
