"""Generate a DB- and registry-grounded legal review package per country.

The hand-written ``docs/legal_sources/<COUNTRY>_LEGAL_REVIEW_PACKAGE.md`` files
are detailed but static and can drift from the live DB. This module produces a
*regenerable*, always-current package that merges:

- the current ``LegalSource`` state (via :mod:`apps.legal_sources.status_report`),
- the per-source ingest policy from ``config/official_source_registry.json``
  (``can_auto_ingest``, ``human_exception_review_required`` + why, ingest mode,
  content markers, ``manual_attach_allowed``),
- an explicit GO/NO-GO decision checklist the Studio must record per source.

Strictly read-only. No DB writes, no network, no PII, no calculation. It never
approves anything — it only consolidates what the Studio must decide.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings

from apps.legal_sources.status_report import build_rows

_REGISTRY_PATH = Path(settings.BASE_DIR) / "config" / "official_source_registry.json"


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, dict[str, Any]]:
    """slug -> registry entry. Empty dict if the registry is missing."""
    if not _REGISTRY_PATH.is_file():
        return {}
    raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    return {e["source_slug"]: e for e in raw.get("entries", [])}


def _registry_overlay(slug: str) -> dict[str, Any]:
    e = _load_registry().get(slug, {})
    return {
        "in_registry": bool(e),
        "source_kind": e.get("source_kind", ""),
        "can_auto_ingest": e.get("can_auto_ingest"),
        "human_exception_review_required": e.get("human_exception_review_required"),
        "why_human_exception_review": e.get("why_human_exception_review_if_any", ""),
        "ingest_mode": e.get("ingest_mode", ""),
        "manual_attach_allowed": e.get("manual_attach_allowed"),
        "content_markers": e.get("content_must_contain", []) or [],
        "no_calculator_activation": e.get("no_calculator_activation"),
    }


def build_review_package(country: str) -> dict[str, Any]:
    """Return a structured review package for one country code.

    Includes every source for the country, flagging those that still require
    Studio review (status != approved) and overlaying the registry policy.
    """
    rows = [row.__dict__ for row in build_rows(country=country)]
    items: list[dict[str, Any]] = []
    for r in rows:
        overlay = _registry_overlay(r["slug"])
        items.append(
            {
                **r,
                "registry": overlay,
                # Decisions the Studio must record. Pure scaffolding — every
                # answer defaults to the safe/blocking value (unverified).
                "decisions": {
                    "document_authentic": None,
                    "sha256_matches_official": None,
                    "markers_present": None,
                    "requires_legal_interpretation": None,
                    "verdict": "pending",  # pending | approve | reject
                },
            }
        )

    needs_review = [i for i in items if i["requires_legal_review"]]
    return {
        "country": country.upper(),
        "total_sources": len(items),
        "approved_sources": sum(1 for i in items if not i["requires_legal_review"]),
        "calculation_ready": sum(1 for i in items if i["calculation_ready"]),
        "needs_review_count": len(needs_review),
        "items": items,
    }


def render_markdown(pkg: dict[str, Any]) -> str:
    c = pkg["country"]
    lines: list[str] = []
    lines.append(f"# {c} — Legal review package (generated, read-only)")
    lines.append("")
    lines.append(
        "> Regenerable snapshot from "
        "`python manage.py generate_legal_review_package --country "
        f"{c} --format markdown`. It merges the live `LegalSource` state with "
        "the registry ingest policy. It **approves nothing** — it lists what "
        "the Studio must decide. See the hand-written "
        f"`{_title(c)}_LEGAL_REVIEW_PACKAGE.md` for the detailed analysis and "
        "`MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md` for the attach procedure."
    )
    lines.append("")
    lines.append(
        f"**Summary:** sources={pkg['total_sources']} · "
        f"approved={pkg['approved_sources']} · "
        f"calculation_ready={pkg['calculation_ready']} · "
        f"needs_review={pkg['needs_review_count']}"
    )
    lines.append("")
    lines.append(
        "Cardinal rule: a source may feed a public calculation **only** when it "
        "is `approved` AND backs an `approved` dataset/formula. Authenticating a "
        "document is necessary but not sufficient. *Meglio nessun calcolo che un "
        "calcolo falso.*"
    )
    lines.append("")
    lines.append("## Sources requiring Studio review")
    lines.append("")
    needs = [i for i in pkg["items"] if i["requires_legal_review"]]
    if not needs:
        lines.append("_None — every catalogued source for this country is approved._")
    for i in needs:
        reg = i["registry"]
        lines.append(f"### `{i['slug']}`")
        lines.append("")
        lines.append(f"- **Title:** {i['title']}")
        lines.append(
            f"- **Type / status / reliability:** {i['source_type']} / "
            f"{i['status']} / {i['reliability']}"
        )
        lines.append(f"- **Official URL:** {i['official_url'] or '—'}")
        lines.append(
            f"- **Dates:** pub={i['publication_date'] or '—'} "
            f"eff={i['effective_date'] or '—'} until={i['valid_until'] or '—'}"
        )
        lines.append(
            f"- **Attachments:** {i['attachment_count']} "
            f"(hashed={i['hashed_attachment_count']}) · versions={i['version_count']}"
        )
        if reg["in_registry"]:
            lines.append(
                f"- **Registry policy:** kind={reg['source_kind'] or '—'} · "
                f"auto_ingest={reg['can_auto_ingest']} · "
                f"human_exception_review={reg['human_exception_review_required']} · "
                f"ingest_mode={reg['ingest_mode'] or '—'} · "
                f"manual_attach_allowed={reg['manual_attach_allowed']}"
            )
            if reg["why_human_exception_review"]:
                lines.append(f"- **Why human review:** {reg['why_human_exception_review']}")
            if reg["content_markers"]:
                lines.append(
                    "- **Content markers:** " + ", ".join(f"`{m}`" for m in reg["content_markers"])
                )
        else:
            lines.append("- **Registry policy:** _not in official_source_registry.json_")
        lines.append("- **Studio decisions to record:**")
        lines.append("  - [ ] Document is the authentic official text")
        lines.append("  - [ ] SHA-256 matches the official download")
        lines.append("  - [ ] Required content markers present")
        lines.append("  - [ ] Whether it needs legal interpretation / mapping")
        lines.append("  - [ ] Verdict: approve / reject (with signature)")
        lines.append("")
    return "\n".join(lines)


def _title(country: str) -> str:
    return {
        "FR": "FRANCE",
        "BE": "BELGIUM",
        "MA": "MOROCCO",
        "TN": "TUNISIA",
        "IT": "ITALY",
    }.get(country.upper(), country.upper())
