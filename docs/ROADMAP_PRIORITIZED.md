# ROADMAP PRIORITIZED — Indennizzati / Studio Legale Badrane

**Data:** 2026-05-10
**Tipo:** vista P0–P5 derivata da `docs/architecture/LOCAL_NEXT_STEPS.md`.
**Scopo:** raggruppare il backlog cross-cutting per **livello di
urgenza** (anziché per fase paese-per-paese), così che Studio e dev
possano scegliere il prossimo batch senza dover ricucire 7 audit.

> Roadmap canonica paese-per-paese: `docs/architecture/LOCAL_NEXT_STEPS.md`
> (Fasi A → E). Questa vista è una **trasformazione**: stessa sostanza,
> ordinata per impatto.

---

## 0. Mapping P-level ↔ Fase canonica

| P-level | Fase canonica | Significato |
|---|---|---|
| **P0** | "Bloccanti pre-uso pubblico" | Senza questi, **non si può** dare il sito a un collaboratore reale |
| **P1** | Fase A + B + alcune voci D | Importanti per qualità prodotto pre-go-live |
| **P2** | Fase D | Hardening prodotto post primo paese non-IT |
| **P3** | Fase E + post-MVP | Multi-lingua premium, espansione contenuti |
| **P4** | post-MVP avanzato | Multi-country (oltre IT/FR/BE/MA/TN) |
| **P5** | "Ultra premium" | Area cliente, upload sicuro, firma incarico, dashboard interna |

---

## 1. P0 — Pre go-live (bloccanti)

> **2026-05-10 — Stato P0**: tutto il lato tecnico è chiuso e tutto
> il lato legale è scaffoldato (codice in linea, default working-copy,
> system check blocca produzione finché lo Studio firma). Vedi
> `docs/P0_TECHNICAL_CLOSURE_2026-05-10.md` per il consolidato.
> Le righe sotto mostrano lo stato finale.

### 1.1 P0 sicurezza/tecnico (vedi `SECURITY_INDEX.md`)

| ID | Voce | Stato | Commit / Note |
|---|---|---|---|
| P0-SEC-1 | Content-Security-Policy emessa (django-csp o reverse proxy) | ✅ CHIUSO | `d2bd12b` (P0-CODICE-4): django-csp 4.x + nonce + `core.E002/E003` |
| P0-SEC-2 | Django system check su `LEAD_NOTIFICATION_TO_EMAILS=[]` | ✅ CHIUSO | `b45ec5d` (P0-CODICE-1): `crm.E001` |

### 1.2 P0 deontologia/legale (vedi `LEGAL_COMPLIANCE_CONTENT_AUDIT.md`)

| ID | Voce | Stato | Commit / Note |
|---|---|---|---|
| P0-LEG-1 | Privacy policy completa firmata, in 4 lingue, versionata | ✅ scaffold (firma Studio in attesa) | `0431ce1` — `core.E006` blocca prod |
| P0-LEG-2 | Modello mandato professionale + flow `mandate_signed` | ✅ scaffold (firma Studio in attesa) | `96e9320` — `core.E008` blocca prod |
| P0-LEG-3 | Doppio consenso (GDPR art. 6 + art. 9) per dati particolari nel wizard | ✅ scaffold (firma Studio in attesa) | `d57a22d` — `core.E004` blocca prod |
| P0-LEG-4 | Retention policy firmata + cron implementato | ✅ scaffold (firma Studio in attesa) | `88a6f9e` — `compliance.E001` blocca prod |
| P0-LEG-5 | Identificativi professionali nel footer (Ordine, P.IVA, PEC, polizza) | ✅ scaffold (dati Studio in attesa) | `5fe7e11` — `core.E001` blocca prod |
| P0-LEG-6 | Disclaimer firmato | ✅ scaffold (firma Studio in attesa) | `0431ce1` — `core.E007` blocca prod |

### 1.3 P0 SEO (vedi `SEO_AUDIT_AND_CONTENT_ARCHITECTURE.md`)

| ID | Voce | Stato | Commit / Note |
|---|---|---|---|
| P0-SEO-1 | `robots.txt` servito | ✅ CHIUSO | `b45ec5d` |
| P0-SEO-2 | `noindex` su `/wizard/result/<uuid>/` e `/contact/thank-you/` | ✅ CHIUSO | `b45ec5d` |
| P0-SEO-3 | hreflang globale (oltre 5 country landings) | ✅ CHIUSO | `1b2cfbc` |

### 1.4 P0 multi-paese (vedi `MULTI_COUNTRY_PATTERN.md` Sez. 4)

| ID | Voce | Effort | Owner |
|---|---|---|---|
| P0-MVP-1 | Almeno **un caso d'uso non-IT** end-to-end verde in staging | XL | Studio + dev |

