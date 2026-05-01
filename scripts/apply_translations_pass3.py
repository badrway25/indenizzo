"""
Apply manual translations to locale/{it,fr,ar}/LC_MESSAGES/django.po.

Iter: F-product-i18n-translations-pass3-visible-copy.

Modus operandi: il dict `TRANSLATIONS` mappa ogni `msgid` (testo source
in inglese, esattamente come compare nei template gettext) a un dict
`{it, fr, ar}`. Lo script:

1. Apre il `.po` per ogni lingua;
2. Per ogni `msgid` nel dict, cerca l'entry corrispondente nel `.po`
   e sostituisce il `msgstr` (anche se non vuoto).
3. Riscrive il `.po`.

Non tocca msgid non presenti nel dict — quindi è sicuro ri-eseguirlo.

Politiche di traduzione:
- Termini legali nominali NON tradotti: D.P.R., Mornet, Gazette du
  Palais, Tableau Indicatif, Moudawana, Loi 98-97, Reg. UE 650/2012,
  CAP, TUN, Code de la famille, ecc. Se un msgid li contiene, la
  traduzione li lascia inalterati nel testo target.
- Brand: "Studio Legale Internazionale" e "Cabinet" → mantenuti.
- AR: per i termini legali stranieri lasciamo il nome originale tra
  parentesi/virgolette quando il template lo permette.
- Tono autorevole, non assicurativo. Mai "ottenere risarcimento" /
  "obtenez votre indemnisation": sempre "valutazione legale" /
  "évaluation juridique".
"""

from __future__ import annotations

import sys
from pathlib import Path

