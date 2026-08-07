"""UI / System tests for Word to Image tool Flet frame with batch support."""

from __future__ import annotations

import time
import flet as ft
from unittest.mock import MagicMock
from pathlib import Path

from officekit.tools.word2img.ui import Word2ImgFrame


def test_word2img_ui_initialization():
    """Verify that Word2ImgFrame correctly constructs all required input controls."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    assert frame.file_path_field.label == "输入 Word 文件或文件夹"
    assert frame.output_dir_field.label == "输出目录 (留空则输出到各文档同级目录)"
    assert frame.file_path_field.read_only is True
    assert frame.output_mode_radio.value == "image"
    assert frame.dpi_dropdown.value == "150"
    assert frame.format_radio.value == "png"
    assert frame.image_options_row.visible is True
    assert frame.run_btn.text == "▶ 开始转换"


def test_word2img_ui_hides_image_options_for_pdf_mode():
    """Selecting PDF output should hide image format and DPI controls."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    frame.output_mode_radio.value = "pdf"
    frame.on_output_mode_change(None)

    assert frame.image_options_row.visible is False

    frame.output_mode_radio.value = "image"
    frame.on_output_mode_change(None)

    assert frame.image_options_row.visible is True


def test_word2img_ui_single_file_selection():
    """Selecting a single file should update the selection list and text field."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    # Simulate picker selection of one file
    mock_event = MagicMock()
    mock_file = MagicMock()
    mock_file.path = "/path/to/my_file.docx"
    mock_event.files = [mock_file]

    frame.on_files_selected(mock_event)
    assert frame.selected_files == ["/path/to/my_file.docx"]
    assert frame.selected_folder == ""
    assert frame.file_path_field.value == "/path/to/my_file.docx"
    page_mock.update.assert_called()


def test_word2img_ui_multiple_files_selection():
    """Selecting multiple files should update selection list and summarize count."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    # Simulate picker selection of three files
    mock_event = MagicMock()
    mock_file_1 = MagicMock()
    mock_file_1.path = "/path/to/file1.docx"
    mock_file_2 = MagicMock()
    mock_file_2.path = "/path/to/file2.docx"
    mock_file_3 = MagicMock()
    mock_file_3.path = "/path/to/file3.doc"
    mock_event.files = [mock_file_1, mock_file_2, mock_file_3]

    frame.on_files_selected(mock_event)
    assert frame.selected_files == ["/path/to/file1.docx", "/path/to/file2.docx", "/path/to/file3.doc"]
    assert frame.selected_folder == ""
    assert frame.file_path_field.value == "已选择 3 个 Word 文件"
    page_mock.update.assert_called()


def test_word2img_ui_rejects_unsupported_file_selection():
    """Unsupported files should not be accepted even if a picker returns them."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)
    frame.show_dialog = MagicMock()

    mock_event = MagicMock()
    mock_file = MagicMock()
    mock_file.path = "/path/to/not-word.pdf"
    mock_event.files = [mock_file]

    frame.on_files_selected(mock_event)

    assert frame.selected_files == []
    frame.show_dialog.assert_called_once_with(
        "文件类型不支持",
        "请选择 .doc 或 .docx 格式的 Word 文档。",
    )


def test_word2img_ui_ignores_invalid_files_from_mixed_selection():
    """Mixed selections should keep valid Word documents and warn about invalid files."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)
    frame.show_dialog = MagicMock()

    mock_event = MagicMock()
    valid_file = MagicMock()
    valid_file.path = "/path/to/file1.docx"
    invalid_file = MagicMock()
    invalid_file.path = "/path/to/file2.pdf"
    mock_event.files = [valid_file, invalid_file]

    frame.on_files_selected(mock_event)

    assert frame.selected_files == ["/path/to/file1.docx"]
    assert frame.file_path_field.value == "/path/to/file1.docx"
    frame.show_dialog.assert_called_once()


def test_word2img_ui_folder_selection():
    """Selecting an input directory should reset files list and update folder variable."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    # Simulate picker directory selection
    mock_event = MagicMock()
    mock_event.path = "/path/to/word_folder"

    frame.on_input_dir_selected(mock_event)
    assert frame.selected_folder == "/path/to/word_folder"
    assert frame.selected_files == []
    assert frame.file_path_field.value == "已选择文件夹: /path/to/word_folder"
    page_mock.update.assert_called()


def test_word2img_ui_output_picker_opens_directory_selector(mocker):
    """Output button should open a directory picker instead of a file picker."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)
    mocker.patch("officekit.tools.word2img.ui.select_macos_directory", return_value=None)
    frame.file_picker.get_directory_path = MagicMock()

    frame.open_output_dir_picker(None)

    assert frame.picker_mode == "output_dir"
    frame.file_picker.get_directory_path.assert_called_once_with()


