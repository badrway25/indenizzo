# I18N translation status

**Iter di riferimento**: F-product-i18n-translations-pass3-visible-copy
**Data**: 2026-05-01
**Stato**: pass 3 implementato — **282 stringhe** (138 pass1+pass2 + **144 pass3 visibili sul body**) tradotte in IT/FR/AR.

> **Update pass 3** (2026-05-01): aggiunte 144 traduzioni visibili
> per ognuna delle 3 lingue IT/FR/AR (totale 432 msgstr riempiti).
> Coperte:
> - footer disclaimer / cookies / "Visit institutional website";
> - 9 case-type label (Road accident, Medical malpractice, …);
> - tutti i form field di contact (First name, Last name, Phone,
>   Country, Case type, How can we help, Send my request, ecc.);
> - tutti i form field del wizard (Date of accident, Age, Permanent
>   disability, Medical expenses, Lost income, Estimated own fault,
>   inheritance fields, ecc.);
> - intro country wizard (Italy/France/Belgium/Morocco/Tunisia
>   road-accident e inheritance scaffold);
> - simulation result UI (Min/Mid/Max, Warnings, Missing documents,
>   Open official source, Internal status code, Run simulation);
> - privacy/disclaimer/rate-limit pagine ufficiali.
> 
> File `.mo` ricompilati. Server live verificato in chromium
> headless: `/fr/contact/`, `/ar/contact/`, `/fr/wizard/`,
> `/ar/wizard/`, `/fr/`, `/ar/` mostrano traduzioni reali e nessun
> "Apply"/"First name"/"Send my request" inglese visibile sul body
> principale.

> **Update pass 2** (precedente): **138 stringhe** (55 pass1 + 37
> pass2A long-form + 46 pass2B labels) tradotte in IT/FR/AR.

> **Update pass 1**: le `.po` sono ora **popolate** per le 55
> stringhe più visibili (header, footer, hero CTA, status badge,
> nav country pages, methodology, wizard start, contact) e
> compilate in `.mo`. Il sito mostra traduzioni reali su `/fr/`,
> `/it/` (default) e `/ar/`. Resta da tradurre il copy lungo
> descrittivo (~542 msgid) — iter dedicato:
> `F-product-i18n-translations-pass2`.

> Il sito ha l'**infrastruttura** i18n in piedi (routing, lang, dir,
> stringhe taggate), ma il **contenuto** non è ancora tradotto.
> Fino a quando i `.po` non saranno completati e compilati in `.mo`,
> visitando `/fr/`, `/en/`, `/ar/` si vedono path corretti ma testo
> in inglese.

---

## 1. Cosa funziona oggi

- **Routing i18n**: `i18n_patterns(prefix_default_language=False)` in
  `config/urls.py`. La lingua default `it` non ha prefisso URL; le
  altre lingue hanno prefisso `/<lang>/`. URL come
  `/fr/countries/france/` o `/ar/countries/morocco/` ritornano 200
  e attivano la traduzione di Django per quella lingua.
- **`<html lang>` + `dir=rtl`**: il base template
  (`templates/base.html`) imposta `<html lang="{{ CURRENT_LANGUAGE }}"
  dir="{% if IS_RTL %}rtl{% else %}ltr{% endif %}">`. Per `/ar/...`
  l'intero layout si flippa a RTL — verificato live nel browser
  pass dopo pass.
- **Language switcher**: il header partial mostra il dropdown
  `IT — Italiano / FR — Français / EN — English / AR — العربية` e
  il path commuta correttamente (verificato negli screenshot
  pass 3/4/pexels).
- **Stringhe taggate**: i template usano `{% translate %}` /
  `{% blocktranslate %}` per il copy delle landing, header, footer,
  case-types, methodology, privacy, disclaimer, wizard, ecc. Le
  view passano dati country-specific via context.
