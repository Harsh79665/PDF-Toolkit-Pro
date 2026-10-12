"""PDF Metadata Sanitizer and Editor: Inspects, modifies, or strips document metadata."""

import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import pypdf

from ..exceptions import ValidationError, OperationError
from ..security.validation import validate_pdf_file

SUPPORTED_FIELDS = [
    "title",
    "author",
    "subject",
    "creator",
    "producer",
    "keywords"
]

METADATA_KEY_MAP = {
    "title": "/Title",
    "author": "/Author",
    "subject": "/Subject",
    "creator": "/Creator",
    "producer": "/Producer",
    "keywords": "/Keywords",
    "creation_date": "/CreationDate",
    "mod_date": "/ModDate"
}

DISCLAIMER_WARNING = (
    "SECURITY NOTICE: Removing metadata removes standard document header properties (Title, Author, Producer, etc.). "
    "This does NOT guarantee full forensic sanitization. Digital signatures may be invalidated. "
    "Content-level information such as visible text, annotations, embedded attachments, form fields, "
    "hidden object streams, and revision history remain intact unless individually stripped."
)

def sanitize_pdf_metadata(
    input_path: Path,
    action: str = "strip_all",
    custom_fields: Optional[Dict[str, str]] = None,
    password: Optional[str] = None
) -> tuple[pypdf.PdfWriter, Dict[str, Any]]:
    """
    Sanitizes or modifies document metadata.
    
    action:
      - 'strip_all': Clears all standard metadata entries.
      - 'update': Updates specified fields with provided values; blanks if empty string.
    """
    path = Path(input_path)
    validate_pdf_file(path, password=password)

    reader = pypdf.PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt(password or "")

    original_raw_meta = reader.metadata or {}
    original_meta = {}
    for k, v in original_raw_meta.items():
        original_meta[str(k).lstrip("/")] = str(v)

    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    changes_diff = {}
    new_metadata: Dict[str, str] = {}

    if action == "strip_all":
        # Clear all standard fields by assigning empty strings or omitting
        for field, pdf_key in METADATA_KEY_MAP.items():
            orig_val = original_meta.get(field.title(), original_meta.get(field, ""))
            if orig_val:
                changes_diff[field] = {
                    "original": orig_val,
                    "updated": "[REMOVED]"
                }
            # pypdf removes or sets empty
            new_metadata[pdf_key] = ""

    elif action == "update":
        custom_fields = custom_fields or {}
        for field, new_val in custom_fields.items():
            field_lower = field.lower()
            pdf_key = METADATA_KEY_MAP.get(field_lower)
            if pdf_key:
                orig_val = original_meta.get(field_lower.title(), original_meta.get(field_lower, ""))
                clean_val = str(new_val).strip()
                if orig_val != clean_val:
                    changes_diff[field_lower] = {
                        "original": orig_val or "[NONE]",
                        "updated": clean_val if clean_val else "[REMOVED]"
                    }
                new_metadata[pdf_key] = clean_val

    else:
        raise ValidationError(f"Invalid metadata sanitization action '{action}'. Choose 'strip_all' or 'update'.")

    # Apply new metadata dictionary
    writer.add_metadata(new_metadata)

    summary = {
        "operation": "sanitize_metadata",
        "action": action,
        "original_metadata": original_meta,
        "fields_changed": len(changes_diff),
        "changes": changes_diff,
        "disclaimer": DISCLAIMER_WARNING
    }

    return writer, summary
