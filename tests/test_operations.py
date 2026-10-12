"""Unit tests for core PDF operations."""

import io
from pathlib import Path
import pytest
import pypdf

from pdf_toolkit.operations.merge import merge_pdfs
from pdf_toolkit.operations.split import split_pdf, parse_page_ranges
from pdf_toolkit.operations.rotate import rotate_pdf
from pdf_toolkit.operations.watermark import apply_watermark
from pdf_toolkit.operations.info import inspect_pdf_document
from pdf_toolkit.operations.metadata import sanitize_pdf_metadata
from pdf_toolkit.operations.extract import extract_pdf_text
from pdf_toolkit.operations.validate import validate_pdf_structure
from pdf_toolkit.exceptions import ValidationError, RangeSyntaxError, EncryptionError

def test_merge_pdfs(sample_pdf_3pages, sample_pdf_1page):
    """Verifies that merging two documents preserves order and produces correct total pages."""
    writer, summary = merge_pdfs([sample_pdf_3pages, sample_pdf_1page])
    assert summary["files_merged"] == 2
    assert summary["total_pages"] == 4
    assert len(writer.pages) == 4


def test_merge_requires_at_least_two_files(sample_pdf_1page):
    """Verifies that merge rejects a single file."""
    with pytest.raises(ValidationError):
        merge_pdfs([sample_pdf_1page])


def test_split_all_pages(sample_pdf_3pages):
    """Verifies splitting a 3-page document into individual 1-page files."""
    outputs, summary = split_pdf(sample_pdf_3pages, mode="all_pages")
    assert summary["output_count"] == 3
    assert len(outputs) == 3
    for writer, filename in outputs:
        assert len(writer.pages) == 1
        assert filename.endswith(".pdf")


def test_split_custom_ranges(sample_pdf_3pages):
    """Verifies splitting with range expressions like '1-2, 3'."""
    outputs, summary = split_pdf(sample_pdf_3pages, mode="custom_ranges", range_expr="1-2, 3")
    assert summary["output_count"] == 2
    assert len(outputs[0][0].pages) == 2
    assert len(outputs[1][0].pages) == 1


def test_split_extract_selection(sample_pdf_3pages):
    """Verifies extracting specific pages into a single document."""
    outputs, summary = split_pdf(sample_pdf_3pages, mode="extract_selection", range_expr="1, 3")
    assert summary["output_count"] == 1
    assert len(outputs[0][0].pages) == 2


def test_split_invalid_syntax(sample_pdf_3pages):
    """Verifies that malformed range expressions raise RangeSyntaxError."""
    with pytest.raises(RangeSyntaxError):
        parse_page_ranges("invalid_range", total_pages=3)
    with pytest.raises(RangeSyntaxError):
        parse_page_ranges("5-10", total_pages=3)  # Out of range
    with pytest.raises(RangeSyntaxError):
        parse_page_ranges("3-1", total_pages=3)   # Start > End


def test_rotate_pdf_all_pages(sample_pdf_3pages):
    """Verifies non-destructive 90 degree clockwise rotation on all pages."""
    writer, summary = rotate_pdf(sample_pdf_3pages, angle=90, page_selection="all")
    assert summary["angle"] == 90
    assert summary["count_rotated"] == 3
    assert writer.pages[0].rotation == 90


def test_rotate_pdf_selected_pages(sample_pdf_3pages):
    """Verifies rotating only page 2."""
    writer, summary = rotate_pdf(sample_pdf_3pages, angle=180, page_selection="selected", range_expr="2")
    assert summary["count_rotated"] == 1
    assert writer.pages[0].rotation == 0
    assert writer.pages[1].rotation == 180
    assert writer.pages[2].rotation == 0


def test_apply_text_watermark(sample_pdf_3pages):
    """Verifies vector text watermark application."""
    writer, summary = apply_watermark(
        sample_pdf_3pages,
        watermark_type="text",
        text="TEST WATERMARK",
        font_size=36,
        opacity=0.3,
        color_hex="#ff0000"
    )
    assert summary["pages_watermarked"] == 3
    assert len(writer.pages) == 3


def test_apply_image_watermark(sample_pdf_3pages, sample_image):
    """Verifies image logo watermark application."""
    writer, summary = apply_watermark(
        sample_pdf_3pages,
        watermark_type="image",
        image_path=sample_image,
        opacity=0.4,
        scale_percent=40
    )
    assert summary["pages_watermarked"] == 3
    assert len(writer.pages) == 3


def test_inspect_pdf_document(sample_pdf_3pages):
    """Verifies deep inspection of page metrics, metadata, and text analysis."""
    info = inspect_pdf_document(sample_pdf_3pages)
    assert info["page_count"] == 3
    assert info["is_encrypted"] is False
    assert "Title" in info["metadata"]
    assert info["text_statistics"]["total_characters"] > 0


def test_sanitize_metadata_strip_all(sample_pdf_3pages):
    """Verifies complete metadata stripping."""
    writer, summary = sanitize_pdf_metadata(sample_pdf_3pages, action="strip_all")
    assert summary["fields_changed"] >= 1
    # Save to buffer and re-inspect
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    reader = pypdf.PdfReader(buf)
    meta = reader.metadata or {}
    assert meta.get("/Title") in (None, "")


def test_sanitize_metadata_update(sample_pdf_3pages):
    """Verifies updating specific metadata fields."""
    writer, summary = sanitize_pdf_metadata(
        sample_pdf_3pages,
        action="update",
        custom_fields={"title": "Updated Title", "author": "New Author"}
    )
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    reader = pypdf.PdfReader(buf)
    assert reader.metadata.get("/Title") == "Updated Title"
    assert reader.metadata.get("/Author") == "New Author"


def test_extract_pdf_text(sample_pdf_3pages):
    """Verifies text extraction using pdfplumber."""
    extracted = extract_pdf_text(sample_pdf_3pages)
    assert extracted["total_characters"] > 0
    assert extracted["total_words"] > 0
    assert "Lorem ipsum" in extracted["full_text"]
    assert extracted["is_scanned"] is False


def test_validate_pdf_structure(sample_pdf_3pages, corrupted_file):
    """Verifies structural validator distinguishes valid from corrupted documents."""
    valid_res = validate_pdf_structure(sample_pdf_3pages)
    assert valid_res["valid"] is True
    assert len(valid_res["errors"]) == 0

    invalid_res = validate_pdf_structure(corrupted_file)
    assert invalid_res["valid"] is False
    assert len(invalid_res["errors"]) > 0


def test_encrypted_pdf_handling(encrypted_pdf):
    """Verifies password validation for encrypted files."""
    # Fails without password
    with pytest.raises(EncryptionError):
        inspect_pdf_document(encrypted_pdf)

    # Succeeds with correct password
    info = inspect_pdf_document(encrypted_pdf, password="testpassword123")
    assert info["page_count"] == 1
