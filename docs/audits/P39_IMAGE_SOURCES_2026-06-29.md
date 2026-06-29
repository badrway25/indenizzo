# P39 — Internal imagery sources (Pexels)

_Date: 2026-06-29 · Phase P39 — Premium Sources Library, Human Results & Internal Imagery._

Seven new **internal body images** (not heroes) were added to enrich the
sources, source-detail, result, services and guided pages. Every image is
fetched server-side only (via `PEXELS_API_KEY` env, never in code/logs),
pinned by `photo_id` in `config/pexels_image_overrides.json`
(`approved_visual: true`), stored under the gitignored `media/pexels/`, and
served as optimised WebP (`<picture>` + lazy loading) with a JPEG fallback.

All photos are used under the [Pexels License](https://www.pexels.com/license/)
(free to use, attribution appreciated). Attribution is recorded here and never
rendered on public pages (per the photo-ID-freeze contract).

| Slot | Photo ID | Photographer | Pexels page | Desktop / mobile WebP | Used on |
|------|----------|--------------|-------------|----------------------|---------|
| `sources_body` | 28216220 | Manuel Torres Garcia | pexels.com/photo/28216220/ | 168 / 64 KB | Sources — "official documents, explained simply" |
| `source_document` | 4792286 | Anete Lusina | pexels.com/photo/4792286/ | 37 / 16 KB | Source detail — document side panel |
| `result_report` | 8111889 | Pavel Danilyuk | pexels.com/photo/8111889/ | 37 / 15 KB | Result pages (precheck / document / estimate) report panel |
| `services_estimate` | 6077520 | Katrin Bolovtsova | pexels.com/photo/6077520/ | 23 / 10 KB | Services — "Make an estimate" |
| `services_documents` | 7681493 | kaboompics.com | pexels.com/photo/7681493/ | 23 / 10 KB | Services — "Check your documents" |
| `services_international` | 7634438 | Marina Leonova | pexels.com/photo/7634438/ | 20 / 7 KB | Services — "Cross-border cases" |
| `guided_workflow` | 8730785 | Mikhail Nilov | pexels.com/photo/8730785/ | 35 / 16 KB | Guided router — visual path |

## Curation rules applied
- Tone: institutional — libraries, document desks, scales, globes, calm legal
  offices. **No** accident/injury imagery, no sensationalism, no insurance/casino
  styling, no money/cash close-ups.
- Each slot carries `avoid_terms` + an `approved_reason` editorial note in the
  override file.
- All chosen photos are landscape ≥ 600px tall (object-cover safe).
- Every WebP is well within the 10–200 KB target.

## Reproduce
```bash
# (PEXELS_API_KEY in env; never committed)
python manage.py fetch_pexels_site_images --slot sources_body   # …per slot
python manage.py compress_pexels_images
python manage.py fetch_pexels_site_images --audit               # FROZEN_MATCH per slot
```

## Browser QA (real Chromium via Playwright)

Verified pages: `/sources/`, `/sources/<id>/`, `/services/`, `/guided/`, and the
document result (`/documents/upload/` → dossier). All with **0 site console errors**.

- **Desktop (1280):** sources opens as a library (image + "how to read a source"
  explainer + premium source cards); source detail is a document sheet (image
  panel + "A cosa serve / Quando può aiutare una stima / Quando basta la verifica
  dei documenti / Collegamenti utili"); services shows three alternating
  image+text bands (image left / right / left); guided is a two-column cockpit
  with a 4-step path (Paese · Caso · Documenti · Risultato); the result page
  carries the human report header (Hai indicato · Possiamo fare ora · Manca
  ancora · Prossimo passo) with a report image.
- **Mobile 390×844:** every page — no horizontal overflow (document width 375 ≤
  390); images and bands stack cleanly; the result report rows stack and the
  side image is hidden below `lg`.
- **RTL (`/ar/...`):** `dir="rtl"`, layout mirrored (band images swap side), all
  new strings render in Arabic, no overflow.

Two classes of real defect were caught here and fixed: multi-line `{# #}`
comments leaking as literal text, and `order-*` utility classes (absent from the
subset CSS) silently failing to alternate the service bands — now driven by DOM
order. Screenshots are stored under the gitignored `.playwright-mcp/` and are not
committed.
