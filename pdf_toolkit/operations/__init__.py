"""Operations module initialization."""

from .merge import merge_pdfs
from .split import split_pdf, parse_page_ranges
from .rotate import rotate_pdf
from .watermark import apply_watermark
from .info import inspect_pdf_document
from .metadata import sanitize_pdf_metadata
from .extract import extract_pdf_text
from .validate import validate_pdf_structure

__all__ = [
    "merge_pdfs",
    "split_pdf",
    "parse_page_ranges",
    "rotate_pdf",
    "apply_watermark",
    "inspect_pdf_document",
    "sanitize_pdf_metadata",
    "extract_pdf_text",
    "validate_pdf_structure"
]
