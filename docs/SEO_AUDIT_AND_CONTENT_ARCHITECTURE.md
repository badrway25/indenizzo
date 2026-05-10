# SEO AUDIT & CONTENT ARCHITECTURE — Indennizzati / Studio Legale Badrane

**Data:** 2026-05-10
**Audience:** dev, content/SEO consulente, futuri Claude Code.
**Scopo:** mappare lo stato SEO tecnico ed editoriale, e definire una
**strategia di content architecture multi-paese × multi-case-type ×
multi-lingua** scalabile, senza duplicare ciò che già esiste in
`docs/architecture/PRODUCT_COUNTRY_LANDING_SEO.md` (4 pass molto
dettagliati: sitemap, canonical, hreflang, JSON-LD, OG/Twitter cards).

> Questo documento integra `PRODUCT_COUNTRY_LANDING_SEO.md` (che è
> autorevole sulle country landing) con la **strategia di crescita
> editoriale** e i **gap SEO tecnici** non ancora coperti.

---

## 0. Cosa è già coperto altrove (NON ripetuto qui)

Vedi `docs/architecture/PRODUCT_COUNTRY_LANDING_SEO.md` per:

- ✅ 5 country landing (`/countries/{italy,france,belgium,morocco,tunisia}/`)
- ✅ `<link rel="canonical">` self-reference (pass 2)
- ✅ `<link rel="alternate" hreflang="it/fr/en/ar/x-default">` (pass 2)
- ✅ `/sitemap.xml` con 12 URL (`CountryLandingSitemap` + `StaticSitemap`, pass 3)
- ✅ JSON-LD `LegalService` su 5 country landing (pass 3)
- ✅ OG / Twitter Card metadata (pass 4)
- ✅ `og:locale` + `og:locale:alternate` (pass 4)
- ✅ OG image PNG 1200×630 per paese + default (pass og-images-pass1)
- ✅ Test SEO automatizzati (122 totali per le country landings)

Stato test SEO complessivo: **buono** sulle country landing, **molto
parziale** sul resto.

---

## 1. Inventario SEO attuale

### 1.1 URL pubblici e copertura SEO

Routing prodotto da `config/urls.py` + `apps.core.urls` + `apps.cases.urls`
+ `apps.crm.urls`:

| URL pattern | Canonical/hreflang | OG/Twitter | JSON-LD | In sitemap | Robots |
|---|---|---|---|---|---|
| `/it/` (`core:home`) | ❌ | ❌ | ❌ | ✅ pri 0.8 | index |
| `/it/methodology/` | ❌ | ❌ | ❌ | ✅ pri 0.6 | index |
| `/it/disclaimer/` | ❌ | ❌ | ❌ | ✅ pri 0.3 | index |
| `/it/privacy/` | ❌ | ❌ | ❌ | ✅ pri 0.3 | index |
| `/it/countries/` | ❌ | ❌ | ❌ | ✅ pri 0.8 | index |
| `/it/countries/italy/`, `france/`, `belgium/`, `morocco/`, `tunisia/` | ✅ | ✅ | ✅ `LegalService` | ✅ pri 0.9 | index |
| `/it/case-types/` | ❌ | ❌ | ❌ | ✅ pri 0.6 | index |
| `/it/wizard/` | ❌ | ❌ | ❌ | ✅ pri 0.6 | index |
| `/it/wizard/it/road-accident/` etc. (5 wizard) | ❌ | ❌ | ❌ | ❌ | index (default) |
| `/it/wizard/result/<uuid>/` | ❌ | ❌ | ❌ | ❌ | **dovrebbe essere `noindex`** |
| `/it/contact/` | ❌ | ❌ | ❌ | ❌ | ✅ noindex,nofollow |
| `/it/contact/thank-you/` | ❌ | ❌ | ❌ | ❌ | (default index — **dovrebbe essere `noindex`**) |
| `/reports/simulation/<uuid>/pdf/` | n/a | n/a | n/a | ❌ | (default — irrilevante per crawl) |

### 1.2 Componenti SEO presenti

