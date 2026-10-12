"""PDF Utility Toolkit — High-performance, non-destructive PDF manipulation."""

from .config import APP_NAME, APP_VERSION, COPYRIGHT_TEXT
from .services.processor import PDFProcessorService
from .services.storage import StorageManager
from .exceptions import ToolkitError, ValidationError, CorruptedFileError, EncryptionError

__version__ = APP_VERSION
__author__ = "Harsh Patel"
__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "COPYRIGHT_TEXT",
    "PDFProcessorService",
    "StorageManager",
    "ToolkitError",
    "ValidationError",
    "CorruptedFileError",
    "EncryptionError"
]
