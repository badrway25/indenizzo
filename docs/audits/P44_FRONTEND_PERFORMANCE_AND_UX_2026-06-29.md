# P44 — Frontend Performance & UX

_Date: 2026-06-29 · Phase P44, Fase N._

## Posture (unchanged, verified)
- **No external CDN** (0 matches in templates + CSS).
- **No `<video>` / Lottie** — explainers and the new "Start here" band are CSS/SVG.
- **Pre-compressed static** re-generated after the CSS edits (`precompress_static`).
- **Images** served as lazy WebP `<picture>` with explicit dimensions (no CLS).
- **Fonts** self-hosted; hero subset preloaded; critical CSS inlined.

## P44 additions, kept light
- The documentation 2.0 sections (`doc-start`, `doc-term`, `doc-faq`) and the
  mega-menu preview are **CSS-only**, reuse existing tokens, add **no images**
  and **no fonts** — zero new network payload.
- The mini-FAQ uses native `<details>`/`<summary>` (no JS).
- Motion stays gated on `prefers-reduced-motion`.

## Lightweight local audit (this pass)
| Check | Result |
|---|---|
| External CDN | 0 |
| `<video>` / heavy media added | 0 |
| Inline `style=` on new partials/pages | 0 |
| Images without `loading="lazy"` (new) | 0 (no new images) |
| Console errors (home / documentation / services / guided / documents / sources) | 0 (Playwright) |
| Horizontal overflow at 390px (changed pages) | none |

## Not run
A full Lighthouse run was not executed (headless Chromium scoring is unstable in
this environment). P44 adds no images, fonts or scripts, so the measured P2/P40
budget is unchanged. Run Lighthouse on a staging deploy before go-live.
