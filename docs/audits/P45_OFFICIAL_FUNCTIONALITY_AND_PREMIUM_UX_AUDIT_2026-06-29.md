# P45 — Official Functionality & Premium UX Audit

_Date: 2026-06-29 · Phase P45, Fase F. What is genuinely useful, what is still
only informative, and where the user needs guidance / a source / a document / an
estimate / a summary._

| Page | Useful today | Still only informative | What the user needs | P45 change |
|---|---|---|---|---|
| Home | hero, intent cards, matrix, honest "no fabricated numbers" copy | — | a clear first step | — (already strong) |
| Guided | full country × category router | the router was a list, not a recommender | a quick "what's my path" answer | **Guided Path Studio**: a client-side recommender (country + injury/offer/law toggles → recommended path), never money without a validated engine |
| Documents | upload + recognition + dossier + animated explainer | — | clarity on privacy + path | — (rich since P40) |
| Sources | library + "how to read a source" + document sheet + filters | filter UX could become a guided finder | find the right source | filters already cover country/category/type/use; left as-is (a guided finder would duplicate them — rule 14) |
| Documentation | Start-here + 9 topics + glossary + mini-FAQ | lacked per-category guidance | "what can I do for my case" | **Guides by case type** (9 cards → the existing case-type landings) |
| Result | human report header + sources + next step + print | — | a clean, printable summary | print CSS already premium; verified |
| Services | 3 visual bands + matrix | — | — | — |
| Countries | per-country landings + readiness | — | — | — |
| Matrix | truthful country × category chips | — | — | — (corrected in P40) |

## New official-functionality structures (P45)
1. **Guided Path Studio** (`/guided/`) — deterministic, CSP-safe JS recommender.
   The "estimate" path is offered **only** for Italy + injury (the only validated
   road/medical engine); Morocco/Tunisia + injury → "an official table is needed
   first"; offer → check offer; cross-border/law → applicable-law; else prepare
   documents. **No monetary figure is ever produced by the widget.**
2. **Guides by case type** (`/documentation/`) — nine category cards linking to
   the existing rich case-type landings.
3. **Official estimate validation packs** (`docs/legal_validation/`) — a formal
   per-candidate hand-off (INAIL, MA/TN road, MA/TN family loss) with a status
   enum. An engine is built only at `ready_for_engine`.

## Where a source / document / estimate / summary applies (honest map)
- **Estimate (figure shown):** IT road accident · IT danno biologico · IT medical
  liability (the only validated engines). Everywhere else → no figure.
- **Document check / summary:** INAIL, loss of a relative, defective product
  (IT); all MA/TN/FR/BE categories without a validated table.
- **Applicable-law framing:** every cross-border case (Roma II / Reg. 650).
- **Source needed before an estimate:** the five validation packs (none ready).

## Conservative decisions (rule 14 — do not reduce clarity)
- No font/palette swap; no redundant home feature section; no form redesign
  (forms already guided since P22–P31); no duplicate "source assistant" on top of
  the existing source filters.
