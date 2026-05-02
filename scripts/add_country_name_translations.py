"""Idempotently append country name msgids to django.po files for it/fr/en/ar."""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Force stdout to UTF-8 so Arabic / arrows print on Windows cp1252 consoles.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# msgid -> {lang: msgstr}
TRANSLATIONS = {
    "Italy": {"it": "Italia", "fr": "Italie", "en": "Italy", "ar": "إيطاليا"},
    "France": {"it": "Francia", "fr": "France", "en": "France", "ar": "فرنسا"},
    "Belgium": {"it": "Belgio", "fr": "Belgique", "en": "Belgium", "ar": "بلجيكا"},
    "Morocco": {"it": "Marocco", "fr": "Maroc", "en": "Morocco", "ar": "المغرب"},
    "Tunisia": {"it": "Tunisia", "fr": "Tunisie", "en": "Tunisia", "ar": "تونس"},
}


def has_msgid(po_text: str, msgid: str) -> bool:
    needle = f'\nmsgid "{msgid}"\n'
    return needle in po_text


def append_block(po_path: Path, lang: str) -> int:
    text = po_path.read_text(encoding="utf-8")
    added = 0
    new_chunks: list[str] = []
    for msgid, langs in TRANSLATIONS.items():
        if has_msgid(text, msgid):
            continue
        msgstr = langs[lang]
        new_chunks.append(f'\nmsgid "{msgid}"\nmsgstr "{msgstr}"\n')
        added += 1
    if added:
        po_path.write_text(text + "".join(new_chunks), encoding="utf-8")
    return added


def main() -> int:
    base = Path(__file__).resolve().parents[1] / "locale"
    total = 0
    for lang in ("it", "fr", "en", "ar"):
        po_path = base / lang / "LC_MESSAGES" / "django.po"
        added = append_block(po_path, lang)
        total += added
        print(f"[{lang}] added {added} new country msgids -> {po_path}")
    print(f"total appended: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
