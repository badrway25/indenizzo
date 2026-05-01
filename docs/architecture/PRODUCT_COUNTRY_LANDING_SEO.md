# Product — country landing pages (SEO + multilingua)

**Iter**: F-product-country-landing-seo-multilang
**Data**: 2026-04-30
**Stato**: implementato + testato in locale. **Nessun deploy.**

> Pagine pubbliche per ciascun paese coperto dall'MVP (IT, FR,
> BE, MA, TN). Spiegano cosa è disponibile oggi, cosa è in
> validazione legale, e guidano l'utente verso wizard/contact.
> Nessuna affermazione di "calcoli reali" per i paesi
> non-Italia. SEO-ready (title/meta description), multilingua
> via i18n_patterns esistente. IT smoke 35/10/0 → 26 268 / 27 353
> / 28 439 EUR verificato.

---

## 1. Cosa è stato aggiunto

| Area | File | Tipo |
|---|---|---|
| URLs | `apps/core/urls.py` | 5 nuovi path `/countries/{italy,france,belgium,morocco,tunisia}/` |
| Views | `apps/core/views.py` | `_country_landing_context()` + 5 view `country_*` |
| Template | `templates/public/country_landing.html` (nuovo) | shared, driven da context |
| Index | `templates/public/countries.html` | aggiunto link "Open country page" per le 5 card |
| Test | `apps/core/test_country_landings.py` (nuovo) | 25 test (5 parametric × 5 path + 9 dedicati) |
| Docs | questo file | — |

Niente nuove dipendenze. Niente touch a calculator/engine/wizard
form/dataset/formula. Niente schema migration.

---

## 2. Mappa URL

URL names (registrati con prefisso `core:`):

| URL name | Path |
|---|---|
| `core:country_italy` | `/countries/italy/` |
| `core:country_france` | `/countries/france/` |
| `core:country_belgium` | `/countries/belgium/` |
| `core:country_morocco` | `/countries/morocco/` |
| `core:country_tunisia` | `/countries/tunisia/` |

Tutti i path sono dentro `i18n_patterns`, quindi automaticamente
disponibili anche con prefisso lingua: `/fr/countries/france/`,
`/ar/countries/morocco/`, `/en/countries/italy/`, ecc.

Verificato dai test: `/fr/...`, `/ar/...`, `/en/...` ritornano
HTTP 200.

---

## 3. Stato prodotto per paese

### 3.1 Italia (IT)
- **Status badge**: `Calculator available` (ok-tone).
- **Case type**: `road_accident_bodily_injury`.
- **Wizard CTA**: `/wizard/it/road-accident/` ("Start Italian compensation simulation").
- **Legal sources**:
  - D.P.R. 12/2025 (Tabella Unica Nazionale) — **approved**
  - D.Lgs. 209/2005 (CAP) — needs review
  - MIMIT 2025 (art. 139) — needs review
  - MIMIT 2025 (macrolesioni) — needs review
  - Tabelle Tribunale Milano 2024 — needs review
- **Messaggio chiave**: l'utente può ottenere un range indicativo (min/mid/max), informativo e non vincolante.

### 3.2 Francia (FR)
- **Status badge**: `Legal sources under review` (warn-tone).
- **Case type**: `road_accident_bodily_injury`.
- **Wizard CTA**: `/wizard/fr/road-accident/` ("Open France validation wizard").
- **Legal sources**:
  - Référentiel Mornet 2024 — needs review
  - Barème Gazette du Palais 2022 — needs review
  - Loi Badinter 1985 — needs review
  - Rapport Dintilhac 2005 — needs review
- **Messaggio chiave**: il wizard accetta la richiesta ma il calculator è scaffold; nessun importo automatico.

### 3.3 Belgio (BE)
- **Status badge**: `Legal sources under review` (warn-tone).
- **Case type**: `road_accident_bodily_injury`.
- **Wizard CTA**: `/wizard/be/road-accident/` ("Open Belgium validation wizard").
- **Legal sources**:
  - Tableau Indicatif 2020 — needs review (historical fallback)
  - Tableau Indicatif 2024 — needs review (OCR pendente)
  - Tables Schryvers — needs review
  - Loi RC auto 1989 — needs review
- **Messaggio chiave**: idem FR, scaffold.

### 3.4 Marocco (MA)
- **Status badge**: `Legal sources under review` (warn-tone).
- **Case type**: `international_inheritance` (NON road accident).
- **Wizard CTA**: `/wizard/ma/inheritance/` ("Request Moroccan inheritance review").
- **Legal sources**:
  - Moudawana (Code de la famille, Loi 70-03) — needs review
  - Code des droits réels (Loi 39-08) — needs review
  - Reg. UE 650/2012 — needs review
