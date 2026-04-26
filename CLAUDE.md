# CLAUDE.md — Studio Legale Badrane LegalTech Platform

## Requisiti permanenti di prodotto

I 6 requisiti vincolanti (multilingua, design premium, fonti validate,
tassonomia modulare, report trasparenti, collegamento al sito madre)
sono in `docs/architecture/PRODUCT_REQUIREMENTS.md`. Quel file è la
fonte canonica: ogni scelta architetturale deve esservi conforme.
In caso di conflitto con questo `CLAUDE.md`, prevalgono i requisiti.

## Missione del progetto

Stai lavorando su una piattaforma Django professionale per lo Studio Legale Internazionale Badrane.

Sito istituzionale esistente:
https://international.studiolegalebadrane.it/

Nuova piattaforma prevista:
https://simulatore.studiolegalebadrane.it/
oppure:
https://indennizzo.studiolegalebadrane.it/

Il sito istituzionale resta il sito madre. Questa web app Django è una piattaforma autonoma collegata al sito madre tramite CTA, SEO, link e identità visiva coerente.

## Obiettivo prodotto

Creare una piattaforma legal-tech per simulazioni indicative relative a:

- risarcimento danni in Italia e all'estero;
- incidenti stradali;
- danno biologico;
- responsabilità medica;
- infortuni sul lavoro;
- danno da morte;
- perdita del rapporto parentale;
- danni patrimoniali;
- successioni ed eredità internazionali;
- casi transfrontalieri.

Paesi iniziali:
- Italia;
- Francia;
- Belgio;
- Marocco;
- Tunisia.

## Regola fondamentale

Non inventare mai dati legali.

Ogni importo, coefficiente, tabella, formula o valore usato in un calcolo deve essere collegato a una fonte.

Ogni fonte deve avere:
- paese;
- titolo;
- tipo fonte;
- URL;
- file o riferimento archiviato;
- data pubblicazione;
- data efficacia;
- data ultimo controllo;
- stato validazione;
- affidabilità;
- note;
- lingua;
- revisore legale se disponibile.

Stati fonte:
- draft;
- extracted;
- needs_review;
- reviewed;
- approved;
- deprecated;
- replaced.

I calcoli pubblici devono usare solo fonti `approved`.
Se non esistono fonti approved, il sistema deve mostrare:
"Il calcolo per questa giurisdizione non è ancora disponibile perché richiede validazione legale."

## Disclaimer obbligatorio

Ogni risultato deve indicare:

"La simulazione è indicativa e non costituisce parere legale, medico-legale o garanzia di risultato. La valutazione effettiva dipende da documenti, perizie, responsabilità, legge applicabile, giurisdizione competente, orientamenti giudiziari e prassi assicurative."

## Strategia architetturale

Lavora prima come architetto, poi come sviluppatore.

Ordine obbligatorio:
1. Audit struttura progetto.
2. Architettura funzionale.
3. Architettura dati legali.
4. Modelli Django.
5. Motore di calcolo.
6. Wizard UX.
7. Report PDF.
8. CRM lead.
9. Admin Studio.
10. GDPR/security.
11. SEO/multilingua.
12. Test.
13. Deploy.

Non iniziare implementazioni casuali.
Non creare app disordinate.
Non inserire logica di calcolo direttamente nelle views.
Non hardcodare dati normativi dentro il codice.

## Stack preferito

- Python 3.12+
- Django 5.2 LTS
- PostgreSQL in produzione
- SQLite solo per sviluppo iniziale
- Redis + Celery per task asincroni
- HTMX + Alpine.js per frontend dinamico leggero
- Tailwind CSS per UI moderna
- Django REST Framework dove utile
- Report PDF lato server
- pytest
- Playwright per test end-to-end
- Docker Compose per produzione/staging

## Struttura app

apps/accounts/
- utenti, ruoli, studio, staff, clienti.

apps/core/
- home, layout, utilities, pagine base.

apps/jurisdictions/
- paesi, sistemi giuridici, lingue, valute.

apps/legal_sources/
- fonti normative, decreti, tabelle, allegati, versioni, validazione.

apps/calculators/
- engine registry, input schema, output schema, validation, explanation builder.

apps/compensation/
- danni, lesioni, danno biologico, danno parentale, danni patrimoniali.

apps/inheritance/
- successioni, quote, legittima, casi internazionali.

apps/cases/
- simulazioni, dati utente, stato pratica, documenti.

apps/reports/
- PDF, esportazioni, report multilingua.

apps/crm/
- lead, richieste consulenza, pipeline Studio.

apps/compliance/
- consenso, privacy, retention, cancellazione dati, audit accessi.

apps/cms_content/
- landing SEO, pagine paese, FAQ, testi multilingua.

apps/analytics/
- funnel simulazione, conversioni, eventi.

## Output standard del motore di calcolo

Ogni engine deve produrre:

{
  "simulation_id": "...",
  "jurisdiction": "...",
  "case_type": "...",
  "currency": "EUR",
  "estimated_min": 0,
  "estimated_mid": 0,
  "estimated_max": 0,
  "breakdown": [],
  "sources": [],
  "assumptions": [],
  "warnings": [],
  "missing_documents": [],
  "confidence": "low|medium|high",
  "legal_disclaimer": "..."
}

## UX

Design:
- premium;
- elegante;
- sobrio;
- autorevole;
- internazionale;
- mobile-first;
- accessibile.

Colori:
- blu notte;
- oro sobrio;
- bianco caldo;
- grigio pietra.

Evitare:
- promesse di guadagno;
- linguaggio aggressivo;
- stile assicurazione/casinò;
- claim non dimostrabili.

## GDPR e sicurezza

Il progetto può trattare dati sensibili:
- salute;
- invalidità;
- reddito;
- morte;
- famiglia;
- successioni;
- documenti legali.

Implementare:
- consenso esplicito;
- data minimization;
- retention;
- cancellazione dati;
- audit log;
- ruoli admin;
- protezione file upload;
- nessun dato sensibile nei log;
- esclusione `.env` dalla lettura;
- disclaimer prima dell'invio dati.

## Comandi utili

Attivazione ambiente:
.\.venv\Scripts\Activate.ps1

Check Django:
python manage.py check

Migrazioni:
python manage.py makemigrations
python manage.py migrate

Test:
pytest

Server locale:
python manage.py runserver 127.0.0.1:8000

Lint:
ruff check .

Format:
black .

## Primo obiettivo

Il primo lavoro non è scrivere subito tutto il sito.
Il primo lavoro è produrre un piano tecnico e creare la base architetturale pulita per il MVP Italia.

MVP iniziale:
1. home simulatore;
2. scelta paese;
3. scelta tipo caso;
4. wizard Italia danno biologico;
5. wizard Italia successione base;
6. risultato simulazione;
7. report PDF;
8. lead form;
9. admin fonti;
10. dashboard lead;
11. disclaimer;
12. GDPR consent;
13. test minimi.

## Regola finale

Meglio nessun calcolo che un calcolo falso.
