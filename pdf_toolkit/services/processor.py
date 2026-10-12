"""Unified PDF Processor Service: Shared by both Flask Web Server and Click CLI."""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import pypdf

from .storage import StorageManager
from ..operations.merge import merge_pdfs
from ..operations.split import split_pdf
from ..operations.rotate import rotate_pdf
from ..operations.watermark import apply_watermark
from ..operations.info import inspect_pdf_document
from ..operations.metadata import sanitize_pdf_metadata
from ..operations.extract import extract_pdf_text
from ..operations.validate import validate_pdf_structure
from ..exceptions import ValidationError, OperationError
from ..logging_config import logger

class PDFProcessorService:
    """
    High-level service orchestrating PDF operations, atomic storage,
    lifecycle management, and consistent response formatting.
    """

    def __init__(self, storage_manager: Optional[StorageManager] = None):
        self.storage = storage_manager or StorageManager()

    def process_merge(
        self,
        input_paths: List[Path],
        passwords: Optional[Dict[str, str]] = None,
        desired_filename: str = "merged_document.pdf",
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes non-destructive merge and saves resulting PDF atomically."""
        start_time = time.time()
        job = job_id or self.storage.create_job_id()

        writer, summary = merge_pdfs(input_paths, passwords=passwords)
        saved_record = self.storage.atomic_save_pdf(
            writer=writer,
            desired_filename=desired_filename,
            operation="merge",
            job_id=job
        )

        duration = round(time.time() - start_time, 3)
        return {
            "success": True,
            "job_id": job,
            "duration_seconds": duration,
            "output": saved_record,
            "summary": summary
        }

    def process_split(
        self,
        input_path: Path,
        mode: str = "all_pages",
        range_expr: Optional[str] = None,
        merge_ranges: bool = False,
        password: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes PDF split and archives multiple outputs into a ZIP if needed."""
        start_time = time.time()
        job = job_id or self.storage.create_job_id()

        outputs, summary = split_pdf(
            input_path=input_path,
            mode=mode,
            range_expr=range_expr,
            merge_ranges=merge_ranges,
            password=password
        )

        if len(outputs) == 1:
            # Single output file generated
            writer, filename = outputs[0]
            saved_record = self.storage.atomic_save_pdf(
                writer=writer,
                desired_filename=filename,
                operation="split",
                job_id=job
            )
            output_records = [saved_record]
            primary_download = saved_record
        else:
            # Multiple outputs generated: save each, then zip them
            output_records = []
            file_paths_for_zip = []

            for idx, (writer, filename) in enumerate(outputs):
                rec = self.storage.atomic_save_pdf(
                    writer=writer,
                    desired_filename=filename,
                    operation="split",
                    job_id=f"{job}_{idx+1}"
                )
                output_records.append(rec)
                f_path, _ = self.storage.get_processed_file(rec["file_id"])
                file_paths_for_zip.append(f_path)

            zip_record = self.storage.create_zip_archive(
                files=file_paths_for_zip,
                archive_name=f"{input_path.stem}_split_pages.zip",
                operation="split",
                job_id=job
            )
            primary_download = zip_record

        duration = round(time.time() - start_time, 3)
        return {
            "success": True,
            "job_id": job,
            "duration_seconds": duration,
            "output": primary_download,
            "all_outputs": output_records,
            "summary": summary
        }

    def process_rotate(
        self,
        input_path: Path,
        angle: int,
        page_selection: str = "all",
        range_expr: Optional[str] = None,
        password: Optional[str] = None,
        desired_filename: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes non-destructive page rotation."""
        start_time = time.time()
        job = job_id or self.storage.create_job_id()

        filename = desired_filename or f"{input_path.stem}_rotated_{angle}deg.pdf"
        writer, summary = rotate_pdf(
            input_path=input_path,
            angle=angle,
            page_selection=page_selection,
            range_expr=range_expr,
            password=password
        )

        saved_record = self.storage.atomic_save_pdf(
            writer=writer,
            desired_filename=filename,
            operation="rotate",
            job_id=job
        )

        duration = round(time.time() - start_time, 3)
        return {
            "success": True,
            "job_id": job,
            "duration_seconds": duration,
            "output": saved_record,
            "summary": summary
        }

    def process_watermark(
        self,
        input_path: Path,
        watermark_type: str = "text",
        text: str = "CONFIDENTIAL",
        font_size: int = 48,
        opacity: float = 0.25,
        color_hex: str = "#2563eb",
        rotation: int = 45,
        placement: str = "center",
        image_path: Optional[Path] = None,
        scale_percent: int = 50,
        page_selection: str = "all",
        range_expr: Optional[str] = None,
        password: Optional[str] = None,
        desired_filename: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes vector text or image watermark application."""
        start_time = time.time()
        job = job_id or self.storage.create_job_id()

        filename = desired_filename or f"{input_path.stem}_watermarked.pdf"
        writer, summary = apply_watermark(
            input_path=input_path,
            watermark_type=watermark_type,
            text=text,
            font_size=font_size,
            opacity=opacity,
            color_hex=color_hex,
            rotation=rotation,
            placement=placement,
            image_path=image_path,
            scale_percent=scale_percent,
            page_selection=page_selection,
            range_expr=range_expr,
            password=password
        )

        saved_record = self.storage.atomic_save_pdf(
            writer=writer,
            desired_filename=filename,
            operation="watermark",
            job_id=job
        )

        duration = round(time.time() - start_time, 3)
        return {
            "success": True,
            "job_id": job,
            "duration_seconds": duration,
            "output": saved_record,
            "summary": summary
        }

    def process_info(self, input_path: Path, password: Optional[str] = None) -> Dict[str, Any]:
        """Inspects document structure and metadata."""
        start_time = time.time()
        details = inspect_pdf_document(input_path, password=password)
        details["duration_seconds"] = round(time.time() - start_time, 3)
        return {"success": True, "data": details}

    def process_sanitize_metadata(
        self,
        input_path: Path,
        action: str = "strip_all",
        custom_fields: Optional[Dict[str, str]] = None,
        password: Optional[str] = None,
        desired_filename: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sanitizes or updates metadata and outputs new PDF."""
        start_time = time.time()
        job = job_id or self.storage.create_job_id()

        filename = desired_filename or f"{input_path.stem}_sanitized.pdf"
        writer, summary = sanitize_pdf_metadata(
            input_path=input_path,
            action=action,
            custom_fields=custom_fields,
            password=password
        )

        saved_record = self.storage.atomic_save_pdf(
            writer=writer,
            desired_filename=filename,
            operation="sanitize_metadata",
            job_id=job
        )

        duration = round(time.time() - start_time, 3)
        return {
            "success": True,
            "job_id": job,
            "duration_seconds": duration,
            "output": saved_record,
            "summary": summary
        }

    def process_extract_text(
        self,
        input_path: Path,
        page_selection: str = "all",
        range_expr: Optional[str] = None,
        password: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extracts text, generates text asset for download, and reports stats."""
        start_time = time.time()
        job = job_id or self.storage.create_job_id()

        extraction = extract_pdf_text(
            input_path=input_path,
            page_selection=page_selection,
            range_expr=range_expr,
            password=password
        )

        # Save downloadable text file
        txt_filename = f"{input_path.stem}_extracted_text.txt"
        saved_record = self.storage.save_text_file(
            content=extraction["full_text"],
            filename=txt_filename,
            operation="extract_text",
            job_id=job
        )

        duration = round(time.time() - start_time, 3)
        return {
            "success": True,
            "job_id": job,
            "duration_seconds": duration,
            "output": saved_record,
            "data": extraction
        }

    def process_validate(self, input_path: Path, password: Optional[str] = None) -> Dict[str, Any]:
        """Validates PDF structure, header, trailer, and parseability."""
        start_time = time.time()
        validation = validate_pdf_structure(input_path, password=password)
        validation["duration_seconds"] = round(time.time() - start_time, 3)
        return {"success": True, "data": validation}
