"""Unit tests for Word to Image core business logic."""

from __future__ import annotations

import pytest
from pathlib import Path

from officekit.tools.word2img.core import (
    convert_word_to_images,
    _command_env,
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
    mocker.patch("officekit.tools.word2img.core.COMMON_COMMAND_PATHS", {})
    with pytest.raises(RuntimeError) as exc_info:
        _find_command("soffice", "libreoffice")
    assert "缺少 Word 转图片依赖" in str(exc_info.value)
    assert "brew install --cask libreoffice" in str(exc_info.value)


def test_find_command_uses_common_macos_app_path(mocker, tmp_path):
    """Finder-launched apps should still find LibreOffice in /Applications."""
    fallback_soffice = tmp_path / "LibreOffice.app" / "Contents" / "MacOS" / "soffice"
    fallback_soffice.parent.mkdir(parents=True)
    fallback_soffice.write_text("mock")
    expected_path = str(fallback_soffice)
    mocker.patch("shutil.which", return_value=None)
    mocker.patch(
        "officekit.tools.word2img.core.COMMON_COMMAND_PATHS",
        {"soffice": (expected_path,)},
    )

    result = _find_command("soffice", "libreoffice")

    assert result == expected_path


def test_find_command_prefers_bundled_libreoffice(mocker, tmp_path):
    """Packaged apps should prefer the bundled LibreOffice binary."""
    vendor_dir = tmp_path / "vendor"
    bundled_soffice = vendor_dir / "LibreOffice" / "program" / "soffice.exe"
    bundled_soffice.parent.mkdir(parents=True)
    bundled_soffice.write_text("mock")

    mocker.patch("officekit.tools.word2img.core._candidate_vendor_dirs", return_value=(vendor_dir,))
    mocker.patch("shutil.which", return_value="/usr/bin/soffice")

    result = _find_command("soffice", "libreoffice")

    assert result == str(bundled_soffice)


def test_find_command_prefers_bundled_poppler(mocker, tmp_path):
    """Packaged apps should prefer the bundled pdftoppm binary."""
    vendor_dir = tmp_path / "vendor"
    bundled_pdftoppm = vendor_dir / "poppler" / "bin" / "pdftoppm"
    bundled_pdftoppm.parent.mkdir(parents=True)
    bundled_pdftoppm.write_text("mock")

    mocker.patch("officekit.tools.word2img.core._candidate_vendor_dirs", return_value=(vendor_dir,))
    mocker.patch("shutil.which", return_value="/usr/bin/pdftoppm")

    result = _find_command("pdftoppm")

    assert result == str(bundled_pdftoppm)


def test_find_command_prefers_bundled_windows_poppler(mocker, tmp_path):
    """Windows packaged apps should prefer bundled pdftoppm.exe."""
    vendor_dir = tmp_path / "vendor"
    bundled_pdftoppm = vendor_dir / "poppler" / "bin" / "pdftoppm.exe"
    bundled_pdftoppm.parent.mkdir(parents=True)
    bundled_pdftoppm.write_text("mock")

    mocker.patch("officekit.tools.word2img.core._candidate_vendor_dirs", return_value=(vendor_dir,))
    mocker.patch("shutil.which", return_value="/usr/bin/pdftoppm")

    result = _find_command("pdftoppm")

    assert result == str(bundled_pdftoppm)


def test_find_command_accepts_bundled_windows_poppler_library_layout(mocker, tmp_path):
    """Older Windows bundles may keep Chocolatey's Library/bin Poppler layout."""
    vendor_dir = tmp_path / "vendor"
    bundled_pdftoppm = vendor_dir / "poppler" / "Library" / "bin" / "pdftoppm.exe"
    bundled_pdftoppm.parent.mkdir(parents=True)
    bundled_pdftoppm.write_text("mock")

    mocker.patch("officekit.tools.word2img.core._candidate_vendor_dirs", return_value=(vendor_dir,))
    mocker.patch("shutil.which", return_value=None)
    mocker.patch("officekit.tools.word2img.core.COMMON_COMMAND_PATHS", {})

    result = _find_command("pdftoppm")

    assert result == str(bundled_pdftoppm)


def test_command_env_adds_bundled_poppler_lib_path(tmp_path):
    """Bundled pdftoppm should receive a local DYLD_LIBRARY_PATH."""
    pdftoppm = tmp_path / "vendor" / "poppler" / "bin" / "pdftoppm"
    lib_dir = tmp_path / "vendor" / "poppler" / "lib"
    pdftoppm.parent.mkdir(parents=True)
    lib_dir.mkdir(parents=True)
    pdftoppm.write_text("mock")

    env = _command_env(str(pdftoppm))

    assert env is not None
    assert str(lib_dir) in env["DYLD_LIBRARY_PATH"]


def test_command_env_adds_bundled_poppler_bin_to_path(tmp_path):
    """Bundled Windows pdftoppm should receive its local bin directory on PATH."""
    pdftoppm = tmp_path / "vendor" / "poppler" / "bin" / "pdftoppm.exe"
    pdftoppm.parent.mkdir(parents=True)
    pdftoppm.write_text("mock")

    env = _command_env(str(pdftoppm))

    assert env is not None
    assert str(pdftoppm.parent) in env["PATH"]


def test_find_command_missing_pdftoppm_includes_poppler_hint(mocker):
    """Missing pdftoppm should tell users how to install Poppler."""
    mocker.patch("shutil.which", return_value=None)
    mocker.patch("officekit.tools.word2img.core.COMMON_COMMAND_PATHS", {})

    with pytest.raises(RuntimeError) as exc_info:
        _find_command("pdftoppm")

    assert "brew install poppler" in str(exc_info.value)


def test_find_command_missing_pdftoppm_lists_checked_vendor_paths(mocker, tmp_path):
    """Missing Poppler errors should point users at the bundled paths that were checked."""
    vendor_dir = tmp_path / "vendor"
    mocker.patch("officekit.tools.word2img.core._candidate_vendor_dirs", return_value=(vendor_dir,))
    mocker.patch("shutil.which", return_value=None)
    mocker.patch("officekit.tools.word2img.core.COMMON_COMMAND_PATHS", {})

    with pytest.raises(RuntimeError) as exc_info:
        _find_command("pdftoppm")

    message = str(exc_info.value)
    assert str(vendor_dir / "poppler" / "bin" / "pdftoppm.exe") in message
    assert str(vendor_dir / "poppler" / "Library" / "bin" / "pdftoppm.exe") in message


def test_convert_word_to_images_defaults_to_source_directory(mocker, tmp_path):
    """Generated images should be written next to the source document by default."""
    docx_file = tmp_path / "test_doc.docx"
    docx_file.write_text("mock content")

    mocker.patch("shutil.which", side_effect=lambda name: f"/mock/bin/{name}")
    mock_run = mocker.patch("officekit.tools.word2img.core._run")

    expected_img_1 = tmp_path / "test_doc-1.png"
    expected_img_2 = tmp_path / "test_doc-2.png"

    def side_effect_run(cmd):
        if "soffice" in cmd[0]:
            outdir = cmd[cmd.index("--outdir") + 1]
            pdf_path = Path(outdir) / "test_doc.pdf"
            pdf_path.write_text("mock pdf")
        elif "pdftoppm" in cmd[0]:
            assert cmd[-1] == str(tmp_path / "test_doc")
            expected_img_1.write_text("img1")
            expected_img_2.write_text("img2")

    mock_run.side_effect = side_effect_run

    result = convert_word_to_images(docx_file, image_format="png", dpi=150)

    assert result == [expected_img_1, expected_img_2]


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
