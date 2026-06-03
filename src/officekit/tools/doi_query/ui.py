"""Flet GUI subpage for the DOI query tool."""

from __future__ import annotations

from pathlib import Path
import flet as ft

from officekit.core.registry import register_tool
from officekit.ui.base import BaseToolFrame, create_section_container
from officekit.ui.file_dialogs import select_macos_file, select_macos_save_file
from officekit.tools.doi_query.core import enrich_excel_with_doi


@register_tool(
    id_="doi_query",
    name="DOI 查询",
    icon_name="SEARCH_OUTLINED",
    selected_icon_name="SEARCH",
)
class DOIQueryFrame(BaseToolFrame):
    """DOI Query tool interface."""

    def __init__(self, page: ft.Page, **kwargs) -> None:
        self.picker_mode: str | None = None

        self.file_path_field = ft.TextField(
            label="Excel 文件路径 (.xlsx)",
            hint_text="请选择 Excel 表格文件...",
            expand=True,
            read_only=True,
        )
        self.output_path_field = ft.TextField(
            label="输出 Excel 文件路径 (留空则默认在同级创建新文件)",
            hint_text="请选择保存路径...",
            expand=True,
        )
        self.sheet_dropdown = ft.Dropdown(
            label="工作表 (Worksheet)",
            hint_text="选择一个工作表...",
            options=[],
            expand=True,
        )
        self.timeout_field = ft.TextField(
            label="超时时间 (秒)",
            value="30",
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # Statistics widgets
        self.total_card = self._create_stat_card("总记录数", "0", ft.Colors.PRIMARY)
        self.success_card = self._create_stat_card("成功匹配", "0", ft.Colors.GREEN)
        self.error_card = self._create_stat_card("查询失败", "0", ft.Colors.RED)

        super().__init__(page, **kwargs)

    def _create_stat_card(self, title: str, init_val: str, text_color: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(title, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(
                        init_val,
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=text_color,
                        key="value",
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=8,
            padding=10,
            expand=True,
            alignment=ft.alignment.center,
        )

    def _set_stat_val(self, card: ft.Container, val: str) -> None:
        col: ft.Column = card.content
        for ctrl in col.controls:
            if getattr(ctrl, "key", None) == "value":
                ctrl.value = val
                break

    def build_ui(self) -> ft.Control:
        # Use a single picker with mode dispatch; macOS uses native AppleScript first.
        self.file_picker = ft.FilePicker(on_result=self.on_picker_result)
        self.page.overlay.append(self.file_picker)

        # Section 1: Files
        section_files = create_section_container(
            "1. 选择 Excel 文件与保存路径",
            [
                ft.Row(
                    controls=[
                        self.file_path_field,
                        ft.IconButton(
                            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
                            tooltip="浏览 Excel 文件",
                            on_click=self.open_input_file_picker,
                        ),
                    ]
                ),
                ft.Row(
                    controls=[
                        self.output_path_field,
                        ft.IconButton(
                            icon=ft.Icons.DRIVE_FILE_MOVE_OUTLINED,
                            tooltip="指定另存为路径",
                            on_click=self.open_output_file_picker,
                        ),
                    ]
                ),
            ],
        )

        # Section 2: Options
        section_options = create_section_container(
            "2. 查询与参数配置",
            [
                ft.Row(
                    controls=[
                        self.sheet_dropdown,
                        self.timeout_field,
                    ],
                    spacing=20,
                )
            ],
        )

        # Section 3: Statistics Banner
        section_stats = create_section_container(
            "3. 统计看板",
            [
                ft.Row(
                    controls=[
                        self.total_card,
                        self.success_card,
                        self.error_card,
                    ],
                    spacing=15,
                )
            ],
        )

        # Section 4: Controls & Progress
        self.run_btn = ft.ElevatedButton(
            "▶ 开始批量查询",
            bgcolor=ft.Colors.BLUE,
            color=ft.Colors.WHITE,
            on_click=self.on_start_click,
            expand=True,
        )
        self.stop_btn = ft.ElevatedButton(
            "⏹ 停止查询",
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
            on_click=self.on_stop_click,
            disabled=True,
            expand=True,
        )
        self.progress_bar = ft.ProgressBar(value=0.0, expand=True, color=ft.Colors.BLUE)
        self.progress_text = ft.Text("状态: 已就绪", size=13, italic=True)

        section_actions = create_section_container(
            "4. 批量执行与进度",
            [
                ft.Row(controls=[self.run_btn, self.stop_btn], spacing=10),
                ft.Row(controls=[self.progress_bar]),
                self.progress_text,
            ],
        )

        # Section 5: Log
        self.log_area = ft.TextField(
            multiline=True,
            min_lines=8,
            max_lines=12,
            read_only=True,
            text_size=12,
            text_style=ft.TextStyle(font_family="monospace"),
            hint_text="处理日志与查询反馈将在此显示...",
            border_color=ft.Colors.OUTLINE_VARIANT,
        )
        section_log = create_section_container("5. 查询日志", [self.log_area])

        # Register input controls
        self.input_controls.extend([
            self.file_path_field,
            self.output_path_field,
            self.sheet_dropdown,
            self.timeout_field,
        ])

        return ft.Column(
            controls=[
                ft.Text("DOI 自动查询与补齐", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "读取 Excel 表格中的 Title, Journal, Year 列，从 Crossref 检索最新 DOI，并保存回新 Excel 文件的“DOI”列中。",
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Divider(height=20, thickness=1),
                ft.ListView(
                    controls=[
                        section_files,
                        section_options,
                        section_stats,
                        section_actions,
                        section_log,
                    ],
                    expand=True,
                    spacing=10,
                ),
            ],
            expand=True,
        )

    def open_input_file_picker(self, e) -> None:
        """Open native picker for the source Excel file."""
        selected_path = select_macos_file(
            "选择 Excel 表格文件",
            allowed_extensions=["xlsx"],
            log=self.log,
        )
        if selected_path is not None:
            if selected_path:
                self._apply_input_file_path(selected_path)
            return

        self.picker_mode = "input_file"
        self.file_picker.pick_files(allowed_extensions=["xlsx"])

    def open_output_file_picker(self, e) -> None:
        """Open native picker for the output Excel path."""
        selected_path = select_macos_save_file(
            "选择 DOI 结果保存路径",
            default_name="doi_results.xlsx",
            log=self.log,
        )
        if selected_path is not None:
            if selected_path:
                self._apply_output_file_path(selected_path)
            return

        self.picker_mode = "output_file"
        self.file_picker.save_file(allowed_extensions=["xlsx"], file_name="doi_results.xlsx")

    def on_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        """Dispatch single FilePicker result by the requested mode."""
        if self.picker_mode == "input_file":
            self.on_file_selected(e)
        elif self.picker_mode == "output_file":
            self.on_output_selected(e)
        self.picker_mode = None

    def on_file_selected(self, e: ft.FilePickerResultEvent) -> None:
        """Handle source file selection and extract sheet names."""
        if e.files and len(e.files) > 0:
            self._apply_input_file_path(e.files[0].path)

    def _apply_input_file_path(self, file_path: str) -> None:
        """Apply source Excel path from any picker backend and load sheets."""
        if not self._is_supported_excel_file(Path(file_path)):
            self.show_dialog("文件类型不支持", "请选择 .xlsx 格式的 Excel 文件。")
            return

        self.file_path_field.value = file_path
        self.log(f"已选择 Excel 文件: {file_path}")

        # Extract sheet names using openpyxl
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True)
            sheets = wb.sheetnames
            wb.close()

            self.sheet_dropdown.options = [ft.dropdown.Option(name) for name in sheets]
            self.sheet_dropdown.value = sheets[0] if sheets else None
            self.log(f"工作表解析成功，共找到 {len(sheets)} 个工作表")
        except Exception as ex:
            self.log(f"工作表解析失败: {str(ex)}", level="WARNING")

        self.page.update()

    def on_output_selected(self, e: ft.FilePickerResultEvent) -> None:
        """Handle output file path selection."""
        if e.path:
            self._apply_output_file_path(e.path)

    def _apply_output_file_path(self, file_path: str) -> None:
        """Apply output Excel path from any picker backend."""
        output_path = self._normalize_excel_output_path(file_path)
        self.output_path_field.value = output_path
        self.page.update()

    def on_start_click(self, e) -> None:
        """Handle start button click."""
        input_file = self.file_path_field.value
        if not input_file or input_file == "请选择 Excel 表格文件...":
            self.show_dialog("警告", "请先选择一个 Excel 表格文件！")
            return
        if not self._is_supported_excel_file(Path(input_file)):
            self.show_dialog("文件类型不支持", "请选择 .xlsx 格式的 Excel 文件。")
            return

        out_file = (
            self._normalize_excel_output_path(self.output_path_field.value)
            if self.output_path_field.value
            else None
        )
        sheet_name = self.sheet_dropdown.value

        try:
            timeout = int(self.timeout_field.value or 30)
        except ValueError:
            self.show_dialog("错误", "超时时间必须是有效的正整数！")
            return

        # Reset statistics card displays
        self._set_stat_val(self.total_card, "0")
        self._set_stat_val(self.success_card, "0")
        self._set_stat_val(self.error_card, "0")

        # Run background task
        self.start_task(self.run_doi_task, input_file, out_file, sheet_name, timeout)

    def _is_supported_excel_file(self, path: Path) -> bool:
        return path.suffix.lower() == ".xlsx"

    def _normalize_excel_output_path(self, file_path: str) -> str:
        path = Path(file_path).expanduser()
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        return str(path)

    def run_doi_task(
        self,
        input_file: str,
        out_file: str | None,
        sheet_name: str | None,
        timeout: int,
        cancel_event: threading.Event | None = None,
    ) -> None:
        """Background task handler."""
        import threading
        self.log(f"正在加载 Excel 工作簿: {Path(input_file).name}...")

        # Keep stats counters
        success_count = [0]
        error_count = [0]

        def on_progress(current: int, total: int, title: str, doi: str) -> None:
            # Update stats values
            if doi.startswith("Error") or doi == "Timeout":
                error_count[0] += 1
            elif doi != "Not Found":
                success_count[0] += 1

            pct = current / total if total > 0 else 1.0
            self._set_stat_val(self.total_card, str(total))
            self._set_stat_val(self.success_card, str(success_count[0]))
            self._set_stat_val(self.error_card, str(error_count[0]))

            self.update_progress(pct, f"进度: {current}/{total} ({pct * 100:.1f}%)")
            truncated_title = title[:35] + "..." if len(title) > 35 else title
            self.log(f"[{current}/{total}] 查询: '{truncated_title}' -> {doi}")

        summary = enrich_excel_with_doi(
            input_file,
            out_file,
            sheet_name=sheet_name,
            timeout=timeout,
            progress_callback=on_progress,
            cancel_event=cancel_event,
        )

        self.log("=" * 60)
        self.log("批量 DOI 补充完成！")
        self.log(f"总处理记录数: {summary.total}")
        self.log(f"成功找到 DOI: {summary.success}")
        self.log(f"未找到 DOI: {summary.not_found}")
        self.log(f"查询出错: {summary.errors}")
        self.log(f"结果已保存至: {summary.output_path}")

        self.update_progress(1.0, "任务处理完成！")
        self.show_dialog(
            "完成",
            f"DOI 查询补齐成功！\n\n"
            f"总记录: {summary.total} 条\n"
            f"成功匹配: {summary.success} 条\n"
            f"未找到: {summary.not_found} 条\n"
            f"错误/超时: {summary.errors} 条\n\n"
            f"文件已存至:\n{summary.output_path}",
        )
