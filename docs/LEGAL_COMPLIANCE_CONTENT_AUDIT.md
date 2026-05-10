# LEGAL COMPLIANCE & CONTENT AUDIT — Indennizzati / Studio Legale Badrane

**Data:** 2026-05-10
**Audience:** lo Studio (avvocato responsabile e referente compliance),
sviluppatori, future istanze Claude Code.
**Scopo:** verificare che i contenuti pubblici della piattaforma
rispettino la deontologia forense italiana (e i vincoli equivalenti
in giurisdizioni FR/BE/MA/TN), il GDPR e le regole di trasparenza
pubblicitaria. **Non è un parere legale**: ogni voce contrassegnata
come "DA VALIDARE STUDIO" deve essere firmata dall'avvocato
responsabile prima del go-live.

> Documento di handover. Non sostituisce un'opinione legale.

---

## 0. Quadro normativo di riferimento

| Norma | Ambito | Note |
|---|---|---|
| **Codice deontologico forense** (CNF, ult. mod. 2024) | Italia, esercizio della professione di avvocato | Art. 17 (informazioni sull'attività professionale), Art. 17-bis (modalità di informazione), Art. 35 (modalità di comunicazione), Art. 38 (rapporto con il cliente). Vincoli: veridicità, correttezza, non comparativa, decoro. |
| **Legge 124/2017 art. 1 c. 152** | Italia, pubblicità avvocati | Liberalizza la pubblicità informativa, mantenendo i vincoli deontologici. |
| **Decreto MEF n. 145/2014** | Italia, equo compenso | Indicazione preventivi e parametri. |
| **GDPR (Reg. UE 2016/679)** | UE, dati personali | Base giuridica, informativa, consenso, retention, diritti dell'interessato. |
| **D.Lgs. 196/2003 (Codice privacy)** | Italia | Integrazione locale del GDPR. |
| **D.Lgs. 70/2003** | Italia, e-commerce / società informazione | Obblighi informativi sui siti professionali (art. 7). |
| **Reg. (UE) 2022/2065 (Digital Services Act)** | UE | Trasparenza piattaforme online (limitato ma applicabile). |
| **Direttive consumatori (Dir. 2011/83/UE)** | UE | Se ci fossero servizi a pagamento on-line (oggi non applicabile: il sito non vende). |
| **Loi 71-1130 du 31 déc. 1971** + **RIN** | Francia, professione avvocato | Vincoli pubblicità simili a deontologia IT. |
| **Code de déontologie ordre barreaux belges** | Belgio | Idem. |
| **Loi 28-08 (Maroc) statut avocats** | Marocco | Idem. |
| **Loi 89-87 (Tunisia) sur la profession d'avocat** | Tunisia | Idem. |

> **Nota:** l'avvocato responsabile dello Studio, iscritto all'Ordine
> di [DA INSERIRE], è il garante deontologico della piattaforma.
> Tutti i testi pubblici devono essere firmati prima del go-live.

---

## 1. Audit del footer e degli identificativi professionali

### 1.1 Stato attuale (`templates/partials/footer.html`)

Il footer espone:

- nome Studio (`Studio Legale Internazionale Badrane`);
- claim "International legal practice with cross-border experience…";
- link al sito madre (`PARENT_SITE_URL`);
- link alle pagine Platform (Countries, Case types, Methodology);
- link alle pagine Legal (Disclaimer, Privacy, Institutional website);
- micro-strip © `SITE_NAME` + "Indicative simulations. Not legal advice.".

### 1.2 Cosa manca per conformità deontologica IT

> ❌ **Bloccante go-live** — DA VALIDARE STUDIO.

| Voce | Stato attuale | Vincolo | Azione |
|---|---|---|---|
| Nome avvocato responsabile e iscrizione Ordine | Assente | Art. 17-bis Cod. deont. + D.Lgs. 70/2003 art. 7 | Aggiungere "Avv. [Nome] — Ordine degli Avvocati di [Foro], iscritto al n° [matricola]". |
| Indirizzo studio | Assente | Idem | Aggiungere indirizzo legale completo. |
| Codice fiscale / P.IVA | Assente | D.Lgs. 70/2003 art. 7 | Aggiungere "C.F./P.IVA [nnnn]". |
| PEC professionale | Assente | D.L. 185/2008 (DPR 285/2014) | Aggiungere "PEC: [...]". |
| Telefono / email contatto | Assente in footer (presente solo via form) | Buona prassi | Aggiungere "Tel: [...] · Email: [...]". |
| Massima assicurativa professionale | Assente | Art. 12 L. 247/2012 + DM 22/9/2016 | Aggiungere "Polizza R.C. professionale n. [polizza] — [Compagnia] — Massimale: [importo]". |
| Indicazione che il sito è autonomo dal sito madre | Non esplicita | Buona prassi (no confusione utente) | Aggiungere "Piattaforma operata da Studio Legale Internazionale Badrane in qualità di sub-dominio del sito istituzionale [PARENT_SITE_URL]." |

**File da modificare**: `templates/partials/footer.html` (aggiungere
sezione "Identificazione professionale"). I valori sono dati stabili
dello Studio: dopo che li hai inseriti, vivono come stringhe
traducibili `{% blocktranslate %}` o costanti settings (`STUDIO_VAT`,
`STUDIO_PEC`, ecc.).

### 1.3 Multi-paese

Per ciascun paese di operatività diretta (FR/BE/MA/TN), se lo Studio
opera attraverso un avvocato di riferimento iscritto al rispettivo
Ordine, le credenziali vanno aggiunte nelle landing paese o in una
pagina "Studio internazionale" dedicata. Se lo Studio opera solo
*via* Italia → DIP, va dichiarato esplicitamente che la procedura in
quei paesi avviene tramite avvocato corrispondente locale.

---

## 2. Audit dei contenuti pubblici (claim, promesse, comparativi)

### 2.1 Home (`templates/public/home.html`)

Estrazione testi rilevanti (riga in file → contenuto):

| Riga | Testo | Verdetto deontologico |
|---|---|---|
| `25-27` | "Indicative simulations for compensation and inheritance, grounded in validated legal sources" | ✅ Veritiero, prudente. |
| `28-30` | "We do not promise outcomes — we help you understand them" | ✅ **Esemplare**: dichiara esplicitamente che non ci sono promesse di risultato. |
| `44-46` | "Simulations are indicative. They do not constitute legal advice or guarantee any outcome" | ✅ Disclaimer in chiaro. |
| `52-69` | "Trust by design" (4 bullet: citazione fonti, no numeri inventati, range trasparenti, multilingua) | ✅ Veritiero, dimostrabile. |
| `100-104` | "Validated sources only" | ✅ Verificabile (`LegalSource.status=approved`). |
| `108-111` | "Transparent ranges" | ✅ Verificabile (output engine ha min/mid/max). |
| `115-118` | "Human review" | ✅ Veritiero. |

**Verdetto Home**: nessun claim deontologicamente problematico
rilevato.

### 2.2 Methodology (`templates/public/methodology.html`)

Tutti i testi sono **descrittivi e veritieri** (ciclo fonte:
draft → approved, ranges con assumptions, "if no approved source
exists … we tell you explicitly. We do not invent a fallback
estimate"). ✅ Verdetto: conforme.

### 2.3 Country landing (`templates/public/country_landing.html`)

Testi paese-per-paese sono descrittivi e indicano le fonti di
riferimento (TUN 2025 per IT, Mornet 2024 + Gazette du Palais 2022
per FR, Tableau Indicatif 2020/2024 per BE, Moudawana + Reg. 650/2012
per MA, CSP Livre IX + Loi 98-97 per TN). ✅ Veritiero.

Per FR/BE/MA/TN i testi dichiarano esplicitamente "no automatic
amount is published before the underlying quantification sources have
been verified". ✅ Conforme.

**Polish suggerito (P2)**: aggiungere in fondo a ogni country
landing una micro-card "Avvocato di riferimento per [Paese]" con
nome + iscrizione Ordine locale (quando applicabile), per evitare
percezione di "studio italiano che si occupa di tutto senza
specializzazione locale".

### 2.4 Disclaimer (`templates/public/disclaimer.html`)

Il testo attuale (l. 13-19) è prudente e completo:

> "This platform offers indicative simulations of compensation and
> inheritance scenarios across multiple jurisdictions. Each simulation
> is based on legal sources catalogued and validated by our team.
>
> A simulation is not legal advice, is not a medico-legal opinion and
> is not a guarantee of outcome. The actual evaluation of a case
> depends on documents, expert reports, liability assessment,
> applicable law, competent jurisdiction, case law and insurance
> practice.
>
> If you require a binding evaluation, please request a legal review
> through our office."

✅ Verdetto: conforme alla regola CLAUDE.md (disclaimer obbligatorio).

⚠️ **Working version**: la riga `21-23` dichiara esplicitamente
*"This text is a working version. The final wording will be reviewed
and signed off by the Studio's legal team."* → **bloccante go-live**:
lo Studio deve firmare la versione finale.

### 2.5 Privacy (`templates/public/privacy.html`)

Anche qui working summary (riga `24-26`): *"A complete privacy policy
will be published before the simulator goes live to the public. This
page is a working summary."*

Contenuto attuale:

- riferimento al GDPR e leggi locali; ✅
- elenco tipi di dato raccolti (input simulazione, lingua/paese, IP/UA, consensi); ✅
- "We do not sell personal data"; ✅
- "We do not share with third parties beyond what is strictly necessary"; ✅
- diritti dell'interessato (accesso, rettifica, cancellazione, anonimizzazione); ✅

⚠️ **Manca per privacy completa pre go-live:**

1. Identità del **titolare del trattamento** (Studio + avvocato
   responsabile + indirizzo + PEC + email DPO se nominato);
2. Base giuridica per ciascun trattamento (consenso art. 6.1.a per
   simulazione e contatto; legittimo interesse art. 6.1.f per
   security/audit log);
3. **Categorie particolari di dati** (art. 9): se l'utente compila
   il wizard con percentuale invalidità, lesioni, dati medici,
   è dato sanitario → richiede base giuridica art. 9.2 esplicita
   (consenso esplicito separato, non confondibile con il privacy
   generico);
4. **Periodi di conservazione** per categoria (oggi: `DataRetentionPolicy`
   è dichiarativo ma il cron F11 non è attivo);
5. **Trasferimenti extra-UE**: se si attiva CRM esterno (n8n
   self-hosted UE: ok; se cloud US: serve clausola SCC + DPIA);
6. **Diritto di reclamo al Garante**;
7. **Cookies**: link al cookie banner settings (oggi banner solo
   informativo);
8. **Modalità di esercizio dei diritti** (form web, PEC, lettera
   raccomandata);
9. **Versione + data** della privacy policy + traccia di
   versionamento via `compliance.ConsentTextVersion`;
10. **Lingua originale** (italiano) + traduzioni autorevoli (FR/EN/AR).

> **Bloccante go-live (P0-LEG-1):** privacy policy definitiva firmata
> dallo Studio e versionata nelle 4 lingue. Vedi
> `apps/compliance/services.record_consent` per il pattern di
> versionamento.

### 2.6 Contact form (`templates/public/contact.html`)

| Riga | Testo | Verdetto |
|---|---|---|
| `13-15` | "Tell us about your case in your own words. A member of the Studio will get back to you to evaluate whether and how we can help" | ✅ Veritiero, no garanzia di accettazione. |
| `21` | "Average response: 3–5 working days" | ✅ Indicazione tempi onesta. |
| `22` | "Sending this form does not create a professional engagement" | ✅ **Esemplare**: chiarisce che non si forma il mandato. |
| `98` | "Briefly describe what happened, when, and where. Avoid sharing sensitive medical details now — we will request them only if needed" | ✅ Data minimization in chiaro all'utente. |
| `106` | "I have read the [privacy notice] and the [disclaimer], and I consent to my data being processed by the Studio for the sole purpose of replying to this request" | ✅ Consenso specifico, finalità limitata. |
| `115` | "Submitting this form does not create a professional engagement" | ✅ Ridondanza utile. |

**Verdetto contact**: conforme. **Polish (P2)**: la `aria-hidden="true"`
sul honeypot e l'`<input type="checkbox" required>` sono corretti.

### 2.7 Cookie consent banner (`templates/partials/cookie_consent_banner.html`)

Stato: **banner informativo, non opt-in granulare**.

- testo: "This site uses only strictly necessary technical cookies
  (session, CSRF). No analytics or marketing trackers are active";
- single-CTA "OK", localStorage `badrane.cookieConsent.v1`;
- ✅ Conforme **finché non ci sono cookie/tracking non essenziali**.

⚠️ **Vincolo futuro**: se si attivano

- Pexels tracking (oggi disattivato di default, `PEXELS_ENABLED=False`);
- Google Analytics / Fathom / Plausible;
- Hotjar / FullStory / qualunque session replay;
- Pixel Meta / TikTok / LinkedIn;
- Mappe Google embed (carica cookie `_ga`);

→ il banner deve diventare **consent manager opt-in granulare**
(layered consent) prima dell'attivazione, con bottoni "Accetta tutti"
/ "Rifiuta tutti" / "Personalizza", e il default deve essere
"non attivo" finché l'utente non sceglie. Vedi linee guida Garante
italiano 10/06/2021.

### 2.8 Result page (`templates/public/wizard_result.html`)

Già auditato in `docs/architecture/PUBLIC_FUNNELS_UX_AUDIT.md`.
Verifica deontologica:

- range min/mid/max chiaramente etichettato come "indicative range";
- "Calculation basis" cita fonti, formula, ipotesi;
- card disclaimer (black/gold) sempre visibile;
- ID simulazione + timestamp tracciabile;

✅ Verdetto: conforme. **Polish (P2)**: aggiungere paragrafo
"Cosa NON è questa stima" (es. "Questa stima non considera la
giurisprudenza specifica del foro competente, il comportamento della
controparte assicurativa, eventuali concorsi di colpa non
documentati, danni patrimoniali non quantificati, …").

---

## 3. Claim deontologicamente problematici da NON usare

Lista di formule da **bandire** dai template, copy SEO, blog, email
marketing. Verificare in audit periodico (`scripts/audit_public_content_hygiene.py`
copre già parte di questo).

| ❌ NON usare | Motivo | Alternativa accettabile |
|---|---|---|
| "Ottieni il massimo risarcimento" | Promessa di risultato | "Comprendi quale range orientativo emerge dalle tabelle" |
| "Risarcimento garantito" | Promessa di risultato | "Valutazione legale dello Studio" |
| "Casi di successo" / "100% successo" | Promessa di risultato + comparativo | "Esempi anonimi orientativi (con consenso scritto del cliente)" |
| "Nessuna spesa anticipata" / "Solo se vinciamo" | In Italia il patto quota lite è regolato; va indicata la struttura del compenso senza farne strumento di marketing | "Preventivo scritto su richiesta. Equo compenso conforme ai parametri ministeriali" |
| "Valutazione gratuita" | Tollerabile se onesto, ma può diventare claim deontologicamente debole se sovraesposto | "Prima valutazione informativa senza impegno" |
| "Lo Studio leader nei risarcimenti" / "I migliori avvocati" | Comparativo elogiativo (vietato) | "Studio internazionale con esperienza in [area] dal [anno]" |
| "Avv. X ha ottenuto € [importo]" senza consenso scritto del cliente | Violazione segreto professionale (art. 28 Cod. deont.) | Mai usare somme o nomi clienti, anche con iniziali, salvo consenso scritto + decisione resa pubblica. |
| "Recensioni clienti" con stelline | Discutibile in Italia (CNF). FR/BE/MA/TN: vincoli simili. | Evitare. Eventualmente "Pareri dei clienti" (testimonial sobri, anonimi, con consenso scritto) — ma scelta da firmare deontologicamente. |
| "Ti aiutiamo in qualsiasi situazione" | Promessa generica indeterminata | "Lo Studio valuta caso per caso se rientra nello scope di competenza" |
| "Procedure rapide" / "In 24 ore risarcimento" | Promessa di tempo non realistica | "Tempi medi di risposta dello Studio: 3–5 giorni lavorativi" (già usato in `contact.html`) |

**Audit script proposto**: estendere `audit_public_content_hygiene.py`
con regex per le frasi vietate sopra. Già oggi lo script copre alcune
parole bandite (vedi `PUBLIC_CONTENT_HYGIENE_AUDIT_PASS5.md`); va
ampliato con questa lista deontologica. **Azione**: ticket
`F-content-hygiene-deontology-pass1`.

---

## 4. Cookie / tracker / terze parti

Inventario stato attuale (verificato in `templates/base.html` +
`config/settings.py`):

| Voce | Stato | Note |
|---|---|---|
| Google Fonts (CSS) | ✅ ATTIVO (`<link>` in `base.html` l. 18-20) | Carica `fonts.gstatic.com`. **Non è privacy-by-default** (Germania ha sanzionato siti per Google Fonts senza consenso). **Mitigazione**: hostare le font localmente in `static/fonts/` (vedi P1 sotto). |
| Google Analytics / GA4 | ❌ assente | OK. |
| Sentry frontend | ❌ assente | OK. Sentry server-side è opt-in via `SENTRY_DSN`. |
| Pexels API | ❌ disattivato di default (`PEXELS_ENABLED=False`) | Quando attivato, le immagini sono cached server-side e servite localmente da `media/pexels/`. Niente tracking. |
| Cookie banner | ✅ presente, informativo only | Vedi Sez. 2.7. |
| reCAPTCHA / hCaptcha | ❌ assente | Sostituito da honeypot + rate limit (privacy-friendly, scelta consapevole). |
| Tag Manager / Pixel | ❌ assente | OK. |
| Mappe embed | ❌ assente | OK. |
| Chat widget (Tawk.to, Intercom) | ❌ assente | OK. |

### P1-LEG-1 — Google Fonts

> 🟡 **Privacy concern (P1)**

Stato: `<link href="https://fonts.googleapis.com/css2?…">` in
`templates/base.html` l. 18-20 → ogni pageview espone l'IP utente a
Google.

**Azione consigliata**: hostare le font localmente.

1. scaricare i WOFF2 di Inter, Cormorant Garamond, Tajawal, Amiri
   (licenze SIL OFL, libere);
2. salvarli in `static/fonts/`;
3. servire via `@font-face` in `static/css/site.css`;
4. rimuovere `<link>` Google Fonts da `base.html`;
5. aggiungere `<link rel="preload">` per i pesi critici (400, 600).

Beneficio: zero terze parti, performance migliore, conformità
privacy automatica. Vedi anche `docs/architecture/REMOVE_TAILWIND_CDN_PASS2.md`
(precedente analogo).

---

## 5. Condizioni di incarico e relazione cliente

> ❌ **Bloccante go-live (P0-LEG-2) — DA VALIDARE STUDIO**

Quando un Lead si trasforma in cliente attivo (post-form, post-prima
consulenza), va formalizzato un **mandato professionale scritto**
conforme a:

- Art. 38 Cod. deont. (scritturazione mandato);
- L. 247/2012 art. 13 (informativa preventivo + parametri);
- D.M. 55/2014 e successive (parametri compenso).

**Stato piattaforma**: nessun flusso di firma incarico online. È
P3/fuori scope MVP (vedi `docs/AUDIT_DELTA_2026-05-10.md` Sez. 4.4).

**Cosa fare prima del go-live**:

1. preparare un **modello di mandato professionale** PDF in 4 lingue;
2. inserire nel `templates/public/contact_thank_you.html` o nella
   email di follow-up al Lead un riferimento esplicito a:
   - "La eventuale instaurazione di un mandato avverrà solo dopo
     una consulenza preliminare e la firma scritta di un incarico
     professionale, conforme ai parametri ministeriali D.M. 55/2014
     e successive modifiche";
3. tracciare lo **stato mandato** in `crm.Lead.status`
   (`received → contacted → qualified → mandate_signed → converted`).
   Oggi la transizione `qualified → converted` non distingue il
   passaggio "mandato firmato"; va aggiunto stato esplicito o
   evento dedicato (`LeadEvent.event_type=MANDATE_SIGNED`).

---

## 6. Conflitto di interessi

Art. 24 Cod. deont. → l'avvocato non può accettare incarichi in
conflitto.

**Stato piattaforma**: nessun controllo automatico. Il Lead arriva
nello Studio e l'avvocato responsabile valuta manualmente prima di
contattare.

**Cosa fare**:

- nel form `apps.crm.forms.ContactForm`, aggiungere un campo
  opzionale "Controparte (nome, ragione sociale)" che alimenti
  `Lead.case_counterparty` (nuovo field), per:
  1. consentire allo Studio una rapida verifica conflitto prima
     della risposta;
  2. evitare di prendere appunti via canali insicuri (email, WhatsApp).
- l'admin Django può poi includere un filtro/list sul nuovo campo;
- politica privacy aggiornata di conseguenza (è dato di terzo, non
  dell'utente: serve richiamo art. 14 GDPR sul "diritto del terzo
  ad essere informato").

> **Decisione DA VALIDARE STUDIO**: vuoi che il form chieda la
> controparte? Pro: filtro conflitto; contro: dato sensibile su
> terzo, complessità GDPR.

---

## 7. Trattamento dati particolari (art. 9 GDPR)

Il wizard pubblico raccoglie:

- dati di salute (percentuale invalidità, ITT/ITP, tipo lesione,
  spese mediche);
- dati di reddito (perdita reddito);
- dati familiari (danno parentale, decesso);
- dati su procedimenti giudiziari (concorso di colpa, offerte
  assicurative ricevute).

Tutti **categorie particolari** ai sensi GDPR art. 9 e 10.

**Stato**: il consenso `ConsentPurpose.code=sim_processing` è
unitario; non distingue tra dati comuni e dati particolari.

> ❌ **Bloccante go-live (P0-LEG-3) — DA VALIDARE STUDIO**

**Azione**:

1. introdurre un secondo `ConsentPurpose.code=sim_special_categories`
   con `required_for_simulation=True`;
2. nel wizard, doppio checkbox:
   - "Acconsento al trattamento dei miei dati personali (GDPR art.
     6.1.a)";
   - "Acconsento espressamente al trattamento delle categorie
     particolari (dati di salute, dati su procedimenti) ai sensi
     dell'art. 9.2.a GDPR, finalizzato alla simulazione orientativa
     da me richiesta";
3. il secondo è opzionale: se rifiutato, il wizard può procedere ma
   alcuni campi (invalidità, lesione, ecc.) non vengono salvati o la
   simulazione viene rifiutata con "consenso esplicito mancante";
4. testi versionati nelle 4 lingue via `ConsentTextVersion`;
5. registrare entrambi i consensi in `ConsentRecord` con
   `purpose=sim_special_categories`.

---

## 8. Retention dati (GDPR art. 5.1.e)

Stato:

- `compliance.DataRetentionPolicy` è dichiarativo;
- `STAFF_AUDIT_RETENTION_*` settings esistono per audit staff (90/180
  giorni), ma `dry_run=True` di default;
- `crm.Lead`, `cases.Simulation`, `compliance.ConsentRecord`: nessun
  cron di cancellazione attivo.

> ❌ **Bloccante go-live (P0-LEG-4) — DA VALIDARE STUDIO**

**Policy dichiarate da firmare**:

| Categoria dato | Retention proposta | Base legale |
|---|---|---|
| `cases.Simulation` (input + output) — Lead non collegato | 90 giorni | Solo finalità tecnica statistica |
| `cases.Simulation` collegata a Lead `received/contacted` | 12 mesi | Risposta + follow-up |
| `cases.Simulation` collegata a Lead `qualified/converted` | 10 anni | Termine prescrizione professionale forense (art. 2946 CC + L. 247/2012) |
| `crm.Lead.status=received/rejected` | 12 mesi | Trattativa preliminare |
| `crm.Lead.status=converted` | 10 anni | Mandato professionale |
| `compliance.ConsentRecord` | come il dato a cui si riferisce + 2 anni (prova del consenso) | Onere della prova art. 7 GDPR |
| `compliance.PrivacyAuditEvent` | 5 anni | Audit GDPR + sicurezza |
| `compliance.StaffAccessEvent` | 90 giorni | Sicurezza |
| `compliance.StaffSecurityAlert` | 180 giorni | Sicurezza |
| `reports.SimulationReport` PDF | come `Simulation` |  |
| `legal_sources.LegalSource` (storico) | mai (cambia solo `status=deprecated/replaced`) | Audit calcolo + decennio |

**Azione**:

1. firma matrix sopra dallo Studio;
2. implementare cron Celery (`F-retention-policy-pass1`) che ogni
   giorno applica la policy con dry-run di default;
3. testo nella privacy policy che cita esattamente questi periodi.

---

## 9. Sicurezza dei dati (GDPR art. 32)

Già coperto da `docs/SECURITY_INDEX.md` (vedi). In sintesi:

- ✅ HTTPS + HSTS in prod;
- ✅ password hash bcrypt;
- ✅ MFA admin opt-in;
- ✅ audit log staff;
- ✅ rate limit form;
- ✅ honeypot;
- ✅ PII redaction logs;
- ❌ CSP non emessa lato Django (P0-SEC-1, vedi SECURITY_INDEX);
- ⚠️ Sentry: scrubber custom presente, ma da auditare in prod la
  prima settimana per assicurarsi che nessun PII raggiunga Sentry.

**Trasferimenti extra-UE**: oggi nessuno se Sentry, Pexels, Google
Fonts disattivati o hostati. Da rivalutare al go-live caso per caso.

---

## 10. Lingua dei contenuti vincolanti

Per ciascun documento legalmente vincolante (privacy, disclaimer,
condizioni mandato), la lingua **italiana** resta la versione di
riferimento (il rapporto professionale è regolato dal diritto
italiano se non diversamente concordato per iscritto).

Le altre lingue sono **traduzioni di cortesia**, da etichettare
esplicitamente:

> *"This is a courtesy translation. The Italian version is the legally
> binding one in case of discrepancy."*

**Azione**: aggiungere questa nota in fondo a privacy/disclaimer per
le versioni FR/EN/AR (e equivalente in arabo).

---

## 11. Tabella riassuntiva — bloccanti go-live deontologici

| ID | Voce | Severità | Owner | Stato |
|---|---|---|---|---|
| P0-LEG-1 | Privacy policy completa firmata, in 4 lingue, versionata | P0 | Studio | working version |
| P0-LEG-2 | Modello mandato professionale + flow `mandate_signed` | P0 | Studio | non esistente |
| P0-LEG-3 | Doppio consenso (art. 6 + art. 9) per dati particolari nel wizard | P0 | Studio + dev | consenso unitario oggi |
| P0-LEG-4 | Retention policy firmata + cron implementato | P0 | Studio + dev | dichiarativa, no cron |
| P0-LEG-5 | Identificativi professionali nel footer (Ordine, P.IVA, PEC, polizza) | P0 | Studio + dev | assenti |
| P0-LEG-6 | Disclaimer firmato (oggi: working version) | P0 | Studio | working version |
| P1-LEG-1 | Google Fonts hostati localmente | P1 | dev | dipendenza terza parte |
| P1-LEG-2 | Audit script `content_hygiene` esteso con frasi deontologiche bandite | P1 | dev | parziale (solo lessico tech) |
| P2-LEG-1 | Avvocato di riferimento per paese (FR/BE/MA/TN) | P2 | Studio | assente |
| P2-LEG-2 | Nota "courtesy translation, IT is binding" su privacy/disclaimer | P2 | dev | assente |
| P2-LEG-3 | Campo controparte nel form (per check conflitto interessi) | P2 | Studio + dev | assente |
| P3-LEG-1 | Pagina "Studio internazionale" con avvocati partner per paese | P3 | Studio | — |

---

## 12. Per Claude Code che prosegue

- **Mai** introdurre claim di risultato nei template senza che lo
  Studio firmi il copy.
- **Mai** committare numeri o nomi di clienti in esempi/casi pratici.
- Estensioni del form `ContactForm`/`*WizardForm` che raccolgono dati
  particolari **devono** aggiornare `ConsentPurpose` corrispondente
  e versionare il `ConsentTextVersion` nelle 4 lingue.
- Ogni nuovo template pubblico passa per `audit_public_content_hygiene.py`
  prima del merge.
- Quando si attiva una terza parte (Pexels live, Sentry, analytics,
  CRM esterno via webhook), aggiornare prima la privacy policy
  versionata e il cookie banner se applicabile.
