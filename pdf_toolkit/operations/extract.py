"""PDF Text Extraction operation using pdfplumber."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import pdfplumber

from ..exceptions import ValidationError, OperationError
from ..security.validation import validate_pdf_file
from .split import parse_page_ranges

def extract_pdf_text(
    input_path: Path,
    page_selection: str = "all",
    range_expr: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts text from a PDF document using pdfplumber.
    Returns extracted text, page breakdown, statistics, and scan detection warnings.
    """
    path = Path(input_path)
    validate_pdf_file(path, password=password)

    page_results = []
    full_text_parts = []
    total_characters = 0
    total_words = 0
    total_lines = 0

    try:
        with pdfplumber.open(str(path), password=password or "") as pdf:
            total_pages = len(pdf.pages)
            target_pages = set()

            if page_selection == "all":
                target_pages = set(range(1, total_pages + 1))
            elif page_selection == "selected":
                if not range_expr:
                    raise ValidationError("Page range expression is required when page_selection is 'selected'.")
                groups = parse_page_ranges(range_expr, total_pages)
                for g in groups:
                    target_pages.update(g)
            else:
                raise ValidationError(f"Invalid page selection '{page_selection}'. Must be 'all' or 'selected'.")

            for idx, page in enumerate(pdf.pages):
                page_num = idx + 1
                if page_num not in target_pages:
                    continue

                text = page.extract_text() or ""
                lines = [l for l in text.split("\n") if l.strip()]
                words = text.split()

                char_count = len(text)
                word_count = len(words)
                line_count = len(lines)

                total_characters += char_count
                total_words += word_count
                total_lines += line_count

                page_entry = {
                    "page_number": page_num,
                    "text": text,
                    "character_count": char_count,
                    "word_count": word_count,
                    "line_count": line_count,
                    "is_empty": char_count == 0
                }
                page_results.append(page_entry)
                
                if text.strip():
                    full_text_parts.append(f"--- Page {page_num} ---\n{text}\n")
                else:
                    full_text_parts.append(f"--- Page {page_num} ---\n[No extractable text found on this page]\n")

        full_extracted_text = "\n".join(full_text_parts)
        is_scanned = total_characters == 0 or (total_characters < 25 and len(target_pages) > 0)

        warning_message = None
        if is_scanned:
            warning_message = (
                "Scanned or Image-Only Document: No selectable text was found on the evaluated pages. "
                "This document likely consists of rasterized images or scanned scans. "
                "An Optical Character Recognition (OCR) engine would be required to extract text from images."
            )

        return {
            "operation": "extract_text",
            "filename": path.name,
            "total_pages_in_doc": total_pages,
            "pages_extracted_count": len(page_results),
            "total_characters": total_characters,
            "total_words": total_words,
            "total_lines": total_lines,
            "is_scanned": is_scanned,
            "warning": warning_message,
            "full_text": full_extracted_text,
            "pages": page_results
        }

    except ValidationError:
        raise
    except Exception as e:
        raise OperationError(f"Text extraction failed: {str(e)}")
