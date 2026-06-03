"""Core tool registry for OfficeKit, promoting zero-intrusion modular extension."""

from __future__ import annotations

import importlib
import pkgutil
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


# Central tool registration - filled dynamically by decorators
REGISTERED_TOOLS: list[ToolMetadata] = []


def register_tool(
    id_: str,
    name: str,
    icon_name: str,
    selected_icon_name: str,
):
    """Class decorator to register a tool frame class into the central registry."""
    def decorator(cls: type[ft.Control]) -> type[ft.Control]:
        metadata = ToolMetadata(
            id_=id_,
            name=name,
            icon_name=icon_name,
            selected_icon_name=selected_icon_name,
            class_path=f"{cls.__module__}.{cls.__name__}",
        )
        # Avoid duplicate registrations
        if not any(t.id == id_ for t in REGISTERED_TOOLS):
            REGISTERED_TOOLS.append(metadata)
        return cls
    return decorator


def load_tool_class(class_path: str) -> type[ft.Control]:
    """Dynamically import and return the tool's frame class from its class path."""
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def discover_tools() -> None:
    """Automatically discover and import all tool submodules to trigger decorator registration."""
    try:
        import officekit.tools
        # Iterate over all subpackages inside officekit.tools
        for _, module_name, is_pkg in pkgutil.iter_modules(
            officekit.tools.__path__, officekit.tools.__name__ + "."
        ):
            if is_pkg:
                ui_module_name = f"{module_name}.ui"
                try:
                    importlib.import_module(ui_module_name)
                except ImportError:
                    # Ignore packages that do not have a .ui submodule or have load issues
                    pass
    except Exception:
        # Prevent any bootstrap crash
        pass


# Run tool discovery upon registry import to dynamically assemble REGISTERED_TOOLS
discover_tools()
