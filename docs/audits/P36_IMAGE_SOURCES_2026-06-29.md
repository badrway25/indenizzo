# P36 — Pexels Image Sources (2026-06-29)

New section imagery for the home "What would you like to do?" intent cards, fetched via
the existing server-side pipeline (`fetch_pexels_site_images` + `compress_pexels_images`)
with `PEXELS_API_KEY` read from env only. **The key is never in code, commits, logs or
this report.** Binaries stay in gitignored `media/pexels/` (regenerated at deploy); only
this attribution doc and the pinned `config/pexels_image_overrides.json` entries are
committed. License: Pexels License.

Each pick was **visually validated in a browser contact sheet** (no people, no kitsch,
no gavel, no food — the kind of mismatch caught and fixed in P32).

| Slot | Photo ID | Photographer | Subject | Desktop WebP |
|------|----------|--------------|---------|--------------|
| `intent_estimate` | 6077520 | Katrin Bolovtsova | Gold balance scales on a professional desk | 24 KB |
| `intent_offer` | 7841410 | RDNE Stock project | Contract document with pens on a wooden table | 114 KB |
| `intent_documents` | 17065769 | Jakub Zerdzicki | Tidy office desk with files and folders | 62 KB |
| `intent_law` | 9331326 | Arturo Añez | A globe nested between classic books | 70 KB |

Derivatives per slot: source `.jpg`, desktop `.webp` (24–114 KB), mobile `.webp`
(10–40 KB), all lazy-loaded with `alt` text and a navy overlay for legibility.

Pre-existing P32 hero slots (documents/sources/case_types/result/guided/home/countries/…)
are unchanged — see `config/pexels_image_overrides.json` and the P32 image-sources doc.
