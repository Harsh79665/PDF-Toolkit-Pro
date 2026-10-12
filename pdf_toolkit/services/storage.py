"""Storage management for temporary uploads, processed outputs, and lifecycle cleanup."""

import os
import time
import uuid
import json
import zipfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import pypdf

from ..config import UPLOADS_DIR, PROCESSED_DIR, FILE_EXPIRATION_HOURS
from ..security.sanitizer import sanitize_filename, sanitize_path
from ..security.validation import validate_pdf_bytes, validate_pdf_file
from ..exceptions import ValidationError, FileNotFoundError, OperationError
from ..logging_config import logger

MANIFEST_FILE = PROCESSED_DIR / "manifest.json"

class StorageManager:
    """Manages file storage, isolated job runs, atomic writes, and asset retention."""

    def __init__(self, uploads_dir: Path = UPLOADS_DIR, processed_dir: Path = PROCESSED_DIR):
        self.uploads_dir = Path(uploads_dir)
        self.processed_dir = Path(processed_dir)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.processed_dir / "manifest.json"
        self._init_manifest()

    def _init_manifest(self) -> None:
        """Initializes the metadata manifest file if absent."""
        if not self.manifest_path.exists():
            try:
                with open(self.manifest_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not initialize manifest: {e}")

    def _read_manifest(self) -> Dict[str, Any]:
        """Reads processed files manifest safely."""
        if not self.manifest_path.exists():
            return {}
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_manifest(self, data: Dict[str, Any]) -> None:
        """Writes processed files manifest atomically."""
        tmp_path = self.manifest_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp_path.replace(self.manifest_path)
        except Exception as e:
            logger.error(f"Failed to update manifest: {e}")
            if tmp_path.exists():
                tmp_path.unlink()

    def create_job_id(self) -> str:
        """Creates a unique job identifier."""
        return uuid.uuid4().hex[:12]

    def save_upload(self, file_storage_or_bytes: Any, filename: str, job_id: Optional[str] = None) -> Path:
        """
        Saves an uploaded file safely within an isolated job directory.
        Performs byte validation before persisting.
        """
        job = job_id or self.create_job_id()
        job_dir = self.uploads_dir / job
        job_dir.mkdir(parents=True, exist_ok=True)

        safe_name = sanitize_filename(filename, fallback="document.pdf")
        destination = job_dir / safe_name

        if hasattr(file_storage_or_bytes, "read"):
            data = file_storage_or_bytes.read()
            if hasattr(file_storage_or_bytes, "seek"):
                file_storage_or_bytes.seek(0)
        elif isinstance(file_storage_or_bytes, bytes):
            data = file_storage_or_bytes
        else:
            raise ValidationError("Unsupported file payload format.")

        # Validate bytes before saving
        validate_pdf_bytes(data, safe_name)

        with open(destination, "wb") as f:
            f.write(data)

        logger.info(f"Saved upload {safe_name} to {destination} (Job: {job})")
        return destination

    def save_image_upload(self, file_storage_or_bytes: Any, filename: str, job_id: Optional[str] = None) -> Path:
        """Saves an image upload safely for watermarking."""
        job = job_id or self.create_job_id()
        job_dir = self.uploads_dir / job
        job_dir.mkdir(parents=True, exist_ok=True)

        safe_name = sanitize_filename(filename, fallback="watermark_image.png")
        destination = job_dir / safe_name

        if hasattr(file_storage_or_bytes, "read"):
            data = file_storage_or_bytes.read()
            if hasattr(file_storage_or_bytes, "seek"):
                file_storage_or_bytes.seek(0)
        elif isinstance(file_storage_or_bytes, bytes):
            data = file_storage_or_bytes
        else:
            raise ValidationError("Unsupported image payload format.")

        with open(destination, "wb") as f:
            f.write(data)

        return destination

    def atomic_save_pdf(
        self,
        writer: pypdf.PdfWriter,
        desired_filename: str,
        operation: str = "general",
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Atomically saves a PdfWriter instance to the processed directory,
        validates the output file is readable, and updates the manifest.
        """
        job = job_id or self.create_job_id()
        file_id = f"{job}_{sanitize_filename(desired_filename, fallback='output.pdf')}"
        safe_output_name = sanitize_filename(desired_filename, fallback="processed.pdf")

        final_path = self.processed_dir / file_id
        temp_path = self.processed_dir / f"{file_id}.tmp"

        try:
            with open(temp_path, "wb") as f:
                writer.write(f)

            # Verification step: ensure output can be reopened and read
            verification = validate_pdf_file(temp_path)
            page_count = verification["page_count"]

            # Atomic move
            temp_path.replace(final_path)

            file_size = final_path.stat().st_size
            created_at = time.time()

            record = {
                "file_id": file_id,
                "display_name": safe_output_name,
                "operation": operation,
                "page_count": page_count,
                "file_size": file_size,
                "created_at": created_at,
                "expires_at": created_at + (FILE_EXPIRATION_HOURS * 3600),
                "is_zip": False
            }

            manifest = self._read_manifest()
            manifest[file_id] = record
            self._write_manifest(manifest)

            logger.info(f"Successfully processed and recorded {file_id} ({operation})")
            return record

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            if final_path.exists():
                final_path.unlink()
            logger.error(f"Failed to atomically save processed PDF: {e}")
            raise OperationError(f"Error finalizing processed PDF: {str(e)}")

    def create_zip_archive(
        self,
        files: List[Path],
        archive_name: str,
        operation: str = "split",
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a zip archive of multiple generated output files."""
        job = job_id or self.create_job_id()
        file_id = f"{job}_{sanitize_filename(archive_name, fallback='archive.zip')}"
        final_path = self.processed_dir / file_id
        temp_path = self.processed_dir / f"{file_id}.tmp"

        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    if file_path.exists():
                        zipf.write(file_path, arcname=file_path.name)

            temp_path.replace(final_path)
            file_size = final_path.stat().st_size
            created_at = time.time()

            record = {
                "file_id": file_id,
                "display_name": sanitize_filename(archive_name, fallback="archive.zip"),
                "operation": operation,
                "page_count": len(files),
                "file_size": file_size,
                "created_at": created_at,
                "expires_at": created_at + (FILE_EXPIRATION_HOURS * 3600),
                "is_zip": True
            }

            manifest = self._read_manifest()
            manifest[file_id] = record
            self._write_manifest(manifest)

            return record

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            if final_path.exists():
                final_path.unlink()
            raise OperationError(f"Failed to create ZIP package: {str(e)}")

    def save_text_file(
        self,
        content: str,
        filename: str,
        operation: str = "extract_text",
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Saves extracted text to a .txt file for download."""
        job = job_id or self.create_job_id()
        file_id = f"{job}_{sanitize_filename(filename, fallback='extracted_text.txt')}"
        final_path = self.processed_dir / file_id

        try:
            with open(final_path, "w", encoding="utf-8") as f:
                f.write(content)

            file_size = final_path.stat().st_size
            created_at = time.time()

            record = {
                "file_id": file_id,
                "display_name": sanitize_filename(filename, fallback="extracted_text.txt"),
                "operation": operation,
                "page_count": 0,
                "file_size": file_size,
                "created_at": created_at,
                "expires_at": created_at + (FILE_EXPIRATION_HOURS * 3600),
                "is_zip": False,
                "is_text": True
            }

            manifest = self._read_manifest()
            manifest[file_id] = record
            self._write_manifest(manifest)

            return record
        except Exception as e:
            raise OperationError(f"Failed to save text asset: {str(e)}")

    def get_processed_file(self, file_id: str) -> tuple[Path, Dict[str, Any]]:
        """Retrieves path and record for a processed file."""
        safe_id = sanitize_filename(file_id)
        file_path = sanitize_path(self.processed_dir, safe_id)

        manifest = self._read_manifest()
        record = manifest.get(safe_id)

        if not file_path.exists():
            # If in manifest but missing on disk, purge from manifest
            if safe_id in manifest:
                del manifest[safe_id]
                self._write_manifest(manifest)
            raise FileNotFoundError(f"File '{file_id}' not found or has expired.")

        if not record:
            # Fallback record
            record = {
                "file_id": safe_id,
                "display_name": safe_id,
                "operation": "unknown",
                "file_size": file_path.stat().st_size,
                "created_at": file_path.stat().st_ctime,
                "is_zip": safe_id.endswith(".zip")
            }

        return file_path, record

    def list_processed_files(self) -> List[Dict[str, Any]]:
        """Lists active processed files sorted by newest first."""
        manifest = self._read_manifest()
        valid_items = []
        updated = False

        for file_id, record in list(manifest.items()):
            file_path = self.processed_dir / file_id
            if file_path.exists():
                valid_items.append(record)
            else:
                del manifest[file_id]
                updated = True

        if updated:
            self._write_manifest(manifest)

        valid_items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return valid_items

    def delete_processed_file(self, file_id: str) -> bool:
        """Safely deletes a processed file and cleans manifest."""
        safe_id = sanitize_filename(file_id)
        file_path = sanitize_path(self.processed_dir, safe_id)

        manifest = self._read_manifest()
        if safe_id in manifest:
            del manifest[safe_id]
            self._write_manifest(manifest)

        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Deleted processed asset {safe_id}")
                return True
            except Exception as e:
                logger.error(f"Error removing file {safe_id}: {e}")
                return False
        return False

    def cleanup_expired(self, max_age_hours: Optional[int] = None) -> int:
        """Removes files older than the retention threshold from uploads and processed dirs."""
        max_age = max_age_hours or FILE_EXPIRATION_HOURS
        threshold = time.time() - (max_age * 3600)
        removed_count = 0

        # Clean processed files
        manifest = self._read_manifest()
        for file_id, record in list(manifest.items()):
            created_at = record.get("created_at", 0)
            if created_at < threshold:
                target = self.processed_dir / file_id
                if target.exists():
                    try:
                        target.unlink()
                        removed_count += 1
                    except Exception:
                        pass
                del manifest[file_id]

        self._write_manifest(manifest)

        # Clean old upload jobs
        if self.uploads_dir.exists():
            for item in self.uploads_dir.iterdir():
                try:
                    if item.stat().st_mtime < threshold:
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink()
                        removed_count += 1
                except Exception:
                    pass

        logger.info(f"Cleanup completed: purged {removed_count} expired files.")
        return removed_count
