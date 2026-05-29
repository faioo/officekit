"""Flet GUI subpage for the Word to image tool."""

from __future__ import annotations

from pathlib import Path
import flet as ft

from officekit.ui.base import BaseToolFrame, create_section_container
from officekit.tools.word2img.core import convert_word_to_images


class Word2ImgFrame(BaseToolFrame):
    """Word to Image tool interface."""

    def __init__(self, page: ft.Page, **kwargs) -> None:
        self.file_path_field = ft.TextField(
            label="Word 文件路径 (.doc, .docx)",
            hint_text="请选择 Word 文档...",
            expand=True,
            read_only=True,
        )
        self.output_dir_field = ft.TextField(
            label="图片输出目录 (留空则默认在文档同级创建目录)",
            hint_text="请选择输出目录...",
            expand=True,
        )
        self.format_radio = ft.RadioGroup(
            content=ft.Row(
                controls=[
                    ft.Radio(value="png", label="PNG (高质量)"),
                    ft.Radio(value="jpeg", label="JPEG (体积小)"),
                ],
                spacing=20,
            ),
            value="png",
        )
        self.dpi_dropdown = ft.Dropdown(
            label="分辨率 (DPI)",
            options=[
                ft.dropdown.Option("96", "96 (低清晰度/快速)"),
                ft.dropdown.Option("150", "150 (推荐清晰度)"),
                ft.dropdown.Option("300", "300 (高清印刷)"),
            ],
            value="150",
            width=200,
        )

        super().__init__(page, **kwargs)

    def build_ui(self) -> ft.Control:
        # File pickers
        self.file_picker = ft.FilePicker(on_result=self.on_file_selected)
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_selected)
        self.page.overlay.extend([self.file_picker, self.dir_picker])

        # Sections
        section_files = create_section_container(
            "1. 选择文件与输出目录",
            [
                ft.Row(
                    controls=[
                        self.file_path_field,
                        ft.IconButton(
                            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
                            tooltip="浏览 Word 文件",
                            on_click=lambda _: self.file_picker.pick_files(
                                allowed_extensions=["doc", "docx"]
                            ),
                        ),
                    ]
                ),
                ft.Row(
                    controls=[
                        self.output_dir_field,
                        ft.IconButton(
                            icon=ft.Icons.DRIVE_FILE_MOVE_OUTLINED,
                            tooltip="浏览输出目录",
                            on_click=lambda _: self.dir_picker.get_directory_path(),
                        ),
                    ]
                ),
            ],
        )

        section_options = create_section_container(
            "2. 转换参数设置",
            [
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text("输出格式:", size=14, weight=ft.FontWeight.W_500),
                                self.format_radio,
                            ]
                        ),
                        ft.VerticalDivider(width=30),
                        self.dpi_dropdown,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                )
            ],
        )

        # Actions
        self.run_btn = ft.ElevatedButton(
            "▶ 开始转换",
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE,
            on_click=self.on_start_click,
            expand=True,
        )
        self.progress_bar = ft.ProgressBar(value=0.0, expand=True, color=ft.Colors.GREEN)
        self.progress_text = ft.Text("状态: 已就绪", size=13, italic=True)

        section_actions = create_section_container(
            "3. 转换控制与进度",
            [
                ft.Row(controls=[self.run_btn]),
                ft.Row(controls=[self.progress_bar]),
                self.progress_text,
            ],
        )

        # Logging
        self.log_area = ft.TextField(
            multiline=True,
            min_lines=8,
            max_lines=12,
            read_only=True,
            text_size=12,
            font_family="monospace",
            hint_text="处理日志将在此显示...",
            border_color=ft.Colors.OUTLINE_VARIANT,
        )

        section_log = create_section_container("4. 处理日志", [self.log_area])

        # Register input controls to be disabled during execution
        self.input_controls.extend([
            self.file_path_field,
            self.output_dir_field,
            self.format_radio,
            self.dpi_dropdown,
        ])

        return ft.Column(
            controls=[
                ft.Text("Word 文档转图片", size=22, weight=ft.FontWeight.BOLD),
                ft.Text("将 Word 文档 (.doc / .docx) 的每一页自动转换为高清 PNG 或 JPEG 图片。", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Divider(height=20, thickness=1),
                ft.ListView(
                    controls=[
                        section_files,
                        section_options,
                        section_actions,
                        section_log,
                    ],
                    expand=True,
                    spacing=10,
                ),
            ],
            expand=True,
        )

    def on_file_selected(self, e: ft.FilePickerResultEvent) -> None:
        """Called when a Word file is selected."""
        if e.files and len(e.files) > 0:
            self.file_path_field.value = e.files[0].path
            self.page.update()

    def on_dir_selected(self, e: ft.FilePickerResultEvent) -> None:
        """Called when an output directory is selected."""
        if e.path:
            self.output_dir_field.value = e.path
            self.page.update()

    def on_start_click(self, e) -> None:
        """Handle run button click."""
        input_file = self.file_path_field.value
        if not input_file or input_file == "请选择 Word 文档...":
            self.show_dialog("警告", "请先选择一个 Word 文档！")
            return

        out_dir = self.output_dir_field.value or None
        img_format = self.format_radio.value
        dpi = int(self.dpi_dropdown.value or 150)

        # Run background thread
        self.start_task(self.run_conversion_task, input_file, out_dir, img_format, dpi)

    def run_conversion_task(
        self, input_file: str, out_dir: str | None, img_format: str, dpi: int
    ) -> None:
        """Synchronous task executed in the background thread."""
        self.log(f"开始转换 Word 文档: {Path(input_file).name}")
        self.update_progress(None, "正在进行文档分析并转换为 PDF...")

        self.log("正在启动 LibreOffice headless 进程，请稍候...")
        # Since convert_word_to_images is blocking, we run it
        # We can update logs as we progress
        images = convert_word_to_images(
            input_path=input_file,
            output_dir=out_dir,
            image_format=img_format,
            dpi=dpi,
        )

        self.log(f"LibreOffice 和 pdftoppm 转换成功！共生成了 {len(images)} 张图片：")
        for idx, img in enumerate(images, 1):
            self.log(f"  [{idx}/{len(images)}] 已保存: {img.name}")

        self.update_progress(1.0, f"完成！成功转换并生成 {len(images)} 张图片。")
        self.show_dialog("成功", f"Word 转图片任务完成！\n\n共生成了 {len(images)} 张图片。")
