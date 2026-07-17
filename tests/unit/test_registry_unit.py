"""Regression tests for tool discovery and application startup."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from officekit.core import registry
from officekit.ui import app


def test_registered_builtin_tools_have_stable_default_order():
    """The default page should remain Word2Img regardless of discovery order."""
    assert [tool.id for tool in registry.REGISTERED_TOOLS[:2]] == [
        "word2img",
        "doi_query",
    ]


def test_discover_tools_registers_builtins_when_package_enumeration_is_empty(
    mocker,
    monkeypatch,
):
    """PyInstaller-like empty package enumeration must not remove built-in tools."""
    monkeypatch.setattr(registry, "REGISTERED_TOOLS", [])
    mocker.patch.object(registry.pkgutil, "iter_modules", return_value=iter(()))

    registry.discover_tools()

    assert [tool.id for tool in registry.REGISTERED_TOOLS] == [
        "word2img",
        "doi_query",
    ]


def test_main_layout_reports_empty_registry_instead_of_index_error(monkeypatch):
    """A damaged installation should fail with an actionable startup error."""
    monkeypatch.setattr(app, "REGISTERED_TOOLS", [])

    with pytest.raises(RuntimeError, match="No OfficeKit tools were registered"):
        app.MainAppLayout(MagicMock())


def test_main_layout_uses_private_page_reference():
    """Current Flet exposes Control.page as read-only during initialization."""
    page = MagicMock()

    layout = app.MainAppLayout(page)

    assert layout.app_page is page
    assert layout.content_container.content is not None
