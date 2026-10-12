"""Validation routines for PDF and image assets."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import pypdf
from PIL import Image

from ..config import MAX_CONTENT_LENGTH, MAX_PAGES_LIMIT, ALLOWED_IMAGE_EXTENSIONS
from ..exceptions import (
    ValidationError,
    CorruptedFileError,
    EncryptionError,
    StorageLimitError
)

PDF_MAGIC = b"%PDF"

def validate_pdf_bytes(data: bytes, filename: str = "document.pdf") -> None:
    """Verifies that bytes represent a non-empty, valid PDF header."""
    if not data or len(data) == 0:
        raise ValidationError(f"File '{filename}' is empty (0 bytes).")
    
    if len(data) > MAX_CONTENT_LENGTH:
        raise StorageLimitError(f"File '{filename}' exceeds maximum allowed size ({MAX_CONTENT_LENGTH // (1024*1024)} MB).")

    # The PDF specification allows whitespace/comments before %PDF within the first 1024 bytes
    header_chunk = data[:1024]
    if PDF_MAGIC not in header_chunk:
        raise CorruptedFileError(f"File '{filename}' does not contain a valid PDF magic signature.")


def validate_pdf_file(file_path: Path, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Performs comprehensive structural inspection and validation of a PDF file.
    Returns metadata summary or raises appropriate ToolkitError.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ValidationError(f"File not found: {path.name}")

    file_size = path.stat().st_size
    if file_size == 0:
        raise ValidationError(f"File '{path.name}' is empty (0 bytes).")

    if file_size > MAX_CONTENT_LENGTH:
        raise StorageLimitError(f"File '{path.name}' exceeds maximum size limit ({MAX_CONTENT_LENGTH // (1024*1024)} MB).")

    with open(path, "rb") as f:
        header = f.read(1024)
        if PDF_MAGIC not in header:
            raise CorruptedFileError(f"File '{path.name}' does not contain a valid PDF signature.")

    try:
        reader = pypdf.PdfReader(str(path))
        is_encrypted = reader.is_encrypted

        if is_encrypted:
            if password is not None:
                decrypt_success = reader.decrypt(password)
                if not decrypt_success or decrypt_success == pypdf.PasswordType.NOT_DECRYPTED:
                    raise EncryptionError(f"Incorrect password provided for encrypted PDF '{path.name}'.")
            else:
                # Try decrypting with empty password (common for permissions-only encryption)
                try:
                    decrypt_success = reader.decrypt("")
                    if not decrypt_success or decrypt_success == pypdf.PasswordType.NOT_DECRYPTED:
                        raise EncryptionError(f"File '{path.name}' is password protected. Please provide a password.")
                    else:
                        is_encrypted = False
                except Exception:
                    raise EncryptionError(f"File '{path.name}' is password protected. Please provide a password.")

        num_pages = len(reader.pages)
        if num_pages == 0:
            raise CorruptedFileError(f"File '{path.name}' contains no readable pages.")

        if num_pages > MAX_PAGES_LIMIT:
            raise StorageLimitError(f"File '{path.name}' has {num_pages} pages, exceeding the limit of {MAX_PAGES_LIMIT} pages.")

        # Probe first page dimensions
        first_page = reader.pages[0]
        box = first_page.mediabox
        width_pt = float(box.width)
        height_pt = float(box.height)
        rotation = first_page.rotation or 0

        # Extract basic metadata
        metadata = reader.metadata or {}
        doc_info = {
            "title": str(metadata.get("/Title") or "").strip(),
            "author": str(metadata.get("/Author") or "").strip(),
            "subject": str(metadata.get("/Subject") or "").strip(),
            "creator": str(metadata.get("/Creator") or "").strip(),
            "producer": str(metadata.get("/Producer") or "").strip(),
        }

        return {
            "valid": True,
            "filename": path.name,
            "file_size": file_size,
            "page_count": num_pages,
            "is_encrypted": is_encrypted,
            "pdf_version": reader.pdf_header,
            "first_page_dimensions": {
                "width_pt": round(width_pt, 2),
                "height_pt": round(height_pt, 2),
                "width_in": round(width_pt / 72.0, 2),
                "height_in": round(height_pt / 72.0, 2),
                "width_mm": round(width_pt * 25.4 / 72.0, 1),
                "height_mm": round(height_pt * 25.4 / 72.0, 1),
                "orientation": "Landscape" if width_pt > height_pt else "Portrait",
                "rotation": rotation
            },
            "metadata": doc_info
        }

    except (EncryptionError, StorageLimitError, ValidationError, CorruptedFileError):
        raise
    except pypdf.errors.PdfReadError as e:
        raise CorruptedFileError(f"Unable to read PDF '{path.name}': Malformed PDF structure ({str(e)}).")
    except Exception as e:
        raise CorruptedFileError(f"Validation failed for '{path.name}': {str(e)}")


def validate_image_file(file_path: Path) -> Dict[str, Any]:
    """Validates an image file for use as a watermark."""
    path = Path(file_path)
    if not path.is_file():
        raise ValidationError(f"Image not found: {path.name}")

    ext = path.suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Unsupported image format '{ext}'. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")

    try:
        with Image.open(path) as img:
            img.verify()
        # Re-open after verify to get attributes
        with Image.open(path) as img:
            width, height = img.size
            format_name = img.format
            return {
                "valid": True,
                "filename": path.name,
                "width": width,
                "height": height,
                "format": format_name
            }
    except Exception as e:
        raise ValidationError(f"Invalid or corrupted image file: {str(e)}")
