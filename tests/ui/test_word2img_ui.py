"""UI / System tests for Word to Image tool Flet frame."""

from __future__ import annotations

import time
import flet as ft
from unittest.mock import MagicMock

from officekit.tools.word2img.ui import Word2ImgFrame


def test_word2img_ui_initialization():
    """Verify that Word2ImgFrame correctly constructs all required input controls."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    assert frame.file_path_field.label == "Word 文件路径 (.doc, .docx)"
    assert frame.file_path_field.read_only is True
    assert frame.dpi_dropdown.value == "150"
    assert frame.format_radio.value == "png"
    assert frame.run_btn.text == "▶ 开始转换"


def test_word2img_ui_file_selection():
    """Selecting a file should update the file path text field."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    # Simulate picker selection
    mock_event = MagicMock()
    mock_file = MagicMock()
    mock_file.path = "/path/to/my_file.docx"
    mock_event.files = [mock_file]

    frame.on_file_selected(mock_event)
    assert frame.file_path_field.value == "/path/to/my_file.docx"
    page_mock.update.assert_called()


def test_word2img_ui_directory_selection():
    """Selecting an output directory should update the output dir text field."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    # Simulate picker directory selection
    mock_event = MagicMock()
    mock_event.path = "/path/to/output_dir"

    frame.on_dir_selected(mock_event)
    assert frame.output_dir_field.value == "/path/to/output_dir"
    page_mock.update.assert_called()


def test_word2img_ui_start_conversion_validation():
    """Clicking start button with empty file path should show a warning dialog."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)
    frame.show_dialog = MagicMock()

    # File path empty or default hint
    frame.file_path_field.value = ""
    frame.on_start_click(None)
    
    frame.show_dialog.assert_called_once_with("警告", "请先选择一个 Word 文档！")


def test_word2img_ui_task_execution(mocker):
    """Clicking start triggers background thread execution and updates log/progress."""
    page_mock = MagicMock()
    frame = Word2ImgFrame(page_mock)

    # Mock business logic converter to prevent real LibreOffice execution
    mock_convert = mocker.patch(
        "officekit.tools.word2img.ui.convert_word_to_images",
        return_value=[MagicMock(name="page-1.png"), MagicMock(name="page-2.png")]
    )
    frame.show_dialog = MagicMock()

    # Fill inputs
    frame.file_path_field.value = "/path/to/test.docx"
    frame.output_dir_field.value = "/path/to/out"
    frame.format_radio.value = "png"
    frame.dpi_dropdown.value = "150"

    # Trigger click
    frame.on_start_click(None)

    # Since it runs in a thread, we wait up to 1 second for completion
    timeout = 10
    while frame.is_running and timeout > 0:
        time.sleep(0.05)
        timeout -= 1

    # Verify background execution succeeded
    mock_convert.assert_called_once_with(
        input_path="/path/to/test.docx",
        output_dir="/path/to/out",
        image_format="png",
        dpi=150,
    )
    assert "转换成功！" in frame.log_area.value
    frame.show_dialog.assert_called_once()
    assert "已保存" in frame.log_area.value
