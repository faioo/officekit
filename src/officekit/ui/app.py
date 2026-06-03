"""Main entrypoint for launching the Flet GUI application."""

from __future__ import annotations

import flet as ft
from officekit.core.registry import REGISTERED_TOOLS, load_tool_class


class MainAppLayout(ft.Row):
    """Layout manager coordinating sidebar NavigationRail and active subpages."""

    def __init__(self, page: ft.Page, **kwargs) -> None:
        self.page = page

        # Lazy instantiation of tool subpages to optimize cold start performance
        self.tool_instances = {}

        # Load only the first tool on initial startup to keep startup time near-zero
        default_tool = REGISTERED_TOOLS[0]
        default_class = load_tool_class(default_tool.class_path)
        self.tool_instances[default_tool.id] = default_class(page)

        # Left Sidebar: NavigationRail (using dynamic string icon resolution)
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=110,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=getattr(ft.Icons, tool.icon_name),
                    selected_icon=getattr(ft.Icons, tool.selected_icon_name),
                    label=tool.name,
                )
                for tool in REGISTERED_TOOLS
            ],
            on_change=self.on_nav_change,
        )

        # Right Area: Container loading the active subpage
        self.content_container = ft.Container(
            content=self.tool_instances[default_tool.id],
            expand=True,
        )

        super().__init__(
            expand=True,
            controls=[
                self.rail,
                ft.VerticalDivider(width=1),
                self.content_container,
            ],
            **kwargs,
        )

    def on_nav_change(self, e: ft.ControlEvent) -> None:
        """Called when user clicks another sidebar navigation item."""
        selected_index = int(self.rail.selected_index)
        tool = REGISTERED_TOOLS[selected_index]
        tool_id = tool.id

        # Lazy instantiate tool frame class on-demand and cache it
        if tool_id not in self.tool_instances:
            tool_class = load_tool_class(tool.class_path)
            self.tool_instances[tool_id] = tool_class(self.page)

        # Update display control and refresh page
        self.content_container.content = self.tool_instances[tool_id]
        self.page.update()


def main_gui(page: ft.Page) -> None:
    """Initialize GUI window configurations and start application."""
    page.title = "OfficeKit 办公小工具平台"
    page.window.width = 1000
    page.window.height = 700
    page.window.min_width = 850
    page.window.min_height = 600

    # Modern visual theme settings
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)

    # Add layouts
    page.add(MainAppLayout(page))
