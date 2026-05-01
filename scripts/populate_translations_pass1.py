"""
Populate .po translations for pass 1.

Iter: F-product-premium-visual-i18n-pass1.

Carica `locale/<lang>/LC_MESSAGES/django.po` per `it`, `fr`, `ar` e
applica una mappa curata di traduzioni per le stringhe ad alta
visibilità (header, footer, hero, CTA, status badge, country pages).

EN non viene toccata: Django fa fallback a `msgid` quando `msgstr` è
vuoto, e le stringhe sorgenti sono già in inglese.

Le stringhe NON tradotte qui restano vuote nel `.po` → fallback in
inglese. È intenzionale: meglio una traduzione parziale validata
che una traduzione totale automatica non validata.

Le denominazioni legali (D.P.R., Mornet, Moudawana, Loi 98-97,
Tabella Unica Nazionale, Tabelle Tribunale di Milano, ecc.)
restano nei loro nomi originali.

Usage:
    python scripts/populate_translations_pass1.py
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Maps: msgid -> msgstr per lingua
# ---------------------------------------------------------------------------

TRANSLATIONS: dict[str, dict[str, str]] = {
    # NAV / common ----------------------------------------------------------
    "Home": {
        "it": "Home",
        "fr": "Accueil",
        "ar": "الرئيسية",
    },
    "Countries": {
        "it": "Paesi",
        "fr": "Pays",
        "ar": "البلدان",
    },
    "Case types": {
        "it": "Tipi di caso",
        "fr": "Types de cas",
        "ar": "أنواع القضايا",
    },
    "Methodology": {
        "it": "Metodologia",
        "fr": "Méthodologie",
        "ar": "المنهجية",
    },
    "Privacy": {
        "it": "Privacy",
        "fr": "Confidentialité",
        "ar": "الخصوصية",
    },
    "Disclaimer": {
        "it": "Avvertenze",
        "fr": "Avertissement",
        "ar": "إخلاء المسؤولية",
    },
    "Request legal review": {
        "it": "Richiedi una valutazione legale",
        "fr": "Demander une revue juridique",
        "ar": "اطلب مراجعة قانونية",
    },
    "Skip to content": {
        "it": "Vai al contenuto",
        "fr": "Aller au contenu",
        "ar": "تخطّي إلى المحتوى",
    },
    "Open country page": {
        "it": "Apri la pagina paese",
        "fr": "Ouvrir la page pays",
        "ar": "افتح صفحة البلد",
    },
    # HERO HOME -------------------------------------------------------------
    "Cross-border legal-tech platform": {
        "it": "Piattaforma legal-tech transfrontaliera",
        "fr": "Plateforme legal-tech transfrontalière",
        "ar": "منصة قانونية-تقنية عابرة للحدود",
    },
    "Indicative simulations for compensation and inheritance, grounded in validated legal sources.": {  # noqa: E501
        "it": "Simulazioni indicative su risarcimenti e successioni, fondate su fonti legali validate.",  # noqa: E501
        "fr": "Simulations indicatives en indemnisation et succession, ancrées dans des sources juridiques validées.",  # noqa: E501
        "ar": "محاكاة إرشادية للتعويضات والميراث، مستندة إلى مصادر قانونية موثقة.",
    },
    "Explore case types": {
        "it": "Esplora i tipi di caso",
        "fr": "Explorer les types de cas",
        "ar": "استعرض أنواع القضايا",
    },
    "Read our methodology": {
        "it": "Leggi la nostra metodologia",
        "fr": "Lire notre méthodologie",
        "ar": "اقرأ منهجيتنا",
    },
    "Trust by design": {
        "it": "Affidabilità progettuale",
        "fr": "Confiance par conception",
        "ar": "الثقة بالتصميم",
    },
    "Jurisdictions": {
        "it": "Giurisdizioni",
        "fr": "Juridictions",
        "ar": "الاختصاصات القضائية",
    },
    "MVP coverage": {
        "it": "Copertura MVP",
        "fr": "Périmètre MVP",
        "ar": "تغطية الإصدار الأولي",
    },
    "See all countries": {
        "it": "Vedi tutti i paesi",
        "fr": "Voir tous les pays",
        "ar": "عرض جميع البلدان",
    },
    "Validated sources only": {
        "it": "Solo fonti validate",
        "fr": "Sources validées uniquement",
        "ar": "مصادر موثقة فقط",
    },
    "Transparent ranges": {
        "it": "Intervalli trasparenti",
        "fr": "Fourchettes transparentes",
        "ar": "نطاقات شفافة",
    },
    "Human review": {
        "it": "Revisione umana",
        "fr": "Revue humaine",
        "ar": "مراجعة بشرية",
    },
    "Ready for a real legal evaluation?": {
        "it": "Pronto per una valutazione legale reale?",
        "fr": "Prêt pour une évaluation juridique réelle ?",
        "ar": "هل أنت جاهز لتقييم قانوني حقيقي؟",
    },
    # COUNTRIES INDEX -------------------------------------------------------
    "Coverage map": {
        "it": "Mappa di copertura",
        "fr": "Carte de couverture",
        "ar": "خريطة التغطية",
    },
    "Countries we cover": {
        "it": "I paesi che copriamo",
        "fr": "Les pays que nous couvrons",
        "ar": "البلدان التي نغطّيها",
    },
    "Available": {
        "it": "Disponibile",
        "fr": "Disponible",
        "ar": "متاح",
    },
    "Legal sources under review": {
        "it": "Fonti legali in revisione",
        "fr": "Sources juridiques en cours de revue",
        "ar": "المصادر القانونية قيد المراجعة",
    },
    "In preparation": {
        "it": "In preparazione",
        "fr": "En préparation",
        "ar": "قيد الإعداد",
    },
    # COUNTRY LANDING -------------------------------------------------------
    "Country page": {
        "it": "Pagina paese",
        "fr": "Page pays",
        "ar": "صفحة البلد",
    },
    "Status": {
        "it": "Stato",
        "fr": "Statut",
        "ar": "الحالة",
    },
    "Calculator available": {
        "it": "Calcolatore disponibile",
        "fr": "Calculateur disponible",
        "ar": "الحاسبة متاحة",
    },
    "Legal basis": {
        "it": "Base legale",
        "fr": "Base juridique",
        "ar": "الأساس القانوني",
    },
    "How to proceed": {
        "it": "Come procedere",
        "fr": "Comment procéder",
        "ar": "كيفية المتابعة",
    },
    "Option 1": {"it": "Opzione 1", "fr": "Option 1", "ar": "الخيار 1"},
    "Option 2": {"it": "Opzione 2", "fr": "Option 2", "ar": "الخيار 2"},
    "Run the simulation wizard": {
        "it": "Avvia la simulazione guidata",
        "fr": "Lancer le simulateur guidé",
        "ar": "شغّل المحاكاة الموجهة",
    },
    "Submit a structured request": {
        "it": "Invia una richiesta strutturata",
        "fr": "Soumettre une demande structurée",
        "ar": "أرسل طلبًا منظمًا",
    },
    "Direct legal review": {
        "it": "Revisione legale diretta",
        "fr": "Revue juridique directe",
        "ar": "مراجعة قانونية مباشرة",
    },
    "approved": {"it": "approvata", "fr": "approuvée", "ar": "معتمدة"},
    "needs review": {
        "it": "in revisione",
        "fr": "à revoir",
        "ar": "بحاجة إلى مراجعة",
    },
    "Breadcrumb": {
        "it": "Percorso",
        "fr": "Fil d'Ariane",
        "ar": "مسار التنقّل",
    },
    "Start Italian compensation simulation": {
        "it": "Avvia la simulazione risarcimento Italia",
        "fr": "Lancer la simulation indemnisation Italie",
        "ar": "ابدأ محاكاة التعويض الإيطالي",
    },
    "Open France validation wizard": {
        "it": "Apri la procedura di validazione Francia",
        "fr": "Ouvrir l'assistant de validation France",
        "ar": "افتح معالج التحقق لفرنسا",
    },
    "Open Belgium validation wizard": {
        "it": "Apri la procedura di validazione Belgio",
        "fr": "Ouvrir l'assistant de validation Belgique",
        "ar": "افتح معالج التحقق لبلجيكا",
    },
    "Request Moroccan inheritance review": {
        "it": "Richiedi revisione successione marocchina",
        "fr": "Demander la revue successorale marocaine",
        "ar": "اطلب مراجعة الميراث المغربي",
    },
    "Request Tunisian inheritance review": {
        "it": "Richiedi revisione successione tunisina",
        "fr": "Demander la revue successorale tunisienne",
        "ar": "اطلب مراجعة الميراث التونسي",
    },
    # METHODOLOGY -----------------------------------------------------------
    "How we work": {
        "it": "Come lavoriamo",
        "fr": "Notre démarche",
        "ar": "طريقة عملنا",
    },
    "Sources of law": {
        "it": "Fonti di diritto",
        "fr": "Sources de droit",
        "ar": "مصادر القانون",
    },
    "Validation status": {
        "it": "Stato di validazione",
        "fr": "Statut de validation",
        "ar": "حالة التحقق",
    },
    "When a calculation is not available": {
        "it": "Quando un calcolo non è disponibile",
        "fr": "Lorsqu'un calcul n'est pas disponible",
        "ar": "عندما لا يكون الحساب متاحًا",
    },
    "Ranges, assumptions and confidence": {
        "it": "Intervalli, ipotesi e affidabilità",
        "fr": "Fourchettes, hypothèses et fiabilité",
        "ar": "النطاقات والافتراضات ومستوى الثقة",
    },
    "draft": {"it": "bozza", "fr": "brouillon", "ar": "مسودة"},
    "deprecated": {"it": "deprecata", "fr": "obsolète", "ar": "ملغاة"},
    # WIZARD ---------------------------------------------------------------
    "Indicative simulation": {
        "it": "Simulazione indicativa",
        "fr": "Simulation indicative",
        "ar": "محاكاة إرشادية",
    },
    "Start a simulation": {
        "it": "Avvia una simulazione",
        "fr": "Démarrer une simulation",
        "ar": "ابدأ محاكاة",
    },
    "Start a guided simulation": {
        "it": "Avvia una simulazione guidata",
        "fr": "Démarrer une simulation guidée",
        "ar": "ابدأ محاكاة موجهة",
    },
    # CONTACT --------------------------------------------------------------
    "Contact the Studio": {
        "it": "Contatta lo Studio",
        "fr": "Contacter le Cabinet",
        "ar": "تواصل مع المكتب",
    },
    "Request a legal review": {
        "it": "Richiedi una valutazione legale",
        "fr": "Demander une revue juridique",
        "ar": "اطلب مراجعة قانونية",
    },
    "Next step": {
        "it": "Prossimo passo",
        "fr": "Étape suivante",
        "ar": "الخطوة التالية",
    },
}


# ---------------------------------------------------------------------------
# .po edit logic
# ---------------------------------------------------------------------------

# Match a `.po` block:
#   msgid "..."        (può essere multiline)
#   msgstr ""          (vuota o singola)
# Strategia minimale: match per chiave singola line (`msgid "<key>"`),
# non gestiamo multiline msgid (che non sono in questa lista). Se la
# chiave è multiline nel .po, semplicemente non la troviamo e
# lasciamo lo skip (non corrompiamo il file).


def update_po(po_path: Path, lang: str) -> int:
    """Aggiorna il `.po` con le traduzioni della mappa per `lang`. Ritorna count aggiornati."""
    text = po_path.read_text(encoding="utf-8")
    updated = 0
    for msgid, by_lang in TRANSLATIONS.items():
        translated = by_lang.get(lang)
        if translated is None:
            continue
        # `msgid` è una stringa singola line. La cerchiamo tra `"...."` con
        # escape per " e \. Per semplicità non escapiamo: gli msgid usati
        # qui non contengono `"`.
        pattern = re.compile(
            r'(^msgid "' + re.escape(msgid) + r'"\nmsgstr ")"',
            flags=re.MULTILINE,
        )
        new_text, n = pattern.subn(
            r"\1" + translated.replace("\\", "\\\\").replace('"', '\\"') + '"', text
        )
        if n > 0:
            text = new_text
            updated += n
    po_path.write_text(text, encoding="utf-8")
    return updated


def main() -> None:
    base = Path(__file__).resolve().parent.parent / "locale"
    for lang in ("it", "fr", "ar"):
        po = base / lang / "LC_MESSAGES" / "django.po"
        if not po.exists():
            print(f"[{lang}] missing {po}, skipped")
            continue
        n = update_po(po, lang)
        print(f"[{lang}] updated {n} entries in {po.relative_to(base.parent)}")


if __name__ == "__main__":
    main()
