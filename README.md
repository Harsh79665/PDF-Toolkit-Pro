# PDF Utility Toolkit — Intermediate

> **“Authored a CLI PDF manipulation toolkit executing non-destructive page transformations, merges, and watermarking, extended with a responsive web interface built using Python, HTML, CSS, and vanilla JavaScript.”**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: Pytest](https://img.shields.io/badge/tests-37%20passed-brightgreen.svg)](https://pytest.org/)

---

## Overview

**PDF Utility Toolkit — Intermediate** is a production-ready, full-stack document processing application designed to automate office document workflows through secure, accurate, and non-destructive PDF manipulation. 

Backed by a high-performance Python engine, the toolkit provides both a modern SaaS browser interface and a Click-powered command-line interface (CLI) sharing the identical service layer. All processing occurs locally within the Python runtime with **zero external third-party cloud uploads or telemetry leaks**.

### Exact Copyright Ownership
**“Copyright Reserved. Made by Harsh Patel.”**

---

## Core Capabilities & Implemented Tools

1. **Merge PDF**: Combine two or more PDF documents with custom ordering (accessible Move Up / Move Down controls). Validates every input, prevents collisions, and tracks cumulative page counts.
2. **Split PDF**: Split documents into individual single-page files, custom page ranges (e.g., `1-3, 5, 8-10`), or extract selected pages into a single combined document. Supports direct downloads and packaged ZIP archives.
3. **Rotate PDF**: Rotate all or selected pages clockwise by 90°, 180°, or 270°. Non-destructive transformation preserving selectable text and vector shapes without rasterization.
4. **Watermark PDF**: Apply high-fidelity vector text watermarks (ReportLab transparent overlay with custom font size, opacity, rotation angle, hex colors, and positions) or branded image watermarks (Pillow/PNG/JPG). Includes interactive live browser preview.
5. **PDF Information**: Deep structural analysis reporting page count, page dimensions (points, inches, millimeters), rotations, encryption status, PDF version, metadata properties, and text density statistics via `pdfplumber`. Detects scanned/image-only documents transparently.
6. **Metadata Sanitizer**: Strip all metadata or replace specific fields (Title, Author, Subject, Keywords). Provides detailed before/after diffs and transparent privacy warnings regarding digital signatures and visible page content.
7. **PDF Text Extractor**: Extract selectable text character streams using `pdfplumber`. Includes instant in-browser viewer, word/character counts, copy-to-clipboard, and clean `.txt` asset download.
8. **PDF Validator**: Multi-stage structural validation checking `%PDF` magic bytes, `%%EOF` trailer markers, catalog nodes, and cross-reference stream readability.
9. **Processed Files & History**: Dedicated storage management tracking generated files, output sizes, page counts, creation timestamps, and automatic 24-hour expiration cleanup with manual deletion controls.
10. **Command-Line Interface (CLI)**: Full Click CLI parity implementing `merge`, `split`, `rotate`, `watermark`, `info`, `sanitize-metadata`, `extract-text`, `validate`, and `version`.

---

## Technology Stack

Strictly adhering to permitted languages: **Python, HTML, CSS, and Vanilla JavaScript**.

- **Backend**: Python 3.9+ (Flask 3.x web server)
- **PDF Core Engines**: `pypdf` 6.x, `pdfplumber` 0.11.x, `reportlab` 4.x/5.x, `pillow` 10.x+
- **CLI Framework**: `Click` 8.x
- **Testing**: `pytest` 8.x (37 automated tests covering operations, security, CLI, and API)
- **Frontend Architecture**:
  - Semantic HTML5 with accessible ARIA attributes
  - Custom Vanilla CSS3 design system with CSS custom properties (tokens)
  - Capsule-style Dark & Light mode toggle switch with `localStorage` persistence and FOUT prevention
  - Vanilla JavaScript ES6+ (Zero external libraries or Node.js frameworks)

---

## Project Structure

```text
PDF Toolkit Pro/
├── app.py                      # Flask application entry point & REST endpoints
├── pdf_toolkit/                # Reusable Python processing package
│   ├── __init__.py             # Package exports & metadata
│   ├── config.py               # Paths, storage limits, and environment settings
│   ├── exceptions.py           # Structured toolkit exceptions
│   ├── logging_config.py       # Safe logging setup
│   ├── cli.py                  # Click command-line interface
│   ├── operations/             # Pure PDF manipulation operations
│   │   ├── __init__.py
│   │   ├── merge.py            # PDF document merging
│   │   ├── split.py            # Splitting & range parsing (e.g. 1-3,5)
│   │   ├── rotate.py           # 90/180/270 degree rotation
│   │   ├── watermark.py        # Vector text & image watermark overlays
│   │   ├── info.py             # Document inspection & metrics
│   │   ├── metadata.py         # Metadata editing & sanitization
│   │   ├── extract.py          # pdfplumber text extraction
│   │   └── validate.py         # Conformance & integrity checks
│   ├── security/               # Validation & path safety
│   │   ├── __init__.py
│   │   ├── sanitizer.py        # Filename sanitization & path traversal guards
│   │   └── validation.py       # Magic byte & structure validators
│   └── services/               # Shared orchestration services
│       ├── __init__.py
│       ├── storage.py          # Atomic writes, manifest tracking & cleanup
│       └── processor.py        # Shared PDFProcessorService layer
├── templates/
│   └── index.html              # HTML5 application interface
├── static/
│   ├── css/
│   │   └── style.css           # Modern SaaS stylesheet & design system
│   ├── js/
│   │   └── app.js              # Vanilla JavaScript frontend engine
│   └── images/
│       ├── logo.svg            # Application vector logo
│       └── favicon.svg         # Application vector favicon
├── tests/                      # Automated pytest suite (37 tests)
│   ├── __init__.py
│   ├── conftest.py             # Synthetic PDF fixtures & test client
│   ├── test_operations.py      # Operations unit tests
│   ├── test_security.py        # Path traversal & sanitization tests
│   ├── test_cli.py             # Click CLI integration tests
│   └── test_web_api.py         # Flask REST API tests
├── uploads/                    # Temporary session upload directory
├── processed_pdfs/             # Temporary processed assets directory
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Build & packaging configuration
├── .env.example                # Documented environment variable template
├── .gitignore                  # Git ignore rules
└── README.md                   # Complete documentation
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.9 or higher installed on your system.

### 2. Set Up Virtual Environment (Recommended)
```bash
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment (Optional)
Copy `.env.example` to `.env` to customize settings:
```bash
copy .env.example .env
```

---

## Running the Web Application

To launch the local web server:
```bash
python app.py
```
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## Command-Line Interface (CLI) Usage

The Click CLI provides direct access to all operations using the same processing services.

### Help & Version
```bash
python -m pdf_toolkit.cli --help
python -m pdf_toolkit.cli version
```

### 1. Merge Documents
```bash
python -m pdf_toolkit.cli merge doc1.pdf doc2.pdf doc3.pdf -o merged_output.pdf
```

### 2. Split Document
```bash
# Split every page into separate files
python -m pdf_toolkit.cli split document.pdf -m all_pages -o ./split_pages

# Split into custom ranges
python -m pdf_toolkit.cli split document.pdf -m custom_ranges -r "1-3, 5, 8-10" -o ./ranges

# Extract selection into a single combined file
python -m pdf_toolkit.cli split document.pdf -m extract_selection -r "1, 3, 5" -o ./extracted
```

### 3. Rotate Pages
```bash
# Rotate all pages clockwise by 90 degrees
python -m pdf_toolkit.cli rotate document.pdf -a 90 -o rotated.pdf

# Rotate only specific pages
python -m pdf_toolkit.cli rotate document.pdf -a 180 -s selected -r "2, 4" -o rotated_p2_p4.pdf
```

### 4. Watermark Document
```bash
# Vector text watermark
python -m pdf_toolkit.cli watermark document.pdf -t "CONFIDENTIAL" --color "#dc2626" --opacity 0.25 -o watermarked.pdf

# Branded image logo watermark
python -m pdf_toolkit.cli watermark document.pdf -i logo.png --opacity 0.35 -o branded.pdf
```

### 5. Inspect Document Information
```bash
python -m pdf_toolkit.cli info document.pdf

# Output machine-readable JSON
python -m pdf_toolkit.cli info document.pdf --json-out
```

### 6. Sanitize Metadata
```bash
# Strip all standard metadata properties
python -m pdf_toolkit.cli sanitize-metadata document.pdf -a strip_all -o sanitized.pdf

# Replace with custom fields
python -m pdf_toolkit.cli sanitize-metadata document.pdf -a update --title "Quarterly Report" --author "Finance Team" -o updated.pdf
```

### 7. Extract Text
```bash
# Extract and preview in terminal
python -m pdf_toolkit.cli extract-text document.pdf

# Extract and save to a .txt file
python -m pdf_toolkit.cli extract-text document.pdf -o extracted_content.txt
```

### 8. Validate Document
```bash
python -m pdf_toolkit.cli validate document.pdf
```

---

## Running Automated Tests

Run the full pytest suite:
```bash
python -m pytest -v
```

All 37 tests verify:
- Merge ordering and page counts
- Splitting modes and range syntax edge cases
- 90°, 180°, and 270° clockwise rotations
- Vector text watermarks and PNG image watermarks
- Metadata extraction, stripping, and updating
- Text extraction accuracy via `pdfplumber`
- Structural integrity checking for corrupted files
- Password-protected document decipherability
- Path traversal rejection (`../../etc/passwd`)
- Filename sanitization and 0-byte upload rejection
- CLI subcommands via `click.testing.CliRunner`
- Flask REST API routes, downloads, and safe asset deletion

---

## Security, Privacy & Integrity Disclosures

1. **Local Execution**: All PDF transformations, parsing, and watermarking execute exclusively on the host server. No external network requests or third-party web services are called.
2. **Non-Destructive Processing**: Original input files are never overwritten in place. Output files are written to isolated temporary files, verified to be reopenable, and atomically moved into destination storage.
3. **Forensic Sanitization Scope**: Removing metadata removes standard document header properties (Title, Author, Producer, ModDate). It does **not** constitute complete forensic redaction; digital signatures may be broken, and content text, annotations, attachments, and form fields remain intact unless manually redacted.
4. **Scanned Documents & OCR**: The text extraction engine extracts true digital text streams. Scanned raster documents without OCR text layers are transparently identified and reported with an explanatory notice.
5. **Temporary File Retention**: Uploaded and processed assets are purged automatically after 24 hours. Users can immediately delete generated files via the web interface.

---

## License & Authorship

Authored by **Harsh Patel**.  
**“Copyright Reserved. Made by Harsh Patel.”**  
Released under the MIT License.
