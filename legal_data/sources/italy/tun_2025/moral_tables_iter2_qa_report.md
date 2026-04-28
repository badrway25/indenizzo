# TUN 2025 — Tabelle 2.A/2.B/2.C iter2 QA report

> Auto-generato da `scripts/legal_data/qa_tun_moral_tables.py`.
> NESSUN dato è stato importato nel DB. NESSUN status promosso.
> Estrazione: `automated_pdfplumber_iter2`. Oracle: Tabella 1 approved.

## Sommario

| Tabella | Totali | consistent | recovered | inconsistent | needs_review | duplicati | negativi | null | mono inv | mono age |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.MIN | 9191 | 9191 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2.MID | 9191 | 9191 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2.MAX | 9191 | 9191 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Atteso per ogni tabella: 9 191 righe (= 91 invalidità × 101 età).

## Tabella 2.MIN

### Spot-check `A` (biologico) vs Tabella 1 approved

| (età, inv) | atteso | letto | esito |
|---|---:|---:|---|
| (0, 10) | 26124 | 26124 | OK |
| (1, 10) | 26124 | 26124 | OK |
| (2, 10) | 25993 | 25993 | OK |
| (50, 50) | 267618 | 267618 | OK |
| (100, 100) | 541329 | 541329 | OK |

### Top 10 pagine con issues residue

| G.U. page | issues / totale | % |
|---:|---:|---:|
| 41 | 0/341 | 0.0% |
| 42 | 0/310 | 0.0% |
| 43 | 0/310 | 0.0% |
| 44 | 0/310 | 0.0% |
| 45 | 0/310 | 0.0% |
| 46 | 0/310 | 0.0% |
| 47 | 0/310 | 0.0% |
| 48 | 0/310 | 0.0% |
| 49 | 0/310 | 0.0% |
| 50 | 0/310 | 0.0% |

## Tabella 2.MID

### Spot-check `A` (biologico) vs Tabella 1 approved

| (età, inv) | atteso | letto | esito |
|---|---:|---:|---|
| (0, 10) | 26124 | 26124 | OK |
| (1, 10) | 26124 | 26124 | OK |
| (2, 10) | 25993 | 25993 | OK |
| (50, 50) | 267618 | 267618 | OK |
| (100, 100) | 541329 | 541329 | OK |

### Top 10 pagine con issues residue

| G.U. page | issues / totale | % |
|---:|---:|---:|
| 73 | 0/341 | 0.0% |
| 74 | 0/310 | 0.0% |
| 75 | 0/310 | 0.0% |
| 76 | 0/310 | 0.0% |
| 77 | 0/310 | 0.0% |
| 78 | 0/310 | 0.0% |
| 79 | 0/310 | 0.0% |
| 80 | 0/310 | 0.0% |
| 81 | 0/310 | 0.0% |
| 82 | 0/310 | 0.0% |

## Tabella 2.MAX

### Spot-check `A` (biologico) vs Tabella 1 approved

| (età, inv) | atteso | letto | esito |
|---|---:|---:|---|
| (0, 10) | 26124 | 26124 | OK |
| (1, 10) | 26124 | 26124 | OK |
| (2, 10) | 25993 | 25993 | OK |
| (50, 50) | 267618 | 267618 | OK |
| (100, 100) | 541329 | 541329 | OK |

### Top 10 pagine con issues residue

| G.U. page | issues / totale | % |
|---:|---:|---:|
| 106 | 0/341 | 0.0% |
| 107 | 0/310 | 0.0% |
| 108 | 0/310 | 0.0% |
| 109 | 0/310 | 0.0% |
| 110 | 0/310 | 0.0% |
| 111 | 0/310 | 0.0% |
| 112 | 0/310 | 0.0% |
| 113 | 0/310 | 0.0% |
| 114 | 0/310 | 0.0% |
| 115 | 0/310 | 0.0% |

## Raccomandazione import

**Sì** per import in **dataset MORAL DRAFT** (separato da quello base `approved`). Tutte le 9 191 celle per tabella sono `consistent` con il vincolo `A + B == A+B` e con `A == oracle Tabella 1`. La monotonicità (inv crescente, età decrescente) è rispettata su tutte e tre le tabelle. La promozione a `approved` resta atto umano dello Studio.

