"""Idempotently append P45 msgids (documentation 'guides by case type') to
django.po for it/fr/en/ar. NEVER runs makemessages."""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "Guides by case type": {"it": "Guide per categoria", "fr": "Guides par type de dossier", "en": "Guides by case type", "ar": "أدلة حسب نوع القضية"},
    "Find your case, see what you can do": {
        "it": "Trova il tuo caso, scopri cosa puoi fare",
        "fr": "Trouvez votre dossier, voyez ce que vous pouvez faire",
        "en": "Find your case, see what you can do", "ar": "اعثر على قضيتك واطّلع على ما يمكنك فعله"},
    "Work injury (INAIL)": {"it": "Infortunio sul lavoro (INAIL)", "fr": "Accident du travail (INAIL)", "en": "Work injury (INAIL)", "ar": "إصابة عمل (INAIL)"},
    "International inheritance": {"it": "Successione internazionale", "fr": "Succession internationale", "en": "International inheritance", "ar": "ميراث دولي"},
    "Foreign citizens in Italy": {"it": "Cittadini stranieri in Italia", "fr": "Citoyens étrangers en Italie", "en": "Foreign citizens in Italy", "ar": "مواطنون أجانب في إيطاليا"},
    # one-liners
    "An indicative estimate where the official table allows it.": {
        "it": "Una stima indicativa dove la tabella ufficiale lo permette.",
        "fr": "Une estimation indicative là où la table officielle le permet.",
        "en": "An indicative estimate where the official table allows it.",
        "ar": "تقدير إرشادي حيث يسمح الجدول الرسمي."},
    "Valued by age and disability percentage.": {
        "it": "Valutato per età e percentuale di invalidità.",
        "fr": "Évalué selon l'âge et le taux d'incapacité.",
        "en": "Valued by age and disability percentage.",
        "ar": "مُقدَّر حسب العمر ونسبة العجز."},
    "We read the clinical records and map the path.": {
        "it": "Leggiamo la documentazione clinica e tracciamo il percorso.",
        "fr": "Nous lisons les dossiers cliniques et traçons le parcours.",
        "en": "We read the clinical records and map the path.",
        "ar": "نقرأ السجلات السريرية ونرسم المسار."},
    "Compare an offer against the official reference.": {
        "it": "Confronta un'offerta con il riferimento ufficiale.",
        "fr": "Comparez une offre à la référence officielle.",
        "en": "Compare an offer against the official reference.",
        "ar": "قارن عرضًا بالمرجع الرسمي."},
    "Check your INAIL documents and any further claim.": {
        "it": "Verifica i documenti INAIL e l'eventuale danno ulteriore.",
        "fr": "Vérifiez vos documents INAIL et toute demande complémentaire.",
        "en": "Check your INAIL documents and any further claim.",
        "ar": "تحقّق من مستندات INAIL وأي مطالبة إضافية."},
    "An assisted path, handled with discretion.": {
        "it": "Un percorso assistito, gestito con discrezione.",
        "fr": "Un parcours accompagné, traité avec discrétion.",
        "en": "An assisted path, handled with discretion.",
        "ar": "مسار مُرافَق، يُدار بتكتّم."},
    "Framed on the Consumer Code; documental analysis.": {
        "it": "Inquadrato sul Codice del Consumo; analisi documentale.",
        "fr": "Cadré sur le Code de la consommation ; analyse documentaire.",
        "en": "Framed on the Consumer Code; documental analysis.",
        "ar": "مؤطَّر على قانون الاستهلاك؛ تحليل مستندي."},
    "Which law applies and what the shares are.": {
        "it": "Quale legge si applica e quali sono le quote.",
        "fr": "Quelle loi s'applique et quelles sont les parts.",
        "en": "Which law applies and what the shares are.",
        "ar": "أي قانون ينطبق وما هي الأنصبة."},
    "Multilingual handling of your case in Italy.": {
        "it": "Gestione multilingue del tuo caso in Italia.",
        "fr": "Gestion multilingue de votre dossier en Italie.",
        "en": "Multilingual handling of your case in Italy.",
        "ar": "معالجة متعددة اللغات لقضيتك في إيطاليا."},
    # --- Guided path studio (quick recommender) ---
    "Quick path finder": {"it": "Trova rapidamente il percorso", "fr": "Trouveur de parcours rapide", "en": "Quick path finder", "ar": "مُحدِّد المسار السريع"},
    "Guided studio": {"it": "Studio guidato", "fr": "Studio guidé", "en": "Guided studio", "ar": "الاستوديو الموجَّه"},
    "Answer a few questions, see the recommended path": {
        "it": "Rispondi a poche domande, vedi il percorso consigliato",
        "fr": "Répondez à quelques questions, voyez le parcours recommandé",
        "en": "Answer a few questions, see the recommended path",
        "ar": "أجب عن بضعة أسئلة، واطّلع على المسار الموصى به"},
    "Where did the case happen?": {"it": "Dove è successo il caso?", "fr": "Où le dossier s'est-il produit ?", "en": "Where did the case happen?", "ar": "أين وقعت القضية؟"},
    "Choose…": {"it": "Scegli…", "fr": "Choisir…", "en": "Choose…", "ar": "اختر…"},
    "Another country / cross-border": {"it": "Un altro paese / transfrontaliero", "fr": "Un autre pays / transfrontalier", "en": "Another country / cross-border", "ar": "بلد آخر / عابر للحدود"},
    "There is a physical injury": {"it": "C'è un danno fisico", "fr": "Il y a un dommage corporel", "en": "There is a physical injury", "ar": "هناك ضرر جسدي"},
    "I have an insurance offer": {"it": "Ho un'offerta assicurativa", "fr": "J'ai une offre d'assurance", "en": "I have an insurance offer", "ar": "لديّ عرض تأمين"},
    "I just want to understand which law applies": {
        "it": "Voglio solo capire quale legge si applica",
        "fr": "Je veux juste comprendre quelle loi s'applique",
        "en": "I just want to understand which law applies",
        "ar": "أريد فقط أن أفهم أي قانون ينطبق"},
    "You can prepare your documents": {"it": "Puoi preparare i documenti", "fr": "Vous pouvez préparer vos documents", "en": "You can prepare your documents", "ar": "يمكنك تجهيز مستنداتك"},
    "Upload what you have: the platform organises your file and lists the official references — no invented amount.": {
        "it": "Carica ciò che hai: la piattaforma organizza il fascicolo ed elenca i riferimenti ufficiali — nessun importo inventato.",
        "fr": "Téléversez ce que vous avez : la plateforme organise votre dossier et liste les références officielles — aucun montant inventé.",
        "en": "Upload what you have: the platform organises your file and lists the official references — no invented amount.",
        "ar": "حمّل ما لديك: تنظّم المنصة ملفك وتسرد المراجع الرسمية — دون أي مبلغ مُختلق."},
    "You can make an estimate": {"it": "Puoi fare una stima", "fr": "Vous pouvez faire une estimation", "en": "You can make an estimate", "ar": "يمكنك إجراء تقدير"},
    "An official validated table exists for this case: answer a few questions and get an indicative range.": {
        "it": "Per questo caso esiste una tabella ufficiale validata: rispondi a poche domande e ottieni un intervallo indicativo.",
        "fr": "Une table officielle validée existe pour ce dossier : répondez à quelques questions et obtenez une fourchette indicative.",
        "en": "An official validated table exists for this case: answer a few questions and get an indicative range.",
        "ar": "يوجد جدول رسمي معتمد لهذه القضية: أجب عن بضعة أسئلة واحصل على نطاق إرشادي."},
    "You can check the offer": {"it": "Puoi controllare l'offerta", "fr": "Vous pouvez vérifier l'offre", "en": "You can check the offer", "ar": "يمكنك التحقّق من العرض"},
    "Compare the insurer's offer against the official reference and see the deviation.": {
        "it": "Confronta l'offerta dell'assicuratore con il riferimento ufficiale e vedi lo scostamento.",
        "fr": "Comparez l'offre de l'assureur à la référence officielle et voyez l'écart.",
        "en": "Compare the insurer's offer against the official reference and see the deviation.",
        "ar": "قارن عرض المؤمِّن بالمرجع الرسمي واطّلع على الفارق."},
    "An official table is needed first": {"it": "Serve prima una tabella ufficiale", "fr": "Une table officielle est d'abord nécessaire", "en": "An official table is needed first", "ar": "يلزم أولًا جدول رسمي"},
    "There is no validated table for this country and case yet, so no figure is shown — prepare your documents and summary instead.": {
        "it": "Per questo paese e caso non esiste ancora una tabella validata, quindi non viene mostrato alcun importo — prepara invece i documenti e il riepilogo.",
        "fr": "Il n'existe pas encore de table validée pour ce pays et ce dossier, donc aucun montant n'est affiché — préparez plutôt vos documents et votre récapitulatif.",
        "en": "There is no validated table for this country and case yet, so no figure is shown — prepare your documents and summary instead.",
        "ar": "لا يوجد بعدُ جدول معتمد لهذا البلد وهذه القضية، لذا لا يُعرَض أي مبلغ — جهّز مستنداتك وملخّصك بدلًا من ذلك."},
    "You can understand which law may apply": {"it": "Puoi capire quale legge può valere", "fr": "Vous pouvez comprendre quelle loi peut s'appliquer", "en": "You can understand which law may apply", "ar": "يمكنك فهم أي قانون قد ينطبق"},
    "For cross-border cases, the platform helps you frame which country's law applies before anything else.": {
        "it": "Per i casi transfrontalieri, la piattaforma ti aiuta a inquadrare quale legge nazionale si applica prima di tutto.",
        "fr": "Pour les dossiers transfrontaliers, la plateforme vous aide à cadrer quelle loi nationale s'applique avant tout.",
        "en": "For cross-border cases, the platform helps you frame which country's law applies before anything else.",
        "ar": "في القضايا العابرة للحدود، تساعدك المنصة على تحديد قانون أي بلد ينطبق قبل كل شيء."},
    "Understand the applicable law": {"it": "Capisci la legge applicabile", "fr": "Comprendre la loi applicable", "en": "Understand the applicable law", "ar": "افهم القانون المنطبق"},
    "A quick guide only — no amount is shown without a validated official table. See the full router below.": {
        "it": "Solo una guida rapida — nessun importo viene mostrato senza una tabella ufficiale validata. Vedi il router completo qui sotto.",
        "fr": "Un guide rapide seulement — aucun montant n'est affiché sans table officielle validée. Voir le routeur complet ci-dessous.",
        "en": "A quick guide only — no amount is shown without a validated official table. See the full router below.",
        "ar": "دليل سريع فقط — لا يُعرَض أي مبلغ دون جدول رسمي معتمد. اطّلع على المُوجِّه الكامل أدناه."},
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
        print(f"[{lang}] added {added} new P45 msgids -> {po_path}")
    print(f"total appended: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
