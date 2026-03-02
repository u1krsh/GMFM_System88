from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    getSampleStyleSheet = None
    colors = None
    letter = None
    SimpleDocTemplate = None

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

from gmfm_app.data.models import Student, Session
from gmfm_app.scoring.items_catalog import get_domains

DOMAIN_NAMES = {"A": "Lying & Rolling", "B": "Sitting", "C": "Crawling & Kneeling", "D": "Standing", "E": "Walking & Running"}

styles = getSampleStyleSheet() if REPORTLAB_AVAILABLE and getSampleStyleSheet else None


def generate_report(
    student: Student,
    session: Session,
    scoring_result: Dict[str, object],
    output_path: Path,
    trend_chart: Optional[bytes] = None,
) -> Path:
    if REPORTLAB_AVAILABLE:
        return _generate_reportlab(student, session, scoring_result, output_path, trend_chart)
    # Try fpdf2 (pure Python) — may have failed at module-level, try lazy import
    try:
        if FPDF_AVAILABLE:
            return _generate_fpdf2(student, session, scoring_result, output_path)
        else:
            from fpdf import FPDF as _  # noqa: F401
            return _generate_fpdf2(student, session, scoring_result, output_path)
    except Exception:
        pass
    # Zero-dependency raw PDF fallback
    return _generate_raw_pdf(student, session, scoring_result, output_path)


# ---------------------------------------------------------------------------
# fpdf2 implementation (pure Python — works on Android)
# ---------------------------------------------------------------------------

