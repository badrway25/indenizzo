"""Catalog-hygiene gate for the translation `.po` files.

Django ignores `#, fuzzy` entries at runtime and renders the (English) source
msgid instead — which is exactly how the GDPR art. 9 special-categories consent
labels shipped in English on /fr/ and /ar/ before this gate existed. The
templates were clean; the leak lived in the catalogs, where no test looked.

This test parses every project catalog and fails on:
  1. ANY `#, fuzzy` entry (the silent-leak failure mode), and
  2. an empty/untranslated msgstr for the public GDPR-consent strings a user
     must accept before submitting health/family data on /fr/, /ar/ and /it/.

It reads the `.po` sources directly (no compile step needed) so it is
deterministic in CI regardless of whether `compilemessages` has run.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

# Public consent strings that must never regress to the English source on the
# non-default languages. Keyed by the fully-concatenated msgid.
PUBLIC_CONSENT_MSGIDS = (
    "I expressly consent to the processing of special categories of personal "
    "data (health, disability, lost income) under GDPR art. 9.2.a, for the sole "
    "purpose of producing this indicative simulation.",
    "I expressly consent to the processing of special categories of personal "
    "data (family events, deaths, civil-status data) under GDPR art. 9.2.a, for "
    "the sole purpose of producing this indicative simulation.",
    "You must give the explicit special-categories consent (GDPR art. 9) to run "
    "a simulation.",
    "You must give the explicit special-categories consent (GDPR art. 9) to "
    "send your request.",
)

# Languages whose catalogs must carry a real translation of the consent strings.
# 'en' is the source language (msgstr left empty → falls back to msgid), so it
# is intentionally excluded from the consent assertion but still fuzzy-checked.
CONSENT_REQUIRED_LANGS = ("it", "fr", "ar")
ALL_LANGS = ("it", "fr", "ar", "en")


def _locale_dir() -> Path:
    return Path(settings.LOCALE_PATHS[0])


def _po_path(lang: str) -> Path:
    return _locale_dir() / lang / "LC_MESSAGES" / "django.po"


def _parse_po(path: str | Path):
    """Minimal .po parser → list of dicts {msgid, msgstr, fuzzy}.

    Blocks are separated by blank lines; msgid/msgstr values may span multiple
    quoted continuation lines. Good enough for hygiene assertions (no plural or
    msgctxt handling needed here).
    """
    text = Path(path).read_text(encoding="utf-8")
    entries = []
    for block in text.split("\n\n"):
        lines = block.splitlines()
        fuzzy = any(l.startswith("#,") and "fuzzy" in l for l in lines)
        msgid_parts, msgstr_parts, state = [], [], None
        for ln in lines:
            if ln.startswith("msgid "):
                state = "msgid"
                msgid_parts.append(ln[len("msgid "):].strip().strip('"'))
            elif ln.startswith("msgstr "):
                state = "msgstr"
                msgstr_parts.append(ln[len("msgstr "):].strip().strip('"'))
            elif ln.startswith('"') and state == "msgid":
                msgid_parts.append(ln.strip().strip('"'))
            elif ln.startswith('"') and state == "msgstr":
                msgstr_parts.append(ln.strip().strip('"'))
        if not msgid_parts:
            continue
        entries.append(
            {
                "msgid": "".join(msgid_parts),
                "msgstr": "".join(msgstr_parts),
                "fuzzy": fuzzy,
            }
        )
    return entries


def test_no_fuzzy_entries_in_any_catalog():
    """A fuzzy entry is silently ignored at runtime → English leak. Forbid all."""
    offenders = {}
    for lang in ALL_LANGS:
        path = _po_path(lang)
        assert path.exists(), f"Missing catalog: {path}"
        fuzzy_ids = [e["msgid"] for e in _parse_po(path) if e["fuzzy"] and e["msgid"]]
        if fuzzy_ids:
            offenders[lang] = fuzzy_ids
    assert not offenders, (
        "Fuzzy entries leak the English source at runtime. Resolve each "
        "(verify the translation matches the current msgid, then drop the "
        f"`#, fuzzy` flag) and recompile. Offenders: {offenders}"
    )


def test_public_consent_strings_are_translated():
    """The GDPR art. 9 consent strings must be translated in it/fr/ar."""
    leaks = []
    for lang in CONSENT_REQUIRED_LANGS:
        by_id = {e["msgid"]: e for e in _parse_po(_po_path(lang))}
        for msgid in PUBLIC_CONSENT_MSGIDS:
            entry = by_id.get(msgid)
            assert entry is not None, f"[{lang}] consent msgid not in catalog: {msgid!r}"
            if not entry["msgstr"].strip() or entry["fuzzy"]:
                leaks.append((lang, msgid))
    assert not leaks, (
        "Public GDPR special-categories consent strings render in English on a "
        f"non-source language (empty or fuzzy msgstr): {leaks}"
    )
