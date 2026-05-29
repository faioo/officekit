"""OfficeKit command entrypoint."""

import sys
from officekit.core.config import APP_NAME, APP_VERSION


def run_cli() -> None:
    """Run the legacy interactive CLI menu."""
    from officekit.tools.doi_query.cli import run_interactive as run_doi_query
    from officekit.tools.word2img.cli import run_interactive as run_word2img

    print(f"{APP_NAME} v{APP_VERSION}")
    print("请选择要使用的工具：")
    print("1. Word 转图片工具")
    print("2. DOI 查询工具")

    choice = input("请输入序号：").strip()

    if choice == "1":
        run_word2img()
        return

    if choice == "2":
        run_doi_query()
        return

    print("未识别的选项。")


def main() -> None:
    """Launch GUI by default, or fall back to CLI if '--cli' is specified."""
    if "--cli" in sys.argv:
        run_cli()
    else:
        # Launch Flet GUI
        import flet as ft
        from officekit.ui.app import main_gui
        ft.app(target=main_gui)


if __name__ == "__main__":
    main()
