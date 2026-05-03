# Public site QA polish — pass 2 (F-product-public-site-qa-polish-pass2-a11y-seo)

Stato: completato 2026-05-03.

Micro-fix professionali su accessibilità, performance immagini e SEO base
sopra la baseline di pass 1. **Niente** dati legali, engine o funzionalità
toccati. Italia 35/10/0 invariato a 26 268 / 27 353 / 28 439 EUR.
FR/BE/MA/TN restano under legal review.

---

## 1. Riepilogo fix

| Area | Tipo | File |
|------|------|------|
| a11y | Token Tailwind: `gold-700` (#6e4d18) per testo badge contrastato | `templates/base.html` |
| a11y | Focus ring esteso a `input`/`select`/`textarea`/`role=button`/`summary` | `templates/base.html` |
| a11y | `prefers-reduced-motion` honoured (animation/transition fast-forward) | `templates/base.html` |
| a11y | Badge "Legal sources under review": da `bg-gold-500/10 text-gold-600` a `bg-gold-500/15 text-gold-700` | `countries.html`, `country_landing.html`, `case_types.html`, `wizard_start.html` |
| a11y | Badge "In preparation": testo `text-stone2-500` → `text-ink-800` | `countries.html`, `case_types.html`, `wizard_start.html` |
| a11y | Language switcher visibile anche su mobile (era `hidden sm:block`) + `aria-label` sul `<form>` + `min-h` 40px sul select | `partials/language_switcher.html` |
| perf | `width`/`height` espliciti su tutte le `<img>` Pexels per evitare CLS | `home.html`, `country_landing.html`, `countries.html`, `partials/_premium_hero_image.html` |
| seo  | `<meta name="description">` override per wizard start, methodology, contact, countries, case_types e i 5 wizard | 9 template (vedi §4) |
| seo  | Title affilati su `wizard/`, `countries/`, `case_types/`, `methodology/`, `contact/` | come sopra |
| test | 62 nuovi test in `apps/core/test_public_site_qa_polish_pass2.py` | nuovi |
| tooling | `scripts/capture_qa_polish_pass2_screenshots.py` (Playwright batch) | nuovo |

---

## 2. Accessibilità

### 2.1 — Contrasto badge "Legal sources under review"

Pre-pass2 la chip su sfondo bianco / sand-50 usava
`bg-gold-500/10 text-gold-600` ⇒ contrasto AA borderline su small text
uppercase tracking-tight.

Fix: introdotto un token `gold-700: #6e4d18` (più scuro di `gold-600`)
nella config Tailwind `base.html` e usato in coppia con un tint di
sfondo leggermente più saturo `gold-500/15`. La nuova combinazione
`bg-gold-500/15 text-gold-700` su white-card supera abbondantemente
4.5:1 per small text.

### 2.2 — Contrasto badge "In preparation"

`bg-stone2-100 text-stone2-500` (#ecebe7 / #7a786f) era ~3.4:1 → sotto
soglia AA per small text. Sostituito con `text-ink-800` (#172e62) che
porta il contrasto sopra 9:1.

### 2.3 — Focus ring più completo

`base.html` estende il selettore `:focus-visible` a `input`, `select`,
`textarea`, `[role="button"]` e `summary` (oltre ad `a` e `button` già
coperti in pass 1). Outline 2px gold + offset 3px, identico al resto
del sito.

### 2.4 — Reduced motion

Aggiunta media query `prefers-reduced-motion: reduce` che disattiva
`scroll-behavior: smooth` e abbassa animation/transition durations a
0.01ms. Ridotto rischio di motion sickness senza spegnere
intenzionalità visiva per chi non ha la preferenza attiva.

### 2.5 — Language switcher su mobile

Pre-pass2 il `<form>` aveva `class="hidden sm:block"`: gli utenti
mobile non potevano cambiare lingua dall'header. Rimosso `hidden`,
aggiunto `aria-label="Language switcher"` sul `<form>` e
`min-h-[40px]` sul `<select>` per touch target. Lo `<label>` interno
resta `sr-only`, invariato.

### 2.6 — Heading order verificato

Test `test_single_h1_per_principal_page` parametrizzato sulle 11
pagine principali ⇒ esattamente UN `<h1>` per pagina (no doppi, no
zero). H2/H3 sono già in ordine semantico nei template esistenti, non
modificati.

---

## 3. Performance immagini

Tutti gli `<img>` Pexels sono già renderizzati da `/media/pexels/…`
(test pass1 #2 + pass2 #2 lo verificano).

Aggiunto `width`/`height` espliciti per ridurre CLS:

| File | Sizing |
|------|--------|
| `home.html` (hero image-as-backdrop, eager + fetchpriority=high) | `width=1920 height=1080` |
| `country_landing.html` (hero figure) | `width=1280 height=640` |
| `countries.html` (card image) | `width=800 height=450` |
| `partials/_premium_hero_image.html` | `width=1280 height=640` |

`decoding="async"` era già presente; `loading="lazy"` su tutte le hero
non above-fold; `loading="eager" + fetchpriority="high"` sull'unica
above-fold (home backdrop). Test
`test_hero_images_have_decoding_async` lo verifica live.

---

## 4. SEO micro-fix

Ogni pagina ora ha una `<meta name="description">` esplicita,
distinta dal default ereditato da `base.html`:

| Path | Title | Meta description (estratto) |
|------|-------|------------------------------|
| `/wizard/` | "Start a guided simulation — …" | "Pick a country and a case type. Indicative simulations are produced only when validated…" |
| `/wizard/it/road-accident/` | "Italy — road accident bodily injury — …" | "…approved TUN 2025 dataset (D.P.R. 12/2025)…" |
| `/wizard/fr/road-accident/` | (invariato) | "…Loi Badinter, Référentiel Mornet, capitalisation tables…" |
| `/wizard/be/road-accident/` | (invariato) | "…Tableau Indicatif, Tables Schryvers…" |
| `/wizard/ma/inheritance/` | (invariato) | "…Moudawana, EU Regulation 650/2012…" |
| `/wizard/tn/inheritance/` | (invariato) | "…Code du statut personnel, EU Regulation 650/2012…" |
| `/methodology/` | "Methodology — sources, validation and ranges — …" | "How we work: source-of-law catalogue, controlled validation lifecycle…" |
| `/contact/` | "Request a legal review — …" | "Tell us about your case in your own words…" |
| `/countries/` | "Countries we cover — …" | "MVP coverage map for the Badrane simulator…" |
| `/case_types/` | "Case types we cover — …" | "Modular taxonomy of case types: each module is activated only when…" |

`noindex, nofollow` resta su `/contact/` e sui 5 wizard come da pass
precedenti (sono pagine private/transazionali). `/sitemap.xml`
invariato e include sempre i 5 country landing.

`canonical` + `hreflang` sui 5 country landing **non** sono stati
toccati: pass2 si limita a verificarli con un nuovo test
parametrizzato.

---

## 5. Funnel verificati

Live runserver: `http://127.0.0.1:31452/` (porta sempre identica a
pass1 per consistenza handover).

Pytest engine-level (`test_italy_smoke_engine_preserves_pass2_contract`):

```
status=calculated, min=26268.00 mid=27353.00 max=28439.00
```

Identico al contratto storico — nessuna regressione introdotta da
pass2.

FR/BE/MA/TN restano `unavailable_requires_legal_validation`. Nessun
nuovo importo numerico esposto.

---

## 6. Test aggiunti

`apps/core/test_public_site_qa_polish_pass2.py` — 62 test (tutti pass):

| # | Cosa verifica |
|---|---------------|
| 1 | 11 pagine principali → esattamente UN `<h1>` (parametrizzato) |
| 2 | 11 pagine non leakkano URL Pexels remoti (`images.pexels.com` o `www.pexels.com/*.jpg`) |
| 3 | 5 hero target (`/`, `/countries/italy/`, `/fr/countries/france/`, `/wizard/`, `/wizard/it/road-accident/`) hanno `decoding="async"` se renderizzano `/media/pexels/` |
| 4 | 5 country landing hanno `<link rel="canonical">` + ≥2 `<link rel="alternate" hreflang="…">` |
| 5 | `/sitemap.xml` 200 e contiene i 5 path `/countries/<slug>/` |
| 6 | Re-check pass1: nessuna attribution Pexels visibile sulle 11 pagine principali |
| 7 | Re-check pass1: `PEXELS_API_KEY` sentinella non leakka mai in HTML |
| 8 | Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR (engine fixture pass2) |
| 9 | `<meta name="description">` overridden con stringa attesa su 9 path (wizard / wizard IT/FR/BE/MA/TN / methodology / contact / countries) |
| 10 | Marker pass2 `text-gold-700` presente su `/countries/france/` |
| 11 | Combo fragile `bg-gold-500/10 text-gold-600` rimossa da `/countries/` |

Suite full: **884 pass** (era 822 dopo pass1 → +62 nuovi).

---

## 7. Screenshot

Tutti in `docs/screenshots/live_qa/public_site_qa_polish_pass2/`.

Desktop (9):

```
01_home_it_desktop.png            06_wizard_start_desktop.png
02_countries_desktop.png          07_contact_desktop.png
03_country_france_fr_desktop.png  08_methodology_desktop.png
04_country_morocco_ar_desktop.png 09_country_italy_desktop.png
05_wizard_it_form_desktop.png
```

Mobile (5):

```
m01_country_italy_mobile.png       m04_country_morocco_ar_mobile.png
m02_home_mobile.png                m05_wizard_it_form_mobile.png
m03_countries_mobile.png
```

Generati da `scripts/capture_qa_polish_pass2_screenshots.py`
(Playwright chromium headless, 1280×900 desktop / 390×844 mobile).

---

## 8. Validazione

Pipeline completa eseguita 2026-05-03:

```
python manage.py makemigrations --check  → No changes detected
python manage.py check                   → System check identified no issues
python manage.py compilemessages         → already compiled and up to date (it/fr/en/ar)
pytest -q                                → 884 passed in 52.80s
ruff check .                             → All checks passed!
black --check .                          → 217 files would be left unchanged
```

Server live attivo: `http://127.0.0.1:31452/` (PID **3784**).

---

## 9. Rischi residui (basso, non-bloccanti)

1. **CDN Tailwind in dev** — runtime JIT non ottimale. Pre-deploy
   resta da migrare a build PostCSS (già nei NO-GO production).
2. **Translation pass su wizard FR/BE/MA/TN** — i nuovi msgid di
   `meta_description` non sono ancora presenti nei file `.po`. Per
   ora il fallback gettext restituisce la stringa English originale.
   Prossimo pass i18n includerà queste 9 stringhe.
3. **Title prefix brand** — il browser tab title resta IT-branded
   anche su FR/AR. Decisione di branding documentata in pass1 §9.
4. **A11y audit automatizzato (Axe/Lighthouse)** — non eseguito in
   questo pass. I micro-fix sono mirati su problemi noti; un audit
   completo è il prossimo step.

---

## 10. Prossimo step consigliato

`F-product-public-site-qa-polish-pass3-a11y-audit` (audit completo):

- Axe-core run automatizzato sulle 11 pagine principali, capture
  delle violazioni residue;
- Lighthouse mobile + desktop sui 4 funnel (home, countries, wizard,
  contact) → target Performance ≥ 90, A11y ≥ 95;
- aggiunta dei msgid `meta_description` nei `.po` it/fr/en/ar;
- review screen-reader manuale (NVDA / VoiceOver) sui 3 funnel
  critici (Italy wizard submit, contact submit, language switch).

Tutti opzionali: il sito resta release-ready dopo pass2.

---

## 11. Comandi utili

```powershell
# Server locale attivo per QA pass2 (porta riusata da pass1)
http://127.0.0.1:31452/

# Stop runserver
powershell -Command "Stop-Process -Id 3784 -Force"

# Run i test pass2
.venv\Scripts\python.exe -m pytest apps/core/test_public_site_qa_polish_pass2.py -q

# Regen screenshot batch (richiede runserver attivo)
.venv\Scripts\python.exe scripts\capture_qa_polish_pass2_screenshots.py --port 31452

# Validation pipeline completo
.venv\Scripts\python.exe manage.py makemigrations --check
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m black --check .
```
