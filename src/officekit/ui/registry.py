"""Registry of available tools for the OfficeKit GUI."""

from __future__ import annotations

import flet as ft
from officekit.tools.word2img.ui import Word2ImgFrame
from officekit.tools.doi_query.ui import DOIQueryFrame

REGISTERED_TOOLS = [
    {
        "id": "word2img",
        "name": "Word 转图片",
        "icon": ft.Icons.IMAGE_OUTLINED,
        "selected_icon": ft.Icons.IMAGE,
        "class": Word2ImgFrame,
    },
    {
        "id": "doi_query",
        "name": "DOI 查询",
        "icon": ft.Icons.SEARCH_OUTLINED,
        "selected_icon": ft.Icons.SEARCH,
        "class": DOIQueryFrame,
    },
]
