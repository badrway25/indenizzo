# LEGAL SIGNATURE PACK — TODO per lo Studio

**Data:** 2026-05-13
**Destinatario:** Studio Legale Internazionale Badrane
**Scopo:** lista operativa, in linguaggio non tecnico, di **cosa deve firmare lo Studio** prima del go-live e **cosa succede dopo la firma**.

> Questo documento non riscrive il contenuto legale. Non scrive testi
> al posto dello Studio. Si limita a **organizzare il processo** in modo
> che ogni firma trovi una casella tecnica corrispondente, e ogni
> casella tecnica abbia una verifica oggettiva.
>
> Niente nella piattaforma viene "fatto passare" come firmato finché
> lo Studio non firma davvero. Il sistema rifiuta lo start in produzione
> finché tutte le caselle sono in `working_copy`.

---

## 1. Quadro generale

La piattaforma raccoglie e tratta dati sensibili (salute, invalidità,
famiglia, reddito, decessi, procedimenti) e produce simulazioni
indicative. Tutto questo richiede 6 atti firmati dallo Studio prima
che la piattaforma possa andare in produzione pubblica.

| Atto | Cosa è | Chi firma | Frequenza |
|---|---|---|---|
| **1. Privacy policy** | Informativa GDPR completa in 4 lingue (IT/FR/EN/AR) | Titolare trattamento Studio | Una volta + revisione annuale |
| **2. Disclaimer** | Avviso che le simulazioni sono indicative e non parere legale | Avvocato responsabile | Una volta + revisione annuale |
| **3. Mandato professionale** | Template di incarico scritto cliente↔Studio | Avvocato responsabile | Una volta + revisione annuale |
| **4. Testo consenso GDPR art. 9** | Consenso esplicito al trattamento di dati particolari (salute, condanne, ecc.) | Avvocato responsabile | Una volta + per ogni cambio |
| **5. Retention policy** | Per ciascuna categoria di dato: quanti giorni li conserviamo, quando anonimizziamo, quando cancelliamo | DPO o avv. responsabile | Una volta + revisione annuale |
| **6. Identificativi professionali** | Nome avvocato, Ordine, P.IVA, PEC, sede, polizza RC | Titolare Studio | Una volta + se cambiano |

---

## 2. Per ciascun atto

### Atto 1 — Privacy policy

- **Cosa firma lo Studio:** il testo completo dell'informativa GDPR (art. 13) in **IT/FR/EN/AR**.
- **Dove si trova nel progetto:** `templates/public/privacy.html` (testo working-copy con banner).
- **Dopo la firma:** Studio comunica al dev:
  - data firma (ISO: `YYYY-MM-DD`)
  - "etichetta" versione (es. `2026-09-15-final`)
- **Dev imposta tre env vars in produzione:**
  ```
  PRIVACY_POLICY_VERSION=<etichetta>
  PRIVACY_POLICY_STATUS=signed
  PRIVACY_POLICY_SIGNED_AT=<data firma>
  ```
- **Cosa NON si può attivare prima:** `manage.py check` in `DEBUG=False` blocca lo start del server.
- **Check tecnico residuo:** `core.E006` (sblocco automatico una volta settate le 3 env).
- **Prova post-firma:**
  - Visita `/privacy/` → banner working-copy sparisce, badge "Signed `<data firma>`" visibile.
  - `manage.py check --deploy` non riporta `core.E006`.

### Atto 2 — Disclaimer

- **Cosa firma lo Studio:** il testo del disclaimer (le 8 sezioni della pagina `/disclaimer/`).
- **Dove si trova nel progetto:** `templates/public/disclaimer.html` (testo working-copy).
- **Dopo la firma:** Studio comunica:
  - data firma
  - etichetta versione
- **Dev imposta:**
  ```
  DISCLAIMER_VERSION=<etichetta>
  DISCLAIMER_STATUS=signed
  DISCLAIMER_SIGNED_AT=<data firma>
  ```
- **Cosa NON si può attivare prima:** start in prod.
- **Check tecnico residuo:** `core.E007`.
- **Prova post-firma:**
  - `/disclaimer/` mostra badge "Signed `<data firma>`".
  - `manage.py check --deploy` clean per E007.

### Atto 3 — Mandato professionale

