"""F-tunisia-csp-adjacent-article-ranges-fetch-pass2 — mapping rebuilder.

The Tunisia inheritance mapping draft now spans the full Livre IX
(arts 89-152) extracted from 7 jurisitetunisie.com pages. Every rule
is still blocked — no ``share_spec`` is derived in this iter — but
the mapping records the load-bearing source slug per article so a
future Studio promotion iter can verify each snippet against the
right official page.

Re-run after editing this script::

    python scripts/legal_data/rebuild_tunisia_inheritance_mapping_draft.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTRACT_JSON = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "tunisia"
    / "extracted"
    / "csp_livre_ix_inheritance_articles.json"
)
OUTPUT = REPO_ROOT / "legal_data" / "mappings" / "tunisia_inheritance_mapping_draft.json"

# The single source slug recorded at the mapping header level — the
# canonical Hajb page that originally seeded the draft. The new
# pages are recorded one-by-one in ``context_sources`` and per-rule
# via ``source_slug`` on each article.
HEADER_SOURCE_SLUG = "tn-code-statut-personnel-livre-ix-succession"
HEADER_SOURCE_SHA = "ab8078968ccfa07eaefc34bb38a1ec49071d000dfe0ffd85b1410d343a348ffd"
HEADER_SOURCE_SIZE = 36183


# Articles whose anchor section is the Hajb chapter (122-143). For
# every other article in Livre IX, the rule's blocker list mentions
# that the share-spec still needs Studio derivation but does not
# tag the article as Hajb.
HAJB_ARTICLE_RANGE = range(122, 144)


def _build_rule(article: dict) -> dict:
    article_no = article["article"]
    snippet = article["text"][:280]
    is_hajb = article_no in HAJB_ARTICLE_RANGE
    blockers = [
        (
            "no share_spec has been derived: this iter pins the article text "
            "verbatim from the validated official_html source but does not "
            "compute any share — Studio review must derive the share_spec "
            "(if any) from the article and from the missing siblings rules "
            "(arts 85-88, 109, 111, 112)."
        ),
        (
            "EU 650/2012 source is currently classified blocked_fetch_failed; "
            "no cross-border rule may fire until it becomes load-bearing"
        ),
    ]
    if is_hajb:
        blockers.append(
            "the article belongs to the Hajb (éviction successorale) chapter "
            "— Hajb is an unsupported_mechanism on the engine; the rule "
            "stays blocked even after Studio derivation until the engine "
            "models eviction"
        )
    return {
        "rule_id": f"tn-csp-art-{article_no}",
        "article_references": [str(article_no)],
        "scenario": {},
        "share_spec": None,
        "blocked": True,
        "source_slug": article["source_slug"],
        "source_sha256": article["source_sha256"],
        "extracted_text_snippet": snippet,
        "extraction_confidence": article["extraction_confidence"],
        "confidence": "low",
        "needs_manual_review": True,
        "activation_blockers": blockers,
        "comment": (
            f"CSP Livre IX, article {article_no}. Text extracted from "
            f"{article['source_slug']!r} ({article['source_sha256'][:12]}…)."
        ),
    }


def _build_context_sources(extraction: dict) -> list[dict]:
    """Build the context_sources block.

    Records every per-page CSP source as ``real_verified``, the TN
    Code DIP as ``real_verified`` (non-load-bearing), and the EU
    650/2012 as ``blocked_fetch_failed`` (non-load-bearing).
    """
    contexts: list[dict] = []
    for page in extraction.get("pages", []):
        if page["slug"] == HEADER_SOURCE_SLUG:
            continue  # already named at the header level
        contexts.append(
            {
                "slug": page["slug"],
                "status": "real_verified",
                "sha256": page["sha256"],
                "size_bytes": page["size_bytes"],
                "load_bearing": True,
                "anchored_articles": page["anchored_articles"],
                "role": (
                    f"Adjacent CSP Livre IX page ({page['filename']}); "
                    f"anchors arts {page['anchored_min']}-{page['anchored_max']}. "
                    "Fetched and validated by "
                    "F-tunisia-csp-adjacent-article-ranges-fetch-pass2; "
                    "load-bearing only insofar as the rules in this mapping "
                    "cite this page's article snippets — no share_spec is "
                    "derived."
                ),
            }
        )
    contexts.append(
        {
            "slug": "tn-code-dip-loi-98-97",
            "status": "real_verified",
            "sha256": "d379a07076177f66cf0fc6ad4704b78dd8c7b79acef03954c598a5218eb8e76a",
            "size_bytes": 15424,
            "load_bearing": False,
            "role": (
                "Tunisian private international law (Code DIP, Loi 98-97). "
                "Provides Tunisian-side conflict-of-laws context for "
                "cross-border successions but is not used to derive any "
                "share. Will become load-bearing only when the engine "
                "wires a TN applicable-law decision skeleton."
            ),
        }
    )
    contexts.append(
        {
            "slug": "eu-regulation-650-2012-successions",
            "status": "blocked_fetch_failed",
            "load_bearing": False,
            "role": (
                "EU Regulation 650/2012 on cross-border successions. "
                "Currently classified as fetch_failed in "
                "legal_data/sources/eu/official_downloaded/official_sync_manifest.json "
                "(EUR-Lex returns HTTP 202 + empty body for synchronous "
                "fetches). The mapping draft refuses to use it as a "
                "load-bearing reference until a real download succeeds."
            ),
            "blocked_reason": "EUR-Lex async content-delivery; manual download required",
            "manual_unblock_path": (
                "Download "
                "https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32012R0650 "
                "into legal_data/sources/eu/official_downloaded/, then "
                "manage.py sync_official_sources --slug "
                "eu-regulation-650-2012-successions, then "
                "manage.py validate_official_legal_sources --commit "
                "--slug eu-regulation-650-2012-successions."
            ),
        }
    )
    return contexts


def main() -> int:
    extraction = json.loads(EXTRACT_JSON.read_text(encoding="utf-8"))
    rules = [_build_rule(a) for a in extraction["articles"]]
    missing_in_local_tree = extraction.get("missing_articles_in_local_source_tree", [])
    hajb_rule_ids = [
        r["rule_id"] for r in rules if int(r["article_references"][0]) in HAJB_ARTICLE_RANGE
    ]

    mapping = {
        "schema_version": "1.0",
        "iter": "F-tunisia-csp-adjacent-article-ranges-fetch-pass2",
        "iter_lineage": [
            "F-tunisia-official-source-real-files-restore-pass1 (real CSP + DIP files restored)",
            "F-tunisia-csp-livre-ix-mapping-draft-pass1 (Hajb-only blocked rules; EU 650 declared blocked context)",
            "F-tunisia-csp-adjacent-article-ranges-fetch-pass2 (added 6 adjacent CSP pages — full Livre IX coverage 89-152)",
        ],
        "country": "TN",
        "case_type": "international_inheritance",
        "source_slug": HEADER_SOURCE_SLUG,
        "source_canonical_reference": (
            "Code du statut personnel — Livre IX (De la succession), Tunisie. "
            "Articles 89-152 split across 7 jurisitetunisie.com pages "
            "(Csp1080, 1085, 1090, 1095, 1100, 1105, 1110). "
            "Loi initiale 1956, version consolidée 2024 publiée par jurisitetunisie.com."
        ),
        "source_sha256": HEADER_SOURCE_SHA,
        "source_size_bytes": HEADER_SOURCE_SIZE,
        "extraction_basis": "official_html",
        "extraction_artifact": str(EXTRACT_JSON.relative_to(REPO_ROOT)).replace("\\", "/"),
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "draft",
        "activation_allowed": False,
        "needs_manual_review": True,
        "context_sources": _build_context_sources(extraction),
        "wizard_inputs": {
            "captured": [
                {
                    "form_field": "deceased_country_of_last_residence",
                    "input_data_path": "deceased_country_of_last_residence",
                    "type": "ISO-3166 alpha-2",
                },
                {
                    "form_field": "nationality",
                    "input_data_path": "nationality",
                    "type": "ISO-3166 alpha-2",
                },
                {"form_field": "has_will", "input_data_path": "has_will", "type": "boolean | None"},
                {"form_field": "spouse_present", "input_data_path": "heirs.spouse", "type": "0|1"},
                {
                    "form_field": "surviving_spouse_gender",
                    "input_data_path": "heirs.surviving_spouse_gender",
                    "type": "'husband' | 'wife' | None",
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
                {"form_field": "father_present", "input_data_path": "heirs.father", "type": "0|1"},
                {"form_field": "mother_present", "input_data_path": "heirs.mother", "type": "0|1"},
                {
                    "form_field": "siblings_count",
                    "input_data_path": "heirs.siblings",
                    "type": "integer (0..30)",
                },
                {
                    "form_field": "estate_value",
                    "input_data_path": "estate_value",
                    "type": "decimal | None",
                },
                {
                    "form_field": "assets_countries",
                    "input_data_path": "assets_countries",
                    "type": "comma-separated ISO codes",
                },
            ],
            "missing_for_full_faraid": [
                "sibling sub-typing (full / consanguine / uterine) — needed for arts 132-139",
                "grandchildren (sons' sons, sons' daughters) — covered by arts 125-127 but no wizard field",
                "agnatic ascendants (paternal grandfather, paternal grandmother) — covered by arts 140-143 but no wizard field",
                "cousin / aunt / uncle relationships — covered by arts 134-137 but no wizard field",
            ],
            "missing_articles_in_local_source_tree": missing_in_local_tree,
        },
        "rules": rules,
        "unsupported_mechanisms": [
            {
                "name": "hajb",
                "label_en": "Eviction (total or by reduction)",
                "article_references": [str(n) for n in HAJB_ARTICLE_RANGE],
                "blocked_rules": hajb_rule_ids,
                "comment": (
                    "Articles 122-143 describe Hajb. The engine cannot apply "
                    "Hajb without the full taxonomy of heir relationships "
                    "(degrees, uterine/consanguine/germain distinction). "
                    "Every Hajb rule in this draft stays blocked even after "
                    "Studio derivation until the engine models eviction."
                ),
            },
            {
                "name": "'awl",
                "label_en": "Proportional reduction when fixed shares exceed unity",
                "article_references": [],
                "blocked_rules": [],
                "comment": (
                    "Likely covered by arts 144-152 now in the local tree, "
                    "but the engine does not model the 'awl arithmetic. The "
                    "Studio reviewer must read the relevant articles and "
                    "decide whether to expose 'awl in a future iter."
                ),
            },
            {
                "name": "radd",
                "label_en": "Devolution of residual to fixed-share heirs",
                "article_references": [],
                "blocked_rules": [],
                "comment": (
                    "Likely covered by arts 144-152 now in the local tree, "
                    "but the engine does not model radd. Studio review "
                    "required."
                ),
            },
            {
                "name": "asaba_residuary_ordering",
                "label_en": "Residuary heirs ordering (asaba)",
                "article_references": [],
                "blocked_rules": [],
                "comment": (
                    "Articles 144-146 (Csp1105) and 147-152 (Csp1110) are "
                    "candidates for the residuary section but require Studio "
                    "review to confirm and to tag every relevant article."
                ),
            },
            {
                "name": "applicable_law_decision",
                "label_en": "TN applicable-law decision",
                "article_references": [],
                "blocked_rules": [],
                "comment": (
                    "The engine has no Tunisian-side applicable-law "
                    "decision skeleton today. Code DIP (Loi 98-97) is "
                    "available locally but not yet wired."
                ),
            },
            {
                "name": "dip_eu_cross_border_coordination",
                "label_en": "TN Code DIP × EU Reg. 650/2012 cross-border coordination",
                "article_references": [],
                "blocked_rules": [],
                "comment": (
                    "Cross-border successions involving EU residents would "
                    "require coordinated TN Code DIP + EU 650/2012 logic. "
                    "EU 650/2012 is currently classified as "
                    "blocked_fetch_failed; no cross-border rule may fire."
                ),
            },
            {
                "name": "eu_650_blocked_real_source_dependency",
                "label_en": "EU 650/2012 source still blocked",
                "article_references": [],
                "blocked_rules": [],
                "comment": (
                    "Hard pre-requisite for any rule that would consult "
                    "EU 650/2012. The mapping refuses to declare such "
                    "rules until the EU source is real-verified."
                ),
            },
        ],
        "blockers_before_activation": [
            "every rule's confidence must be reviewed by a Studio reviewer reading the extracted_text_snippet against the corresponding jurisitetunisie.com page",
            "no rule has a share_spec — this iter expanded the corpus but did not derive shares; the next mapping iter must propose share_specs and re-classify rules where Hajb does not apply",
            "the engine must implement Hajb (eviction) before any of the 22 Hajb-tagged rules (arts 122-143) can fire",
            "EU 650/2012 must be unblocked (real-verified file + classification=fetch_success) before any cross-border rule may be drafted",
            "TN applicable-law decision skeleton must be wired",
            f"missing-in-source-tree articles ({missing_in_local_tree}) require an alternative edition (e.g. JORT 1956) before Studio review can be exhaustive",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[ok] wrote {OUTPUT.relative_to(REPO_ROOT)}")
    print(f"     rules: {len(rules)} (all blocked)")
    print(f"     hajb-tagged rules: {len(hajb_rule_ids)}")
    print(f"     non-hajb rules:    {len(rules) - len(hajb_rule_ids)}")
    print(f"     activation_allowed: {mapping['activation_allowed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
