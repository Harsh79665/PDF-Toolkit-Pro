"""Sanitization utilities for filenames, paths, and user inputs."""

import re
import os
from pathlib import Path
from ..exceptions import ValidationError

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]")

def sanitize_filename(filename: str, max_length: int = 120, fallback: str = "document.pdf") -> str:
    """
    Sanitizes a filename to prevent path traversal, control character injection,
    and filesystem reserved name collisions.
    """
    if not filename or not isinstance(filename, str):
        return fallback

    # Strip null bytes and normalize separators before extracting basename
    filename = filename.replace("\0", "").replace("\\", "/")
    filename = os.path.basename(filename).strip()

    # Split name and extension
    dot_idx = filename.rfind(".")
    if dot_idx > 0:
        stem = filename[:dot_idx]
        ext = filename[dot_idx:].lower()
    else:
        stem = filename
        ext = ""

    # Replace unsafe characters
    clean_stem = _SAFE_FILENAME_RE.sub("_", stem)
    clean_ext = _SAFE_FILENAME_RE.sub("", ext)

    # Collapse repeated underscores
    clean_stem = re.sub(r"_+", "_", clean_stem).strip("._ ")

    if not clean_stem:
        clean_stem = "file"

    if len(clean_stem) > max_length:
        clean_stem = clean_stem[:max_length]

    clean_name = f"{clean_stem}{clean_ext}" if clean_ext else clean_stem
    return clean_name or fallback


def sanitize_path(base_dir: Path, untrusted_path: str | Path) -> Path:
    """
    Resolves untrusted path and ensures it resides strictly inside base_dir.
    Raises ValidationError if path traversal is detected.
    """
    base_dir = Path(base_dir).resolve()
    target = (base_dir / untrusted_path).resolve()

    try:
        # Python 3.9+ is_relative_to
        if not target.is_relative_to(base_dir):
            raise ValidationError("Access denied: Path traversal attempt detected.", code="PATH_TRAVERSAL")
    except AttributeError:
        # Fallback for older python
        try:
            target.relative_to(base_dir)
        except ValueError:
            raise ValidationError("Access denied: Path traversal attempt detected.", code="PATH_TRAVERSAL")

    return target
