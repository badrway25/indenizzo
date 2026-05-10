# Studio sign-off action pack

**Per**: Studio Legale Internazionale Badrane
**Da**: dev team
**Data**: 2026-05-10
**Stato piattaforma**: P0 tecnico chiuso, in attesa firma Studio per go-live.

---

## In una pagina

La piattaforma è tecnicamente pronta per andare in produzione, ma per
**rispetto della deontologia forense** rifiuta di partire finché lo
Studio non firma i testi legali e fornisce i dati professionali
obbligatori. Questo documento elenca esattamente cosa serve, suddiviso
in 8 sezioni. Nessuna sezione è opzionale: il sistema blocca il deploy
finché tutte sono complete.

Per ogni sezione indichiamo:

- **Cosa serve**: il contenuto che lo Studio deve fornire o firmare.
- **Versione**: l'etichetta firmata che resterà tracciata in audit.
- **Lingue**: dove serve traduzione.
- **Effetto se manca**: quale parte della piattaforma resta bloccata.

Quando una sezione è chiusa, il team tecnico imposta la corrispondente
env var (vedi `docs/PRODUCTION_ENV_REQUIRED_VARS.md`) e il system
check sblocca il deploy.

---

## 1. Identificativi professionali per il footer

**Riferimento normativo**: art. 17-bis Cod. deontologico forense, D.Lgs.
70/2003 art. 7, L. 247/2012 art. 12.

Lo Studio deve fornire:

| Campo | Esempio | Obbligatorio P0 |
|---|---|---|
| Nome avvocato responsabile della piattaforma | "Avv. Mario Rossi" | ✅ |
| Ordine di appartenenza | "Ordine degli Avvocati di Milano" | ✅ |
| Numero iscrizione (Albo) | "12345" | ⚪ raccomandato (esposto se disponibile) |
| Partita IVA | "IT01234567890" | ✅ |
| Codice fiscale | "RSSMRA80A01H501Z" | ⚪ raccomandato |
| PEC ufficiale | "studio.badrane@pec.example.it" | ✅ |
| Indirizzo studio fisico | "Via Tale 1, 20100 Milano" | ✅ |
| Compagnia assicuratrice RC professionale | "Generali Italia SpA" | ✅ |
| Numero polizza | "POL-IT-987654" | ✅ |
| Massimale polizza | "€ 5.000.000" | ⚪ raccomandato |

**Effetto se manca**: footer mostra `[da configurare prima del
go-live]` in posizione di ogni campo vuoto. In produzione il check
`core.E001` blocca `manage.py check` finché tutti i 7 campi
obbligatori sono valorizzati.

---

## 2. Privacy policy finale (pagina /privacy/)

**Stato attuale**: la pagina `/privacy/` mostra una versione
**working-copy** strutturata in 9 sezioni (titolare, dati raccolti,
categorie particolari art. 9, basi giuridiche, retention, diritti
dell'interessato, condivisione, versioni del consenso usate dalla
piattaforma, contatto). Il testo è un placeholder ragionato, non un
testo legale firmato.

Lo Studio deve fornire:

- **Testo definitivo** delle 9 sezioni, riveduto e firmato.
- **Versione**: stringa stabile, es. `2026-09-15-final`.
- **Data firma**: data ISO, es. `2026-09-15`.
- **Lingue richieste**: `it` (binding), `fr`, `en`, `ar` (courtesy
  translations). Il dev team applica le traduzioni alle stringhe
  `gettext` corrispondenti.

**Effetto se manca**: pagina `/privacy/` mostra il banner arancione
"Working copy". Check `core.E006` blocca produzione.

---

## 3. Disclaimer finale (pagina /disclaimer/)

**Stato attuale**: la pagina `/disclaimer/` mostra una versione
**working-copy** in 9 sezioni che coprono i punti deontologici
richiesti (natura informativa, no consulenza automatica, no garanzia
di risultato, range indicativi, fonti delle tabelle, incarico solo
con accordo scritto, indipendenza professionale, dati e
riservatezza, gestione internazionale).

Lo Studio deve fornire:

- **Testo definitivo** delle 9 sezioni, riveduto e firmato.
- **Versione**: es. `2026-09-15-final`.
- **Data firma**: es. `2026-09-15`.
- **Lingue richieste**: `it` (binding), `fr`, `en`, `ar`.

**Effetto se manca**: pagina `/disclaimer/` mostra il banner
arancione "Working copy". Check `core.E007` blocca produzione.