- **Messaggio chiave**: framework successioni cross-border. Wizard raccoglie input qualitativi; nessun calcolo quote farḍ automatico.

### 3.5 Tunisia (TN)
- **Status badge**: `Legal sources under review` (warn-tone).
- **Case type**: `international_inheritance`.
- **Wizard CTA**: `/wizard/tn/inheritance/` ("Request Tunisian inheritance review").
- **Legal sources**:
  - CSP (Livre IX «De la succession») — needs review
  - Loi 98-97 (Code DIP) — needs review
  - JORT 1956 — needs review
  - Reg. UE 650/2012 — needs review
- **Messaggio chiave**: idem MA, con specificità Loi 98-97 + Reg. 650/2012.

---

## 4. Messaggi legali approvati / non approvati

### 4.1 Italia (calcolatore disponibile)

> "Studio Legale Badrane provides an indicative compensation
> simulation for Italy based on approved legal sources. The
> estimate is informative and never a guarantee of outcome."

### 4.2 FR / BE / MA / TN (sotto review)

> "Legal sources for {country} are currently under Studio
> review. The wizard accepts your request and our team replies
> after a manual legal validation. No automatic estimate is
> issued until that review is complete."

Inoltre, in fondo a ogni pagina **non-Italia**:

> "No automatic estimate is currently issued until legal review
> is complete."

### 4.3 Cosa NON appare mai

- ❌ Importi numerici (verificato dai test: `26268`, `27353`,
  `28439` non sono presenti su FR/BE).
- ❌ Claim "guaranteed result", "best compensation", "maximum
  payout", ecc.
- ❌ Comparazioni con concorrenti.
- ❌ Affermazioni che il calculator è disponibile per FR/BE/MA/TN.

---

## 5. SEO / meta implementati

Per ogni landing:

- **`<title>`**: `"{country} — coverage and legal sources — {SITE_NAME}"`. Country-specific via `blocktranslate`.
- **`<meta name="description">`**: per IT contiene "indicative compensation simulation for Italy"; per gli altri "{country} legal sources are under Studio review. No automatic estimate is currently issued."
- **`<meta name="robots">`**: `index, follow` (default base.html).
- **H1 unico**: ogni pagina ha esattamente UN tag `<h1>` (verificato dai test).
- **Struttura H2/H3 pulita**: H2 per "What this page covers", "Current status", "Legal basis", "Next step". Niente H3 oggi.

### 5.1 Cosa NON è ancora implementato (fuori scope pass)

- `<link rel="canonical">` (nessun pattern esistente da estendere — sarà un pass dedicato).
- `og:title` / `og:description` (idem).
- `<link rel="alternate" hreflang="...">` (cross-link automatico tra versioni multilingua).
- Schema.org JSON-LD `LegalService` / `Service`.
- Sitemap dynamic (Django `sitemaps` framework).

---

## 6. Multilingua / i18n

### 6.1 Stringhe traducibili
Tutte le stringhe di testo nei template usano `{% translate %}`
o `{% blocktranslate %}` (con `with country=...` per i nomi
paese). Nessuna stringa è hardcoded in inglese senza marker.

### 6.2 Supporto i18n_patterns
Django `i18n_patterns` di config/urls.py applica automaticamente
i prefissi:
- `/countries/italy/` (default it)
- `/fr/countries/italy/`
- `/en/countries/italy/`
- `/ar/countries/italy/` (RTL automatico via `dir="rtl"` in base.html)

Test verificati:
- `/fr/countries/france/` → 200
- `/ar/countries/morocco/` → 200
- `/en/countries/italy/` → 200

### 6.3 Compilazione `.mo`
Le `.po` non sono compilate in questo iter (niente `manage.py
compilemessages`). Le stringhe sono **marcate** ma il
fallback è il testo source inglese. La traduzione professionale
sarà un pass dedicato (vedi §8).

### 6.4 Cautela giuridica
Per i nomi di fonti legali (Moudawana, CSP, Tableau Indicatif,
ecc.) si usa la denominazione **originale** del documento, mai
una "traduzione giuridica" creativa. Esempio: si scrive "Code
du statut personnel — Livre IX «De la succession»" identico
in tutte le lingue, non si traduce in inglese il termine
tecnico legale.

---

## 7. Test aggiunti (25 totali, tutti passati)

