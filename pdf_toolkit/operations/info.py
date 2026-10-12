"""PDF Information operation: Deep structural inspection, page metrics, metadata, and text analysis."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import pypdf
import pdfplumber

from ..exceptions import ValidationError, OperationError
from ..security.validation import validate_pdf_file

def inspect_pdf_document(input_path: Path, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Performs deep inspection of a PDF document:
    - Page metrics (dimensions, rotations, orientations)
    - Metadata entries
    - Text presence and extraction statistics (via pdfplumber)
    - Encryption and structure flags
    - Transparent detection of scanned or image-only content
    """
    path = Path(input_path)
    base_info = validate_pdf_file(path, password=password)

    file_size_bytes = path.stat().st_size
    reader = pypdf.PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt(password or "")

    total_pages = len(reader.pages)
    page_details = []
    unique_sizes = set()

    for idx, page in enumerate(reader.pages):
        box = page.mediabox
        w_pt = float(box.width)
        h_pt = float(box.height)
        rot = page.rotation or 0
        orientation = "Landscape" if w_pt > h_pt else "Portrait"
        size_key = f"{round(w_pt, 1)}x{round(h_pt, 1)}"
        unique_sizes.add(size_key)

        page_details.append({
            "page_number": idx + 1,
            "width_pt": round(w_pt, 2),
            "height_pt": round(h_pt, 2),
            "width_in": round(w_pt / 72.0, 2),
            "height_in": round(h_pt / 72.0, 2),
            "width_mm": round(w_pt * 25.4 / 72.0, 1),
            "height_mm": round(h_pt * 25.4 / 72.0, 1),
            "rotation": rot,
            "orientation": orientation
        })

    # Read all raw metadata keys
    raw_meta = reader.metadata or {}
    metadata_dict = {}
    for key, val in raw_meta.items():
        clean_key = str(key).lstrip("/").strip()
        metadata_dict[clean_key] = str(val).strip()

    # Deep text inspection with pdfplumber (sampled for performance if many pages)
    total_characters = 0
    total_words = 0
    pages_with_text = 0
    pages_scanned_or_empty = 0

    try:
        with pdfplumber.open(str(path), password=password or "") as plumber_pdf:
            for p_idx, p in enumerate(plumber_pdf.pages):
                txt = p.extract_text() or ""
                char_count = len(txt)
                word_count = len(txt.split())

                total_characters += char_count
                total_words += word_count

                if char_count > 20:
                    pages_with_text += 1
                else:
                    pages_scanned_or_empty += 1

        is_likely_scanned = (total_characters < 50 and total_pages > 0) or (pages_scanned_or_empty == total_pages)
    except Exception:
        total_characters = 0
        total_words = 0
        is_likely_scanned = False
        pages_with_text = 0
        pages_scanned_or_empty = total_pages

    return {
        "filename": path.name,
        "file_size_bytes": file_size_bytes,
        "file_size_formatted": _format_bytes(file_size_bytes),
        "page_count": total_pages,
        "pdf_version": reader.pdf_header,
        "is_encrypted": reader.is_encrypted,
        "has_mixed_sizes": len(unique_sizes) > 1,
        "metadata": metadata_dict,
        "pages": page_details,
        "text_statistics": {
            "total_characters": total_characters,
            "total_words": total_words,
            "pages_with_extractable_text": pages_with_text,
            "pages_without_text": pages_scanned_or_empty,
            "is_likely_scanned": is_likely_scanned,
            "ocr_applied": False,
            "notice": (
                "Scanned or image-only document detected. Characters cannot be extracted without an OCR engine."
                if is_likely_scanned else
                "Standard selectable text detected."
            )
        }
    }


def _format_bytes(size: int) -> str:
    """Formats raw byte counts into human-readable strings."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024.0
    return f"{size:.1f} TB"
