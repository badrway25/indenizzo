"""F-morocco-moudawana-real-pdf-remap-pass2 — one-shot rebuilder.

Iter origin: F-morocco-moudawana-real-pdf-remap-pass2.
Refined in: F-morocco-moudawana-mapping-refinement-pass3 (split
article 346 mother case, add ``unsupported_mechanisms`` section,
add ``activation_blockers`` per rule).

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
        "iter": "F-morocco-moudawana-mapping-refinement-pass3",
        "iter_lineage": [
            "F-morocco-moudawana-livre-iii-mapping-draft-pass1 (placeholder PDF — superseded)",
            "F-morocco-moudawana-real-pdf-remap-pass2 (real PDF, 8 rules)",
            "F-morocco-moudawana-mapping-refinement-pass3 (split 346, unsupported_mechanisms, activation_blockers)",
        ],
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
                "activation_blockers": [
                    "article 342 lists four other 1/2 cases (single daughter, single granddaughter, single full sister, single consanguine sister) — this rule isolates only the husband case",
                ],
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
                "activation_blockers": [],
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
                "activation_blockers": [],
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
                "activation_blockers": [],
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
                "activation_blockers": [],
                "comment": (
                    "Article 345 (1): deux filles ou plus du de cujus, en "
                    "l'absence de fils, partagent collectivement 2/3."
                ),
            },
            {
                "rule_id": "ma-inh-mother-no-descendants-no-multi-siblings",
                "article_references": ["346"],
                "scenario": {
                    "mother": 1,
                    "sons": 0,
                    "daughters": 0,
                    "siblings": "<=1",
                },
                "share_spec": {"mother": "1/3"},
                "extracted_text_snippet": _snippet(articles, "346"),
                "confidence": "medium",
                "needs_manual_review": True,
                "activation_blockers": [
                    "wizard already captures siblings_count → input_data.heirs.siblings",
                    "engine must read heirs.siblings to gate this rule",
                    "Studio review must confirm the precise threshold (the article uses 'deux ou plus' = >=2)",
                ],
                "comment": (
                    "Article 346 (1): la mere prend 1/3 si le de cujus ne "
                    "laisse pas de descendants a vocation successorale ni "
                    "deux ou plus de freres et soeurs (meme evinces par "
                    "hajb). The wizard already captures siblings_count via "
                    "the inheritance form; the engine still needs to gate "
                    "this rule on heirs.siblings <= 1 before activation."
                ),
            },
            {
                "rule_id": "ma-inh-mother-no-descendants-multi-siblings-blocked",
                "article_references": ["346", "347"],
                "scenario": {
                    "mother": 1,
                    "sons": 0,
                    "daughters": 0,
                    "siblings": ">=2",
                },
                "share_spec": None,
                "extracted_text_snippet": _snippet(articles, "346"),
                "confidence": "medium",
                "needs_manual_review": True,
                "activation_blockers": [
                    "rule is BLOCKED: when 2+ siblings exist without descendants, the mother's share is reduced (classical 'hajb noqsan' = reduction by exclusion). The exact reduced fraction depends on doctrinal interpretation of articles 346-347 + the asaba/Ta'sib mechanics in articles 348-356. This pass refuses to assign a numeric share until a Studio reviewer signs off.",
                    "blocked_by_unsupported_mechanism: hajb_noqsan",
                ],
                "blocked": True,
                "comment": (
                    "Companion to ma-inh-mother-no-descendants-no-multi-"
                    "siblings: when the de cujus leaves no descendants but "
                    "two or more siblings (even when those siblings are "
                    "themselves excluded by hajb), article 346 explicitly "
                    "carves out the 1/3 mother case. The reduced share "
                    "owed to the mother in that scenario is doctrinal "
                    "(hajb noqsan) and outside this draft's scope."
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
                "activation_blockers": [
                    "father's residual asaba claim on the remainder (when only female descendants exist) is NOT modelled here — articles 348-356",
                ],
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
                "activation_blockers": [],
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
        "wizard_inputs": {
            "captured": [
                {
                    "form_field": "spouse_present",
                    "input_data_path": "heirs.spouse",
                    "type": "boolean (0|1)",
                },
                {
                    "form_field": "sons_count",
                    "input_data_path": "heirs.sons",
                    "type": "integer (0..30)",
                },
                {
                    "form_field": "daughters_count",
                    "input_data_path": "heirs.daughters",
                    "type": "integer (0..30)",
                },
                {
                    "form_field": "father_present",
                    "input_data_path": "heirs.father",
                    "type": "boolean (0|1)",
                },
                {
                    "form_field": "mother_present",
                    "input_data_path": "heirs.mother",
                    "type": "boolean (0|1)",
                },
                {
                    "form_field": "siblings_count",
                    "input_data_path": "heirs.siblings",
                    "type": "integer (0..30)",
                },
            ],
            "missing_for_full_faraid": [
                "husband_vs_wife distinction (current 'spouse_present' boolean is gender-neutral; mapping rules use husband/wife separately for articles 342-344)",
                "sibling sub-typing (full / consanguine / uterine) — articles 348-351",
                "grandchildren (son's daughters, son's sons) — article 345 (2)",
                "agnatic ascendants (paternal grandfather, paternal grandmother) — article 339",
            ],
        },
        "unsupported_mechanisms": [
            {
                "name": "hajb",
                "label_en": "Exclusion of an heir by a closer-degree heir",
                "article_references": ["332", "333", "334", "335"],
                "blocked_rules": ["ma-inh-mother-no-descendants-multi-siblings-blocked"],
                "comment": "Two flavours: hajb hirman (total exclusion) and hajb noqsan (partial reduction). The mother-with-multi-siblings rule depends on hajb noqsan.",
            },
            {
                "name": "'awl",
                "label_en": "Proportional reduction when fixed shares exceed unity",
                "article_references": ["364"],
                "blocked_rules": [],
                "comment": "Required whenever the sum of Fardh shares > 1 (e.g. husband 1/2 + 2 sisters 2/3 = 7/6). The current engine has no awl pass.",
            },
            {
                "name": "radd",
                "label_en": "Devolution of the residue when no asaba is present",
                "article_references": ["374", "375", "376", "377", "378"],
                "blocked_rules": [],
                "comment": "Without an asaba heir, the residue is redistributed pro rata among the Fardh heirs (excluding the spouse).",
            },
            {
                "name": "ta'sib / asaba ordering",
                "label_en": "Residuary heir ordering across degrees",
                "article_references": [
                    "339",
                    "348",
                    "349",
                    "350",
                    "351",
                    "352",
                    "353",
                    "354",
                    "355",
                    "356",
                ],
                "blocked_rules": [],
                "comment": "The current engine uses a sons:daughters 2:1 fixed-residue rule that is correct only for the simple parental-line case. Full asaba ordering involves agnatic/cognatic relatives across multiple degrees.",
            },
            {
                "name": "kalala",
                "label_en": "Siblings-only inheritance (no descendants, no ascendants)",
                "article_references": ["348", "351"],
                "blocked_rules": [],
                "comment": "Distinct doctrinal regime when the de cujus leaves only siblings.",
            },
            {
                "name": "applicable_law_decision",
                "label_en": "EU 650/2012 applicable-law selection",
                "article_references": [],
                "blocked_rules": [],
                "comment": "Whether Moroccan substantive law applies in a cross-border case is decided by Reg. 650/2012; tracked separately by the applicable-law skeleton engine.",
            },
        ],
        "blockers_before_activation": [
            "every rule's confidence must be re-checked by a Studio reviewer reading the extracted_text_snippet alongside the full article in the source PDF",
            "the engine must read heirs.siblings (already captured by the wizard) and gate ma-inh-mother-no-descendants-no-multi-siblings on siblings <= 1 before activation",
            "the engine must distinguish husband vs wife (currently both fold into 'spouse'); rules ma-inh-husband-* and ma-inh-wife-* are intentionally redundant on the spouse axis until that split lands",
            "every entry in unsupported_mechanisms must either be modelled or have an explicit blocked_rules list of cases the engine refuses to compute",
            "EU 650/2012 applicable-law decision must be wired before the public funnel can output a Moroccan-law allocation for cross-border cases",
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
