# P44 — Premium Frontend & Feature Audit

_Date: 2026-06-29 · Phase P44, Fase B. Honest per-area assessment of the public
surface after the P35–P40 stack, and what P44 changes._

| Area | Already premium | Could be more elegant | Too static / textual | Needs icon/preview/animation | P44 fix |
|---|---|---|---|---|---|
| Home | Hero, intent cards, matrix, honest "no fabricated numbers" copy | — | Long page already | — | No new section (already covers "why we don't invent estimates" at lines 92/241 — adding more would reduce clarity, rule 14) |
| Mega-menu | Icon + label + description + CTA per panel | A one-line value preview was missing | Slightly link-list-like | Mini-preview line | **Added a `nav-menu__preview` line to all 5 dropdowns** |
| Services | 3 alternating image+text bands, matrix | — | — | — | Unchanged (rich since P39) |
| Guided | 2-col cockpit + 4-step path preview + image | — | — | — | Unchanged (rich since P39) |
| Documents | Animated CSS explainer (Upload → Recognise → Path) | — | — | — | Unchanged (P40 explainer) |
| Sources | Library + "how to read a source" + document sheet | — | — | — | Unchanged (P39) |
| Documentation | Sticky TOC + 9 topic cards | Lacked a quick-start, glossary and FAQ | Was card-only | Start-here band, glossary, FAQ accordion | **Documentation 2.0**: "Start here" navy band, simple glossary, mini-FAQ accordion, 2 new anchors |
| Results | Human report header + side image | — | — | — | Unchanged (P39) |
| Matrix | Truthful country × category chips | — | — | — | Already corrected in P40 (only IT shows "Estimate available") |
| Search | Functional over sources + key pages | Could gain result previews | Plain list | — | Out of P44 scope (functional, low risk) |
| Mobile drawer | Sectioned, RTL-safe, outside header | — | — | — | Unchanged (P37 fix) |
| Arabic RTL | dir=rtl, mirrored, self-hosted Amiri/Tajawal | — | — | — | New P44 strings translated + RTL-verified |

## Decisions (conservative by design)
- **Typography / palette / font family:** not swapped. The self-hosted
  Cormorant + Inter (+ Amiri/Tajawal) pairing and the navy/gold/sand/stone token
  palette already cover the requested "international law firm" tone with no CDN.
  See `P44_TYPOGRAPHY_AND_PALETTE` reasoning carried from P40. P44 adds depth via
  a navy "Start here" band and a dashed-rule menu preview, not a re-skin.
- **Forms:** the guided/precheck/upload forms already use premium inputs,
  checkbox-cards, focus rings, step indicators and "what happens next" copy from
  P22–P31. P44 does not redesign them (no clarity gain; rule 14).
- **Feature sections / previews:** the home, guided, documents and sources pages
  already carry the requested feature/preview content cumulatively (P36–P40);
  P44 focuses new content where it was genuinely missing — the documentation hub.

## What P44 ships
1. Documentation 2.0 (start-here band, glossary, mini-FAQ, anchors).
2. Mega-menu mini-previews (5 panels).
3. Re-verified estimate-validation workstream (no new engine — see
   `P44_OFFICIAL_ESTIMATE_EXPANSION_VALIDATION`).
4. Guard tests, performance note, browser QA (desktop / mobile 390 / RTL).
