"""Idempotently append P44 msgids (documentation 2.0: start-here, glossary,
mini-FAQ; mega-menu mini-previews) to django.po for it/fr/en/ar. NEVER runs
makemessages."""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- Documentation: Start here ---
    "Start here": {"it": "Inizia qui", "fr": "Commencez ici", "en": "Start here", "ar": "ابدأ من هنا"},
    "New here? Three steps to your first simulation": {
        "it": "Sei nuovo? Tre passi per la tua prima simulazione",
        "fr": "Nouveau ? Trois étapes pour votre première simulation",
        "en": "New here? Three steps to your first simulation",
        "ar": "جديد هنا؟ ثلاث خطوات نحو محاكاتك الأولى"},
    "Choose your country and your case.": {
        "it": "Scegli il paese e il caso.", "fr": "Choisissez votre pays et votre dossier.",
        "en": "Choose your country and your case.", "ar": "اختر بلدك وقضيتك."},
    "Answer a few simple questions.": {
        "it": "Rispondi a poche domande semplici.", "fr": "Répondez à quelques questions simples.",
        "en": "Answer a few simple questions.", "ar": "أجب عن بضعة أسئلة بسيطة."},
    "Get an estimate or a clear documental summary.": {
        "it": "Ottieni una stima o un riepilogo documentale chiaro.",
        "fr": "Obtenez une estimation ou un récapitulatif documentaire clair.",
        "en": "Get an estimate or a clear documental summary.",
        "ar": "احصل على تقدير أو ملخّص مستندي واضح."},
    "Start the guided path": {
        "it": "Avvia il percorso guidato", "fr": "Lancer le parcours guidé",
        "en": "Start the guided path", "ar": "ابدأ المسار الموجَّه"},
    "Read how it works": {
        "it": "Leggi come funziona", "fr": "Lire comment ça marche",
        "en": "Read how it works", "ar": "اقرأ كيف يعمل"},
    # --- Documentation: glossary ---
    "Simple glossary": {"it": "Glossario semplice", "fr": "Glossaire simple", "en": "Simple glossary", "ar": "مسرد مبسّط"},
    "A few words, explained plainly": {
        "it": "Poche parole, spiegate in modo semplice",
        "fr": "Quelques mots, expliqués simplement",
        "en": "A few words, explained plainly", "ar": "بعض الكلمات، مشروحة ببساطة"},
    "Indicative estimate": {"it": "Stima indicativa", "fr": "Estimation indicative", "en": "Indicative estimate", "ar": "تقدير إرشادي"},
    "A range, not a promise — a starting point for negotiation, based on official sources.": {
        "it": "Un intervallo, non una promessa — un punto di partenza per la trattativa, basato su fonti ufficiali.",
        "fr": "Une fourchette, pas une promesse — un point de départ pour la négociation, fondé sur des sources officielles.",
        "en": "A range, not a promise — a starting point for negotiation, based on official sources.",
        "ar": "نطاق، لا وعد — نقطة انطلاق للتفاوض، استنادًا إلى مصادر رسمية."},
    "A law, decree or official table that grounds what the platform shows.": {
        "it": "Una legge, un decreto o una tabella ufficiale che fonda ciò che la piattaforma mostra.",
        "fr": "Une loi, un décret ou une table officielle qui fonde ce que la plateforme affiche.",
        "en": "A law, decree or official table that grounds what the platform shows.",
        "ar": "قانون أو مرسوم أو جدول رسمي يستند إليه ما تعرضه المنصة."},
    "Official table": {"it": "Tabella ufficiale", "fr": "Table officielle", "en": "Official table", "ar": "جدول رسمي"},
    "The validated table that lets the platform calculate. Without it, no figure is shown.": {
        "it": "La tabella validata che permette alla piattaforma di calcolare. Senza, non viene mostrato alcun importo.",
        "fr": "La table validée qui permet à la plateforme de calculer. Sans elle, aucun montant n'est affiché.",
        "en": "The validated table that lets the platform calculate. Without it, no figure is shown.",
        "ar": "الجدول المعتمد الذي يتيح للمنصة الحساب. وبدونه لا يُعرَض أي مبلغ."},
    "The harm to your health and daily life, valued by age and disability percentage.": {
        "it": "Il danno alla tua salute e alla vita quotidiana, valutato per età e percentuale di invalidità.",
        "fr": "L'atteinte à votre santé et à votre vie quotidienne, évaluée selon l'âge et le taux d'incapacité.",
        "en": "The harm to your health and daily life, valued by age and disability percentage.",
        "ar": "الضرر الذي يلحق بصحتك وحياتك اليومية، مُقدَّرًا حسب العمر ونسبة العجز."},
    "Documental check": {"it": "Verifica documentale", "fr": "Vérification documentaire", "en": "Documental check", "ar": "تحقّق مستندي"},
    "When there is no table, the platform organises your documents instead of guessing.": {
        "it": "Quando non c'è una tabella, la piattaforma organizza i tuoi documenti invece di indovinare.",
        "fr": "Lorsqu'il n'y a pas de table, la plateforme organise vos documents au lieu de deviner.",
        "en": "When there is no table, the platform organises your documents instead of guessing.",
        "ar": "عندما لا يوجد جدول، تنظّم المنصة مستنداتك بدل التخمين."},
    "Applicable law": {"it": "Legge applicabile", "fr": "Loi applicable", "en": "Applicable law", "ar": "القانون المنطبق"},
    "For cross-border cases, which country's law applies to your situation.": {
        "it": "Per i casi transfrontalieri, quale legge nazionale si applica alla tua situazione.",
        "fr": "Pour les dossiers transfrontaliers, quelle loi nationale s'applique à votre situation.",
        "en": "For cross-border cases, which country's law applies to your situation.",
        "ar": "في القضايا العابرة للحدود، قانون أي بلد ينطبق على وضعك."},
    # --- Documentation: mini-FAQ ---
    "Quick answers": {"it": "Risposte rapide", "fr": "Réponses rapides", "en": "Quick answers", "ar": "إجابات سريعة"},
    "Common questions": {"it": "Domande comuni", "fr": "Questions courantes", "en": "Common questions", "ar": "أسئلة شائعة"},
    "Is the estimate binding?": {"it": "La stima è vincolante?", "fr": "L'estimation est-elle contraignante ?", "en": "Is the estimate binding?", "ar": "هل التقدير مُلزِم؟"},
    "No. It is indicative and does not constitute legal advice or a guarantee. The actual amount depends on documents, expert reports and the competent court.": {
        "it": "No. È indicativa e non costituisce parere legale né garanzia. L'importo effettivo dipende da documenti, perizie e dal giudice competente.",
        "fr": "Non. Elle est indicative et ne constitue ni un avis juridique ni une garantie. Le montant réel dépend des documents, des expertises et du tribunal compétent.",
        "en": "No. It is indicative and does not constitute legal advice or a guarantee. The actual amount depends on documents, expert reports and the competent court.",
        "ar": "لا. إنه إرشادي ولا يشكّل استشارة قانونية ولا ضمانًا. ويعتمد المبلغ الفعلي على المستندات والتقارير الخبيرة والمحكمة المختصة."},
    "What does it cost to try?": {"it": "Quanto costa provare?", "fr": "Combien coûte un essai ?", "en": "What does it cost to try?", "ar": "كم تكلفة التجربة؟"},
    "Running a simulation and preparing a summary is free. A professional engagement begins only with a separate written agreement.": {
        "it": "Eseguire una simulazione e preparare un riepilogo è gratuito. Un incarico professionale inizia solo con un accordo scritto separato.",
        "fr": "Lancer une simulation et préparer un récapitulatif est gratuit. Un mandat professionnel ne commence qu'avec un accord écrit distinct.",
        "en": "Running a simulation and preparing a summary is free. A professional engagement begins only with a separate written agreement.",
        "ar": "تشغيل محاكاة وإعداد ملخّص مجاني. ولا يبدأ التوكيل المهني إلا باتفاق مكتوب منفصل."},
    "What happens to my documents?": {"it": "Cosa succede ai miei documenti?", "fr": "Qu'arrive-t-il à mes documents ?", "en": "What happens to my documents?", "ar": "ماذا يحدث لمستنداتي؟"},
    "They are analysed in memory to build your result and are not stored. You decide what to share with the Studio.": {
        "it": "Sono analizzati in memoria per costruire il tuo risultato e non vengono conservati. Decidi tu cosa condividere con lo Studio.",
        "fr": "Ils sont analysés en mémoire pour construire votre résultat et ne sont pas conservés. Vous décidez de ce que vous partagez avec le Cabinet.",
        "en": "They are analysed in memory to build your result and are not stored. You decide what to share with the Studio.",
        "ar": "تُحلَّل في الذاكرة لبناء نتيجتك ولا تُخزَّن. وأنت تقرّر ما تشاركه مع المكتب."},
    "Why does my case show no amount?": {"it": "Perché il mio caso non mostra un importo?", "fr": "Pourquoi mon dossier n'affiche aucun montant ?", "en": "Why does my case show no amount?", "ar": "لماذا لا تُظهر قضيتي أي مبلغ؟"},
    "Because there is no validated official table for it yet. The platform never invents a figure — it helps you prepare your documents instead.": {
        "it": "Perché non esiste ancora una tabella ufficiale validata. La piattaforma non inventa mai un importo — ti aiuta invece a preparare i documenti.",
        "fr": "Parce qu'il n'existe pas encore de table officielle validée. La plateforme n'invente jamais de montant — elle vous aide plutôt à préparer vos documents.",
        "en": "Because there is no validated official table for it yet. The platform never invents a figure — it helps you prepare your documents instead.",
        "ar": "لأنه لا يوجد بعدُ جدول رسمي معتمد لها. لا تختلق المنصة أي مبلغ أبدًا — بل تساعدك على تجهيز مستنداتك."},
    # --- Mega-menu mini-previews ---
    "In 3 steps: country, case, documents.": {
        "it": "In 3 passaggi: paese, caso, documenti.", "fr": "En 3 étapes : pays, dossier, documents.",
        "en": "In 3 steps: country, case, documents.", "ar": "في 3 خطوات: البلد، القضية، المستندات."},
    "Upload PDF or images — your files are never stored.": {
        "it": "Carica PDF o immagini — i tuoi file non vengono mai conservati.",
        "fr": "Téléversez PDF ou images — vos fichiers ne sont jamais conservés.",
        "en": "Upload PDF or images — your files are never stored.",
        "ar": "حمّل ملفات PDF أو صورًا — لا تُخزَّن ملفاتك أبدًا."},
    "Choose where the case happened.": {
        "it": "Scegli dove è successo il caso.", "fr": "Choisissez où le dossier s'est produit.",
        "en": "Choose where the case happened.", "ar": "اختر أين وقعت القضية."},
    "See the official rules we use — and when a table allows a calculation.": {
        "it": "Vedi le regole ufficiali che usiamo — e quando una tabella permette il calcolo.",
        "fr": "Voyez les règles officielles que nous utilisons — et quand une table permet le calcul.",
        "en": "See the official rules we use — and when a table allows a calculation.",
        "ar": "اطّلع على القواعد الرسمية التي نستخدمها — ومتى يتيح جدولٌ الحساب."},
    "Understand how the platform works, simply.": {
        "it": "Capisci come funziona la piattaforma, in modo semplice.",
        "fr": "Comprenez simplement comment fonctionne la plateforme.",
        "en": "Understand how the platform works, simply.",
        "ar": "افهم كيف تعمل المنصة، ببساطة."},
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
        print(f"[{lang}] added {added} new P44 msgids -> {po_path}")
    print(f"total appended: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