---

## 4. Consenso GDPR art. 6 (privacy base) — testo della checkbox

**Riferimento normativo**: GDPR art. 6.1.b (misure precontrattuali).

**Stato attuale**: ogni form pubblico (`/contact/`, 4 wizard) mostra
una checkbox obbligatoria con il testo working-copy:

> "Ho letto e accetto l'informativa sulla privacy."

Lo Studio deve fornire:

- **Testo definitivo della checkbox** — la formulazione precisa che
  il cliente accetta. Inclusi i link da puntare (privacy policy
  signed).
- **Versione**: es. `2026-09-15-final`. Il sistema salva questa
  versione su ogni `Lead.privacy_consent_version` e
  `Simulation.privacy_consent_version` in DB, e su ogni
  `ConsentRecord.text_version`.
- **Lingue**: `it` (binding), `fr`, `en`, `ar`.

**Effetto se manca**: ogni submit registra la versione "working-copy"
in DB; la prova del consenso non è probatoria. Check `core.E004`
blocca produzione.

---

## 5. Consenso GDPR art. 9 (categorie particolari) — testo della checkbox

**Riferimento normativo**: GDPR art. 9.2.a (consenso esplicito per
dati sanitari, eventi familiari, procedimenti giudiziari).

**Stato attuale**: testo working-copy:

> "I expressly consent to the processing of special categories of
> personal data (health, family events, judicial proceedings) under
> GDPR art. 9.2.a, for the sole purpose of replying to this request."

Questa è una checkbox **separata** dalla precedente — l'art. 9
richiede consenso *esplicito* e distinto dal consenso art. 6.

Lo Studio deve fornire:

- **Testo definitivo italiano** (vincolante), poi traduzioni.
- **Versione**: es. `2026-09-15-final`.
- **Lingue**: `it`, `fr`, `en`, `ar`.

**Effetto se manca**: stesso `core.E004` blocca produzione.

---

## 6. Retention policy

**Stato attuale**: scaffold tecnico pronto. Il sistema è in modalità
**dry_run**: conta candidati senza modificare nulla. I numeri di
default (Lead 365 giorni, Simulation 365 giorni, ConsentRecord 1825
giorni, Audit log 1825 giorni) sono **valori di sviluppo, non parere
legale**.

Lo Studio deve fornire (in coordinamento con DPO se nominato):

