from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from gmfm_app.data.models import Patient, Session
from gmfm_app.scoring.items_catalog import get_domains

styles = getSampleStyleSheet()


def generate_report(
    patient: Patient,
    session: Session,
    scoring_result: Dict[str, object],
    output_path: Path,
    trend_chart: Optional[bytes] = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, topMargin=36, bottomMargin=36)
    story = []

    story.append(Paragraph("GROSS MOTOR FUNCTION MEASURE (GMFM)", styles["Title"]))
    story.append(Paragraph("SCORE SHEET (GMFM-88 and GMFM-66)", styles["Heading2"]))
    story.append(Spacer(1, 6))

    header_lines = [
        f"Child's Name: {patient.given_name} {patient.family_name}",
        f"ID#: {patient.identifier or '—'}",
        f"Assessment Date: {session.created_at.strftime('%Y-%m-%d')}",
        f"Scale: GMFM-{session.scale}",
        f"Session ID: {session.id}",
        f"Total Score: {scoring_result['total_percent']}%",
    ]
    for line in header_lines:
        story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 12))

    summary_table = _build_summary_table(scoring_result)
    story.append(summary_table)
    story.append(Spacer(1, 12))

    for domain in get_domains(session.scale):
        story.append(Paragraph(f"Item {domain.dimension}: {domain.title}", styles["Heading3"]))
        story.append(_build_domain_table(domain, session.raw_scores))
        story.append(Spacer(1, 6))

    if trend_chart:
        chart_image = Image(io.BytesIO(trend_chart), width=400, height=180)
        story.append(Spacer(1, 12))
        story.append(chart_image)

    doc.build(story)
    return output_path


def _build_domain_table(domain, raw_scores: Dict[int, int]) -> Table:
    data = [["Item", "Description", "0", "1", "2", "3", "NT"]]
    for item in domain.items:
        row = [item.number, item.description, "", "", "", "", ""]
        if item.number in raw_scores:
            score = int(raw_scores[item.number])
            index = max(0, min(3, score)) + 2
            row[index] = "X"
        else:
            row[-1] = "X"
        data.append(row)
    table = Table(data, colWidths=[30, 250, 30, 30, 30, 30, 30])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    return table


def _build_summary_table(result: Dict[str, object]) -> Table:
    data = [["Dimension", "% Score", "Items Scored"]]
    for domain, payload in result.get("domains", {}).items():
        data.append(
            [
                domain,
                f"{payload['percent']:.1f}",
                f"{payload['n_items_scored']}/{payload['n_items_total']}",
            ]
        )
    data.append(["Total", f"{result['total_percent']:.1f}", f"{result['items_scored']}/{result['items_total']}"])
    table = Table(data, colWidths=[200, 80, 120])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ]
        )
    )
    return table
