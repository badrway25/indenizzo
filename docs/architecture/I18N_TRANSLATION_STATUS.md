# I18N translation status

**Iter di riferimento**: F-product-premium-visual-i18n-pass1
**Data**: 2026-05-01
**Stato**: pass 1 implementato — 55 stringhe ad alta visibilità tradotte in IT/FR/AR.

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