"""
Rendering del PDF della simulazione con reportlab platypus.

Pure function `render_simulation_pdf_bytes(simulation, language) -> bytes`:
prende una `Simulation` persistita e restituisce i bytes del PDF, senza
alcun side effect su DB. Il caller (service) è responsabile della
persistenza del `SimulationReport` e dell'audit.

Decisioni di design:

- Framework: `reportlab` (già in requirements come `reportlab>=4.2`).
- Layout: `SimpleDocTemplate` su A4 con `Paragraph` + `Table` + `Spacer`.
- Stile: sobrio, monocromo grafite/oro pallido, font integrato Helvetica
  (per portabilità in assenza di font esterni).
- RTL/Arabic: reportlab non gestisce bene il bidi senza shaping engine;
  il caller (`services.generate_simulation_report`) gestisce il fallback
  LTR e lo annota nei metadata. Le `labels.py` contengono già etichette
  inglesi per `lang=ar`.
- Privacy: `input_data` è filtrato dalla whitelist `_INPUT_WHITELIST`
  prima di essere mostrato. Honeypot, consensi, flag interni vengono
  esclusi.
"""

from __future__ import annotations

import io
from decimal import Decimal
from typing import Any

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.calculators.disclaimer import get_disclaimer
from apps.cases.models import Simulation

from .labels import DEFAULT_LANGUAGE, get_labels

# Whitelist dei campi di `input_data` mostrabili nel PDF. Tutto il resto
# (honeypot `website`, `consent_simulation`, `_anonymized`, ...) è
# escluso a prescindere. Le etichette sono multilingua.
_INPUT_WHITELIST: dict[str, dict[str, str]] = {
    "accident_country": {
        "it": "Paese dell'incidente",
        "fr": "Pays de l'accident",
        "en": "Accident country",
        "ar": "Accident country",
    },
    "accident_date": {
        "it": "Data dell'incidente",
        "fr": "Date de l'accident",
        "en": "Accident date",
        "ar": "Accident date",
    },
    "victim_age": {
        "it": "Età del danneggiato",
        "fr": "Âge de la victime",
        "en": "Victim age",
        "ar": "Victim age",
    },
    "permanent_disability_percentage": {
        "it": "% invalidità permanente",
        "fr": "% incapacité permanente",
        "en": "Permanent disability %",
        "ar": "Permanent disability %",
    },
    "total_temporary_disability_days": {
        "it": "Giorni di inabilità totale",
        "fr": "Jours d'incapacité totale",
        "en": "Total temporary disability days",
        "ar": "Total temporary disability days",
    },
    "partial_temporary_disability_days": {
        "it": "Giorni di inabilità parziale",
        "fr": "Jours d'incapacité partielle",
        "en": "Partial temporary disability days",
        "ar": "Partial temporary disability days",
    },
    "medical_expenses": {
        "it": "Spese mediche documentate",
        "fr": "Frais médicaux documentés",
        "en": "Documented medical expenses",
        "ar": "Documented medical expenses",
    },
    "lost_income": {
        "it": "Reddito perso documentato",
        "fr": "Revenu perdu documenté",
        "en": "Documented lost income",
        "ar": "Documented lost income",
    },
    "fault_percentage": {
        "it": "% concorso/responsabilità",
        "fr": "% de responsabilité",
        "en": "Fault percentage",
        "ar": "Fault percentage",
    },
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_simulation_pdf_bytes(simulation: Simulation, *, language: str | None = None) -> bytes:
    """Render del PDF in memoria. Ritorna i bytes del file."""
    lang = (language or simulation.locale or DEFAULT_LANGUAGE).lower().split("-", 1)[0]
    labels = get_labels(lang)
    styles = _build_styles()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=labels["report_title"],
        author=labels["studio_name"],
    )

    story: list[Any] = []
    story.extend(_build_cover(simulation, labels, styles))
    story.extend(_build_general(simulation, labels, styles))
    story.extend(_build_input(simulation, labels, styles, lang))
    story.extend(_build_result(simulation, labels, styles))
    story.extend(_build_sources(simulation, labels, styles))
    story.extend(_build_warnings(simulation, labels, styles))
    story.extend(_build_missing(simulation, labels, styles))
    story.extend(_build_assumptions(simulation, labels, styles))
    story.append(PageBreak())
    story.extend(_build_disclaimer(simulation, labels, styles, lang))
    story.extend(_build_cta(simulation, labels, styles))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def _build_cover(simulation: Simulation, labels, styles) -> list[Any]:
    return [
        Paragraph(labels["studio_name"], styles["studio_name"]),
        Spacer(1, 6 * mm),
        Paragraph(labels["report_title"], styles["title"]),
        Spacer(1, 4 * mm),
        _kv_table(
            [
                (labels["label_simulation_id"], str(simulation.public_id)),
                (
                    labels["label_generated_at"],
                    timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M"),
                ),
                (labels["label_language"], (simulation.locale or "it").upper()),
            ],
            styles,
        ),
        Spacer(1, 8 * mm),
    ]