- **`og:locale` + alternates** (pass 4): il social scraper riceve
  `og:locale="it_IT"` (lingua corrente) + `og:locale:alternate` per
  le altre.
- **Hreflang `<link>`** (pass 2): le 5 country landing dichiarano
  `<link rel="alternate" hreflang="it|fr|en|ar|x-default">` con
  URL i18n-prefixed corretti.

## 2. Cosa NON funziona ancora

- **Le traduzioni `.po` non sono state completate**: il file
  `locale/<lang>/LC_MESSAGES/django.po` esiste come scheletro per
  ciascuna lingua, ma le stringhe sono in larga parte non tradotte.
- **`compilemessages` non è in pipeline**: anche dove qualche
  traduzione è presente nel `.po`, manca il `.mo` compilato che
  Django carica a runtime. Risultato: `gettext()` ritorna la
  stringa source (inglese) anche su `/fr/` o `/ar/`.
- **Conseguenza visibile**: visitando `/fr/countries/france/` la
  pagina è strutturalmente corretta (URL, dir, hreflang) ma il
  testo del body resta in inglese ("France — what we currently
  cover", "Status", "How to proceed", ecc.).
- **Nessun fallback "smart"**: niente integrazione DeepL/Google
  Translate. Le traduzioni saranno scritte a mano e validate.

## 3. Lingue supportate (settings)

```python
LANGUAGES = [
    ("it", "Italiano"),
    ("fr", "Français"),
    ("en", "English"),
    ("ar", "العربية"),
]
LANGUAGE_CODE = "it"  # default, no URL prefix
```

`it` è la lingua default per scelta strategica: il sito principale
dello Studio è in italiano, e il prodotto è una piattaforma legale
italiana che si espande all'estero.

## 4. Perché non traduciamo "automaticamente"

Le traduzioni di una piattaforma legale **devono essere validate da
un avvocato qualificato** nella giurisdizione di destinazione:

- termini come "danno biologico", "préjudice corporel", "préjudice
  d'agrément", "diya", "Moudawana", "successioni internazionali"
  non hanno traduzioni 1-a-1 universali;
- usare una traduzione automatica genericamente accettabile può
  produrre claim legalmente fuorvianti (es. tradurre "indicative
  range" come "range certain" in francese);
- il tono dello Studio è autorevole, non assicurativo / non
  casinò: Google Translate tende a scegliere registri non
  professionali.

Per questo motivo le `.po` saranno popolate manualmente e validate
in revisione legale — esattamente come le tabelle / formule
`approved` per il calcolatore.

## 5. Prossimo step — F-product-i18n-translations-pass1

Iter dedicato che farà:

1. `manage.py makemessages -l it -l fr -l en -l ar` per generare
   `.po` aggiornati (cattura le stringhe correntemente taggate);
2. **Traduzione manuale** delle landing 5-paesi + header/footer +
   wizard CTA + disclaimer + privacy/methodology in `it/fr/en`;
3. **Arabo (RTL)**: tipografia + traduzione, pass dedicato per
   verificare layout RTL (numeri, punteggiatura, allineamenti);
4. **Validazione legale interna** dello Studio sulle stringhe
   sensibili (case types, danni, claim);
5. `compilemessages` in CI + dev workflow;
6. Test che verifichino che `/fr/` mostri stringhe FR, `/en/`
   stringhe EN, `/ar/` stringhe AR (non più fallback inglese).

Da quel momento, gli `og:title`/`og:description` (già gettext-
powered da pass 4) si tradurranno automaticamente coerentemente
con il body, perché il view usa le stesse chiavi del template.

## 6. Note operative

- I `.po` template restano nel repo (gli `.mo` no — sono build
  artifact; aggiungerli a `.gitignore` quando la pipeline sarà
  pronta).
- Le traduzioni di paesi-specifici (es. nomi di leggi citati in
  Legal basis) **non vanno tradotte**: "D.P.R. 13 gennaio 2025, n.
  12 — Tabella Unica Nazionale art. 138 CAP" deve restare nel suo
  italiano legalmente preciso anche sulla versione `/fr/` o `/en/`.
  Il pass di traduzione tradurrà solo il copy editoriale (titoli,
  descrizioni, CTA), non i riferimenti normativi.
- Per Pexels (immagini), nessun problema i18n: non c'è copy
  visibile sopra/sotto le foto (vedi pass corrente).

---

## 7. Pass 3 — dettaglio (F-product-i18n-translations-pass3-visible-copy)

### 7.1 Numeri

| Lingua | msgid totali | msgstr riempiti pass3 | msgstr ancora vuoti |
|---|---:|---:|---:|
| IT | 597 | +144 (= 282 totali) | 316 |
| FR | 597 | +144 (= 282 totali) | 316 |
| AR | 597 | +144 (= 282 totali) | 316 |

I 316 msgstr residui per lingua sono **non visibili a utente
finale**: sono label admin/backend (nomi modello in lowercase,
verbose-plural ORM, help_text amministratore, choices interne di
admin-action, ecc.). Verranno tradotti solo se/quando lo Studio
attiverà l'admin in lingue diverse dall'italiano.

### 7.2 Cosa è stato tradotto in questo iter

Categorie ad alta visibilità (vedi `scripts/apply_translations_pass3.py`):

- **Header/footer/disclaimer**: "This platform provides indicative
  simulations only…", "This site uses only strictly necessary
  cookies…", "Visit institutional website", "Studio Legale
  Internazionale", "Cookie notice", "Legal disclaimer", "OK",
  "Primary navigation", "Apply".
- **Hero CTA**: "Start Italian compensation simulation",
  "%(site)s — International compensation simulator".
- **Case types** (9 label): Road accident, Medical malpractice,
  Work injury, Death compensation, Parental loss, Patrimonial
  damage, Inheritance basic/international, Generic legal assessment.
- **Status / confidence**: Unavailable — requires legal validation,
  Insufficient input, Calculated, Error, Low/Medium/High.
- **Wizard CTA**: Start this simulation, Open scaffold wizard,
  "Each module is activated only after…", "A simulation is not
  legal advice…", description bodily-injury / scaffold-review.
- **Contact form**: Website (do not fill), First name, Last name,
  Email, Phone number, Preferred language, Country, Select a
  country, Case type, Not specified, How can we help?, helptext
  ("Briefly describe…"), consent checkbox label con link a
  /privacy /disclaimer, Submitting this form does not create…,
  Send my request, Request received, Thank you, validators.
- **Wizard form (Italy bodily injury)**: Date of accident, Age,
  Permanent disability %, Total / partial temporary disability,
  Medical expenses, Lost income, Estimated own fault, consent
  checkbox + validators.
- **Wizard form (inheritance)**: Country of last domicile, Habitual
  residence, Nationality, Will, Surviving spouse, Children, Parents,
  Countries with assets, Additional context.
- **Country wizard intros** (FR/BE/MA/TN scaffold): "Module under
  legal validation", "All fields below are optional…", "This
  module is a scaffold…" per ciascuno dei 4 paesi sotto revisione.
- **Result UI**: Min/Mid/Max, Warnings, Missing documents, Open
  official source, Internal status code, "This simulation is
  indicative…", Run simulation, fallback "Economic estimate not
  available…".
- **Privacy / disclaimer / rate-limit**: Personal data, Too many
  requests, Rate limit, "We process personal data in accordance
  with the EU GDPR…", "We do not sell personal data…", "You can
  request access, rectification, deletion…", "If you require a
  binding evaluation…", "This text is a working version. The final
  wording will be reviewed and signed off by the Studio's legal
  team."

### 7.3 Cosa resta (NON in scope di pass3)

1. **Admin label backend** (~316 msgid per lingua): nomi modello,
   help_text admin, action labels, ORM verbose names. Solo lo Studio
   userà l'admin, oggi in italiano. Da tradurre solo se in futuro
   l'admin sarà condiviso con avvocati FR/AR.
2. **Stringhe template-side ancora intrinseche al codice**: alcuni
   template injettano testo non `gettext`-wrapped (es. logo
   "Studio Legale Internazionale Badrane" hard-coded — già
   intenzionale per brand consistency). Questo non è un bug.
3. **EN translations**: il file `locale/en/LC_MESSAGES/django.po`
   resta non tradotto (i msgid stessi sono in inglese). Quindi
   `/en/` mostra il source. Coerente con design.

### 7.4 Termini che richiedono revisione Studio / madrelingua

**Francese — revisione avvocato FR**:
- "Préjudice corporel" vs "dommage corporel": uniformati a
  "préjudice corporel" (più tecnico-giuridico). Validare con
  avvocato FR.
- "Concorso di colpa" → "Part de responsabilité personnelle":
  termine assicurativo standard FR ma può variare per regione
  (Belgique ha "concours de fautes"). Per Belgio considerare
  variante.
- "Incarico professionale" → "Mandat professionnel": terminologia
  ordine-degli-avvocati FR. OK.

**Arabo — revisione madrelingua + giurista MA/TN**:
- **Rischio elevato**: termini legali arabi non hanno traduzione
  univoca cross-paese. Es.:
  - "Inheritance — international" → "ميراث — دولي" (universale, OK)
  - "Bodily injury" → "أضرار جسدية" (modern standard arabic, neutro
    geograficamente)
  - "Liability" → tradotto come "مسؤولية" in più punti, ma in
    diritto MA/TN spesso si trova "تبعة" o "مسؤولية مدنية".
- **Verbose vs concise**: il copy AR generato è in MSA letterario
  (es. "تقدّم هذه المنصة محاكاة إرشادية فقط"). Un native MA/TN
  potrebbe preferire forme più colloquiali. Da validare con
  Studio.
- **Codice di famiglia / Moudawana**: lasciato sempre come
  "Moudawana" o tra parentesi accanto al termine arabo, perché è
  il nome legale ufficiale del Code de la famille marocchino.
  Non tradotto come "مدوّنة الأسرة" da solo per coerenza con
  citazioni FR già presenti nei country wizard.

**Italiano**:
- "Incarico professionale" / "mandato professionale": entrambi
  validi. Scelto "incarico" (più colloquiale, in linea con
  comunicazione cliente). Da validare.
- "Concorso di colpa" → standard giuridico italiano. OK.

### 7.5 Verifica live

Server `manage.py runserver --noreload` attivo durante tutto il
pass su `http://127.0.0.1:31448/`. 8 screenshot full-page salvati
in `docs/screenshots/live_qa/i18n_translations_pass3/` (FR home,
FR France landing, FR wizard, FR contact, AR home RTL, AR Morocco
RTL, AR wizard RTL, AR contact RTL).

### 7.6 Test

`apps/core/test_i18n_translations_pass3.py` (14 test):
1. `/fr/` ha ≥10 marker FR pass3 (real-content).
2. `/fr/countries/france/` non contiene "Visit institutional website",
   "Send my request", "First name" (regression-guard).
3. `/ar/` ha ≥8 marker AR pass3 reali.
4. `/ar/countries/morocco/` ha `dir="rtl"` + ≥5 marker AR + parola
   "محاكاة إرشادية".
5. `/en/` resta inglese (no contamination FR/AR).
6. Nomi fonti legali (Mornet, Moudawana, Loi Badinter, D.P.R.,
   Tableau, Reg. UE 650/2012) preservati su 5 path.
7. Italia smoke 35/10/0 → 26 268 / 27 353 / 28 439 EUR invariato.
8. `.mo` esistono e > 30 KB per IT/FR/AR.