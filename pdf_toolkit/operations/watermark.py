"""PDF Watermark operation: Vector text and image watermark overlays using ReportLab and pypdf."""

import io
import math
from pathlib import Path
from typing import Dict, Any, Optional, List
import pypdf
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

from ..exceptions import ValidationError, OperationError
from ..security.validation import validate_pdf_file, validate_image_file
from .split import parse_page_ranges

def _hex_to_rgb(hex_code: str) -> tuple[float, float, float]:
    """Converts a hex color (#RRGGBB) to 0.0-1.0 RGB tuple."""
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join([c * 2 for c in hex_code])
    if len(hex_code) != 6:
        return (0.5, 0.5, 0.5)
    r = int(hex_code[0:2], 16) / 255.0
    g = int(hex_code[2:4], 16) / 255.0
    b = int(hex_code[4:6], 16) / 255.0
    return (r, g, b)


def _create_text_watermark_page(
    width: float,
    height: float,
    text: str,
    font_size: int = 48,
    opacity: float = 0.25,
    color_hex: str = "#2563eb",
    rotation: int = 45,
    placement: str = "center"
) -> pypdf.PageObject:
    """Generates an in-memory single-page PDF containing the text watermark."""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    
    # Configure alpha & color
    can.saveState()
    try:
        color = HexColor(color_hex)
        can.setFillColor(color, alpha=opacity)
        can.setStrokeColor(color, alpha=opacity)
    except Exception:
        can.setFillColorRGB(0.2, 0.4, 0.8, alpha=opacity)

    can.setFont("Helvetica-Bold", font_size)

    # Calculate coordinates based on placement
    if placement == "center":
        x = width / 2.0
        y = height / 2.0
        angle = rotation
    elif placement == "diagonal":
        x = width / 2.0
        y = height / 2.0
        angle = math.degrees(math.atan2(height, width))
    elif placement == "top_left":
        x = width * 0.2
        y = height * 0.85
        angle = rotation
    elif placement == "top_right":
        x = width * 0.8
        y = height * 0.85
        angle = rotation
    elif placement == "bottom_left":
        x = width * 0.2
        y = height * 0.15
        angle = rotation
    elif placement == "bottom_right":
        x = width * 0.8
        y = height * 0.15
        angle = rotation
    else:
        x = width / 2.0
        y = height / 2.0
        angle = rotation

    can.translate(x, y)
    can.rotate(angle)
    # Draw centered on translated origin
    can.drawCentredString(0, -font_size / 3.0, text)
    can.restoreState()
    can.save()

    packet.seek(0)
    watermark_pdf = pypdf.PdfReader(packet)
    return watermark_pdf.pages[0]


def _create_image_watermark_page(
    width: float,
    height: float,
    image_path: Path,
    opacity: float = 0.3,
    scale_percent: int = 50,
    placement: str = "center"
) -> pypdf.PageObject:
    """Generates an in-memory single-page PDF containing the image watermark."""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    can.saveState()

    with Image.open(image_path) as img:
        img_w, img_h = img.size
        img_aspect = img_w / float(img_h)

    # Desired max dimension based on page width and scale
    target_w = (width * (scale_percent / 100.0))
    target_h = target_w / img_aspect

    if target_h > height * 0.8:
        target_h = height * 0.8
        target_w = target_h * img_aspect

    if placement == "center":
        x = (width - target_w) / 2.0
        y = (height - target_h) / 2.0
    elif placement == "top_left":
        x = width * 0.05
        y = height - target_h - (height * 0.05)
    elif placement == "top_right":
        x = width - target_w - (width * 0.05)
        y = height - target_h - (height * 0.05)
    elif placement == "bottom_left":
        x = width * 0.05
        y = height * 0.05
    elif placement == "bottom_right":
        x = width - target_w - (width * 0.05)
        y = height * 0.05
    else:
        x = (width - target_w) / 2.0
        y = (height - target_h) / 2.0

    try:
        # ReportLab supports mask='auto' for PNG transparency
        can.setFillAlpha(opacity)
    except Exception:
        pass

    can.drawImage(
        str(image_path),
        x,
        y,
        width=target_w,
        height=target_h,
        mask="auto",
        preserveAspectRatio=True
    )
    can.restoreState()
    can.save()

    packet.seek(0)
    watermark_pdf = pypdf.PdfReader(packet)
    return watermark_pdf.pages[0]


def apply_watermark(
    input_path: Path,
    watermark_type: str = "text",
    # Text watermark options
    text: str = "CONFIDENTIAL",
    font_size: int = 48,
    opacity: float = 0.25,
    color_hex: str = "#2563eb",
    rotation: int = 45,
    placement: str = "center",
    # Image watermark options
    image_path: Optional[Path] = None,
    scale_percent: int = 50,
    # Scope
    page_selection: str = "all",
    range_expr: Optional[str] = None,
    password: Optional[str] = None
) -> tuple[pypdf.PdfWriter, Dict[str, Any]]:
    """
    Applies vector text or image watermark to the PDF document.
    Maintains underlying vector content and adjusts dynamically to mixed page sizes.
    """
    path = Path(input_path)
    validate_pdf_file(path, password=password)

    reader = pypdf.PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt(password or "")

    total_pages = len(reader.pages)
    target_pages_1based = set()

    if page_selection == "all":
        target_pages_1based = set(range(1, total_pages + 1))
    elif page_selection == "selected":
        if not range_expr:
            raise ValidationError("Please provide a page range expression for watermark application.")
        range_groups = parse_page_ranges(range_expr, total_pages)
        for g in range_groups:
            target_pages_1based.update(g)
    else:
        raise ValidationError(f"Invalid page selection '{page_selection}'. Must be 'all' or 'selected'.")

    # Clamping opacity
    opacity = max(0.01, min(1.0, float(opacity)))

    if watermark_type == "image":
        if not image_path or not Path(image_path).is_file():
            raise ValidationError("Image watermark requires a valid image file.")
        validate_image_file(Path(image_path))
    elif watermark_type == "text":
        if not text or not text.strip():
            raise ValidationError("Watermark text cannot be empty.")
    else:
        raise ValidationError(f"Unsupported watermark type '{watermark_type}'. Must be 'text' or 'image'.")

    writer = pypdf.PdfWriter()
    watermarked_count = 0

    try:
        for idx in range(total_pages):
            page = reader.pages[idx]
            page_num_1based = idx + 1

            if page_num_1based in target_pages_1based:
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)

                if watermark_type == "text":
                    watermark_page = _create_text_watermark_page(
                        width=width,
                        height=height,
                        text=text.strip(),
                        font_size=font_size,
                        opacity=opacity,
                        color_hex=color_hex,
                        rotation=rotation,
                        placement=placement
                    )
                else:
                    watermark_page = _create_image_watermark_page(
                        width=width,
                        height=height,
                        image_path=Path(image_path),
                        opacity=opacity,
                        scale_percent=scale_percent,
                        placement=placement
                    )

                page.merge_page(watermark_page)
                watermarked_count += 1

            writer.add_page(page)

        summary = {
            "operation": "watermark",
            "watermark_type": watermark_type,
            "total_pages": total_pages,
            "pages_watermarked": watermarked_count,
            "placement": placement,
            "opacity": opacity
        }
        if watermark_type == "text":
            summary["text"] = text
            summary["color"] = color_hex
            summary["rotation"] = rotation
        else:
            summary["image"] = Path(image_path).name

        return writer, summary

    except ValidationError:
        raise
    except Exception as e:
        raise OperationError(f"Watermark application failed: {str(e)}")
