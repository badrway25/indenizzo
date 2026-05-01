# Premium visual + i18n pass 1

**Iter**: F-product-premium-visual-i18n-pass1
**Data**: 2026-05-01
**Stato**: implementato + testato in locale + verificato live nel browser. **Nessun deploy.**

> Primo passo concreto verso un sito visivamente professionale: hero
> image opzionale su tutto il sito pubblico, polish UX leggero su
> methodology, e prima vera traduzione editoriale di IT/FR/AR.
> Nessun cambio di dati legali o calcoli.

---

## 1. Cosa è cambiato visivamente

- **Hero image partial unificato**:
  `templates/partials/_premium_hero_image.html`. Renderizza `<img>`
  rounded-3xl + shadow-card, niente caption visibile (Pexels
  attribution resta solo nel manifest interno). Se la slot è
  assente, il partial NON renderizza nulla — il template chiamante
  mantiene il fallback.
- **Slot site-wide** integrate in: home, countries index, 5 country
  landing, methodology, wizard start, 5 country wizards, contact.
  Senza manifest il sito resta completamente servibile (fallback
  elegante).
- **Methodology** è passata da text-only a 4 card (2x2), prefisso
  numerato 01/02/03/04, look coerente con home e country landing.
- **Country landing**: layout pass3 mantenuto invariato (è già
  premium).

---

## 2. Slot immagini Pexels (15 slot)

`apps/core/pexels.py::SITE_IMAGE_SLOTS`:

| purpose | country | query |
|---|---|---|
| `home_hero` | — | `elegant law office interior` |
| `countries_index` | — | `international legal documents office` |
| `country_landing` | IT | `Rome courthouse architecture` |
| `country_landing` | FR | `Paris courthouse architecture` |
| `country_landing` | BE | `Brussels courthouse architecture` |
| `country_landing` | MA | `Morocco architecture courthouse` |
| `country_landing` | TN | `Tunis architecture courthouse` |
| `methodology_hero` | — | `legal documents desk premium` |
| `wizard_start_hero` | — | `law office consultation table` |
| `wizard_italy_road_accident_hero` | IT | `Italian courthouse architecture` |
| `wizard_france_road_accident_hero` | FR | `French courthouse architecture` |
| `wizard_belgium_road_accident_hero` | BE | `Belgian courthouse architecture` |
| `wizard_morocco_inheritance_hero` | MA | `Moroccan legal documents` |
| `wizard_tunisia_inheritance_hero` | TN | `Tunisian architecture courthouse` |
| `contact_hero` | — | `law office consultation` |

Tono: istituzionale (architettura, uffici, documenti). Niente
incidenti, ferite, sangue, ambulanze, foto stock generiche.

---

## 3. Come fetchare le immagini

```bash
# anteprima senza chiamate
python manage.py fetch_pexels_site_images --dry-run --all

# set della key (locale, non committata)
export PEXELS_API_KEY="..."

# scarica tutto
python manage.py fetch_pexels_site_images --all

# o solo una slot (per country)
python manage.py fetch_pexels_site_images --country IT --force
```

Senza `PEXELS_API_KEY`: il comando esce con `CommandError`
leggibile, niente file modificato, e il sito **funziona lo stesso**
con i fallback (test `test_pages_render_with_no_pexels_manifest`
verde).

---

## 4. Fetch reale eseguito?

In questa sessione la `PEXELS_API_KEY` non era configurata
nell'ambiente del developer agent: il fetch reale **non è stato
eseguito**. La verifica live è stata fatta in due modalità:

1. **Senza manifest**: tutti gli endpoint pubblici renderizzano
   senza immagini (fallback testuale già premium).
2. **Con manifest seedato a mano** (1×1 PNG mislabeled come JPG,
   solo per dimostrare il flusso WITH-image): hero image render,
   alt corretto, NESSUNA caption visibile, og:image override sul
   file locale.

Per attivare le foto reali, lo Studio deve:
1. ottenere una API key Pexels (gratuita su `pexels.com`);
2. impostarla come env var `PEXELS_API_KEY` (esempio in
   `.env.example`, mai nel repo);
3. eseguire `python manage.py fetch_pexels_site_images --all`.

---

## 5. Stato traduzioni

`makemessages` ha generato `.po` per tutti i 4 paesi
(`locale/{it,fr,en,ar}/LC_MESSAGES/django.po`, ~1819 righe / 597
msgid ciascuno).

Lo script `scripts/populate_translations_pass1.py` ha applicato
una **mappa curata di 55 traduzioni** ad alta visibilità per IT,
FR e AR (EN resta vuota → fallback automatico al `msgid`).

`compilemessages` ha prodotto 4 `django.mo`:
- `locale/it/LC_MESSAGES/django.mo`
- `locale/fr/LC_MESSAGES/django.mo`
- `locale/en/LC_MESSAGES/django.mo`
- `locale/ar/LC_MESSAGES/django.mo`

**Cosa è stato tradotto** (per ognuna di IT/FR/AR):

- nav header (Home, Countries, Case types, Methodology, Privacy,
  Disclaimer);
- footer + CTA "Request legal review";
- hero home (eyebrow, H1, sottotitolo, CTA "Explore case types",
  "Read our methodology", "Trust by design", "Jurisdictions",
  "MVP coverage");
- countries index (Coverage map, Countries we cover, Available,
  Legal sources under review, In preparation, Open country page);
- country landing (Country page, Status, Calculator available,
  Legal basis, How to proceed, Option 1/2, Run the simulation
  wizard, Submit a structured request, Direct legal review,
  approved, needs review, Breadcrumb, country-specific CTAs);
- methodology (How we work, Sources of law, Validation status,
  When a calculation is not available, Ranges/assumptions/
  confidence, draft, deprecated);
