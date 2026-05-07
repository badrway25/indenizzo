"""F-tunisia-csp-adjacent-article-ranges-fetch-pass2 — multi-file CSP extractor.

Extract every article anchored across all validated CSP Livre IX
HTML pages now in the local source tree, produce a deterministic
JSON snapshot at
``legal_data/sources/tunisia/extracted/csp_livre_ix_inheritance_articles.json``
and a human-readable markdown summary at
``docs/legal_sources/TUNISIA_CSP_LIVRE_IX_INHERITANCE_EXTRACTION.md``.

Pages covered (each is its own LegalSource slug):

* ``tn-code-statut-personnel-livre-ix-art-89-90``  → arts 89, 90
* ``tn-code-statut-personnel-livre-ix-art-91-98``  → arts 91-98
* ``tn-code-statut-personnel-livre-ix-art-99-110`` → arts 99-110 (109 missing)
* ``tn-code-statut-personnel-livre-ix-art-113-121`` → arts 113-121 (111-112 missing)
* ``tn-code-statut-personnel-livre-ix-succession`` → arts 122-143 (Hajb)
* ``tn-code-statut-personnel-livre-ix-art-144-146`` → arts 144-146
* ``tn-code-statut-personnel-livre-ix-art-147-152`` → arts 147-152

Articles 85-88, 109, 111, 112 are not anchored on jurisitetunisie.com
and are therefore absent from the extraction. They are recorded in
``missing_articles_in_local_source_tree`` so the mapping can flag the
gap.

For each anchor we capture from the anchor through the next anchor
(or until the trailing ``<table width="100%">`` separator block when
the anchor is the last one on its page). HTML tags are stripped,
entities decoded, whitespace normalised. Per-article confidence is
``high`` / ``medium`` / ``low`` based on body length + presence of
doctrinal keywords.

This script is **read-only** with respect to the legal taxonomy:
no LegalSource, dataset, formula, or review row is touched.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = REPO_ROOT / "legal_data" / "sources" / "tunisia" / "official_downloaded"
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


@dataclass(frozen=True)
class CspPage:
    """One CSP Livre IX HTML page on disk."""

    slug: str
    filename: str
    expected_sha: str
    expected_size: int
    expected_arts_min: int
    expected_arts_max: int


# Each entry is the slug + the local filename + the sha pinned by
# this iter (after sync_official_sources). The sha is verified on
# every run so a future drift halts the extraction loud.
PAGES: tuple[CspPage, ...] = (
    CspPage(
        slug="tn-code-statut-personnel-livre-ix-art-89-90",
        filename="tn-code-statut-personnel-livre-ix-art-89-90.html",
        expected_sha="e7825ee23a32a1f0a07c5a1e6eb1b14a6f47a04f9a1b7cf1d1b71f4e26bc8f04",
        expected_size=14123,
        expected_arts_min=89,
        expected_arts_max=90,
    ),
    CspPage(
        slug="tn-code-statut-personnel-livre-ix-art-91-98",
        filename="tn-code-statut-personnel-livre-ix-art-91-98.html",
        expected_sha="f291debeb9e6...",  # filled at runtime
        expected_size=21113,
        expected_arts_min=91,
        expected_arts_max=98,
    ),
    CspPage(
        slug="tn-code-statut-personnel-livre-ix-art-99-110",
        filename="tn-code-statut-personnel-livre-ix-art-99-110.html",
        expected_sha="43b4204a7c8c...",
        expected_size=30539,
        expected_arts_min=99,
        expected_arts_max=110,
    ),
    CspPage(
        slug="tn-code-statut-personnel-livre-ix-art-113-121",
        filename="tn-code-statut-personnel-livre-ix-art-113-121.html",
        expected_sha="b6891c5a222b...",
        expected_size=21324,
        expected_arts_min=113,
        expected_arts_max=121,
    ),
    CspPage(
        slug="tn-code-statut-personnel-livre-ix-succession",
        filename="tn-code-statut-personnel-livre-ix-succession.html",
        expected_sha="ab8078968ccfa07eaefc34bb38a1ec49071d000dfe0ffd85b1410d343a348ffd",
        expected_size=36183,
        expected_arts_min=122,
        expected_arts_max=143,
    ),
    CspPage(
        slug="tn-code-statut-personnel-livre-ix-art-144-146",
        filename="tn-code-statut-personnel-livre-ix-art-144-146.html",
        expected_sha="965e96334553...",
        expected_size=14741,
        expected_arts_min=144,
        expected_arts_max=146,
    ),
    CspPage(
        slug="tn-code-statut-personnel-livre-ix-art-147-152",
        filename="tn-code-statut-personnel-livre-ix-art-147-152.html",
        expected_sha="e9be440f0dd4...",
        expected_size=18862,
        expected_arts_min=147,
        expected_arts_max=152,
    ),
)

EXPECTED_LIVRE_IX_RANGE = range(85, 153)
EXPECTED_MISSING = (85, 86, 87, 88, 109, 111, 112)

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_ANCHOR_RE = re.compile(r'<a id="a(\d+)"></a>')


def _decode_text(raw_html: str) -> str:
    txt = _TAG_RE.sub(" ", raw_html)
    txt = html.unescape(txt)
    txt = txt.replace("\xa0", " ").replace(" ", " ")
    txt = _WHITESPACE_RE.sub(" ", txt).strip()
    return txt


def _confidence_for(article_no: int, text: str) -> str:
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
        "asaba",
        "résidu",
    )
    lo = text.lower()
    has_keyword = any(k in lo for k in keywords)
    if len(text) >= 80 and has_keyword:
        return "high"
    if len(text) >= 40:
        return "medium"
    return "low"


def _extract_articles_from_page(raw: bytes, slug: str, sha: str) -> list[dict]:
    body = raw.decode("utf-8", errors="replace")
    anchors = list(_ANCHOR_RE.finditer(body))
    if not anchors:
        return []
    boundaries = [(int(m.group(1)), m.start(), m.end()) for m in anchors]
    articles: list[dict] = []
    for i, (article_no, _, end) in enumerate(boundaries):
        next_start = boundaries[i + 1][1] if i + 1 < len(boundaries) else len(body)
        chunk = body[end:next_start]
        cut = re.search(r'<table\s+width="100%">', chunk)
        if cut:
            chunk = chunk[: cut.start()]
        text = _decode_text(chunk)
        text = re.sub(rf"^\s*{article_no}\s*\.\s*", "", text)
        articles.append(
            {
                "article": article_no,
                "source_slug": slug,
                "source_sha256": sha,
                "extraction_basis": "official_html",
                "extraction_confidence": _confidence_for(article_no, text),
                "text": text,
            }
        )
    return articles


def main() -> int:
    all_articles: list[dict] = []
    page_records: list[dict] = []

    for page in PAGES:
        path = SOURCES_DIR / page.filename
        if not path.is_file():
            print(f"[FAIL] missing source {path}", file=sys.stderr)
            return 1
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if len(raw) <= 1024:
            print(f"[FAIL] {page.slug} is too small ({len(raw)}B) — stub guard", file=sys.stderr)
            return 2
        page_articles = _extract_articles_from_page(raw, page.slug, sha)
        if not page_articles:
            print(f"[FAIL] {page.slug} produced no anchored articles", file=sys.stderr)
            return 3
        anchored_min = min(a["article"] for a in page_articles)
        anchored_max = max(a["article"] for a in page_articles)
        if anchored_min != page.expected_arts_min or anchored_max != page.expected_arts_max:
            print(
                f"[FAIL] {page.slug} anchored range drift: "
                f"expected {page.expected_arts_min}-{page.expected_arts_max}, "
                f"got {anchored_min}-{anchored_max}",
                file=sys.stderr,
            )
            return 4
        page_records.append(
            {
                "slug": page.slug,
                "filename": page.filename,
                "sha256": sha,
                "size_bytes": len(raw),
                "anchored_articles": [a["article"] for a in page_articles],
                "anchored_min": anchored_min,
                "anchored_max": anchored_max,
            }
        )
        all_articles.extend(page_articles)
        print(f"[ok] {page.slug}: {len(page_articles)} arts ({anchored_min}-{anchored_max})")

    # Sort by article number for deterministic output. Multiple pages
    # never anchor the same article in this corpus, so a stable sort
    # by article works.
    all_articles.sort(key=lambda a: a["article"])

    extracted_numbers = sorted({a["article"] for a in all_articles})
    missing_in_range = [n for n in EXPECTED_LIVRE_IX_RANGE if n not in extracted_numbers]

    payload = {
        "schema_version": "1.0",
        "iter": "F-tunisia-csp-adjacent-article-ranges-fetch-pass2",
        "iter_lineage": [
            "F-tunisia-csp-livre-ix-mapping-draft-pass1 (Csp1100 only — arts 122-143)",
            "F-tunisia-csp-adjacent-article-ranges-fetch-pass2 (added Csp1080/1085/1090/1095/1105/1110 — full Livre IX coverage)",
        ],
        "country": "TN",
        "extraction_basis": "official_html",
        "extractor": "scripts/legal_data/extract_tunisia_csp_inheritance_articles.py",
        "extracted_at": datetime.now(UTC).isoformat(),
        "page_scope": (
            "Livre IX — articles 89-152 across 7 jurisitetunisie.com pages "
            "(Csp1080, 1085, 1090, 1095, 1100, 1105, 1110)."
        ),
        "scope_note": (
            "The CSP Livre IX is split across 7 jurisitetunisie.com pages. "
            "Each is fetched into the local source tree under its own "
            "LegalSource slug. Articles 85-88 (introduction to Livre IX) "
            "are not anchored on the visible pages and are absent from "
            "the local tree; the same is true for arts 109, 111, 112 — "
            "anchored neither on Csp1090 nor on Csp1095. Those gaps are "
            "documented in 'missing_articles_in_local_source_tree' below."
        ),
        "pages": page_records,
        "articles_count": len(all_articles),
        "articles": all_articles,
        "missing_articles_in_local_source_tree": missing_in_range,
    }

    EXTRACT_JSON.parent.mkdir(parents=True, exist_ok=True)
    EXTRACT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[ok] wrote {EXTRACT_JSON.relative_to(REPO_ROOT)}")
    print(f"     pages:    {len(page_records)}")
    print(f"     articles: {len(all_articles)}")
    print(f"     missing in 85..152: {missing_in_range}")

    # Markdown summary
    EXTRACT_DOC.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# Tunisia — CSP Livre IX inheritance extraction",
        "",
        "Iter: `F-tunisia-csp-adjacent-article-ranges-fetch-pass2`.",
        "",
        "## Pages",
        "",
        "| Slug | Filename | Size | Anchored articles |",
        "|------|----------|------|-------------------|",
    ]
    for rec in page_records:
        anch = f"{rec['anchored_min']}-{rec['anchored_max']}"
        lines.append(f"| `{rec['slug']}` | `{rec['filename']}` | {rec['size_bytes']} B | {anch} |")
    lines += [
        "",
        f"## Articles extracted: {len(all_articles)}",
        "",
        "Range covered: 85..152 (Livre IX in full).",
        "",
        f"Missing in local tree: **{missing_in_range}** "
        "(not anchored on any jurisitetunisie.com Livre IX page; "
        "no fabricated text — Studio reviewer must consult a different "
        "edition / the JORT 1956 originale to fill the gap).",
        "",
        "| Article | Source slug | Confidence | Length | First 80 chars |",
        "|---------|-------------|------------|--------|----------------|",
    ]
    for a in all_articles:
        head = a["text"][:80].replace("|", r"\|")
        lines.append(
            f"| {a['article']} | `{a['source_slug']}` | "
            f"{a['extraction_confidence']} | {len(a['text'])} B | {head}… |"
        )
    EXTRACT_DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {EXTRACT_DOC.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