| Componente | Posizione | Stato |
|---|---|---|
| `<title>` block | `templates/base.html:6` con default + override per pagina | ✅ |
| `<meta name="description">` | `base.html:7` con default + override | ✅ |
| `<meta name="robots">` | `base.html:8` con default `index, follow` | ✅ |
| `<html lang="…" dir="…">` | `base.html:2` derivato da `CURRENT_LANGUAGE` + `IS_RTL` | ✅ |
| Skip-link a11y | `base.html:50-52` | ✅ |
| `prefers-reduced-motion` honor | `base.html:36-44` | ✅ |
| Focus ring uniforme | `base.html:29-35` | ✅ |
| Header / footer / disclaimer banner / cookie banner | partial in `templates/partials/` | ✅ |
| Open Graph / Twitter | solo country landing | 🟡 parziale |
| Sitemap | `apps/core/sitemaps.py` | ✅ ma solo 12 URL |
| `robots.txt` | **assente** | ❌ |
| `humans.txt` | assente | n/a |
| Lighthouse baseline + gating CI | non in CI; `run_public_lighthouse_audit.py` esiste | 🟡 |
| Performance budget | non definito | ❌ |
| Google Search Console / Bing Webmaster Tools | non collegati | ❌ |

### 1.3 Performance — Core Web Vitals

Stato Lighthouse (da `docs/reports/lighthouse/release_readiness_audit_pass1/summary.md`
e simili pass): every page passes a11y / SEO / structural fallback rules.

Aree di miglioramento note:

- Google Fonts esterni (vedi `LEGAL_COMPLIANCE_CONTENT_AUDIT.md`
  Sez. 4) → impatto LCP + privacy;
- Tailwind CDN era stato un tempo attivo, ora rimosso (vedi
  `REMOVE_TAILWIND_CDN_PASS2.md`); CSS è locale `static/css/site.css`;
- Pexels images cached server-side (ok);
- nessun bundling JavaScript significativo (sito è quasi-static
  HTMX-friendly).

---

## 2. Gap SEO tecnici (P0/P1)

### 2.1 P0-SEO-1: `robots.txt` assente

Stato: nessun file `robots.txt` servito (verificato: `find` su `**/robots.txt` → 0 match).

Senza `robots.txt`, i crawler accedono a tutto inclusi `/admin/`,
endpoint potenzialmente sensibili.

**Azione**:

1. creare `apps.core.views.robots_txt` che ritorna il testo statico:

```
User-agent: *
Disallow: /admin/
Disallow: /staff/
Disallow: /wizard/result/
Disallow: /reports/
Disallow: /contact/
Disallow: /contact/thank-you/

Sitemap: https://simulatore.studiolegalebadrane.it/sitemap.xml
```

2. registrare in `config/urls.py` fuori da `i18n_patterns`:

```python
path("robots.txt", robots_txt, name="robots_txt"),
```

3. test: `apps/core/test_robots.py` — verifica 200, content-type
   text/plain, presenza Disallow critici.

### 2.2 P0-SEO-2: `noindex` mancante su result e thank-you

`/wizard/result/<uuid>/` e `/contact/thank-you/` non hanno
`<meta name="robots" content="noindex,nofollow">`.

`/contact/` invece ce l'ha (`templates/public/contact.html` l. 5):
```django
{% block meta_robots %}noindex, nofollow{% endblock %}
```

**Azione**: aggiungere lo stesso block in
`templates/public/wizard_result.html` e
`templates/public/contact_thank_you.html`. Result page contiene
input personali del visitatore: deve essere `noindex,nofollow`.

### 2.3 P0-SEO-3: hreflang esteso a tutte le pagine pubbliche

Oggi solo le 5 country landing hanno `<link rel="alternate" hreflang>`.
Home, methodology, privacy, disclaimer, countries index, case-types,
wizard hub **non hanno** alternate links.

Conseguenza: Google non sa che `/it/` e `/fr/` sono versioni
linguistiche dello stesso contenuto.

**Azione**:

1. estendere `apps.core.seo.build_hreflang_alternates()` per accettare
   un `view_name` qualunque (oggi è già parametrico, vedi
   `PRODUCT_COUNTRY_LANDING_SEO.md` §9-bis);
