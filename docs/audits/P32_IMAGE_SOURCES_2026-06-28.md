# P32 — Pexels Image Sources (2026-06-28)

All imagery comes from Pexels via the existing server-side pipeline
(`apps/core/pexels.py`, `manage.py fetch_pexels_site_images` + `compress_pexels_images`),
fetched only with `PEXELS_API_KEY` read from env. **The API key is never stored in
code, commits, logs, screenshots or this report.** Binaries live in gitignored
`media/pexels/` (regenerated at deploy via the fetch command); only this attribution
doc and the pinned `config/pexels_image_overrides.json` entries are committed.

License: Pexels License (free to use, attribution appreciated, no attribution
required). Each slot is pinned to a validated `photo_id` so `--all --force`
reproduces the same image.

## P32 new slots (visually validated in a browser contact sheet)

| Slot | Photo ID | Photographer | Subject | Pexels URL | Desktop WebP |
|------|----------|--------------|---------|------------|--------------|
| `documents_hero` | 8112185 | Pavel Danilyuk | Lawyer's desk: Lady Justice statue, diploma, laptop (no people) | pexels.com/photo/diploma-figurine-and-documents-on-a-desk-8112185/ | 33 KB |
| `sources_hero` | 32008370 | Guohua Song | Grand library interior, elegant arches, warm reading room | pexels.com/photo/stunning-view-of-grand-library-interior-32008370/ | 168 KB |
| `case_types_hero` | 9685285 | Pixabay | Striking Lady Justice statue (sword + scales), Dresden — architectural | pexels.com/photo/9685285/ | ~79 KB |
| `result_hero` | 10347152 | Ron Lach | Neat desk: binders, papers, coffee — organised dossier (no people) | pexels.com/photo/office-documentation-and-papers-laying-on-desks-10347152/ | 50 KB |
| `guided_hero` | 669610 | Lukas Blazek | Overhead desk: laptop + documents — "map your case" | pexels.com/photo/person-holding-blue-ballpoint-pen-on-white-notebook-669610/ | 46 KB |

Each slot ships three derivatives: source `.jpg` (≤205 KB), desktop `.webp`
(33–168 KB), mobile `.webp` (13–66 KB). Editorial rules applied: institutional/
architecture/documents tone, **no stock people, no gavel kitsch, no monetary/charts
implication** (curation notes frozen in `config/pexels_image_overrides.json`).

## Pre-existing slots (unchanged)
home_hero, countries_index, country_landing_{IT,FR,BE,MA,TN}, methodology_hero,
wizard_start_hero, wizard_{italy,france,belgium}_road_accident_hero,
wizard_{morocco,tunisia}_inheritance_hero, contact_hero, services_hero, about_hero,
ta3ouid_hero, how_it_works_hero, faq_hero — see `config/pexels_image_overrides.json`.
