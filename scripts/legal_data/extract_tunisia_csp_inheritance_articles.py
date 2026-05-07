"""F-tunisia-csp-livre-ix-mapping-draft-pass1 — CSP Livre IX extractor.

Extract every article anchored in the official Code du statut personnel
HTML page for Livre IX (De la succession), produce a deterministic
JSON snapshot under
``legal_data/sources/tunisia/extracted/csp_livre_ix_inheritance_articles.json``
and a human-readable markdown summary under
``docs/legal_sources/TUNISIA_CSP_LIVRE_IX_INHERITANCE_EXTRACTION.md``.

Strategy:

* The source is the real, validated HTML
  ``tn-code-statut-personnel-livre-ix-succession.html`` (sha
  ``ab8078968ccfa07e…``, 36 183 B). The file contains 22 articles
  (122–143) anchored as ``<a id="aXXX"></a>``.
* For each anchor we capture the content from the anchor to the
  next anchor (or to the trailing ``<hr>`` separator block when the
  anchor is the last one).
* We strip HTML tags, decode entities, normalise whitespace.
* We tag the extraction with ``extraction_basis="official_html"``
  and a per-article ``extraction_confidence`` derived from the
  density of structural cues in the body (article header marker,
  minimum length, presence of a doctrinal keyword).

This script is **read-only** with respect to ``LegalSource``,
``CompensationDataset``, ``CalculationFormula``: the extraction
artefact is the only output.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_HTML = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "tunisia"
    / "official_downloaded"
    / "tn-code-statut-personnel-livre-ix-succession.html"
)
EXTRACT_JSON = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "tunisia"
    / "extracted"
    / "csp_livre_ix_inheritance_articles.json"
)
EXTRACT_DOC = (
    REPO_ROOT / "docs" / "legal_sources" / "TUNISIA_CSP_LIVRE_IX_INHERITANCE_EXTRACTION.md"
)

SOURCE_SLUG = "tn-code-statut-personnel-livre-ix-succession"
EXPECTED_SHA = "ab8078968ccfa07eaefc34bb38a1ec49071d000dfe0ffd85b1410d343a348ffd"
EXPECTED_SIZE = 36183


_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_ANCHOR_RE = re.compile(r'<a id="a(\d+)"></a>')


def _decode_text(raw_html: str) -> str:
    txt = _TAG_RE.sub(" ", raw_html)
    txt = html.unescape(txt)
    # Surrogate / mojibake clean-up: the source uses Latin-1 entities
    # plus a few non-breaking-space characters.
    txt = txt.replace("\xa0", " ").replace(" ", " ")
    txt = _WHITESPACE_RE.sub(" ", txt).strip()
    return txt


def _confidence_for(article_no: int, text: str) -> str:
    """Per-article extraction confidence.

    * ``high`` — text length ≥ 80 chars, contains at least one
      doctrinal keyword (Hajb, fardh, héritage, succession,
      part, fils, fille, mère, père, frère, sœur).
    * ``medium`` — text length ≥ 40 chars.
    * ``low`` — anything shorter (anchor present but body missing).
    """
    keywords = (
        "hajb",
        "fardh",
        "héritage",
        "succession",
        "héritier",
        "héritiers",
        "part",
        "moitié",
        "tiers",
        "quart",
        "huitième",
        "fils",
        "fille",
        "mère",
        "père",
        "frère",
        "sœur",
        "petit-fils",
        "petite-fille",
        "germain",
        "consanguin",
        "utérin",
    )
    lo = text.lower()
    has_keyword = any(k in lo for k in keywords)
    if len(text) >= 80 and has_keyword:
        return "high"
    if len(text) >= 40:
        return "medium"
    return "low"


def _extract_articles(raw: bytes) -> list[dict]:
    body = raw.decode("utf-8", errors="replace")
    anchors = list(_ANCHOR_RE.finditer(body))
    if not anchors:
        return []
    boundaries = [(int(m.group(1)), m.start(), m.end()) for m in anchors]
    articles: list[dict] = []
    for i, (article_no, _, end) in enumerate(boundaries):
        next_start = boundaries[i + 1][1] if i + 1 < len(boundaries) else len(body)
        # Trim to the trailing <table width="100%"> block — the
        # horizontal rule that separates articles. If the table is
        # missing (e.g. the very last article), keep until next
        # anchor / EOF.
        chunk = body[end:next_start]
        cut = re.search(r'<table\s+width="100%">', chunk)
        if cut:
            chunk = chunk[: cut.start()]
        text = _decode_text(chunk)
        # Drop the leading article number repeat (the body often
        # starts with " 122. " right after the anchor).
        text = re.sub(rf"^\s*{article_no}\s*\.\s*", "", text)
        articles.append(
            {
                "article": article_no,
                "text": text,
                "extraction_confidence": _confidence_for(article_no, text),
            }
        )
    return articles


def main() -> int:
    if not SRC_HTML.is_file():
        print(f"[FAIL] source HTML missing: {SRC_HTML}", file=sys.stderr)
        return 1
    raw = SRC_HTML.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != EXPECTED_SHA:
        print(
            f"[FAIL] source sha drift: expected {EXPECTED_SHA[:16]}…, got {sha[:16]}…",
            file=sys.stderr,
        )
        return 2
    if len(raw) != EXPECTED_SIZE:
        print(
            f"[FAIL] source size drift: expected {EXPECTED_SIZE}, got {len(raw)}", file=sys.stderr
        )
        return 3

    articles = _extract_articles(raw)
    payload = {
        "schema_version": "1.0",
        "iter": "F-tunisia-csp-livre-ix-mapping-draft-pass1",
        "country": "TN",
        "source_slug": SOURCE_SLUG,
        "source_sha256": sha,
        "size_bytes": len(raw),
        "extraction_basis": "official_html",
        "extractor": "scripts/legal_data/extract_tunisia_csp_inheritance_articles.py",
        "extracted_at": datetime.now(UTC).isoformat(),
        "page_scope": "Livre IX — articles 122–143 (Hajb + Fardh fragment)",
        "scope_note": (
            "The official jurisitetunisie.com page for the Code du statut "
            "personnel — Livre IX exposes only articles 122–143 of the "
            "Successions book (Hajb / éviction + the first share rules). "
            "Articles 85–121 and 144–152 are on adjacent pages that have "
            "not yet been fetched into the local source tree. The mapping "
            "draft restricts itself to what is anchored in this single "
            "validated file."
        ),
        "articles_count": len(articles),
        "articles": [
            {
                "article": a["article"],
                "source_slug": SOURCE_SLUG,
                "source_sha256": sha,
                "extraction_basis": "official_html",
                "extraction_confidence": a["extraction_confidence"],
                "text": a["text"],
            }
            for a in articles
        ],
    }
    EXTRACT_JSON.parent.mkdir(parents=True, exist_ok=True)
    EXTRACT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[ok] wrote {EXTRACT_JSON.relative_to(REPO_ROOT)}")
    print(f"     articles: {len(articles)}")
    print(f"     sha:      {sha}")

    # Markdown summary
    EXTRACT_DOC.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# Tunisia — CSP Livre IX inheritance extraction",
        "",
        "Iter: `F-tunisia-csp-livre-ix-mapping-draft-pass1`.",
        "",
        f"Source: `{SOURCE_SLUG}` " f"(sha256 `{sha}`, {len(raw)} bytes).",
        "",
        "Scope note: the validated jurisitetunisie.com page hosts only",
        "articles 122–143 of Livre IX (Hajb + the first share rules).",
        "Articles 85–121 and 144–152 sit on adjacent pages not yet in",
        "the local source tree.",
        "",
        f"Articles extracted: **{len(articles)}**",
        "",
        "| Article | Confidence | Body length | First 80 chars |",
        "|---------|------------|-------------|----------------|",
    ]
    for a in articles:
        head = a["text"][:80].replace("|", r"\|")
        lines.append(
            f"| {a['article']} | {a['extraction_confidence']} | {len(a['text'])} B | {head}… |"
        )
    EXTRACT_DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {EXTRACT_DOC.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
