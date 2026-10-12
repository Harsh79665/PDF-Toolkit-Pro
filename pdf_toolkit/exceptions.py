"""Custom exceptions for PDF Utility Toolkit."""

class ToolkitError(Exception):
    """Base exception for all PDF Toolkit operations."""
    def __init__(self, message: str, code: str = "PROCESSING_ERROR", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

    def to_dict(self):
        return {
            "error": True,
            "code": self.code,
            "message": self.message
        }


class ValidationError(ToolkitError):
    """Raised when file or parameter validation fails."""
    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        super().__init__(message, code=code, status_code=400)


class CorruptedFileError(ValidationError):
    """Raised when an uploaded file is not a valid PDF or has corrupted structure."""
    def __init__(self, message: str = "The uploaded file is corrupted or not a valid PDF."):
        super().__init__(message, code="CORRUPTED_FILE")


class EncryptionError(ToolkitError):
    """Raised when an encrypted PDF is supplied without correct password."""
    def __init__(self, message: str = "The PDF is password protected or the provided password is invalid."):
        super().__init__(message, code="ENCRYPTION_ERROR", status_code=401)


class RangeSyntaxError(ValidationError):
    """Raised when page range syntax cannot be parsed or contains invalid pages."""
    def __init__(self, message: str):
        super().__init__(message, code="INVALID_PAGE_RANGE")


class FileNotFoundError(ToolkitError):
    """Raised when a requested file or asset does not exist."""
    def __init__(self, message: str = "The requested file was not found."):
        super().__init__(message, code="FILE_NOT_FOUND", status_code=404)


class StorageLimitError(ToolkitError):
    """Raised when file size or page count exceeds configured limits."""
    def __init__(self, message: str):
        super().__init__(message, code="LIMIT_EXCEEDED", status_code=413)


class OperationError(ToolkitError):
    """Raised when a specific PDF operation encounters an unexpected issue."""
    def __init__(self, message: str, code: str = "OPERATION_FAILED"):
        super().__init__(message, code=code, status_code=500)
