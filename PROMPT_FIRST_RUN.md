# PROMPT_FIRST_RUN.md

Agisci come team di agenti coordinati per creare la piattaforma Django "Simulatore Risarcimenti e Successioni Internazionali" dello Studio Legale Internazionale Badrane.

Prima di modificare codice in modo esteso:
1. leggi CLAUDE.md;
2. ispeziona la struttura attuale del progetto;
3. verifica settings.py, apps, requirements, template iniziale;
4. usa, se utile, questi subagent:
   - product-architect;
   - legal-data-architect;
   - django-architect;
   - ux-ui-designer;
   - security-gdpr-reviewer.

Obiettivo del primo run:
- non costruire tutto;
- fare audit iniziale;
- proporre architettura MVP;
- creare piano operativo fase per fase;
- poi implementare solo la base indispensabile se sicura.

MVP iniziale:
1. legal_sources con modello fonti e status approval;
2. jurisdictions con Country/Jurisdiction/Currency;
3. calculators con interfaccia engine e output standard;
4. cases con Simulation;
5. compliance con ConsentRecord;
6. crm con Lead;
7. core con pagine base;
8. disclaimer globale;
9. test minimi;
10. admin base.

Regole:
- non inventare importi legali;
- i calcoli pubblici usano solo fonti approved;
- dati demo devono essere marcati come demo;
- se mancano fonti, mostrare "requires legal validation";
- ogni risultato deve avere disclaimer;
- non leggere .env;
- non inserire dati sensibili nei log;
- mantenere design premium, sobrio, internazionale.

Prima risposta richiesta:
1. riepilogo di ciò che hai trovato;
2. rischi;
3. piano fasi;
4. lista file che intendi modificare;
5. comandi che vuoi eseguire.