- **Versione policy**: es. `2026-09-15-final`.
- **Giorni di retention per scope**:
  - `Lead` (richieste contatto): ___ giorni → poi anonymize
  - `Simulation` (input wizard): ___ giorni → poi anonymize
  - `ConsentRecord` (registro consensi): ___ giorni (tipicamente
    coincide con il periodo di prescrizione delle azioni
    contrattuali / dell'audit GDPR)
  - `PrivacyAuditEvent` (registro accessi): ___ giorni
- **Modalità**: `dry_run` (conta, non agisce), `anonymize` (oscura
  PII, mantiene audit trail), `delete` (cancellazione fisica). Per
  scope diversi puoi avere modalità diverse: documenta la scelta.
- **Firma**: la policy va firmata e archiviata con il resto della
  documentazione GDPR.

**Effetto se manca**: il management command
`run_retention_policy` rifiuta di girare in modalità diversa da
`dry_run`. In produzione il check `compliance.E001` blocca il
deploy se la policy contiene `working-copy`.

> **Importante**: in P0 il `delete` fisico di `Lead` / `Simulation`
> è **doppiamente bloccato**: serve sia `--yes-i-understand` sia
> `--allow-delete`. `ConsentRecord` e `PrivacyAuditEvent` non
> vengono mai cancellati automaticamente. Quando lo Studio firma la
> policy può chiedere al dev team di abilitare scope-by-scope.

---

## 7. Mandato professionale (template)

**Stato attuale**: scaffold tecnico pronto. Il sistema:

- separa `Lead` (richiesta in entrata, **pre-contrattuale**) da
  `Lead.mandate_signed=True` (incarico professionale firmato);
- mostra in ogni `/contact/thank-you/` e `/wizard/result/<uuid>/`
  un riquadro "Professional engagement" che ribadisce: la
  valutazione preliminare non costituisce incarico, l'incarico
  richiede accordo scritto separato (mandato);
- espone in admin il fieldset "Mandate (professional engagement)";
- offre la guard `assert_mandate_signed_for_case_activation(lead)`
  che ogni futuro flow di promozione lead → pratica deve chiamare.

Lo Studio deve fornire:

- **Template definitivo del mandato professionale**. Può essere PDF
  fornito al cliente offline + workflow Studio, oppure (in futuro)
  flusso di firma online. P0 supporta lo scenario offline.
- **Versione**: es. `2026-09-15-final`.
- **Data firma del template** (ovvero: quando lo Studio ha
  approvato la versione corrente del testo, non ogni singola firma
  cliente): es. `2026-09-15`.
- **Processo di firma**: lo Studio sceglie tra
  - `manual` — staff inserisce la firma manualmente in admin;
  - `upload` — cliente carica scan firmato (richiede sviluppo P5);
  - `external_signature` — provider terzo (richiede sviluppo P5);
  - `staff` — firma offline registrata da staff dopo riunione
    (raccomandato per P0).

**Effetto se manca**: il riquadro mandate notice mostra il banner
arancione working-copy. Check `core.E008` blocca produzione.

---

## 8. Review legale di almeno un paese non-IT

**Stato attuale**: l'unico calcolatore reale e attivo è quello
italiano (D.P.R. 12/2025 — danno biologico). Per FR, BE, MA, TN il
sistema mostra coerentemente `unavailable_requires_legal_validation`,
con il messaggio:

> "Il calcolo per questa giurisdizione non è ancora disponibile
> perché richiede validazione legale."

I review package sono pronti in
`docs/legal_sources/<COUNTRY>_LEGAL_REVIEW_PACKAGE.md`. Per ogni
paese che lo Studio sceglie di attivare prima del go-live, va
firmato:

| Paese | Materia | Doc |
|---|---|---|
| 🇫🇷 Francia | Incidenti stradali (Loi Badinter, Mornet, Gazette du Palais) | `docs/legal_sources/FRANCE_LEGAL_REVIEW_PACKAGE.md` |
| 🇧🇪 Belgio | Incidenti stradali (Indicative Tabel) | `docs/legal_sources/BELGIUM_LEGAL_REVIEW_PACKAGE.md` |
| 🇲🇦 Marocco | Successioni (Moudawana) | `docs/legal_sources/MOROCCO_LEGAL_REVIEW_PACKAGE.md` |
| 🇹🇳 Tunisia | Successioni (CSP — Code du statut personnel) | `docs/legal_sources/TUNISIA_LEGAL_REVIEW_PACKAGE.md` |

Per ogni paese scelto, lo Studio deve:

- approvare le fonti normative usate (status `approved`);
- approvare la formula di calcolo (status `approved`);
- approvare i casi d'uso supportati;
- approvare il disclaimer specifico per paese.

**Effetto**: il vincolo del CLAUDE.md ("almeno un caso d'uso non-IT
verde end-to-end" in `LOCAL_NEXT_STEPS.md` Sez. 0) viene sciolto al
primo paese firmato.

---

## Checklist di consegna allo Studio

Quando lo Studio rimanda al team tecnico:

- [ ] 7 campi STUDIO_* obbligatori valorizzati;
- [ ] testo privacy policy firmato + versione + data;
- [ ] testo disclaimer firmato + versione + data;
- [ ] testo checkbox art. 6 firmato + versione (4 lingue);
- [ ] testo checkbox art. 9 firmato + versione (4 lingue);
- [ ] retention policy firmata: versione + giorni per scope +
      modalità per scope;
- [ ] template mandato professionale firmato + versione + data +
      processo di firma scelto;
- [ ] almeno un paese non-IT approvato (FR/BE/MA/TN).

Il team tecnico:

1. setta tutte le env var (vedi
   `docs/PRODUCTION_ENV_REQUIRED_VARS.md`);
2. lancia la traduzione `.po` per le 4 lingue;
3. corre la `docs/GO_LIVE_GATE_CHECKLIST.md`;
4. deploy.

---

## Cosa il team tecnico **non** può fare al posto dello Studio

- Inventare dati professionali (Ordine, P.IVA, polizza).
- Firmare un testo legale al posto dello Studio.
- Decidere giorni di retention (è una decisione legale).
- Approvare fonti FR/BE/MA/TN (richiede valutazione di un
  avvocato del Foro o consulente).
- Decidere il processo di firma del mandato.

Tutto il resto (scaffold, system check, audit trail, test) è
chiuso e pronto.
