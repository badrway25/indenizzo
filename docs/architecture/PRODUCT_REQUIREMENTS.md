# Product Requirements — Studio Legale Badrane LegalTech Platform

Documento canonico dei requisiti di prodotto. Estende e si coordina con
`CLAUDE.md` (regole operative). In caso di conflitto, prevale qui.

Aggiornato: 2026-04-26.

---

## REQ-1 — Multilingua obbligatorio

La piattaforma è multilingua **by design**. Non è un'opzione aggiungibile
in seguito.

Lingue ufficiali (ordine di priorità):

1. `it` — italiano
2. `fr` — francese
3. `en` — inglese
4. `ar` — arabo (RTL)

Implicazioni vincolanti:

- ogni pagina pubblica è traducibile;
- ogni testo legale e disclaimer ha versioni per lingua;
- ogni consenso GDPR è versionato per lingua (`ConsentTextVersion.language`);
- ogni report PDF è generabile nella lingua scelta dall'utente;
- ogni fonte legale dichiara la lingua originale (`LegalSource.language`);
- il frontend supporta RTL per arabo (test visuale obbligatorio in F7);
- gli URL pubblici hanno prefisso lingua: `/it/`, `/fr/`, `/en/`, `/ar/`;
- usare `LANGUAGES` Django (già configurato in `config/settings.py`);
- `locale/` è popolato e committato;
- mai stringhe hardcoded non traducibili nei template;
- usare `{% trans %}`, `{% blocktranslate %}`, `gettext_lazy` ovunque;
- nei modelli con contenuti pubblici prevedere campi traducibili o
  modello collegato per lingua (preferito: modello collegato, vedi
  pattern `ConsentTextVersion`).

Non è obbligatorio tradurre tutto subito. È obbligatorio che ogni scelta
architetturale sia compatibile con traduzione futura senza refactor pesante.

---

## REQ-2 — Design premium, moderno, elegante

Identità visiva: studio legale internazionale premium.

Aggettivi guida: sobrio, autorevole, moderno, elegante, professionale,
rassicurante, mobile-first, accessibile.

Palette consigliata:

- blu notte (primario);
- oro sobrio (accenti, mai sfondo grande);
- bianco caldo;
- grigio pietra;
- verde solo per stati positivi.

Da evitare in modo assoluto:

- stile assicurazione aggressiva;
- stile startup/giocattolo;
- promesse di risultato ("ottieni subito X €");
- colori troppo saturi;
- copy sensazionalistico.

La UI definitiva è F7. Da subito ogni template, form, naming e flusso
deve essere compatibile con una UI premium (no markup pensato per
estetica fintech, no copy "scopri quanto puoi ottenere!").

---

## REQ-3 — Dati reali, fonti validate, nessun dato inventato

Regola assoluta del progetto:

- non inventare importi;
- non inventare coefficienti;
- non inventare formule;
- non usare dati demo nei calcoli pubblici;
- non hardcodare importi legali nel codice;
- ogni valore giuridico è collegato a una `LegalSource`;
- ogni `LegalSource` ha uno `status`;
- solo `LegalSource.status == approved` alimenta calcoli pubblici;
- ogni risultato espone fonti, ipotesi, formule, limiti, disclaimer.

Se manca una fonte approvata per la giurisdizione richiesta:

- il sistema risponde "calcolo non disponibile / requires legal validation";
- non produce stima fittizia;
- propone CTA verso consulenza umana.

Meglio nessun calcolo che un calcolo falso.

---

## REQ-4 — Completezza giuridica modulare

La tassonomia dei moduli è ampia. L'implementazione è in profondità,
modulo per modulo, paese per paese. Non si implementa "tutto superficiale".

### A. Risarcimento danni

- incidente stradale;
- danno biologico;
- invalidità permanente;
- invalidità temporanea totale/parziale;
- danno morale;
- danno estetico;
- danno patrimoniale;
- spese mediche;
- perdita reddito;
- assistenza futura;
- concorso di colpa;
- danno da morte;
- danno parentale;
- danno terminale;
- danno catastrofale;
- danno da perdita chance;
- danno da lesione consenso informato;
- responsabilità medica;
- infezioni ospedaliere;
- errore diagnostico;
- ritardo diagnostico;
- infortunio sul lavoro;
- danno scolastico/professionale;
- danno da vacanza rovinata (se gestibile);
- danno da diffamazione (modulo futuro).

