"""Base classes and utility components for OfficeKit GUI."""

from __future__ import annotations

from datetime import datetime
import threading
import traceback
import flet as ft


class BaseToolFrame(ft.Container):
    """Base class for all second-level tool subpages in OfficeKit GUI."""

    def __init__(self, page: ft.Page, **kwargs) -> None:
        super().__init__(expand=True, padding=20, **kwargs)
        self.page = page
        self.log_area: ft.TextField | None = None
        self.progress_bar: ft.ProgressBar | None = None
        self.progress_text: ft.Text | None = None
        self.run_btn: ft.Button | None = None
        self.stop_btn: ft.Button | None = None
        self.input_controls: list[ft.Control] = []
        self.is_running = False
        self.current_thread: threading.Thread | None = None

        # Build the main layout
        self.content = self.build_ui()

    def build_ui(self) -> ft.Control:
        """Must be overridden by subclasses to return the main UI layout."""
        raise NotImplementedError

    def log(self, message: str, level: str = "INFO") -> None:
        """Thread-safe logging helper."""
        if not self.log_area:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{timestamp}] [{level}] "
        # Append message and update
        self.log_area.value = (self.log_area.value or "") + f"{prefix}{message}\n"
        self.page.update()

    def update_progress(self, value: float | None, text: str = "") -> None:
        """Thread-safe progress updates. Value should be between 0.0 and 1.0 (or None for indeterminate)."""
        if self.progress_bar:
            self.progress_bar.value = value
        if self.progress_text and text:
            self.progress_text.value = text
        self.page.update()

    def start_task(self, target, *args, **kwargs) -> None:
        """Runs the target function in a background thread."""
        if self.is_running:
            return
        self.is_running = True
        self._set_controls_state(disabled=True)
        if self.log_area:
            self.log_area.value = ""
        self.update_progress(None, "任务启动中...")

        def wrapper() -> None:
            try:
                target(*args, **kwargs)
            except Exception as error:
                self.log(f"任务运行出错: {str(error)}", level="ERROR")
                self.log(traceback.format_exc(), level="DEBUG")
                self.show_dialog("错误", f"任务运行出错:\n{str(error)}")
            finally:
                self.is_running = False
                self._set_controls_state(disabled=False)
                self.update_progress(0.0, "已就绪")
                self.page.update()

        self.current_thread = threading.Thread(target=wrapper, daemon=True)
        self.current_thread.start()

    def _set_controls_state(self, disabled: bool) -> None:
        for control in self.input_controls:
            control.disabled = disabled
        if self.run_btn:
            # For flet buttons, disabled changes appearance
            self.run_btn.disabled = disabled
        if self.stop_btn:
            self.stop_btn.disabled = not disabled
        self.page.update()

    def show_dialog(self, title: str, content: str) -> None:
        """Show an alert dialog to the user."""
        def close_dlg(e) -> None:
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(content),
            actions=[ft.TextButton("确定", on_click=close_dlg)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()


def create_section_container(title: str, controls: list[ft.Control]) -> ft.Container:
    """Helper to create a unified, beautifully styled section with a title."""
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=ft.colors.PRIMARY),
                ft.Divider(height=1, thickness=1),
                *controls,
            ],
            spacing=10,
        ),
        bgcolor=ft.colors.SURFACE_VARIANT,
        border_radius=8,
        padding=15,
        margin=ft.margin.only(bottom=15),
    )
