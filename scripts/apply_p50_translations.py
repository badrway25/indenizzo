"""Idempotently append P50 msgids ("what it takes to show an amount" FAQ) to
django.po for it/fr/en/ar. NEVER runs makemessages."""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "What does it take to show an amount?": {
        "it": "Cosa serve per mostrare un importo?",
        "fr": "Que faut-il pour afficher un montant ?",
        "en": "What does it take to show an amount?",
        "ar": "ما الذي يلزم لعرض مبلغ؟"},
    "Three things: an official table or rule from a public authority, a clear way to apply it to your case, and a verified example to check it against. When all three exist we show the amount — otherwise we prepare your documents.": {
        "it": "Tre cose: una tabella o regola ufficiale di un ente pubblico, un modo chiaro per applicarla al tuo caso e un esempio verificato per controllarla. Quando ci sono tutte e tre mostriamo l'importo, altrimenti prepariamo i tuoi documenti.",
        "fr": "Trois choses : une table ou une règle officielle d'une autorité publique, une façon claire de l'appliquer à votre cas, et un exemple vérifié pour la contrôler. Quand les trois existent, nous affichons le montant ; sinon, nous préparons vos documents.",
        "en": "Three things: an official table or rule from a public authority, a clear way to apply it to your case, and a verified example to check it against. When all three exist we show the amount — otherwise we prepare your documents.",
        "ar": "ثلاثة أمور: جدول أو قاعدة رسمية من جهة عامة، وطريقة واضحة لتطبيقها على حالتك، ومثال موثّق للتحقق منها. عند توفّر الثلاثة نعرض المبلغ، وإلا نُجهّز مستنداتك."},
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
        print(f"[{lang}] added {added} new P50 msgids -> {po_path}")
    print(f"total appended: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
