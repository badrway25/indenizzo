# P29 — Official documents pipeline

Date: 2026-06-28. Companion to the source library (`apps/core/official_sources.py`),
the approval queue (`CHATGPT_APPROVAL_QUEUE_2026-06-26.md`) and the P25 estimate-
expansion review. For each priority source: where it lives, whether a downloadable
official copy exists, what is still missing to activate a monetary engine, and how
the public library exposes it. **No heavy file is committed** — only metadata, the
official URL and (when a copy is verified) a SHA-256 hash.

## Storage policy

- `external_official_url` — the source card links to the institution's official
  portal / document page (Normattiva, EUR-Lex, ACAPS, Légifrance, …). Default.
- `local_verified_copy` — a light, verified copy with a recorded hash; used only
  when an official stable URL is unavailable AND the copy is authorised. **Not in
  use yet** (no file committed).
- `metadata_only` — no public URL; the card shows the citation only (e.g. the
  Belgian Tableau indicatif, a non-binding practice).

No temporary OCR output, no scanned PDF and no downloaded binary is ever stored
in the repo. Downloadable PDFs are offered only where a documented, stable official
PDF endpoint exists (the EU regulations on EUR-Lex).

## Per-source state

| Source | Country | Official link | PDF download | Table present | Missing for engine | Unlocks |
|--------|---------|---------------|--------------|---------------|--------------------|---------|
| art. 139 CAP | IT | Normattiva | via portal | yes (in engine) | — (live) | estimate, offer |
| TUN — D.P.R. 12/2025 | IT | Gazzetta Ufficiale | via portal | yes (in engine) | — (live) | estimate |
| L. 24/2017 (Gelli) | IT | Normattiva | via portal | n/a | — (live tabular) | tabular |
| T.U. INAIL — D.P.R. 1124/1965 | IT | inail.it | via portal | no | **grado×età capital table** (D.M. 45/2019) machine-readable | pre-check |
| D.Lgs. 38/2000 | IT | inail.it | via portal | no | same INAIL table | pre-check |
| D.M. 45/2019 | IT | inail.it | via portal | the table itself, not yet imported | import + canary | pre-check |
| Codice Civile 2043/2059 | IT | Normattiva | via portal | none (no statutory table) | n/a — judicial practice only | pre-check |
| Codice del Consumo 114–127 | IT | Normattiva | via portal | none | **no statutory monetary formula** — stays pre-check | pre-check |
| Dahir 1-84-177 | MA | sgg.gov.ma | via portal | capital-de-référence base table (scanned) | the base table (âge×salaire) | pre-check |
| ACAPS guide | MA | acaps.ma | via portal | complementary % extracted | base table | pre-check |
| Code des assurances Titre V | TN | cga.gov.tn | via portal | barème (hosts unreachable here) | owner-provided barème text | pre-check |
| Loi 2005-86 | TN | iort.gov.tn | via portal | — | barème | pre-check |
| Loi Badinter | FR | légifrance | via portal | none (no single state barème) | n/a | pre-check |
| Code des assurances | FR | légifrance | via portal | none | n/a | pre-check |
| Loi 21/11/1989 | BE | ejustice | via portal | none | n/a | pre-check |
| Tableau indicatif | BE | — (metadata only) | — | non-binding practice | **not a state source** — never an engine | pre-check |
| Reg. Roma II 864/2007 | EU | EUR-Lex | **yes (official PDF)** | n/a | n/a | applicable law |
| Reg. UE 650/2012 | EU | EUR-Lex | **yes (official PDF)** | n/a | n/a | applicable law |

## Priorities (unchanged, restated)

1. **INAIL grado×età capital table** — import `D.M. 45/2019` values, then a canary
   (one official grade×age value, 2025 revaluation).
2. **Morocco capital-de-référence** — the âge×salaire base table from the Dahir annex.
3. **Tunisia barème Titre V** — owner-provided text (official hosts unreachable here).
4. **Death / heirs (MA/TN)** — eligible-relatives rules alongside the road barème.
5. **Defective product** — confirmed: **no official statutory monetary formula** →
   stays a documental pre-check (Codice del Consumo frames liability, not an amount).
6. **Loss of a relative (IT)** — confirmed: **no state table** (Milan/Rome tables are
   judicial practice, not an official state source) → stays a guided pre-check.

Nothing is invented. Where an engine cannot be activated, the platform improves the
readiness / dossier and the source library makes the evidence transparent — never a
fabricated figure.
