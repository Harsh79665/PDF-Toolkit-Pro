"""Click-based Command-Line Interface for PDF Utility Toolkit."""

import sys
import json
from pathlib import Path
from typing import Optional
import click

from .config import APP_NAME, APP_VERSION, COPYRIGHT_TEXT
from .services.processor import PDFProcessorService
from .exceptions import ToolkitError

processor = PDFProcessorService()

@click.group()
@click.version_option(version=APP_VERSION, prog_name=APP_NAME, message=f"%(prog_name)s v%(version)s\n{COPYRIGHT_TEXT}")
def cli():
    """PDF Utility Toolkit — High-performance, non-destructive PDF manipulation."""
    pass


@cli.command("version")
def version_cmd():
    """Display application version and copyright details."""
    click.echo(f"{APP_NAME} — Version {APP_VERSION}")
    click.echo(COPYRIGHT_TEXT)


@cli.command("merge")
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path), required=True, help="Destination path for merged PDF.")
@click.option("-p", "--password", "passwords", multiple=True, help="Password in filename:password format.")
def merge_cmd(files, output_path, passwords):
    """Merge two or more PDF documents into a single file."""
    if len(files) < 2:
        click.secho("Error: At least two PDF files are required for merging.", fg="red", err=True)
        sys.exit(1)

    pwd_dict = {}
    for entry in passwords:
        if ":" in entry:
            name, pwd = entry.split(":", 1)
            pwd_dict[name.strip()] = pwd.strip()

    try:
        click.echo(f"Merging {len(files)} files...")
        result = processor.process_merge(
            input_paths=list(files),
            passwords=pwd_dict,
            desired_filename=output_path.name
        )
        saved_file, _ = processor.storage.get_processed_file(result["output"]["file_id"])
        
        # Copy to user destination
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(saved_file, "rb") as src, open(output_path, "wb") as dst:
            dst.write(src.read())

        click.secho(f"✓ Successfully merged {result['summary']['files_merged']} files into '{output_path}'.", fg="green")
        click.echo(f"  Total pages: {result['summary']['total_pages']}")
        click.echo(f"  Duration: {result['duration_seconds']}s")
    except ToolkitError as e:
        click.secho(f"Error [{e.code}]: {e.message}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Unexpected error: {str(e)}", fg="red", err=True)
        sys.exit(1)


