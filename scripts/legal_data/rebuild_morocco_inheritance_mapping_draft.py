"""F-morocco-moudawana-real-pdf-remap-pass2 — one-shot rebuilder.

Read the freshly-extracted Moudawana articles JSON and emit a
mapping draft anchored on the real PDF's sha256, with every rule
carrying an ``extracted_text_snippet`` lifted verbatim from the
extraction artefact.

This script is committed for traceability but is one-shot in
intent: re-running it overwrites the JSON, which is the desired
behaviour when the extraction artefact changes (new PDF revision,
new article numbering, etc.).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXTRACTION = REPO / "legal_data/sources/morocco/extracted/moudawana_inheritance_articles.json"
MAPPING = REPO / "legal_data/mappings/morocco_inheritance_mapping_draft.json"

EXPECTED_SHA = "41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96"


def _snippet(articles: dict, article_no: str, max_len: int = 220) -> str:
    a = articles.get(article_no)
    if not a:
        return ""
    text = a["text"]
    return text[:max_len].rstrip() + ("…" if len(text) > max_len else "")


def main() -> int:
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    if extraction["source_sha256"] != EXPECTED_SHA:
        print(
            f"[error] extraction sha256 mismatch: got "
            f"{extraction['source_sha256']!r}, expected {EXPECTED_SHA!r}",
            file=sys.stderr,
        )
        return 1
    if extraction.get("extractor") != "pdfplumber":
        print(
            f"[error] extractor={extraction.get('extractor')!r}; "
            f"only 'pdfplumber' against the real PDF is accepted",
            file=sys.stderr,
        )
        return 1
    articles = {a["article"]: a for a in extraction["articles"]}
    if not articles:
        print("[error] no articles extracted from the real PDF", file=sys.stderr)
        return 1

    mapping = {
        "schema_version": "1.0",
        "iter": "F-morocco-moudawana-real-pdf-remap-pass2",
        "country": "MA",
        "case_type": "international_inheritance",
        "source_slug": "ma-code-famille-moudawana-fr-pdf",
        "source_canonical_reference": (
            "Loi n. 70-03 portant Code de la famille (Moudawana) — "
            "Livre VI : De la succession (articles 321-395)"
        ),
        "source_sha256": EXPECTED_SHA,
        "source_size_bytes": extraction["size_bytes"],
        "extraction_basis": "official_pdf",
        "status": "draft",
        "activation_allowed": False,
        "needs_manual_review": True,
        "extraction_provenance": {
            "extraction_artifact": str(EXTRACTION.relative_to(REPO)).replace("\\", "/"),
            "extracted_articles_count": len(extraction["articles"]),
            "extractor": extraction["extractor"],
            "generated_at": extraction["generated_at"],
            "previous_pass_used_synthetic_stub": False,
            "previous_pass_replaced_by_iter": ("F-morocco-moudawana-real-pdf-remap-pass2"),
        },
        "rules": [
            {
                "rule_id": "ma-inh-husband-without-descendants",
                "article_references": ["342"],
                "scenario": {"husband": 1, "sons": 0, "daughters": 0},
                "share_spec": {"husband": "1/2"},
                "extracted_text_snippet": _snippet(articles, "342"),
                "confidence": "medium",
                "needs_manual_review": True,
                "comment": (
                    "Article 342 (1): l'epoux a droit a 1/2 si l'epouse n'a "
                    "laisse aucune descendance a vocation successorale "
                    "(masculine ou feminine). Confidence=medium because the "
                    "article also lists 1/2 cases for unique daughter / "
                    "single sister; this rule isolates the husband-only case."
                ),
            },
            {
                "rule_id": "ma-inh-husband-with-descendants",
                "article_references": ["343"],
                "scenario": {"husband": 1, "sons": ">=1", "daughters": ">=0"},
                "share_spec": {"husband": "1/4"},
                "extracted_text_snippet": _snippet(articles, "343"),
                "confidence": "medium",
                "needs_manual_review": True,
                "comment": (
                    "Article 343 (1): l'epoux concourant avec une descendance "
                    "de l'epouse a vocation successorale prend 1/4."
                ),
            },
            {
                "rule_id": "ma-inh-wife-without-descendants",
                "article_references": ["343"],
                "scenario": {"wife": 1, "sons": 0, "daughters": 0},
                "share_spec": {"wife": "1/4"},
                "extracted_text_snippet": _snippet(articles, "343"),
                "confidence": "medium",
                "needs_manual_review": True,
                "comment": (
                    "Article 343 (2): l'epouse en l'absence de descendance "
                    "de l'epoux a vocation successorale prend 1/4."
                ),
            },
            {
                "rule_id": "ma-inh-wife-with-descendants",
                "article_references": ["344"],
                "scenario": {"wife": 1, "sons": ">=1", "daughters": ">=0"},
                "share_spec": {"wife": "1/8"},
                "extracted_text_snippet": _snippet(articles, "344"),
                "confidence": "high",
                "needs_manual_review": True,
                "comment": (
                    "Article 344: l'epouse prend 1/8 lorsque l'epoux laisse "
                    "une descendance a vocation successorale. Article text "
                    "is unambiguous."
                ),
            },
            {
                "rule_id": "ma-inh-multiple-daughters-no-sons",
                "article_references": ["345"],
                "scenario": {"sons": 0, "daughters": ">=2"},
                "share_spec": {"daughters_group": "2/3"},
                "extracted_text_snippet": _snippet(articles, "345"),
                "confidence": "high",
                "needs_manual_review": True,
                "comment": (
                    "Article 345 (1): deux filles ou plus du de cujus, en "
                    "l'absence de fils, partagent collectivement 2/3."
                ),
            },
            {
                "rule_id": "ma-inh-mother-no-descendants-no-multi-siblings",
                "article_references": ["346"],
                "scenario": {"mother": 1, "sons": 0, "daughters": 0},
                "share_spec": {"mother": "1/3"},
                "extracted_text_snippet": _snippet(articles, "346"),
                "confidence": "medium",
                "needs_manual_review": True,
                "comment": (
                    "Article 346 (1): la mere prend 1/3 si le de cujus ne "
                    "laisse pas de descendants a vocation successorale ni "
                    "deux ou plus de freres et soeurs (meme evinces par "
                    "hajb). The wizard does not yet capture sibling counts; "
                    "this rule cannot be activated until it does."
                ),
            },
            {
                "rule_id": "ma-inh-father-with-descendants",
                "article_references": ["347"],
                "scenario": {"father": 1, "sons": ">=1", "daughters": ">=0"},
                "share_spec": {"father": "1/6"},
                "extracted_text_snippet": _snippet(articles, "347"),
                "confidence": "high",
                "needs_manual_review": True,
                "comment": (
                    "Article 347 (1): le pere en presence d'enfant ou "
                    "d'enfant de fils du de cujus (homme ou femme) prend 1/6."
                ),
            },
            {
                "rule_id": "ma-inh-mother-with-descendants",
                "article_references": ["347"],
                "scenario": {"mother": 1, "sons": ">=1", "daughters": ">=0"},
                "share_spec": {"mother": "1/6"},
                "extracted_text_snippet": _snippet(articles, "347"),
                "confidence": "high",
                "needs_manual_review": True,
                "comment": (
                    "Article 347 (2): la mere en presence d'enfant ou "
                    "d'enfant de fils du de cujus prend 1/6."
                ),
            },
        ],
        "fixture_compatibility": {
            "engine": "morocco_inheritance_v1",
            "amount_rule": "morocco_inheritance_fixed_share_direct",
            "smoke_scenario": {
                "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
                "estate_value": "800000",
                "expected_breakdown": {
                    "spouse_amount_eur": "100000",
                    "sons_group_amount_eur_approx": "466666.67",
                    "daughters_group_amount_eur_approx": "233333.33",
                },
                "anchor_rule_id": "ma-inh-wife-with-descendants",
                "anchor_article": "344",
            },
            "fixture_only": True,
            "public_db_activation": False,
        },
        "non_modelled_concepts": [
            "hajb (exclusion by closer-degree heir) — see articles 332-335",
            "'awl (proportional reduction when shares exceed unity) — article 364",
            "radd (devolution of residue) — articles 374-378",
            "ta'sib / asaba ordering across degrees — articles 339, 348-356",
            "kalala (siblings inheritance specifics) — articles 348, 351",
            "EU 650/2012 applicable-law decision (skeleton iter, separate)",
        ],
        "blockers_before_activation": [
            (
                "every rule's confidence must be re-checked by a Studio "
                "reviewer reading the extracted_text_snippet alongside the "
                "full article in the source PDF"
            ),
            (
                "hajb / 'awl / radd / asaba ordering must be modelled before "
                "the engine output can claim completeness"
            ),
            (
                "the wizard must capture sibling counts before mother-1/3 "
                "(article 346) can be activated"
            ),
            (
                "EU 650/2012 applicable-law decision must be wired before "
                "the public funnel can output a Moroccan-law allocation for "
                "cross-border cases"
            ),
        ],
    }

    # Programmatic invariants enforced at write time.
    extracted_articles_set = {a["article"] for a in extraction["articles"]}
    for rule in mapping["rules"]:
        refs = set(rule["article_references"])
        if not refs & extracted_articles_set:
            print(
                f"[error] rule {rule['rule_id']} references articles " f"not in extraction: {refs}",
                file=sys.stderr,
            )
            return 1
        if not rule["extracted_text_snippet"].strip():
            print(
                f"[error] rule {rule['rule_id']} has empty snippet",
                file=sys.stderr,
            )
            return 1

    MAPPING.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] wrote {MAPPING.relative_to(REPO)}")
    print(f"     rules: {len(mapping['rules'])}")
    print(f"     source_sha256: {EXPECTED_SHA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
