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
    """Try to parse a date from various formats."""
    date_text = date_text.strip()
    if not date_text:
        return None
    
    # Common date formats
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_text, fmt).date()
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


def parse_docx(file_path: str | Path) -> ImportedAssessment:
    """
    Parse a GMFM assessment DOCX file.
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        ImportedAssessment with parsed data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ImportError: If python-docx is not installed
        Exception: If file can't be parsed as DOCX
    """
    # Lazy import to avoid error on Android
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx is required for DOCX import. This feature is not available on mobile.")
    
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    document = Document(file_path)
    result = ImportedAssessment()
    
    # Parse paragraphs for student info
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        
        # Check for various fields
        if "name" in text.lower() and "evaluator" not in text.lower():
            value = _extract_paragraph_value(text, "Name")
            if value:
                result.student_name = value
                result.given_name, result.family_name = _parse_name(value)
        
        elif "assessment date" in text.lower() or "date" in text.lower()[:10]:
            value = _extract_paragraph_value(text, "Assessment Date")
            if not value:
                value = _extract_paragraph_value(text, "Date")
            if value:
                result.assessment_date = _parse_date(value)
        
        elif "evaluator" in text.lower():
            # Handle "Evaluator's name:" format first (longer match)
            value = _extract_paragraph_value(text, "Evaluator's name")
            if not value:
                value = _extract_paragraph_value(text, "Evaluator")
            
            if value:
                result.evaluator_name = value
    
    # Parse tables for scores
    for table in document.tables:
        for row in table.rows:
            cells = row.cells
            if len(cells) >= 3:
                item_num = _extract_item_number(cells[0].text)
                score = _parse_score(cells[2].text)
                
                if item_num is not None and score is not None:
                    result.raw_scores[item_num] = score
    
    # Add evaluator to notes if present
    if result.evaluator_name:
        result.notes = f"Evaluator: {result.evaluator_name}"
    
    return result


def import_assessment_to_db(
    assessment: ImportedAssessment,
    db_context,
    scale: str = "88"
) -> Tuple[int, int]:
    """
    Import an assessment into the database.
    
    Args:
        assessment: Parsed assessment data
        db_context: Database context for connections
        scale: GMFM scale ("66" or "88")
        
    Returns:
        Tuple of (student_id, session_id)
    """
    import json
    from datetime import datetime
    
    with db_context.connect() as conn:
        cursor = conn.cursor()
        
        # Check if student already exists
        given = assessment.given_name or assessment.student_name.split()[0] if assessment.student_name else "Unknown"
        family = assessment.family_name or (assessment.student_name.split()[-1] if len(assessment.student_name.split()) > 1 else "Student")
        
        cursor.execute(
            "SELECT id FROM students WHERE given_name = ? AND family_name = ?",
            (given, family)
        )
        row = cursor.fetchone()
        
        if row:
            student_id = row[0]
        else:
            # Create new student
            now = datetime.utcnow().isoformat()
            cursor.execute(
                """INSERT INTO students (given_name, family_name, dob, identifier, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (given, family, None, None, now)
            )
            student_id = cursor.lastrowid
        
        # Calculate total score
        if assessment.raw_scores:
            total = sum(assessment.raw_scores.values()) / (len(assessment.raw_scores) * 3) * 100
        else:
            total = 0.0
        
        # Create session
        now = datetime.utcnow().isoformat()
        cursor.execute(
            """INSERT INTO sessions (student_id, scale, raw_scores, total_score, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (student_id, scale, json.dumps(assessment.raw_scores), total, assessment.notes, now)
        )
        session_id = cursor.lastrowid
        
        conn.commit()
        
    return student_id, session_id