- **Cosa firma lo Studio:**
  1. Il template del mandato (testo legale del documento che il cliente sottoscriverà per dare incarico allo Studio).
  2. Versioni in lingua (almeno IT; FR/EN/AR se l'incarico può essere accettato in quelle lingue).
- **Dove si trova nel progetto:** template **da fornire** dallo Studio (oggi NON esiste).
- **Dopo la firma:** Studio comunica al dev:
  - file PDF + versione testuale per ogni lingua
  - data firma del template
- **Dev fa:**
  1. Crea il record `compliance.MandateTemplateVersion` con `status=signed` per ogni lingua (via admin Django o data migration).
  2. Imposta env:
     ```
     MANDATE_TEMPLATE_VERSION=<etichetta>
     MANDATE_TEMPLATE_STATUS=signed
     MANDATE_TEMPLATE_SIGNED_AT=<data firma>
     REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=True
     ```
- **Cosa NON si può attivare prima:**
  - Start in prod (check `core.E008` blocca).
  - Promozione di un Lead a "pratica attiva" (il flag `mandate_signed` resta `False` finché il cliente non firma il proprio mandato individuale).
- **Check tecnico residuo:** `core.E008`.
- **Prova post-firma:**
  - `manage.py check --deploy` clean per E008.
  - Workflow di promozione Lead → pratica richiede `MandateAcceptance` con `accepted=True`.

### Atto 4 — Testo consenso GDPR art. 9

- **Cosa firma lo Studio:** il testo dei **due consensi** mostrati nei form pubblici (contact + wizard):
  1. Consenso art. 6 (trattamento generale dati personali per fornire il servizio).
  2. Consenso art. 9 (trattamento di dati particolari: salute, invalidità, procedimenti, ecc.).
- **Dove si trova nel progetto:** `templates/partials/consent_checkboxes.html` + traduzioni in `locale/{it,fr,en,ar}/LC_MESSAGES/django.po`.
- **Dopo la firma:** Studio comunica:
  - etichetta versione del testo finale (la stessa per i due o due distinte se preferisce).
- **Dev imposta:**
  ```
  PRIVACY_NOTICE_VERSION=<etichetta>
  SPECIAL_CATEGORIES_NOTICE_VERSION=<etichetta>
  ```
- **Effetto sul database:** ogni `ConsentRecord` creato da quel momento avrà `text_version = <etichetta>`. Lo storico precedente non viene riscritto: la piattaforma traccia ogni cambio.
- **Cosa NON si può attivare prima:** start in prod (check `core.E004`).
- **Check tecnico residuo:** `core.E004`.
- **Prova post-firma:**
  - Submit `/contact/` → record `ConsentRecord` ha `text_version` corretto.
  - `manage.py check --deploy` clean per E004.

### Atto 5 — Retention policy

- **Cosa firma lo Studio (decide):**

| Categoria dato | Domanda da rispondere | Suggerimento di partenza (NON è un parere legale) |
|---|---|---|
| **Lead** (richiesta di contatto, nome, email, telefono, messaggio) | Dopo quanti giorni anonimizziamo se nessuna conversione? | 365 giorni (default codice) |
| **Simulation** (input wizard, output calcolo, IP, UA, fonti) | Dopo quanti giorni anonimizziamo? | 365 giorni |
| **ConsentRecord** (atto di consenso) | Conservazione per prova storica? | 1825 giorni (5 anni, default codice) |
| **PrivacyAuditEvent** (log accessi/cambi) | Audit log lifetime? | 1825 giorni |

- **Dopo la firma:** Studio comunica:
  - giorni decisi per ciascuna categoria
  - etichetta versione policy
  - data firma
- **Dev imposta:**
  ```
  RETENTION_POLICY_VERSION=<etichetta>
  RETENTION_ENABLED=True
  RETENTION_MODE=anonymize
  RETENTION_LEAD_DAYS=<giorni>
  RETENTION_SIMULATION_DAYS=<giorni>
  RETENTION_CONSENT_RECORD_DAYS=<giorni>
  RETENTION_AUDIT_LOG_DAYS=<giorni>
  RETENTION_REQUIRE_SIGNED_VERSION=True
  ```
- **Dev schedula cron:**
  - Celery Beat o cronjob shell che esegue `python manage.py run_retention_policy` quotidianamente.
- **Cosa NON si può attivare prima:** start in prod (check `compliance.E001`).
- **Check tecnico residuo:** `compliance.E001`.
- **Prova post-firma:**
  - `python manage.py run_retention_policy --dry-run` produce log con candidati per ciascuna categoria.
  - `RetentionRunLog` registra l'esecuzione.
  - `manage.py check --deploy` clean per `compliance.E001`.

### Atto 6 — Identificativi professionali (footer obbligatorio)

- **Cosa fornisce lo Studio:**

| Campo | Esempio formato |
|---|---|
| Nome avvocato responsabile | `Avv. <Nome Cognome>` |
| Ordine di iscrizione | `Ordine degli Avvocati di <Città>` |
| Numero iscrizione (opt) | `<numero>` |
| Partita IVA | `IT<11 cifre>` (formato UE) |
| Codice Fiscale (opt) | `<16 caratteri>` |
| PEC ufficiale | `<studio>@pec.<dominio>` |
| Indirizzo fisico Studio | `Via X, n., CAP Città` |
| Compagnia assicurativa RC professionale | `<Compagnia>` |
| Numero polizza RC | `<numero>` |
| Massimale (opt) | `<importo>` |

- **Dev imposta nel secret store / env:**
  ```
  STUDIO_LEAD_LAWYER_NAME=...
  STUDIO_BAR_ASSOCIATION=...
  STUDIO_VAT_NUMBER=...
  STUDIO_PEC_EMAIL=...
  STUDIO_PHYSICAL_ADDRESS=...
  STUDIO_PROFESSIONAL_INSURANCE_INSURER=...
  STUDIO_PROFESSIONAL_INSURANCE_POLICY=...
  ```
- **Cosa NON si può attivare prima:** start in prod (check `core.E001`).
- **Check tecnico residuo:** `core.E001`.
- **Prova post-firma:**
  - `/` footer mostra dati reali (niente più placeholder `[da configurare prima del go-live]`).
  - `manage.py check --deploy` clean per E001.

---

## 3. Cosa rimane bloccato finché tutti gli atti non sono firmati

Riassunto delle 6 firme → 7 check Django (E001 conta come 1 blocco multi-campo):

| Check Django | Atto richiesto |
|---|---|
| `core.E001` | Atto 6 (identificativi footer) |
| `core.E002` | CSP enabled (tecnico, non Studio) |
| `core.E003` | CSP non report-only (tecnico) |
| `core.E004` | Atto 4 (consenso art. 9) |
| `core.E006` | Atto 1 (privacy policy) |
| `core.E007` | Atto 2 (disclaimer) |
| `core.E008` | Atto 3 (mandato) |
| `compliance.E001` | Atto 5 (retention) |
| `crm.E001` | Lead notification recipient (tecnico) |

Finché anche **uno solo** di questi check è rosso, `manage.py check` in `DEBUG=False` fallisce e il server non parte in produzione.

---

## 4. Prove tecniche da fare DOPO le firme

Dopo che lo Studio comunica le firme e il dev imposta gli env, eseguire (su staging):

1. **System check pulito:**
   ```
   DJANGO_DEBUG=False python manage.py check --deploy
   ```
   Atteso: `System check identified no issues (0 silenced).`

2. **Migrazioni:**
   ```
   python manage.py makemigrations --check --dry-run
   ```
   Atteso: `No changes detected`.

3. **Test suite:**
   ```
   pytest -q
   ```
   Atteso: `2148+ passed`.

4. **Canarino IT live:**
   ```
   curl -s https://<staging-host>/wizard/it/road-accident/ -o /dev/null -w "%{http_code}\n"
   # poi simulazione 35/10/0 → expected 26268/27353/28439 EUR
   ```

5. **Verifica visiva /privacy/, /disclaimer/:**
   - Badge "Signed `<data>`" visibile.
   - Banner working-copy non più visibile.
   - Versione mostrata = versione comunicata dallo Studio.

6. **Verifica visiva footer:**
   - Tutti i dati Studio reali presenti.
   - Nessun `[da configurare prima del go-live]`.

7. **Submit /contact/:**
   - Form salvato come Lead.
   - `ConsentRecord` ha `text_version` = etichetta firmata.
   - Mail arriva a `LEAD_NOTIFICATION_TO_EMAILS`.

8. **Retention dry-run:**
   ```
   python manage.py run_retention_policy --dry-run
   ```
   Atteso: log con conteggio candidati per scope, status=SUCCESS, `RetentionRunLog` creato.

---

## 5. Cosa lo Studio NON deve fare

- **Non comunicare etichette versione che contengono `working-copy`, `draft`, `provisional`, `bozza`**: i check le rifiutano per design.
- **Non chiedere al dev di "bypassare temporaneamente" un check**: il sistema è progettato perché non sia possibile.
- **Non firmare un testo legale che non si ha intenzione di onorare**: il sistema traccia chi ha approvato cosa e quando (`LegalReview`, `MandateAcceptance`).

---

## 6. Sequenza operativa consigliata

Per evitare di tornare in produzione due volte:

1. **Studio prepara in parallelo** i 6 atti (1-4 settimane lato Studio).
2. **Comunicazione coordinata al dev**: una sola email/incontro in cui Studio passa al dev tutti i dati / etichette / date / file PDF mandato.
3. **Dev imposta tutti gli env in un unico file `.env.production`** (mai committato).
4. **Dev esegue le 8 prove post-firma** su staging.
5. **Se tutto verde → deploy in produzione.** Altrimenti: feedback al Studio + iterare.

---

## 7. Documenti correlati

- `docs/go_live/GO_LIVE_READINESS_MATRIX_2026-05-13.md` — vista 20 aree.
- `docs/go_live/ENV_CONTRACT_GO_LIVE.md` — contratto env vars.
- `docs/PRODUCTION_ENV_REQUIRED_VARS.md` — fonte canonica env.
- `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md` — audit deontologico completo.
- `docs/GO_LIVE_GATE_CHECKLIST.md` — gate check 13 sezioni pre-deploy.