2. context processor o template tag che inietti automaticamente
   alternate links nel `head_extra` di ogni template che extends
   `base.html`;
3. test in `apps/core/test_seo_hreflang_global.py`.

### 2.4 P1-SEO-1: sitemap espansa

La sitemap attuale ha 12 URL nella sola lingua default. Per essere
SEO-complete dovrebbe avere:

- 12 URL × 4 lingue = **48 entry**, oppure
- usare `<xhtml:link rel="alternate" hreflang>` *dentro la sitemap*
  (sitemap multi-lingua, vedi
  https://developers.google.com/search/docs/specialty/international/localized-versions).

Oggi siamo nel caso *"hreflang in HTML head"*, che è valido ma meno
robusto se le pagine non sono crawlate spesso. Pattern raccomandato:
**combinare entrambi**.

**Azione**:

1. estendere `CountryLandingSitemap` e `StaticSitemap` per emettere
   `<url>` con `<xhtml:link>` per ogni lingua;
2. Django `sitemaps` framework supporta questo via override
   `_urls()` o subclassing — c'è un pattern noto;
3. test: la sitemap deve avere `12 × 4 = 48` `<url>` con
   `xhtml:link` correttamente popolati.

### 2.5 P1-SEO-2: Lighthouse gating CI

`scripts/run_public_lighthouse_audit.py` esiste ma non è in CI
(`pytest` non lo invoca).

**Azione**:

1. workflow GitHub Actions / GitLab CI / Jenkins (a seconda dello
   Studio) che esegue Lighthouse su:
   - home it/fr/en/ar;
   - 5 country landing in 4 lingue (20 URL);
   - methodology;
   - wizard IT;
   - result page IT (con simulazione 35/10/0 fixture);
2. baseline: a11y/SEO/best-practices ≥ 95, perf ≥ 80;
3. fail PR se baseline non rispettata.

### 2.6 P1-SEO-3: schema.org `FAQPage`, `BreadcrumbList`, `Article`

Oggi solo `LegalService` su country landing.

**Azione**:

- `BreadcrumbList`: country landing già ha breadcrumb HTML
  (`country_landing.html:73-80`), va aggiunto JSON-LD coerente.
  Helper `apps.core.seo.build_breadcrumb_json_ld()` da scrivere.
- `FAQPage`: quando si aggiungeranno sezioni FAQ (vedi Sez. 4 sotto),
  emettere lo schema `FAQPage` con domande/risposte.
- `Article`: per il blog/guide editoriale (vedi Sez. 5 sotto).

### 2.7 P1-SEO-4: `<meta name="theme-color">`, `<meta name="application-name">`

Mancanti. Ridotto impatto SEO ma utili per trust visibility (icona
browser, install prompt PWA se mai).

### 2.8 P1-SEO-5: Google Search Console / Bing Webmaster Tools

Non configurati. Al go-live:

1. registrare proprietà `simulatore.studiolegalebadrane.it`;
2. caricare `sitemap.xml`;
3. configurare hreflang reporting;
4. monitorare Coverage report (errori crawl, pagine escluse).

### 2.9 P1-SEO-6: Performance budget e LCP/FID/CLS

Definire budget esplicito:

- LCP < 2.5 s su 4G slow (mobile);
- FID < 100 ms;
- CLS < 0.1;
- Total Blocking Time < 300 ms;
- pagina < 200 KB transfer compresso (target).

Lighthouse CI lo valida. Fonts locali (P1-LEG-1) sono il primo
beneficio.

---

## 3. Strategia URL e content architecture multi-lingua

### 3.1 Principio guida

> Una piattaforma legale **multi-paese × multi-case-type ×
> multi-lingua** ha 5 × 6 × 4 ≈ 120 pagine pivot. Senza una
> tassonomia stabile, l'SEO si frammenta in URL incoerenti e
> contenuti duplicati.

Tre dimensioni:

- **Paese** (5 attuali, 7+ futuri): `it`, `fr`, `be`, `ma`, `tn` →
  `es`, `de`, `ca`, `ro`, `dz`, `eg`, …
- **Case type** (6 grandi famiglie):
  - `road-accident` (incidente stradale);
  - `medical-malpractice` (responsabilità medica);
  - `workplace-injury` (infortunio sul lavoro);
  - `wrongful-death` (danno da decesso, perdita parentale);
  - `inheritance` (successioni internazionali);
  - `cross-border-claims` (reclami transfrontalieri).
- **Lingua** (4 attuali): `it`, `fr`, `en`, `ar`.

### 3.2 URL pattern raccomandato

Mantenere `i18n_patterns` Django (lingua come prefisso, default IT no
prefisso), poi:

| Layer | URL | Esempio |
|---|---|---|
| **Country pivot** (esiste oggi) | `/{lang}/countries/{country}/` | `/fr/countries/morocco/` |
| **Case-type pivot** (NUOVO) | `/{lang}/cases/{case-type}/` | `/it/cases/danno-biologico/` |
| **Country × case-type** (NUOVO, leaf SEO) | `/{lang}/{country}/{case-type}/` | `/it/italia/incidente-stradale/`, `/fr/maroc/successions/` |
| **Authority topic** (NUOVO, evergreen) | `/{lang}/topics/{topic}/` | `/it/topics/tabella-unica-nazionale-2025/` |
| **Glossario** (NUOVO) | `/{lang}/glossary/{term}/` | `/it/glossary/danno-morale/` |
| **FAQ globale** (NUOVO) | `/{lang}/faq/` | `/it/faq/` |
| **Blog/guide** (NUOVO) | `/{lang}/blog/{slug}/` | `/it/blog/incidente-marocco-italia-cosa-fare/` |
| **Wizard** (esiste) | `/{lang}/wizard/{country}/{case-type}/` | `/it/wizard/it/road-accident/` |

> **Decisione di slug per le case-type**: usare slug **localizzati**
> (`incidente-stradale` in IT, `accident-route` in FR, `road-accident`
> in EN, `حادث-طريق` in AR transcribed Latin), perché Google usa lo
> slug come segnale rank. Non usare lo stesso slug inglese in tutte
> le lingue.

### 3.3 Slug per case-type (proposta)

| Case-type | IT | FR | EN | AR (translit) |
|---|---|---|---|---|
| Road accident bodily injury | `incidente-stradale` | `accident-route` | `road-accident` | `hadith-tariq` |
| Medical malpractice | `responsabilita-medica` | `responsabilite-medicale` | `medical-malpractice` | `khata-tibbi` |
| Workplace injury | `infortunio-sul-lavoro` | `accident-travail` | `workplace-injury` | `hadith-aml` |
| Wrongful death / perdita parentale | `danno-da-decesso` | `prejudice-deces` | `wrongful-death` | `darar-wafa` |
| International inheritance | `successioni-internazionali` | `successions-internationales` | `international-inheritance` | `irth-dawli` |
| Cross-border claims | `reclami-transfrontalieri` | `reclamations-transfrontalieres` | `cross-border-claims` | `mutalabat-aabira` |

> **DA VALIDARE**: lo Studio (e idealmente un madrelingua arabo
> esperto di lessico legale) firma gli slug AR — è importante per
> deontologia e SEO.

### 3.4 Slug per country (mantenere consistente)

| Country code | IT | FR | EN | AR |
|---|---|---|---|---|
| IT | `italia` | `italie` | `italy` | `italia` |
| FR | `francia` | `france` | `france` | `firansa` |
| BE | `belgio` | `belgique` | `belgium` | `bilijika` |
| MA | `marocco` | `maroc` | `morocco` | `al-maghrib` |
| TN | `tunisia` | `tunisie` | `tunisia` | `tunis` |

### 3.5 Pagine "country × case-type" (leaf SEO)

> 5 paesi × 6 case-type × 4 lingue = **120 pagine leaf**. Non vanno
> create tutte subito.

**Strategia di rollout**:

1. **Fase 1 (P1-SEO)**: solo le combinazioni **operative**:
   - IT × road-accident (calculator REAL) — pagina già coperta
     parzialmente da `/wizard/it/road-accident/`, va integrata con
     una pagina leaf SEO-friendly `/it/italia/incidente-stradale/`
     che spiega: "cosa è il danno biologico", "TUN 2025", "come si
     calcola", "esempio worked", "richiedi simulazione" (link al
     wizard);
