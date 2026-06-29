# P36 — Estimate Coverage & Official Sources (2026-06-29)

Purpose: answer "why are there monetary estimates only in some sections?" honestly,
and map exactly what would be needed to unlock more — **without inventing any figure,
table or coefficient** (the project's first rule: *meglio nessun calcolo che un calcolo
falso*).

## How an estimate is allowed
A monetary range (min/mid/max) may be shown **only** when an official source is
`usable_for_engine` (legally validated) AND an engine + canary test exists. Sources at
`usable_for_precheck`, `approval_needed` or `non_binding_practice` **must not** produce a
figure — the platform shows a document pre-check / dossier path instead.

## Estimate coverage today (8 validated engines)

| Country | Category | Engine? | Source basis (`usable_for_engine`) |
|---|---|:--:|---|
| Italy | Road accident — bodily injury | ✅ | `it-cap-139` (art. 139) + `it-tun-2025` (Tabella Unica D.P.R. 12/2025) |
| Italy | Road accident — micro-lesions | ✅ | `it-cap-139` |
| Italy | Medical liability — biological damage | ✅ | `it-gelli-24-2017` + `it-tun-2025` |
| Italy | Inheritance (basic legittima) | ✅ | civil-code basis |
| France | Road accident — bodily injury | ✅ | validated FR engine |
| Belgium | Road accident — bodily injury | ✅ | validated BE engine |
| Morocco | International inheritance | ✅ | validated MA engine |
| Tunisia | International inheritance | ✅ | validated TN engine |

## No estimate yet → pre-check / dossier (correct behaviour)

| Country | Category | Why no figure | Path shown to user |
|---|---|---|---|
| Italy | INAIL / work injury | `it-dm-45-2019` + `it-dlgs-38-2000` are **`approval_needed`** (grade×age table not yet legally validated) | Pre-check INAIL → dossier |
| Italy | Loss of a relative | civil-code only (`usable_for_precheck`); no validated parental-loss table | Pre-check → dossier |
| Italy | Defective product | `it-consumo-114-127` `usable_for_precheck` | Pre-check → dossier |
| Morocco | Road accident | `ma-dahir-1-84-177`, `ma-acaps-guide` are **`approval_needed`** (capital de référence not validated) | Pre-check Morocco → dossier |
| Tunisia | Road accident | `tn-code-assurances` (Titre V), `tn-loi-2005-86` **`approval_needed`** (barème not validated) | Pre-check Tunisia → dossier |
| Belgium | Road accident detail | `be-tableau-indicatif` is **`non_binding_practice`** | Estimate uses the validated engine; the indicative table is shown as context only |
| Cross-border | Road accident / succession | `eu-roma-ii-864-2007`, `eu-reg-650-2012` `usable_for_precheck` (applicable-law framing, not a tariff) | Applicable-law framing → dossier |

## Official sources (23) — status snapshot
`usable_for_engine` (3): it-cap-139, it-tun-2025, it-gelli-24-2017.
`usable_for_precheck` (12): it-cc-2043-2059, it-cc-1223-1226, it-consumo-114-127,
it-tu-inail-1124, ma-doc, ma-code-assurances, ma-moudawana, tn-doc, fr-loi-badinter,
fr-code-assurances, be-loi-1989, eu-roma-ii-864-2007, eu-reg-650-2012.
`approval_needed` (5): it-dlgs-38-2000, it-dm-45-2019, ma-dahir-1-84-177, ma-acaps-guide,
tn-code-assurances, tn-loi-2005-86.
`non_binding_practice` (1): be-tableau-indicatif.

## What would unlock the next estimates (priority)
1. **INAIL (Italy)** — the grade×age indemnity table (`D.M. 45/2019`) must be extracted,
   legally validated and flipped to `usable_for_engine`; then add an engine + canary.
2. **Morocco road accident** — *capital de référence* + liability rule (`Dahir 1-84-177`,
   ACAPS guide) validated → engine + canary.
3. **Tunisia road accident** — *barème Titre V* (`Code des assurances`) validated →
   engine + canary.

## Decision for P36 (Fase N) — honest
**No new monetary engine is activated in this phase.** Every candidate source above is
`approval_needed` (not legally validated). Promoting an unvalidated barème/table to a
public figure would violate the platform's first rule and risk inventing coefficients.
The user-facing copy stays simple and truthful, e.g.:
> "Possiamo preparare i documenti subito. L'importo richiede prima la verifica della
> tabella ufficiale di questo paese."

Unlocking these requires a **legal reviewer** to validate each table and a developer to
add the engine + canary — a controlled follow-up, not something to fabricate here.