- wizard start (Indicative simulation, Start a simulation, Start
  a guided simulation);
- contact (Contact the Studio, Request a legal review, Next step).

**Cosa NON è stato tradotto** (intenzionalmente):
- riferimenti normativi (D.P.R., Mornet, Gazette du Palais,
  Moudawana, Loi 98-97, Tableau Indicatif, Tabelle Tribunale di
  Milano, ecc.) — i nomi ufficiali restano nelle loro lingue
  legali precise;
- bullet text lungo che richiede revisione editoriale dello Studio
  (lasciato in inglese; il test verifica solo che le traduzioni
  ad alta visibilità ci siano).

---

## 6. Cosa richiede review Studio

Le 55 stringhe tradotte sono state scritte da agente, ispirate al
tono "studio legale internazionale, sobrio, professionale", ma:

- **Italiano**: revisione di terminologia legale (es. "intervalli
  trasparenti" vs "fasce trasparenti", "affidabilità progettuale"
  vs altre opzioni) e stile editoriale;
- **Francese**: revisione di terminologia legale francese (es.
  "indemnisation" vs "réparation", "demander une revue
  juridique" vs "solliciter un avis"), conformità con uso forense
  belga/marocchino se rilevante;
- **Arabo**: revisione **prudente** di un madrelingua. La
  traduzione corrente è generale e adatta a un contesto pubblico
  internazionale, ma la terminologia legale specifica
  (compensation/indemnity → تعويض, jurisdiction → اختصاص,
  ecc.) va validata da un avvocato arabofono dello Studio prima
  di qualsiasi promozione esterna.

Il documento `docs/architecture/I18N_TRANSLATION_STATUS.md` è
stato aggiornato con il nuovo stato.

---

## 7. Screenshot before/after

In `docs/screenshots/live_qa/premium_visual_i18n_pass1/`:

**before/** (baseline pre-iter):
- `01_home.png`
- `02_methodology.png`
- `03_wizard_start.png`
- `04_contact.png`

**after/** (post-iter):
- `01_home.png` — IT default, header tradotto, hero "Simulazioni
  indicative su risarcimenti e successioni…", trust card,
  methodology preview "Solo fonti validate / Intervalli
  trasparenti / Revisione umana", CTA banner "Pronto per una
  valutazione legale reale?"
- `02_methodology.png` — IT default, "Metodologia" + 4 card 2x2
  con prefissi numerati 01-04
- `03_fr_countries_france.png` — FR live, nav "Pays/Types de cas/
  Méthodologie", breadcrumb "Accueil/Pays/France", badge "SOURCES
  JURIDIQUES EN COURS DE REVUE", CTA "Demander une revue
  juridique"
- `04_ar_morocco_rtl.png` — AR live, layout flippato RTL, nav
  araba (المنهجية, البلدان, أنواع القضايا), badge "المصادر
  القانونية قيد المراجعة", CTA "اطلب مراجعة قانونية"
- `05_wizard_start.png` — IT default, "Avvia una simulazione
  guidata", FR/BE/MA badge "FONTI LEGALI IN REVISIONE"
- `06_contact.png` — IT default, "CONTATTA LO STUDIO" / "Richiedi
  una valutazione legale"
- `07_countries.png` — IT default, "MAPPA DI COPERTURA" / "I paesi
  che copriamo" / "DISPONIBILE" / "FONTI LEGALI IN REVISIONE" /
  "Apri la pagina paese"
- `08_italy_mobile.png` — viewport 390×844, mobile layout, hero
  immagine seedata (placeholder rosso), breadcrumb "Paesi/Italy",
  "PAGINA PAESE"

---

## 8. Server live lasciato attivo

| Campo | Valore |
|---|---|
| Porta | **51876** |
| URL base | `http://127.0.0.1:51876/` |
| PID | **26856** |
| Comando avvio | `DJANGO_DEBUG=true DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost ./.venv/Scripts/python.exe manage.py runserver 127.0.0.1:51876 --noreload` |
| Stop manuale | PowerShell: `Stop-Process -Id 26856 -Force`; Bash/CMD: `taskkill //F //PID 26856` |

URL principali da aprire per validare visivamente:
- `http://127.0.0.1:51876/` — home IT default
- `http://127.0.0.1:51876/methodology/` — methodology card 2×2
- `http://127.0.0.1:51876/fr/countries/france/` — landing FR tradotta
- `http://127.0.0.1:51876/ar/countries/morocco/` — landing AR RTL
- `http://127.0.0.1:51876/wizard/` — wizard start
- `http://127.0.0.1:51876/contact/` — contact form

---

## 9. Prossimo backlog visuale

- **Pexels fetch reale**: una volta che la API key è disponibile,
  scaricare le 15 slot reali (oggi al posto delle foto vere c'è
  solo il fallback testuale).
- **Conversione SVG → PNG** per `og-country-default` (X non
  supporta SVG nelle Twitter Card image).
- **5 OG image country-specific** (`og-italy.png`,
  `og-france.png`, ecc.) — l'helper accetta già `country_code`.
- **Traduzioni completare**: oggi 55/597 msgid; mancano i bullet
  lunghi descrittivi delle landing e del wizard. Iter dedicato:
  `F-product-i18n-translations-pass2`.
- **Validazione legale dei termini sensibili** (DPR, danni,
  successione, indemnisation, تعويض) da un avvocato Studio per
  ogni lingua.
- **Lighthouse audit** su tutte le 13 pagine principali.
- **Cookie banner restyling**: oggi è poco discreto su mobile,
  copre lo status badge in alcune view.
- **Tailwind PostCSS pipeline** (CDN attuale → produzione).