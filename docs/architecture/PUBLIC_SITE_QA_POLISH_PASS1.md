# Public site QA polish — pass 1 (F-product-public-site-qa-polish-pass1)

Stato: completato 2026-05-01.

QA prodotto end-to-end del sito pubblico dopo immagini Pexels, OG asset
PNG e traduzioni i18n pass3. Obiettivo: identificare e risolvere
piccoli problemi UX/copy/template che restano dopo i pass infrastrutturali,
**senza toccare dati legali o motori di calcolo**.

Nessun dato approvato modificato. Italy 35/10/0 invariato a
26 268 / 27 353 / 28 439 EUR. FR/BE/MA/TN restano under legal review.

---

## 1. Pagine testate

### Desktop (1280×900)

| # | Path | Lang | Status |
|---|------|------|--------|
| 1 | `/` | IT | 200 |
| 2 | `/fr/` | FR | 200 |
| 3 | `/ar/` | AR | 200 (RTL) |
| 4 | `/countries/` | IT | 200 |
| 5 | `/countries/italy/` | IT | 200 |
| 6 | `/fr/countries/france/` | FR | 200 |
| 7 | `/ar/countries/morocco/` | AR | 200 (RTL) |
| 8 | `/methodology/` | IT | 200 |
| 9 | `/fr/methodology/` | FR | 200 |
| 10 | `/wizard/` | IT | 200 |
| 11 | `/wizard/it/road-accident/` | IT | 200 |
| 12 | `/wizard/fr/road-accident/` | IT default | 200 |
| 13 | `/wizard/be/road-accident/` | IT default | 200 |
| 14 | `/wizard/ma/inheritance/` | IT default | 200 |
| 15 | `/wizard/tn/inheritance/` | IT default | 200 |
| 16 | `/contact/` | IT | 200 |
| 17 | `/fr/contact/` | FR | 200 |
| 18 | `/ar/contact/` | AR | 200 |
| 19 | `/privacy/` | IT | 200 |
| 20 | `/disclaimer/` | IT | 200 |
| 21 | `/sitemap.xml` | — | 200 |

### Mobile (390×844 viewport, iPhone-ish)

- `/`, `/countries/`, `/countries/italy/`, `/wizard/`, `/contact/`,
  `/ar/countries/morocco/` (RTL).

Tutte single-column, nessun overflow orizzontale, CTA above-fold visibile.

---

## 2. Problemi trovati

### 2.1 — CTA "Start Italy simulation" non tradotto