### B. Successioni

- successione legittima;
- successione testamentaria;
- quote di legittima;
- lesione di legittima;
- riduzione donazioni;
- ruoli: coniuge, figli, genitori, fratelli/sorelle;
- beni immobili;
- beni in più paesi;
- residenza abituale;
- cittadinanza;
- legge applicabile;
- casi internazionali.

### C. Casi internazionali

- incidente in Italia con vittima straniera;
- incidente all'estero con cittadino italiano;
- assicurazione estera;
- responsabile residente in altro paese;
- beni successori in più paesi;
- eredi in paesi diversi;
- scelta lingua del report;
- confronto orientativo tra giurisdizioni (solo se legalmente fondato).

### Paesi

- Iniziali (MVP): Italia, Francia, Belgio, Marocco, Tunisia.
- Futuri: Spagna, Germania, Canada, Romania, Algeria, Egitto, altri.

Sequenza di lavoro:

1. tassonomia completa (questo documento);
2. MVP Italia in profondità (un modulo alla volta);
3. estensione paese per paese.

---

## REQ-5 — Report e trasparenza

Ogni simulazione è esportabile in un report che contiene:

- dati inseriti dall'utente (con consenso);
- paese / giurisdizione;
- tipo caso;
- risultato stimato (se disponibile);
- range minimo / medio / massimo;
- fonti usate (titolo, URL, data);
- versione fonte;
- data fonte;
- formule applicate;
- ipotesi;
- documenti mancanti che limitano la stima;
- livello di affidabilità (`low | medium | high`);
- limiti dichiarati della simulazione;
- disclaimer obbligatorio (vedi `CLAUDE.md`);
- CTA verso valutazione legale umana dello Studio.

Il report è generato lato server, multilingua (REQ-1), e non contiene
mai claim di garanzia di risultato.

---

## REQ-6 — Collegamento al sito madre

Sito madre (istituzionale): `https://international.studiolegalebadrane.it/`.

La piattaforma è autonoma ma coordinata:

- header/footer coerenti con il sito madre;
- link diretto al sito madre (logo, footer);
- CTA dal sito madre verso simulatore (lavoro SEO/landing);
- CTA dal simulatore verso consulenza Studio (form lead);
- tracciamento conversioni (F12 analytics);
- SEO multilingua coordinata, no contenuti duplicati cross-domain.

`PARENT_SITE_URL` è già esposto come setting (`config/settings.py`),
da usare via context processor nei template, mai hardcoded.

---

## Mappa requisito → fase

| Requisito | F0 | F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | F9 | F10 | F11 | F12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REQ-1 multilingua | base | rispetto FK lingua | seed lingue | testi consenso versionati | calc i18n | wizard i18n | report i18n | UI RTL | landing i18n | — | retention testi | — | analytics i18n |
| REQ-2 design premium | — | — | — | naming sobrio | — | — | — | UI definitiva | landing premium | — | — | — | — |
| REQ-3 fonti validate | — | core | — | audit | engine usa `.approved()` | enforce manca-fonte | — | — | — | — | retention storico | — | — |
| REQ-4 completezza | — | — | — | — | tassonomia | engine modulare | wizard modulare | — | — | — | — | — | — |
| REQ-5 report | — | — | — | audit eventi | output engine | — | — | — | — | PDF server | — | — | — |
| REQ-6 sito madre | settings | — | — | — | — | — | — | header/footer | landing | — | — | deploy | analytics |

---

## Glossario rapido

- **Fonte approvata**: `LegalSource.status == approved` e non scaduta.
- **Calcolo pubblico**: qualsiasi output mostrato a utente non-staff.
- **Sito madre**: dominio istituzionale; questa piattaforma è un sub-dominio.
- **Modulo**: una categoria di calcolo (es. "danno biologico Italia").