def _build_general(simulation: Simulation, labels, styles) -> list[Any]:
    rows = [
        (
            labels["label_jurisdiction"],
            simulation.jurisdiction.code if simulation.jurisdiction_id else "—",
        ),
        (
            labels["label_country"],
            simulation.country.code if simulation.country_id else "—",
        ),
        (labels["label_case_type"], simulation.case_type),
        (
            labels["label_created_at"],
            simulation.created_at.strftime("%Y-%m-%d %H:%M") if simulation.created_at else "—",
        ),
        (labels["label_status"], simulation.status),
        (labels["label_confidence"], simulation.confidence or "—"),
        (labels["label_currency"], simulation.currency or "—"),
    ]
    return [
        Paragraph(labels["section_general"], styles["h2"]),
        _kv_table(rows, styles),
        Spacer(1, 6 * mm),
    ]


def _build_input(simulation: Simulation, labels, styles, lang: str) -> list[Any]:
    """Mostra solo i campi della whitelist con valore non vuoto."""
    rows: list[tuple[str, str]] = []
    raw = simulation.input_data or {}
    for key, label_per_lang in _INPUT_WHITELIST.items():
        value = raw.get(key)
        if value in (None, "", []):
            continue
        rows.append((label_per_lang.get(lang) or label_per_lang["en"], str(value)))

    body: list[Any] = [Paragraph(labels["section_input"], styles["h2"])]
    if not rows:
        body.append(Paragraph(labels["no_input"], styles["body_muted"]))
    else:
        body.append(_kv_table(rows, styles))
    body.append(Spacer(1, 6 * mm))
    return body


def _build_result(simulation: Simulation, labels, styles) -> list[Any]:
    body: list[Any] = [Paragraph(labels["section_result"], styles["h2"])]

    # Decisione di mostrare estimated_*: SOLO se lo status è `calculated`
    # E almeno uno dei valori è non-null. Mai inventare la stima: se lo
    # status non è `calculated` (o tutto è None), il report dichiara
    # esplicitamente l'indisponibilità (REQ "Mai mostrare importi se
    # estimated_min/mid/max sono null"). Il guard su status è difesa in
    # profondità: lega la presentazione all'invariante "no calcolo falso",
    # coerente con la result page web.
    has_amount = simulation.status == "calculated" and any(
        v is not None
        for v in (simulation.estimated_min, simulation.estimated_mid, simulation.estimated_max)
    )

    if not has_amount:
        body.append(Paragraph(labels["no_estimate"], styles["body_muted"]))
        body.append(Spacer(1, 6 * mm))
        return body

    currency = simulation.currency or ""
    body.append(
        _kv_table(
            [
                (labels["label_min"], _fmt_amount(simulation.estimated_min, currency)),
                (labels["label_mid"], _fmt_amount(simulation.estimated_mid, currency)),
                (labels["label_max"], _fmt_amount(simulation.estimated_max, currency)),
            ],
            styles,
        )
    )

    breakdown = (simulation.output_data or {}).get("breakdown") or []
    if breakdown:
        body.append(Spacer(1, 4 * mm))
        body.append(Paragraph("Breakdown", styles["h3"]))
        for item in breakdown:
            label = item.get("label") or "—"
            mid = item.get("amount_mid") or item.get("amount_min") or "—"
            note = item.get("notes") or ""
            text = f"<b>{_escape(label)}</b>: {_escape(str(mid))} {_escape(currency)}"
            if note:
                text += f"<br/><font size=9 color='#6b6b6b'>{_escape(note)}</font>"
            body.append(Paragraph(text, styles["body"]))
            body.append(Spacer(1, 2 * mm))

    body.append(Spacer(1, 6 * mm))
    return body


def _build_sources(simulation: Simulation, labels, styles) -> list[Any]:
    body: list[Any] = [Paragraph(labels["section_sources"], styles["h2"])]
    sources = simulation.sources_snapshot or []
    if not sources:
        body.append(Paragraph(labels["no_sources"], styles["body_muted"]))
        body.append(Spacer(1, 6 * mm))
        return body

    for src in sources:
        title = _escape(src.get("title") or "—")
        citation = _escape(src.get("citation") or "")
        url = _escape(src.get("official_url") or "")
        country = _escape(src.get("country") or "")
        source_type = _escape(src.get("source_type") or "")
        pub_date = _escape(src.get("publication_date") or "")

        meta_bits = [b for b in [country, source_type, pub_date] if b]
        meta_line = " · ".join(meta_bits)

        body.append(Paragraph(f"<b>{title}</b>", styles["body"]))
        if citation:
            body.append(Paragraph(citation, styles["body_mono"]))
        if meta_line:
            body.append(Paragraph(meta_line, styles["body_muted"]))
        if url:
            body.append(
                Paragraph(f'<link href="{url}" color="#a06b00">{url}</link>', styles["body_link"])
            )
        body.append(Spacer(1, 3 * mm))

    body.append(Spacer(1, 4 * mm))
    return body


