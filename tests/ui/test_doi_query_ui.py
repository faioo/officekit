"""UI / System tests for DOI Query tool Flet frame."""

from __future__ import annotations

import time
import flet as ft
from unittest.mock import MagicMock

from officekit.tools.doi_query.ui import DOIQueryFrame
from officekit.tools.doi_query.core import DOIQuerySummary


def test_doi_ui_initialization():
    """Verify that DOIQueryFrame correctly constructs all required input controls."""
    page_mock = MagicMock()
    frame = DOIQueryFrame(page_mock)

    assert frame.file_path_field.label == "Excel 文件路径 (.xlsx)"
    assert frame.timeout_field.value == "30"
    assert frame.run_btn.text == "▶ 开始批量查询"
    # Verify stats cards
    assert frame.total_card is not None
    assert frame.success_card is not None
    assert frame.error_card is not None


def test_doi_ui_file_selection_loads_sheets(mocker):
    """Selecting an Excel file should parse and populate the worksheet dropdown options."""
    page_mock = MagicMock()
    frame = DOIQueryFrame(page_mock)

    # Mock openpyxl workbook reading
    mock_wb = MagicMock()
    mock_wb.sheetnames = ["Sheet1", "Sheet2", "Summary"]
    mock_load_workbook = mocker.patch("openpyxl.load_workbook", return_value=mock_wb)

    mock_event = MagicMock()
    mock_file = MagicMock()
    mock_file.path = "/path/to/research.xlsx"
    mock_event.files = [mock_file]

    frame.on_file_selected(mock_event)

    assert frame.file_path_field.value == "/path/to/research.xlsx"
    assert len(frame.sheet_dropdown.options) == 3
    assert frame.sheet_dropdown.options[0].key == "Sheet1"
    assert frame.sheet_dropdown.options[1].key == "Sheet2"
    assert frame.sheet_dropdown.options[2].key == "Summary"
    assert frame.sheet_dropdown.value == "Sheet1"

    mock_load_workbook.assert_called_once_with("/path/to/research.xlsx", read_only=True)
    mock_wb.close.assert_called_once()
    page_mock.update.assert_called()


def test_doi_ui_start_query_validation():
    """Clicking start with empty inputs should alert warning dialogue."""
    page_mock = MagicMock()
    frame = DOIQueryFrame(page_mock)
    frame.show_dialog = MagicMock()

    # Empty inputs
    frame.file_path_field.value = ""
    frame.on_start_click(None)
    frame.show_dialog.assert_called_once_with("警告", "请先选择一个 Excel 表格文件！")


def test_doi_ui_start_query_invalid_timeout():
    """Clicking start with invalid non-numeric timeout should show error dialog."""
    page_mock = MagicMock()
    frame = DOIQueryFrame(page_mock)
    frame.show_dialog = MagicMock()

    frame.file_path_field.value = "/path/to/file.xlsx"
    frame.timeout_field.value = "abc"  # Invalid
    frame.on_start_click(None)
    frame.show_dialog.assert_called_once_with("错误", "超时时间必须是有效的正整数！")


def test_doi_ui_task_execution(mocker):
    """Verify background Thread successfully runs DOI enrichment, updating UI counters."""
    page_mock = MagicMock()
    frame = DOIQueryFrame(page_mock)

    # 1. Mock the core enrich function
    mock_summary = DOIQuerySummary(
        output_path=MagicMock(),
        total=5,
        success=3,
        not_found=1,
        errors=1,
    )
    
    # Simulate enrich_excel_with_doi calling the progress callback inside
    def fake_enrich(input_path, output_path, sheet_name, timeout, progress_callback):
        if progress_callback:
            # Trigger 3 successes, 1 error, 1 not_found
            progress_callback(1, 5, "Paper 1", "10.1109/1")
            progress_callback(2, 5, "Paper 2", "10.1109/2")
            progress_callback(3, 5, "Paper 3", "Error: Timeout")
            progress_callback(4, 5, "Paper 4", "10.1109/4")
            progress_callback(5, 5, "Paper 5", "Not Found")
        return mock_summary

    mocker.patch(
        "officekit.tools.doi_query.ui.enrich_excel_with_doi",
        side_effect=fake_enrich
    )
    frame.show_dialog = MagicMock()

    # Fill inputs
    frame.file_path_field.value = "/path/to/papers.xlsx"
    frame.output_path_field.value = "/path/to/out.xlsx"
    frame.sheet_dropdown.value = "Sheet1"
    frame.timeout_field.value = "10"

    # 2. Trigger task execution
    frame.on_start_click(None)

    # Wait for background thread completion
    timeout = 10
    while frame.is_running and timeout > 0:
        time.sleep(0.05)
        timeout -= 1

    # 3. Verify final statistics and log contents
    # Success card key="value" inside card column should be 3
    success_text_control = frame.success_card.content.controls[1]
    error_text_control = frame.error_card.content.controls[1]
    total_text_control = frame.total_card.content.controls[1]
    
    assert success_text_control.value == "3"
    assert error_text_control.value == "1"
    assert total_text_control.value == "5"

    assert "批量 DOI 补充完成！" in frame.log_area.value
    assert "总处理记录数: 5" in frame.log_area.value
    frame.show_dialog.assert_called_once()
