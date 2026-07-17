"""Lightweight in-process test doubles for the Flet ``Page``.

These replace ``MagicMock`` in UI tests so real wiring behaviour -- overlay
registration, ``page.update()`` calls, window/theme setup and navigation -- is
actually exercised instead of being silently swallowed by a mock. No Flutter
toolchain or running Flet session is required: only the small slice of the
``Page`` API that OfficeKit's UI code touches is emulated.
"""

from __future__ import annotations

import types
from collections.abc import Iterator
from typing import Any


class FakePage:
    """Minimal stand-in for :class:`flet.Page` used by OfficeKit's UI code.

    Emulates only what the app relies on: a real ``overlay`` list (so dialog /
    file-picker registration can be asserted), a ``controls`` list populated by
    ``add``, a ``window`` namespace, theme/title attributes, and an ``update``
    method that counts invocations instead of rendering.
    """

    def __init__(self) -> None:
        self.overlay: list[Any] = []
        self.controls: list[Any] = []
        self.window = types.SimpleNamespace()
        self.title: str | None = None
        self.theme: Any = None
        self.theme_mode: Any = None
        self.update_count = 0

    def update(self, *args: Any, **kwargs: Any) -> None:
        self.update_count += 1

    def add(self, *controls: Any) -> None:
        self.controls.extend(controls)


def iter_controls(root: Any) -> Iterator[Any]:
    """Depth-first walk over a Flet control subtree, yielding every control.

    Handles the container attributes actually used in this codebase
    (``content``, ``controls``, ``actions``) and guards against cycles.
    """
    seen: set[int] = set()
    stack: list[Any] = [root]
    while stack:
        node = stack.pop()
        if node is None or id(node) in seen:
            continue
        seen.add(id(node))
        yield node

        content = getattr(node, "content", None)
        if content is not None and not isinstance(content, str):
            stack.append(content)

        for attr in ("controls", "actions"):
            children = getattr(node, attr, None)
            if isinstance(children, (list, tuple)):
                stack.extend(children)


def find_controls(root: Any, control_type: type) -> list[Any]:
    """Return every control of ``control_type`` within ``root``'s subtree."""
    return [control for control in iter_controls(root) if isinstance(control, control_type)]
