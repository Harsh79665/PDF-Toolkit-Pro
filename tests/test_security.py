"""Security tests for filename sanitization, path traversal prevention, and limits."""

import pytest
from pathlib import Path

from pdf_toolkit.security.sanitizer import sanitize_filename, sanitize_path
from pdf_toolkit.security.validation import validate_pdf_bytes, validate_pdf_file
from pdf_toolkit.exceptions import ValidationError, CorruptedFileError, StorageLimitError

def test_sanitize_filename_basic():
    """Verifies that filename is properly sanitized."""
    assert sanitize_filename("Normal Document.pdf") == "Normal_Document.pdf"
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("..\\..\\windows\\system32.pdf") == "system32.pdf"
    assert sanitize_filename("") == "document.pdf"
    assert sanitize_filename(None) == "document.pdf"


def test_sanitize_filename_special_characters():
    """Verifies that shell characters, control characters, and null bytes are neutralized."""
    raw = "test;rm -rf /;`calc.exe`\0.pdf"
    sanitized = sanitize_filename(raw)
    assert ";" not in sanitized
    assert "`" not in sanitized
    assert "\0" not in sanitized
    assert sanitized.endswith(".pdf")


def test_path_traversal_detection(tmp_path):
    """Verifies that attempts to escape base directory raise ValidationError."""
    base_dir = tmp_path / "sandbox"
    base_dir.mkdir()

    # Valid relative subpath
    valid_path = sanitize_path(base_dir, "child.pdf")
    assert valid_path.is_relative_to(base_dir)

    # Path traversal attack
    with pytest.raises(ValidationError) as exc_info:
        sanitize_path(base_dir, "../../../evil.txt")
    assert "Path traversal" in str(exc_info.value)


def test_empty_bytes_validation():
    """Verifies that empty payloads are rejected."""
    with pytest.raises(ValidationError):
        validate_pdf_bytes(b"")


def test_corrupted_header_validation():
    """Verifies that payloads without %PDF header are rejected."""
    with pytest.raises(CorruptedFileError):
        validate_pdf_bytes(b"NOT_A_VALID_PDF_HEADER_CONTENT")


def test_empty_file_validation(tmp_path):
    """Verifies that a 0-byte file on disk is rejected."""
    empty_file = tmp_path / "empty.pdf"
    empty_file.touch()
    with pytest.raises(ValidationError):
        validate_pdf_file(empty_file)