2. **Fase 2 (post Studio review)**: leaf per FR/BE × road-accident,
   MA/TN × inheritance — identico pattern, ma dichiara
   esplicitamente "valutazione legale preliminare manuale, no
   automatic estimate";
3. **Fase 3 (espansione)**: leaf per case-type ulteriori (medical
   malpractice, workplace, ecc.) **solo dopo** che esistono fonti
   approved e calculator (anche solo di scaffold);
4. **Fase 4 (espansione paesi)**: nuovi paesi (Spagna, Germania,
   Romania, ecc.) seguono lo stesso pattern.

### 3.6 Page template per leaf country × case-type

Ogni leaf deve avere:

- H1 unico: "{Case-type localizzato} — {Country localizzato}";
- introduzione (250-400 parole): cosa è, quando si applica,
  riferimenti normativi locali (link a country pivot e topic);
- box "Range tipici" (se calculator approved) o "Valutazione legale
  preliminare" (se scaffold);
- elenco fonti citate con link a topic page;
- esempio worked (numerico per IT, narrativo per FR/BE/MA/TN);
- FAQ (3-5 domande pertinenti, marcate con schema `FAQPage`);
- CTA primaria al wizard del paese;
- CTA secondaria al `/contact/`;
- breadcrumb completa: Home > Countries > {Country} > {Case-type};
- canonical, hreflang, OG, JSON-LD `Article` + `FAQPage` +
  `BreadcrumbList`.

