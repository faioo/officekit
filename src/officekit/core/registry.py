"""Core tool registry for OfficeKit, promoting zero-intrusion modular extension."""

from __future__ import annotations

import importlib
import logging
import pkgutil
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import flet as ft

logger = logging.getLogger("officekit")

BUILTIN_TOOL_ORDER = ("word2img", "doi_query")


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


def _register_metadata(metadata: ToolMetadata) -> None:
    """Register metadata once and preserve deterministic navigation ordering."""
    if not any(tool.id == metadata.id for tool in REGISTERED_TOOLS):
        REGISTERED_TOOLS.append(metadata)
        _sort_registered_tools()


def _sort_registered_tools() -> None:
    priorities = {
        tool_id: index for index, tool_id in enumerate(BUILTIN_TOOL_ORDER)
    }
    REGISTERED_TOOLS.sort(
        key=lambda tool: (
            priorities.get(tool.id, len(priorities)),
            tool.id,
        )
    )


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
        _register_metadata(metadata)
        return cls
    return decorator


def load_tool_class(class_path: str) -> type[ft.Control]:
    """Dynamically import and return the tool's frame class from its class path."""
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _load_word2img_frame():
    from officekit.tools.word2img.ui import Word2ImgFrame

    return Word2ImgFrame


def _load_doi_query_frame():
    from officekit.tools.doi_query.ui import DOIQueryFrame

    return DOIQueryFrame


def _load_builtin_class(loader, module_name: str):
    """Load a built-in unless its module is the caller still being initialized."""
    try:
        return loader()
    except ImportError:
        module = sys.modules.get(module_name)
        spec = getattr(module, "__spec__", None)
        if module is not None and getattr(spec, "_initializing", False):
            return None
        raise


def _register_builtin_tools() -> None:
    """Import and register built-ins explicitly so frozen builds can trace them."""
    builtins = (
        (
            _load_builtin_class(
                _load_word2img_frame,
                "officekit.tools.word2img.ui",
            ),
            "word2img",
            "Word 转图片",
            "IMAGE_OUTLINED",
            "IMAGE",
        ),
        (
            _load_builtin_class(
                _load_doi_query_frame,
                "officekit.tools.doi_query.ui",
            ),
            "doi_query",
            "DOI 查询",
            "SEARCH_OUTLINED",
            "SEARCH",
        ),
    )
    for tool_class, tool_id, name, icon_name, selected_icon_name in builtins:
        if tool_class is None:
            continue
        _register_metadata(
            ToolMetadata(
                id_=tool_id,
                name=name,
                icon_name=icon_name,
                selected_icon_name=selected_icon_name,
                class_path=f"{tool_class.__module__}.{tool_class.__name__}",
            )
        )


def discover_tools() -> None:
    """Automatically discover and import all tool submodules to trigger decorator registration."""
    try:
        import officekit.tools

        for _, module_name, is_pkg in pkgutil.iter_modules(
            officekit.tools.__path__,
            officekit.tools.__name__ + ".",
        ):
            if not is_pkg:
                continue
            ui_module_name = f"{module_name}.ui"
            try:
                importlib.import_module(ui_module_name)
            except ImportError as error:
                logger.warning(
                    "Failed to import tool module %s: %s",
                    ui_module_name,
                    error,
                )
            except Exception:
                logger.exception("Tool module %s failed during discovery", ui_module_name)
    except Exception as error:
        logger.exception("Unable to enumerate OfficeKit tool packages")
        raise RuntimeError("Unable to enumerate OfficeKit tool packages") from error

    try:
        _register_builtin_tools()
    except Exception as error:
        logger.exception("Unable to register built-in OfficeKit tools")
        raise RuntimeError("Unable to register built-in OfficeKit tools") from error

    _sort_registered_tools()
    if not REGISTERED_TOOLS:
        raise RuntimeError("No OfficeKit tools were registered")


# Run tool discovery upon registry import to dynamically assemble REGISTERED_TOOLS
discover_tools()
