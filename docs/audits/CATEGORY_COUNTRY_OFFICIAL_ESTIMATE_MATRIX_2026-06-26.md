# Category × Country official-estimate matrix (P14)

Date: 2026-06-26 · Branch: `feature/p3-public-ux-redesign`

The platform is organised as **COUNTRY × CATEGORY × OFFICIAL SOURCE × ESTIMATE
TYPE**. Each cell resolves to one public state — never a weak/blocked label,
never an invented amount:

- `numeric` — official computable formula/table imported + canary green → euro estimate.
- `tabular` — official table covers only part (e.g. danno biologico) → partial estimate.
- `comparison` — compares a user amount against the official estimate.
- `pre_check` — official source exists but the numeric table is not yet imported →
  structured documental pre-check (says exactly which data/source, then the estimate
  activates once the table is validated). NOT "not available".
- `guided` — official normative basis, no computable formula → assisted pathway + source chips.
- `applicable_law` — conflict-of-laws framing (Rome II / Reg. 650/2012), no amount.

Internal-only (docs/admin/approval packs, never public):
`chatgpt_approval_required_for_numeric_engine`.

## Engines live today (numeric/tabular/comparison)

| key | engine | type |
|---|---|---|
| IT road micro 1–9% | `italy_art139_micro_v1` | numeric |
| IT road macro 10–100% | `italy_tun_point_value_v1` | numeric |
| IT medical (danno biologico) | `medical_liability_biological_damage` | tabular |
| IT insurance offer | reuse road engines | comparison |

Everything else below is `pre_check` or `guided` (no invented figures).

---

## ITALIA

| # | Category | Official source · norm | Formula? | Engine | Public state | Input | Public output | CTA |
|---|---|---|:--:|:--:|---|---|---|---|
| 1 | Road accident — injury | D.P.R. 12/2025 (TUN); art. 139 CAP (D.Lgs. 209/2005) | yes | yes | **numeric** | età, invalidità %, ITT | min/mid/max € | wizard road |
| 2 | Road accident — death | artt. 2043, 2059 c.c.; CAP RC auto | no (no state table) | no | **guided** | rapporto, età, conviv., offerta | inquadramento + checklist | contatto |
| 3 | Loss of relative / parental | artt. 2043, 2059, 1223, 1226 c.c. | no (Milano = prassi, non statale) | no | **guided** | rapporto, conviv., docs | percorso assistito | contatto |
| 4 | Medical liability | L. 24/2017; artt. 138–139 CAP | yes (tabellare) | yes | **tabular** | invalidità %, ITT | stima danno biologico | wizard medical |
| 5 | Work injury / INAIL | D.P.R. 1124/1965; D.Lgs. 38/2000; D.M. 45/2019 | table not imported | no | **pre_check** | grado, età, data, tipo, capitale/rendita | pre-check INAIL + dati per stima | contatto |
| 6 | Defective product | artt. 114–127 Cod. Consumo; Dir. 85/374/CEE | no | no | **guided** | prodotto, difetto, nesso, prova | analisi guidata | contatto |
| 7 | Insurance offer | TUN/art. 139; CAP artt. 145, 148 | yes (confronto) | yes | **comparison** | offerta + età + invalidità | offerta vs stima + scostamento | wizard offer |
| 8 | International / applicable law | Reg. (CE) 864/2007 (Roma II) | — | no | **applicable_law** | parti, luogo evento | inquadramento legge | contatto |
| 9 | Foreign citizens / Ta3ouid | TUN; Roma II | yes se IT | reuse | **numeric (se IT)** | come road | stima se danno in IT | wizard road |
| 10 | Foreign / consular docs | Reg. (UE) 650/2012; conv. consolari | no | no | **guided** | documenti | verifica documentale | contatto |

## MAROCCO (non solo successione)