def _generate_fpdf2(
    student: Student,
    session: Session,
    scoring_result: Dict[str, object],
    output_path: Path,
) -> Path:
    output_path = output_path.with_suffix(".pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "GMFM Assessment Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"GMFM-{session.scale} Score Sheet", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    # Separator line
    pdf.set_draw_color(13, 148, 136)  # PRIMARY teal
    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # Student info
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Student Information", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    info_lines = [
        f"Name: {student.given_name} {student.family_name}",
        f"ID / MRN: {student.identifier or '-'}",
        f"Date of Birth: {student.dob.strftime('%B %d, %Y') if student.dob else '-'}",
        f"Assessment Date: {session.created_at.strftime('%B %d, %Y  %H:%M')}",
        f"Scale: GMFM-{session.scale}",
    ]
    for line in info_lines:
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Total score highlight
    total = scoring_result.get("total_percent", 0)
    pdf.set_fill_color(13, 148, 136)  # PRIMARY
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 12, f"  Total Score: {total:.1f}%", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    # Domain summary table
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Domain Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    domains = scoring_result.get("domains", {})
    col_w = [70, 40, 40]
    total_w = sum(col_w)

    # Table header
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(col_w[0], 8, "Domain", border=1, fill=True)
    pdf.cell(col_w[1], 8, "% Score", border=1, fill=True, align="C")
    pdf.cell(col_w[2], 8, "Items", border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    for d_key, d_val in domains.items():
        name = DOMAIN_NAMES.get(d_key, d_key)
        pdf.cell(col_w[0], 7, f"{d_key}: {name}", border=1)
        pdf.cell(col_w[1], 7, f"{d_val.get('percent', 0):.1f}%", border=1, align="C")
        scored = d_val.get("n_items_scored", 0)
        total_items = d_val.get("n_items_total", 0)
        pdf.cell(col_w[2], 7, f"{scored}/{total_items}", border=1, align="C")
        pdf.ln()

    # Total row
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(13, 148, 136)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col_w[0], 8, "TOTAL", border=1, fill=True)
    pdf.cell(col_w[1], 8, f"{total:.1f}%", border=1, fill=True, align="C")
    items_scored = scoring_result.get("items_scored", 0)
    items_total = scoring_result.get("items_total", 0)
    pdf.cell(col_w[2], 8, f"{items_scored}/{items_total}", border=1, fill=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # Detailed item scores per domain
    for domain in get_domains(session.scale):
        pdf.set_font("Helvetica", "B", 11)
        d_name = DOMAIN_NAMES.get(domain.dimension, domain.title)
        pdf.cell(0, 8, f"Dimension {domain.dimension}: {d_name}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        item_col = [18, 95, 12, 12, 12, 12, 12]
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(240, 240, 240)
        for h, w in zip(["#", "Description", "0", "1", "2", "3", "NT"], item_col):
            pdf.cell(w, 6, h, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for item in domain.items:
            # Check if we need a new page
            if pdf.get_y() > 265:
                pdf.add_page()

            pdf.cell(item_col[0], 5, str(item.number), border=1, align="C")
            desc = item.description[:48] + "..." if len(item.description) > 48 else item.description
            pdf.cell(item_col[1], 5, desc, border=1)
            score = session.raw_scores.get(item.number) if session.raw_scores else None
            if score is None:
                score = session.raw_scores.get(str(item.number)) if session.raw_scores else None
            for v in ["0", "1", "2", "3"]:
                mark = "X" if score is not None and str(score) == v else ""
                pdf.cell(item_col[2 + int(v)], 5, mark, border=1, align="C")
            nt_mark = "X" if score is None else ""
            pdf.cell(item_col[6], 5, nt_mark, border=1, align="C")
            pdf.ln()

        pdf.ln(4)

    # Notes
    if session.notes:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Notes", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, session.notes)

    pdf.output(str(output_path))
    return output_path


# ---------------------------------------------------------------------------
# Raw PDF fallback (zero external dependencies — works everywhere)
# Draws real bordered tables, shaded headers, proportional Helvetica text.
# ---------------------------------------------------------------------------

class _PdfPage:
    """Accumulates PDF drawing commands (graphics + text) for one page."""

    # Approximate Helvetica char widths as fraction of font size (not monospaced)
    _CHAR_W = 0.52  # average width of a Helvetica character / font-size

    def __init__(self, page_w: int = 612, page_h: int = 792,
                 margin_l: int = 40, margin_r: int = 40,
                 margin_t: int = 42, margin_b: int = 42):
        self.W = page_w
        self.H = page_h
        self.ML = margin_l
        self.MR = margin_r
        self.MT = margin_t
        self.MB = margin_b
        self.usable_w = page_w - margin_l - margin_r
        self.y = page_h - margin_t  # current cursor (top of next element)
        self._gfx: list[str] = []   # graphics stream parts
        self._txt: list[str] = []   # text stream parts

    @property
    def remaining(self) -> float:
        return self.y - self.MB

    # -- primitives ----------------------------------------------------------

    def _esc(self, s: str) -> str:
        return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    def _rect(self, x, y, w, h, fill_rgb=None, stroke=True):
        if fill_rgb:
            r, g, b = fill_rgb
            self._gfx.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        if stroke:
            self._gfx.append("0 0 0 RG")
            self._gfx.append("0.4 w")
        self._gfx.append(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re")
        if fill_rgb and stroke:
            self._gfx.append("B")   # fill + stroke
        elif fill_rgb:
            self._gfx.append("f")
        else:
            self._gfx.append("S")

    def _text(self, x, y, text, size, bold=False, color_rgb=None):
        font = "/F2" if bold else "/F1"
        self._txt.append("BT")
        if color_rgb:
            r, g, b = color_rgb
            self._txt.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        else:
            self._txt.append("0 0 0 rg")  # always explicit black
        self._txt.append(f"{font} {size} Tf")
        self._txt.append(f"{x:.1f} {y:.1f} Td")
        self._txt.append(f"({self._esc(text)}) Tj")
        self._txt.append("ET")

    def _text_right(self, x_right, y, text, size, bold=False, color_rgb=None):
        tw = len(text) * size * self._CHAR_W
        self._text(x_right - tw, y, text, size, bold, color_rgb=color_rgb)

    def _text_center(self, x_center, y, text, size, bold=False, color_rgb=None):
        tw = len(text) * size * self._CHAR_W
        self._text(x_center - tw / 2, y, text, size, bold, color_rgb=color_rgb)

    # -- high-level helpers --------------------------------------------------

    def text_line(self, text: str, size: int = 10, bold: bool = False,
                  align: str = "L", color_rgb=None):
        """Draw a single line of text at the current cursor, advance y."""
        leading = max(int(size * 1.5), 12)
        if align == "C":
            self._text_center(self.ML + self.usable_w / 2, self.y - size, text, size, bold, color_rgb=color_rgb)
        elif align == "R":
            self._text_right(self.W - self.MR, self.y - size, text, size, bold, color_rgb=color_rgb)
        else:
            self._text(self.ML, self.y - size, text, size, bold, color_rgb=color_rgb)
        self.y -= leading

    def spacer(self, h: float = 6):
        self.y -= h

    def hline(self, color_rgb=(0.05, 0.58, 0.53), thickness: float = 1.0):
        """Draw a horizontal line across the usable width."""
        r, g, b = color_rgb
        self._gfx.append(f"{r:.3f} {g:.3f} {b:.3f} RG")
        self._gfx.append(f"{thickness} w")
        self._gfx.append(f"{self.ML} {self.y:.1f} m {self.W - self.MR:.1f} {self.y:.1f} l S")
        self._gfx.append("0 0 0 RG")
        self.y -= thickness + 3

    def table_row(self, cells: list, col_widths: list, row_h: float = 14,
                  font_size: int = 9, bold: bool = False,
                  fill_rgb=None, aligns: list = None, text_color_rgb=None):
        """Draw one table row with bordered cells."""
        x = self.ML
        cell_y = self.y - row_h
        text_y = cell_y + (row_h - font_size) / 2 + 1  # vertically center text
        pad = 3
        if aligns is None:
            aligns = ["L"] * len(cells)
        for i, (cell_text, cw) in enumerate(zip(cells, col_widths)):
            self._rect(x, cell_y, cw, row_h, fill_rgb=fill_rgb, stroke=True)
            al = aligns[i] if i < len(aligns) else "L"
            if al == "C":
                self._text_center(x + cw / 2, text_y, str(cell_text), font_size, bold, color_rgb=text_color_rgb)
            elif al == "R":
                self._text_right(x + cw - pad, text_y, str(cell_text), font_size, bold, color_rgb=text_color_rgb)
            else:
                self._text(x + pad, text_y, str(cell_text), font_size, bold, color_rgb=text_color_rgb)
            x += cw
        self.y -= row_h

    def filled_banner(self, text: str, size: int = 14, bold: bool = True,
                      fill_rgb=(0.05, 0.58, 0.53), text_rgb=(1, 1, 1)):
        """Full-width colored banner with text (like a total-score bar)."""
        h = size + 10
        self._rect(self.ML, self.y - h, self.usable_w, h, fill_rgb=fill_rgb)
        self._text(self.ML + 6, self.y - h + (h - size) / 2 + 1, text, size, bold, color_rgb=text_rgb)
        self.y -= h + 4

    def stream_bytes(self) -> bytes:
        """Return the combined content stream for this page.
        Graphics are drawn first (rects/lines), then text on top.
        We reset fill color to black before the text section so no
        rectangle fill colour bleeds into text rendering."""
        parts = []
        if self._gfx:
            parts.append("q")  # save graphics state
            parts.extend(self._gfx)
            parts.append("Q")  # restore — clears fill/stroke color changes
        # All text drawn with explicit color
        parts.extend(self._txt)
        combined = "\n".join(parts)
        return combined.encode("latin-1", errors="replace")


def _generate_raw_pdf(
    student: Student,
    session: Session,
    scoring_result: Dict[str, object],
    output_path: Path,
) -> Path:
    """Generate a detailed PDF with proper tables using only Python builtins."""
    output_path = output_path.with_suffix(".pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = scoring_result.get("total_percent", 0)
    domains_data = scoring_result.get("domains", {})
    finished_pages: list[_PdfPage] = []

    def new_page() -> _PdfPage:
        return _PdfPage()

    pg = new_page()

    def ensure_space(need: float):
        """Flush page if not enough vertical room."""
        nonlocal pg
        if pg.remaining < need:
            finished_pages.append(pg)
            pg = new_page()

    # ── Header ────────────────────────────────────────────────────────
    pg.text_line("GROSS MOTOR FUNCTION MEASURE (GMFM)", 16, bold=True, align="C")
    pg.text_line(f"SCORE SHEET  (GMFM-{session.scale})", 12, bold=True, align="C")
    pg.spacer(4)
    pg.hline()
    pg.spacer(2)

    # ── Student info ──────────────────────────────────────────────────
    pg.text_line("Student Information", 12, bold=True)
    pg.spacer(2)
    info = [
        f"Name: {student.given_name} {student.family_name}",
        f"ID#: {student.identifier or '-'}",
        f"Date of Birth: {student.dob.strftime('%Y-%m-%d') if student.dob else '-'}",
        f"Assessment Date: {session.created_at.strftime('%Y-%m-%d')}",
        f"Scale: GMFM-{session.scale}",
        f"Session ID: {session.id}",
    ]
    for line in info:
        pg.text_line(line, 10)
    pg.spacer(6)

    # ── Total score banner ────────────────────────────────────────────
    pg.filled_banner(f"  Total Score: {total:.1f}%", size=14)
    pg.spacer(6)

    # ── Domain Summary Table ──────────────────────────────────────────
    pg.text_line("Domain Summary", 12, bold=True)
    pg.spacer(2)

    sum_cols = [220, 100, 100]  # Domain | % Score | Items
    sum_aligns = ["L", "C", "C"]
    hdr_fill = (0.91, 0.91, 0.91)  # light gray
    pg.table_row(["Domain", "% Score", "Items Scored"], sum_cols, row_h=16,
                 font_size=10, bold=True, fill_rgb=hdr_fill, aligns=sum_aligns)
    for d_key, d_val in domains_data.items():
        name = DOMAIN_NAMES.get(d_key, d_key)
        pct = d_val.get("percent", 0)
        n_scored = d_val.get("n_items_scored", 0)
        n_total = d_val.get("n_items_total", 0)
        pg.table_row(
            [f"{d_key}: {name}", f"{pct:.1f}%", f"{n_scored}/{n_total}"],
            sum_cols, row_h=14, font_size=9, aligns=sum_aligns,
        )
    # Total row
    tot_items_scored = scoring_result.get("items_scored", 0)
    tot_items_total = scoring_result.get("items_total", 0)
    pg.table_row(
        ["TOTAL", f"{total:.1f}%", f"{tot_items_scored}/{tot_items_total}"],
        sum_cols, row_h=16, font_size=10, bold=True,
        fill_rgb=(0.05, 0.58, 0.53), aligns=sum_aligns,
        text_color_rgb=(1, 1, 1),  # white text on teal
    )
    pg.spacer(6)

    # ── Notes ─────────────────────────────────────────────────────────
    if session.notes:
        pg.text_line("Notes", 11, bold=True)
        pg.spacer(2)
        words = session.notes.split()
        line = ""
        for w in words:
            if len(line) + len(w) + 1 > 80:
                pg.text_line(line, 9)
                line = w
            else:
                line = f"{line} {w}" if line else w
        if line:
            pg.text_line(line, 9)
        pg.spacer(4)

    # ── Item Detail — continuous flow with real tables ────────────────
    try:
        domain_list = get_domains(session.scale)
    except Exception:
        domain_list = []

    # Column widths for item table: #, Description, 0, 1, 2, 3, NT
    item_cols = [30, 280, 28, 28, 28, 28, 28]  # total ~450 fits in 532 usable
    item_aligns = ["C", "L", "C", "C", "C", "C", "C"]
    item_hdr = ["#", "Description", "0", "1", "2", "3", "NT"]
    ITEM_ROW_H = 13
    HDR_ROW_H = 15

    for domain_obj in domain_list:
        d_name = DOMAIN_NAMES.get(domain_obj.dimension, domain_obj.title)

        # Need space for: title(18) + gap(4) + header row(15) + at least 3 items(39)
        ensure_space(18 + 4 + HDR_ROW_H + ITEM_ROW_H * 3)

        pg.text_line(f"Dimension {domain_obj.dimension}: {d_name}", 11, bold=True)
        pg.spacer(2)
        pg.table_row(item_hdr, item_cols, row_h=HDR_ROW_H, font_size=8,
                     bold=True, fill_rgb=hdr_fill, aligns=item_aligns)

        for item in domain_obj.items:
            ensure_space(ITEM_ROW_H)

            # If we just started a fresh page, re-print domain header + table header
            if pg.y >= pg.H - pg.MT - 5:
                pg.text_line(f"Dimension {domain_obj.dimension} (cont.)", 10, bold=True)
                pg.spacer(2)
                pg.table_row(item_hdr, item_cols, row_h=HDR_ROW_H, font_size=8,
                             bold=True, fill_rgb=hdr_fill, aligns=item_aligns)

            score = session.raw_scores.get(item.number) if session.raw_scores else None
            if score is None and session.raw_scores:
                score = session.raw_scores.get(str(item.number))
            desc = item.description[:55] + ".." if len(item.description) > 55 else item.description
            c0 = "X" if score is not None and str(score) == "0" else ""
            c1 = "X" if score is not None and str(score) == "1" else ""
            c2 = "X" if score is not None and str(score) == "2" else ""
            c3 = "X" if score is not None and str(score) == "3" else ""
            nt = "X" if score is None else ""
            pg.table_row(
                [str(item.number), desc, c0, c1, c2, c3, nt],
                item_cols, row_h=ITEM_ROW_H, font_size=8, aligns=item_aligns,
            )

        pg.spacer(8)

    # Collect final page
    finished_pages.append(pg)

    # ── Write PDF ─────────────────────────────────────────────────────
    _write_pdf_pages(output_path, finished_pages)
    return output_path


def _write_pdf_pages(path: Path, pages: list) -> None:
    """Assemble finished _PdfPage objects into a valid PDF file."""
    objs: list[bytes] = [b""] * 4  # catalog=1, pages=2, font=3, fontBold=4

    content_ids = []
    page_ids = []

    for pg in pages:
        stream = pg.stream_bytes()
        # content stream object
        cid = len(objs) + 1
        objs.append(
            f"{cid} 0 obj\n".encode()
            + b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
            + stream + b"\nendstream\nendobj\n"
        )
        content_ids.append(cid)
        # page object (placeholder, rewritten below)
        pid = len(objs) + 1
        objs.append(b"placeholder")
        page_ids.append(pid)

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objs[0] = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    objs[1] = f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>\nendobj\n".encode()
    objs[2] = b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    objs[3] = b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n"

    for i, pid in enumerate(page_ids):
        cid = content_ids[i]
        objs[pid - 1] = (
            f"{pid} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            f" /Contents {cid} 0 R"
            f" /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>\n"
            f"endobj\n"
        ).encode()

    header = b"%PDF-1.4\n"
    body = b"".join(objs)
    xref_lines = [f"0 {len(objs) + 1}", "0000000000 65535 f "]
    offset = len(header)
    for obj_data in objs:
        xref_lines.append(f"{offset:010d} 00000 n ")
        offset += len(obj_data)
    xref_offset = len(header) + len(body)
    xref = ("xref\n" + "\n".join(xref_lines) + "\n").encode()
    trailer = (
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    ).encode()
    path.write_bytes(header + body + xref + trailer)


# ---------------------------------------------------------------------------
# reportlab implementation (desktop — needs C extensions)
# ---------------------------------------------------------------------------

def _generate_reportlab(
    student: Student,
    session: Session,
    scoring_result: Dict[str, object],
    output_path: Path,
    trend_chart: Optional[bytes] = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, topMargin=36, bottomMargin=36)
    story = []

    story.append(Paragraph("GROSS MOTOR FUNCTION MEASURE (GMFM)", styles["Title"]))
    story.append(Paragraph("SCORE SHEET (GMFM-88)", styles["Heading2"]))
    story.append(Spacer(1, 6))

    header_lines = [
        f"Student's Name: {student.given_name} {student.family_name}",
        f"ID#: {student.identifier or '—'}",
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