**Sintomo.** Su `/`, `/fr/`, `/ar/` la primary CTA dell'hero rendering
mostrava letteralmente "Start Italy simulation →" su tutte le tre
lingue (mai "Avvia simulazione…", "Lancer la simulation Italie", "ابدأ
محاكاة التعويض في إيطاليا").

**Causa.** Mismatch fra `templates/public/home.html` (msgid
`"Start Italy simulation"`) e i file `locale/*/django.po` di pass3
(msgid `"Start Italian compensation simulation"`, già tradotto).

**Fix.** Allineato il template al msgid già tradotto in pass3. Nessun
nuovo msgid aggiunto.

```diff
-{% translate "Start Italy simulation" %}
+{% translate "Start Italian compensation simulation" %}
```

### 2.2 — Nomi paese non tradotti

**Sintomo.** Su `/countries/`, `/fr/countries/`, `/ar/countries/`, e
sulle 5 country landing, le card mostravano `Italy` / `France` /
`Belgium` / `Morocco` / `Tunisia` letterali, anche su FR e AR.
Stessa cosa nella griglia "MVP coverage" della home (5 codici paese
+ etichetta inglese).

**Causa.** `MVP_COUNTRIES.name_key` veniva renderizzato grezzo come
`{{ country.name_key }}` o passato come variabile a
`{% blocktranslate with country=country_name_key %}` senza essere
prima passato attraverso gettext.

**Fix.**

1. `apps/core/views.py:_render_country_landing` ora calcola
   `country_name = _(country_name_key)` e lo aggiunge al contesto
   (`ctx["country_name"]`). L'OG title/description ora
   interpola la versione tradotta.
2. `templates/public/countries.html`, `home.html` (griglia MVP),
   `country_landing.html` (breadcrumb + 5 blocktranslate `with`)
   ora usano la versione tradotta.
3. Aggiunti 5 msgid (`Italy`, `France`, `Belgium`, `Morocco`,
   `Tunisia`) a `locale/{fr,en,ar}/LC_MESSAGES/django.po` con le
   traduzioni native; IT li conteneva già da pass precedenti.
4. `compilemessages` rigenera i `.mo`.

Risultato verificato live:

| Locale | Countries card | Home grid | Breadcrumb landing |
|--------|---------------|-----------|---------------------|
| IT | Italia/Francia/Belgio/Marocco/Tunisia | id. | id. |
| FR | Italie/France/Belgique/Maroc/Tunisie | id. | id. |
| AR | إيطاليا/فرنسا/بلجيكا/المغرب/تونس | id. | id. |

---

## 3. Funnel verificati

Tutti via runserver locale (`http://127.0.0.1:31452`), sessione `requests`.

### 3.1 — Italia 35/10/0 → calcolato, range conservato

```
status=302 → /wizard/result/<uuid>/
26.268,00 / 27.353,00 / 28.439,00 EUR  (= 26 268 / 27 353 / 28 439)
PDF: 200 application/pdf, 6.4 KB, magic = b'%PDF'
Legal-review CTA: /contact/?sim=<uuid>
```

### 3.2 — FR/BE/MA/TN → unavailable, nessun importo

| Path | status | unavail msg | importo? |
|------|--------|-------------|----------|
| `/wizard/fr/road-accident/` | 200 | yes | no |
| `/wizard/be/road-accident/` | 200 | yes | no |
| `/wizard/ma/inheritance/` | 200 | yes | no |
| `/wizard/tn/inheritance/` | 200 | yes | no |

### 3.3 — Contact submit → thank-you IT

```
POST /contact/ con (qa+local@example.test, IT, message Lorem ipsum…)
→ 200 /contact/thank-you/
body include "GRAZIE", "La tua richiesta è stata ricevuta."
```

---

## 4. Fix applicati (riepilogo)

| Area | File | Tipo |
|------|------|------|
| Hero CTA | `templates/public/home.html` | msgid alignment |
| Card paese | `templates/public/countries.html` | wrap `translate` |
| Home grid | `templates/public/home.html` (line 89) | wrap `translate` |
| Breadcrumb + blocktranslate | `templates/public/country_landing.html` | usa `country_name` translated |
| View | `apps/core/views.py:_render_country_landing` | aggiunge `country_name = _(country_name_key)` |
| Catalog | `locale/{fr,en,ar}/LC_MESSAGES/django.po` | +5 msgid country names |
| Catalog binari | `locale/{fr,en,ar}/LC_MESSAGES/django.mo` | rebuilt |
| Tooling | `scripts/add_country_name_translations.py` | helper idempotente |
| Tooling | `scripts/capture_qa_polish_pass1_screenshots.py` | playwright batch |
| Tests | `apps/core/test_public_site_qa_polish_pass1.py` | +48 test |
| Doc | `docs/architecture/PUBLIC_SITE_QA_POLISH_PASS1.md` | questo file |

Nessun altro fix UX significativo applicato in questo pass: hero,
spacing, breadcrumbs, cookie banner, RTL e mobile sono già OK dopo i
pass precedenti.

---

## 5. Screenshot

Tutti in `docs/screenshots/live_qa/public_site_qa_polish_pass1/`.

Desktop (14):

```
01_home_it_desktop.png            08_wizard_start_desktop.png
02_home_fr_desktop.png            09_wizard_italy_form_desktop.png
03_home_ar_desktop.png            10_wizard_fr_road_desktop.png
04_countries_desktop.png          11_wizard_ma_inheritance_desktop.png
05_country_italy_desktop.png      12_methodology_desktop.png
06_country_france_fr_desktop.png  13_contact_desktop.png
07_country_morocco_ar_desktop.png 14_disclaimer_desktop.png
```

Funnel (2):

```
15_italy_result_desktop.png
16_contact_thank_you_desktop.png
```

Mobile (6):

```
m01_home_mobile.png            m04_wizard_mobile.png
m02_countries_mobile.png       m05_contact_mobile.png
m03_country_italy_mobile.png   m06_country_morocco_ar_mobile.png
```

22 PNG, generati da `scripts/capture_qa_polish_pass1_screenshots.py`
(Playwright chromium headless).

---

## 6. Test aggiunti / aggiornati

`apps/core/test_public_site_qa_polish_pass1.py` — 48 test (tutti pass):

| # | Cosa verifica |
|---|---------------|
| 1 | 21 pagine pubbliche → 200 (parametrizzato) |
| 2 | 11 pagine non espongono "Photo by … on Pexels" / "Foto di" / "Crédit photo" / "Photographed by" |
| 3 | 5 pagine non leakkano un valore PEXELS_API_KEY (sentinella in `override_settings`) |
| 4 | `/fr/` ha "Cabinet Légal International" + "Lancer la simulation Italie" |
| 5 | `/ar/` ha ≥3/5 marker arabi pass3 |
| 6 | 4 wizard FR/BE/MA/TN POSTati con consenso non mostrano numeri formato `\d{1,3}[\s.,\xa0]\d{3}\s*EUR` |
| 7 | Italia 35/10/0 a livello engine (fixture seed) → 26 268 / 27 353 / 28 439 |
| 8 | `/sitemap.xml` contiene i 5 path `/countries/<slug>/` |
| 9 | PDF report Italia → 200 `application/pdf` con magic `b'%PDF'` |
| 10 | Contact submit IT default → "grazie" / "ricevuta" su `/contact/thank-you/` |
| 11 | Country names su `/countries/`, `/fr/countries/`, `/ar/countries/` sono tradotti correttamente in IT/FR/AR |

Suite full: **822 pass** (era 774 dopo pass3 → +48 nuovi).

---

## 7. Funnel Italia (numerico)

Engine-level (fixture `italy_smoke_qa_pass1`):

```python
sim = run_simulation(
    jurisdiction_code="IT-NATIONAL",
    case_type="road_accident_bodily_injury",
    input_data={"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0},
)
assert sim.status == "calculated"
assert sim.estimated_min == Decimal("26268")
assert sim.estimated_mid == Decimal("27353")
assert sim.estimated_max == Decimal("28439")
```

Live-server (sessione `requests` → `/wizard/it/road-accident/`):

- min `26.268`, mid `27.353`, max `28.439` EUR (formattazione IT)
- PDF download `/reports/simulation/<uuid>/pdf/` → 200 `application/pdf` 6 KB

Identico ai 3 pass precedenti. Nessuna regressione.

---

## 8. Funnel FR/BE/MA/TN

Tutte le pagine wizard rispondono 200 e POST con consenso non
producono numeri di simulazione visibili. Risposta: "richiede
validazione legale" (IT default) / "validation juridique requise" (FR)
/ "بحاجة إلى تحقق قانوني" (AR).

Nessun calculator attivo: i moduli sono scaffold, e i test #6 ora
guardano la corretta side-effect di non emettere stime numeriche.

---

## 9. Rischi residui

Bassi — nessuno blocca rilascio:

1. **Nomi paese FR vs IT/AR** — la Francia in francese è "France"
   (uguale al sorgente inglese, ma intenzionale). Verificato col
   pattern di traduzione standard (`msgid "France" / msgstr "France"`),
   nessuna divergenza.
2. **Title HTML mixto** — il browser tab title mantiene il prefisso
   "Simulatore Risarcimenti Studio Legale Badrane —" (brand IT)
   anche su FR/AR. Decisione di branding (consistente col
   `og:site_name` e con la home institutionale). Documentato come
   convenzione, non bug.
3. **Cookie banner sovrapposto al content sotto il fold** — già
   noto, gestito dal banner JS che si nasconde dopo "OK". Non
   intercetta CTA above-fold.
4. **Translation pass4 (review giurista nativo)** — AR e fonti
   legali MA/TN non sono ancora state ri-validate da un native
   speaker giurista. È la dipendenza dichiarata nei doc pass3.

---

## 10. Prossimo step consigliato

`F-product-public-site-qa-polish-pass2` (visual + a11y micro-fixes):

- contrasto AA su badge "FONTI LEGALI IN REVISIONE" su sfondi chiari;
- hero image lazy-loading: aggiungere `decoding="async"` esplicito su
  ogni `<img>` Pexels (alcuni mancano);
- meta description su `/wizard/it/road-accident/` è ancora il default
  (genera conflitto leggero con le landing); customizzare per
  case_type;
- `<title>` blocco — eventualmente sostituire l'IT brand prefix con
  un brand neutro multilingua su FR/AR (`Indennizzo · Studio
  Legale Badrane`) — solo se il cliente lo conferma.

Tutti opzionali, nessuno blocca rilascio.

---

## 11. Comandi utili (riepilogo)

```powershell
# Server locale già attivo per QA pass1
http://127.0.0.1:31452/

# Stop runserver
powershell -Command "Stop-Process -Id <PID> -Force"

# Recompile catalog binari (se modifichi .po)
.venv\Scripts\python.exe manage.py compilemessages -l it -l fr -l ar -l en

# Regen screenshot batch (richiede runserver attivo)
.venv\Scripts\python.exe scripts\capture_qa_polish_pass1_screenshots.py --port 31452

# Run i test pass1
.venv\Scripts\python.exe -m pytest apps/core/test_public_site_qa_polish_pass1.py -q

# Validation pipeline completo
.venv\Scripts\python.exe manage.py makemigrations --check
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m black --check .
```
