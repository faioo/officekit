"""Core tool registry for OfficeKit, promoting zero-intrusion modular extension."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import flet as ft


class ToolMetadata:
    """Metadata representing a registered tool in OfficeKit."""

    def __init__(
        self,
        id_: str,
        name: str,
        icon_name: str,
        selected_icon_name: str,
        class_path: str,
    ) -> None:
        self.id = id_
        self.name = name
        self.icon_name = icon_name              # e.g., "IMAGE_OUTLINED"
        self.selected_icon_name = selected_icon_name  # e.g., "IMAGE"
        self.class_path = class_path            # e.g., "officekit.tools.word2img.ui.Word2ImgFrame"


# Central tool registration - dynamic and extensible
REGISTERED_TOOLS: list[ToolMetadata] = [
    ToolMetadata(
        id_="word2img",
        name="Word 转图片",
        icon_name="IMAGE_OUTLINED",
        selected_icon_name="IMAGE",
        class_path="officekit.tools.word2img.ui.Word2ImgFrame",
    ),
    ToolMetadata(
        id_="doi_query",
        name="DOI 查询",
        icon_name="SEARCH_OUTLINED",
        selected_icon_name="SEARCH",
        class_path="officekit.tools.doi_query.ui.DOIQueryFrame",
    ),
]


def load_tool_class(class_path: str) -> type[ft.Control]:
    """Dynamically import and return the tool's frame class from its class path."""
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)
