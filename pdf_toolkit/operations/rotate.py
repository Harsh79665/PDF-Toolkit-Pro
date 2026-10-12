"""PDF Rotate operation: Non-destructive page rotation by 90, 180, or 270 degrees clockwise."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdf

from ..exceptions import ValidationError, OperationError
from ..security.validation import validate_pdf_file
from .split import parse_page_ranges

VALID_ANGLES = {90, 180, 270}

def rotate_pdf(
    input_path: Path,
    angle: int,
    page_selection: str = "all",
    range_expr: Optional[str] = None,
    password: Optional[str] = None
) -> tuple[pypdf.PdfWriter, Dict[str, Any]]:
    """
    Rotates all or selected pages in a PDF document by angle (90, 180, 270 degrees clockwise).
    Preserves text content and vector graphics without rasterization.
    """
    if angle not in VALID_ANGLES:
        raise ValidationError(f"Invalid rotation angle {angle}°. Must be one of: 90, 180, or 270 degrees.")

    path = Path(input_path)
    validate_pdf_file(path, password=password)

    reader = pypdf.PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt(password or "")

    total_pages = len(reader.pages)
    target_pages_1based = set()

    if page_selection == "all":
        target_pages_1based = set(range(1, total_pages + 1))
    elif page_selection == "selected":
        if not range_expr:
            raise ValidationError("Please provide a page range expression (e.g., '1,3,5' or '2-4') for selected page rotation.")
        range_groups = parse_page_ranges(range_expr, total_pages)
        for group in range_groups:
            target_pages_1based.update(group)
    else:
        raise ValidationError(f"Unsupported page selection mode '{page_selection}'. Must be 'all' or 'selected'.")

    writer = pypdf.PdfWriter()
    rotated_pages = []

    try:
        for idx in range(total_pages):
            page = reader.pages[idx]
            page_num_1based = idx + 1

            if page_num_1based in target_pages_1based:
                # Rotate clockwise non-destructively
                page.rotate(angle)
                rotated_pages.append(page_num_1based)

            writer.add_page(page)

        summary = {
            "operation": "rotate",
            "angle": angle,
            "page_selection": page_selection,
            "total_pages": total_pages,
            "pages_rotated": sorted(list(rotated_pages)),
            "count_rotated": len(rotated_pages)
        }

        return writer, summary

    except Exception as e:
        raise OperationError(f"Rotation operation failed: {str(e)}")
