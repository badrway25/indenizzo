"""
Etichette multilingua per il report PDF.

Tenute fuori da `gettext` di proposito: il report è un artefatto legale
distribuito offline, deve avere stringhe stabili e revisionate per ogni
release. Aggiornare significa aprire una PR su questo file e farla
firmare dallo Studio.

Lingue supportate: it (default), fr, en, ar.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "it"

# RTL languages — per ora solo arabo. Se reportlab non è in grado di
# renderizzare bene il bidi, il service emette un warning tecnico nel
# `metadata` del report e ricade su LTR senza bloccare la generazione.
RTL_LANGUAGES: frozenset[str] = frozenset({"ar"})


_LABELS: dict[str, dict[str, str]] = {
    "it": {
        "report_title": "Report di simulazione preliminare",
        "studio_name": "Studio Legale Internazionale Badrane",
        "section_general": "Dati generali",
        "section_input": "Dati forniti",
        "section_result": "Risultato",
        "section_sources": "Fonti citate",
        "section_warnings": "Avvertenze",
        "section_missing": "Documenti / requisiti mancanti",
        "section_assumptions": "Assunzioni",
        "section_provenance": "Tracciabilità del calcolo",
        "provenance_tagline": "Calcolo tracciato e riproducibile.",
        "label_source_version": "Versione fonte",
        "label_source_hash": "Hash fonte",
        "label_engine_version": "Versione engine",
        "label_calc_date": "Data calcolo",
        "section_disclaimer": "Disclaimer legale",
        "section_cta": "Prossimi passi",
        "label_simulation_id": "ID simulazione",
        "label_generated_at": "Data generazione",
        "label_language": "Lingua",
        "label_jurisdiction": "Giurisdizione",
        "label_country": "Paese",
        "label_case_type": "Tipo di caso",
        "label_created_at": "Data simulazione",
        "label_status": "Stato",
        "label_confidence": "Confidenza",
        "label_currency": "Valuta",
        "label_min": "Minimo",
        "label_mid": "Medio",
        "label_max": "Massimo",
        "no_estimate": (
            "La stima economica non è disponibile perché il calcolo "
            "richiede fonti, dataset e formule approvate o ulteriori dati."
        ),
        "no_sources": "Nessuna fonte approvata applicata al calcolo.",
        "no_warnings": "Nessuna avvertenza tecnica.",
        "no_missing": "Nessun documento o requisito mancante.",
        "no_assumptions": "Nessuna assunzione registrata.",
        "no_input": "Nessun dato fornito dall'utente.",
        "cta_text": ("Per una valutazione legale personalizzata, contatta lo Studio."),
        "cta_contact": "Modulo di contatto",
        "cta_parent_site": "Sito istituzionale",
        "footer_page": "Pagina",
    },
    "fr": {
        "report_title": "Rapport de simulation préliminaire",
        "studio_name": "Studio Legale Internazionale Badrane",
        "section_general": "Données générales",
        "section_input": "Données fournies",
        "section_result": "Résultat",
        "section_sources": "Sources citées",
        "section_warnings": "Avertissements",
        "section_missing": "Documents / exigences manquantes",
        "section_assumptions": "Hypothèses",
        "section_provenance": "Traçabilité du calcul",
        "provenance_tagline": "Calcul tracé et reproductible.",
        "label_source_version": "Version de la source",
        "label_source_hash": "Empreinte de la source",
        "label_engine_version": "Version du moteur",
        "label_calc_date": "Date du calcul",
        "section_disclaimer": "Avis juridique",
        "section_cta": "Prochaines étapes",
        "label_simulation_id": "ID simulation",
        "label_generated_at": "Date de génération",
        "label_language": "Langue",
        "label_jurisdiction": "Juridiction",
        "label_country": "Pays",
        "label_case_type": "Type de cas",
        "label_created_at": "Date de simulation",
        "label_status": "Statut",
        "label_confidence": "Confiance",
        "label_currency": "Devise",
        "label_min": "Minimum",
        "label_mid": "Médian",
        "label_max": "Maximum",
        "no_estimate": (
            "L'estimation économique n'est pas disponible : le calcul "
            "exige des sources, jeux de données et formules approuvés ou "
            "des informations supplémentaires."
        ),
        "no_sources": "Aucune source approuvée appliquée au calcul.",
        "no_warnings": "Aucun avertissement technique.",
        "no_missing": "Aucun document ou exigence manquante.",
        "no_assumptions": "Aucune hypothèse enregistrée.",
        "no_input": "Aucune donnée fournie par l'utilisateur.",
        "cta_text": ("Pour une évaluation juridique personnalisée, contactez l'Étude."),
        "cta_contact": "Formulaire de contact",
        "cta_parent_site": "Site institutionnel",
        "footer_page": "Page",
    },
    "en": {
        "report_title": "Preliminary simulation report",
        "studio_name": "Studio Legale Internazionale Badrane",
        "section_general": "General data",
        "section_input": "Provided data",
        "section_result": "Result",
        "section_sources": "Cited sources",
        "section_warnings": "Warnings",
        "section_missing": "Missing documents / requirements",
        "section_assumptions": "Assumptions",
        "section_provenance": "Calculation traceability",
        "provenance_tagline": "Tracked and reproducible calculation.",
        "label_source_version": "Source version",
        "label_source_hash": "Source hash",
        "label_engine_version": "Engine version",
        "label_calc_date": "Calculation date",
        "section_disclaimer": "Legal disclaimer",
        "section_cta": "Next steps",
        "label_simulation_id": "Simulation ID",
        "label_generated_at": "Generated at",
        "label_language": "Language",
        "label_jurisdiction": "Jurisdiction",
        "label_country": "Country",
        "label_case_type": "Case type",
        "label_created_at": "Simulation date",
        "label_status": "Status",
        "label_confidence": "Confidence",
        "label_currency": "Currency",
        "label_min": "Minimum",
        "label_mid": "Mid",
        "label_max": "Maximum",
        "no_estimate": (
            "The economic estimate is not available: the calculation "
            "requires approved legal sources, datasets and formulas, or "
            "additional input."
        ),
        "no_sources": "No approved source applied to the calculation.",
        "no_warnings": "No technical warning.",
        "no_missing": "No missing document or requirement.",
        "no_assumptions": "No assumption recorded.",
        "no_input": "No input provided by the user.",
        "cta_text": ("For a personalised legal assessment, contact the Studio."),
        "cta_contact": "Contact form",
        "cta_parent_site": "Parent website",
        "footer_page": "Page",
    },
    "ar": {
        "report_title": "Preliminary simulation report (Arabic LTR fallback)",
        "studio_name": "Studio Legale Internazionale Badrane",
        "section_general": "General data",
        "section_input": "Provided data",
        "section_result": "Result",
        "section_sources": "Cited sources",
        "section_warnings": "Warnings",
        "section_missing": "Missing documents / requirements",
        "section_assumptions": "Assumptions",
        "section_provenance": "Calculation traceability",
        "provenance_tagline": "Tracked and reproducible calculation.",
        "label_source_version": "Source version",
        "label_source_hash": "Source hash",
        "label_engine_version": "Engine version",
        "label_calc_date": "Calculation date",
        "section_disclaimer": "Legal disclaimer",
        "section_cta": "Next steps",
        "label_simulation_id": "Simulation ID",
        "label_generated_at": "Generated at",
        "label_language": "Language",
        "label_jurisdiction": "Jurisdiction",
        "label_country": "Country",
        "label_case_type": "Case type",
        "label_created_at": "Simulation date",
        "label_status": "Status",
        "label_confidence": "Confidence",
        "label_currency": "Currency",
        "label_min": "Minimum",
        "label_mid": "Mid",
        "label_max": "Maximum",
        "no_estimate": (
            "The economic estimate is not available: the calculation "
            "requires approved legal sources, datasets and formulas, or "
            "additional input."
        ),
        "no_sources": "No approved source applied to the calculation.",
        "no_warnings": "No technical warning.",
        "no_missing": "No missing document or requirement.",
        "no_assumptions": "No assumption recorded.",
        "no_input": "No input provided by the user.",
        "cta_text": ("For a personalised legal assessment, contact the Studio."),
        "cta_contact": "Contact form",
        "cta_parent_site": "Parent website",
        "footer_page": "Page",
    },
}


def get_labels(language: str | None) -> dict[str, str]:
    code = (language or DEFAULT_LANGUAGE).lower().split("-", 1)[0]
    return _LABELS.get(code) or _LABELS[DEFAULT_LANGUAGE]


def is_rtl(language: str | None) -> bool:
    code = (language or DEFAULT_LANGUAGE).lower().split("-", 1)[0]
    return code in RTL_LANGUAGES