# fmt: off
TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- Languages (used in <select> form fields) ----------------------------
    "Italiano": {"it": "Italiano",   "fr": "Italien",   "ar": "إيطالية"},
    "Français": {"it": "Francese",   "fr": "Français",  "ar": "فرنسية"},
    "English":  {"it": "Inglese",    "fr": "Anglais",   "ar": "إنجليزية"},
    "العربية":  {"it": "Arabo",      "fr": "Arabe",     "ar": "العربية"},

    # --- Case types (visible in wizard, contact, country pages) -------------
    "Road accident — bodily injury": {
        "it": "Incidente stradale — danno biologico",
        "fr": "Accident de la route — préjudice corporel",
        "ar": "حادث طريق — أضرار جسدية",
    },
    "Medical malpractice": {
        "it": "Responsabilità medica",
        "fr": "Responsabilité médicale",
        "ar": "مسؤولية طبية",
    },
    "Work injury": {
        "it": "Infortunio sul lavoro",
        "fr": "Accident du travail",
        "ar": "إصابة عمل",
    },
    "Death compensation": {
        "it": "Risarcimento da morte",
        "fr": "Indemnisation pour décès",
        "ar": "تعويض عن الوفاة",
    },
    "Parental loss": {
        "it": "Perdita del rapporto parentale",
        "fr": "Perte du lien parental",
        "ar": "فقدان الرابطة الأبوية",
    },
    "Patrimonial damage": {
        "it": "Danno patrimoniale",
        "fr": "Préjudice patrimonial",
        "ar": "ضرر مالي",
    },
    "Inheritance — basic": {
        "it": "Successione — base",
        "fr": "Succession — base",
        "ar": "ميراث — أساسي",
    },
    "Inheritance — international": {
        "it": "Successione — internazionale",
        "fr": "Succession — internationale",
        "ar": "ميراث — دولي",
    },
    "Generic legal assessment": {
        "it": "Valutazione legale generica",
        "fr": "Évaluation juridique générique",
        "ar": "تقييم قانوني عام",
    },
    # --- Status / confidence labels -----------------------------------------
    "Unavailable — requires legal validation": {
        "it": "Non disponibile — richiede validazione legale",
        "fr": "Non disponible — validation juridique requise",
        "ar": "غير متاح — يتطلب تحقق قانوني",
    },
    "Insufficient input": {
        "it": "Dati insufficienti",
        "fr": "Données insuffisantes",
        "ar": "مدخلات غير كافية",
    },
    "Calculated": {
        "it": "Calcolato",
        "fr": "Calculé",
        "ar": "محسوب",
    },
    "Error": {"it": "Errore", "fr": "Erreur", "ar": "خطأ"},
    "Low":    {"it": "Bassa",  "fr": "Faible", "ar": "منخفض"},
    "Medium": {"it": "Media",  "fr": "Moyenne","ar": "متوسط"},
    "High":   {"it": "Alta",   "fr": "Élevée", "ar": "مرتفع"},

    # --- Footer / disclaimer / cookies (visible everywhere) ------------------
    "This platform provides indicative simulations only. It is not legal, medico-legal advice nor a guarantee of outcome.": {
        "it": "Questa piattaforma fornisce esclusivamente simulazioni indicative. Non costituisce parere legale, medico-legale né garanzia di risultato.",
        "fr": "Cette plateforme fournit uniquement des simulations indicatives. Elle ne constitue ni un avis juridique, ni un avis médico-légal, ni une garantie de résultat.",
        "ar": "تقدّم هذه المنصة محاكاة إرشادية فقط. ولا تعدّ رأيًا قانونيًا أو طبيًا قانونيًا، ولا ضمانًا للنتيجة.",
    },
    "This site uses only strictly necessary technical cookies (session, CSRF). No analytics or marketing trackers are active.": {
        "it": "Questo sito utilizza solo cookie tecnici strettamente necessari (sessione, CSRF). Nessun cookie di analytics o marketing è attivo.",
        "fr": "Ce site utilise uniquement des cookies techniques strictement nécessaires (session, CSRF). Aucun traceur analytique ou marketing n'est actif.",
        "ar": "يستخدم هذا الموقع فقط ملفات تعريف الارتباط التقنية الضرورية (الجلسة، CSRF). لا تُستخدم أي أدوات تتبّع تحليلية أو تسويقية.",
    },
    "Visit institutional website": {
        "it": "Visita il sito istituzionale",
        "fr": "Visiter le site institutionnel",
        "ar": "زيارة الموقع المؤسسي",
    },
    "Studio Legale Internazionale": {
        "it": "Studio Legale Internazionale",
        "fr": "Cabinet Légal International",
        "ar": "المكتب القانوني الدولي",
    },
    "Cookie notice": {
        "it": "Informativa cookie",
        "fr": "Avis cookies",
        "ar": "إشعار ملفات تعريف الارتباط",
    },
    "Legal disclaimer": {
        "it": "Avvertenze legali",
        "fr": "Avertissement juridique",
        "ar": "إخلاء المسؤولية القانوني",
    },
    "Legal notice": {
        "it": "Note legali",
        "fr": "Mentions légales",
        "ar": "إشعار قانوني",
    },
    "OK": {"it": "OK", "fr": "OK", "ar": "موافق"},
    "Primary navigation": {
        "it": "Navigazione principale",
        "fr": "Navigation principale",
        "ar": "التنقل الرئيسي",
    },
    "Apply": {
        "it": "Conferma",
        "fr": "Appliquer",
        "ar": "تطبيق",
    },

    # --- Hero CTA -------------------------------------------------------------
    "Start Italian compensation simulation": {
        "it": "Avvia simulazione risarcimento Italia",
        "fr": "Lancer la simulation Italie",
        "ar": "ابدأ محاكاة التعويض في إيطاليا",
    },
    "%(site)s — International compensation simulator": {
        "it": "%(site)s — Simulatore di risarcimento internazionale",
        "fr": "%(site)s — Simulateur d'indemnisation international",
        "ar": "%(site)s — محاكي التعويضات الدولي",
    },
    "%(site)s — simulazioni indicative su risarcimenti e successioni internazionali, basate su fonti legali validate.": {
        "it": "%(site)s — simulazioni indicative su risarcimenti e successioni internazionali, basate su fonti legali validate.",
        "fr": "%(site)s — simulations indicatives sur les indemnisations et successions internationales, fondées sur des sources juridiques validées.",
        "ar": "%(site)s — محاكاة إرشادية للتعويضات والمواريث الدولية، مستندة إلى مصادر قانونية موثقة.",
    },

    # --- Wizard --------------------------------------------------------------
    "Start this simulation": {
        "it": "Avvia questa simulazione",
        "fr": "Lancer cette simulation",
        "ar": "ابدأ هذه المحاكاة",
    },
    "Open scaffold wizard": {
        "it": "Apri assistente in modalità canovaccio",
        "fr": "Ouvrir l'assistant en mode canevas",
        "ar": "افتح المعالج في الوضع الهيكلي",
    },
    "Each module is activated only after the underlying legal sources are catalogued and validated by the Studio.": {
        "it": "Ogni modulo viene attivato solo dopo che le fonti legali sottostanti sono catalogate e validate dallo Studio.",
        "fr": "Chaque module est activé uniquement après que les sources juridiques sous-jacentes ont été cataloguées et validées par le Cabinet.",
        "ar": "يتم تفعيل كل وحدة فقط بعد فهرسة المصادر القانونية الأساسية والتحقق منها من قبل المكتب.",
    },
    "A simulation is not legal advice. It is an informative starting point. The Studio remains free to accept or decline a matter.": {
        "it": "Una simulazione non è un parere legale. È un punto di partenza informativo. Lo Studio resta libero di accettare o rifiutare un caso.",
        "fr": "Une simulation n'est pas un avis juridique. C'est un point de départ informatif. Le Cabinet reste libre d'accepter ou de refuser un dossier.",
        "ar": "المحاكاة ليست رأيًا قانونيًا. إنها نقطة انطلاق إعلامية. يبقى المكتب حرًا في قبول أو رفض القضية.",
    },
    "Bodily injury after a road accident. The wizard collects optional inputs and persists a simulation. No estimate is produced unless validated legal sources are available.": {
        "it": "Danno biologico a seguito di incidente stradale. L'assistente raccoglie dati opzionali e salva la simulazione. Nessuna stima viene prodotta in assenza di fonti legali validate.",
        "fr": "Préjudice corporel après un accident de la route. L'assistant collecte des données optionnelles et enregistre la simulation. Aucune estimation n'est produite tant que des sources juridiques validées ne sont pas disponibles.",
        "ar": "أضرار جسدية بعد حادث طريق. يجمع المعالج مدخلات اختيارية ويحفظ المحاكاة. لا يصدر أي تقدير إلا إذا كانت المصادر القانونية المعتمدة متاحة.",
    },
    "Bodily injury after a road accident. The wizard accepts inputs but the legal sources are still under Studio review, so the simulation returns \"requires legal validation\" rather than a numeric estimate.": {
        "it": "Danno biologico a seguito di incidente stradale. L'assistente accetta dati ma le fonti legali sono ancora in revisione presso lo Studio, quindi la simulazione restituisce \"richiede validazione legale\" anziché una stima numerica.",
        "fr": "Préjudice corporel après un accident de la route. L'assistant accepte les données mais les sources juridiques sont encore en cours de revue par le Cabinet, la simulation retourne donc « validation juridique requise » plutôt qu'une estimation chiffrée.",
        "ar": "أضرار جسدية بعد حادث طريق. يقبل المعالج المدخلات لكن المصادر القانونية لا تزال قيد المراجعة لدى المكتب، لذا تُرجع المحاكاة \"بحاجة إلى تحقق قانوني\" بدل تقدير رقمي.",
    },

    # --- Contact form labels -------------------------------------------------
    "Website (do not fill)": {
        "it": "Sito web (non compilare)",
        "fr": "Site web (ne pas remplir)",
        "ar": "موقع الويب (لا تملأ)",
    },
    "First name": {
        "it": "Nome",
        "fr": "Prénom",
        "ar": "الاسم",
    },
    "Last name": {
        "it": "Cognome",
        "fr": "Nom",
        "ar": "اللقب",
    },
    "Email": {
        "it": "Email",
        "fr": "Courriel",
        "ar": "بريد إلكتروني",
    },
    "Phone number": {
        "it": "Telefono",
        "fr": "Téléphone",
        "ar": "رقم الهاتف",
    },
    "Preferred language": {
        "it": "Lingua preferita",
        "fr": "Langue préférée",
        "ar": "اللغة المفضّلة",
    },
    "Country": {
        "it": "Paese",
        "fr": "Pays",
        "ar": "البلد",
    },
    "Select a country (optional)": {
        "it": "Seleziona un paese (opzionale)",
        "fr": "Choisir un pays (optionnel)",
        "ar": "اختر بلدًا (اختياري)",
    },
    "Case type": {
        "it": "Tipo di caso",
        "fr": "Type d'affaire",
        "ar": "نوع القضية",
    },
    "Not specified": {
        "it": "Non specificato",
        "fr": "Non précisé",
        "ar": "غير محدّد",
    },
    "How can we help?": {
        "it": "Come possiamo aiutarti?",
        "fr": "Comment pouvons-nous vous aider ?",
        "ar": "كيف يمكننا مساعدتك؟",
    },
    "Briefly describe what happened, when, and where. Avoid sharing sensitive medical details now — we will request them only if needed.": {
        "it": "Descrivi brevemente cosa è accaduto, quando e dove. Evita di condividere dettagli medici sensibili adesso — li richiederemo solo se necessario.",
        "fr": "Décrivez brièvement ce qui s'est passé, quand et où. Évitez pour l'instant de partager des détails médicaux sensibles — nous vous les demanderons uniquement si nécessaire.",
        "ar": "صف بإيجاز ما حدث، ومتى، وأين. تجنّب الآن مشاركة تفاصيل طبية حساسة — سنطلبها فقط عند الحاجة.",
    },
    "I have read the <a href=\"/privacy/\" class=\"underline\">privacy notice</a> and the <a href=\"/disclaimer/\" class=\"underline\">disclaimer</a>, and I consent to my data being processed by the Studio for the sole purpose of replying to this request.": {
        "it": "Ho letto l'<a href=\"/privacy/\" class=\"underline\">informativa sulla privacy</a> e l'<a href=\"/disclaimer/\" class=\"underline\">avvertenza</a>, e acconsento al trattamento dei miei dati da parte dello Studio al solo scopo di rispondere a questa richiesta.",
        "fr": "J'ai lu l'<a href=\"/privacy/\" class=\"underline\">avis de confidentialité</a> et l'<a href=\"/disclaimer/\" class=\"underline\">avertissement</a>, et je consens au traitement de mes données par le Cabinet à seule fin de répondre à cette demande.",
        "ar": "لقد قرأت <a href=\"/privacy/\" class=\"underline\">إشعار الخصوصية</a> و<a href=\"/disclaimer/\" class=\"underline\">إخلاء المسؤولية</a>، وأوافق على معالجة بياناتي من قبل المكتب لغرض الرد على هذا الطلب فقط.",
    },
    "Submitting this form does not create a professional engagement.": {
        "it": "L'invio del modulo non costituisce conferimento di incarico professionale.",
        "fr": "L'envoi de ce formulaire ne crée pas de mandat professionnel.",
        "ar": "إرسال هذا النموذج لا يُنشئ تكليفًا مهنيًا.",
    },
    "Submitting this form does not create a professional engagement. The Studio remains free to accept or decline the matter.": {
        "it": "L'invio del modulo non costituisce conferimento di incarico professionale. Lo Studio resta libero di accettare o rifiutare il caso.",
        "fr": "L'envoi de ce formulaire ne crée pas de mandat professionnel. Le Cabinet reste libre d'accepter ou de refuser le dossier.",
        "ar": "إرسال هذا النموذج لا يُنشئ تكليفًا مهنيًا. يبقى المكتب حرًا في قبول أو رفض القضية.",
    },
    "Submitting this form does not create a professional engagement. No documents are collected.": {
        "it": "L'invio del modulo non costituisce conferimento di incarico professionale. Nessun documento viene raccolto.",
        "fr": "L'envoi de ce formulaire ne crée pas de mandat professionnel. Aucun document n'est collecté.",
        "ar": "إرسال هذا النموذج لا يُنشئ تكليفًا مهنيًا. لا تُجمع أي مستندات.",
    },
    "Send my request": {
        "it": "Invia la mia richiesta",
        "fr": "Envoyer ma demande",
        "ar": "إرسال طلبي",
    },
    "Request received": {
        "it": "Richiesta ricevuta",
        "fr": "Demande reçue",
        "ar": "تم استلام الطلب",
    },
    "Thank you": {
        "it": "Grazie",
        "fr": "Merci",
        "ar": "شكرًا لك",
    },
    "Your request has been received.": {
        "it": "La tua richiesta è stata ricevuta.",
        "fr": "Votre demande a bien été reçue.",
        "ar": "تم استلام طلبك.",
    },
    "A member of our team will review your request and get back to you. Cross-border cases may take a few working days to assess.": {
        "it": "Un membro del nostro team esaminerà la richiesta e ti risponderà. I casi transfrontalieri possono richiedere alcuni giorni lavorativi.",
        "fr": "Un membre de notre équipe examinera votre demande et vous recontactera. Les dossiers transfrontaliers peuvent demander quelques jours ouvrés.",
        "ar": "سيقوم أحد أعضاء فريقنا بمراجعة طلبك والرد عليك. قد تستغرق القضايا العابرة للحدود بضعة أيام عمل للتقييم.",
    },
    "I have read and accept the privacy notice.": {
        "it": "Ho letto e accetto l'informativa sulla privacy.",
        "fr": "J'ai lu et j'accepte l'avis de confidentialité.",
        "ar": "لقد قرأت إشعار الخصوصية وأوافق عليه.",
    },
    "You must accept the privacy notice to send your request.": {
        "it": "Devi accettare l'informativa sulla privacy per inviare la richiesta.",
        "fr": "Vous devez accepter l'avis de confidentialité pour envoyer votre demande.",
        "ar": "يجب الموافقة على إشعار الخصوصية لإرسال طلبك.",
    },
    "Please describe your case in at least %(n)d characters.": {
        "it": "Descrivi il tuo caso in almeno %(n)d caratteri.",
        "fr": "Veuillez décrire votre dossier en au moins %(n)d caractères.",
        "ar": "يرجى وصف قضيتك بـ %(n)d حرفًا على الأقل.",
    },

    # --- Wizard form fields (Italy bodily injury) ---------------------------
    "Date of the accident": {
        "it": "Data del sinistro",
        "fr": "Date de l'accident",
        "ar": "تاريخ الحادث",
    },
    "If you don't know the exact date, leave this empty.": {
        "it": "Se non conosci la data esatta, lascia il campo vuoto.",
        "fr": "Si vous ne connaissez pas la date exacte, laissez ce champ vide.",
        "ar": "إذا لم تعرف التاريخ بدقة، اترك هذا الحقل فارغًا.",
    },
    "Age of the injured person": {
        "it": "Età della persona infortunata",
        "fr": "Âge de la personne blessée",
        "ar": "عمر الشخص المصاب",
    },
    "Age at the time of the accident, in years.": {
        "it": "Età al momento del sinistro, in anni.",
        "fr": "Âge au moment de l'accident, en années.",
        "ar": "العمر وقت الحادث، بالسنوات.",
    },
    "Permanent disability (%)": {
        "it": "Invalidità permanente (%)",
        "fr": "Incapacité permanente (%)",
        "ar": "العجز الدائم (%)",
    },
    "Only if a medical report has assessed it. Otherwise leave empty.": {
        "it": "Solo se accertata da una perizia medico-legale. Altrimenti lascia vuoto.",
        "fr": "Uniquement si une expertise médicale l'a évaluée. Sinon, laissez vide.",
        "ar": "فقط إذا قام تقرير طبي بتقييمها. خلاف ذلك اترك الحقل فارغًا.",
    },
    "Total temporary disability — days": {
        "it": "Invalidità temporanea totale — giorni",
        "fr": "Incapacité temporaire totale — jours",
        "ar": "العجز المؤقت الكلي — أيام",
    },
    "Partial temporary disability — days": {
        "it": "Invalidità temporanea parziale — giorni",
        "fr": "Incapacité temporaire partielle — jours",
        "ar": "العجز المؤقت الجزئي — أيام",
    },
    "Documented medical expenses": {
        "it": "Spese mediche documentate",
        "fr": "Frais médicaux documentés",
        "ar": "نفقات طبية موثّقة",
    },
    "Currency: EUR. Only amounts you can document.": {
        "it": "Valuta: EUR. Solo importi che puoi documentare.",
        "fr": "Devise : EUR. Uniquement les montants que vous pouvez justifier.",
        "ar": "العملة: يورو. فقط المبالغ التي يمكنك إثباتها.",
    },
    "Lost income": {
        "it": "Reddito perso",
        "fr": "Revenu perdu",
        "ar": "الدخل المفقود",
    },
    "Currency: EUR. Net income lost due to the accident.": {
        "it": "Valuta: EUR. Reddito netto perso a causa del sinistro.",
        "fr": "Devise : EUR. Revenu net perdu en raison de l'accident.",
        "ar": "العملة: يورو. الدخل الصافي المفقود بسبب الحادث.",
    },
    "Estimated own fault (%)": {
        "it": "Concorso di colpa stimato (%)",
        "fr": "Part de responsabilité personnelle estimée (%)",
        "ar": "الخطأ الذاتي المقدّر (%)",
    },
    "0% if you believe you bear no responsibility.": {
        "it": "0% se ritieni di non avere alcuna responsabilità.",
        "fr": "0 % si vous estimez n'avoir aucune responsabilité.",
        "ar": "0٪ إذا كنت تعتقد أنك لا تتحمّل أي مسؤولية.",
    },
    "I consent to processing the data above for the sole purpose of producing an indicative simulation.": {
        "it": "Acconsento al trattamento dei dati sopra al solo scopo di produrre una simulazione indicativa.",
        "fr": "Je consens au traitement des données ci-dessus aux seules fins de produire une simulation indicative.",
        "ar": "أوافق على معالجة البيانات أعلاه لغرض وحيد هو إنتاج محاكاة إرشادية.",
    },
    "You must accept the simulation consent to run a simulation.": {
        "it": "Devi accettare il consenso alla simulazione per eseguire una simulazione.",
        "fr": "Vous devez accepter le consentement à la simulation pour la lancer.",
        "ar": "يجب الموافقة على إذن المحاكاة لتشغيل المحاكاة.",
    },
    "The accident date cannot be in the future.": {
        "it": "La data del sinistro non può essere futura.",
        "fr": "La date de l'accident ne peut pas être dans le futur.",
        "ar": "لا يمكن أن يكون تاريخ الحادث في المستقبل.",
    },

    # --- Inheritance wizard fields ------------------------------------------
    "Country of the deceased's last domicile": {
        "it": "Paese dell'ultimo domicilio del defunto",
        "fr": "Pays du dernier domicile du défunt",
        "ar": "بلد آخر إقامة للمتوفى",
    },
    "ISO 3166-1 alpha-2 code, e.g. MA, TN, IT, FR, BE.": {
        "it": "Codice ISO 3166-1 alpha-2, es. MA, TN, IT, FR, BE.",
        "fr": "Code ISO 3166-1 alpha-2, par ex. MA, TN, IT, FR, BE.",
        "ar": "رمز ISO 3166-1 alpha-2، مثل MA, TN, IT, FR, BE.",
    },
    "Habitual residence country at death": {
        "it": "Paese di residenza abituale al decesso",
        "fr": "Pays de résidence habituelle au décès",
        "ar": "بلد الإقامة المعتادة عند الوفاة",
    },
    "If different from the country of last domicile.": {
        "it": "Se diverso dal paese dell'ultimo domicilio.",
        "fr": "Si différent du pays du dernier domicile.",
        "ar": "إذا كان مختلفًا عن بلد آخر إقامة.",
    },
    "Nationality of the deceased": {
        "it": "Nazionalità del defunto",
        "fr": "Nationalité du défunt",
        "ar": "جنسية المتوفى",
    },
    "ISO 3166-1 alpha-2 code.": {
        "it": "Codice ISO 3166-1 alpha-2.",
        "fr": "Code ISO 3166-1 alpha-2.",
        "ar": "رمز ISO 3166-1 alpha-2.",
    },
    "Did the deceased leave a will?": {
        "it": "Il defunto ha lasciato testamento?",
        "fr": "Le défunt a-t-il laissé un testament ?",
        "ar": "هل ترك المتوفى وصية؟",
    },
    "Surviving spouse?": {
        "it": "Coniuge superstite?",
        "fr": "Conjoint survivant ?",
        "ar": "هل يوجد زوج/زوجة على قيد الحياة؟",
    },
    "Number of surviving children": {
        "it": "Numero di figli superstiti",
        "fr": "Nombre d'enfants survivants",
        "ar": "عدد الأبناء الأحياء",
    },
    "Number of surviving parents (0, 1, or 2)": {
        "it": "Numero di genitori superstiti (0, 1 o 2)",
        "fr": "Nombre de parents survivants (0, 1 ou 2)",
        "ar": "عدد الوالدين الأحياء (0 أو 1 أو 2)",
    },
    "Countries where assets are located": {
        "it": "Paesi in cui si trovano i beni",
        "fr": "Pays où se trouvent les biens",
        "ar": "البلدان التي توجد فيها الأصول",
    },
    "Comma-separated ISO codes, e.g. 'MA, FR, IT'.": {
        "it": "Codici ISO separati da virgola, es. 'MA, FR, IT'.",
        "fr": "Codes ISO séparés par virgule, par ex. 'MA, FR, IT'.",
        "ar": "رموز ISO مفصولة بفواصل، مثل 'MA, FR, IT'.",
    },
    "Additional context": {
        "it": "Contesto aggiuntivo",
        "fr": "Contexte additionnel",
        "ar": "سياق إضافي",
    },
    "Anything you think is relevant. No documents needed.": {
        "it": "Qualsiasi cosa ritieni rilevante. Nessun documento necessario.",
        "fr": "Tout ce que vous jugez pertinent. Aucun document n'est nécessaire.",
        "ar": "أي معلومة تراها ذات صلة. لا حاجة إلى مستندات.",
    },

    # --- Simulation result UI labels ----------------------------------------
    "Simulation result": {"it": "Risultato simulazione", "fr": "Résultat de la simulation", "ar": "نتيجة المحاكاة"},
    "Preliminary result": {"it": "Risultato preliminare", "fr": "Résultat préliminaire", "ar": "نتيجة أولية"},
    "Min": {"it": "Min", "fr": "Min", "ar": "أدنى"},
    "Mid": {"it": "Centrale", "fr": "Médian", "ar": "وسطي"},
    "Max": {"it": "Max", "fr": "Max", "ar": "أقصى"},
    "Warnings": {"it": "Avvertenze", "fr": "Avertissements", "ar": "تحذيرات"},
    "Missing documents": {"it": "Documenti mancanti", "fr": "Documents manquants", "ar": "مستندات ناقصة"},
    "Open official source": {"it": "Apri fonte ufficiale", "fr": "Ouvrir la source officielle", "ar": "افتح المصدر الرسمي"},
    "This simulation is indicative and does not constitute legal advice or guarantee of outcome.": {
        "it": "Questa simulazione è indicativa e non costituisce parere legale né garanzia di risultato.",
        "fr": "Cette simulation est indicative et ne constitue ni un avis juridique ni une garantie de résultat.",
        "ar": "هذه المحاكاة إرشادية ولا تعدّ رأيًا قانونيًا ولا ضمانًا للنتيجة.",
    },
    "Simulation ID": {"it": "ID simulazione", "fr": "ID de simulation", "ar": "معرّف المحاكاة"},
    "Internal status code": {"it": "Codice di stato interno", "fr": "Code de statut interne", "ar": "رمز الحالة الداخلي"},
    "Run simulation": {"it": "Esegui simulazione", "fr": "Lancer la simulation", "ar": "تشغيل المحاكاة"},

    # --- Result fallback / not available -----------------------------------
    "Economic estimate not available without approved sources or legal validation.": {
        "it": "Stima economica non disponibile in assenza di fonti approvate o validazione legale.",
        "fr": "Estimation économique indisponible sans sources approuvées ni validation juridique.",
        "ar": "التقدير الاقتصادي غير متاح بدون مصادر معتمدة أو تحقق قانوني.",
    },
    "This is the platform behaving as designed: rather than producing a number that could mislead you, the simulation explicitly reports that the underlying legal sources have not yet been validated for this jurisdiction and case type.": {
        "it": "È il comportamento progettato della piattaforma: invece di produrre un numero che potrebbe trarre in inganno, la simulazione segnala esplicitamente che le fonti legali sottostanti non sono ancora validate per questa giurisdizione e tipo di caso.",
        "fr": "C'est le comportement attendu de la plateforme : plutôt que de produire un chiffre qui pourrait induire en erreur, la simulation indique explicitement que les sources juridiques sous-jacentes ne sont pas encore validées pour cette juridiction et ce type de cas.",
        "ar": "هذا هو السلوك المقصود للمنصة: بدلًا من إنتاج رقم قد يضلّلك، تُبلغ المحاكاة صراحةً بأن المصادر القانونية الأساسية لم يتمّ التحقق منها بعد لهذه الاختصاص وهذا النوع من القضايا.",
    },

    # --- Country wizard intros (FR/BE/MA/TN scaffold) -----------------------
    "Module under legal validation": {
        "it": "Modulo in validazione legale",
        "fr": "Module en cours de validation juridique",
        "ar": "وحدة قيد التحقق القانوني",
    },
    "All fields below are optional. If you don't know a value, leave it empty. The simulation will not invent numbers: it produces an estimate only when validated legal sources are available, and otherwise returns an honest \"requires legal validation\" status.": {
        "it": "Tutti i campi seguenti sono opzionali. Se non conosci un valore, lascialo vuoto. La simulazione non inventa numeri: produce una stima solo quando sono disponibili fonti legali validate, altrimenti restituisce onestamente lo stato \"richiede validazione legale\".",
        "fr": "Tous les champs ci-dessous sont optionnels. Si vous ne connaissez pas une valeur, laissez-la vide. La simulation n'invente pas de chiffres : elle produit une estimation uniquement lorsque des sources juridiques validées sont disponibles, sinon elle retourne honnêtement le statut « validation juridique requise ».",
        "ar": "جميع الحقول أدناه اختيارية. إذا لم تعرف قيمة، اتركها فارغة. لا تختلق المحاكاة الأرقام: تُنتج تقديرًا فقط عند توفر مصادر قانونية معتمدة، وإلا فإنها تُرجع بصدق الحالة \"يتطلب تحقق قانوني\".",
    },
    "All fields below are optional. The simulation will not invent inheritance shares or amounts: it produces an estimate only when validated legal sources are available, and otherwise returns an honest \"requires legal validation\" status.": {
        "it": "Tutti i campi seguenti sono opzionali. La simulazione non inventa quote o importi successori: produce una stima solo quando sono disponibili fonti legali validate, altrimenti restituisce onestamente lo stato \"richiede validazione legale\".",
        "fr": "Tous les champs ci-dessous sont optionnels. La simulation n'invente pas de parts successorales ni de montants : elle produit une estimation uniquement lorsque des sources juridiques validées sont disponibles, sinon elle retourne honnêtement le statut « validation juridique requise ».",
        "ar": "جميع الحقول أدناه اختيارية. لا تختلق المحاكاة حصصًا أو مبالغ ميراثية: تُنتج تقديرًا فقط عند توفر مصادر قانونية معتمدة، وإلا فإنها تُرجع بصدق الحالة \"يتطلب تحقق قانوني\".",
    },
    "The simulation is indicative and does not constitute legal advice, medical-legal opinion, or guarantee of outcome.": {
        "it": "La simulazione è indicativa e non costituisce parere legale, medico-legale né garanzia di risultato.",
        "fr": "La simulation est indicative et ne constitue ni un avis juridique, ni un avis médico-légal, ni une garantie de résultat.",
        "ar": "المحاكاة إرشادية ولا تشكّل رأيًا قانونيًا أو طبيًا قانونيًا، ولا ضمانًا للنتيجة.",
    },
    "The simulation is indicative and does not constitute legal advice or guarantee of outcome. Inheritance matters in Morocco follow the Moudawana (Code de la famille), Livre III: a precise computation requires Studio review of the actual case context.": {
        "it": "La simulazione è indicativa e non costituisce parere legale né garanzia di risultato. Le successioni in Marocco seguono la Moudawana (Code de la famille), Libro III: un calcolo preciso richiede la revisione dello Studio del contesto effettivo del caso.",
        "fr": "La simulation est indicative et ne constitue ni un avis juridique ni une garantie de résultat. Les successions au Maroc relèvent de la Moudawana (Code de la famille), Livre III : un calcul précis nécessite la revue du Cabinet sur le contexte réel du dossier.",
        "ar": "المحاكاة إرشادية ولا تشكّل رأيًا قانونيًا ولا ضمانًا للنتيجة. تخضع المواريث في المغرب لمدوّنة الأسرة (Moudawana)، الكتاب الثالث: يتطلّب الحساب الدقيق مراجعة المكتب لسياق القضية الفعلي.",
    },
    "The simulation is indicative and does not constitute legal advice or guarantee of outcome. Inheritance matters in Tunisia follow the Code du statut personnel, Livre IX: a precise computation requires Studio review of the actual case context.": {
        "it": "La simulazione è indicativa e non costituisce parere legale né garanzia di risultato. Le successioni in Tunisia seguono il Code du statut personnel, Libro IX: un calcolo preciso richiede la revisione dello Studio del contesto effettivo del caso.",
        "fr": "La simulation est indicative et ne constitue ni un avis juridique ni une garantie de résultat. Les successions en Tunisie relèvent du Code du statut personnel, Livre IX : un calcul précis nécessite la revue du Cabinet sur le contexte réel du dossier.",
        "ar": "المحاكاة إرشادية ولا تشكّل رأيًا قانونيًا ولا ضمانًا للنتيجة. تخضع المواريث في تونس لمجلة الأحوال الشخصية، الكتاب التاسع: يتطلّب الحساب الدقيق مراجعة المكتب لسياق القضية الفعلي.",
    },
    "Italy — road accident bodily injury": {
        "it": "Italia — danno biologico da incidente stradale",
        "fr": "Italie — préjudice corporel après accident de la route",
        "ar": "إيطاليا — أضرار جسدية من حادث طريق",
    },
    "France — road accident bodily injury": {
        "it": "Francia — danno biologico da incidente stradale",
        "fr": "France — préjudice corporel après accident de la route",
        "ar": "فرنسا — أضرار جسدية من حادث طريق",
    },
    "Belgium — road accident bodily injury": {
        "it": "Belgio — danno biologico da incidente stradale",
        "fr": "Belgique — préjudice corporel après accident de la route",
        "ar": "بلجيكا — أضرار جسدية من حادث طريق",
    },
    "Morocco — international inheritance": {
        "it": "Marocco — successione internazionale",
        "fr": "Maroc — succession internationale",
        "ar": "المغرب — ميراث دولي",
    },
    "Tunisia — international inheritance": {
        "it": "Tunisia — successione internazionale",
        "fr": "Tunisie — succession internationale",
        "ar": "تونس — ميراث دولي",
    },
    "This wizard is informative. It does not replace a medical-legal report or a lawyer's opinion. It does not collect documents.": {
        "it": "Questo assistente è informativo. Non sostituisce una perizia medico-legale né il parere di un avvocato. Non raccoglie documenti.",
        "fr": "Cet assistant est informatif. Il ne remplace ni une expertise médico-légale ni l'avis d'un avocat. Il ne collecte aucun document.",
        "ar": "هذا المعالج إعلامي. لا يحلّ محل تقرير طبي قانوني ولا رأي محامٍ. ولا يجمع مستندات.",
    },
    "This module is a scaffold. The Belgian calculator engine is registered but the legal sources (Loi du 21 novembre 1989, Tableau indicatif des cours et tribunaux, barème Schryvers) are still under Studio review. The wizard will return \"requires legal validation\" rather than a numeric estimate.": {
        "it": "Questo modulo è in modalità canovaccio. Il motore di calcolo belga è registrato ma le fonti legali (Loi du 21 novembre 1989, Tableau indicatif des cours et tribunaux, barème Schryvers) sono ancora in revisione dallo Studio. L'assistente restituirà \"richiede validazione legale\" anziché una stima numerica.",
        "fr": "Ce module est un canevas. Le moteur de calcul belge est enregistré mais les sources juridiques (Loi du 21 novembre 1989, Tableau indicatif des cours et tribunaux, barème Schryvers) sont encore en revue au Cabinet. L'assistant retournera « validation juridique requise » plutôt qu'une estimation chiffrée.",
        "ar": "هذه الوحدة في الوضع الهيكلي. تم تسجيل محرك الحساب البلجيكي لكن المصادر القانونية (Loi du 21 novembre 1989, Tableau indicatif des cours et tribunaux, barème Schryvers) لا تزال قيد المراجعة لدى المكتب. سيُرجع المعالج \"بحاجة إلى تحقق قانوني\" بدل تقدير رقمي.",
    },
    "This module is a scaffold. The French calculator engine is registered but the legal sources (Loi Badinter, Référentiel indicatif, barème de capitalisation) are still under Studio review. The wizard will return \"requires legal validation\" rather than a numeric estimate.": {
        "it": "Questo modulo è in modalità canovaccio. Il motore di calcolo francese è registrato ma le fonti legali (Loi Badinter, Référentiel indicatif, barème de capitalisation) sono ancora in revisione dallo Studio. L'assistente restituirà \"richiede validazione legale\" anziché una stima numerica.",
        "fr": "Ce module est un canevas. Le moteur de calcul français est enregistré mais les sources juridiques (Loi Badinter, Référentiel indicatif, barème de capitalisation) sont encore en revue au Cabinet. L'assistant retournera « validation juridique requise » plutôt qu'une estimation chiffrée.",
        "ar": "هذه الوحدة في الوضع الهيكلي. تم تسجيل محرك الحساب الفرنسي لكن المصادر القانونية (Loi Badinter, Référentiel indicatif, barème de capitalisation) لا تزال قيد المراجعة لدى المكتب. سيُرجع المعالج \"بحاجة إلى تحقق قانوني\" بدل تقدير رقمي.",
    },
    "This module is a scaffold. The Moroccan calculator engine is registered but the legal sources (Moudawana Livre III, Code des obligations et des contrats, Code de procédure civile) are still under Studio review. The wizard will return \"requires legal validation\" rather than computed shares.": {
        "it": "Questo modulo è in modalità canovaccio. Il motore di calcolo marocchino è registrato ma le fonti legali (Moudawana Livre III, Code des obligations et des contrats, Code de procédure civile) sono ancora in revisione dallo Studio. L'assistente restituirà \"richiede validazione legale\" anziché quote calcolate.",
        "fr": "Ce module est un canevas. Le moteur de calcul marocain est enregistré mais les sources juridiques (Moudawana Livre III, Code des obligations et des contrats, Code de procédure civile) sont encore en revue au Cabinet. L'assistant retournera « validation juridique requise » plutôt que des parts calculées.",
        "ar": "هذه الوحدة في الوضع الهيكلي. تم تسجيل محرك الحساب المغربي لكن المصادر القانونية (Moudawana Livre III, Code des obligations et des contrats, Code de procédure civile) لا تزال قيد المراجعة لدى المكتب. سيُرجع المعالج \"بحاجة إلى تحقق قانوني\" بدل حصص محسوبة.",
    },
    "This module is a scaffold. The Tunisian calculator engine is registered but the legal sources (Code du statut personnel Livre IX, Code des obligations et des contrats, Code de droit international privé) are still under Studio review. The wizard will return \"requires legal validation\" rather than computed shares.": {
        "it": "Questo modulo è in modalità canovaccio. Il motore di calcolo tunisino è registrato ma le fonti legali (Code du statut personnel Livre IX, Code des obligations et des contrats, Code de droit international privé) sono ancora in revisione dallo Studio. L'assistente restituirà \"richiede validazione legale\" anziché quote calcolate.",
        "fr": "Ce module est un canevas. Le moteur de calcul tunisien est enregistré mais les sources juridiques (Code du statut personnel Livre IX, Code des obligations et des contrats, Code de droit international privé) sont encore en revue au Cabinet. L'assistant retournera « validation juridique requise » plutôt que des parts calculées.",
        "ar": "هذه الوحدة في الوضع الهيكلي. تم تسجيل محرك الحساب التونسي لكن المصادر القانونية (Code du statut personnel Livre IX, Code des obligations et des contrats, Code de droit international privé) لا تزال قيد المراجعة لدى المكتب. سيُرجع المعالج \"بحاجة إلى تحقق قانوني\" بدل حصص محسوبة.",
    },

    # --- Modular taxonomy + Roadmap labels ----------------------------------
    "Modular taxonomy": {
        "it": "Tassonomia modulare",
        "fr": "Taxonomie modulaire",
        "ar": "تصنيف معياري",
    },
    "We implement modules in depth, one at a time. Each case type is activated only after the relevant legal sources are catalogued and validated for the chosen jurisdiction.": {
        "it": "Implementiamo i moduli in profondità, uno alla volta. Ogni tipo di caso viene attivato solo dopo che le fonti legali rilevanti sono catalogate e validate per la giurisdizione scelta.",
        "fr": "Nous implémentons les modules en profondeur, un à la fois. Chaque type de dossier est activé uniquement après que les sources juridiques pertinentes ont été cataloguées et validées pour la juridiction choisie.",
        "ar": "ننفّذ الوحدات بعمق، واحدة في كل مرة. يتم تفعيل كل نوع قضية فقط بعد فهرسة المصادر القانونية ذات الصلة والتحقق منها لاختصاص قضائي مختار.",
    },
    "A calculator is registered for this case type. Estimates appear only when approved legal sources are available for the chosen jurisdiction.": {
        "it": "Un calcolatore è registrato per questo tipo di caso. Le stime compaiono solo quando sono disponibili fonti legali approvate per la giurisdizione scelta.",
        "fr": "Un calculateur est enregistré pour ce type d'affaire. Les estimations n'apparaissent que lorsque des sources juridiques approuvées sont disponibles pour la juridiction choisie.",
        "ar": "تم تسجيل حاسبة لهذا النوع من القضايا. تظهر التقديرات فقط عندما تكون المصادر القانونية المعتمدة متاحة للاختصاص القضائي المختار.",
    },
    "A calculator scaffold is registered for this case type. Legal sources are still under Studio review, so the wizard returns \"requires legal validation\" and never invents amounts or shares.": {
        "it": "Un canovaccio di calcolatore è registrato per questo tipo di caso. Le fonti legali sono ancora in revisione presso lo Studio, quindi l'assistente restituisce \"richiede validazione legale\" e non inventa mai importi né quote.",
        "fr": "Un canevas de calculateur est enregistré pour ce type d'affaire. Les sources juridiques sont encore en revue au Cabinet, l'assistant retourne donc « validation juridique requise » et n'invente jamais de montants ni de parts.",
        "ar": "تم تسجيل قالب حاسبة لهذا النوع من القضايا. لا تزال المصادر القانونية قيد المراجعة لدى المكتب، لذا يُرجع المعالج \"بحاجة إلى تحقق قانوني\" ولا يختلق مبالغ أو حصصًا أبدًا.",
    },
    "This module is on the roadmap. The Studio will activate it once the underlying legal sources are validated.": {
        "it": "Questo modulo è in roadmap. Lo Studio lo attiverà una volta validate le fonti legali sottostanti.",
        "fr": "Ce module est inscrit à la feuille de route. Le Cabinet l'activera une fois les sources juridiques sous-jacentes validées.",
        "ar": "هذه الوحدة على خارطة الطريق. سيقوم المكتب بتفعيلها بمجرّد التحقق من المصادر القانونية الأساسية.",
    },
    "Additional modules under preparation include catastrophic damage, loss of chance, defamation, school/professional damage and ruined holiday claims, where legally tractable.": {
        "it": "Ulteriori moduli in preparazione includono danno catastrofale, perdita di chance, diffamazione, danno scolastico/professionale e vacanza rovinata, ove giuridicamente trattabili.",
        "fr": "D'autres modules en préparation couvrent le préjudice catastrophique, la perte de chance, la diffamation, le préjudice scolaire/professionnel et la vacance gâchée, lorsque c'est juridiquement traitable.",
        "ar": "تشمل الوحدات الأخرى قيد الإعداد الضرر الكارثي، وضياع الفرصة، والقذف، والضرر المدرسي/المهني، ومطالبات تعطّل العطلة، عندما يكون ذلك قابلًا للمعالجة قانونيًا.",
    },

    # --- Privacy / disclaimer / rate-limit pages ----------------------------
    "Personal data": {"it": "Dati personali", "fr": "Données personnelles", "ar": "البيانات الشخصية"},
    "Too many requests": {"it": "Troppe richieste", "fr": "Trop de demandes", "ar": "طلبات أكثر من اللازم"},
    "Rate limit": {"it": "Limite di frequenza", "fr": "Limitation de débit", "ar": "حدّ المعدّل"},
    "For security reasons we received too many submissions from your network in a short time. Please try again later.": {
        "it": "Per motivi di sicurezza abbiamo ricevuto troppi invii dalla tua rete in poco tempo. Riprova più tardi.",
        "fr": "Pour des raisons de sécurité, nous avons reçu trop d'envois depuis votre réseau en peu de temps. Veuillez réessayer plus tard.",
        "ar": "لأسباب أمنية، تلقينا عددًا كبيرًا من الإرسالات من شبكتك في وقت قصير. يرجى المحاولة لاحقًا.",
    },
    "If you need urgent assistance, please contact the Studio directly via the institutional website.": {
        "it": "Se hai bisogno di assistenza urgente, contatta direttamente lo Studio tramite il sito istituzionale.",
        "fr": "Si vous avez besoin d'une assistance urgente, contactez directement le Cabinet via le site institutionnel.",
        "ar": "إذا كنت بحاجة إلى مساعدة عاجلة، يرجى التواصل مع المكتب مباشرة عبر الموقع المؤسسي.",
    },
    "We process personal data in accordance with the EU General Data Protection Regulation (GDPR) and the privacy laws applicable in each jurisdiction we cover.": {
        "it": "Trattiamo i dati personali in conformità al Regolamento UE sulla protezione dei dati (GDPR) e alle leggi sulla privacy applicabili in ciascuna giurisdizione che copriamo.",
        "fr": "Nous traitons les données personnelles conformément au Règlement Général sur la Protection des Données (RGPD) et aux lois sur la vie privée applicables dans chaque juridiction couverte.",
        "ar": "نعالج البيانات الشخصية وفقًا للائحة الأوروبية العامة لحماية البيانات (GDPR) وقوانين الخصوصية المطبقة في كل اختصاص قضائي نغطّيه.",
    },
    "When you use the simulator we may collect: the inputs you provide for the simulation, the language and country you choose, technical metadata such as IP address and user agent, and the consents you grant.": {
        "it": "Quando usi il simulatore possiamo raccogliere: i dati che fornisci per la simulazione, la lingua e il paese che scegli, metadati tecnici come indirizzo IP e user agent, e i consensi che concedi.",
        "fr": "Lorsque vous utilisez le simulateur, nous pouvons collecter : les données que vous fournissez pour la simulation, la langue et le pays choisis, des métadonnées techniques comme l'adresse IP et l'agent utilisateur, et les consentements que vous accordez.",
        "ar": "عند استخدام المحاكي، قد نجمع: المدخلات التي تقدّمها للمحاكاة، واللغة والبلد الذي تختاره، والبيانات التقنية مثل عنوان IP ووكيل المستخدم، والموافقات التي تمنحها.",
    },
    "We do not sell personal data. We do not share it with third parties beyond what is strictly necessary to provide our legal services and meet legal obligations.": {
        "it": "Non vendiamo dati personali. Non li condividiamo con terzi oltre quanto strettamente necessario per fornire i nostri servizi legali e adempiere agli obblighi di legge.",
        "fr": "Nous ne vendons pas les données personnelles. Nous ne les partageons avec des tiers que dans la stricte mesure nécessaire pour fournir nos services juridiques et respecter nos obligations légales.",
        "ar": "نحن لا نبيع البيانات الشخصية. ولا نشاركها مع أطراف ثالثة إلا في الحدّ الضروري لتقديم خدماتنا القانونية والوفاء بالالتزامات القانونية.",
    },
    "You can request access, rectification, deletion or anonymization of your data at any time by contacting the Studio.": {
        "it": "Puoi richiedere accesso, rettifica, cancellazione o anonimizzazione dei tuoi dati in qualsiasi momento contattando lo Studio.",
        "fr": "Vous pouvez demander l'accès, la rectification, la suppression ou l'anonymisation de vos données à tout moment en contactant le Cabinet.",
        "ar": "يمكنك طلب الوصول إلى بياناتك أو تصحيحها أو حذفها أو جعلها مجهولة الهوية في أي وقت بالتواصل مع المكتب.",
    },
    "A complete privacy policy will be published before the simulator goes live to the public. This page is a working summary.": {
        "it": "Una privacy policy completa verrà pubblicata prima che il simulatore vada live al pubblico. Questa pagina è una sintesi di lavoro.",
        "fr": "Une politique de confidentialité complète sera publiée avant la mise en production publique du simulateur. Cette page est un résumé de travail.",
        "ar": "ستُنشر سياسة خصوصية كاملة قبل إطلاق المحاكي للجمهور. هذه الصفحة ملخّص أوّلي.",
    },
    "This platform offers indicative simulations of compensation and inheritance scenarios across multiple jurisdictions. Each simulation is based on legal sources catalogued and validated by our team.": {
        "it": "Questa piattaforma offre simulazioni indicative di scenari di risarcimento e successione in più giurisdizioni. Ogni simulazione si basa su fonti legali catalogate e validate dal nostro team.",
        "fr": "Cette plateforme propose des simulations indicatives de scénarios d'indemnisation et de succession dans plusieurs juridictions. Chaque simulation s'appuie sur des sources juridiques cataloguées et validées par notre équipe.",
        "ar": "تقدّم هذه المنصة محاكاة إرشادية لسيناريوهات التعويض والميراث عبر عدة اختصاصات قضائية. تستند كل محاكاة إلى مصادر قانونية مفهرسة ومعتمدة من قبل فريقنا.",
    },
    "A simulation is not legal advice, is not a medico-legal opinion and is not a guarantee of outcome. The actual evaluation of a case depends on documents, expert reports, liability assessment, applicable law, competent jurisdiction, case law and insurance practice.": {
        "it": "Una simulazione non è un parere legale, non è un parere medico-legale e non è una garanzia di risultato. La valutazione effettiva di un caso dipende da documenti, perizie, valutazione della responsabilità, legge applicabile, giurisdizione competente, orientamenti giudiziari e prassi assicurativa.",
        "fr": "Une simulation n'est pas un avis juridique, ni un avis médico-légal, ni une garantie de résultat. L'évaluation réelle d'un dossier dépend des documents, des expertises, de l'évaluation de la responsabilité, du droit applicable, de la juridiction compétente, de la jurisprudence et des pratiques assurantielles.",
        "ar": "المحاكاة ليست رأيًا قانونيًا ولا رأيًا طبيًا قانونيًا ولا ضمانًا للنتيجة. يعتمد التقييم الفعلي للقضية على المستندات والخبرات وتقدير المسؤولية والقانون الواجب التطبيق والاختصاص القضائي والاجتهاد القضائي والممارسات التأمينية.",
    },
    "If you require a binding evaluation, please request a legal review through our office.": {
        "it": "Se hai bisogno di una valutazione vincolante, richiedi una revisione legale attraverso il nostro Studio.",
        "fr": "Si vous avez besoin d'une évaluation contraignante, veuillez demander une revue juridique auprès de notre Cabinet.",
        "ar": "إذا كنت بحاجة إلى تقييم ملزم، يرجى طلب مراجعة قانونية عبر مكتبنا.",
    },
    "This text is a working version. The final wording will be reviewed and signed off by the Studio's legal team.": {
        "it": "Questo testo è una versione di lavoro. La formulazione finale sarà rivista e approvata dal team legale dello Studio.",
        "fr": "Ce texte est une version de travail. La formulation finale sera revue et validée par l'équipe juridique du Cabinet.",
        "ar": "هذا النصّ نسخة عمل. ستتمّ مراجعة الصياغة النهائية واعتمادها من قبل الفريق القانوني للمكتب.",
    },
}
# fmt: on