@cli.command("split")
@click.argument("file", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("-m", "--mode", type=click.Choice(["all_pages", "custom_ranges", "extract_selection"]), default="all_pages", help="Split mode.")
@click.option("-r", "--range", "range_expr", type=str, help="Page range expression (e.g. '1-3,5,8-10').")
@click.option("-o", "--output-dir", "output_dir", type=click.Path(path_type=Path), default=Path("."), help="Directory to save output file(s).")
@click.option("--password", type=str, default=None, help="Password if encrypted.")
def split_cmd(file, mode, range_expr, output_dir, password):
    """Split a PDF into single pages, custom ranges, or extract selected pages."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"Splitting '{file.name}' using mode '{mode}'...")
        result = processor.process_split(
            input_path=file,
            mode=mode,
            range_expr=range_expr,
            password=password
        )

        outputs = result.get("all_outputs") or [result["output"]]
        for rec in outputs:
            src_file, _ = processor.storage.get_processed_file(rec["file_id"])
            dest = output_dir / rec["display_name"]
            with open(src_file, "rb") as s, open(dest, "wb") as d:
                d.write(s.read())
            click.echo(f"  Created: {dest}")

        click.secho(f"✓ Split complete. Generated {len(outputs)} file(s).", fg="green")
    except ToolkitError as e:
        click.secho(f"Error [{e.code}]: {e.message}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Unexpected error: {str(e)}", fg="red", err=True)
        sys.exit(1)


@cli.command("rotate")
@click.argument("file", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("-a", "--angle", type=click.Choice(["90", "180", "270"]), required=True, help="Clockwise rotation angle in degrees.")
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path), required=True, help="Destination output path.")
@click.option("-s", "--scope", type=click.Choice(["all", "selected"]), default="all", help="Target pages to rotate.")
@click.option("-r", "--range", "range_expr", type=str, help="Page range if scope is 'selected' (e.g. '1,3-5').")
@click.option("--password", type=str, default=None, help="Password if encrypted.")
def rotate_cmd(file, angle, output_path, scope, range_expr, password):
    """Rotate all or selected pages clockwise by 90, 180, or 270 degrees."""
    try:
        rot_angle = int(angle)
        click.echo(f"Rotating pages of '{file.name}' by {rot_angle}°...")
        result = processor.process_rotate(
            input_path=file,
            angle=rot_angle,
            page_selection=scope,
            range_expr=range_expr,
            password=password,
            desired_filename=output_path.name
        )
        saved_file, _ = processor.storage.get_processed_file(result["output"]["file_id"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(saved_file, "rb") as s, open(output_path, "wb") as d:
            d.write(s.read())

        click.secho(f"✓ Successfully rotated {result['summary']['count_rotated']} page(s) -> '{output_path}'.", fg="green")
    except ToolkitError as e:
        click.secho(f"Error [{e.code}]: {e.message}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Unexpected error: {str(e)}", fg="red", err=True)
        sys.exit(1)


@cli.command("watermark")
@click.argument("file", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path), required=True, help="Destination output path.")
@click.option("-t", "--text", type=str, help="Text watermark content.")
@click.option("-i", "--image", "image_path", type=click.Path(exists=True, path_type=Path), help="Image watermark file path.")
@click.option("--opacity", type=float, default=0.25, help="Opacity level (0.05 to 1.0).")
@click.option("--color", type=str, default="#2563eb", help="Hex color code for text watermark.")
@click.option("--font-size", type=int, default=48, help="Font size in points.")
@click.option("--rotation", type=int, default=45, help="Rotation angle in degrees.")
@click.option("--placement", type=click.Choice(["center", "diagonal", "top_left", "top_right", "bottom_left", "bottom_right"]), default="center")
@click.option("-s", "--scope", type=click.Choice(["all", "selected"]), default="all")
@click.option("-r", "--range", "range_expr", type=str, help="Page range if scope is 'selected'.")
@click.option("--password", type=str, default=None, help="Password if encrypted.")
def watermark_cmd(file, output_path, text, image_path, opacity, color, font_size, rotation, placement, scope, range_expr, password):
    """Apply vector text or image watermark overlay to a PDF document."""
    try:
        wm_type = "image" if image_path else "text"
        wm_text = text or "CONFIDENTIAL"
        click.echo(f"Applying {wm_type} watermark to '{file.name}'...")

        result = processor.process_watermark(
            input_path=file,
            watermark_type=wm_type,
            text=wm_text,
            font_size=font_size,
            opacity=opacity,
            color_hex=color,
            rotation=rotation,
            placement=placement,
            image_path=image_path,
            page_selection=scope,
            range_expr=range_expr,
            password=password,
            desired_filename=output_path.name
        )
        saved_file, _ = processor.storage.get_processed_file(result["output"]["file_id"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(saved_file, "rb") as s, open(output_path, "wb") as d:
            d.write(s.read())

        click.secho(f"✓ Watermark applied to {result['summary']['pages_watermarked']} page(s) -> '{output_path}'.", fg="green")
    except ToolkitError as e:
        click.secho(f"Error [{e.code}]: {e.message}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Unexpected error: {str(e)}", fg="red", err=True)
        sys.exit(1)


@cli.command("info")
@click.argument("file", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--json-out", is_flag=True, help="Output information as JSON format.")
@click.option("--password", type=str, default=None, help="Password if encrypted.")
def info_cmd(file, json_out, password):
    """Inspect PDF metrics, dimensions, encryption, metadata, and text stats."""
    try:
        result = processor.process_info(file, password=password)
        data = result["data"]

        if json_out:
            click.echo(json.dumps(data, indent=2))
            return

        click.secho(f"--- Document Overview: {data['filename']} ---", bold=True, fg="blue")
        click.echo(f"  File Size: {data['file_size_formatted']} ({data['file_size_bytes']} bytes)")
        click.echo(f"  Pages: {data['page_count']}")
        click.echo(f"  PDF Version: {data['pdf_version']}")
        click.echo(f"  Encrypted: {'Yes' if data['is_encrypted'] else 'No'}")
        
        click.secho("\n--- First Page Metrics ---", bold=True)
        if data["pages"]:
            fp = data["pages"][0]
            click.echo(f"  Dimensions: {fp['width_pt']} x {fp['height_pt']} pt ({fp['width_in']} x {fp['height_in']} in)")
            click.echo(f"  Orientation: {fp['orientation']}, Rotation: {fp['rotation']}°")

        click.secho("\n--- Metadata Fields ---", bold=True)
        if data["metadata"]:
            for k, v in data["metadata"].items():
                click.echo(f"  {k}: {v}")
        else:
            click.echo("  (No metadata present)")

        click.secho("\n--- Text Statistics ---", bold=True)
        ts = data["text_statistics"]
        click.echo(f"  Extractable Characters: {ts['total_characters']}")
        click.echo(f"  Extractable Words: {ts['total_words']}")
        click.echo(f"  Pages with Text: {ts['pages_with_extractable_text']} / {data['page_count']}")
        if ts["is_likely_scanned"]:
            click.secho(f"  Notice: {ts['notice']}", fg="yellow")

    except ToolkitError as e:
        click.secho(f"Error [{e.code}]: {e.message}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Unexpected error: {str(e)}", fg="red", err=True)
        sys.exit(1)


@cli.command("sanitize-metadata")
@click.argument("file", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path), required=True, help="Destination output path.")
@click.option("-a", "--action", type=click.Choice(["strip_all", "update"]), default="strip_all", help="Sanitization action.")
@click.option("--title", type=str, help="Set custom Title.")
@click.option("--author", type=str, help="Set custom Author.")
@click.option("--subject", type=str, help="Set custom Subject.")
@click.option("--keywords", type=str, help="Set custom Keywords.")
@click.option("--password", type=str, default=None, help="Password if encrypted.")
def sanitize_cmd(file, output_path, action, title, author, subject, keywords, password):
    """Strip or update document metadata properties."""
    try:
        custom_fields = {}
        if title is not None: custom_fields["title"] = title
        if author is not None: custom_fields["author"] = author
        if subject is not None: custom_fields["subject"] = subject
        if keywords is not None: custom_fields["keywords"] = keywords

        click.echo(f"Sanitizing metadata for '{file.name}' ({action})...")
        result = processor.process_sanitize_metadata(
            input_path=file,
            action=action,
            custom_fields=custom_fields if action == "update" else None,
            password=password,
            desired_filename=output_path.name
        )
        saved_file, _ = processor.storage.get_processed_file(result["output"]["file_id"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(saved_file, "rb") as s, open(output_path, "wb") as d:
            d.write(s.read())

        click.secho(f"✓ Metadata sanitized -> '{output_path}'.", fg="green")
        click.echo(f"  Fields modified: {result['summary']['fields_changed']}")
        click.secho(f"\n{result['summary']['disclaimer']}", fg="yellow")
    except ToolkitError as e:
        click.secho(f"Error [{e.code}]: {e.message}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Unexpected error: {str(e)}", fg="red", err=True)
        sys.exit(1)


@cli.command("extract-text")
@click.argument("file", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path), help="Optional path to save extracted text (.txt).")
@click.option("-s", "--scope", type=click.Choice(["all", "selected"]), default="all")
@click.option("-r", "--range", "range_expr", type=str, help="Page range if scope is 'selected'.")
@click.option("--password", type=str, default=None, help="Password if encrypted.")
def extract_cmd(file, output_path, scope, range_expr, password):
    """Extract text from a PDF document using pdfplumber."""
    try:
        click.echo(f"Extracting text from '{file.name}'...")
        result = processor.process_extract_text(
            input_path=file,
            page_selection=scope,
            range_expr=range_expr,
            password=password
        )
        data = result["data"]

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(data["full_text"])
            click.secho(f"✓ Extracted text saved to '{output_path}'.", fg="green")
        else:
            click.echo("\n--- Extracted Text Preview ---")
            sample = data["full_text"][:2000]
            click.echo(sample)
            if len(data["full_text"]) > 2000:
                click.echo(f"\n... [Truncated: {len(data['full_text'])} characters total. Use -o to save full text]")

        click.echo(f"\nStats: {data['total_words']} words, {data['total_characters']} characters across {data['pages_extracted_count']} page(s).")
        if data.get("warning"):
            click.secho(f"Warning: {data['warning']}", fg="yellow")

    except ToolkitError as e:
        click.secho(f"Error [{e.code}]: {e.message}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Unexpected error: {str(e)}", fg="red", err=True)
        sys.exit(1)


@cli.command("validate")
@click.argument("file", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--password", type=str, default=None, help="Password if encrypted.")
@click.option("--json-out", is_flag=True, help="Output validation as JSON.")
def validate_cmd(file, password, json_out):
    """Validate PDF header, trailer, catalog, structure, and integrity."""
    try:
        result = processor.process_validate(file, password=password)
        data = result["data"]

        if json_out:
            click.echo(json.dumps(data, indent=2))
            return

        status_text = "PASSED" if data["valid"] else "FAILED"
        status_color = "green" if data["valid"] else "red"
        click.secho(f"Validation Status: {status_text}", bold=True, fg=status_color)
        click.echo(f"  File: {data['filename']} ({data['file_size']} bytes)")
        click.echo(f"  PDF Version: {data['pdf_version']}")
        click.echo(f"  Pages: {data['page_count']}")

        click.secho("\nStructural Checks:", bold=True)
        for chk in data["checks"]:
            mark = "✓" if chk["passed"] else "✗"
            color = "green" if chk["passed"] else "red"
            click.secho(f"  [{mark}] {chk['name']}: {chk['detail']}", fg=color)

        if data["warnings"]:
            click.secho("\nWarnings:", bold=True, fg="yellow")
            for w in data["warnings"]:
                click.secho(f"  ! {w}", fg="yellow")

        if data["errors"]:
            click.secho("\nErrors:", bold=True, fg="red")
            for err in data["errors"]:
                click.secho(f"  ✗ {err}", fg="red")

        click.secho(f"\n{data['disclaimer']}", fg="cyan")

        if not data["valid"]:
            sys.exit(1)

    except ToolkitError as e:
        click.secho(f"Error [{e.code}]: {e.message}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Unexpected error: {str(e)}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
