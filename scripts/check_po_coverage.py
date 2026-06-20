#!/usr/bin/env python
"""Minimal i18n translation-coverage gate (C1).

Computes, per locale, the share of non-empty ``msgstr`` over translatable
``msgid`` entries (the header entry with empty msgid is ignored), and fails
if a locale drops below a configured floor.

This is intentionally a *no-regression* gate, NOT a 100% gate: the full
legal translation of the catalog is a Studio deliverable (C1). The floor
exists so that already-translated strings cannot silently regress and so
new high-priority strings get translated before merge.

Usage::

    python scripts/check_po_coverage.py --min it=30 --min fr=30 --min ar=30

Exit code 1 if any locale is below its floor, else 0.
"""

from __future__ import annotations

import argparse
import pathlib
import sys


def _join_quoted(parts: list[str]) -> str:
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
            out.append(p[1:-1])
    return "".join(out)


def parse_po(path: pathlib.Path) -> tuple[int, int]:
    """Return (real_translated, total).

    A msgid counts as REAL-translated only when its msgstr is non-empty AND the
    entry is NOT flagged ``#, fuzzy``. Fuzzy entries carry a guessed/stale
    translation that ``msgfmt`` skips at compile time (the page renders the
    English source), so counting them would over-report visible coverage.
    """
    lines = path.read_text(encoding="utf-8").split("\n")
    total = translated = 0
    i, n = 0, len(lines)
    fuzzy = False
    while i < n:
        line = lines[i]
        if line.startswith("#,"):
            # Flags line (e.g. "#, fuzzy" or "#, fuzzy, python-format").
            fuzzy = "fuzzy" in [f.strip() for f in line[2:].split(",")]
            i += 1
            continue
        if line.startswith("msgid "):
            mid = [line[len("msgid ") :]]
            j = i + 1
            while j < n and lines[j].startswith('"'):
                mid.append(lines[j])
                j += 1
            msgid = _join_quoted(mid)
            if j < n and lines[j].startswith("msgstr "):
                ms = [lines[j][len("msgstr ") :]]
                k = j + 1
                while k < n and lines[k].startswith('"'):
                    ms.append(lines[k])
                    k += 1
                msgstr = _join_quoted(ms)
                if msgid != "":  # skip the PO header entry
                    total += 1
                    if msgstr.strip() and not fuzzy:
                        translated += 1
                fuzzy = False
                i = k
                continue
        # Any non-comment, non-msgid line resets the pending fuzzy flag.
        if not line.startswith("#"):
            fuzzy = False
        i += 1
    return translated, total


def main() -> int:
    ap = argparse.ArgumentParser(description="i18n coverage gate")
    ap.add_argument("--min", action="append", default=[], help="locale=pct (e.g. it=30)")
    ap.add_argument("--root", default="locale")
    args = ap.parse_args()

    floors: dict[str, float] = {}
    for m in args.min:
        loc, _, pct = m.partition("=")
        floors[loc] = float(pct or 0)

    root = pathlib.Path(args.root)
    locales = sorted(floors) or ["it", "fr", "ar"]
    failed = False
    for loc in locales:
        po = root / loc / "LC_MESSAGES" / "django.po"
        if not po.is_file():
            print(f"[skip] {loc}: no catalog at {po}")
            continue
        tr, tot = parse_po(po)
        pct = 100.0 * tr / tot if tot else 0.0
        floor = floors.get(loc, 0.0)
        ok = pct >= floor
        print(f"[{'ok' if ok else 'FAIL'}] {loc}: {tr}/{tot} = {pct:.1f}% (floor {floor:.0f}%)")
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
