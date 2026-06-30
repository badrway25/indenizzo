"""P50 — guard the official-source harvest command (allowlist, robots, dry-run,
metadata/hash), the extraction-destination schema, the validation packs, and the
unchanged cardinal-rule guardrails (no engine without a validated table + canary,
no internal status leaks, no heavy PDFs committed)."""

from __future__ import annotations

import json
import re
from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import Client

BASE = Path(settings.BASE_DIR)
CMD = (BASE / "apps" / "legal_sources" / "management" / "commands"
       / "harvest_official_sources.py").read_text("utf-8")
PACKS = BASE / "docs" / "legal_validation"
LEGAL_TABLES = BASE / "apps" / "calculators" / "data" / "legal_tables"


# --- 1-3. Allowlist · refuses non-official · dry-run ----------------------
def test_allowlist_is_official_domains_only():
    from apps.legal_sources.management.commands.harvest_official_sources import ALLOWED_DOMAINS

    assert ALLOWED_DOMAINS  # non-empty
    bad = [d for d in ALLOWED_DOMAINS
           if not re.search(r"\.(gov\.\w+|gouv\.fr|fgov\.be|europa\.eu)$|normattiva\.it|"
                            r"gazzettaufficiale\.it|inail\.it|acaps\.ma|legislation\.tn$", d)]
    assert not bad, f"non-official domains in allowlist: {bad}"
    # no blog / commercial / aggregator hosts
    for forbidden in ("blogspot", "wordpress", "medium.com", "scribd", "wikipedia"):
        assert forbidden not in CMD.lower()


def test_command_refuses_non_official_domains():
    assert "not in ALLOWED_DOMAINS" in CMD
    assert "REFUSED non-official domain" in CMD


def test_command_respects_robots_and_is_not_aggressive():
    assert "robotparser" in CMD and "_robots_allows" in CMD
    assert "robots_allowed" in CMD
    # one request per target: a single requests.get in the per-target loop (plus robots)
    assert CMD.count("requests.get(") <= 2


def test_dry_run_makes_no_network_and_prints_plan():
    out = StringIO()
    call_command("harvest_official_sources", "--dry-run", stdout=out)
    text = out.getvalue()
    assert "DRY-RUN" in text and "harvest plan" in text
    assert "No engine is created by harvesting" in text


# --- 4. Metadata includes hash + provenance -------------------------------
def test_manifest_records_hash_and_provenance():
    for field in ("sha256_first_chunk", "fetched_at", "authority", "http_status", "content_type"):
        assert field in CMD, f"manifest missing provenance field {field}"
    # heavy bodies are not stored, only hashed (capped)
    assert "MAX_SNAPSHOT_BYTES" in CMD


# --- 5-6. Extraction schema: source_id + cannot-use-unless-ready -----------
def test_legal_table_schema_requires_provenance_and_canary():
    schema = json.loads((LEGAL_TABLES / "_schema.json").read_text("utf-8"))
    for req in ("source_id", "authority", "url", "hash", "validation_status", "canaries"):
        assert req in schema["required"], f"schema must require {req}"
    assert "ready_for_engine" in schema["properties"]["validation_status"]["enum"]


def test_no_table_data_files_yet():
    # No (country, category, version).json exists — nothing is validated yet.
    data_files = [p for p in LEGAL_TABLES.rglob("*.json") if p.name != "_schema.json"]
    assert data_files == [], f"unexpected (unvalidated) table data: {data_files}"


# --- 7. Validation pack per high-priority source --------------------------
@pytest.mark.parametrize("pack", [
    "INAIL_WORK_INJURY_VALIDATION.md", "MOROCCO_ROAD_DAMAGE_VALIDATION.md",
    "TUNISIA_ROAD_DAMAGE_VALIDATION.md", "MOROCCO_FAMILY_LOSS_VALIDATION.md",
    "TUNISIA_FAMILY_LOSS_VALIDATION.md", "PRODUCT_LIABILITY_VALIDATION.md",
    "FRANCE_ROAD_DAMAGE_VALIDATION.md", "BELGIUM_ROAD_DAMAGE_VALIDATION.md",
])
def test_validation_pack_exists_and_has_status(pack):
    text = (PACKS / pack).read_text("utf-8")
    assert "**Status:**" in text
    assert any(s in text for s in (
        "ready_for_engine", "needs_legal_review", "needs_official_table",
        "needs_formula", "needs_canary", "not_calculable"))


def test_harvest_plan_and_gap_map_exist():
    assert (BASE / "docs" / "audits" / "P50_OFFICIAL_SOURCE_HARVEST_PLAN_2026-06-30.md").is_file()
    assert (BASE / "docs" / "audits" / "P47_MISSING_OFFICIAL_SOURCES_FOR_ESTIMATES_2026-06-30.md").is_file()


# --- 8. No internal status leaks in public pages --------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/guided/", "/sources/", "/documentation/", "/countries/"])
def test_no_internal_status_leak(path):
    body = Client().get(path, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8").lower()
    for leak in ("ready_for_engine", "needs_legal_review", "not_calculable",
                 "validation_status", "usable_for_engine", "needs_official_table"):
        assert leak not in body, f"{path} leaks internal status {leak!r}"


# --- 9. No engine activated without canary (engine set unchanged) ----------
def test_no_new_engine_activated():
    from apps.calculators.registry import list_available_calculators

    assert {(j, c) for j, c in list_available_calculators()} == {
        ("BE-NATIONAL", "road_accident_bodily_injury"),
        ("FR-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "inheritance_basic"),
        ("IT-NATIONAL", "medical_liability_biological_damage"),
        ("IT-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "road_accident_microlesions"),
        ("MA-NATIONAL", "international_inheritance"),
        ("TN-NATIONAL", "international_inheritance"),
    }


# --- 10. Matrix only says "estimate available" where Italy engine pays ------
def test_matrix_still_truthful():
    from apps.core.templatetags.estimate_tags import _MATRIX, ST_ESTIMATE

    italy = sum(1 for i, (_c, rows) in enumerate(_MATRIX)
                for _cat, s in rows if s == ST_ESTIMATE and i == 0)
    other = sum(1 for i, (_c, rows) in enumerate(_MATRIX)
                for _cat, s in rows if s == ST_ESTIMATE and i != 0)
    assert italy == 3 and other == 0


# --- 11. Public "what it takes" explanation -------------------------------
@pytest.mark.django_db
def test_public_what_it_takes_explanation():
    body = Client().get("/documentation/", HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert "Cosa serve per mostrare un importo" in body


# --- 12. No heavy / committed PDFs in code trees --------------------------
def test_no_committed_pdfs_in_code_trees():
    for tree in ("apps", "static", "templates"):
        pdfs = list((BASE / tree).rglob("*.pdf"))
        assert pdfs == [], f"unexpected committed PDFs under {tree}/: {pdfs}"
