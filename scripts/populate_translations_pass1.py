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
    # ---------------------------------------------------------------------
    # PASS 2 — long-form copy: hero descriptions, methodology bullets,
    # wizard descriptions, status messages, disclaimers, country landing
    # subtitles. Tono: studio legale internazionale, sobrio.
    # ---------------------------------------------------------------------
    # HOME hero copy
    "A professional tool by Studio Legale Internazionale Badrane. Each estimate is supported by validated legal sources, transparent ranges and clear assumptions. We do not promise outcomes — we help you understand them.": {  # noqa: E501
        "it": "Uno strumento professionale dello Studio Legale Internazionale Badrane. Ogni stima si basa su fonti legali validate, intervalli trasparenti e ipotesi esplicite. Non promettiamo risultati: aiutiamo a comprenderli.",  # noqa: E501
        "fr": "Un outil professionnel du Cabinet Légal International Badrane. Chaque estimation s'appuie sur des sources juridiques validées, des fourchettes transparentes et des hypothèses explicites. Nous ne promettons aucun résultat : nous aidons à le comprendre.",  # noqa: E501
        "ar": "أداة احترافية من المكتب القانوني الدولي بدران. تستند كل تقدير إلى مصادر قانونية موثقة ونطاقات شفافة وفرضيات واضحة. نحن لا نعد بالنتائج، بل نساعد على فهمها.",  # noqa: E501
    },
    "Simulations are indicative. They do not constitute legal advice or guarantee any outcome.": {  # noqa: E501
        "it": "Le simulazioni sono indicative. Non costituiscono parere legale né garanzia di risultato.",  # noqa: E501
        "fr": "Les simulations sont indicatives. Elles ne constituent ni un avis juridique ni une garantie de résultat.",  # noqa: E501
        "ar": "المحاكاة إرشادية. لا تُعدّ رأيًا قانونيًا ولا ضمانًا للنتيجة.",
    },
    "Every estimate cites the legal sources behind it: title, version and date.": {
        "it": "Ogni stima cita le fonti legali sottostanti: titolo, versione e data.",
        "fr": "Chaque estimation cite les sources juridiques sous-jacentes : titre, version et date.",  # noqa: E501
        "ar": "تستشهد كل تقدير بالمصادر القانونية الداعمة: العنوان والإصدار والتاريخ.",
    },
    "If a jurisdiction is not yet legally validated, we say so explicitly — no fabricated numbers.": {  # noqa: E501
        "it": "Se una giurisdizione non è ancora validata, lo diciamo in modo esplicito: nessun numero inventato.",  # noqa: E501
        "fr": "Si une juridiction n'est pas encore validée, nous l'indiquons explicitement : aucun chiffre inventé.",  # noqa: E501
        "ar": "إذا لم يتم بعد التحقق من اختصاص ما، فإننا نوضح ذلك صراحةً: لا أرقام مُختلَقة.",  # noqa: E501
    },
    "Reports include ranges, assumptions, missing documents and confidence level.": {
        "it": "I report includono intervalli, ipotesi, documenti mancanti e livello di affidabilità.",  # noqa: E501
        "fr": "Les rapports incluent fourchettes, hypothèses, documents manquants et niveau de fiabilité.",  # noqa: E501
        "ar": "تشمل التقارير النطاقات والافتراضات والمستندات الناقصة ومستوى الثقة.",
    },
    "Available in Italian, French, English and Arabic.": {
        "it": "Disponibile in italiano, francese, inglese e arabo.",
        "fr": "Disponible en italien, français, anglais et arabe.",
        "ar": "متاح بالإيطالية والفرنسية والإنجليزية والعربية.",
    },
    "Our international team handles compensation, medical liability and cross-border inheritance matters across Europe and North Africa.": {  # noqa: E501
        "it": "Il nostro team internazionale gestisce risarcimenti, responsabilità medica e successioni transfrontaliere in Europa e Nord Africa.",  # noqa: E501
        "fr": "Notre équipe internationale traite les indemnisations, la responsabilité médicale et les successions transfrontalières en Europe et en Afrique du Nord.",  # noqa: E501
        "ar": "يتولى فريقنا الدولي قضايا التعويض والمسؤولية الطبية والميراث العابر للحدود في أوروبا وشمال أفريقيا.",  # noqa: E501
    },
    "Start Italy simulation": {
        "it": "Avvia simulazione Italia",
        "fr": "Lancer la simulation Italie",
        "ar": "ابدأ محاكاة إيطاليا",
    },
    # METHODOLOGY 4 cards
    "Every coefficient and figure used in a public calculation is tied to a legal source marked as approved by our team.": {  # noqa: E501
        "it": "Ogni coefficiente e cifra usata in un calcolo pubblico è legata a una fonte legale marcata come approvata dal nostro team.",  # noqa: E501
        "fr": "Chaque coefficient et chiffre utilisé dans un calcul public est rattaché à une source juridique approuvée par notre équipe.",  # noqa: E501
        "ar": "يرتبط كل معامل ورقم مستخدم في الحساب العام بمصدر قانوني معتمد من فريقنا.",
    },
    "You receive a minimum, a midpoint and a maximum, with the assumptions, the formulas and the missing documents clearly listed.": {  # noqa: E501
        "it": "Ricevi un minimo, un valore centrale e un massimo, con ipotesi, formule e documenti mancanti elencati in modo chiaro.",  # noqa: E501
        "fr": "Vous recevez un minimum, une valeur centrale et un maximum, avec hypothèses, formules et documents manquants clairement listés.",  # noqa: E501
        "ar": "تتلقى حدًا أدنى وقيمة وسطى وحدًا أقصى، مع الافتراضات والصيغ والمستندات الناقصة موضحة بوضوح.",  # noqa: E501
    },
    "A simulation is a starting point. The Studio takes over for real legal evaluation when you need a binding opinion.": {  # noqa: E501
        "it": "Una simulazione è un punto di partenza. Lo Studio subentra con una valutazione legale reale quando serve un parere vincolante.",  # noqa: E501
        "fr": "Une simulation est un point de départ. Le Cabinet prend le relais avec une évaluation juridique réelle lorsqu'un avis contraignant est nécessaire.",  # noqa: E501
        "ar": "المحاكاة هي نقطة انطلاق. يتولى المكتب التقييم القانوني الفعلي عند الحاجة إلى رأي ملزم.",  # noqa: E501
    },
    "Our simulator is built on a single principle: no figure is shown to the public unless we can cite the legal source behind it. This page explains how we collect, validate and version those sources.": {  # noqa: E501
        "it": "Il nostro simulatore si basa su un solo principio: nessuna cifra viene mostrata al pubblico senza poter citare la fonte legale che la fonda. Questa pagina spiega come raccogliamo, validiamo e versioniamo le fonti.",  # noqa: E501
        "fr": "Notre simulateur repose sur un seul principe : aucun chiffre n'est montré au public sans pouvoir en citer la source juridique. Cette page explique comment nous collectons, validons et versionnons les sources.",  # noqa: E501
        "ar": "يقوم محاكينا على مبدأ واحد: لا يُعرض أي رقم على الجمهور دون إمكانية الاستشهاد بالمصدر القانوني الذي يدعمه. توضح هذه الصفحة كيف نجمع المصادر ونوثقها ونديرها بإصدارات.",  # noqa: E501
    },
    "For each jurisdiction we maintain a catalogue of laws, ministerial decrees, court compensation tables, administrative guidelines, insurance references and academic doctrine. Each source records its country, jurisdiction, language, citation, official URL, publication date and effective date.": {  # noqa: E501
        "it": "Per ogni giurisdizione manteniamo un catalogo di leggi, decreti ministeriali, tabelle risarcitorie, linee guida amministrative, riferimenti assicurativi e dottrina accademica. Ogni fonte registra paese, giurisdizione, lingua, citazione, URL ufficiale, data di pubblicazione ed efficacia.",  # noqa: E501
        "fr": "Pour chaque juridiction nous tenons un catalogue de lois, décrets ministériels, barèmes d'indemnisation, lignes directrices administratives, références d'assurance et doctrine. Chaque source consigne son pays, sa juridiction, sa langue, sa citation, son URL officielle, sa date de publication et d'effet.",  # noqa: E501
        "ar": "نحتفظ لكل اختصاص بكتالوج للقوانين والمراسيم الوزارية وجداول التعويض والإرشادات الإدارية والمراجع التأمينية والفقه. يسجّل كل مصدر بلده واختصاصه ولغته والاستشهاد به ورابطه الرسمي وتاريخ نشره وسريانه.",  # noqa: E501
    },
    "A source moves through a controlled lifecycle: draft, extracted, needs review, reviewed, approved, deprecated, replaced. Only sources marked as approved can feed a public calculation.": {  # noqa: E501
        "it": "Una fonte attraversa un ciclo di vita controllato: bozza, estratta, in revisione, revisionata, approvata, deprecata, sostituita. Solo le fonti marcate come approvate alimentano un calcolo pubblico.",  # noqa: E501
        "fr": "Une source suit un cycle de vie contrôlé : brouillon, extraite, à revoir, revue, approuvée, obsolète, remplacée. Seules les sources marquées comme approuvées alimentent un calcul public.",  # noqa: E501
        "ar": "يتنقل المصدر عبر دورة حياة محكمة: مسودة، مستخرج، بحاجة إلى مراجعة، مراجَع، معتمد، ملغى، مستبدل. لا تُغذّي الحساب العام إلا المصادر المعتمدة.",  # noqa: E501
    },
    "If no approved source exists for the jurisdiction or the case type you select, the platform tells you explicitly. We do not invent a fallback estimate. Instead, we invite you to request a human legal evaluation.": {  # noqa: E501
        "it": "Se non esiste alcuna fonte approvata per la giurisdizione o il tipo di caso scelto, la piattaforma lo dichiara in modo esplicito. Non inventiamo una stima di ripiego: invitiamo a richiedere una valutazione legale umana.",  # noqa: E501
        "fr": "Si aucune source approuvée n'existe pour la juridiction ou le type de cas choisi, la plateforme le déclare explicitement. Nous n'inventons aucune estimation de repli : nous invitons à demander une évaluation juridique humaine.",  # noqa: E501
        "ar": "إذا لم يوجد مصدر معتمد للاختصاص أو نوع القضية المختار، تُعلِن المنصة ذلك صراحةً. لا نختلق تقديرًا بديلًا: ندعوك إلى طلب تقييم قانوني بشري.",  # noqa: E501
    },
    "Every available simulation reports a minimum, a midpoint and a maximum, with the formulas, the assumptions, the missing documents and a confidence level (low, medium, high). The full disclaimer is always attached.": {  # noqa: E501
        "it": "Ogni simulazione disponibile riporta un minimo, un valore centrale e un massimo, con formule, ipotesi, documenti mancanti e livello di affidabilità (bassa, media, alta). Il disclaimer completo è sempre allegato.",  # noqa: E501
        "fr": "Chaque simulation disponible présente un minimum, une valeur centrale et un maximum, avec formules, hypothèses, documents manquants et niveau de fiabilité (faible, moyenne, élevée). L'avertissement complet est toujours joint.",  # noqa: E501
        "ar": "تُقدّم كل محاكاة متاحة حدًا أدنى وقيمة وسطى وحدًا أقصى، مع الصيغ والافتراضات والمستندات الناقصة ومستوى الثقة (منخفض، متوسط، مرتفع). يُرفق إخلاء المسؤولية الكامل دائمًا.",  # noqa: E501
    },
    # COUNTRIES INDEX additional
    "We start with a focused MVP perimeter and extend country by country, only after legal sources are validated. Each country progresses through three states: in preparation, requires legal validation, available.": {  # noqa: E501
        "it": "Partiamo da un perimetro MVP mirato ed estendiamo paese per paese, solo dopo che le fonti legali sono validate. Ogni paese attraversa tre stati: in preparazione, richiede validazione legale, disponibile.",  # noqa: E501
        "fr": "Nous partons d'un périmètre MVP ciblé et nous étendons pays par pays, uniquement après validation des sources juridiques. Chaque pays passe par trois états : en préparation, validation juridique requise, disponible.",  # noqa: E501
        "ar": "ننطلق من نطاق إصدار أولي مركّز ونتوسع بلدًا بعد آخر، فقط بعد التحقق من المصادر القانونية. يمرّ كل بلد بثلاث حالات: قيد الإعداد، يتطلب التحقق القانوني، متاح.",  # noqa: E501
    },
    "A calculator is registered for this country. Real estimates require approved legal sources.": {  # noqa: E501
        "it": "È registrato un calcolatore per questo paese. Le stime reali richiedono fonti legali approvate.",  # noqa: E501
        "fr": "Un calculateur est enregistré pour ce pays. Les estimations réelles requièrent des sources juridiques approuvées.",  # noqa: E501
        "ar": "تم تسجيل حاسبة لهذا البلد. تتطلب التقديرات الفعلية مصادر قانونية معتمدة.",
    },
    'A calculator scaffold is registered. Legal sources are still under Studio review, so the wizard returns "requires legal validation" and never invents numbers.': {  # noqa: E501
        "it": 'È registrato uno scaffold del calcolatore. Le fonti legali sono ancora in revisione, quindi la procedura risponde "richiede validazione legale" e non inventa numeri.',  # noqa: E501
        "fr": "Un canevas de calculateur est enregistré. Les sources juridiques sont en cours de revue, l'assistant répond donc « validation juridique requise » et n'invente aucun chiffre.",  # noqa: E501
        "ar": 'تم تسجيل هيكل حاسبة. لا تزال المصادر القانونية قيد المراجعة، لذا يردّ المعالج "بحاجة إلى تحقق قانوني" ولا يختلق أرقامًا.',  # noqa: E501
    },
    "Modules for this country are being prepared. Sources are still under legal validation.": {  # noqa: E501
        "it": "I moduli per questo paese sono in preparazione. Le fonti sono ancora in validazione legale.",  # noqa: E501
        "fr": "Les modules pour ce pays sont en préparation. Les sources sont en cours de validation juridique.",  # noqa: E501
        "ar": "تجري حاليًا تحضير وحدات هذا البلد. لا تزال المصادر قيد التحقق القانوني.",
    },
    "Future jurisdictions on the roadmap include Spain, Germany, Canada, Romania, Algeria and Egypt.": {  # noqa: E501
        "it": "Le giurisdizioni future in roadmap includono Spagna, Germania, Canada, Romania, Algeria ed Egitto.",  # noqa: E501
        "fr": "Les juridictions futures à la feuille de route incluent l'Espagne, l'Allemagne, le Canada, la Roumanie, l'Algérie et l'Égypte.",  # noqa: E501
        "ar": "تشمل الاختصاصات المستقبلية في خارطة الطريق إسبانيا وألمانيا وكندا ورومانيا والجزائر ومصر.",  # noqa: E501
    },
    "Need a direct review?": {
        "it": "Hai bisogno di una valutazione diretta?",
        "fr": "Besoin d'une revue directe ?",
        "ar": "هل تحتاج إلى مراجعة مباشرة؟",
    },
    "Request a legal review on a complex case": {
        "it": "Richiedi una valutazione legale su un caso complesso",
        "fr": "Demander une revue juridique sur un cas complexe",
        "ar": "اطلب مراجعة قانونية لقضية معقدة",
    },
    'If your case spans multiple jurisdictions, includes foreign assets, or the calculator status reads "Legal sources under review", the Studio team can review the file directly and propose the next step.': {  # noqa: E501
        "it": 'Se il tuo caso coinvolge più giurisdizioni, beni esteri, o il calcolatore indica "fonti legali in revisione", il team dello Studio può esaminare il fascicolo direttamente e proporre il passo successivo.',  # noqa: E501
        "fr": "Si votre dossier concerne plusieurs juridictions, des actifs étrangers, ou si le statut du calculateur indique « sources juridiques en cours de revue », l'équipe du Cabinet peut l'examiner directement et proposer la prochaine étape.",  # noqa: E501
        "ar": 'إذا كانت قضيتك تشمل عدة اختصاصات أو أصولًا أجنبية، أو إذا أشارت حالة الحاسبة إلى "المصادر القانونية قيد المراجعة"، فإن فريق المكتب يمكنه دراسة الملف مباشرةً واقتراح الخطوة التالية.',  # noqa: E501
    },
    # COUNTRY LANDING long copy
    "Studio Legale Badrane provides an indicative compensation simulation for %(country)s based on approved legal sources. The estimate is informative and never a guarantee of outcome.": {  # noqa: E501
        "it": "Lo Studio Legale Badrane fornisce una simulazione indicativa di risarcimento per %(country)s basata su fonti legali approvate. La stima è informativa e mai una garanzia di risultato.",  # noqa: E501
        "fr": "Le Cabinet Légal Badrane fournit une simulation d'indemnisation indicative pour %(country)s à partir de sources juridiques approuvées. L'estimation est informative et ne constitue jamais une garantie de résultat.",  # noqa: E501
        "ar": "يقدّم مكتب بدران للمحاماة محاكاة إرشادية للتعويض عن %(country)s استنادًا إلى مصادر قانونية معتمدة. التقدير ذو طابع إعلامي ولا يشكّل أبدًا ضمانًا للنتيجة.",  # noqa: E501
    },
    "Legal sources for %(country)s are currently under Studio review. The wizard accepts your request and our team replies after a manual legal validation. No automatic estimate is issued until that review is complete.": {  # noqa: E501
        "it": "Le fonti legali per %(country)s sono attualmente in revisione presso lo Studio. La procedura raccoglie la richiesta e il nostro team risponde dopo una validazione legale manuale. Nessuna stima automatica viene emessa finché la revisione non è completa.",  # noqa: E501
        "fr": "Les sources juridiques pour %(country)s sont actuellement en cours de revue par le Cabinet. L'assistant enregistre votre demande et notre équipe répond après une validation juridique manuelle. Aucune estimation automatique n'est émise tant que la revue n'est pas terminée.",  # noqa: E501
        "ar": "المصادر القانونية لـ %(country)s قيد المراجعة حاليًا لدى المكتب. يستقبل المعالج طلبك ويردّ فريقنا بعد تحقق قانوني يدوي. لا تصدر أي تقديرات تلقائية قبل اكتمال المراجعة.",  # noqa: E501
    },
    "%(country)s — what we currently cover": {
        "it": "%(country)s — cosa copriamo attualmente",
        "fr": "%(country)s — ce que nous couvrons actuellement",
        "ar": "%(country)s — ما نغطّيه حاليًا",
    },
    "%(country)s — coverage and legal sources": {
        "it": "%(country)s — copertura e fonti legali",
        "fr": "%(country)s — couverture et sources juridiques",
        "ar": "%(country)s — التغطية والمصادر القانونية",
    },
    "Indicative compensation simulation for %(country)s, based on approved legal sources. The estimate is informative and never a guarantee of outcome.": {  # noqa: E501
        "it": "Simulazione indicativa di risarcimento per %(country)s, basata su fonti legali approvate. La stima è informativa e mai una garanzia di risultato.",  # noqa: E501
        "fr": "Simulation d'indemnisation indicative pour %(country)s, fondée sur des sources juridiques approuvées. L'estimation est informative et ne garantit jamais aucun résultat.",  # noqa: E501
        "ar": "محاكاة تعويض إرشادية لـ %(country)s، استنادًا إلى مصادر قانونية معتمدة. التقدير ذو طابع إعلامي ولا يضمن أي نتيجة.",  # noqa: E501
    },
    "%(country)s legal sources are under Studio review. No automatic estimate is currently issued; the wizard collects your request for a legal review.": {  # noqa: E501
        "it": "Le fonti legali per %(country)s sono in revisione presso lo Studio. Nessuna stima automatica viene attualmente emessa; la procedura raccoglie la richiesta per una valutazione legale.",  # noqa: E501
        "fr": "Les sources juridiques pour %(country)s sont en cours de revue par le Cabinet. Aucune estimation automatique n'est actuellement émise ; l'assistant enregistre votre demande pour une revue juridique.",  # noqa: E501
        "ar": "المصادر القانونية لـ %(country)s قيد المراجعة لدى المكتب. لا تصدر حاليًا أي تقديرات تلقائية؛ يستقبل المعالج طلبك من أجل المراجعة القانونية.",  # noqa: E501
    },
    "The wizard accepts compatible inputs and returns an indicative range based on the approved dataset.": {  # noqa: E501
        "it": "La procedura accetta input compatibili e restituisce un intervallo indicativo basato sul dataset approvato.",  # noqa: E501
        "fr": "L'assistant accepte des entrées compatibles et retourne une fourchette indicative fondée sur le jeu de données approuvé.",  # noqa: E501
        "ar": "يقبل المعالج المدخلات المتوافقة ويعيد نطاقًا إرشاديًا استنادًا إلى مجموعة البيانات المعتمدة.",  # noqa: E501
    },
    'The wizard collects your request and persists it. The calculator is in scaffold mode: response is "requires legal validation" — no automatic estimate is issued.': {  # noqa: E501
        "it": 'La procedura raccoglie e archivia la richiesta. Il calcolatore è in modalità scaffold: la risposta è "richiede validazione legale" — nessuna stima automatica viene emessa.',  # noqa: E501
        "fr": "L'assistant enregistre votre demande. Le calculateur est en mode canevas : la réponse est « validation juridique requise » — aucune estimation automatique n'est émise.",  # noqa: E501
        "ar": 'يجمع المعالج طلبك ويحتفظ به. الحاسبة في وضع هيكلي: الرد هو "بحاجة إلى تحقق قانوني" — لا تصدر أي تقديرات تلقائية.',  # noqa: E501
    },
    'Approved sources have been validated by the Studio\'s legal team. Sources marked as "needs review" are catalogued but cannot drive any public estimate yet.': {  # noqa: E501
        "it": 'Le fonti approvate sono state validate dal team legale dello Studio. Le fonti marcate come "in revisione" sono catalogate ma non possono ancora alimentare alcuna stima pubblica.',  # noqa: E501
        "fr": "Les sources approuvées ont été validées par l'équipe juridique du Cabinet. Les sources marquées « à revoir » sont cataloguées mais ne peuvent pas encore alimenter une estimation publique.",  # noqa: E501
        "ar": 'المصادر المعتمدة تم التحقق منها من قِبل الفريق القانوني للمكتب. أما المصادر المُعلَّمة بـ "بحاجة إلى مراجعة" فهي مفهرسة ولا يمكنها بعد دعم أي تقدير عام.',  # noqa: E501
    },
    "This page is informative. Any simulation provided by the platform is indicative and does not constitute legal, medical-legal advice nor a guarantee of outcome. The actual valuation depends on documents, expert reports, liability, applicable law, competent jurisdiction, judicial orientations and insurance practice.": {  # noqa: E501
        "it": "Questa pagina è informativa. Qualsiasi simulazione fornita dalla piattaforma è indicativa e non costituisce parere legale, medico-legale, né garanzia di risultato. La valutazione effettiva dipende da documenti, perizie, responsabilità, legge applicabile, giurisdizione competente, orientamenti giudiziari e prassi assicurative.",  # noqa: E501
        "fr": "Cette page est informative. Toute simulation fournie par la plateforme est indicative et ne constitue ni avis juridique, ni avis médico-légal, ni garantie de résultat. L'évaluation effective dépend des documents, expertises, responsabilités, droit applicable, juridiction compétente, orientations jurisprudentielles et pratiques assurantielles.",  # noqa: E501
        "ar": "هذه الصفحة إعلامية. أي محاكاة تقدّمها المنصة ذات طابع إرشادي ولا تشكّل رأيًا قانونيًا أو طبيًا قانونيًا أو ضمانًا للنتيجة. يعتمد التقييم الفعلي على المستندات والخبرات والمسؤولية والقانون الواجب التطبيق والاختصاص القضائي والتوجهات القضائية والممارسات التأمينية.",  # noqa: E501
    },
    "No automatic estimate is currently issued until legal review is complete.": {
        "it": "Attualmente nessuna stima automatica viene emessa finché la revisione legale non è completa.",  # noqa: E501
        "fr": "Aucune estimation automatique n'est émise tant que la revue juridique n'est pas terminée.",  # noqa: E501
        "ar": "لا تصدر حاليًا أي تقديرات تلقائية إلى حين اكتمال المراجعة القانونية.",
    },
    # WIZARD START copy
    'Pick the country and the case type that best fits your situation. The simulation is indicative: it will only produce an estimate when validated legal sources are available — otherwise it returns a clear "requires legal validation" status.': {  # noqa: E501
        "it": 'Scegli il paese e il tipo di caso più adatto alla tua situazione. La simulazione è indicativa: produrrà una stima solo se sono disponibili fonti legali validate — altrimenti restituisce uno stato chiaro "richiede validazione legale".',  # noqa: E501
        "fr": "Choisissez le pays et le type de cas le mieux adapté à votre situation. La simulation est indicative : elle ne produira une estimation que si des sources juridiques validées sont disponibles — sinon elle retourne un statut clair « validation juridique requise ».",  # noqa: E501
        "ar": 'اختر البلد ونوع القضية الأنسب لحالتك. المحاكاة إرشادية: لن تُنتج تقديرًا إلا إذا كانت المصادر القانونية المعتمدة متاحة — وإلا فإنها تُرجع حالة واضحة "بحاجة إلى تحقق قانوني".',  # noqa: E501
    },
    "Module ready": {
        "it": "Modulo pronto",
        "fr": "Module prêt",
        "ar": "الوحدة جاهزة",
    },
    # CONTACT page
    "Tell us about your case in your own words. A member of the Studio will get back to you to evaluate whether and how we can help.": {  # noqa: E501
        "it": "Raccontaci il tuo caso con parole tue. Un membro dello Studio ti risponderà per valutare se e come possiamo aiutarti.",  # noqa: E501
        "fr": "Décrivez votre cas avec vos propres mots. Un membre du Cabinet vous répondra pour évaluer si et comment nous pouvons vous aider.",  # noqa: E501
        "ar": "اشرح قضيتك بكلماتك. سيردّ عليك أحد أعضاء المكتب لتقييم ما إذا كان بإمكاننا مساعدتك وكيفية ذلك.",  # noqa: E501
    },
    # ---------------------------------------------------------------------
    # PASS 2 batch B — short labels, CTAs, footer items, status badges
    # ---------------------------------------------------------------------
    "(optional)": {"it": "(facoltativo)", "fr": "(facultatif)", "ar": "(اختياري)"},
    "About the accident": {
        "it": "Informazioni sull'incidente",
        "fr": "À propos de l'accident",
        "ar": "حول الحادث",
    },
    "About the deceased": {
        "it": "Informazioni sul defunto",
        "fr": "À propos du défunt",
        "ar": "حول المتوفى",
    },
    "Assets and context": {
        "it": "Beni e contesto",
        "fr": "Actifs et contexte",
        "ar": "الأصول والسياق",
    },
    "Assumptions": {
        "it": "Ipotesi",
        "fr": "Hypothèses",
        "ar": "الافتراضات",
    },
    "Back to homepage": {
        "it": "Torna alla home",
        "fr": "Retour à l'accueil",
        "ar": "العودة إلى الرئيسية",
    },
    "Back to methodology": {
        "it": "Torna alla metodologia",
        "fr": "Retour à la méthodologie",
        "ar": "العودة إلى المنهجية",
    },
    "Choose language": {
        "it": "Scegli la lingua",
        "fr": "Choisir la langue",
        "ar": "اختر اللغة",
    },
    "Cited legal sources": {
        "it": "Fonti legali citate",
        "fr": "Sources juridiques citées",
        "ar": "المصادر القانونية المُستشهد بها",
    },
    "Coming next": {
        "it": "Prossimamente",
        "fr": "À venir",
        "ar": "قريبًا",
    },
    "Coming soon": {
        "it": "In arrivo",
        "fr": "Bientôt",
        "ar": "قريبًا",
    },
    "Cookies": {"it": "Cookie", "fr": "Cookies", "ar": "ملفات تعريف الارتباط"},
    "Created at": {
        "it": "Creato il",
        "fr": "Créé le",
        "ar": "أُنشئ في",
    },
    "Documented economic impact": {
        "it": "Impatto economico documentato",
        "fr": "Impact économique documenté",
        "ar": "الأثر الاقتصادي الموثق",
    },
    "Download PDF report": {
        "it": "Scarica report PDF",
        "fr": "Télécharger le rapport PDF",
        "ar": "تنزيل تقرير PDF",
    },
    "Important": {
        "it": "Importante",
        "fr": "Important",
        "ar": "مهم",
    },
    "Indicative range": {
        "it": "Intervallo indicativo",
        "fr": "Fourchette indicative",
        "ar": "نطاق إرشادي",
    },
    "Indicative simulation wizard": {
        "it": "Procedura di simulazione indicativa",
        "fr": "Assistant de simulation indicatif",
        "ar": "معالج المحاكاة الإرشادية",
    },
    "Indicative simulations. Not legal advice.": {
        "it": "Simulazioni indicative. Non costituiscono parere legale.",
        "fr": "Simulations indicatives. Ne constituent pas un avis juridique.",
        "ar": "محاكاة إرشادية. لا تُعدّ رأيًا قانونيًا.",
    },
    "Injury and disability": {
        "it": "Lesione e invalidità",
        "fr": "Blessure et incapacité",
        "ar": "الإصابة والعجز",
    },
    "Institutional website": {
        "it": "Sito istituzionale",
        "fr": "Site institutionnel",
        "ar": "الموقع المؤسسي",
    },
    "International legal practice with cross-border experience in compensation, inheritance and complex jurisdictional matters.": {  # noqa: E501
        "it": "Studio legale internazionale con esperienza transfrontaliera in risarcimenti, successioni e questioni giurisdizionali complesse.",  # noqa: E501
        "fr": "Cabinet juridique international avec expérience transfrontalière en indemnisation, succession et questions juridictionnelles complexes.",  # noqa: E501
        "ar": "ممارسة قانونية دولية ذات خبرة عابرة للحدود في التعويضات والميراث والمسائل الاختصاصية المعقدة.",  # noqa: E501
    },
    "Notice.": {"it": "Avviso.", "fr": "Avis.", "ar": "تنبيه."},
    "Notice": {"it": "Avviso", "fr": "Avis", "ar": "تنبيه"},
    "PDF attached": {
        "it": "PDF allegato",
        "fr": "PDF joint",
        "ar": "PDF مرفق",
    },
    "Platform": {"it": "Piattaforma", "fr": "Plateforme", "ar": "المنصة"},
    "Legal": {"it": "Legale", "fr": "Juridique", "ar": "قانوني"},
    "Privacy notice": {
        "it": "Informativa privacy",
        "fr": "Avis de confidentialité",
        "ar": "إشعار الخصوصية",
    },
    "Read the full disclaimer": {
        "it": "Leggi il disclaimer completo",
        "fr": "Lire l'avertissement complet",
        "ar": "اقرأ إخلاء المسؤولية الكامل",
    },
    "Read the privacy notice": {
        "it": "Leggi l'informativa privacy",
        "fr": "Lire l'avis de confidentialité",
        "ar": "اقرأ إشعار الخصوصية",
    },
    "Recap of inputs": {
        "it": "Riepilogo dei dati inseriti",
        "fr": "Récapitulatif des saisies",
        "ar": "ملخص المدخلات",
    },
    "Reference dataset: Tabella Unica Nazionale 2025 (D.P.R. 12/2025), with the biological component and the moral range (Tabelle 2.A/2.B/2.C).": {  # noqa: E501
        "it": "Dataset di riferimento: Tabella Unica Nazionale 2025 (D.P.R. 12/2025), con la componente biologica e l'intervallo morale (Tabelle 2.A/2.B/2.C).",  # noqa: E501
        "fr": "Jeu de données de référence : Tabella Unica Nazionale 2025 (D.P.R. 12/2025), avec la composante biologique et la fourchette morale (Tabelle 2.A/2.B/2.C).",  # noqa: E501
        "ar": "مجموعة البيانات المرجعية: Tabella Unica Nazionale 2025 (D.P.R. 12/2025) مع المكوّن البيولوجي والنطاق الأدبي (Tabelle 2.A/2.B/2.C).",  # noqa: E501
    },
    "Road traffic accident — bodily injury (danno biologico) under Italian law.": {  # noqa: E501
        "it": "Incidente stradale — danno biologico secondo il diritto italiano.",
        "fr": "Accident de la circulation — dommage corporel selon le droit italien.",
        "ar": "حادث مرور — ضرر جسدي وفق القانون الإيطالي.",
    },
    "Road traffic accident — bodily injury (préjudice corporel) under French law.": {  # noqa: E501
        "it": "Incidente stradale — préjudice corporel secondo il diritto francese.",
        "fr": "Accident de la circulation — préjudice corporel selon le droit français.",
        "ar": "حادث مرور — ضرر جسدي وفق القانون الفرنسي.",
    },
    "Road traffic accident — bodily injury under Belgian law.": {
        "it": "Incidente stradale — danno corporale secondo il diritto belga.",
        "fr": "Accident de la circulation — dommage corporel selon le droit belge.",
        "ar": "حادث مرور — ضرر جسدي وفق القانون البلجيكي.",
    },
    "International inheritance with Moroccan elements — heirs, foreign assets, applicable law.": {  # noqa: E501
        "it": "Successione internazionale con elementi marocchini — eredi, beni esteri, legge applicabile.",  # noqa: E501
        "fr": "Succession internationale avec éléments marocains — héritiers, actifs étrangers, droit applicable.",  # noqa: E501
        "ar": "ميراث دولي بعناصر مغربية — الورثة، الأصول الأجنبية، القانون الواجب التطبيق.",  # noqa: E501
    },
    "International inheritance with Tunisian elements — heirs, foreign assets, applicable law.": {  # noqa: E501
        "it": "Successione internazionale con elementi tunisini — eredi, beni esteri, legge applicabile.",  # noqa: E501
        "fr": "Succession internationale avec éléments tunisiens — héritiers, actifs étrangers, droit applicable.",  # noqa: E501
        "ar": "ميراث دولي بعناصر تونسية — الورثة، الأصول الأجنبية، القانون الواجب التطبيق.",  # noqa: E501
    },
    "Reference framework: Moudawana (Code de la famille, Loi 70-03), Code des droits réels and EU Succession Regulation 650/2012.": {  # noqa: E501
        "it": "Quadro di riferimento: Moudawana (Code de la famille, Loi 70-03), Code des droits réels e Regolamento UE Successioni 650/2012.",  # noqa: E501
        "fr": "Cadre de référence : Moudawana (Code de la famille, Loi 70-03), Code des droits réels et Règlement UE Successions 650/2012.",  # noqa: E501
        "ar": "الإطار المرجعي: المدوّنة (قانون الأسرة 70-03)، قانون الحقوق العينية، ولائحة الاتحاد الأوروبي للمواريث 650/2012.",  # noqa: E501
    },
    "Reference framework: Code du statut personnel — Livre IX, Loi n°98-97 (Code de droit international privé), EU Regulation 650/2012.": {  # noqa: E501
        "it": "Quadro di riferimento: Code du statut personnel — Livre IX, Loi n°98-97 (Codice di diritto internazionale privato), Regolamento UE 650/2012.",  # noqa: E501
        "fr": "Cadre de référence : Code du statut personnel — Livre IX, Loi n°98-97 (Code de droit international privé), Règlement UE 650/2012.",  # noqa: E501
        "ar": "الإطار المرجعي: مجلة الأحوال الشخصية — الكتاب التاسع، القانون عدد 98-97 (مجلة القانون الدولي الخاص)، لائحة الاتحاد الأوروبي 650/2012.",  # noqa: E501
    },
    "The wizard collects qualitative inputs; no automatic share calculation is performed yet.": {  # noqa: E501
        "it": "La procedura raccoglie input qualitativi; nessun calcolo automatico delle quote viene ancora eseguito.",  # noqa: E501
        "fr": "L'assistant recueille des entrées qualitatives ; aucun calcul automatique des parts n'est encore effectué.",  # noqa: E501
        "ar": "يجمع المعالج مدخلات نوعية؛ لا يُجرى حتى الآن أي حساب تلقائي للحصص.",
    },
    'The wizard is in scaffold mode: it returns "requires legal validation" rather than a number.': {  # noqa: E501
        "it": 'La procedura è in modalità scaffold: restituisce "richiede validazione legale" anziché un numero.',  # noqa: E501
        "fr": "L'assistant est en mode canevas : il retourne « validation juridique requise » plutôt qu'un nombre.",  # noqa: E501
        "ar": 'المعالج في وضع هيكلي: يردّ "بحاجة إلى تحقق قانوني" بدلًا من رقم.',
    },
    "The wizard is in scaffold mode and never invents amounts.": {
        "it": "La procedura è in modalità scaffold e non inventa mai importi.",
        "fr": "L'assistant est en mode canevas et n'invente jamais de montants.",
        "ar": "المعالج في وضع هيكلي ولا يختلق أي مبالغ.",
    },
    "Candidate sources under Studio review: Référentiel Mornet 2024 and Barème de capitalisation Gazette du Palais 2022.": {  # noqa: E501
        "it": "Fonti candidate in revisione presso lo Studio: Référentiel Mornet 2024 e Barème de capitalisation Gazette du Palais 2022.",  # noqa: E501
        "fr": "Sources candidates en cours de revue au Cabinet : Référentiel Mornet 2024 et Barème de capitalisation Gazette du Palais 2022.",  # noqa: E501
        "ar": "المصادر المرشّحة قيد المراجعة لدى المكتب: Référentiel Mornet 2024 و Barème de capitalisation Gazette du Palais 2022.",  # noqa: E501
    },
    "Candidate sources under Studio review: Tableau Indicatif 2020, Tableau Indicatif 2024 and Tables Schryvers for capitalisation.": {  # noqa: E501
        "it": "Fonti candidate in revisione presso lo Studio: Tableau Indicatif 2020, Tableau Indicatif 2024 e Tables Schryvers per la capitalizzazione.",  # noqa: E501
        "fr": "Sources candidates en cours de revue au Cabinet : Tableau Indicatif 2020, Tableau Indicatif 2024 et Tables Schryvers pour la capitalisation.",  # noqa: E501
        "ar": "المصادر المرشّحة قيد المراجعة لدى المكتب: Tableau Indicatif 2020 و Tableau Indicatif 2024 وجداول Schryvers للرسملة.",  # noqa: E501
    },
    "Approved TUN 2025 dataset feeds an indicative range (minimum, central, maximum). Result is not legal advice.": {  # noqa: E501
        "it": "Il dataset TUN 2025 approvato alimenta un intervallo indicativo (minimo, centrale, massimo). Il risultato non costituisce parere legale.",  # noqa: E501
        "fr": "Le jeu de données TUN 2025 approuvé alimente une fourchette indicative (minimum, centrale, maximum). Le résultat ne constitue pas un avis juridique.",  # noqa: E501
        "ar": "تُغذّي مجموعة بيانات TUN 2025 المعتمدة نطاقًا إرشاديًا (الحد الأدنى، الوسط، الأقصى). النتيجة لا تشكل رأيًا قانونيًا.",  # noqa: E501
    },
    "Provide age, disability percentage and fault percentage. The wizard returns an indicative range based on the approved TUN 2025 dataset.": {  # noqa: E501
        "it": "Inserisci età, percentuale di invalidità e percentuale di colpa. La procedura restituisce un intervallo indicativo basato sul dataset TUN 2025 approvato.",  # noqa: E501
        "fr": "Indiquez l'âge, le pourcentage d'incapacité et le pourcentage de faute. L'assistant retourne une fourchette indicative fondée sur le jeu de données TUN 2025 approuvé.",  # noqa: E501
        "ar": "أدخل العمر ونسبة العجز ونسبة الخطأ. يُرجع المعالج نطاقًا إرشاديًا استنادًا إلى مجموعة بيانات TUN 2025 المعتمدة.",  # noqa: E501
    },
    "Open the country wizard to share the case context. We persist the request and reply after a manual legal review. No automatic estimate is issued.": {  # noqa: E501
        "it": "Apri la procedura del paese per condividere il contesto del caso. Archiviamo la richiesta e rispondiamo dopo una revisione legale manuale. Nessuna stima automatica viene emessa.",  # noqa: E501
        "fr": "Ouvrez l'assistant pays pour partager le contexte de l'affaire. Nous enregistrons la demande et répondons après une revue juridique manuelle. Aucune estimation automatique n'est émise.",  # noqa: E501
        "ar": "افتح معالج البلد لمشاركة سياق القضية. نحتفظ بالطلب ونردّ بعد مراجعة قانونية يدوية. لا تصدر أي تقديرات تلقائية.",  # noqa: E501
    },
    "If the case is complex, write to the Studio. A lawyer reviews the file, identifies applicable law and competent jurisdiction, and proposes the next step.": {  # noqa: E501
        "it": "Se il caso è complesso, scrivi allo Studio. Un avvocato esamina il fascicolo, identifica legge applicabile e giurisdizione competente, e propone il passo successivo.",  # noqa: E501
        "fr": "Si le dossier est complexe, écrivez au Cabinet. Un avocat l'examine, identifie le droit applicable et la juridiction compétente, et propose la prochaine étape.",  # noqa: E501
        "ar": "إذا كانت القضية معقدة، اكتب إلى المكتب. يدرس محامٍ الملف ويحدد القانون الواجب التطبيق والاختصاص القضائي ويقترح الخطوة التالية.",  # noqa: E501
    },
    'I have read the <a href="/privacy/" class="underline">privacy notice</a> and consent to processing the data above for the sole purpose of producing an indicative simulation.': {  # noqa: E501
        "it": 'Ho letto l\'<a href="/privacy/" class="underline">informativa privacy</a> e acconsento al trattamento dei dati indicati al solo fine di produrre una simulazione indicativa.',  # noqa: E501
        "fr": 'J\'ai lu l\'<a href="/privacy/" class="underline">avis de confidentialité</a> et consens au traitement des données ci-dessus dans le seul but de produire une simulation indicative.',  # noqa: E501
        "ar": 'لقد قرأت <a href="/privacy/" class="underline">إشعار الخصوصية</a> وأوافق على معالجة البيانات أعلاه لغرض إنتاج محاكاة إرشادية فقط.',  # noqa: E501
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


def _po_escape(s: str) -> str:
    """Escape Python string for `.po` storage: backslash + double quote."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def update_po(po_path: Path, lang: str) -> int:
    """Aggiorna il `.po` con le traduzioni della mappa per `lang`. Ritorna count aggiornati.

    Gestisce sia msgid single-line (la maggior parte, dato che usiamo
    `--no-wrap` su `makemessages`) che gli msgstr vuoti che vogliamo
    sostituire. Se la traduzione contiene `\\` o `"`, vengono escapati
    come da formato `.po`.
    """
    text = po_path.read_text(encoding="utf-8")
    updated = 0
    for msgid, by_lang in TRANSLATIONS.items():
        translated = by_lang.get(lang)
        if translated is None:
            continue
        po_msgid = _po_escape(msgid)
        po_msgstr = _po_escape(translated)
        pattern = re.compile(
            r'(^msgid "' + re.escape(po_msgid) + r'"\nmsgstr ")"',
            flags=re.MULTILINE,
        )
        new_text, n = pattern.subn(r"\1" + po_msgstr + '"', text)
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