| # | Category | Official source · norm | Formula? | Candidate engine | Public state | Input | Output | CTA |
|---|---|---|:--:|:--:|---|---|---|---|
| 1 | Road accident — injury | Dahir 1-84-177 (1984); ACAPS; Code des assurances | barème scanné (annexe) | yes (cand.) | **pre_check** | revenu, âge, IPP, responsabilité | dati per stima Dahir | contatto |
| 2 | Road accident — death | Dahir 1984 (ayants droit); ACAPS | % ayants droit estratti | yes (cand.) | **pre_check** | décès, ayants droit, revenu | dati per indemnité | contatto |
| 3 | Bodily damage / incapacité | Dahir 1984; ACAPS guide | capital de référence mancante | yes (cand.) | **pre_check** | revenu, âge, IPP | inquadramento + dati | contatto |
| 4 | Ayants droit / familiari | Dahir 1984 (conjoint 25%, descendants…) | % estratti | yes (cand.) | **pre_check** | rapporto, n. familiari | distribuzione % | contatto |
| 5 | Responsabilité civile | Code des obligations et des contrats | no | no | **guided** | fatti, responsabilità | inquadramento | contatto |
| 6 | Assurance obligatoire | Code des assurances; ACAPS | no | no | **guided** | polizza, offerta | verifica documentale | contatto |
| 7 | Succession internationale | Moudawana (Loi 70-03); Reg. 650/2012 | no | no | **guided** | eredi, beni | analisi successoria | wizard MA inh. |

> Moudawana resta SOLO per status/familiari/successione, mai motore danno corporeo.

## TUNISIA (oltre la pagina generica)

| # | Category | Official source · norm | Formula? | Candidate | Public state | Input | Output | CTA |
|---|---|---|:--:|:--:|---|---|---|---|
| 1 | Road accident — injury | Loi 2005-86; Code des assurances Titre V (art. 110–179); CGA | barème statale **vincolante** non estratto qui | yes (cand.) | **pre_check** | revenu, âge, IPP | dati per barème | contatto |
| 2 | Road accident — death | Loi 2005-86 (décès/ayants droit) | barème non estratto | yes (cand.) | **pre_check** | décès, ayants droit | dati per indemnité | contatto |
| 3 | Responsabilité assurance | Code des assurances; CGA | no | no | **guided** | polizza, offerta | inquadramento assicurativo | contatto |
| 4 | Bodily damage | Loi 2005-86; COC tunisien | barème non estratto | yes (cand.) | **pre_check** | IPP, revenu | dati per stima | contatto |
| 5 | Succession internationale | CSP (Livre IX); Loi 98-97; Reg. 650/2012 | no | no | **guided** | eredi, beni | analisi successoria | wizard TN inh. |

## FRANCIA

| # | Category | Source | State barème? | State | Output |
|---|---|---|:--:|---|---|
| 1 | Road accident — injury | Loi Badinter (85-677); Code des assurances | no (Mornet/Dintilhac indicativi) | **guided** | inquadramento Badinter |
| 2 | Death / parental | Code civil; Badinter | no | **guided** | percorso assistito |
| 3 | Bodily damage | Nomenclature Dintilhac (classif.) | no | **guided** | inquadramento |
| 4 | Insurance offer | Code des assurances | no engine | **guided** | verifica documentale |
| 5 | Docs | — | — | **guided** | verifica documentale |

## BELGIO

| # | Category | Source | State barème? | State | Output |
|---|---|---|:--:|---|---|
| 1 | Road accident — injury | Loi 21/11/1989 (RC auto); Code civil | no (Tableau indicatif non statale) | **guided** | inquadramento RC |
| 2 | Bodily damage | Code civil resp. extracontr. | no | **guided** | percorso assistito |
| 3 | Death | Code civil | no | **guided** | percorso assistito |
| 4 | Assurance | SPF Économie; Loi 1989 | no | **guided** | verifica documentale |

## UNIONE EUROPEA / INTERNAZIONALE

| # | Category | Source | State | Output |
|---|---|---|---|---|
| 1 | International road accident | Reg. (CE) 864/2007 (Roma II) | **applicable_law** | legge applicabile + foro |
| 2 | International succession | Reg. (UE) 650/2012 | **applicable_law** | legge applicabile |
| 3 | Cross-border docs | conv. consolari; 650/2012 | **guided** | coordinamento documentale |

---

## What unlocks numeric estimates (→ approval queue)

- **INAIL table (IT)** → unlocks IT work-injury numeric. See `FOR_CHATGPT_APPROVAL_INAIL_TABLE_2026-06-26.md`.
- **Morocco capital-de-référence table (Dahir annex)** → unlocks MA road/death/bodily numeric (formula + coefficients already extracted). See `MOROCCO_BAREME_CANDIDATE_2026-06-26.md`.
- **Tunisia Code des assurances Titre V barème** → unlocks TN road/death numeric. See `FOR_CHATGPT_APPROVAL_TUNISIA_NUMERIC_ENGINE_2026-06-26.md`.
- France/Belgium: no state barème → guided is final.
- Death/parental (IT): no state/ministerial table → guided is final.

Consolidated decisions: `CHATGPT_APPROVAL_QUEUE_2026-06-26.md`.
