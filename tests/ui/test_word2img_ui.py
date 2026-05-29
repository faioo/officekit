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
    assert frame.file_path_field.read_only is True
    assert frame.dpi_dropdown.value == "150"
    assert frame.format_radio.value == "png"
    assert frame.run_btn.text == "▶ 开始转换"


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
