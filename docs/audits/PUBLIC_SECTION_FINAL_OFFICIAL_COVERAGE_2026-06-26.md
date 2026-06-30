# Public section — final official coverage (P10)

Date: 2026-06-26 · Branch: `feature/p3-public-ux-redesign`

Authoritative map of every public section's **final product state**, its
**official source basis**, and whether a computable engine exists. Cardinal
rule honoured: no amount/coefficient/table is invented; a numeric engine
exists **only** where an approved official dataset has been imported and
canary-tested. Everything else is a premium **official guided path** — never
a weak label.

Allowed public states: `numeric_estimate_approved`,
`tabular_biological_damage_approved`, `offer_comparison_approved`,
`official_guided_path_approved`.
Internal-only (docs/tests/admin, never public):
`chatgpt_approval_required_for_numeric_engine`.

| # | Section | Public state | Official source (chip) | Norm | Computable formula | Engine | If no engine — reason |
|---|---|---|---|---|:--:|:--:|---|
| 1 | Incidente stradale (IT) | `numeric_estimate_approved` | D.P.R. 12/2025 — TUN; artt. 138–139 CAP | D.Lgs. 209/2005 | yes | `italy_tun_point_value_v1` | — |
| 2 | Microlesioni 1–9% (IT) | `numeric_estimate_approved` | D.M. MIMIT 18/07/2025; art. 139 CAP | art. 139 D.Lgs. 209/2005 | yes | `italy_art139_micro_v1` | — |
| 3 | Macrolesioni ≥10% (IT) | `numeric_estimate_approved` | D.P.R. 12/2025 — TUN; art. 138 CAP | art. 138 D.Lgs. 209/2005 | yes | `italy_tun_point_value_v1` | — |
| 4 | Responsabilità sanitaria (IT) | `tabular_biological_damage_approved` | L. 24/2017; artt. 138–139 CAP | L. 24/2017 (Gelli-Bianco) | yes (tabellare) | `medical_liability_biological_damage` | colpa/nesso/perdita di chance restano analisi guidata |
| 5 | Verifica offerta assicurativa (IT) | `offer_comparison_approved` | TUN 2025; artt. 138–139 CAP; IVASS | D.Lgs. 209/2005 | yes (confronto) | reuse engines 1–3 | — |
| 6 | INAIL / infortunio lavoro | `official_guided_path_approved` | D.P.R. 1124/1965; D.Lgs. 38/2000 art.13; D.M. 12/07/2000 | TU INAIL | **table not yet imported** | no | tabella indennizzo D.M. 2000 non ancora estratta/verificata → `FOR_CHATGPT_APPROVAL_INAIL_TABLE_2026-06-26.md` |
| 7 | Decesso / danno parentale (IT) | `official_guided_path_approved` | artt. 2043, 2059, 1223 Cod. Civile | Cod. Civile | no statale | no | nessuna tabella **governativa/ministeriale** computabile (Milano = prassi giurisprudenziale, non fonte statale) |
| 8 | Prodotto difettoso (IT) | `official_guided_path_approved` | artt. 114–127 Cod. del Consumo; Dir. 85/374/CEE | D.Lgs. 206/2005 | no | no | norma di responsabilità senza barème: quantificazione caso-per-caso |
| 9 | Marocco — incidenti stradali | `official_guided_path_approved` | Dahir 1-84-177; ACAPS; Code des assurances | Dahir 1984 | barème non estratto | no | `FOR_CHATGPT_APPROVAL_MOROCCO_BAREME_2026-06-25.md` (PDF non parsato a valori verificati) |
| 10 | Francia — circulation | `official_guided_path_approved` | Loi Badinter (85-677); Code des assurances; nomenclature Dintilhac | Loi 85-677 | no barème statale | no | Mornet/Gazette du Palais = référentiel indicativo, non legge statale → nessuna stima numerica |
| 11 | Belgio — RC auto | `official_guided_path_approved` | Loi 21/11/1989; Code civil (resp. extracontr.) | Moniteur belge | Tableau indicatif non statale | no | il Tableau indicatif è indicativo, non obbligatorio statale → no engine |
| 12 | Tunisia — accidents corporels | `official_guided_path_approved` | Code des assurances TN; COC; JORT | JORT | barème non confermato | no | `FOR_CHATGPT_APPROVAL_FR_BE_TN_2026-06-25.md` |
| 13 | Casi internazionali | `official_guided_path_approved` | Reg. (CE) 864/2007 (Roma II); Reg. (UE) 650/2012 | EUR-Lex | no (legge applicabile) | no | inquadramento conflitto di leggi, non quantificazione |
| 14 | Ta3ouid / cittadini stranieri in Italia | `official_guided_path_approved` (stima IT TUN se invalidità accertata) | TUN 2025; Reg. (CE) 864/2007 | D.P.R. 12/2025 | yes se IT | reuse engine IT | per danno su territorio IT usa engine 1–3; profilo multilingue |
| 15 | Documentazione estera / consolare | `official_guided_path_approved` | Reg. (UE) 650/2012; convenzioni consolari | EUR-Lex | no | no | servizio documentale, nessun importo |

## Public copy & CTA per guided section

- INAIL: «Indennizzo INAIL e danno differenziale: percorso assistito con fonte ufficiale» → CTA contatto guidato. Chip: D.P.R. 1124/1965 · D.Lgs. 38/2000 · D.M. 12/07/2000.
- Prodotto difettoso: «Responsabilità da prodotto difettoso: analisi guidata su fonte ufficiale» → `/case-types/product-liability/`. Chip: artt. 114–127 Cod. del Consumo · Dir. 85/374/CEE.
- Decesso/parentale: «Percorso assistito per familiari e danno parentale». Chip: artt. 2043, 2059, 1223 c.c.
- Marocco: «Incidenti stradali in Marocco: percorso assistito fondato su Dahir 1984, ACAPS e responsabilità civile».
- Francia: «Accidents de la circulation en France: inquadramento Loi Badinter e percorso assistito».
- Belgio: «Belgio: inquadramento responsabilità civile/assicurativa e percorso assistito».
- Tunisia: «Tunisia: percorso assistito con inquadramento assicurativo e civile».
- Internazionali: «Inquadramento della legge applicabile e coordinamento documentale».

## What stays internal only

- The technical states (`chatgpt_approval_required_for_numeric_engine`, dataset
  `needs_review`, source `content_hash`) live in admin/docs/tests, never public.
- Approval packs (this folder, `FOR_CHATGPT_APPROVAL_*`) list the exact official
  data needed to turn a guided path into a numeric engine — the public never
  sees a blocked/"not available"/"placeholder" label.

## Engine policy

A new numeric engine is added **only** after an official dataset is imported,
approved, and canary-tested to the cent (as for art. 138/139). Where the
official table could not be extracted and verified in this environment, the
section ships as a guided path and the gap is documented in an approval pack —
never as an invented figure.
