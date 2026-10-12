"""Integration tests for the Click Command-Line Interface."""

from pathlib import Path
from click.testing import CliRunner
import pypdf

from pdf_toolkit.cli import cli

def test_cli_version():
    """Verifies CLI version command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "PDF Utility Toolkit" in result.output
    assert "Harsh Patel" in result.output


def test_cli_merge(sample_pdf_3pages, sample_pdf_1page, tmp_path):
    """Verifies CLI merge command."""
    out_file = tmp_path / "merged_cli.pdf"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "merge",
        str(sample_pdf_3pages),
        str(sample_pdf_1page),
        "-o", str(out_file)
    ])
    assert result.exit_code == 0
    assert out_file.exists()
    reader = pypdf.PdfReader(str(out_file))
    assert len(reader.pages) == 4


def test_cli_split(sample_pdf_3pages, tmp_path):
    """Verifies CLI split command."""
    out_dir = tmp_path / "split_output"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "split",
        str(sample_pdf_3pages),
        "-m", "all_pages",
        "-o", str(out_dir)
    ])
    assert result.exit_code == 0
    assert len(list(out_dir.glob("*.pdf"))) == 3


def test_cli_rotate(sample_pdf_3pages, tmp_path):
    """Verifies CLI rotate command."""
    out_file = tmp_path / "rotated_cli.pdf"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "rotate",
        str(sample_pdf_3pages),
        "-a", "90",
        "-o", str(out_file)
    ])
    assert result.exit_code == 0
    assert out_file.exists()
    reader = pypdf.PdfReader(str(out_file))
    assert reader.pages[0].rotation == 90


def test_cli_watermark(sample_pdf_3pages, tmp_path):
    """Verifies CLI watermark command."""
    out_file = tmp_path / "watermark_cli.pdf"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "watermark",
        str(sample_pdf_3pages),
        "-t", "OFFICIAL DRAFT",
        "-o", str(out_file)
    ])
    assert result.exit_code == 0
    assert out_file.exists()


def test_cli_info(sample_pdf_3pages):
    """Verifies CLI info command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["info", str(sample_pdf_3pages)])
    assert result.exit_code == 0
    assert "Document Overview" in result.output
    assert "Pages: 3" in result.output


def test_cli_sanitize_metadata(sample_pdf_3pages, tmp_path):
    """Verifies CLI sanitize-metadata command."""
    out_file = tmp_path / "sanitized_cli.pdf"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "sanitize-metadata",
        str(sample_pdf_3pages),
        "-a", "strip_all",
        "-o", str(out_file)
    ])
    assert result.exit_code == 0
    assert out_file.exists()


def test_cli_extract_text(sample_pdf_3pages, tmp_path):
    """Verifies CLI extract-text command."""
    out_txt = tmp_path / "extracted.txt"
    runner = CliRunner()
    result = runner.invoke(cli, [
        "extract-text",
        str(sample_pdf_3pages),
        "-o", str(out_txt)
    ])
    assert result.exit_code == 0
    assert out_txt.exists()
    content = out_txt.read_text(encoding="utf-8")
    assert "Lorem ipsum" in content


def test_cli_validate(sample_pdf_3pages, corrupted_file):
    """Verifies CLI validate command on valid and corrupted files."""
    runner = CliRunner()
    res_valid = runner.invoke(cli, ["validate", str(sample_pdf_3pages)])
    assert res_valid.exit_code == 0
    assert "PASSED" in res_valid.output

    res_corrupt = runner.invoke(cli, ["validate", str(corrupted_file)])
    assert res_corrupt.exit_code == 1
    assert "FAILED" in res_corrupt.output
