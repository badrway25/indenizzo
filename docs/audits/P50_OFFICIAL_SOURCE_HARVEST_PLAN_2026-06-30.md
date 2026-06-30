# P50 — Official Source Harvest Plan

_Date: 2026-06-30 · Phase P50, Fase B. The plan that drives
`manage.py harvest_official_sources`. Official domains only; robots-respecting;
no aggressive scraping; **harvesting never activates an estimate** — a legal
reviewer validates the table and fills the canary first._

## Allowlist (the only hosts the harvester may fetch)
normattiva.it · gazzettaufficiale.it · inail.it · eur-lex.europa.eu ·
sgg.gov.ma · acaps.ma · cga.gov.tn · iort.gov.tn · legislation.tn ·
legifrance.gouv.fr · economie.fgov.be. Any other host is **refused**.

## Plan per country × category
| Country | Category | Official source to seek | Target site | Doc type | Needs PDF | Needs HTML scrape | Needs OCR | Risk | Priority | Expected output |
|---|---|---|---|---|---|---|---|---|---|---|
| IT | INAIL/work | D.M. 12/07/2000 menomazioni + D.M. 45/2019 | inail.it / normattiva / gazzettaufficiale | PDF+HTML | yes | maybe | maybe | high | **high** | verbatim menomazione%×età indemnity table |
| MA | road / biologico | Dahir 1-84-177 capital de référence | acaps.ma / sgg.gov.ma | PDF (scan) | yes | no | **yes** | high | **high** | transcribed barème + AIPP method |
| TN | road / biologico | Code des assurances Titre V barème | cga.gov.tn / iort.gov.tn | HTML/PDF | maybe | yes | maybe | medium | **high** | transcribed Titre V scale + coefficients |
| MA | loss of relative | Dahir ayants-droit shares | sgg.gov.ma | PDF (scan) | yes | no | yes | high | medium | verbatim share table (inside road barème) |
| TN | loss of relative | Titre V décès distribution | cga.gov.tn | HTML/PDF | maybe | yes | maybe | medium | medium | verbatim distribution |
| IT | road / biologico / medical | CAP art.139 + TUN D.P.R. | normattiva | HTML | no | no | no | low | done | provenance only (engine already live) |
| IT | inheritance | C.C. Libro II legittima | normattiva | HTML | no | yes | no | low | medium | legittima/quota fractions |
| MA/TN | inheritance | Moudawana / CSP faraïd | sgg.gov.ma / iort.gov.tn | HTML/PDF | maybe | yes | maybe | high | medium | faraïd shares + estate-value rules |
| IT/EU | defective product | Cod. Consumo 114–127 / Dir. 85/374 | normattiva / eur-lex | HTML | no | no | no | n/a | low | **no quantum exists** → framing only |
| FR | road | Loi Badinter (no State barème) | legifrance | HTML | no | no | no | n/a | low | **no binding barème** → framing only |
| BE | road | Loi 1989 (Tableau Indicatif non-binding) | economie.fgov.be | HTML | no | no | no | n/a | low | **no binding barème** → framing only |
| EU | cross-border / succession | Roma II 864/2007 · Reg. 650/2012 | eur-lex | HTML/PDF | no | no | no | low | low | conflict-of-laws framing only |

## Priority order
1. IT INAIL · 2. MA road · 3. TN road · 4. MA/TN family loss ·
5. product liability **only if** an official monetary formula exists (it does not) ·
6. FR/BE **only if** a binding State source exists (it does not).

## Hard stops (cardinal rule)
- No engine without a validated official table **and** a legally-reviewed canary.
- Non-binding practice (Mornet, Tableau Indicatif, Milano table) may be documented
  internally but **never** drives an automatic official amount.
- No CAPTCHA/paywall/login bypass; robots.txt respected; one request per target.
- No heavy PDF / OCR temp / debug committed; only a gitignored provenance manifest.
