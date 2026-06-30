"""Idempotently append P40 msgids (documentation hub, feature/preview sections,
explainer cards) to django.po for it/fr/en/ar. NEVER runs makemessages."""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- Documentation hub ---
    "How to use the platform": {
        "it": "Come usare la piattaforma", "fr": "Comment utiliser la plateforme",
        "en": "How to use the platform", "ar": "كيفية استخدام المنصة"},
    "Plain-language guides to the Badrane platform: how the simulation works, how to prepare your documents, how to read the result and the official sources, which countries are covered and when the platform can produce an estimate.": {
        "it": "Guide in linguaggio semplice alla piattaforma Badrane: come funziona la simulazione, come preparare i documenti, come leggere il risultato e le fonti ufficiali, quali paesi sono coperti e quando la piattaforma può produrre una stima.",
        "fr": "Guides en langage clair de la plateforme Badrane : comment fonctionne la simulation, comment préparer vos documents, comment lire le résultat et les sources officielles, quels pays sont couverts et quand la plateforme peut produire une estimation.",
        "en": "Plain-language guides to the Badrane platform: how the simulation works, how to prepare your documents, how to read the result and the official sources, which countries are covered and when the platform can produce an estimate.",
        "ar": "أدلة بلغة بسيطة لمنصة بدران: كيف تعمل المحاكاة، كيف تجهّز مستنداتك، كيف تقرأ النتيجة والمصادر الرسمية، أي البلدان مشمولة، ومتى يمكن للمنصة إنتاج تقدير."},
    "Short, plain-language guides — written for people, not for engineers. Find what you need, in order, from a first simulation to reading your result.": {
        "it": "Guide brevi e semplici — scritte per le persone, non per i tecnici. Trova ciò che ti serve, in ordine, dalla prima simulazione alla lettura del risultato.",
        "fr": "Des guides courts et clairs — écrits pour les gens, pas pour les ingénieurs. Trouvez ce qu'il vous faut, dans l'ordre, de la première simulation à la lecture du résultat.",
        "en": "Short, plain-language guides — written for people, not for engineers. Find what you need, in order, from a first simulation to reading your result.",
        "ar": "أدلة قصيرة وواضحة — مكتوبة للناس، لا للمهندسين. اعثر على ما تحتاجه بالترتيب، من أول محاكاة إلى قراءة نتيجتك."},
    "On this page": {"it": "In questa pagina", "fr": "Sur cette page", "en": "On this page", "ar": "في هذه الصفحة"},
    "Documentation topics": {"it": "Argomenti della documentazione", "fr": "Sujets de la documentation", "en": "Documentation topics", "ar": "مواضيع التوثيق"},
    "How the simulation works": {"it": "Come funziona la simulazione", "fr": "Comment fonctionne la simulation", "en": "How the simulation works", "ar": "كيف تعمل المحاكاة"},
    "How to prepare your documents": {"it": "Come preparare i documenti", "fr": "Comment préparer vos documents", "en": "How to prepare your documents", "ar": "كيف تجهّز مستنداتك"},
    "How to read your result": {"it": "Come leggere il risultato", "fr": "Comment lire votre résultat", "en": "How to read your result", "ar": "كيف تقرأ نتيجتك"},
    "How to read the official sources": {"it": "Come leggere le fonti ufficiali", "fr": "Comment lire les sources officielles", "en": "How to read the official sources", "ar": "كيف تقرأ المصادر الرسمية"},
    "Which countries are covered": {"it": "Quali paesi sono coperti", "fr": "Quels pays sont couverts", "en": "Which countries are covered", "ar": "أي البلدان مشمولة"},
    "When the platform can estimate": {"it": "Quando la piattaforma può stimare", "fr": "Quand la plateforme peut estimer", "en": "When the platform can estimate", "ar": "متى يمكن للمنصة أن تقدّر"},
    "When it prepares only a summary": {"it": "Quando prepara solo un riepilogo", "fr": "Quand elle prépare seulement un récapitulatif", "en": "When it prepares only a summary", "ar": "متى تُعدّ ملخّصًا فقط"},
    "Privacy and your data": {"it": "Privacy e i tuoi dati", "fr": "Confidentialité et vos données", "en": "Privacy and your data", "ar": "الخصوصية وبياناتك"},
    "Frequently asked questions": {"it": "Domande frequenti", "fr": "Questions fréquentes", "en": "Frequently asked questions", "ar": "الأسئلة الشائعة"},
    "You choose your country and your case, answer a few questions, and the platform shows what it can do: an indicative estimate where an official table allows it, or a guided check of your documents otherwise. No amount is ever invented.": {
        "it": "Scegli il paese e il caso, rispondi a poche domande e la piattaforma mostra cosa può fare: una stima indicativa dove una tabella ufficiale lo permette, oppure una verifica guidata dei documenti. Nessun importo viene mai inventato.",
        "fr": "Vous choisissez votre pays et votre dossier, répondez à quelques questions, et la plateforme montre ce qu'elle peut faire : une estimation indicative là où une table officielle le permet, sinon une vérification guidée de vos documents. Aucun montant n'est jamais inventé.",
        "en": "You choose your country and your case, answer a few questions, and the platform shows what it can do: an indicative estimate where an official table allows it, or a guided check of your documents otherwise. No amount is ever invented.",
        "ar": "تختار بلدك وقضيتك، وتجيب عن بضعة أسئلة، فتُظهر المنصة ما يمكنها فعله: تقديرًا إرشاديًا حيث يسمح جدول رسمي، أو فحصًا موجَّهًا لمستنداتك. ولا يُختلق أي مبلغ أبدًا."},
    "Gather what you have — the accident report, the medical report, the insurer's offer, pay slips. Upload them and the platform recognises each one, links it to the official sources and tells you what is still useful. Your files are analysed in memory and never stored.": {
        "it": "Raccogli ciò che hai — il verbale dell'incidente, il referto medico, l'offerta dell'assicurazione, le buste paga. Caricali e la piattaforma riconosce ognuno, lo collega alle fonti ufficiali e ti dice cosa è ancora utile. I file sono analizzati in memoria e mai conservati.",
        "fr": "Rassemblez ce que vous avez — le constat, le rapport médical, l'offre de l'assureur, les fiches de paie. Téléversez-les : la plateforme reconnaît chacun, le relie aux sources officielles et vous indique ce qui est encore utile. Vos fichiers sont analysés en mémoire et jamais conservés.",
        "en": "Gather what you have — the accident report, the medical report, the insurer's offer, pay slips. Upload them and the platform recognises each one, links it to the official sources and tells you what is still useful. Your files are analysed in memory and never stored.",
        "ar": "اجمع ما لديك — محضر الحادث، التقرير الطبي، عرض المؤمِّن، كشوف الراتب. حمّلها فتتعرّف المنصة على كل منها وتربطه بالمصادر الرسمية وتخبرك بما لا يزال مفيدًا. تُحلَّل ملفاتك في الذاكرة ولا تُخزَّن أبدًا."},
    "Every result is written in plain words: what you indicated, what the platform can do now, what is still missing and your next step. Where there is a figure, it is an indicative range from official sources — a starting point for negotiation, not a promise of payment.": {
        "it": "Ogni risultato è scritto in parole semplici: cosa hai indicato, cosa può fare ora la piattaforma, cosa manca ancora e il prossimo passo. Dove c'è un importo, è un intervallo indicativo dalle fonti ufficiali — un punto di partenza per la trattativa, non una promessa di pagamento.",
        "fr": "Chaque résultat est écrit en mots simples : ce que vous avez indiqué, ce que la plateforme peut faire maintenant, ce qui manque encore et votre prochaine étape. Lorsqu'il y a un chiffre, c'est une fourchette indicative issue des sources officielles — un point de départ pour la négociation, pas une promesse de paiement.",
        "en": "Every result is written in plain words: what you indicated, what the platform can do now, what is still missing and your next step. Where there is a figure, it is an indicative range from official sources — a starting point for negotiation, not a promise of payment.",
        "ar": "كل نتيجة مكتوبة بكلمات بسيطة: ما أوضحته، وما يمكن للمنصة فعله الآن، وما لا يزال ناقصًا، وخطوتك التالية. وحيث يوجد رقم، فهو نطاق إرشادي من المصادر الرسمية — نقطة انطلاق للتفاوض، لا وعدًا بالدفع."},
    "The library shows the laws, decrees and official tables behind every path. Each source says which country and category it belongs to, what it lets you do, and whether it can feed an estimate or only guide a document check.": {
        "it": "La biblioteca mostra leggi, decreti e tabelle ufficiali dietro ogni percorso. Ogni fonte indica a quale paese e categoria appartiene, cosa permette e se può alimentare una stima o solo guidare una verifica dei documenti.",
        "fr": "La bibliothèque montre les lois, décrets et tables officielles derrière chaque parcours. Chaque source indique à quel pays et catégorie elle appartient, ce qu'elle permet, et si elle peut alimenter une estimation ou seulement guider une vérification des documents.",
        "en": "The library shows the laws, decrees and official tables behind every path. Each source says which country and category it belongs to, what it lets you do, and whether it can feed an estimate or only guide a document check.",
        "ar": "تُظهر المكتبة القوانين والمراسيم والجداول الرسمية وراء كل مسار. يوضّح كل مصدر إلى أي بلد وفئة ينتمي، وما الذي يتيحه، وهل يمكنه تغذية تقدير أم توجيه التحقّق من المستندات فقط."},
    "The platform covers Italy, France, Belgium, Morocco and Tunisia, plus cross-border cases. What it can do differs by country and by case — the country pages and the coverage table show exactly where an estimate is available today.": {
        "it": "La piattaforma copre Italia, Francia, Belgio, Marocco e Tunisia, oltre ai casi transfrontalieri. Ciò che può fare varia per paese e per caso — le pagine paese e la tabella di copertura mostrano esattamente dove oggi è disponibile una stima.",
        "fr": "La plateforme couvre l'Italie, la France, la Belgique, le Maroc et la Tunisie, ainsi que les dossiers transfrontaliers. Ce qu'elle peut faire diffère selon le pays et le dossier — les pages pays et la table de couverture montrent exactement où une estimation est disponible aujourd'hui.",
        "en": "The platform covers Italy, France, Belgium, Morocco and Tunisia, plus cross-border cases. What it can do differs by country and by case — the country pages and the coverage table show exactly where an estimate is available today.",
        "ar": "تغطّي المنصة إيطاليا وفرنسا وبلجيكا والمغرب وتونس، إضافة إلى القضايا العابرة للحدود. وما يمكنها فعله يختلف حسب البلد والقضية — وتُظهر صفحات البلدان وجدول التغطية بالضبط أين يتوفّر تقدير اليوم."},
    "A figure appears only when an official table or formula is validated and tested. Where the law provides a complete national table, the platform can calculate an indicative range. Where it does not, the platform helps you prepare instead of guessing.": {
        "it": "Un importo compare solo quando una tabella o formula ufficiale è validata e testata. Dove la legge prevede una tabella nazionale completa, la piattaforma può calcolare un intervallo indicativo. Dove non c'è, la piattaforma ti aiuta a preparare invece di indovinare.",
        "fr": "Un chiffre n'apparaît que lorsqu'une table ou formule officielle est validée et testée. Là où la loi prévoit une table nationale complète, la plateforme peut calculer une fourchette indicative. Sinon, elle vous aide à préparer plutôt qu'à deviner.",
        "en": "A figure appears only when an official table or formula is validated and tested. Where the law provides a complete national table, the platform can calculate an indicative range. Where it does not, the platform helps you prepare instead of guessing.",
        "ar": "لا يظهر رقم إلا عندما يُعتمد جدول أو صيغة رسمية ويُختبر. حيث يوفّر القانون جدولًا وطنيًا كاملًا، يمكن للمنصة حساب نطاق إرشادي. وحيث لا يوجد، تساعدك المنصة على التجهيز بدل التخمين."},
    "When there is no validated table for your case, the platform does not show a number. Instead it organises your file, lists the official references that apply and prepares a clear summary you can send to the Studio.": {
        "it": "Quando non c'è una tabella validata per il tuo caso, la piattaforma non mostra un numero. Organizza invece il tuo fascicolo, elenca i riferimenti ufficiali applicabili e prepara un riepilogo chiaro da inviare allo Studio.",
        "fr": "Lorsqu'il n'y a pas de table validée pour votre dossier, la plateforme n'affiche pas de chiffre. Elle organise votre dossier, liste les références officielles applicables et prépare un récapitulatif clair à envoyer au Cabinet.",
        "en": "When there is no validated table for your case, the platform does not show a number. Instead it organises your file, lists the official references that apply and prepares a clear summary you can send to the Studio.",
        "ar": "عندما لا يوجد جدول معتمد لقضيتك، لا تعرض المنصة رقمًا. بل تنظّم ملفك، وتسرد المراجع الرسمية المنطبقة، وتُعدّ ملخّصًا واضحًا يمكنك إرساله إلى المكتب."},
    "You decide what to share. Uploaded files are analysed only to build your result and are not stored. Sensitive data is handled with care, and a simulation is never a legal engagement — that begins only with a separate written agreement.": {
        "it": "Decidi tu cosa condividere. I file caricati sono analizzati solo per costruire il tuo risultato e non vengono conservati. I dati sensibili sono trattati con cura e una simulazione non è mai un incarico legale — quello inizia solo con un accordo scritto separato.",
        "fr": "Vous décidez de ce que vous partagez. Les fichiers téléversés sont analysés uniquement pour construire votre résultat et ne sont pas conservés. Les données sensibles sont traitées avec soin, et une simulation n'est jamais un mandat juridique — celui-ci ne commence qu'avec un accord écrit distinct.",
        "en": "You decide what to share. Uploaded files are analysed only to build your result and are not stored. Sensitive data is handled with care, and a simulation is never a legal engagement — that begins only with a separate written agreement.",
        "ar": "أنت تقرّر ما تشاركه. تُحلَّل الملفات المرفوعة فقط لبناء نتيجتك ولا تُخزَّن. تُعالَج البيانات الحساسة بعناية، والمحاكاة ليست توكيلًا قانونيًا أبدًا — فذلك لا يبدأ إلا باتفاق مكتوب منفصل."},
    "Short answers to the questions people ask most: is the estimate binding, what does it cost, what happens to my documents, and how the Studio can help next.": {
        "it": "Risposte brevi alle domande più frequenti: la stima è vincolante, quanto costa, cosa succede ai miei documenti e come lo Studio può aiutarti dopo.",
        "fr": "Réponses courtes aux questions les plus fréquentes : l'estimation est-elle contraignante, combien ça coûte, qu'arrive-t-il à mes documents, et comment le Cabinet peut aider ensuite.",
        "en": "Short answers to the questions people ask most: is the estimate binding, what does it cost, what happens to my documents, and how the Studio can help next.",
        "ar": "إجابات قصيرة عن أكثر الأسئلة شيوعًا: هل التقدير مُلزِم، وكم يكلّف، وماذا يحدث لمستنداتي، وكيف يمكن للمكتب المساعدة لاحقًا."},
    "This documentation is informative and does not constitute legal advice. A simulation is indicative; the actual valuation depends on documents, expert reports, applicable law and the competent jurisdiction.": {
        "it": "Questa documentazione è informativa e non costituisce parere legale. Una simulazione è indicativa; la valutazione effettiva dipende da documenti, perizie, legge applicabile e giurisdizione competente.",
        "fr": "Cette documentation est informative et ne constitue pas un avis juridique. Une simulation est indicative ; l'évaluation réelle dépend des documents, des expertises, de la loi applicable et de la juridiction compétente.",
        "en": "This documentation is informative and does not constitute legal advice. A simulation is indicative; the actual valuation depends on documents, expert reports, applicable law and the competent jurisdiction.",
        "ar": "هذا التوثيق إعلامي ولا يشكّل استشارة قانونية. المحاكاة إرشادية؛ ويعتمد التقييم الفعلي على المستندات والتقارير الخبيرة والقانون المنطبق والجهة القضائية المختصة."},
    # CTA labels + nav
    "See the method": {"it": "Vedi il metodo", "fr": "Voir la méthode", "en": "See the method", "ar": "اطّلع على المنهجية"},
    "Open the source library": {"it": "Apri la biblioteca delle fonti", "fr": "Ouvrir la bibliothèque des sources", "en": "Open the source library", "ar": "افتح مكتبة المصادر"},
    "See what we can estimate": {"it": "Vedi cosa possiamo stimare", "fr": "Voir ce que nous pouvons estimer", "en": "See what we can estimate", "ar": "اطّلع على ما يمكننا تقديره"},
    "Prepare a summary": {"it": "Prepara un riepilogo", "fr": "Préparer un récapitulatif", "en": "Prepare a summary", "ar": "أعدّ ملخّصًا"},
    "Read the privacy notice": {"it": "Leggi l'informativa privacy", "fr": "Lire la politique de confidentialité", "en": "Read the privacy notice", "ar": "اقرأ إشعار الخصوصية"},
    "Read the FAQ": {"it": "Leggi le FAQ", "fr": "Lire la FAQ", "en": "Read the FAQ", "ar": "اقرأ الأسئلة الشائعة"},
    "Plain-language guides to the platform.": {"it": "Guide semplici alla piattaforma.", "fr": "Guides en langage clair de la plateforme.", "en": "Plain-language guides to the platform.", "ar": "أدلة بلغة بسيطة للمنصة."},
    "Open documentation": {"it": "Apri la documentazione", "fr": "Ouvrir la documentation", "en": "Open documentation", "ar": "افتح التوثيق"},
    # --- Documents explainer animation ---
    "How document recognition works": {"it": "Come funziona il riconoscimento dei documenti", "fr": "Comment fonctionne la reconnaissance des documents", "en": "How document recognition works", "ar": "كيف يعمل التعرّف على المستندات"},
    "Upload": {"it": "Carica", "fr": "Téléverser", "en": "Upload", "ar": "حمّل"},
    "Your document is analysed in memory and never stored.": {"it": "Il tuo documento è analizzato in memoria e mai conservato.", "fr": "Votre document est analysé en mémoire et jamais conservé.", "en": "Your document is analysed in memory and never stored.", "ar": "يُحلَّل مستندك في الذاكرة ولا يُخزَّن أبدًا."},
    "Recognise": {"it": "Riconosci", "fr": "Reconnaître", "en": "Recognise", "ar": "تعرّف"},
    "Your path": {"it": "Il tuo percorso", "fr": "Votre parcours", "en": "Your path", "ar": "مسارك"},
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
        print(f"[{lang}] added {added} new P40 msgids -> {po_path}")
    print(f"total appended: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