Template parametrico riutilizzabile, simile al pattern già usato per
country landing.

---

## 4. FAQ schema e contenuti pivot evergreen

### 4.1 FAQ globale `/it/faq/`

15-25 domande coperte, raggruppate in 4-5 sezioni:

- **Cos'è una simulazione?** (3 domande: cosa è, cosa NON è,
  come è prodotta)
- **Affidabilità delle fonti** (3 domande: che fonti, come validate,
  cosa cambia se cambiano)
- **Privacy e dati** (3 domande: cosa raccogliamo, retention,
  diritti GDPR)
- **Procedura legale** (4-5 domande: prossimi passi dopo simulazione,
  costi, tempi, dove vado se sono italiano in Marocco, ecc.)
- **Casi internazionali** (3-4 domande: legge applicabile, foro
  competente, traduzione documenti)

Schema `FAQPage` JSON-LD: ogni Q&A è una `Question` con `acceptedAnswer`
`Answer.text`.

### 4.2 FAQ per paese (sezione dentro country landing)

Aggiungere una sezione FAQ dedicata al paese (3-5 domande paese-specifiche)
in fondo al `templates/public/country_landing.html`. Esempio MA:

- "Sono italiano sposato con marocchina, asset in entrambi i paesi.
  Quale legge si applica alla successione?"
- "I figli nati fuori matrimonio hanno gli stessi diritti?"
- "Posso fare professio juris (scelta legge applicabile)?"

Marcate `FAQPage`.

### 4.3 Authority topic pages (pivot SEO)

Ogni topic con alta search intent ha pagina dedicata:

| Topic IT | URL | Search intent (IT) |
|---|---|---|
| Tabella Unica Nazionale 2025 | `/it/topics/tabella-unica-nazionale-2025/` | "TUN 2025", "tabella unica risarcimenti 2025", "dpr 12/2025" |
| Danno biologico | `/it/topics/danno-biologico/` | "danno biologico calcolo", "punti invalidità" |
| Danno morale | `/it/topics/danno-morale/` | "danno morale 2025" |
| Danno parentale | `/it/topics/danno-parentale/` | "danno parentale tabelle Milano" |
| Tabelle Milano vs TUN | `/it/topics/tabelle-milano-vs-tun-2025/` | comparativo (deontologicamente OK perché informativo) |
| Reg. UE 650/2012 | `/it/topics/regolamento-ue-650-2012/` | "successione internazionale UE" |
| Codice di Famiglia Marocco (Moudawana) | `/it/topics/moudawana-successione/` | "successione Marocco regole islamiche" |
| Loi Badinter | `/fr/topics/loi-badinter/` | "indemnisation accident loi badinter" |
| Référentiel Mornet 2024 | `/fr/topics/referentiel-mornet-2024/` | "barème mornet" |

