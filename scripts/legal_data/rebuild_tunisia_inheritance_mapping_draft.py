"""F-tunisia-csp-livre-ix-mapping-draft-pass1 — mapping draft rebuilder.

The Tunisia inheritance mapping draft is a thin, deliberately
under-claiming JSON snapshot tied to the validated CSP Livre IX
extraction artefact. It does **not** contain any active share rule:
the only article range we have on disk (122–143) covers the Hajb
(éviction successorale) — a mechanism the engine does not model
and which the brief explicitly lists under
``unsupported_mechanisms``.

Every rule in the draft is therefore a **blocked** rule with no
``share_spec``. The mapping pins:

* the source slug + sha (real-verified by
  ``F-tunisia-official-source-real-files-restore-pass1``);
* the context_sources, with EU 650/2012 declared explicitly as
  ``blocked_fetch_failed`` and ``load_bearing=false``;
* the wizard inputs already captured by the form;
* every CSP article anchored on the official page as a ``blocked``
  ``ma_inh_csp_art_*``-style rule with the article's text snippet
  for Studio review;
* the unsupported_mechanisms list including the explicit dependency
  on the EU 650 source being unblocked before any cross-border rule
  can fire.

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

SOURCE_SLUG = "tn-code-statut-personnel-livre-ix-succession"


def _build_rule(article: dict) -> dict:
    article_no = article["article"]
    snippet = article["text"][:280]
    return {
        "rule_id": f"tn-csp-art-{article_no}",
        "article_references": [str(article_no)],
        "scenario": {},
        "share_spec": None,
        "blocked": True,
        "extracted_text_snippet": snippet,
        "extraction_confidence": article["extraction_confidence"],
        "confidence": "low",
        "needs_manual_review": True,
        "activation_blockers": [
            "the available CSP page (articles 122–143) covers Hajb (éviction successorale), an unsupported_mechanism — no share_spec can be derived from this article alone",
            "the CSP Fardh / share-distribution articles (85–121, 144–152) live on adjacent jurisitetunisie.com pages not yet fetched into the local source tree",
            "EU 650/2012 source is currently classified blocked_fetch_failed; no cross-border rule may fire until it becomes load-bearing",
        ],
        "comment": (
            f"CSP Livre IX, article {article_no}. Text extracted from the "
            f"validated official_html source (sha pinned in the mapping "
            f"header). The article belongs to the Hajb (éviction) section "
            f"of Livre IX; this iter records the article verbatim for "
            f"Studio review but does not derive any computed share."
        ),
    }


def main() -> int:
    extraction = json.loads(EXTRACT_JSON.read_text(encoding="utf-8"))
    rules = [_build_rule(a) for a in extraction["articles"]]

    mapping = {
        "schema_version": "1.0",
        "iter": "F-tunisia-csp-livre-ix-mapping-draft-pass1",
        "iter_lineage": [
            "F-tunisia-official-source-real-files-restore-pass1 (real CSP + DIP files restored)",
            "F-tunisia-csp-livre-ix-mapping-draft-pass1 (Hajb-only blocked rules; EU 650 declared blocked context)",
        ],
        "country": "TN",
        "case_type": "international_inheritance",
        "source_slug": SOURCE_SLUG,
        "source_canonical_reference": (
            "Code du statut personnel — Livre IX (De la succession), Tunisie. "
            "Articles 122–143 only (Hajb / éviction). "
            "Loi initiale 1956, version consolidée 2024 publiée par jurisitetunisie.com."
        ),
        "source_sha256": extraction["source_sha256"],
        "source_size_bytes": extraction["size_bytes"],
        "extraction_basis": "official_html",
        "extraction_artifact": str(EXTRACT_JSON.relative_to(REPO_ROOT)).replace("\\", "/"),
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "draft",
        "activation_allowed": False,
        "needs_manual_review": True,
        "context_sources": [
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
            },
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
            },
        ],
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
                "sibling sub-typing (full / consanguine / uterine) — needed for arts 132–139",
                "grandchildren (sons' sons, sons' daughters) — covered by arts 125–127 but no wizard field",
                "agnatic ascendants (paternal grandfather, paternal grandmother) — covered by arts 140–143 but no wizard field",
                "cousin / aunt / uncle relationships — covered by arts 134–137 but no wizard field",
            ],
            "missing_articles_for_share_distribution": [
                "CSP arts 85–121 (general succession + Fardh shares) — not in local source tree",
                "CSP arts 144–152 (residual rules + remainders) — not in local source tree",
            ],
        },
        "rules": rules,
        "unsupported_mechanisms": [
            {
                "name": "hajb",
                "label_en": "Eviction (total or by reduction)",
                "article_references": [str(a["article"]) for a in extraction["articles"]],
                "blocked_rules": [r["rule_id"] for r in rules],
                "comment": (
                    "All 22 articles in the available CSP page (122–143) "
                    "describe Hajb. The engine cannot apply Hajb without "
                    "the full taxonomy of heir relationships (degrees, "
                    "uterine/consanguine/germain distinction). Every rule "
                    "in this draft is therefore blocked."
                ),
            },
            {
                "name": "'awl",
                "label_en": "Proportional reduction when fixed shares exceed unity",
                "article_references": [],
                "blocked_rules": [],
                "comment": (
                    "Not on the available CSP page; covered in arts 144+ "
                    "which are not in the local source tree."
                ),
            },
            {
                "name": "radd",
                "label_en": "Devolution of residual to fixed-share heirs",
                "article_references": [],
                "blocked_rules": [],
                "comment": "Not on the available CSP page.",
            },
            {
                "name": "asaba_residuary_ordering",
                "label_en": "Residuary heirs ordering (asaba)",
                "article_references": [],
                "blocked_rules": [],
                "comment": "Not on the available CSP page.",
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
            "every rule's confidence must be reviewed by a Studio reviewer reading the extracted_text_snippet against the full CSP Livre IX page",
            "the missing CSP article ranges (85–121, 144–152) must be fetched and validated before any share_spec can be drafted",
            "the engine must implement Hajb (eviction) before any rule from this mapping can fire",
            "EU 650/2012 must be unblocked (real-verified file + classification=fetch_success) before any cross-border rule may be drafted",
            "TN applicable-law decision skeleton must be wired",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[ok] wrote {OUTPUT.relative_to(REPO_ROOT)}")
    print(f"     rules: {len(rules)} (all blocked)")
    print(f"     source_sha256: {mapping['source_sha256']}")
    print(f"     activation_allowed: {mapping['activation_allowed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