> ↑ vincolo cardinale di `LOCAL_NEXT_STEPS.md` Sez. 0. Sblocco
> dipende dal completamento di un ramo qualunque tra:
>
> - FR road accident: post Studio review checklist Mornet+Gazette;
> - BE road accident: post Studio review checklist + decisione
>   B2 (esthétique vs forfait), B4 (formula camions);
> - MA inheritance: post mapping firmato Moudawana;
> - TN inheritance: post mapping firmato CSP + decisione DIP
>   doppia regola di conflitto.

**Dipendenza esterna**: lo Studio compila i 4 review package
(`docs/legal_sources/<COUNTRY>_LEGAL_REVIEW_PACKAGE.md`) riga per
riga. Niente codice dev può sbloccare questo P0 senza la firma
Studio.

### 1.5 P0 closure recap

Tutti i P0 dev-side sono chiusi al **2026-05-10**. Per andare in
produzione servono solo le firme Studio (vedi
`docs/STUDIO_SIGNOFF_ACTION_PACK.md`) e la valorizzazione delle env
var (`docs/PRODUCTION_ENV_REQUIRED_VARS.md`). La checklist
operativa è in `docs/GO_LIVE_GATE_CHECKLIST.md`.

**Prossimo batch consigliato**: `P1-CRM-1..7` (webhook firmato HMAC +
n8n workflow) oppure `P1-LEG-1` (Google Fonts locali per chiudere il
debito CSP-via-CDN). Scelta operativa allo Studio.

---

## 2. P1 — Importanti per qualità prodotto

### 2.1 P1 — Hardening sicurezza/privacy

| ID | Voce | Effort | Doc canonico |
|---|---|---|---|
| P1-SEC-1 | Cookie banner: piano per consent manager opt-in se si attivano tracker | S | `LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 2.7 |
| P1-LEG-1 | Google Fonts hostati localmente | S | `LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 4 |
| P1-LEG-2 | Estendere `audit_public_content_hygiene.py` con frasi deontologiche bandite | S | `LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 3 |
| P1-SEC-3 | WAF/CDN/edge security in prod (Cloudflare / Caddy + CrowdSec) | M | `SECURITY_INDEX.md` Sez. 4.5 |

### 2.2 P1 — Integrazione CRM (vedi `CRM_INTEGRATION_PLAN.md`)

| ID | Voce | Effort | Note |
|---|---|---|---|
| P1-CRM-1 | `LeadWebhookDelivery` model + migration | S | |
| P1-CRM-2 | Webhook dispatcher firmato HMAC | M | |
| P1-CRM-3 | Celery task con retry esponenziale (5 × 60s con jitter) | S | |
| P1-CRM-4 | Idempotency-key stabile per delivery | S | |
| P1-CRM-5 | n8n workflow template + runbook | M | |
| P1-CRM-6 | Privacy policy aggiornata con elenco trasferimenti | S | dipende da scelta CRM |
| P1-CRM-7 | DPA firmato con CRM esterno (se non self-hosted) | M | dipende da scelta CRM |

### 2.3 P1 — SEO

| ID | Voce | Effort | Doc |
|---|---|---|---|
| P1-SEO-1 | Sitemap multi-lingua espansa (48 entry) | S | `SEO_AUDIT_AND_CONTENT_ARCHITECTURE.md` Sez. 2.4 |
| P1-SEO-2 | Lighthouse gating CI | M | idem Sez. 2.5 |
| P1-SEO-3 | Schema `BreadcrumbList`, `FAQPage` | S | idem Sez. 2.6 |
| P1-SEO-4 | `theme-color`, `application-name` | XS | idem Sez. 2.7 |
| P1-SEO-5 | Google Search Console + Bing Webmaster | S | idem Sez. 2.8 |
| P1-SEO-6 | Performance budget + CI gating | M | idem Sez. 2.9 |

### 2.4 P1 — Engine

| ID | Voce | Effort |
|---|---|---|
| P1-ENG-1 | Decidere `IT/inheritance_basic`: implementare o de-registrare | M |
| P1-ENG-2 | Tabelle Tribunale Milano 2024 IT promosse o restano `needs_review` | L |

### 2.5 P1 — Infrastruttura

| ID | Voce | Effort |
|---|---|---|
| P1-INFRA-1 | `legal_data/` con `.gitkeep` + struttura placeholder + runbook esteso | XS |
| P1-INFRA-2 | Apps placeholder vuote (`inheritance`, `cms_content`, `analytics`): scoping (rimuovere o pianificare) | S |

---

## 3. P2 — Polish post primo paese non-IT verde

| ID | Voce | Effort | Doc |
|---|---|---|---|
| P2-UX-1 | Cookie banner sovrapposizione mobile @ 375 px | XS | `PRODUCT_RELEASE_READINESS_AUDIT_PASS1.md` |
| P2-UX-2 | AR/RTL typography weight tune-up | XS | idem |
| P2-UX-3 | Crop foto hero TN/MA standardizzati | XS | idem |
| P2-UX-4 | Banner FR/BE wizard "Run simulation" → "Submit for legal review" | XS | `PUBLIC_FUNNELS_UX_AUDIT.md` |
| P2-UX-5 | Sezione FAQ per paese in country landing | M | `SEO_AUDIT_AND_CONTENT_ARCHITECTURE.md` Sez. 4.2 |
| P2-LEG-1 | Avvocato di riferimento per paese (FR/BE/MA/TN) | S | `LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 11 |
| P2-LEG-2 | Nota "courtesy translation, IT is binding" su privacy/disclaimer | XS | idem |
| P2-LEG-3 | Campo controparte nel form (per check conflitto interessi) | S (decisione Studio) | idem Sez. 6 |
| P2-CRM-1 | WhatsApp Business "Acknowledge" template | M | `CRM_INTEGRATION_PLAN.md` Sez. 5 |
| P2-CRM-2 | Reverse webhook `lead.updated` (CRM→Django) | M (DA DECIDERE STUDIO) | idem Sez. 7 |
| P2-CRM-3 | Propagazione `lead.deleted` ai webhook (GDPR art. 17) | M | idem Sez. 8.3 |
| P2-SEC-1 | Pen-test esterno | L (procurement) | `SECURITY_INDEX.md` |
| P2-SEC-2 | Account lockout admin (estensione di pass 9) | M | idem |
| P2-SEC-3 | 2FA per ruoli client/lawyer | M | idem |
| P2-SEO-1 | Leaf pages country × case-type (es. `/it/italia/incidente-stradale/`) | M | `SEO_AUDIT_AND_CONTENT_ARCHITECTURE.md` Sez. 3.5 |
| P2-SEO-2 | Topic pages pivot (TUN 2025, Loi Badinter, Mornet, Moudawana, …) | L | idem Sez. 4.3 |
| P2-SEO-3 | FAQ globale `/it/faq/` | M | idem Sez. 4.1 |
| P2-SEO-4 | Glossario `/it/glossary/...` | M | idem Sez. 4.4 |
| P2-ENG-1 | Consolidamento test `_passN` dispersi | M | nessun blocco di prodotto |

