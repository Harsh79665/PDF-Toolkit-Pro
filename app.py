"""Flask Web Application for PDF Utility Toolkit — Intermediate."""

import os
import sys
from pathlib import Path
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    Response
)
from werkzeug.exceptions import RequestEntityTooLarge

from pdf_toolkit.config import (
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    COPYRIGHT_TEXT,
    MAX_CONTENT_LENGTH,
    MAX_PAGES_LIMIT,
    ALLOWED_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    HOST,
    PORT,
    DEBUG,
    SECRET_KEY
)
from pdf_toolkit.services.processor import PDFProcessorService
from pdf_toolkit.services.storage import StorageManager
from pdf_toolkit.exceptions import ToolkitError, ValidationError, FileNotFoundError
from pdf_toolkit.security.sanitizer import sanitize_filename
from pdf_toolkit.security.validation import validate_pdf_file, validate_image_file
from pdf_toolkit.logging_config import logger

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

storage = StorageManager()
processor = PDFProcessorService(storage_manager=storage)


@app.after_request
def set_security_headers(response: Response) -> Response:
    """Sets standard web security headers."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Allow self, inline styles for dynamic theming, and Google Fonts
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "script-src 'self' 'unsafe-inline'; "
        "connect-src 'self';"
    )
    return response


@app.errorhandler(ToolkitError)
def handle_toolkit_error(err: ToolkitError):
    """Handles structured toolkit exceptions gracefully."""
    logger.warning(f"Toolkit error [{err.code}]: {err.message}")
    return jsonify(err.to_dict()), err.status_code


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(err):
    """Handles payload size limit violations."""
    limit_mb = MAX_CONTENT_LENGTH // (1024 * 1024)
    return jsonify({
        "error": True,
        "code": "PAYLOAD_TOO_LARGE",
        "message": f"File exceeds the maximum upload limit of {limit_mb} MB."
    }), 413


@app.errorhandler(404)
def handle_not_found(err):
    return jsonify({
        "error": True,
        "code": "NOT_FOUND",
        "message": "The requested resource was not found."
    }), 404


@app.errorhandler(500)
def handle_server_error(err):
    logger.error(f"Internal server error: {err}")
    return jsonify({
        "error": True,
        "code": "INTERNAL_ERROR",
        "message": "An internal error occurred while processing your request. Please try again."
    }), 500


# --- Views ---

@app.route("/")
def index():
    """Renders the main productivity workspace."""
    # Pre-run expired file cleanup
    try:
        storage.cleanup_expired()
    except Exception:
        pass

    return render_template(
        "index.html",
        app_name=APP_NAME,
        app_version=APP_VERSION,
        app_description=APP_DESCRIPTION,
        copyright_text=COPYRIGHT_TEXT,
        max_upload_mb=MAX_CONTENT_LENGTH // (1024 * 1024),
        max_pages=MAX_PAGES_LIMIT
    )


# --- REST API Endpoints ---

@app.route("/api/upload", methods=["POST"])
def upload_files():
    """
    Accepts one or multiple PDF or image uploads.
    Saves to an isolated session directory and validates file integrity.
    """
    if "files" not in request.files and "image" not in request.files:
        raise ValidationError("No files were attached to the upload request.")

    job_id = storage.create_job_id()
    saved_items = []

    # Handle image upload (for watermark)
    if "image" in request.files:
        image_file = request.files["image"]
        if image_file and image_file.filename:
            img_path = storage.save_image_upload(image_file, image_file.filename, job_id=job_id)
            img_info = validate_image_file(img_path)
            saved_items.append({
                "type": "image",
                "filename": img_path.name,
                "job_id": job_id,
                "width": img_info["width"],
                "height": img_info["height"],
                "format": img_info["format"]
            })

    # Handle PDF files
    uploaded_files = request.files.getlist("files")
    password = request.form.get("password")

    for file_obj in uploaded_files:
        if not file_obj or not file_obj.filename:
            continue

        raw_name = file_obj.filename
        ext = Path(raw_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f"File '{raw_name}' has an unsupported extension. Only .pdf files are accepted.")

        saved_path = storage.save_upload(file_obj, raw_name, job_id=job_id)
        
        # Validate and extract quick metadata
        info = validate_pdf_file(saved_path, password=password)
        saved_items.append({
            "type": "pdf",
            "filename": saved_path.name,
            "original_name": raw_name,
            "job_id": job_id,
            "file_size": info["file_size"],
            "page_count": info["page_count"],
            "is_encrypted": info["is_encrypted"],
            "dimensions": info["first_page_dimensions"],
            "pdf_version": info["pdf_version"],
            "metadata": info["metadata"]
        })

    if not saved_items:
        raise ValidationError("No valid files were successfully processed.")

    return jsonify({
        "success": True,
        "job_id": job_id,
        "files": saved_items
    })


@app.route("/api/process", methods=["POST"])
def process_operation():
    """
    Unified processing endpoint dispatching to the shared service layer.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    operation = data.get("operation")
    job_id = data.get("job_id")
    password = data.get("password")

    if not operation:
        raise ValidationError("Operation type must be specified.")

    if not job_id:
        raise ValidationError("Job ID is required to locate session files.")

    job_dir = storage.uploads_dir / job_id
    if not job_dir.exists():
        raise ValidationError("Upload session expired or not found. Please re-upload your document.")

    # 1. MERGE
    if operation == "merge":
        file_order = data.get("file_order") or []
        if isinstance(file_order, str):
            import json
            try:
                file_order = json.loads(file_order)
            except Exception:
                file_order = [f.strip() for f in file_order.split(",") if f.strip()]

        if not file_order or len(file_order) < 2:
            raise ValidationError("Merge requires at least two PDF files.")

        input_paths = []
        for fn in file_order:
            clean_fn = sanitize_filename(fn)
            p = job_dir / clean_fn
            if not p.is_file():
                raise ValidationError(f"Source file '{clean_fn}' not found in upload session.")
            input_paths.append(p)

        desired_name = data.get("output_filename") or "merged_document.pdf"
        result = processor.process_merge(
            input_paths=input_paths,
            passwords={Path(p).name: password for p in input_paths} if password else None,
            desired_filename=desired_name,
            job_id=job_id
        )
        return jsonify(result)

    # 2. SINGLE-FILE OPERATIONS
    # Locate primary source file
    filename = data.get("filename")
    if not filename:
        # Find first PDF in job directory
        pdf_files = list(job_dir.glob("*.pdf"))
        if not pdf_files:
            raise ValidationError("No PDF file found in session directory.")
        target_path = pdf_files[0]
    else:
        clean_fn = sanitize_filename(filename)
        target_path = job_dir / clean_fn
        if not target_path.is_file():
            raise ValidationError(f"File '{clean_fn}' not found in session.")

    if operation == "split":
        mode = data.get("mode", "all_pages")
        range_expr = data.get("range_expr")
        merge_ranges = str(data.get("merge_ranges", "false")).lower() in ("true", "1")
        result = processor.process_split(
            input_path=target_path,
            mode=mode,
            range_expr=range_expr,
            merge_ranges=merge_ranges,
            password=password,
            job_id=job_id
        )
        return jsonify(result)

    elif operation == "rotate":
        try:
            angle = int(data.get("angle", 90))
        except (ValueError, TypeError):
            raise ValidationError("Angle must be an integer (90, 180, or 270).")

        scope = data.get("scope", "all")
        range_expr = data.get("range_expr")
        result = processor.process_rotate(
            input_path=target_path,
            angle=angle,
            page_selection=scope,
            range_expr=range_expr,
            password=password,
            job_id=job_id
        )
        return jsonify(result)

    elif operation == "watermark":
        wm_type = data.get("watermark_type", "text")
        text = data.get("text", "CONFIDENTIAL")
        try:
            font_size = int(data.get("font_size", 48))
            opacity = float(data.get("opacity", 0.25))
            rotation = int(data.get("rotation", 45))
            scale_percent = int(data.get("scale_percent", 50))
        except (ValueError, TypeError):
            raise ValidationError("Invalid numeric parameter in watermark options.")

        color_hex = data.get("color_hex", "#2563eb")
        placement = data.get("placement", "center")
        scope = data.get("scope", "all")
        range_expr = data.get("range_expr")

        # Handle image watermark path if applicable
        image_path = None
        if wm_type == "image":
            image_name = data.get("image_filename")
            if image_name:
                img_candidate = job_dir / sanitize_filename(image_name)
                if img_candidate.is_file():
                    image_path = img_candidate
            if not image_path:
                # Look for any image in job dir
                for ext in ALLOWED_IMAGE_EXTENSIONS:
                    imgs = list(job_dir.glob(f"*{ext}"))
                    if imgs:
                        image_path = imgs[0]
                        break

        result = processor.process_watermark(
            input_path=target_path,
            watermark_type=wm_type,
            text=text,
            font_size=font_size,
            opacity=opacity,
            color_hex=color_hex,
            rotation=rotation,
            placement=placement,
            image_path=image_path,
            scale_percent=scale_percent,
            page_selection=scope,
            range_expr=range_expr,
            password=password,
            job_id=job_id
        )
        return jsonify(result)

    elif operation == "info":
        result = processor.process_info(target_path, password=password)
        return jsonify(result)

    elif operation == "sanitize_metadata":
        action = data.get("action", "strip_all")
        custom_fields = data.get("custom_fields") or {}
        if isinstance(custom_fields, str):
            import json
            try:
                custom_fields = json.loads(custom_fields)
            except Exception:
                custom_fields = {}

        result = processor.process_sanitize_metadata(
            input_path=target_path,
            action=action,
            custom_fields=custom_fields,
            password=password,
            job_id=job_id
        )
        return jsonify(result)

    elif operation == "extract_text":
        scope = data.get("scope", "all")
        range_expr = data.get("range_expr")
        result = processor.process_extract_text(
            input_path=target_path,
            page_selection=scope,
            range_expr=range_expr,
            password=password,
            job_id=job_id
        )
        return jsonify(result)

    elif operation == "validate":
        result = processor.process_validate(target_path, password=password)
        return jsonify(result)

    else:
        raise ValidationError(f"Unsupported operation '{operation}'.")


