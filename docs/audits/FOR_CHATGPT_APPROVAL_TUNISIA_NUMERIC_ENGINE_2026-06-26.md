# Approval pack — Tunisia road-injury barème (loi 2005-86)

Date: 2026-06-26 · Section: Tunisia (#12) · Currency: **TND** · Target engine
`tunisia_road_injury_bareme`.

## Decision requested

Provide / validate the bodily-injury compensation barème of the **Code des
assurances, Titre V (art. 110–179)** so the candidate engine can be built.

## Why it is a strong candidate

**Loi n° 2005-86 du 15 août 2005** inserted Titre V into the Code des assurances:
a compensation regime for bodily injury in traffic accidents whose **rating
scale (barème) is binding on both insurers and judges**, with a ±15% evaluation
margin, a 6-month amiable-offer duty, and a guarantee fund (art. 172–176). A
binding **state** barème (unlike FR/BE) → a numeric engine is feasible.

## Extraction attempt (P12) — environmental blocker, documented

- Official hosts attempted: **cga.gov.tn** (Code_Assurance_Version_FR.pdf) →
  `http=000` (not reachable); **legislation.tn** (Code des assurances / loi
  2005-86) → `ECONNREFUSED`. Both Tunisian official sites are unreachable from
  this environment, so the barème tables could not be fetched/parsed here.
- No third-party/blog source was used (rule: official only).

## Exact data needed

From Code des assurances Titre V (art. 110–179):
- the **revenu de référence** rules and any income floor/ceiling;
- the **coefficient / capitalisation scale by age** (and the taux d'incapacité
  application);
- the **décès / ayants droit** distribution;
- at least one **official worked example** for a canary.

### Expected format (CSV/JSON → CompensationTableRow)

```
row_type=tn_capitalisation_coeff   age_min, age_max, coefficient
row_type=tn_income_floor           point_value(TND)
```

## Precise question for ChatGPT

> Fornisci il barème vincolante del Code des assurances tunisino, Titre V
> (art. 110–179, loi 2005-86): revenu de référence, coefficient/capitalisation
> per età, taux d'incapacité, décès/ayants droit, con almeno un esempio
> ufficiale verificabile. Indica articolo/fonte per ogni valore.

## If approved → implementation

importer `import_tunisia_bareme` → approved dataset (TND) → engine
`tunisia_road_injury_bareme` fail-closed → canary green → UI guided→numeric
(TND, never euro). Until then Tunisia stays `official_guided_path_approved`.
