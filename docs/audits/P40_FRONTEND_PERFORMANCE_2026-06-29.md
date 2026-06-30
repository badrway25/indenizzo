# P40 — Frontend Performance

_Date: 2026-06-29 · Phase P40, Fase M._

## Principles already in place (verified)
- **No external CDN.** 0 references to googleapis / unpkg / jsdelivr / cdnjs /
  tailwindcss in templates or CSS. All CSS, JS and fonts are self-hosted and
  served by WhiteNoise.
- **Pre-compressed static.** `manage.py precompress_static` writes `.gz`
  companions for `design-system.css` / `site.css` / `fonts.css`; WhiteNoise
  serves the compressed variant. Re-run after every CSS edit (done in P40).
- **Images.** All Pexels photos are optimised WebP via a `<picture>` element
  with a JPEG fallback, `loading="lazy"` and explicit `width`/`height` (no layout
  shift). Internal P39 body images are 7–168 KB; heroes are subset to mobile WebP
  under 640px.
- **Fonts.** Hero subset (Inter 400, Cormorant 700) is `<link rel="preload">`ed;
  the rest load async behind the critical-CSS block in `base.html`. Arabic fonts
  are self-hosted (Amiri/Tajawal).
- **Critical CSS** is inlined above the external stylesheets; `site.css` loads
  async to keep LCP fast.

## P40 additions, kept light
- **No video.** The "explainer" sections are pure CSS/SVG animation
  (`.explainer-flow`), not `<video>`/Lottie — zero extra bytes, no decode cost,
  no render-blocking. Motion is gated on `prefers-reduced-motion: no-preference`
  and disabled under `reduce`.
- **No new fonts / no palette swap** — zero added web-font payload.
- **New components are CSS-only** (`.doc-card`, `.explainer-*`,
  documentation hub) and reuse existing tokens; the documentation hub adds no
  images of its own (it reuses the methodology hero slot).
- **No layout shift** from the new sections (cards have intrinsic sizing; the
  explainer connector is absolutely positioned and does not reflow content).

## Lightweight local audit (this pass)
| Check | Result |
|---|---|
| External CDN references | 0 |
| `<video>` / Lottie / heavy media added | 0 |
| Inline `style=` on new partials | 0 |
| Images without `loading="lazy"` (new partials) | 0 |
| Console errors on home / documents / sources / guided / documentation | 0 (Playwright) |
| Horizontal overflow at 390px (new/changed pages) | none |

## Not run this pass
A full Lighthouse run was not executed in this environment (headless Chromium
scoring is unstable here). The optimisations above are the same ones the prior
P2 performance passes measured; P40 added no heavy assets, so the budget is
unchanged. A Lighthouse run on a staging deploy remains the recommended gate
before go-live.