def _build_warnings(simulation: Simulation, labels, styles) -> list[Any]:
    return _build_bullet_section(
        title=labels["section_warnings"],
        items=(simulation.output_data or {}).get("warnings") or [],
        empty_label=labels["no_warnings"],
        styles=styles,
    )


def _build_missing(simulation: Simulation, labels, styles) -> list[Any]:
    return _build_bullet_section(
        title=labels["section_missing"],
        items=(simulation.output_data or {}).get("missing_documents") or [],
        empty_label=labels["no_missing"],
        styles=styles,
    )


def _build_assumptions(simulation: Simulation, labels, styles) -> list[Any]:
    return _build_bullet_section(
        title=labels["section_assumptions"],
        items=(simulation.output_data or {}).get("assumptions") or [],
        empty_label=labels["no_assumptions"],
        styles=styles,
    )


def _build_disclaimer(simulation: Simulation, labels, styles, lang: str) -> list[Any]:
    text = (simulation.output_data or {}).get("legal_disclaimer") or get_disclaimer(lang)
    return [
        Paragraph(labels["section_disclaimer"], styles["h2"]),
        Paragraph(_escape(text), styles["body_disclaimer"]),
        Spacer(1, 6 * mm),
    ]


def _build_cta(simulation: Simulation, labels, styles) -> list[Any]:
    parent_url = "https://international.studiolegalebadrane.it/"
    contact_url = f"/contact/?sim={simulation.public_id}"
    return [
        Paragraph(labels["section_cta"], styles["h2"]),
        Paragraph(_escape(labels["cta_text"]), styles["body"]),
        Spacer(1, 2 * mm),
        Paragraph(
            f"{labels['cta_contact']}: "
            f'<link href="{contact_url}" color="#a06b00">{contact_url}</link>',
            styles["body"],
        ),
        Paragraph(
            f"{labels['cta_parent_site']}: "
            f'<link href="{parent_url}" color="#a06b00">{parent_url}</link>',
            styles["body"],
        ),
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_bullet_section(*, title, items, empty_label, styles) -> list[Any]:
    body: list[Any] = [Paragraph(title, styles["h2"])]
    if not items:
        body.append(Paragraph(empty_label, styles["body_muted"]))
    else:
        for item in items:
            body.append(Paragraph(f"• {_escape(str(item))}", styles["body"]))
    body.append(Spacer(1, 4 * mm))
    return body


def _kv_table(rows, styles) -> Table:
    data = [
        [
            Paragraph(f"<b>{_escape(k)}</b>", styles["body"]),
            Paragraph(_escape(str(v)), styles["body"]),
        ]
        for k, v in rows
    ]
    table = Table(data, colWidths=[55 * mm, None])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e6e2dc")),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _build_styles():
    base = getSampleStyleSheet()
    ink = colors.HexColor("#1f1f1f")
    muted = colors.HexColor("#6b6b6b")
    gold = colors.HexColor("#a06b00")

    return {
        "studio_name": ParagraphStyle(
            "studio_name",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=gold,
            spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=ink,
            leading=26,
            alignment=TA_LEFT,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=ink,
            spaceBefore=2,
            spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=ink,
            spaceBefore=2,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            textColor=ink,
            leading=13,
        ),
        "body_muted": ParagraphStyle(
            "body_muted",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            textColor=muted,
            leading=13,
        ),
        "body_mono": ParagraphStyle(
            "body_mono",
            parent=base["BodyText"],
            fontName="Courier",
            fontSize=9,
            textColor=ink,
            leading=11,
        ),
        "body_link": ParagraphStyle(
            "body_link",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            textColor=gold,
            leading=11,
        ),
        "body_disclaimer": ParagraphStyle(
            "body_disclaimer",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=muted,
            leading=12,
            spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=muted,
            alignment=TA_LEFT,
        ),
    }


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b6b6b"))
    text = f"Studio Legale Internazionale Badrane · Pagina {doc.page}"
    canvas.drawString(18 * mm, 10 * mm, text)
    canvas.restoreState()


def _fmt_amount(amount: Decimal | None, currency: str) -> str:
    if amount is None:
        return "—"
    # Decimal → string. NIENTE locale formatting: vogliamo output stabile
    # per audit (un PDF rigenerato deve corrispondere a quello precedente
    # bit-per-bit nel formato dei numeri).
    return f"{amount} {currency}".strip()


def _escape(text: str) -> str:
    """
    Escape minimo per Paragraph (reportlab interpreta `<>&` come HTML).
    Non sostituiamo `\\n` con `<br/>` di default: chi vuole interruzioni
    le passa esplicite.
    """
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Public re-exports for tests
# ---------------------------------------------------------------------------

__all__ = ["render_simulation_pdf_bytes", "_INPUT_WHITELIST"]