def _escape_po_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _po_to_msgid_text(line: str, continuation_lines: list[str]) -> str:
    """Concatena msgid (può essere multilinea) decodificando escape."""
    raw = line.strip()
    if raw.startswith("msgid "):
        raw = raw[6:]
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    parts = [raw]
    for cont in continuation_lines:
        c = cont.rstrip("\n").strip()
        if c.startswith('"') and c.endswith('"'):
            c = c[1:-1]
        parts.append(c)
    s = "".join(parts)
    return s.replace('\\"', '"').replace("\\\\", "\\").replace("\\n", "\n").replace("\\t", "\t")


def update_po(po_path: Path, lang: str) -> tuple[int, int]:
    """Restituisce (matched, replaced) per la lingua data."""
    raw = po_path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    matched = 0
    replaced = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("msgid "):
            # Collect continuation
            cont_idx = i + 1
            cont_lines: list[str] = []
            while cont_idx < len(lines) and lines[cont_idx].lstrip().startswith('"'):
                cont_lines.append(lines[cont_idx])
                cont_idx += 1
            msgid_text = _po_to_msgid_text(line, cont_lines)
            # Find msgstr
            if cont_idx < len(lines) and lines[cont_idx].startswith("msgstr "):
                msgstr_idx = cont_idx
                msgstr_cont_idx = msgstr_idx + 1
                msgstr_cont_count = 0
                while msgstr_cont_idx + msgstr_cont_count < len(lines) and lines[
                    msgstr_cont_idx + msgstr_cont_count
                ].lstrip().startswith('"'):
                    msgstr_cont_count += 1
                # Look up translation
                if msgid_text in TRANSLATIONS:
                    matched += 1
                    target = TRANSLATIONS[msgid_text].get(lang, "")
                    if target:
                        replaced += 1
                        out.extend(lines[i:msgstr_idx])
                        out.append(f'msgstr "{_escape_po_string(target)}"\n')
                        i = msgstr_idx + 1 + msgstr_cont_count
                        continue
                # No translation: copy as-is up to end of msgstr block
                out.extend(lines[i : msgstr_idx + 1 + msgstr_cont_count])
                i = msgstr_idx + 1 + msgstr_cont_count
                continue
        out.append(line)
        i += 1
    po_path.write_text("".join(out), encoding="utf-8")
    return matched, replaced


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    total_replaced = 0
    for lang in ("it", "fr", "ar"):
        po = repo / "locale" / lang / "LC_MESSAGES" / "django.po"
        if not po.exists():
            print(f"[i18n-pass3] missing: {po}", file=sys.stderr)
            return 1
        m, r = update_po(po, lang)
        total_replaced += r
        print(f"[i18n-pass3] {lang}: matched {m} entries, replaced {r} msgstr")
    print(f"[i18n-pass3] TOTAL replaced across 3 langs: {total_replaced}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
