"""
Disclaimer legali del motore.

REQ-1 (multilingua): il disclaimer è disponibile nelle 4 lingue ufficiali.
Le traduzioni qui sono umane e revisionate, NON `gettext`: il disclaimer
deve apparire SEMPRE identico ad ogni utente nella sua lingua, senza
dipendere dal locale di sistema. Eventuali aggiornamenti legali si
fanno con un commit esplicito a questo file.

Aggiungere lingue significa aggiungere una entry: il fallback è `it`.
"""

from __future__ import annotations

LEGAL_DISCLAIMERS: dict[str, str] = {
    "it": (
        "La simulazione è indicativa e non costituisce parere legale, "
        "medico-legale o garanzia di risultato. La valutazione effettiva "
        "dipende da documenti, perizie, responsabilità, legge applicabile, "
        "giurisdizione competente, orientamenti giudiziari e prassi "
        "assicurative."
    ),
    "fr": (
        "La simulation est indicative et ne constitue ni un avis juridique, "
        "ni un avis médico-légal, ni une garantie de résultat. L'évaluation "
        "effective dépend des documents, expertises, responsabilités, du "
        "droit applicable, de la juridiction compétente, de la jurisprudence "
        "et des pratiques d'assurance."
    ),
    "en": (
        "This simulation is indicative and does not constitute legal advice, "
        "medico-legal opinion or guarantee of outcome. The actual assessment "
        "depends on documents, expert reports, liability, applicable law, "
        "competent jurisdiction, case law and insurance practice."
    ),
    "ar": (
        "المحاكاة إرشادية ولا تُعدّ رأياً قانونياً أو طبياً قانونياً ولا "
        "ضماناً للنتيجة. يعتمد التقييم الفعلي على الوثائق والخبرات "
        "والمسؤوليات والقانون الواجب التطبيق والاختصاص القضائي والاجتهاد "
        "القضائي والممارسات التأمينية."
    ),
}

DEFAULT_LANGUAGE = "it"


def get_disclaimer(language: str | None = None) -> str:
    """Restituisci il disclaimer nella lingua richiesta, fallback `it`."""
    code = (language or DEFAULT_LANGUAGE).lower()
    return LEGAL_DISCLAIMERS.get(code, LEGAL_DISCLAIMERS[DEFAULT_LANGUAGE])