`apps/core/test_country_landings.py`:
1. `test_country_landings_return_200` (5 parametric) — tutte le 5 landing rispondono 200.
2. `test_country_landings_have_single_h1` (5 parametric) — esattamente 1 `<h1>` per pagina.
3. `test_italy_landing_has_wizard_cta` — link `/wizard/it/road-accident/` + badge "Calculator available".
4. `test_france_landing_marked_under_review_and_no_calculated_claim` — "Legal sources under review" + "requires legal validation"; importi IT (26268/27353/28439) NON presenti.
5. `test_belgium_landing_under_review_and_no_amounts` — idem FR, "scaffold" presente.
6. `test_morocco_landing_inheritance_wording_and_cta` — "International inheritance"/"inheritance", Moudawana, Reg. 650/2012, link `/wizard/ma/inheritance/`.
7. `test_tunisia_landing_inheritance_wording_and_cta` — CSP, Loi 98-97, link `/wizard/tn/inheritance/`.
8. `test_countries_index_links_to_five_landings` — `/countries/` contiene 5 link.
9. `test_country_landings_i18n_prefixed` (3 parametric) — `/fr/.../france/`, `/ar/.../morocco/`, `/en/.../italy/` → 200.
10. `test_country_landings_have_seo_title_and_meta_description` (5 parametric) — title customizzato, meta description ≥ 30 char.
11. `test_italy_smoke_run_simulation_35_10_0` — 35/10/0 → 26 268 / 27 353 / 28 439 EUR (canarino regressione).

Test 11 conferma che il calculator IT non è stato toccato.

---

## 8. Cosa resta per produzione

### 8.1 Sitemap dynamic
- Django `sitemaps` framework con `LandingSitemap` che enumera le
  5 landing per le 4 lingue (20 entry totali).
- Endpoint `/sitemap.xml` accessibile pubblicamente.
- `<lastmod>` da `git log` o da una variabile manuale.

### 8.2 hreflang completo
- `<link rel="alternate" hreflang="it" href="/countries/italy/">`
  + 3 alternative su ogni landing.
- Necessario per Google Search Console multi-region.
- Implementabile via context processor che esponga le 4 alternate URLs.

### 8.3 Traduzioni professionali
Oggi: stringhe marcate ma `.po` non compilate. Per la
produzione:
1. Esecuzione `manage.py makemessages -l fr -l en -l ar`.
2. Traduzione professionale (no LLM) delle landing
   country-specific.
3. **Importante**: per le fonti legali tecniche, le traduzioni
   devono essere validate dallo Studio (non ricreare un termine
   giuridico).
4. `manage.py compilemessages` in pipeline build.

### 8.4 Schema.org JSON-LD
Schema `LegalService` o `Service` per migliorare la SERP. Esempio:
```json
{
  "@context": "https://schema.org",
  "@type": "LegalService",
  "name": "Studio Legale Internazionale Badrane",
  "areaServed": ["Italy", "France", "Belgium", "Morocco", "Tunisia"],
  "url": "https://simulatore.studiolegalebadrane.it/countries/italy/"
}
```

### 8.5 Contenuti lunghi
Pass futuro:
- FAQ per paese (almeno 5 domande/risposte per ciascuno).
- Casi tipo (worked examples) per IT.
- Glossario legale localizzato.
- Blog/articoli (CMS dedicato — `apps.cms_content` già scaffoldato).

### 8.6 OG / Twitter cards
Per condivisione social:
- `og:title`, `og:description`, `og:image` per paese.
- `twitter:card`, `twitter:title`.
- Immagine paese dedicata (oggi nessuna).

### 8.7 Performance
- Tailwind via CDN (warning su CLAUDE.md): passare a build PostCSS.
- Static asset compression (gzip/brotli) lato reverse proxy.
- Lazy loading immagini quando aggiunte.

---

## 9. Validazione

```bash
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
```

---

## 9-bis. Appendice — Pass 2: canonical + hreflang

**Iter**: F-product-country-landing-pass2-canonical-hreflang.
**Data**: 2026-05-01.

### File aggiunti / modificati (pass 2)

| Area | File | Tipo |
|---|---|---|
| Helpers | `apps/core/seo.py` (nuovo) | `build_canonical_url`, `build_hreflang_alternates` |
| Views | `apps/core/views.py` | `_render_country_landing()` shared che inietta canonical+alternates |
| Template | `templates/public/country_landing.html` | block `head_extra` con `<link rel=canonical>` + `<link rel=alternate hreflang=...>` |
| Test | `apps/core/test_country_landings_seo.py` (nuovo) | 9 test (21 con parametric expanded) |