> Topic page = **pillar content**: 1500-3000 parole, ben strutturato,
> con riferimenti cliccabili alle fonti, sub-link ai leaf paese ×
> case-type, link al wizard se applicable.

> **Vincolo deontologico (LEGAL_COMPLIANCE_CONTENT_AUDIT.md Sez. 3)**:
> nessun esempio numerico citabile come "il nostro cliente ha
> ottenuto X €". Solo importi tabellari ufficiali tratti da fonti
> approved.

### 4.4 Glossario `/it/glossary/...`

50-100 termini chiave (danno biologico, danno morale, Loi Badinter,
Moudawana, professio juris, ḥajb, ʿawl, radd, faraïd, …).

Ogni termine ha pagina dedicata 200-400 parole + link bidirezionali
a topic / country / case-type. Schema `DefinedTerm` (subclass di
`DefinedTermSet`).

### 4.5 Blog / guide

L'app `apps.cms_content/` è scaffold vuoto. Va implementata in
**Fase 4** (post-MVP):

- modello `Article` con `slug`, `title`, `body`, `author` (FK User
  staff/lawyer), `country`, `case_type`, `published_at`, `updated_at`,
  `language`, `featured_image`, `meta_title`, `meta_description`;
- multilingua via `django-modeltranslation` (già in `requirements.txt`)
  o pattern collegato (`ArticleTranslation`);
- RSS feed `/it/blog/feed.xml`;
- categorie / tag;
- schema `Article` JSON-LD;
- view list + detail.

**Naming articoli — esempi (non ancora scritti)**:

- "Incidente stradale in Italia per cittadino straniero: cosa fare nei primi 30 giorni" (cross-link IT × road-accident);
- "Successione transfrontaliera Marocco-Italia: il Reg. UE 650/2012 e la Moudawana" (cross-link MA × inheritance);
- "Quando il calcolo TUN 2025 può essere superato dalle tabelle del Tribunale di Milano" (topic IT);
- "Préjudice corporel en France: barème Mornet 2024 et capitalisation" (FR);
- "Faraïd: les parts d'héritage en droit musulman et leur application en Europe" (MA/TN cross-border).

> Frequenza target: 1 articolo/settimana. Ogni articolo va firmato
> da un avvocato (autore visibile, schema `author` come `Person` con
> `jobTitle` Avvocato, `worksFor` Studio).

### 4.6 RSS / Atom feed

- `/it/blog/feed.xml` per articoli;
- `/it/legal-sources/feed.xml` per nuove fonti approvate (utile per
  professionisti che monitorano aggiornamenti normativi).

---

## 5. Internal linking strategy

### 5.1 Principio

Ogni pagina di leaf (country × case-type, topic, articolo) deve
linkare a **3-5 pagine correlate**:

- 1 link a country pivot;
- 1 link a case-type pivot (quando esisterà);
- 1-2 link a topic pages pivot;
- 1 link al wizard del paese;
- 1 link a `/contact/` (CTA);
- (se applicable) link a glossary terms.

### 5.2 Anchor text

- Variare l'anchor text (no "click qui");
- Usare keyword secondarie ("come si calcola il danno biologico",
  "quale legge si applica");
- Mai over-optimization (no farcire ogni anchor con keyword
  primaria).

### 5.3 Cross-link multilingua

Oltre agli `hreflang` `<head>`, ogni pagina dovrebbe avere un
language switcher visibile (già presente nel header) **e** un link
testuale "Read this page in Italian / Français / English / العربية"
in fondo, per migliorare la signal di traduzione.

### 5.4 Pagina `/sitemap-html/` (per umani)

Oltre alla `sitemap.xml` per i bot, una pagina HTML "Indice del sito"
per umani:

- elenco country landings, case-type, topic, glossary, blog;
- raggruppato per lingua;
- accessibile da footer.

Aiuta utenti a trovare contenuti e Google a discovery.

---

## 6. Performance e Core Web Vitals

### 6.1 Stato attuale

