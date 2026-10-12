"""PDF Split operation: Splits a PDF into single pages, custom ranges, or extracts selected pages."""

import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pypdf

from ..exceptions import ValidationError, RangeSyntaxError, OperationError
from ..security.validation import validate_pdf_file

def parse_page_ranges(range_string: str, total_pages: int) -> List[List[int]]:
    """
    Parses a page range string such as '1-3, 5, 8-10' into groups of 1-based page indices.
    Returns a list of page lists, e.g., [[1, 2, 3], [5], [8, 9, 10]].
    Raises RangeSyntaxError on invalid tokens or out-of-bounds page numbers.
    """
    if not range_string or not range_string.strip():
        raise RangeSyntaxError("Page range expression cannot be empty.")

    clean_str = range_string.strip()
    # Check for invalid characters
    if not re.match(r"^[0-9,\s\-]+$", clean_str):
        raise RangeSyntaxError(f"Invalid characters in page range '{range_string}'. Only numbers, commas, and hyphens are allowed.")

    parts = [p.strip() for p in clean_str.split(",") if p.strip()]
    if not parts:
        raise RangeSyntaxError("No valid page numbers found in range expression.")

    groups: List[List[int]] = []

    for part in parts:
        if "-" in part:
            sub_parts = [s.strip() for s in part.split("-")]
            if len(sub_parts) != 2 or not sub_parts[0] or not sub_parts[1]:
                raise RangeSyntaxError(f"Malformed range segment '{part}'. Expected format 'start-end' (e.g. 1-3).")
            
            try:
                start = int(sub_parts[0])
                end = int(sub_parts[1])
            except ValueError:
                raise RangeSyntaxError(f"Non-integer value in range segment '{part}'.")

            if start < 1:
                raise RangeSyntaxError(f"Page numbers must be 1 or greater. Found '{start}'.")
            if end < start:
                raise RangeSyntaxError(f"Invalid range '{part}': start page ({start}) cannot be greater than end page ({end}).")
            if end > total_pages:
                raise RangeSyntaxError(f"Page {end} exceeds the document's total page count ({total_pages}).")

            groups.append(list(range(start, end + 1)))
        else:
            try:
                page_num = int(part)
            except ValueError:
                raise RangeSyntaxError(f"Invalid page number '{part}'.")

            if page_num < 1:
                raise RangeSyntaxError(f"Page numbers must be 1 or greater. Found '{page_num}'.")
            if page_num > total_pages:
                raise RangeSyntaxError(f"Page {page_num} exceeds the document's total page count ({total_pages}).")

            groups.append([page_num])

    return groups


def split_pdf(
    input_path: Path,
    mode: str = "all_pages",
    range_expr: Optional[str] = None,
    merge_ranges: bool = False,
    password: Optional[str] = None
) -> Tuple[List[Tuple[pypdf.PdfWriter, str]], Dict[str, Any]]:
    """
    Splits a PDF according to the selected mode:
    - 'all_pages': creates a 1-page PDF for every page in the document.
    - 'custom_ranges': splits according to range_expr into individual files per range group,
                       or if merge_ranges is True, into a single document containing all extracted pages.
    - 'extract_selection': extracts specified pages into a single document.
    
    Returns:
        (list_of_tuples_[(writer, output_filename)], summary_dict)
    """
    path = Path(input_path)
    validate_pdf_file(path, password=password)

    reader = pypdf.PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt(password or "")

    total_pages = len(reader.pages)
    base_stem = path.stem
    outputs: List[Tuple[pypdf.PdfWriter, str]] = []

    try:
        if mode == "all_pages":
            for page_idx in range(total_pages):
                writer = pypdf.PdfWriter()
                writer.add_page(reader.pages[page_idx])
                filename = f"{base_stem}_page_{page_idx + 1}.pdf"
                outputs.append((writer, filename))

            summary = {
                "operation": "split",
                "mode": "all_pages",
                "total_source_pages": total_pages,
                "output_count": len(outputs)
            }

        elif mode in ("custom_ranges", "extract_selection"):
            if not range_expr:
                raise ValidationError("Page range expression must be specified for custom range split.")

            range_groups = parse_page_ranges(range_expr, total_pages)

            if merge_ranges or mode == "extract_selection":
                # Combine all selected pages into a single document
                writer = pypdf.PdfWriter()
                extracted_pages = []
                for group in range_groups:
                    for p in group:
                        # 0-based indexing for reader.pages
                        writer.add_page(reader.pages[p - 1])
                        extracted_pages.append(p)

                filename = f"{base_stem}_extracted.pdf"
                outputs.append((writer, filename))
                summary = {
                    "operation": "split",
                    "mode": mode,
                    "range_expression": range_expr,
                    "pages_extracted": extracted_pages,
                    "total_source_pages": total_pages,
                    "output_count": 1
                }
            else:
                # Each range group becomes a separate PDF document
                for idx, group in enumerate(range_groups):
                    writer = pypdf.PdfWriter()
                    for p in group:
                        writer.add_page(reader.pages[p - 1])

                    if len(group) == 1:
                        filename = f"{base_stem}_page_{group[0]}.pdf"
                    else:
                        filename = f"{base_stem}_pages_{group[0]}-{group[-1]}.pdf"

                    outputs.append((writer, filename))

                summary = {
                    "operation": "split",
                    "mode": "custom_ranges",
                    "range_expression": range_expr,
                    "total_source_pages": total_pages,
                    "output_count": len(outputs)
                }
        else:
            raise ValidationError(f"Unsupported split mode '{mode}'. Choose 'all_pages' or 'custom_ranges'.")

        return outputs, summary

    except (ValidationError, RangeSyntaxError):
        raise
    except Exception as e:
        raise OperationError(f"Split operation failed: {str(e)}")