### Helper API

```python
from apps.core.seo import build_canonical_url, build_hreflang_alternates

build_canonical_url(request) -> str
# es. "https://example.test/countries/italy/"
# Self-reference: la versione localizzata canonicalizza se stessa.

build_hreflang_alternates(request, view_name="core:country_italy") -> list[dict]
# [
#   {"lang": "it",        "href": "https://.../countries/italy/"},
#   {"lang": "fr",        "href": "https://.../fr/countries/italy/"},
#   {"lang": "en",        "href": "https://.../en/countries/italy/"},
#   {"lang": "ar",        "href": "https://.../ar/countries/italy/"},
#   {"lang": "x-default", "href": "https://.../countries/italy/"},
# ]
```

Pure-functions, nessun touch DB. Mai sollevano: se `reverse(view_name)`
fallisce per una lingua, quell'entry viene saltata (la pagina
resta servibile).

### Mapping lingue → URL

`config/urls.py` usa `i18n_patterns(prefix_default_language=False)` con
`LANGUAGE_CODE=it`, quindi:

| Lingua | URL pattern |
|---|---|
| `it` (default) | `/countries/<slug>/` |
| `fr` | `/fr/countries/<slug>/` |
| `en` | `/en/countries/<slug>/` |
| `ar` | `/ar/countries/<slug>/` |

`x-default` punta sempre alla versione `it` (no prefisso). Verificato
dal test #4: `x-default` href è identico a `it` href.

### Comportamento canonical

- Self-reference: la versione `/fr/countries/france/` ha
  `<link rel="canonical" href=".../fr/countries/france/">`.
  Pattern raccomandato da Google quando si usa hreflang.
- `request.build_absolute_uri(request.path)` → niente dominio
  hardcoded.

### Limiti pass 2

- Solo le 5 landing paese sono cablate. Home, methodology, privacy
  ecc. NON hanno ancora canonical/hreflang. Sarà un pass futuro
  (richiede uno sweep templates).
- Nessun OG/Twitter card aggiunto (pass futuro).
- Nessun `og:locale` / `og:locale:alternate`.
- Le traduzioni `.po` non sono compilate: il content delle
  alternates è ancora in inglese sul body, ma i `<link>` puntano
  correttamente alle URL i18n-prefixed.

### Test aggiunti (21 totali, tutti passati)

`apps/core/test_country_landings_seo.py`:
1. `test_italy_landing_has_canonical` — `/countries/italy/` → canonical termina con `/countries/italy/`.
2. `test_france_landing_has_canonical` — idem per Francia.
3. `test_country_landings_have_all_hreflang_alternates` × 5 — ogni landing ha {it, fr, en, ar, x-default}.
4. `test_x_default_points_to_italian_default_version` — `x-default` href = `it` href, no prefisso.
5. `test_french_prefixed_path_canonical_contains_fr_prefix` — `/fr/countries/france/` → canonical contiene `/fr/`.
6. `test_arabic_landing_has_arabic_alternate` — `/ar/countries/morocco/` ha `hreflang=ar`.
7. `test_no_duplicate_hreflang` × 5 — nessun lang duplicato per pagina.
8. `test_country_landings_still_200` × 5 — 200 invariato.
9. `test_italy_smoke_run_simulation_35_10_0` — 26 268 / 27 353 / 28 439.

### Cosa resta per produzione

- **Sitemap dynamic** (`django.contrib.sitemaps`): includere le 5
  landing × 4 lingue (20 entry) con `<lastmod>`.
- **OG / Twitter cards**: per paese, con immagine dedicata.
- **`og:locale:alternate`**: equivalente OG di hreflang.
- **JSON-LD `LegalService`**: schema.org markup per migliorare
  SERP rich result.
- **Traduzioni professionali** validate dallo Studio (i `.po` di
  ogni lingua), poi `compilemessages` in pipeline.
- Estendere canonical/hreflang **a tutte le pagine pubbliche**
  (home, methodology, privacy, disclaimer, /countries/, /case-types/),
  non solo le 5 landing paese.

---

## 10. Disclaimer

Questo iter aggiunge solo pagine informative pubbliche. Non
altera dati legali, calcoli, o l'output del calcolatore Italia.
Le claim sono caute e conformi a CLAUDE.md (nessuna garanzia di
risultato, nessun valore inventato per i paesi non operativi).
Il disclaimer obbligatorio CLAUDE.md è presente in fondo a ogni
landing e nel partial `disclaimer_banner.html` globale.
