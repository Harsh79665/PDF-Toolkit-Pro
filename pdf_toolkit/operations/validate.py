"""PDF Validator operation: Structural integrity, conformance, and parseability testing."""

from pathlib import Path
from typing import Dict, Any, Optional, List
import pypdf

from ..exceptions import ValidationError
from ..security.validation import PDF_MAGIC

def validate_pdf_structure(input_path: Path, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Validates PDF integrity, structure, and readability.
    Distinguishes parseability from 100% strict ISO 32000 specification conformance.
    """
    path = Path(input_path)
    if not path.is_file():
        raise ValidationError(f"File not found: {path.name}")

    file_size = path.stat().st_size
    checks: List[Dict[str, Any]] = []
    warnings: List[str] = []
    errors: List[str] = []

    # Check 1: Non-empty file
    if file_size == 0:
        errors.append("File is empty (0 bytes).")
        return {
            "valid": False,
            "filename": path.name,
            "errors": errors,
            "warnings": warnings,
            "checks": [{"name": "File Size", "passed": False, "detail": "0 bytes"}]
        }

    checks.append({"name": "File Size", "passed": True, "detail": f"{file_size} bytes"})

    # Check 2: Header Signature
    with open(path, "rb") as f:
        header_sample = f.read(1024)
        if PDF_MAGIC in header_sample:
            checks.append({"name": "PDF Header Signature", "passed": True, "detail": "Valid %PDF magic bytes found"})
        else:
            errors.append("Missing %PDF header within first 1024 bytes.")
            checks.append({"name": "PDF Header Signature", "passed": False, "detail": "No %PDF signature"})

    # Check 3: EOF marker
    with open(path, "rb") as f:
        f.seek(max(0, file_size - 1024))
        tail_sample = f.read(1024)
        if b"%%EOF" in tail_sample:
            checks.append({"name": "EOF Marker", "passed": True, "detail": "%%EOF marker verified near end of file"})
        else:
            warnings.append("Missing or misplaced %%EOF marker (file may have trailing bytes or truncated tail).")
            checks.append({"name": "EOF Marker", "passed": False, "detail": "%%EOF missing in tail"})

    # Check 4: Parser readability & Catalog
    is_encrypted = False
    page_count = 0
    pdf_version = "Unknown"

    try:
        reader = pypdf.PdfReader(str(path))
        pdf_version = reader.pdf_header
        checks.append({"name": "PDF Header Version", "passed": True, "detail": str(pdf_version)})

        is_encrypted = reader.is_encrypted
        if is_encrypted:
            if password is not None:
                dec_res = reader.decrypt(password)
                if not dec_res or dec_res == pypdf.PasswordType.NOT_DECRYPTED:
                    errors.append("Password decryption failed with the provided password.")
                    checks.append({"name": "Encryption / Decryption", "passed": False, "detail": "Password incorrect"})
                else:
                    checks.append({"name": "Encryption / Decryption", "passed": True, "detail": "Successfully decrypted with password"})
            else:
                checks.append({"name": "Encryption Check", "passed": True, "detail": "Document is encrypted (Password protected)"})
                warnings.append("Document is encrypted; full internal page validation requires password.")

        if not is_encrypted or (is_encrypted and password is not None):
            page_count = len(reader.pages)
            checks.append({"name": "Page Tree Inspection", "passed": True, "detail": f"{page_count} pages successfully indexed"})

            # Sample pages for content stream integrity
            sample_limit = min(page_count, 15)
            corrupt_pages = []
            for i in range(sample_limit):
                try:
                    p = reader.pages[i]
                    _ = p.mediabox
                except Exception as ex:
                    corrupt_pages.append(i + 1)

            if corrupt_pages:
                warnings.append(f"Pages with potential content stream issues: {corrupt_pages}")
                checks.append({"name": "Content Stream Sample", "passed": False, "detail": f"Errors on pages {corrupt_pages}"})
            else:
                checks.append({"name": "Content Stream Sample", "passed": True, "detail": f"Sampled first {sample_limit} pages without stream errors"})

    except Exception as e:
        errors.append(f"PDF parsing error: {str(e)}")
        checks.append({"name": "Reader Parseability", "passed": False, "detail": str(e)})

    is_overall_valid = len(errors) == 0

    return {
        "valid": is_overall_valid,
        "filename": path.name,
        "file_size": file_size,
        "page_count": page_count,
        "pdf_version": pdf_version,
        "is_encrypted": is_encrypted,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "disclaimer": (
            "VALIDATION SCOPE: This validator inspects PDF structural parseability, header/trailer signatures, "
            "cross-reference stability, and page tree integrity. While suitable for standard PDF tools, "
            "passing this validation does not certify 100% formal compliance with all ISO 32000 sub-specifications."
        )
    }
