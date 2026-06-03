"""Integration tests for DOI Query Excel processing and Crossref mock enrichment."""

from __future__ import annotations

import openpyxl
from pathlib import Path
from unittest.mock import MagicMock

from officekit.tools.doi_query.core import enrich_excel_with_doi


def test_enrich_excel_integration(mocker, tmp_path):
    """Test reading Excel, appending DOI column, and saving results."""
    # 1. Create a mock input Excel workbook
    input_xlsx = tmp_path / "papers.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Papers"
    
    # Write headers and rows
    headers = ["Title", "Journal", "Year", "Extra"]
    ws.append(headers)
    
    rows = [
        ["Attention Is All You Need", "NeurIPS", "2017", "A"],
        ["Deep Residual Learning for Image Recognition", "CVPR", "2016", "B"],
        ["Paper Without DOI", "NoName Journal", "2020", "C"],
    ]
    for row in rows:
        ws.append(row)
    wb.save(input_xlsx)
    wb.close()

    # 2. Mock requests.Session.get to return fake API responses
    mock_get = mocker.patch("requests.Session.get")
    
    # We will simulate different results for each query
    # Row 1: Success
    response_1 = MagicMock()
    response_1.json.return_value = {
        "message": {"items": [{"DOI": "10.1145/3065386"}]}
    }
    response_1.raise_for_status = MagicMock()
    
    # Row 2: Success
    response_2 = MagicMock()
    response_2.json.return_value = {
        "message": {"items": [{"DOI": "10.1109/CVPR.2016.90"}]}
    }
    response_2.raise_for_status = MagicMock()
    
    # Row 3: Not Found
    response_3 = MagicMock()
    response_3.json.return_value = {
        "message": {"items": []}
    }
    response_3.raise_for_status = MagicMock()

    mock_get.side_effect = [response_1, response_2, response_3]

    # 3. Setup progress callback tracker
    callback_records = []
    def progress_cb(current: int, total: int, title: str, doi: str) -> None:
        callback_records.append((current, total, title, doi))

    # 4. Run the enrichment process
    output_xlsx = tmp_path / "papers_enriched.xlsx"
    summary = enrich_excel_with_doi(
        input_path=input_xlsx,
        output_path=output_xlsx,
        sheet_name="Papers",
        timeout=15,
        progress_callback=progress_cb,
    )

    # 5. Verify the Summary
    assert summary.output_path == output_xlsx
    assert summary.total == 3
    assert summary.success == 2
    assert summary.not_found == 1
    assert summary.errors == 0

    # 6. Verify progress callback triggers
    assert len(callback_records) == 3
    assert callback_records[0] == (1, 3, "Attention Is All You Need", "10.1145/3065386")
    assert callback_records[1] == (2, 3, "Deep Residual Learning for Image Recognition", "10.1109/CVPR.2016.90")
    assert callback_records[2] == (3, 3, "Paper Without DOI", "Not Found")

    # 7. Open output Excel file and inspect the columns
    wb_out = openpyxl.load_workbook(output_xlsx)
    ws_out = wb_out["Papers"]
    
    # Check headers
    out_headers = [cell.value for cell in ws_out[1]]
    assert out_headers == ["Title", "Journal", "Year", "Extra", "DOI"]

    # Check rows content
    row_2 = [cell.value for cell in ws_out[2]]
    assert row_2 == ["Attention Is All You Need", "NeurIPS", "2017", "A", "10.1145/3065386"]

    row_3 = [cell.value for cell in ws_out[3]]
    assert row_3 == ["Deep Residual Learning for Image Recognition", "CVPR", "2016", "B", "10.1109/CVPR.2016.90"]

    row_4 = [cell.value for cell in ws_out[4]]
    assert row_4 == ["Paper Without DOI", "NoName Journal", "2020", "C", "Not Found"]

    wb_out.close()
