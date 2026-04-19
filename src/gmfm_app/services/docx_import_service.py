"""
DOCX Import Service - Parse GMFM assessment DOCX files

Parses DOCX files formatted like GMFCS.docx and extracts:
- Student information (name, assessment date, evaluator)
- GMFM-88 scores from tables

NOTE: python-docx is imported lazily inside parse_docx() to avoid
import errors on Android where the library may not be available.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass
class ImportedAssessment:
    """Parsed assessment data from a DOCX file."""
    student_name: str = ""
    given_name: str = ""
    family_name: str = ""
    assessment_date: Optional[date] = None
    evaluator_name: str = ""
    raw_scores: Dict[int, int] = field(default_factory=dict)
    notes: str = ""
    
    @property
    def is_valid(self) -> bool:
        """Check if minimum required data is present."""
        return bool(self.student_name or (self.given_name and self.family_name))


def _parse_name(name_text: str) -> Tuple[str, str]:
    """Split a full name into given and family names."""
    name_text = name_text.strip()
    if not name_text:
        return ("", "")
    
    parts = name_text.split()
    if len(parts) == 1:
        return (parts[0], "")
    elif len(parts) == 2:
        return (parts[0], parts[1])
    else:
        # First name is first part, family name is rest
        return (parts[0], " ".join(parts[1:]))


def _parse_date(date_text: str) -> Optional[date]:
    """Try to parse a date from various formats, including month/year only."""
    date_text = date_text.strip()
    if not date_text:
        return None
    
    # Full date formats
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%Y/%m/%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_text, fmt).date()
        except ValueError:
            continue
    
    # Month/year only formats (default to 1st of month)
    month_year_formats = [
        "%B %Y",      # "October 2023"
        "%b %Y",      # "Oct 2023"
        "%m/%Y",      # "10/2023"
        "%Y-%m",      # "2023-10"
        "%Y/%m",      # "2023/10"
        "%m-%Y",      # "10-2023"
    ]
    
    for fmt in month_year_formats:
        try:
            return datetime.strptime(date_text, fmt).date().replace(day=1)
        except ValueError:
            continue
    
    return None


def _parse_score(score_text: str) -> Optional[int]:
    """Parse a score value (0-3) or return None for NT/empty."""
    score_text = score_text.strip().upper()
    
    if not score_text or score_text == "NT":
        return None
    
    try:
        score = int(score_text)
        if 0 <= score <= 3:
            return score
    except ValueError:
        pass
    
    return None


def _extract_item_number(item_text: str) -> Optional[int]:
    """Extract the item number from a table cell."""
    item_text = item_text.strip()
    if not item_text:
        return None
    
    # Match patterns like "1.", "1", "10.", etc.
    match = re.match(r"^(\d+)\.?$", item_text)
    if match:
        return int(match.group(1))
    
    return None


def _extract_paragraph_value(paragraph_text: str, prefix: str) -> str:
    """Extract value after a prefix like 'Name:' or 'Assessment Date:'."""
    if prefix.lower() in paragraph_text.lower():
        # Find the colon and get everything after
        idx = paragraph_text.lower().find(prefix.lower())
        if idx >= 0:
            after = paragraph_text[idx + len(prefix):]
            # Remove any leading colons or semicolons
            after = after.lstrip(":;").strip()
            return after
    return ""


def _iter_block_items(document):
    """Yield Paragraph and Table objects in document order."""
    from docx.table import Table as DocxTable
    from docx.text.paragraph import Paragraph as DocxParagraph
    from docx.oxml.ns import qn

    for child in document.element.body.iterchildren():
        if child.tag == qn('w:p'):
            yield DocxParagraph(child, document)
        elif child.tag == qn('w:tbl'):
            yield DocxTable(child, document)


def parse_docx(file_path: str | Path) -> list:
    """
    Parse a GMFM assessment DOCX file, extracting all sessions.

    A single DOCX may contain multiple assessment sessions for the same
    student (each with its own Assessment Date header).  This function
    returns one ImportedAssessment per session found.

    Args:
        file_path: Path to the DOCX file

    Returns:
        List of ImportedAssessment objects (one per session found)
    """
    # Lazy import to avoid error on Android
    try:
        from docx import Document
        from docx.table import Table as DocxTable
        from docx.text.paragraph import Paragraph as DocxParagraph
    except ImportError:
        raise ImportError("python-docx is required for DOCX import. This feature is not available on mobile.")

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    document = Document(file_path)

    assessments: list = []
    current = ImportedAssessment()
    last_name = ""
    last_evaluator = ""

    def _finalize(assessment: ImportedAssessment):
        """Add notes and append to results if valid."""
        if not assessment.student_name and last_name:
            assessment.student_name = last_name
            assessment.given_name, assessment.family_name = _parse_name(last_name)
        if assessment.evaluator_name and not assessment.notes:
            assessment.notes = f"Evaluator: {assessment.evaluator_name}"
        if assessment.is_valid or assessment.raw_scores:
            assessments.append(assessment)

    for item in _iter_block_items(document):
        if isinstance(item, DocxParagraph):
            text = item.text.strip()
            if not text:
                continue

            # Detect student name
            if "name" in text.lower() and "evaluator" not in text.lower():
                value = _extract_paragraph_value(text, "Name")
                if value:
                    last_name = value
                    if not current.raw_scores:
                        current.student_name = value
                        current.given_name, current.family_name = _parse_name(value)

            # Detect assessment date — a new date after scores signals a new session
            elif "assessment date" in text.lower() or "date" in text.lower()[:10]:
                value = _extract_paragraph_value(text, "Assessment Date")
                if not value:
                    value = _extract_paragraph_value(text, "Date")
                if value:
                    parsed_date = _parse_date(value)
                    if parsed_date is not None:
                        if current.raw_scores:
                            # Finalise previous session, start a new one
                            _finalize(current)
                            current = ImportedAssessment()
                            current.student_name = last_name
                            current.given_name, current.family_name = _parse_name(last_name)
                            current.evaluator_name = last_evaluator
                        current.assessment_date = parsed_date

            # Detect evaluator
            elif "evaluator" in text.lower():
                value = _extract_paragraph_value(text, "Evaluator's name")
                if not value:
                    value = _extract_paragraph_value(text, "Evaluator")
                if value:
                    last_evaluator = value
                    current.evaluator_name = value

        elif isinstance(item, DocxTable):
            for row in item.rows:
                cells = row.cells
                
                # Check for metadata hidden in tables (e.g. headers)
                for cell in cells:
                    text = cell.text.strip()
                    if not text: continue
                    text_lower = text.lower()
                    
                    if "name" in text_lower and "evaluator" not in text_lower:
                        val = _extract_paragraph_value(text, "Name")
                        if val:
                            last_name = val
                            if not current.raw_scores:
                                current.student_name = val
                                current.given_name, current.family_name = _parse_name(val)
                    
                    elif "assessment date" in text_lower or text_lower.startswith("date"):
                        val = _extract_paragraph_value(text, "Assessment Date") or _extract_paragraph_value(text, "Date:") or _extract_paragraph_value(text, "Date")
                        if val:
                            parsed_date = _parse_date(val)
                            if parsed_date:
                                if current.raw_scores:
                                    _finalize(current)
                                    current = ImportedAssessment()
                                    current.student_name = last_name
                                    current.given_name, current.family_name = _parse_name(last_name)
                                    current.evaluator_name = last_evaluator
                                current.assessment_date = parsed_date

                # Check for scores
                if len(cells) >= 3:
                    item_num = _extract_item_number(cells[0].text)
                    score = _parse_score(cells[2].text)
                    # Alternate format fallback
                    if score is None and len(cells) >= 4:
                        score = _parse_score(cells[3].text)
                        
                    if item_num is not None and score is not None:
                        # Bulletproof session split: If we see an item we already scored (like Item #1), 
                        # it's 100% a new repeated session table.
                        if item_num in current.raw_scores:
                            _finalize(current)
                            current = ImportedAssessment()
                            current.student_name = last_name
                            current.given_name, current.family_name = _parse_name(last_name)
                            current.evaluator_name = last_evaluator
                            # We don't have a new date yet, but keep it blank so user can fill it.
                            
                        current.raw_scores[item_num] = score

    # Finalise the last (or only) session
    _finalize(current)

    return assessments if assessments else [ImportedAssessment()]


def import_assessment_to_db(
    assessment: ImportedAssessment,
    db_context,
    scale: str = "88",
    user_id: int = 1
) -> Tuple[int, int]:
    """
    Import an assessment into the database using Repositories to ensure cloud sync.
    
    Args:
        assessment: Parsed assessment data
        db_context: Database context for connections
        scale: GMFM scale ("88")
        user_id: ID of the currently logged-in user
        
    Returns:
        Tuple of (student_id, session_id)
    """
    from gmfm_app.data.models import Student, Session
    from gmfm_app.data.repositories import StudentRepository, SessionRepository
    from datetime import datetime

    student_repo = StudentRepository(db_context, user_id=user_id)
    session_repo = SessionRepository(db_context, user_id=user_id)

    # 1. Deduplicate or Create Student
    given = assessment.given_name or (assessment.student_name.split()[0] if assessment.student_name else "Unknown")
    family = assessment.family_name or (assessment.student_name.split()[-1] if assessment.student_name and len(assessment.student_name.split()) > 1 else "Student")

    # Try to find existing student for this user
    existing_students = student_repo.list_students()
    student_id = None
    for s in existing_students:
        if s.given_name == given and s.family_name == family:
            student_id = s.id
            break
            
    if not student_id:
        now = datetime.utcnow()
        new_student = Student(
            given_name=given,
            family_name=family,
            dob=None,
            identifier=None,
            created_at=now
        )
        created_student = student_repo.create_student(new_student)
        student_id = created_student.id

    # 2. Create Session
    if assessment.raw_scores:
        total = sum(assessment.raw_scores.values()) / (len(assessment.raw_scores) * 3) * 100
    else:
        total = 0.0

    if assessment.assessment_date:
        created = datetime(
            assessment.assessment_date.year,
            assessment.assessment_date.month,
            assessment.assessment_date.day,
        )
    else:
        created = datetime.utcnow()

    new_session = Session(
        student_id=student_id,
        scale=scale,
        raw_scores=assessment.raw_scores,
        total_score=total,
        notes=assessment.notes,
        created_at=created
    )
    created_session = session_repo.create_session(new_session)

    return student_id, created_session.id
