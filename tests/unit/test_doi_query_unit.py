"""Unit tests for DOI Query core business logic."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock
import requests

from officekit.tools.doi_query.core import (
    query_doi,
    _find_column,
    _find_columns,
)


def test_query_doi_empty():
    """Empty query inputs should instantly return Not Found without hitting network."""
    assert query_doi("", "", "") == "Not Found"
    assert query_doi(None, None, None) == "Not Found"


def test_query_doi_success(mocker):
    """Test successful DOI retrieval from Crossref API."""
    mock_get = mocker.patch("requests.get")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "items": [
                {"DOI": "10.1000/xyz123"}
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = query_doi("A Sample Paper", "Journal of Testing", "2026")
    assert result == "10.1000/xyz123"
    mock_get.assert_called_once_with(
        "https://api.crossref.org/works",
        params={"query.bibliographic": "A Sample Paper Journal of Testing 2026", "rows": 1},
        timeout=30,
    )


def test_query_doi_not_found(mocker):
    """Test when Crossref API has no matching results."""
    mock_get = mocker.patch("requests.get")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "items": []
        }
    }
    mock_get.return_value = mock_response

    result = query_doi("Paper That Does Not Exist", "Fake Journal", "2000")
    assert result == "Not Found"


def test_query_doi_timeout(mocker):
    """Test handling of requests Timeout exception."""
    mock_get = mocker.patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out"))
    
    result = query_doi("Some Title", "Some Journal", "2026")
    assert result == "Timeout"


def test_query_doi_error(mocker):
    """Test handling of requests RequestException."""
    mock_get = mocker.patch(
        "requests.get", 
        side_effect=requests.exceptions.RequestException("Connection refused by remote host")
    )
    
    result = query_doi("Some Title", "Some Journal", "2026")
    assert result.startswith("Error: Connection refused")


def test_find_column_helper():
    """Test finding 1-based column indexes from headers."""
    headers = ["ID", "Title", "Journal", "Year", "DOI"]
    assert _find_column(headers, "Title") == 2
    assert _find_column(headers, "doi") == 5
    assert _find_column(headers, "Author") is None


def test_find_columns_success():
    """Test successful lookup of all required columns."""
    headers = ["Year", "title", "JOURNAL", "Extra"]
    columns = _find_columns(headers)
    assert columns == {
        "Title": 2,
        "Journal": 3,
        "Year": 1,
    }


def test_find_columns_missing():
    """Missing required columns should raise ValueError."""
    headers = ["title", "JOURNAL"]
    with pytest.raises(ValueError) as exc_info:
        _find_columns(headers)
    assert "missing required columns: Year" in str(exc_info.value)