---

## 4. P3 — Multi-lingua premium e espansione editoriale

| ID | Voce | Effort | Note |
|---|---|---|---|
| P3-I18N-1 | Compilazione `.po` definitive in 4 lingue (traduzioni firmate Studio) | L | dipende da scelta traduttore professionale |
| P3-I18N-2 | Coerenza terminologia legale cross-lingua (glossario tecnico bilingue) | L | |
| P3-CONTENT-1 | Attivazione `apps.cms_content/` (oggi placeholder) | L | `apps/cms_content/` da modellare |
| P3-CONTENT-2 | Blog 1 articolo/settimana con autori avvocati | continuativo | richiede `apps.cms_content/` ready |
| P3-CONTENT-3 | RSS / Atom feed | S | dopo `cms_content` |
| P3-CONTENT-4 | Sitemap-html per umani | S | |
| P3-UX-1 | Animazioni micro-interaction premium (rispettando `prefers-reduced-motion`) | M | |
| P3-A11Y-1 | WCAG 2.2 AA full audit | L | |

---

## 5. P4 — Multi-country oltre MVP

| ID | Voce | Effort | Note |
|---|---|---|---|
| P4-COUNTRY-1 | Spagna (incidente stradale + responsabilità medica) | XL | Baremo Tabular |
| P4-COUNTRY-2 | Germania (incidente stradale) | XL | StVG, Schmerzensgeldtabelle |
| P4-COUNTRY-3 | Romania (incidente stradale per cittadini RO in IT/FR) | L | |
| P4-COUNTRY-4 | Algeria (successioni internazionali) | L | |
| P4-COUNTRY-5 | Egitto (successioni internazionali) | L | |
| P4-COUNTRY-6 | Canada (Quebec) | L | |
| P4-CASE-1 | Responsabilità medica IT (case_type `medical_malpractice`) | XL | post P0-MVP-1 |
| P4-CASE-2 | Infortunio sul lavoro IT (case_type `workplace_injury`) | XL | INAIL differenziale |
| P4-CASE-3 | Danno da decesso / parentale IT | XL | tabelle Milano |

Stima: ogni nuovo paese o case_type è un blocco di 4-8 settimane
calendar (dipende da Studio review).

---

