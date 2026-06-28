# P32 — Visual Rescue Browser Audit (2026-06-28)

Method: a parallel 7-agent UI audit (reading the served CSS + rendered HTML of the
live dev server) plus real-browser screenshots (desktop, mobile probe, RTL). The
platform already owns a strong premium component layer (`.premium-btn`,
`.premium-card`, `.premium-badge`, a CSP-safe motion system) and clean hygiene
(no inline styles, no CDN, reduce-motion everywhere). **The problem is uneven
adoption + a few hard CSS defects, not architecture.**

## Five dominant problems (by how much they cheapen the premium impression)

1. **Dead overflow utilities (highest blast radius).** The Tailwind CDN runtime was
   removed; the hand-written `site.css` does **not** define `truncate`, `min-w-0`,
   `shrink-0`, `place-items-center` (only `flex-shrink-0` exists). ~50 template
   sites silently fail. Concrete clip: `/case-types/` status chip is physically cut
   by the card's `overflow:hidden` at 360px; Arabic filenames bidi-reorder/wrap.
   **One CSS fix repairs the whole surface.**
2. **Two button "eras" on one screen.** ~half the public CTAs use `.premium-btn`
   (lift, shimmer, focus-ring, 44px); the other half are copy-pasted raw utilities
   (`rounded-full bg-ink-950 …`) — flat, stateless, height-drifted. The global
   consultation CTA (every page) and the conversion screens mix both.
3. **`.premium-card` defined 3× with conflicting radius/shadow/overflow** and ships
   **zero padding**, so every page invents `p-4/5/6/7`; the country grid and the
   whole result page bypass the component with bespoke `rounded-3xl shadow-card`.
4. **No mobile navigation.** Six of eight header links are `hidden md/lg:` with no
   hamburger/drawer — deleted, not collapsed. Sub-768px users cannot reach Sources,
   Documents, etc.
5. **Heroless / monotonous imagery.** `/case-types/<slug>/`, `/documents/upload/`,
   `/search/` ship heroless; one office photo repeats across guided→case-types→precheck;
   `/documents/`, `/sources/` borrow non-topical photos.

Targeted defects: dropzone drag cue references undefined `var(--ivory)`; flagship
`countries.html`/`country_landing.html` have zero scroll-reveal; only 10/84 arrows
animate; Italian "Prossimamente" echoes banned coming-soon wording; stat numerals
never count up.

## Prioritized fixes (ordered by visual impact)

| # | Dimension | Problem | Fix | Effort |
|---|-----------|---------|-----|--------|
| 1 | CSS | `truncate`/`min-w-0`/`shrink-0`/`place-items-center` are no-ops | add the utilities to `site.css`, re-`precompress_static` | S |
| 2 | Overflow | case-type status chip clipped at 360px | wrap chip, drop `whitespace-nowrap`, `min-w-0` on title | S |
| 3 | Buttons | global `cta_consultation.html` flat on every page | `.premium-btn premium-btn-primary` (+`.cta-arrow`) | S |
| 4 | Badges | `.premium-badge` is `nowrap`, no max-width → clips IT/FR/AR | tolerant spec (wrap, `max-width:100%`, `overflow-wrap`) | S |
| 5 | Cards | `.premium-card` 3× conflicting + no padding | one rule + built-in padding + `--tight`/`--roomy`/`--grid` | M |
| 6 | Navbar | no mobile drawer | `lg:hidden` hamburger → off-canvas drawer (all links + CTA + lang) | M |
| 7 | Buttons | country_landing / wizard_result / case_type_landing / precheck / countries / home / guided_router / contact_thank_you / about / rate_limited use flat raw CTAs | migrate to `.premium-btn` (+ `premium-btn-on-dark` for dark hero) | M |
| 8 | Imagery | heroless pages + duplicate office photo | dedicated topical slots (documents/sources/case_types/result/guided), wire heroes, eager LCP | M |
| 9 | Overflow | source chips / sidebar k-v rows overflow | `break-words` + `min-w-0` + `shrink-0` | M |
| 10 | Motion | flat below fold; static numerals; idle parallax | `data-reveal` stagger on countries/result; count-up on stat band | M |
| 11 | Hygiene | "Prossimamente" coming-soon wording | confident editorial wording, keep status render-scan guard | S |
| 12 | Filenames | wrap + bidi-reorder under RTL | `dir="ltr"` + truncate after utilities exist | S |

## Unified component specs

- **Buttons** — one language: `.premium-btn` + `-primary`/`-secondary`/`-gold`/`-ghost`/`-danger`,
  new `-on-dark` for hero-over-photo; sizes `-sm`/(default)/`-lg`; `-block`; arrow always
  `<span class="cta-arrow">→</span>`; min 44px; no ad-hoc `px-/py-/bg-` on CTAs.
- **Badge** — wrap-tolerant: `white-space:normal; max-width:100%; overflow-wrap:anywhere;
  text-align:center; line-height:1.25;` one size (11px), one tracking (.14em).
- **Card** — one canonical surface, built-in padding (`--ds-space-5`), `--tight`/`--roomy`/`--grid`
  modifiers, one icon container, badge top-right, CTA row bottom-pinned.
- **Navbar** — desktop inline (transition-smoothed hover) + mobile off-canvas drawer with
  focus-trap/Escape/backdrop/scroll-lock; CTA + language switcher in both.

## Pages needing heroes
Heroless → must get one: `/case-types/<slug>/`, `/documents/upload/`, `/search/`.
Non-topical/duplicate → dedicated slot: `/guided/`, `/case-types/`, `/precheck/`, `/sources/`, `/documents/`.

## Definition of Done
Utilities defined + served `.gz` verified; `.premium-card`/`.premium-badge` single-source;
no flat `rounded-full bg-ink-950` CTAs remain (guard test); mobile drawer reachable; no
heroless public page; staggered reveal on flagship pages; count-up stats; IT/FR/AR(RTL)
overflow-free; real-browser desktop + 360px pass; i18n 0 fuzzy; canaries green.
