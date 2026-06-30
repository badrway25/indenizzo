"""Idempotently append P39 msgids (premium sources, human results, internal
imagery) to django.po for it/fr/en/ar. NEVER runs makemessages."""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# msgid -> {lang: msgstr}. en mirrors the msgid.
TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- Sources intro (was an English leak: no it/fr/ar msgstr existed) ---
    "Each path on the platform is grounded in an official source. Browse the library by country, category or type, see what each source unlocks, and open the official document.": {
        "it": "Ogni percorso della piattaforma si fonda su una fonte ufficiale. Sfoglia la biblioteca per paese, categoria o tipo, vedi cosa permette ogni fonte e apri il documento ufficiale.",
        "fr": "Chaque parcours de la plateforme repose sur une source officielle. Parcourez la bibliothèque par pays, catégorie ou type, voyez ce que permet chaque source et ouvrez le document officiel.",
        "en": "Each path on the platform is grounded in an official source. Browse the library by country, category or type, see what each source unlocks, and open the official document.",
        "ar": "يستند كل مسار في المنصة إلى مصدر رسمي. تصفّح المكتبة حسب البلد أو الفئة أو النوع، واطّلع على ما يتيحه كل مصدر، وافتح الوثيقة الرسمية.",
    },
    # --- Sources library ("how to read a source") ---
    "Official documents, explained simply": {
        "it": "Documenti ufficiali, spiegati in modo semplice",
        "fr": "Documents officiels, expliqués simplement",
        "en": "Official documents, explained simply",
        "ar": "وثائق رسمية، مشروحة ببساطة",
    },
    "How to read a source": {
        "it": "Come leggere una fonte",
        "fr": "Comment lire une source",
        "en": "How to read a source",
        "ar": "كيف تقرأ مصدرًا",
    },
    "Every source answers the same five questions. Read them in order and you will know exactly what each document lets you do.": {
        "it": "Ogni fonte risponde alle stesse cinque domande. Leggile in ordine e saprai con esattezza cosa ti permette ogni documento.",
        "fr": "Chaque source répond aux mêmes cinq questions. Lisez-les dans l'ordre et vous saurez exactement ce que chaque document permet.",
        "en": "Every source answers the same five questions. Read them in order and you will know exactly what each document lets you do.",
        "ar": "كل مصدر يجيب عن الأسئلة الخمسة نفسها. اقرأها بالترتيب لتعرف بالضبط ما يتيحه كل مستند.",
    },
    "Which country's law the document belongs to.": {
        "it": "A quale legge nazionale appartiene il documento.",
        "fr": "À quelle loi nationale appartient le document.",
        "en": "Which country's law the document belongs to.",
        "ar": "إلى قانون أي بلد ينتمي المستند.",
    },
    "The kind of case it applies to.": {
        "it": "Il tipo di caso a cui si applica.",
        "fr": "Le type de dossier auquel il s'applique.",
        "en": "The kind of case it applies to.",
        "ar": "نوع القضية التي ينطبق عليها.",
    },
    "What it lets you do": {
        "it": "Cosa ti permette",
        "fr": "Ce qu'elle permet",
        "en": "What it lets you do",
        "ar": "ما الذي تتيحه",
    },
    "Whether it can feed an estimate or guide a document check.": {
        "it": "Se può alimentare una stima o guidare una verifica dei documenti.",
        "fr": "Si elle peut alimenter une estimation ou guider une vérification des documents.",
        "en": "Whether it can feed an estimate or guide a document check.",
        "ar": "ما إذا كانت تغذّي تقديرًا أو توجّه التحقّق من المستندات.",
    },
    "When a table is needed": {
        "it": "Quando serve una tabella",
        "fr": "Quand une table est nécessaire",
        "en": "When a table is needed",
        "ar": "متى تكون هناك حاجة إلى جدول",
    },
    "A figure appears only when the official table or formula is validated.": {
        "it": "Un importo compare solo quando la tabella o la formula ufficiale è validata.",
        "fr": "Un montant n'apparaît que lorsque la table ou la formule officielle est validée.",
        "en": "A figure appears only when the official table or formula is validated.",
        "ar": "لا يظهر أي مبلغ إلا عندما يُعتمد الجدول أو الصيغة الرسمية.",
    },
    "When a document check is enough": {
        "it": "Quando basta la verifica dei documenti",
        "fr": "Quand une vérification des documents suffit",
        "en": "When a document check is enough",
        "ar": "متى يكفي التحقّق من المستندات",
    },
    "Without a validated table, the source still guides which documents to prepare.": {
        "it": "Senza una tabella validata, la fonte indica comunque quali documenti preparare.",
        "fr": "Sans table validée, la source indique tout de même quels documents préparer.",
        "en": "Without a validated table, the source still guides which documents to prepare.",
        "ar": "حتى بدون جدول معتمد، يرشدك المصدر إلى المستندات التي يجب تجهيزها.",
    },
    # --- Source detail sheet ---
    "What this source is for": {
        "it": "A cosa serve questa fonte",
        "fr": "À quoi sert cette source",
        "en": "What this source is for",
        "ar": "ما الغرض من هذا المصدر",
    },
    "When it can support an estimate": {
        "it": "Quando può aiutare una stima",
        "fr": "Quand elle peut soutenir une estimation",
        "en": "When it can support an estimate",
        "ar": "متى يمكن أن تدعم تقديرًا",
    },
    "This source backs an indicative estimate: when your data matches the validated table, the platform can calculate a range.": {
        "it": "Questa fonte sostiene una stima indicativa: quando i tuoi dati corrispondono alla tabella validata, la piattaforma può calcolare un intervallo.",
        "fr": "Cette source soutient une estimation indicative : lorsque vos données correspondent à la table validée, la plateforme peut calculer une fourchette.",
        "en": "This source backs an indicative estimate: when your data matches the validated table, the platform can calculate a range.",
        "ar": "يدعم هذا المصدر تقديرًا إرشاديًا: عندما تتطابق بياناتك مع الجدول المعتمد، يمكن للمنصة حساب نطاق.",
    },
    "This source does not produce a figure on its own. A number appears only where a national table or formula is validated.": {
        "it": "Questa fonte da sola non produce un importo. Un numero compare solo dove una tabella o formula nazionale è validata.",
        "fr": "Cette source ne produit pas de montant à elle seule. Un chiffre n'apparaît que là où une table ou une formule nationale est validée.",
        "en": "This source does not produce a figure on its own. A number appears only where a national table or formula is validated.",
        "ar": "لا ينتج هذا المصدر مبلغًا بمفرده. لا يظهر رقم إلا حيث يُعتمد جدول أو صيغة وطنية.",
    },
    "Use it to see which documents to prepare and which official references apply to your case, even before any amount.": {
        "it": "Usala per vedere quali documenti preparare e quali riferimenti ufficiali valgono per il tuo caso, ancora prima di qualsiasi importo.",
        "fr": "Utilisez-la pour voir quels documents préparer et quelles références officielles s'appliquent à votre dossier, avant même tout montant.",
        "en": "Use it to see which documents to prepare and which official references apply to your case, even before any amount.",
        "ar": "استخدمها لمعرفة المستندات التي يجب تجهيزها والمراجع الرسمية التي تنطبق على قضيتك، حتى قبل أي مبلغ.",
    },
    "Useful links": {
        "it": "Collegamenti utili",
        "fr": "Liens utiles",
        "en": "Useful links",
        "ar": "روابط مفيدة",
    },
    # --- Services internal sections ---
    "See an indicative range where an official table exists": {
        "it": "Vedi un intervallo indicativo dove esiste una tabella ufficiale",
        "fr": "Voyez une fourchette indicative là où une table officielle existe",
        "en": "See an indicative range where an official table exists",
        "ar": "اطّلع على نطاق إرشادي حيث يوجد جدول رسمي",
    },
    "Answer a few questions about your case. Where the law and the validated table allow it, you get an indicative range — never an invented number.": {
        "it": "Rispondi a poche domande sul tuo caso. Dove la legge e la tabella validata lo permettono, ottieni un intervallo indicativo — mai un numero inventato.",
        "fr": "Répondez à quelques questions sur votre dossier. Là où la loi et la table validée le permettent, vous obtenez une fourchette indicative — jamais un chiffre inventé.",
        "en": "Answer a few questions about your case. Where the law and the validated table allow it, you get an indicative range — never an invented number.",
        "ar": "أجب عن بضعة أسئلة حول قضيتك. حيث يسمح القانون والجدول المعتمد، تحصل على نطاق إرشادي — لا رقم مُختلق أبدًا.",
    },
    "Start the estimate": {
        "it": "Avvia la stima",
        "fr": "Lancer l'estimation",
        "en": "Start the estimate",
        "ar": "ابدأ التقدير",
    },
    "Upload your file and see which path fits": {
        "it": "Carica il tuo fascicolo e scopri quale percorso è adatto",
        "fr": "Téléversez votre dossier et voyez quel parcours convient",
        "en": "Upload your file and see which path fits",
        "ar": "حمّل ملفك واطّلع على المسار المناسب",
    },
    "Add your documents: each is recognised and linked to the official sources, then combined into one dossier with a clear next step.": {
        "it": "Aggiungi i tuoi documenti: ognuno viene riconosciuto e collegato alle fonti ufficiali, poi riunito in un unico fascicolo con un passo successivo chiaro.",
        "fr": "Ajoutez vos documents : chacun est reconnu et relié aux sources officielles, puis réuni en un seul dossier avec une étape suivante claire.",
        "en": "Add your documents: each is recognised and linked to the official sources, then combined into one dossier with a clear next step.",
        "ar": "أضِف مستنداتك: يُتعرّف على كل منها ويُربط بالمصادر الرسمية، ثم تُجمع في ملف واحد بخطوة تالية واضحة.",
    },
    "Upload documents": {
        "it": "Carica i documenti",
        "fr": "Téléverser des documents",
        "en": "Upload documents",
        "ar": "حمّل المستندات",
    },
    "Cross-border cases": {
        "it": "Casi esteri",
        "fr": "Dossiers transfrontaliers",
        "en": "Cross-border cases",
        "ar": "القضايا العابرة للحدود",
    },
    "Understand which country's law may apply": {
        "it": "Capisci quale legge nazionale può valere",
        "fr": "Comprenez quelle loi nationale peut s'appliquer",
        "en": "Understand which country's law may apply",
        "ar": "افهم قانون أي بلد قد ينطبق",
    },
    "For accidents or successions across borders, start from the country and see the official references and the documents to prepare.": {
        "it": "Per incidenti o successioni transfrontaliere, parti dal paese e vedi i riferimenti ufficiali e i documenti da preparare.",
        "fr": "Pour les accidents ou successions transfrontaliers, partez du pays et voyez les références officielles et les documents à préparer.",
        "en": "For accidents or successions across borders, start from the country and see the official references and the documents to prepare.",
        "ar": "في الحوادث أو المواريث العابرة للحدود، ابدأ من البلد واطّلع على المراجع الرسمية والمستندات الواجب تجهيزها.",
    },
    # --- Guided router path preview ---
    "Case": {"it": "Caso", "fr": "Dossier", "en": "Case", "ar": "القضية"},
    # --- Human result report summary ---
    "Your result in plain words": {
        "it": "Il tuo risultato in parole semplici",
        "fr": "Votre résultat en mots simples",
        "en": "Your result in plain words",
        "ar": "نتيجتك بكلمات بسيطة",
    },
    "Your result, in plain words": {
        "it": "Il tuo risultato, in parole semplici",
        "fr": "Votre résultat, en mots simples",
        "en": "Your result, in plain words",
        "ar": "نتيجتك، بكلمات بسيطة",
    },
    "You indicated": {
        "it": "Hai indicato",
        "fr": "Vous avez indiqué",
        "en": "You indicated",
        "ar": "لقد أوضحت",
    },
    "We can do now": {
        "it": "Possiamo fare ora",
        "fr": "Ce que nous pouvons faire maintenant",
        "en": "We can do now",
        "ar": "ما يمكننا فعله الآن",
    },
    "We can calculate an indicative range from the validated official sources.": {
        "it": "Possiamo calcolare un intervallo indicativo dalle fonti ufficiali validate.",
        "fr": "Nous pouvons calculer une fourchette indicative à partir des sources officielles validées.",
        "en": "We can calculate an indicative range from the validated official sources.",
        "ar": "يمكننا حساب نطاق إرشادي من المصادر الرسمية المعتمدة.",
    },
    "We can check your documents and point you to the right path.": {
        "it": "Possiamo controllare i tuoi documenti e indicarti il percorso giusto.",
        "fr": "Nous pouvons vérifier vos documents et vous orienter vers le bon parcours.",
        "en": "We can check your documents and point you to the right path.",
        "ar": "يمكننا فحص مستنداتك وإرشادك إلى المسار الصحيح.",
    },
    "We can prepare your dossier and list the official references that apply.": {
        "it": "Possiamo preparare il tuo fascicolo ed elencare i riferimenti ufficiali che valgono.",
        "fr": "Nous pouvons préparer votre dossier et lister les références officielles applicables.",
        "en": "We can prepare your dossier and list the official references that apply.",
        "ar": "يمكننا تجهيز ملفك وسرد المراجع الرسمية المنطبقة.",
    },
    "Still missing": {
        "it": "Manca ancora",
        "fr": "Il manque encore",
        "en": "Still missing",
        "ar": "ما زال ناقصًا",
    },
    "Your next step": {
        "it": "Prossimo passo",
        "fr": "Prochaine étape",
        "en": "Your next step",
        "ar": "خطوتك التالية",
    },
    "The information you entered about your case.": {
        "it": "Le informazioni che hai inserito sul tuo caso.",
        "fr": "Les informations que vous avez saisies sur votre dossier.",
        "en": "The information you entered about your case.",
        "ar": "المعلومات التي أدخلتها عن قضيتك.",
    },
    "A short legal review by the Studio to confirm the details of your case.": {
        "it": "Una breve revisione legale dello Studio per confermare i dettagli del tuo caso.",
        "fr": "Un bref examen juridique du Cabinet pour confirmer les détails de votre dossier.",
        "en": "A short legal review by the Studio to confirm the details of your case.",
        "ar": "مراجعة قانونية قصيرة من المكتب لتأكيد تفاصيل قضيتك.",
    },
    "Send your summary to the Studio and gather the documents listed below.": {
        "it": "Invia il tuo riepilogo allo Studio e raccogli i documenti elencati qui sotto.",
        "fr": "Envoyez votre récapitulatif au Cabinet et rassemblez les documents listés ci-dessous.",
        "en": "Send your summary to the Studio and gather the documents listed below.",
        "ar": "أرسل ملخّصك إلى المكتب واجمع المستندات المذكورة أدناه.",
    },
    "A short legal review by the Studio to confirm documents, expert reports and the responsibility split.": {
        "it": "Una breve revisione legale dello Studio per confermare documenti, perizie e la ripartizione delle responsabilità.",
        "fr": "Un bref examen juridique du Cabinet pour confirmer les documents, les expertises et le partage des responsabilités.",
        "en": "A short legal review by the Studio to confirm documents, expert reports and the responsibility split.",
        "ar": "مراجعة قانونية قصيرة من المكتب لتأكيد المستندات والتقارير الخبيرة وتوزيع المسؤولية.",
    },
    "Download the PDF, then request a legal review from the Studio.": {
        "it": "Scarica il PDF, poi richiedi una revisione legale allo Studio.",
        "fr": "Téléchargez le PDF, puis demandez un examen juridique au Cabinet.",
        "en": "Download the PDF, then request a legal review from the Studio.",
        "ar": "نزّل ملف PDF ثم اطلب مراجعة قانونية من المكتب.",
    },
    "Open the recommended path, or send the whole dossier to the Studio.": {
        "it": "Apri il percorso consigliato, oppure invia l'intero fascicolo allo Studio.",
        "fr": "Ouvrez le parcours recommandé, ou envoyez l'intégralité du dossier au Cabinet.",
        "en": "Open the recommended path, or send the whole dossier to the Studio.",
        "ar": "افتح المسار الموصى به، أو أرسل الملف بأكمله إلى المكتب.",
    },
}


def has_msgid(po_text: str, msgid: str) -> bool:
    return f'\nmsgid "{msgid}"\n' in po_text


def append_block(po_path: Path, lang: str) -> int:
    text = po_path.read_text(encoding="utf-8")
    added = 0
    chunks: list[str] = []
    for msgid, langs in TRANSLATIONS.items():
        if has_msgid(text, msgid):
            continue
        chunks.append(f'\nmsgid "{msgid}"\nmsgstr "{langs[lang]}"\n')
        added += 1
    if added:
        po_path.write_text(text + "".join(chunks), encoding="utf-8")
    return added


def main() -> int:
    base = Path(__file__).resolve().parents[1] / "locale"
    total = 0
    for lang in ("it", "fr", "en", "ar"):
        po_path = base / lang / "LC_MESSAGES" / "django.po"
        added = append_block(po_path, lang)
        total += added
        print(f"[{lang}] added {added} new P39 msgids -> {po_path}")
    print(f"total appended: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
