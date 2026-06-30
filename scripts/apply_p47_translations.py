"""Idempotently append P47 msgids (honest 'why no amount' callout) to django.po
for it/fr/en/ar. NEVER runs makemessages."""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "Why some sections show no amount": {
        "it": "Perché alcune sezioni non mostrano un importo",
        "fr": "Pourquoi certaines sections n'affichent aucun montant",
        "en": "Why some sections show no amount",
        "ar": "لماذا لا تُظهر بعض الأقسام أي مبلغ"},
    "Why do some sections show no amount?": {
        "it": "Perché alcune sezioni non mostrano un importo?",
        "fr": "Pourquoi certaines sections n'affichent-elles aucun montant ?",
        "en": "Why do some sections show no amount?",
        "ar": "لماذا لا تُظهر بعض الأقسام أي مبلغ؟"},
    "We only show an amount when a verified official rule or table exists.": {
        "it": "Mostriamo un importo solo quando esiste una regola o tabella ufficiale verificata.",
        "fr": "Nous n'affichons un montant que lorsqu'une règle ou une table officielle vérifiée existe.",
        "en": "We only show an amount when a verified official rule or table exists.",
        "ar": "نعرض مبلغًا فقط عندما توجد قاعدة أو جدول رسمي موثّق."},
    "If a table is missing, we still help you prepare your documents.": {
        "it": "Se manca una tabella, ti aiutiamo comunque a preparare i documenti.",
        "fr": "S'il manque une table, nous vous aidons tout de même à préparer vos documents.",
        "en": "If a table is missing, we still help you prepare your documents.",
        "ar": "إذا كان هناك جدول مفقود، فإننا نساعدك مع ذلك على تجهيز مستنداتك."},
    "A correct summary is better than an unreliable number.": {
        "it": "Meglio un riepilogo corretto che un numero non affidabile.",
        "fr": "Mieux vaut un récapitulatif correct qu'un chiffre peu fiable.",
        "en": "A correct summary is better than an unreliable number.",
        "ar": "ملخّص صحيح خير من رقم غير موثوق."},
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
        print(f"[{lang}] added {added} new P47 msgids -> {po_path}")
    print(f"total appended: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