@app.route("/api/download/<file_id>")
def download_file(file_id: str):
    """Safely serves a generated PDF, TXT, or ZIP asset."""
    file_path, record = storage.get_processed_file(file_id)
    download_name = record.get("display_name") or file_path.name

    mimetype = "application/pdf"
    if file_path.suffix.lower() == ".zip":
        mimetype = "application/zip"
    elif file_path.suffix.lower() == ".txt":
        mimetype = "text/plain; charset=utf-8"

    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=download_name
    )


@app.route("/api/files", methods=["GET"])
def list_files():
    """Returns active processed files from manifest."""
    files = storage.list_processed_files()
    return jsonify({"success": True, "files": files})


@app.route("/api/delete/<file_id>", methods=["DELETE", "POST"])
def delete_file(file_id: str):
    """Safely deletes a processed asset."""
    success = storage.delete_processed_file(file_id)
    if not success:
        raise FileNotFoundError("Asset could not be found or was already deleted.")
    return jsonify({"success": True, "message": "Asset deleted successfully."})


@app.route("/api/cleanup", methods=["POST"])
def trigger_cleanup():
    """Manual cleanup trigger for expired assets."""
    count = storage.cleanup_expired()
    return jsonify({"success": True, "purged_count": count})


if __name__ == "__main__":
    logger.info(f"Starting {APP_NAME} on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
