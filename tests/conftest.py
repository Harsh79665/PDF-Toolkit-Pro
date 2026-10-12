"""Pytest fixtures and synthetic PDF generators."""

import io
from pathlib import Path
import pytest
import pypdf
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from app import app
from pdf_toolkit.services.storage import StorageManager
from pdf_toolkit.services.processor import PDFProcessorService

@pytest.fixture
def test_dirs(tmp_path):
    """Provides temporary directories for uploads and processed assets."""
    uploads = tmp_path / "uploads"
    processed = tmp_path / "processed"
    uploads.mkdir()
    processed.mkdir()
    return {"uploads": uploads, "processed": processed}


@pytest.fixture
def storage_mgr(test_dirs):
    """Provides an isolated StorageManager instance."""
    return StorageManager(uploads_dir=test_dirs["uploads"], processed_dir=test_dirs["processed"])


@pytest.fixture
def processor_svc(storage_mgr):
    """Provides an isolated PDFProcessorService instance."""
    return PDFProcessorService(storage_manager=storage_mgr)


@pytest.fixture
def web_client():
    """Provides Flask test client with testing mode enabled."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_pdf_3pages(tmp_path) -> Path:
    """Creates a genuine 3-page synthetic PDF with metadata and text."""
    pdf_path = tmp_path / "sample_3pages.pdf"
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)

    for i in range(1, 4):
        c.drawString(100, 700, f"Synthetic Test Document — Page {i}")
        c.drawString(100, 650, f"Lorem ipsum paragraph on page {i} for extraction verification.")
        c.showPage()

    c.save()
    packet.seek(0)

    reader = pypdf.PdfReader(packet)
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata({
        "/Title": "Synthetic Test Specimen",
        "/Author": "QA Test Engineer",
        "/Subject": "Automated Testing",
        "/Keywords": "test, synthetic, pypdf"
    })

    with open(pdf_path, "wb") as f:
        writer.write(f)

    return pdf_path


@pytest.fixture
def sample_pdf_1page(tmp_path) -> Path:
    """Creates a 1-page synthetic PDF."""
    pdf_path = tmp_path / "sample_1page.pdf"
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    c.drawString(100, 700, "Single Page Document for Unit Tests")
    c.showPage()
    c.save()
    packet.seek(0)

    with open(pdf_path, "wb") as f:
        f.write(packet.getvalue())

    return pdf_path


@pytest.fixture
def encrypted_pdf(tmp_path) -> Path:
    """Creates an encrypted synthetic PDF protected with password 'testpassword123'."""
    pdf_path = tmp_path / "encrypted_sample.pdf"
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    c.drawString(100, 700, "Secret Protected Content")
    c.showPage()
    c.save()
    packet.seek(0)

    reader = pypdf.PdfReader(packet)
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt("testpassword123")

    with open(pdf_path, "wb") as f:
        writer.write(f)

    return pdf_path


@pytest.fixture
def sample_image(tmp_path) -> Path:
    """Creates a small synthetic PNG image for watermark testing."""
    img_path = tmp_path / "watermark_logo.png"
    img = Image.new("RGBA", (100, 100), color=(37, 99, 235, 180))
    img.save(img_path, format="PNG")
    return img_path


@pytest.fixture
def corrupted_file(tmp_path) -> Path:
    """Creates an invalid non-PDF file."""
    bad_path = tmp_path / "corrupt_file.pdf"
    with open(bad_path, "wb") as f:
        f.write(b"NOT_A_PDF_HEADER_THIS_IS_CORRUPTED_DATA_123456789")
    return bad_path
