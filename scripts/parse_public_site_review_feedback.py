"""Parse + valida un CSV checklist review compilato dallo Studio.

Iter F-product-studio-review-feedback-intake.

Pipeline:

1. Header esatto:
   ``area,page_url,language,review_item,current_status,reviewer,
   status,notes,reviewed_at``
2. Validazione riga-per-riga:
   - ``status`` ∈ {pending, approved, change_requested, rejected,
     not_applicable};
   - ``reviewer`` non vuoto se ``status != pending``;
   - ``reviewed_at`` non vuoto se ``status != pending``;
   - ``notes`` non vuote se ``status ∈ {change_requested, rejected}``;
   - ``area``, ``page_url``, ``review_item`` non vuoti;
   - ``language`` ∈ {it, fr, en, ar, all}.
3. Aggregazione:
   - counts per status;
   - counts per area;
   - lista NO-GO ancora aperti (mappa NO-GO ↔ righe checklist);
   - lista change_requested con notes;
   - lista rejected con notes;
   - elenco proposte tecniche derivate (senza applicare nulla).
4. Output:
   - report markdown:
     ``docs/review/PUBLIC_SITE_STUDIO_REVIEW_FEEDBACK_SUMMARY.md`` (default,
     override con ``--summary <path>``);
   - exit 0 se schema valido, 1 se invalido (lo script stampa la
     lista delle violazioni a stderr/stdout prima di uscire).

Lo script è **read-only** sul resto del repo e **non** applica
correzioni: si limita a trasformare il feedback dello Studio in un
artefatto leggibile.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


def _force_utf8_stdio() -> None:
    """Wrap stdout/stderr in UTF-8 so the markdown summary (— → arrows,
    accents) survives Windows cp1252 consoles when --no-summary is used.
    Only called from `__main__` so pytest's capture machinery is not
    disturbed at import time."""
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SUMMARY_PATH = (
    REPO_ROOT / "docs" / "review" / "PUBLIC_SITE_STUDIO_REVIEW_FEEDBACK_SUMMARY.md"
)

REQUIRED_HEADER = [
    "area",
    "page_url",
    "language",
    "review_item",
    "current_status",
    "reviewer",
    "status",
    "notes",
    "reviewed_at",
]
ALLOWED_STATUSES = {"pending", "approved", "change_requested", "rejected", "not_applicable"}
ALLOWED_LANGUAGES = {"it", "fr", "en", "ar", "all"}
NEEDS_NOTES_STATUSES = {"change_requested", "rejected"}

# NO-GO Studio (vedi docs/review/PUBLIC_SITE_STUDIO_REVIEW_PACKAGE.md §7).
# Ogni voce mappa a un set di area/pattern in modo che l'aggregator
# possa marcare il NO-GO come "still open" se almeno una riga
# correlata non è ancora "approved" o "not_applicable".
NO_GO_DEFINITIONS = [
    {
        "id": "ar_translations_native_review",
        "label": "Traduzioni AR non native-validated",
        "match_areas": {"translations", "legal_tone"},
        "match_languages": {"ar"},
    },
    {
        "id": "under_review_countries_appearance",
        "label": "FR/BE/MA/TN non devono sembrare calculator attivi",
        "match_areas": {"no_claim_under_review"},
        "match_languages": None,
    },
    {
        "id": "pexels_country_images_approval",
        "label": "Immagini paese Pexels da approvare",
        "match_areas": {"pexels"},
        "match_languages": None,
    },
    {
        "id": "disclaimer_privacy_signoff",
        "label": "Disclaimer e privacy notice da approvare",
        "match_areas": {"disclaimer", "privacy"},
        "match_languages": None,
    },
    {
        "id": "cookie_banner_confirmation",
        "label": "Cookie banner — confermare 'no analytics no marketing'",
        "match_areas": {"cookie"},
        "match_languages": None,
    },
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Row:
    line: int
    area: str
    page_url: str
    language: str
    review_item: str
    current_status: str
    reviewer: str
    status: str
    notes: str
    reviewed_at: str


@dataclass
class Report:
    rows: list[Row]
    violations: list[str]
    counts_by_status: Counter
    counts_by_area: Counter
    no_go_open: list[dict]
    no_go_resolved: list[dict]
    proposed_tech_tasks: list[dict]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _row_violations(row: Row) -> list[str]:
    issues: list[str] = []
    if not row.area.strip():
        issues.append("empty `area`")
    if not row.page_url.strip():
        issues.append("empty `page_url`")
    if not row.review_item.strip():
        issues.append("empty `review_item`")
    if row.language not in ALLOWED_LANGUAGES:
        issues.append(f"language={row.language!r} not in {sorted(ALLOWED_LANGUAGES)}")
    if row.status not in ALLOWED_STATUSES:
        issues.append(f"status={row.status!r} not in {sorted(ALLOWED_STATUSES)}")
    if row.status != "pending":
        if not row.reviewer.strip():
            issues.append(f"reviewer empty but status={row.status!r}")
        if not row.reviewed_at.strip():
            issues.append(f"reviewed_at empty but status={row.status!r}")
    if row.status in NEEDS_NOTES_STATUSES and not row.notes.strip():
        issues.append(f"notes empty but status={row.status!r}")
    return [f"line {row.line}: {msg}" for msg in issues]


def parse_csv(csv_path: Path) -> Report:
    if not csv_path.exists():
        return Report(
            rows=[],
            violations=[f"missing CSV: {csv_path}"],
            counts_by_status=Counter(),
            counts_by_area=Counter(),
            no_go_open=[],
            no_go_resolved=[],
            proposed_tech_tasks=[],
        )

    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != REQUIRED_HEADER:
            return Report(
                rows=[],
                violations=[
                    "header mismatch: " f"{reader.fieldnames!r} (expected {REQUIRED_HEADER!r})"
                ],
                counts_by_status=Counter(),
                counts_by_area=Counter(),
                no_go_open=[],
                no_go_resolved=[],
                proposed_tech_tasks=[],
            )

        rows: list[Row] = []
        violations: list[str] = []
        for idx, raw in enumerate(reader, start=2):  # csv lines (header is line 1)
            row = Row(
                line=idx,
                area=(raw.get("area") or "").strip(),
                page_url=(raw.get("page_url") or "").strip(),
                language=(raw.get("language") or "").strip(),
                review_item=(raw.get("review_item") or "").strip(),
                current_status=(raw.get("current_status") or "").strip(),
                reviewer=(raw.get("reviewer") or "").strip(),
                status=(raw.get("status") or "").strip(),
                notes=(raw.get("notes") or "").strip(),
                reviewed_at=(raw.get("reviewed_at") or "").strip(),
            )
            rows.append(row)
            violations.extend(_row_violations(row))

    counts_by_status = Counter(r.status for r in rows)
    counts_by_area = Counter(r.area for r in rows)

    no_go_open: list[dict] = []
    no_go_resolved: list[dict] = []
    for definition in NO_GO_DEFINITIONS:
        related = [
            r
            for r in rows
            if r.area in definition["match_areas"]
            and (
                definition["match_languages"] is None or r.language in definition["match_languages"]
            )
        ]
        related_unresolved = [r for r in related if r.status not in {"approved", "not_applicable"}]
        entry = {
            "id": definition["id"],
            "label": definition["label"],
            "related_total": len(related),
            "related_unresolved": len(related_unresolved),
            "rows_unresolved": related_unresolved,
        }
        if related_unresolved:
            no_go_open.append(entry)
        elif related:
            # All related rows resolved (approved / not_applicable).
            no_go_resolved.append(entry)
        else:
            # No related rows at all — keep it as open with related_total=0
            # so reviewer notices the checklist doesn't cover this NO-GO.
            no_go_open.append(entry)

    proposed = _propose_tech_tasks(rows)

    return Report(
        rows=rows,
        violations=violations,
        counts_by_status=counts_by_status,
        counts_by_area=counts_by_area,
        no_go_open=no_go_open,
        no_go_resolved=no_go_resolved,
        proposed_tech_tasks=proposed,
    )


def _propose_tech_tasks(rows: list[Row]) -> list[dict]:
    """Trasforma change_requested/rejected in proposte tecniche.

    Niente applicazione: solo elenco. Una proposta tecnica ha sempre
    `change` (cosa fare) e `confirm_with_studio` (cosa va richiesto
    allo Studio prima di toccare un template).
    """
    proposals: list[dict] = []
    for row in rows:
        if row.status not in NEEDS_NOTES_STATUSES:
            continue
        # Suggerimento operativo per area: identifichiamo path / file
        # candidati senza modificare nulla.
        suggested_files: list[str] = []
        if row.area.startswith("country_landing"):
            suggested_files.append("templates/public/country_landing.html")
            suggested_files.append("apps/core/views.py:_country_landing_context")
        elif row.area.startswith("wizard_italy"):
            suggested_files.append("templates/public/wizard_italy_road_accident.html")
        elif row.area.startswith("wizard_france"):
            suggested_files.append("templates/public/wizard_france_road_accident.html")
        elif row.area.startswith("wizard_belgium"):
            suggested_files.append("templates/public/wizard_belgium_road_accident.html")
        elif row.area.startswith("wizard_morocco"):
            suggested_files.append("templates/public/wizard_morocco_inheritance.html")
        elif row.area.startswith("wizard_tunisia"):
            suggested_files.append("templates/public/wizard_tunisia_inheritance.html")
        elif row.area == "home":
            suggested_files.append("templates/public/home.html")
        elif row.area == "countries_index":
            suggested_files.append("templates/public/countries.html")
        elif row.area == "contact":
            suggested_files.append("templates/public/contact.html")
        elif row.area == "privacy":
            suggested_files.append("templates/public/privacy.html")
        elif row.area == "disclaimer":
            suggested_files.append("templates/public/disclaimer.html")
        elif row.area == "cookie":
            suggested_files.append("templates/partials/cookie_consent_banner.html")
        elif row.area == "pexels":
            suggested_files.append("media/pexels/pexels_manifest.json")
            suggested_files.append("apps/core/management/commands/fetch_pexels_site_images.py")
        elif row.area == "translations":
            suggested_files.append("locale/<lang>/LC_MESSAGES/django.po")
        elif row.area == "legal_tone":
            suggested_files.append("templates/public/*.html")
        elif row.area == "seo":
            suggested_files.append("templates/base.html")
            suggested_files.append("apps/core/seo.py")
        elif row.area == "a11y":
            suggested_files.append("templates/base.html")

        proposals.append(
            {
                "area": row.area,
                "page_url": row.page_url,
                "language": row.language,
                "review_item": row.review_item,
                "status": row.status,
                "reviewer": row.reviewer,
                "reviewed_at": row.reviewed_at,
                "notes": row.notes,
                "suggested_files": suggested_files,
                "confirm_with_studio": (
                    "Conferma il wording finale prima di applicare"
                    if row.status == "change_requested"
                    else "Conferma se la riga va riscritta o rimossa"
                ),
            }
        )
    return proposals


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_summary_markdown(csv_path: Path, report: Report) -> str:
    rel_csv = csv_path.as_posix()
    total = len(report.rows)
    approved = report.counts_by_status.get("approved", 0)
    change_requested = report.counts_by_status.get("change_requested", 0)
    rejected = report.counts_by_status.get("rejected", 0)
    not_applicable = report.counts_by_status.get("not_applicable", 0)
    pending = report.counts_by_status.get("pending", 0)

    lines: list[str] = []
    add = lines.append

    add("# Public site Studio review — feedback summary")
    add("")
    add(f"Generated from: `{rel_csv}`.")
    add("")
    add("Read-only artefact prodotto da")
    add("`scripts/parse_public_site_review_feedback.py` (iter")
    add("F-product-studio-review-feedback-intake). **Nessuna modifica**")
    add("ai template, ai dataset legali, ai motori o al DB è stata applicata.")
    add("Le 'proposte tecniche' della §8 sono candidate da discutere con lo")
    add("Studio prima di toccare i template.")
    add("")
    add("---")
    add("")

    # 1. Executive summary
    add("## 1. Executive summary")
    add("")
    if total == 0:
        add("Nessuna riga letta dal CSV (file vuoto o solo header).")
    else:
        ratio = (approved / total) * 100 if total else 0
        add(f"- Righe totali: **{total}**.")
        add(f"- Approved: **{approved}** ({ratio:.0f}%).")
        add(f"- Change requested: **{change_requested}**.")
        add(f"- Rejected: **{rejected}**.")
        add(f"- Not applicable: **{not_applicable}**.")
        add(f"- Pending (non ancora reviewed): **{pending}**.")
        if report.violations:
            add("- Violazioni schema/dati: " f"**{len(report.violations)}** (vedi §10).")
    add("")

    # 2. Counts per status
    add("## 2. Counts per status")
    add("")
    add("| Status | Count |")
    add("|--------|------:|")
    for status in ("approved", "change_requested", "rejected", "not_applicable", "pending"):
        add(f"| {status} | {report.counts_by_status.get(status, 0)} |")
    add("")
    add("### Counts per area")
    add("")
    add("| Area | Count |")
    add("|------|------:|")
    for area, count in sorted(report.counts_by_area.items()):
        add(f"| {area} | {count} |")
    add("")

    # 3. Approved
    add("## 3. Approved items")
    add("")
    approved_rows = [r for r in report.rows if r.status == "approved"]
    if approved_rows:
        add("| # | Area | Page | Lang | Item | Reviewer | Reviewed at |")
        add("|---|------|------|------|------|----------|-------------|")
        for i, r in enumerate(approved_rows, start=1):
            item = r.review_item.replace("|", "\\|")[:80]
            add(
                f"| {i} | {r.area} | `{r.page_url}` | {r.language} | "
                f"{item} | {r.reviewer or '—'} | {r.reviewed_at or '—'} |"
            )
    else:
        add("_Nessun item approved._")
    add("")

    # 4. Change requested
    add("## 4. Change requested items")
    add("")
    cr_rows = [r for r in report.rows if r.status == "change_requested"]
    if cr_rows:
        for i, r in enumerate(cr_rows, start=1):
            add(f"### 4.{i} — {r.area} · `{r.page_url}` ({r.language})")
            add("")
            add(f"**Item:** {r.review_item}")
            add("")
            add(f"**Reviewer:** {r.reviewer or '—'} — **Reviewed at:** {r.reviewed_at or '—'}")
            add("")
            add(f"**Notes from Studio:** {r.notes}")
            add("")
    else:
        add("_Nessun change_requested ricevuto._")
    add("")

    # 5. Rejected
    add("## 5. Rejected items")
    add("")
    rj_rows = [r for r in report.rows if r.status == "rejected"]
    if rj_rows:
        for i, r in enumerate(rj_rows, start=1):
            add(f"### 5.{i} — {r.area} · `{r.page_url}` ({r.language})")
            add("")
            add(f"**Item:** {r.review_item}")
            add("")
            add(f"**Reviewer:** {r.reviewer or '—'} — **Reviewed at:** {r.reviewed_at or '—'}")
            add("")
            add(f"**Notes from Studio:** {r.notes}")
            add("")
    else:
        add("_Nessuna riga rejected._")
    add("")

    # 6. Pending
    add("## 6. Pending items")
    add("")
    pending_rows = [r for r in report.rows if r.status == "pending"]
    if pending_rows:
        add(f"Restano **{len(pending_rows)}** righe da revieware. Esempi (max 10):")
        add("")
        for r in pending_rows[:10]:
            item = r.review_item[:90]
            add(f"- `{r.page_url}` · {r.area} · {r.language} — {item}")
        if len(pending_rows) > 10:
            add(f"- _… altre {len(pending_rows) - 10} righe pending._")
    else:
        add("_Nessuna riga pending: lo Studio ha completato la review._")
    add("")

    # 7. NO-GO open
    add("## 7. NO-GO ancora aperti")
    add("")
    if report.no_go_open:
        for entry in report.no_go_open:
            add(
                f"- **{entry['label']}** "
                f"(id `{entry['id']}`) — "
                f"{entry['related_unresolved']}/{entry['related_total']} righe non risolte."
            )
    else:
        add("_Tutti i NO-GO sono coperti da righe approved/not_applicable._")
    if report.no_go_resolved:
        add("")
        add("### NO-GO risolti")
        add("")
        for entry in report.no_go_resolved:
            add(f"- {entry['label']} ({entry['related_total']}/{entry['related_total']} risolti).")
    add("")

    # 8. Proposed tech tasks
    add("## 8. Task tecnici proposti (NON applicati)")
    add("")
    if report.proposed_tech_tasks:
        for i, p in enumerate(report.proposed_tech_tasks, start=1):
            add(f"### 8.{i} — {p['area']} · `{p['page_url']}` ({p['language']}) — {p['status']}")
            add("")
            add(f"**Studio note:** {p['notes']}")
            add("")
            if p["suggested_files"]:
                add("**File candidati:**")
                for f in p["suggested_files"]:
                    add(f"- `{f}`")
                add("")
            add(f"**Action gating:** {p['confirm_with_studio']}.")
            add("")
    else:
        add("_Nessuna proposta tecnica generata (nessun change_requested/rejected)._")
    add("")

    # 9. What stays blocked
    add("## 9. Cosa resta bloccato")
    add("")
    blockers: list[str] = []
    if pending > 0:
        blockers.append(f"{pending} righe checklist ancora pending → review Studio incompleta.")
    if report.no_go_open:
        for entry in report.no_go_open:
            blockers.append(
                f"NO-GO `{entry['id']}` non risolto "
                f"({entry['related_unresolved']}/{entry['related_total']} righe da chiudere)."
            )
    if change_requested > 0:
        blockers.append(
            f"{change_requested} righe change_requested → richiedono fix copy/template + ri-review."
        )
    if rejected > 0:
        blockers.append(
            f"{rejected} righe rejected → richiedono decisione su rimozione/riscrittura."
        )
    if not blockers:
        add("_Nessun blocker residuo: il sito può essere mostrato a un cliente esterno._")
    else:
        for line in blockers:
            add(f"- {line}")
    add("")

    # 10. Schema violations (only if any)
    if report.violations:
        add("## 10. Violazioni schema/dati")
        add("")
        add("Lo script è uscito con exit code 1. Correggere il CSV e rieseguire.")
        add("")
        for v in report.violations[:50]:
            add(f"- {v}")
        if len(report.violations) > 50:
            add(f"- _… altre {len(report.violations) - 50} violazioni._")
        add("")

    add("---")
    add("")
    add("Generato da `scripts/parse_public_site_review_feedback.py`. Fonte CSV: " f"`{rel_csv}`.")
    add("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path al CSV review compilato dallo Studio")
    parser.add_argument(
        "--summary",
        default=str(DEFAULT_SUMMARY_PATH),
        help="Path al file markdown di summary (default docs/review/PUBLIC_SITE_STUDIO_REVIEW_FEEDBACK_SUMMARY.md)",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Stampa il summary su stdout invece che su file",
    )
    args = parser.parse_args(argv)

    csv_path = Path(args.csv).resolve()
    report = parse_csv(csv_path)

    summary_md = render_summary_markdown(csv_path, report)
    if args.no_summary:
        print(summary_md)
    else:
        summary_path = Path(args.summary).resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary_md, encoding="utf-8")
        print(f"[review-feedback] summary written: {summary_path}")

    print(f"[review-feedback] rows: {len(report.rows)}")
    print(f"[review-feedback] approved: {report.counts_by_status.get('approved', 0)}")
    print(
        f"[review-feedback] change_requested: "
        f"{report.counts_by_status.get('change_requested', 0)}"
    )
    print(f"[review-feedback] rejected: {report.counts_by_status.get('rejected', 0)}")
    print(f"[review-feedback] pending: {report.counts_by_status.get('pending', 0)}")
    print(
        f"[review-feedback] not_applicable: " f"{report.counts_by_status.get('not_applicable', 0)}"
    )
    print(f"[review-feedback] NO-GO open: {len(report.no_go_open)}")
    print(f"[review-feedback] proposed tech tasks: {len(report.proposed_tech_tasks)}")

    if report.violations:
        print(
            f"\n[review-feedback] VIOLATIONS ({len(report.violations)}):",
            file=sys.stderr,
        )
        for v in report.violations[:50]:
            print(f"  - {v}", file=sys.stderr)
        if len(report.violations) > 50:
            print(f"  - … altre {len(report.violations) - 50} violazioni.", file=sys.stderr)
        return 1

    print("[review-feedback] schema OK.")
    return 0


if __name__ == "__main__":
    _force_utf8_stdio()
    sys.exit(main())