## 6. P5 — Ultra premium (post-MVP, area cliente)

| ID | Voce | Effort | Note |
|---|---|---|---|
| P5-CLIENT-1 | Area cliente autenticata | XL | login client + dashboard |
| P5-CLIENT-2 | Upload documenti sicuro (mime whitelist + AV scan) | L | |
| P5-CLIENT-3 | Firma incarico online (eIDAS qualified signature?) | XL | depend on signature provider |
| P5-CLIENT-4 | Tracking pratica (stato + timeline visibile cliente) | L | |
| P5-CLIENT-5 | Notifiche (email / WhatsApp Business / SMS) | M | post P2-CRM-1 |
| P5-CLIENT-6 | Pagamenti / fatturazione | XL | normalmente fuori scope |
| P5-ANALYTICS-1 | Dashboard interna KPI lead/giorno (oggi `apps.analytics` placeholder) | L | |
| P5-ANALYTICS-2 | Reportistica cliente (PDF mensile attività) | L | |

> P5 è esplicitamente **out-of-scope MVP** in
> `LOCAL_NEXT_STEPS.md` Sez. 6. Tracciato qui per memoria.

---

## 7. Effort code

- **XS** ≤ 2 ore
- **S** ≤ 1 giorno
- **M** ≤ 1 settimana
- **L** ≤ 1 mese
- **XL** > 1 mese

Stime indicative dev-side. Effort Studio (review legale, mapping,
firma) è in molti casi il bottleneck reale, non il codice.

---

## 8. Sequenza consigliata (next 30/60/90 giorni)

### 8.1 Sprint 1 (0-30 giorni) — Sblocco go-live tecnico

Obiettivo: **chiudere tutti i P0 tecnici** (P0-SEC-1, P0-SEC-2,
P0-SEO-1, P0-SEO-2, P0-SEO-3, P0-LEG-5) entro 30 giorni.

In parallelo, lo Studio inizia il review FR (la più matura per
dataset).

**Deliverable Sprint 1**:

- CSP attivo;
- `manage.py check --deploy` clean;
- `robots.txt` + `noindex` su pagine sensibili;
- hreflang globale;
- footer con identificativi professionali;
- IT canarino verde 35/10/0 (canarino sempre).

### 8.2 Sprint 2 (30-60 giorni) — Sblocco go-live legale

Obiettivo: **chiudere i P0 deontologici** (P0-LEG-1, P0-LEG-3,
P0-LEG-4, P0-LEG-6).

- privacy policy completa firmata;
- doppio consenso art. 6 + art. 9;
- retention cron implementato;
- disclaimer firmato.

In parallelo, lo Studio completa review FR e/o BE.

### 8.3 Sprint 3 (60-90 giorni) — Primo paese non-IT verde

Obiettivo: **P0-MVP-1**. Implementare engine FR (o BE) reale post
review Studio.

- import dataset FR approved;
- calculator FR REAL (override `_compute_with_sources`);
- wizard FR funzionante;
- test E2E + Lighthouse + screenshot;
- staging deploy con feature flag FR enabled.

### 8.4 Sprint 4+ — Hardening + integrazione + go-live

P1 in batch (CRM webhook, n8n, P0-LEG-2 mandato professionale,
ecc.). Quindi go-live in produzione.

---

## 9. Cosa NON è in roadmap (espliciti out-of-scope MVP)

Da `LOCAL_NEXT_STEPS.md` Sez. 6:

- ❌ Calcolatori pluri-giurisdizione automatici (es. successioni
  con asset in IT + MA + FR contemporaneamente). Resta caso
  "richiede consulenza" finché Studio non valida la combinazione.
- ❌ Integrazione real-time con sistemi assicurativi / database
  pubblici.
- ❌ Pagamenti / fatturazione (Studio gestisce offline).
- ❌ Mobile app nativa.
- ❌ Calcolatori per casi che richiedono perizia medica
  obbligatoria (devono restare scaffold con `missing_documents`).

---

## 10. Per Claude Code che riprende la roadmap

- **Mai** saltare P0 per accelerare un P1.
- Ogni iter chiude con il canarino IT 35/10/0 verde.
- Aggiornare questa roadmap (e `LOCAL_NEXT_STEPS.md`) quando un
  P0/P1 viene chiuso o quando emerge un nuovo gap.
- Le decisioni "DA VALIDARE STUDIO" (CRM target, hosting n8n,
  WhatsApp sì/no, sincronizzazione bidirezionale, ecc.) sono
  bottleneck non tecnici: tracciarle separatamente, non
  bloccare il dev se possono essere implementate dietro flag
  opt-in.
- Quando si propone un nuovo iter, dichiarare a quale P-level
  appartiene e quale dipendenza chiude.
