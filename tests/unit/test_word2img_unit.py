"""Unit tests for Word to Image core business logic."""

from __future__ import annotations

import pytest
from pathlib import Path

from officekit.tools.word2img.core import (
    convert_word_to_images,
    _find_command,
)


def test_convert_word_to_images_file_not_found():
    """Missing input file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError) as exc_info:
        convert_word_to_images("nonexistent_doc.docx")
    assert "Word document not found" in str(exc_info.value)


def test_convert_word_to_images_unsupported_suffix(tmp_path):
    """Unsupported document file extension should raise ValueError."""
    temp_file = tmp_path / "test.txt"
    temp_file.write_text("dummy content")

    with pytest.raises(ValueError) as exc_info:
        convert_word_to_images(temp_file)
    assert "Unsupported Word document type" in str(exc_info.value)


def test_convert_word_to_images_unsupported_format(tmp_path):
    """Unsupported output image format should raise ValueError."""
    temp_file = tmp_path / "test.docx"
    temp_file.write_text("dummy content")

    with pytest.raises(ValueError) as exc_info:
        convert_word_to_images(temp_file, image_format="gif")
    assert "Unsupported image format" in str(exc_info.value)


def test_find_command_exists(mocker):
    """shutil.which finding a command should return its path."""
    mock_which = mocker.patch("shutil.which", return_value="/usr/bin/soffice")
    result = _find_command("soffice")
    assert result == "/usr/bin/soffice"
    mock_which.assert_called_once_with("soffice")


def test_find_command_missing(mocker):
    """If command is not found, raise RuntimeError."""
    mocker.patch("shutil.which", return_value=None)
    with pytest.raises(RuntimeError) as exc_info:
        _find_command("soffice", "libreoffice")
    assert "Missing required command" in str(exc_info.value)


def test_convert_word_to_images_successful_flow(mocker, tmp_path):
    """Verify conversion workflow executes soffice and pdftoppm correctly."""
    # Create a mock docx
    docx_file = tmp_path / "test_doc.docx"
    docx_file.write_text("mock content")

    # Mock dependencies
    mocker.patch("shutil.which", side_effect=lambda name: f"/mock/bin/{name}")
    mock_run = mocker.patch("officekit.tools.word2img.core._run")

    # Mock the output files generated in temp dir and output dir
    # During execution, pdftoppm output suffix will be e.g. -1.png, -2.png
    output_dir = tmp_path / "images"
    
    # We mock Path.glob to return some mock image Paths so that the function finishes successfully
    mock_img_1 = output_dir / "test_doc-1.png"
    mock_img_2 = output_dir / "test_doc-2.png"
    
    # Pre-create output files in mock_run to simulate successful conversion
    def side_effect_run(cmd):
        if "soffice" in cmd[0]:
            # Convert-to pdf command, creates the pdf in temp directory
            outdir = cmd[cmd.index("--outdir") + 1]
            pdf_path = Path(outdir) / "test_doc.pdf"
            pdf_path.write_text("mock pdf")
        elif "pdftoppm" in cmd[0]:
            # pdftoppm command, creates the images
            output_dir.mkdir(parents=True, exist_ok=True)
            mock_img_1.write_text("img1")
            mock_img_2.write_text("img2")

    mock_run.side_effect = side_effect_run

    result = convert_word_to_images(docx_file, output_dir=output_dir, image_format="png", dpi=150)
    
    assert len(result) == 2
    assert result[0] == mock_img_1
    assert result[1] == mock_img_2
    assert mock_run.call_count == 2  # Soffice first, then pdftoppm