def test_word2img_ui_output_picker_uses_macos_native_selector(mocker):
    """On macOS, output button should use the native AppleScript directory selector."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)
    mocker.patch(
        "officekit.tools.word2img.ui.select_macos_directory",
        return_value="/path/to/output_images",
    )
    frame.file_picker.get_directory_path = MagicMock()

    frame.open_output_dir_picker(None)

    assert frame.output_dir_field.value == "/path/to/output_images"
    frame.file_picker.get_directory_path.assert_not_called()
    page_mock.update.assert_called()


def test_word2img_ui_input_files_picker_uses_macos_native_selector(mocker):
    """On macOS, the input file option should use native picker and still validate file types."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)
    mocker.patch(
        "officekit.tools.word2img.ui.select_macos_files",
        return_value=["/path/to/file1.docx", "/path/to/file2.pdf"],
    )
    frame.show_dialog = MagicMock()
    frame.file_picker.pick_files = MagicMock()

    frame.open_input_files_picker()

    assert frame.selected_files == ["/path/to/file1.docx"]
    assert frame.file_path_field.value == "/path/to/file1.docx"
    frame.file_picker.pick_files.assert_not_called()
    frame.show_dialog.assert_called_once()


def test_word2img_ui_output_selection():
    """Selecting an output directory should update the output text field."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    # Simulate picker directory selection
    mock_event = MagicMock()
    mock_event.path = "/path/to/output_images"

    frame.on_output_dir_selected(mock_event)
    assert frame.output_dir_field.value == "/path/to/output_images"
    page_mock.update.assert_called()


def test_word2img_ui_start_conversion_validation():
    """Clicking start button without choosing anything should show a warning dialog."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)
    frame.show_dialog = MagicMock()

    # Empty selections
    frame.selected_files = []
    frame.selected_folder = ""
    frame.on_start_click(None)
    
    frame.show_dialog.assert_called_once_with("警告", "请先选择一个或多个 Word 文件，或者选择一个文件夹！")


def test_word2img_ui_task_execution_multiple_files(mocker):
    """Clicking start triggers background thread execution and updates log/progress for all files."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    # Mock business logic converter
    mock_convert = mocker.patch(
        "officekit.tools.word2img.ui.convert_word_to_images",
        return_value=[Path("/path/to/out/test-1.png"), Path("/path/to/out/test-2.png")]
    )
    frame.show_dialog = MagicMock()

    # Fill inputs
    frame.selected_files = ["/path/to/doc1.docx", "/path/to/doc2.doc"]
    frame.output_dir_field.value = "/path/to/out"
    frame.output_mode_radio.value = "image"
    frame.format_radio.value = "png"
    frame.dpi_dropdown.value = "150"

    # Trigger click
    frame.on_start_click(None)

    # Wait for thread completion
    timeout = 10
    while frame.is_running and timeout > 0:
        time.sleep(0.05)
        timeout -= 1

    # Verify business logic was called for each file
    assert mock_convert.call_count == 2
    mock_convert.assert_any_call(
        input_path=Path("/path/to/doc1.docx"),
        output_dir="/path/to/out",
        image_format="png",
        dpi=150,
    )
    mock_convert.assert_any_call(
        input_path=Path("/path/to/doc2.doc"),
        output_dir="/path/to/out",
        image_format="png",
        dpi=150,
    )

    assert "批量转换任务结束！" in frame.log_area.value
    assert "成功: 2 / 2" in frame.log_area.value
    frame.show_dialog.assert_called_once()


def test_word2img_ui_task_execution_pdf_mode(mocker):
    """PDF output mode should call convert_word_to_pdf instead of image conversion."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    mock_convert_pdf = mocker.patch(
        "officekit.tools.word2img.ui.convert_word_to_pdf",
        return_value=Path("/path/to/out/doc1.pdf"),
    )
    mock_convert_images = mocker.patch(
        "officekit.tools.word2img.ui.convert_word_to_images",
    )
    frame.show_dialog = MagicMock()

    frame.selected_files = ["/path/to/doc1.docx", "/path/to/doc2.doc"]
    frame.output_dir_field.value = "/path/to/out"
    frame.output_mode_radio.value = "pdf"

    frame.on_start_click(None)

    timeout = 10
    while frame.is_running and timeout > 0:
        time.sleep(0.05)
        timeout -= 1

    assert mock_convert_pdf.call_count == 2
    mock_convert_pdf.assert_any_call(
        input_path=Path("/path/to/doc1.docx"),
        output_dir="/path/to/out",
    )
    mock_convert_pdf.assert_any_call(
        input_path=Path("/path/to/doc2.doc"),
        output_dir="/path/to/out",
    )
    mock_convert_images.assert_not_called()

    assert "批量转换任务结束！" in frame.log_area.value
    assert "成功: 2 / 2" in frame.log_area.value
    frame.show_dialog.assert_called_once()
    assert "PDF" in frame.show_dialog.call_args[0][1]