Da `release_readiness_audit_pass1` (ultimo audit Lighthouse):
"every page passes a11y / SEO / structural fallback rules". Nessun
numero LCP/FID/CLS dichiarato — vanno baseline-ati.

### 6.2 Quick wins già identificati

1. **Google Fonts locali** (P1-LEG-1) → -100-300 ms LCP, +privacy;
2. **Image lazy loading** → tutte le `<img>` non hero hanno
   `loading="lazy"` (verificato in `country_landing.html:104`);
3. **Hero image preload** → `loading="eager" decoding="async"
   fetchpriority="high"` (verificato in `home.html:13`);
4. **CSS critico inline**: piccola porzione critica già in `<style>`
   inline (`base.html:22-45`) — ok;
5. **No JS framework**: HTMX + Alpine sono leggeri, no React/Vue
   bundle;
6. **HTTP/2 + brotli** lato reverse proxy (Caddy/nginx).

### 6.3 Quick wins da implementare

- `Cache-Control: public, max-age=31536000, immutable` su
  `/static/` (configurazione reverse proxy);
- `Cache-Control: public, max-age=86400` su `/media/pexels/`;
- Server-Timing header per debug perf in staging (off in prod);
- Preconnect a `fonts.gstatic.com` se le font restano remote (fallback);
- HTML compression (gzip/brotli) su HTML server-rendered.

### 6.4 Performance budget proposto

| Metrica | Mobile (4G) | Desktop |
|---|---|---|
| LCP | < 2.5 s | < 1.5 s |
| FID/INP | < 100 ms / < 200 ms | < 50 ms / < 100 ms |
| CLS | < 0.1 | < 0.05 |
| TBT | < 300 ms | < 100 ms |
| Bytes (transfer compressed) | < 200 KB | < 250 KB |
| Requests | < 30 | < 35 |

CI gating su Lighthouse mobile (peggiore) come indicatore.

---

## 7. Multi-paese e ruolo SEO del sito madre

> `https://international.studiolegalebadrane.it/` (sito madre) è
> **dominio istituzionale**. La piattaforma è
> `https://simulatore.studiolegalebadrane.it/` (sub-dominio).

### 7.1 No canonical cross-domain

Il sito madre **non deve** canonicalizzare verso il simulatore (e
viceversa). Sono prodotti distinti con search intent diverso.

### 7.2 Cross-link controllati

- Sito madre → simulatore: CTA "Prova il simulatore" su pagine
  servizi pertinenti (incidenti stradali, successioni internazionali);
- Simulatore → sito madre: link nel footer (`PARENT_SITE_URL`),
  link "Visita il sito istituzionale" in header CTA, link da
  pagina `/about/` (se aggiunta).

### 7.3 No duplicazione contenuti

Se il sito madre ha già una pagina su "Loi Badinter", il simulatore
**non** deve duplicarla: deve linkarla. Eventualmente una topic page
sul simulatore può essere più tecnica/operativa, mentre quella sul
sito madre più generale/marketing.

> **DA VALIDARE STUDIO**: chi possiede ciascun topic? Va concordato
> prima di scrivere blog/topic per evitare duplication issue su
> Google.

### 7.4 Schema.org coerenza

Sul simulatore: `LegalService` con `parentOrganization` =
`Organization` "Studio Legale Internazionale Badrane" (sito madre).

Sul sito madre: `LegalService` o `Organization` autoreferenziale.

Coerenza naming + URL trans-domini aiuta Knowledge Graph.

---

## 8. Roadmap SEO (allineata a `LOCAL_NEXT_STEPS.md`)

### 8.1 Pre-go-live (P0)

- P0-SEO-1 `robots.txt` (Sez. 2.1)
- P0-SEO-2 `noindex` su result + thank-you (Sez. 2.2)
- P0-SEO-3 hreflang globale (Sez. 2.3)
- P0-LEG-1 privacy policy completa (vedi `LEGAL_COMPLIANCE_CONTENT_AUDIT.md`)
- P0-LEG-5 footer con identificativi professionali (idem)
- P1-LEG-1 Google Fonts locali (idem) — anche un beneficio SEO

### 8.2 Post-go-live IT (P1)

