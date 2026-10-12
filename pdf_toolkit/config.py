"""Configuration module for PDF Utility Toolkit."""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "processed_pdfs"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Create directories if they do not exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Application Settings
APP_NAME = "PDF Utility Toolkit — Intermediate"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Your Complete PDF Workflow Toolkit — Secure, Accurate, and Non-destructive PDF Processing"
COPYRIGHT_TEXT = "Copyright Reserved. Made by Harsh Patel."

# Security & Processing Constraints
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", 50 * 1024 * 1024))  # 50 MB
ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_PAGES_LIMIT = int(os.environ.get("MAX_PAGES_LIMIT", 500))  # Maximum pages per document
FILE_EXPIRATION_HOURS = int(os.environ.get("FILE_EXPIRATION_HOURS", 24))  # 24-hour cleanup TTL

# Server Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "pdf-toolkit-secure-local-session-key-intermediate-2026")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", 5000))
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")
