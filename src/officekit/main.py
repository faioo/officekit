"""OfficeKit command entrypoint."""

import flet as ft
from officekit.ui.app import main_gui


def main() -> None:
    """Launch Flet GUI desktop application by default."""
    ft.app(target=main_gui)


if __name__ == "__main__":
    main()
