"""F-morocco-moudawana-livre-iii-mapping-draft-pass1.

Read the official, approved Moudawana PDF and extract every section
that looks like a succession / héritage / héritiers / parts article.

Source of truth (and the ONLY input this script accepts):
``legal_data/sources/morocco/official_downloaded/ma-code-famille-moudawana-fr-pdf.pdf``.

Outputs:

- ``legal_data/sources/morocco/extracted/moudawana_inheritance_articles.json``
- ``docs/legal_sources/MOROCCO_MOUDAWANA_INHERITANCE_EXTRACTION.md``

The JSON entries follow the shape::

    {
      "article": "321",
      "title": "Des successions",
      "text": "<verbatim excerpt>",
      "source_sha256": "...",
      "page_start": 12,
      "page_end": 13,
      "extraction_confidence": "high|medium|low"
    }

If the local PDF is too small / a stub / unreadable, the JSON still
records the input invariants (path, sha256, byte size) but the
``articles`` array is empty and ``extraction_blocked_reason`` is
populated. No automatic rule mapping is performed — that is the job
of the companion ``legal_data/mappings/morocco_inheritance_mapping_draft.json``
file, which a human author curates from this extraction (or, when
the local PDF is a stub, from the canonical published Moudawana
text plus a future re-fetch).

Read-only on the DB. The script never writes to ``LegalSource`` /
``CompensationDataset`` / ``CalculationFormula`` /
``CompensationTableRow``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
from datetime import UTC, datetime

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


PDF_PATH_DEFAULT = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "morocco"
    / "official_downloaded"
    / "ma-code-famille-moudawana-fr-pdf.pdf"
)
JSON_OUT_DEFAULT = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "morocco"
    / "extracted"
    / "moudawana_inheritance_articles.json"
)
MD_OUT_DEFAULT = (
    REPO_ROOT / "docs" / "legal_sources" / "MOROCCO_MOUDAWANA_INHERITANCE_EXTRACTION.md"
)

# Section anchors that mark the inheritance volume of the Moudawana.
INHERITANCE_HEADER_RE = re.compile(
    r"(?i)\b(succession|h[ée]ritage|h[ée]ritiers|parts? successorales?)\b"
)
ARTICLE_RE = re.compile(r"(?im)^\s*Article\s+(\d+)[\s.\-:]*(.*)$")

# Minimum PDF byte size below which we assume the file is a stub /
# placeholder and skip pdfplumber entirely. Real Moudawana
# distributions are megabyte-scale; a few hundred bytes is a
# fixture, not a document.
MIN_REAL_PDF_BYTES = 50_000


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _try_extract_text(path: pathlib.Path) -> tuple[str, str]:
    """Return ``(full_text, extractor)``. ``extractor`` is one of
    ``pdfplumber``, ``raw_bytes``, ``stub``."""
    if path.stat().st_size < MIN_REAL_PDF_BYTES:
        # Very small PDFs in this repo are synthetic test stubs. We
        # do not attempt OCR — the iter doc explains the path.
        return ("", "stub")
    try:
        import pdfplumber  # noqa: F401
    except Exception:
        # pdfplumber not available — fall back to raw bytes scan.
        try:
            return (path.read_bytes().decode("utf-8", errors="replace"), "raw_bytes")
        except Exception:
            return ("", "stub")
    import pdfplumber

    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = []
            for p in pdf.pages:
                pages.append(p.extract_text() or "")
            return ("\n\n".join(pages), "pdfplumber")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] pdfplumber failed: {exc}", file=sys.stderr)
        return ("", "stub")


def _extract_articles(text: str) -> list[dict]:
    if not text.strip():
        return []
    # Split on Article boundaries; keep the article number + its
    # body until the next Article anchor.
    matches = list(ARTICLE_RE.finditer(text))
    out: list[dict] = []
    for i, m in enumerate(matches):
        article_no = m.group(1)
        title_tail = (m.group(2) or "").strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        # Confine the snippet to the first ~280 chars to keep the
        # JSON small; humans can re-extract from the source.
        snippet = (title_tail + "\n" + body).strip()
        snippet_short = snippet[:280] + ("…" if len(snippet) > 280 else "")
        if not INHERITANCE_HEADER_RE.search(snippet):
            # Skip non-inheritance articles at this stage. The
            # mapping draft can refer to extra slugs by article number
            # if a future iter expands scope.
            continue
        out.append(
            {
                "article": article_no,
                "title": title_tail or "",
                "text": snippet_short,
                "extraction_confidence": (
                    "high" if len(body) > 200 else ("medium" if len(body) > 60 else "low")
                ),
            }
        )
    return out


def _render_md(report: dict) -> str:
    lines = [
        "# Moudawana — extraction des articles de succession (pass 1)",
        "",
        "Iter: F-morocco-moudawana-livre-iii-mapping-draft-pass1.",
        "",
        f"- source PDF: `{report['pdf_path']}`",
        f"- sha256: `{report['source_sha256']}`",
        f"- size: `{report['size_bytes']}` bytes",
        f"- extractor: `{report['extractor']}`",
        f"- generated_at: `{report['generated_at']}`",
        f"- articles extracted: `{len(report['articles'])}`",
    ]
    if report.get("extraction_blocked_reason"):
        lines.extend(
            [
                "",
                f"**Extraction blocked:** {report['extraction_blocked_reason']}",
                "",
                "The dev environment ships a synthetic fixture in place of the "
                "real Moudawana PDF. The extraction returned an empty article "
                "list. The mapping draft JSON beside it lists the canonical "
                "Moudawana inheritance article numbers anchored on this same "
                "approved source slug and tags every rule with "
                "`needs_manual_review=true`. Production deployment must "
                "replace the synthetic fixture with the real document and "
                "re-run this script before the mapping draft can advance.",
            ]
        )
    if report["articles"]:
        lines.extend(
            [
                "",
                "## Articles extracted",
                "",
                "| Article | Title | Confidence |",
                "| --- | --- | :-: |",
            ]
        )
        for art in report["articles"]:
            title = (art.get("title") or "").replace("|", "\\|")[:80]
            lines.append(
                f"| `{art['article']}` | {title} | " f"{art.get('extraction_confidence', 'low')} |"
            )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", default=str(PDF_PATH_DEFAULT))
    parser.add_argument("--json-out", default=str(JSON_OUT_DEFAULT))
    parser.add_argument("--md-out", default=str(MD_OUT_DEFAULT))
    parser.add_argument(
        "--require-source-slug",
        default="ma-code-famille-moudawana-fr-pdf",
        help=(
            "If set, require the LegalSource with this slug to exist, be "
            "APPROVED, and reference a [official_source_validation] block "
            "with validation_status=passed before running the extraction."
        ),
    )
    args = parser.parse_args()

    pdf_path = pathlib.Path(args.pdf)
    if not pdf_path.is_absolute():
        pdf_path = (REPO_ROOT / pdf_path).resolve()

    if not pdf_path.is_file():
        print(f"[error] PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    sha = _sha256(pdf_path)
    size = pdf_path.stat().st_size

    if args.require_source_slug:
        sys.path.insert(0, str(REPO_ROOT))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        import django

        django.setup()

        from apps.legal_sources.enums import SourceStatus
        from apps.legal_sources.models import LegalSource

        try:
            src = LegalSource.objects.get(slug=args.require_source_slug)
        except LegalSource.DoesNotExist:
            print(
                f"[error] required LegalSource missing: {args.require_source_slug!r}",
                file=sys.stderr,
            )
            return 1
        if src.status != SourceStatus.APPROVED:
            print(
                f"[error] LegalSource {args.require_source_slug!r} is not "
                f"APPROVED (status={src.status!r}); refusing to extract",
                file=sys.stderr,
            )
            return 1
        if "[official_source_validation] BEGIN" not in (src.notes or ""):
            print(
                f"[error] LegalSource {args.require_source_slug!r} carries no "
                f"[official_source_validation] block; refusing to extract",
                file=sys.stderr,
            )
            return 1

    text, extractor = _try_extract_text(pdf_path)
    articles = _extract_articles(text)

    blocked_reason = ""
    if extractor == "stub":
        blocked_reason = (
            f"local PDF is too small ({size} bytes) — looks like a synthetic "
            "fixture, not the real Moudawana document"
        )
    elif extractor == "raw_bytes":
        blocked_reason = (
            "pdfplumber is not installed; raw-byte fallback is unlikely to "
            "produce useful text on a real PDF"
        )

    report = {
        "schema_version": "1.0",
        "iter": "F-morocco-moudawana-livre-iii-mapping-draft-pass1",
        "generated_at": datetime.now(UTC).isoformat(),
        "pdf_path": str(pdf_path.relative_to(REPO_ROOT)),
        "source_sha256": sha,
        "size_bytes": size,
        "extractor": extractor,
        "extraction_blocked_reason": blocked_reason,
        "articles": [
            {**a, "source_sha256": sha, "page_start": None, "page_end": None} for a in articles
        ],
    }

    json_path = pathlib.Path(args.json_out)
    if not json_path.is_absolute():
        json_path = (REPO_ROOT / json_path).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = pathlib.Path(args.md_out)
    if not md_path.is_absolute():
        md_path = (REPO_ROOT / md_path).resolve()
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_render_md(report), encoding="utf-8")

    print(f"[json] {json_path}")
    print(f"[md]   {md_path}")
    print(
        f"[summary] extractor={extractor}  articles={len(articles)}  "
        f"sha256={sha[:12]}…  size={size}"
    )
    if blocked_reason:
        print(f"[note] {blocked_reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
