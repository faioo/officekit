"""Boot / integration tests driving the app with a real FakePage.

These exercise the startup path that a mocked page previously hid: full
``main_gui`` setup, lazy tool instantiation and navigation switching, plus a
per-tool boot smoke that scales automatically as new tools are registered.
"""

from __future__ import annotations

import flet as ft
import pytest

from officekit.core.registry import REGISTERED_TOOLS, load_tool_class
from officekit.ui.app import MainAppLayout, main_gui


def test_main_gui_boots_end_to_end(fake_page):
    main_gui(fake_page)

    assert fake_page.title
    assert fake_page.window.width and fake_page.window.height
    assert fake_page.theme is not None

    layouts = [control for control in fake_page.controls if isinstance(control, MainAppLayout)]
    assert len(layouts) == 1


def test_main_layout_lazy_instantiates_tools(fake_page):
    layout = MainAppLayout(fake_page)

    # Only the first (default) tool is built on cold start.
    assert len(layout.tool_instances) == 1
    assert REGISTERED_TOOLS[0].id in layout.tool_instances

    # Switching navigation lazily builds and shows the second tool.
    second = REGISTERED_TOOLS[1]
    layout.rail.selected_index = 1
    layout.on_nav_change(None)

    assert second.id in layout.tool_instances
    assert layout.content_container.content is layout.tool_instances[second.id]


def test_navigation_rail_matches_registry(fake_page):
    layout = MainAppLayout(fake_page)

    assert len(layout.rail.destinations) == len(REGISTERED_TOOLS)
    for destination, tool in zip(layout.rail.destinations, REGISTERED_TOOLS):
        assert destination.label == tool.name
        assert destination.icon is not None
        assert destination.selected_icon is not None


@pytest.mark.parametrize("tool", REGISTERED_TOOLS, ids=lambda tool: tool.id)
def test_registered_tool_boots(tool, fake_page):
    tool_class = load_tool_class(tool.class_path)

    frame = tool_class(fake_page)

    # build_ui produced a real content tree without raising.
    assert frame.content is not None
    # Icon names must resolve against ft.Icons, or the app crashes at startup.
    assert getattr(ft.Icons, tool.icon_name) is not None
    assert getattr(ft.Icons, tool.selected_icon_name) is not None
