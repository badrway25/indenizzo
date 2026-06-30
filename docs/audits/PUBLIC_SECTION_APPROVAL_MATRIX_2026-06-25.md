# Public section approval matrix (P9)

**Phase**: P9 · 2026-06-25. Product-state (not technical) approval for every
public section. Internal/technical states (`manual_review_required`,
`unresolved`, `fail_closed`, `placeholder`, `source_verified`, `in_review`) are
**banned from the public surface** and never appear here as a section state.

## Allowed product states

- `numeric_estimate_approved` — official engine + approved dataset → a public
  number is produced for compatible inputs.
- `tabular_biological_damage_approved` — official tabular biological-damage
  estimate (TUN/art. 139) where the injury + medical-legal data are compatible.
- `offer_comparison_approved` — compares a received offer against the official
  tabular estimate.
- `official_guided_path_approved` — premium assisted path with an official
  normative framing; no automatic figure (none exists officially).
- `chatgpt_approval_required_for_numeric_engine` — an official table exists but
  is not yet machine-verified; a precise approval pack names what is needed.

## Matrix

| # | Section | Product state | Official basis | Public output |
|---|---|---|---|---|
| 1 | Incidente stradale | **numeric_estimate_approved** | D.P.R. 12/2025 (TUN art.138) + art.139 CAP (D.M. MIMIT 2025) | micro 1–9% (€) + macro ≥10% (€) |
| 2 | Responsabilità sanitaria | **tabular_biological_damage_approved** | L. 24/2017 → artt. 138/139 CAP | stima tabellare del danno biologico (1–9% art.139, ≥10% TUN) |
| 3 | Offerta assicurativa | **offer_comparison_approved** | CAP artt. 145/148 + TUN/art.139 | confronto offerta vs stima tabellare ufficiale |
| 4 | Infortunio lavoro / INAIL | **official_guided_path_approved** + `chatgpt_approval_required_for_numeric_engine` | D.P.R. 1124/1965 · D.M. 12/07/2000 · D.M. 45/2019 | percorso assistito; engine numerico in attesa tabella (FOR_CHATGPT_APPROVAL_INAIL) |
| 5 | Decesso / danno parentale | **official_guided_path_approved** | artt. 2043/2059/1223/1226 c.c. | percorso assistito per i familiari (no tabella nazionale ufficiale) |
| 6 | Prodotto difettoso | **official_guided_path_approved** | D.Lgs. 206/2005 artt. 114–127 | base normativa ufficiale + analisi del danno |
| 7 | Marocco | **official_guided_path_approved** + `chatgpt_approval_required_for_numeric_engine` | Dahir 1984 · DOC · Code des Assurances | inquadramento Dahir 1984 + percorso assistito; barème in attesa OCR (FOR_CHATGPT_APPROVAL_MOROCCO_BAREME) |
| 8 | Francia | **official_guided_path_approved** | Loi Badinter · Code des assurances | inquadramento Loi Badinter + percorso assistito (nessun barème statale computabile) |
| 9 | Belgio | **official_guided_path_approved** | Loi 21/11/1989 | inquadramento belga + percorso assistito (Tableau Indicatif = indicativo, non statale) |
| 10 | Tunisia | **official_guided_path_approved** | COC tunisino | percorso assistito con diritto tunisino |
| 11 | Casi internazionali | **official_guided_path_approved** | Reg. CE 864/2007 (Roma II) | inquadramento legge applicabile + percorso guidato |
| 12 | Ta3ouid / stranieri | **official_guided_path_approved** | Roma II · CAP/TUN (Italia) | percorso assistito multilingue |

## Public copy rule

Every section renders premium, authoritative copy — **never** "non disponibile",
"valutazione necessaria", "in revisione", "da validare", "fail-closed". Numeric
sections show the estimate (with the official source drawer + disclaimer); guided
sections show "Percorso assistito con fonte ufficiale" / "Inquadramento normativo
ufficiale" / "Stima tabellare se compatibile". FR/BE/MA/TN show **no euro
estimate** (no official engine) — only the premium guided path.
