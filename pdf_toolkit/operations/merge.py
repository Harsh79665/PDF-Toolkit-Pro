"""PDF Merge operation: Combines multiple PDF documents into a single document."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdf

from ..exceptions import ValidationError, OperationError
from ..security.validation import validate_pdf_file

def merge_pdfs(
    input_paths: List[Path],
    passwords: Optional[Dict[str, str]] = None
) -> tuple[pypdf.PdfWriter, Dict[str, Any]]:
    """
    Merges two or more PDF files in the specified order.
    Preserves original files and validates all inputs.
    
    Returns (writer, summary_dict)
    """
    if not input_paths or len(input_paths) < 2:
        raise ValidationError("Merging requires at least two PDF documents.")

    passwords = passwords or {}
    merger = pypdf.PdfWriter()
    file_summaries = []
    total_pages = 0

    try:
        for idx, file_path in enumerate(input_paths):
            path = Path(file_path)
            pwd = passwords.get(path.name) or passwords.get(str(path))
            
            # Validate input file
            info = validate_pdf_file(path, password=pwd)
            
            reader = pypdf.PdfReader(str(path))
            if reader.is_encrypted:
                reader.decrypt(pwd or "")

            num_pages = len(reader.pages)
            for page in reader.pages:
                merger.add_page(page)

            file_summaries.append({
                "index": idx + 1,
                "filename": path.name,
                "page_count": num_pages,
                "file_size": path.stat().st_size
            })
            total_pages += num_pages

        summary = {
            "operation": "merge",
            "files_merged": len(input_paths),
            "total_pages": total_pages,
            "inputs": file_summaries
        }
        return merger, summary

    except ValidationError:
        raise
    except Exception as e:
        raise OperationError(f"Merge operation failed: {str(e)}")