- P1-SEO-1 sitemap espansa multi-lingua
- P1-SEO-2 Lighthouse gating CI
- P1-SEO-3 schema.org `BreadcrumbList`, `FAQPage` su country landing
- P1-SEO-5 Google Search Console + Bing Webmaster
- prima leaf page `/it/italia/incidente-stradale/` (Sez. 3.5)
- topic page TUN 2025 (Sez. 4.3)
- FAQ globale `/it/faq/` con 15 domande (Sez. 4.1)
- glossario IT primi 20 termini (Sez. 4.4)

### 8.3 Post Studio review FR/BE/MA/TN (P2)

- leaf pages per FR/BE/MA/TN × case-type rispettivo
- topic pages per Loi Badinter, Mornet, Tableau Indicatif, Moudawana
- traduzioni professionali `.po` it/fr/en/ar firmate dallo Studio
- `compilemessages` in pipeline build
- FAQ per paese

### 8.4 Espansione editoriale (P3)

- attivare `apps.cms_content/`
- blog con 1 articolo/settimana
- newsletter (opt-in, GDPR-aware)
- RSS feed
- podcast (out of scope MVP)

### 8.5 Espansione paesi (P4-P5)

Ogni nuovo paese aggiunge:

- country pivot
- legal review package
- 1-2 case-type leaf pages
- traduzioni
- `LegalService` schema dedicato

---

## 9. Tabella riassuntiva — gap SEO

| ID | Voce | Severità | Owner | File |
|---|---|---|---|---|
| P0-SEO-1 | `robots.txt` assente | P0 | dev | `apps/core/views.py` + `config/urls.py` |
| P0-SEO-2 | `noindex` su result + thank-you | P0 | dev | template |
| P0-SEO-3 | hreflang globale (oltre country landings) | P0 | dev | context processor / template tag |
| P1-SEO-1 | Sitemap multi-lingua espansa (48 entry) | P1 | dev | `apps/core/sitemaps.py` |
| P1-SEO-2 | Lighthouse gating CI | P1 | dev + CI | workflow + `run_public_lighthouse_audit.py` |
| P1-SEO-3 | `BreadcrumbList` + `FAQPage` schema | P1 | dev | `apps/core/seo.py` |
| P1-SEO-4 | `theme-color`, `application-name` | P1 | dev | `base.html` |
| P1-SEO-5 | GSC / Bing Webmaster | P1 | Studio + dev | DNS / verification file |
| P1-SEO-6 | Performance budget + CI gating | P1 | dev + CI | Lighthouse config |
| P2-SEO-1 | Leaf pages country × case-type | P2 | dev + content | URL pattern + template |
| P2-SEO-2 | Topic pages pivot | P2 | dev + content | URL + template |
| P2-SEO-3 | FAQ globale + per paese | P2 | content + dev | template + JSON-LD |
| P2-SEO-4 | Glossario | P2 | content | template |
| P3-SEO-1 | Blog (cms_content) | P3 | dev + content | `apps.cms_content/` |
| P3-SEO-2 | RSS feed | P3 | dev | `Feed` Django |
| P3-SEO-3 | Sitemap-html per umani | P3 | dev | view + template |

---

## 10. Per Claude Code che riprende SEO

- **Mai** introdurre nuovi URL pubblici senza:
  - canonical self-reference;
  - hreflang alternates per le 4 lingue + `x-default`;
  - meta description ≥ 50 char e ≤ 160 char;
  - 1 solo `<h1>`;
  - struttura H2/H3 logica;
  - test in `apps/core/test_*_seo.py` o equivalent.
- **Mai** indicizzare pagine con dati personali (result, thank-you,
  area cliente futura).
- **Mai** duplicare contenuti tra simulatore e sito madre senza
  decidere chi possiede il topic.
- **Mai** creare slug uguali in lingue diverse: usare slug
  localizzati anche se l'URL diventa più lungo.
- Quando si aggiunge una topic/leaf page, aggiornare anche:
  1. `apps/core/sitemaps.py` (entry sitemap);
  2. internal linking dalle pivot esistenti;
  3. test SEO automatizzati;
  4. screenshot in `docs/screenshots/live_qa/<iter>/`.
