"""Flet GUI subpage for the Word to image tool."""

from __future__ import annotations

from pathlib import Path
import flet as ft

from officekit.ui.base import BaseToolFrame, create_section_container
from officekit.ui.file_dialogs import select_macos_directory, select_macos_files
from officekit.tools.word2img.core import SUPPORTED_WORD_SUFFIXES, convert_word_to_images


class Word2ImgFrame(BaseToolFrame):
    """Word to Image tool interface with batch and directory support."""

    def __init__(self, page: ft.Page, **kwargs) -> None:
        self.selected_files: list[str] = []
        self.selected_folder: str = ""
        self.picker_mode: str | None = None
        self.input_source_dialog: ft.AlertDialog | None = None

        self.file_path_field = ft.TextField(
            label="输入 Word 文件或文件夹",
            hint_text="点击右侧图标选择 Word 文件或文件夹...",
            expand=True,
            read_only=True,
        )
        self.output_dir_field = ft.TextField(
            label="图片输出目录 (留空则输出到各文档同级目录)",
            hint_text="点击右侧图标选择输出目录...",
            expand=True,
            read_only=True,
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
        # A single picker with mode dispatch avoids picker state conflicts on desktop.
        self.file_picker = ft.FilePicker(on_result=self.on_picker_result)
        self.page.overlay.append(self.file_picker)

        # Sections
        section_files = create_section_container(
            "1. 选择文件与输出目录",
            [
                ft.Row(
                    controls=[
                        self.file_path_field,
                        ft.IconButton(
                            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
                            tooltip="选择 Word 文件或文件夹",
                            on_click=self.show_input_source_dialog,
                        ),
                    ]
                ),
                ft.Row(
                    controls=[
                        self.output_dir_field,
                        ft.IconButton(
                            icon=ft.Icons.DRIVE_FILE_MOVE_OUTLINED,
                            tooltip="选择输出图片保存目录",
                            on_click=self.open_output_dir_picker,
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
            text_style=ft.TextStyle(font_family="monospace"),
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
                ft.Text("支持单个文件、多个文件或整个文件夹的 Word 文档 (.doc / .docx) 批量转换为高清图片。", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
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

    def show_input_source_dialog(self, e) -> None:
        """Let the user choose whether the single input button opens files or a folder."""

        def close_dialog() -> None:
            if self.input_source_dialog:
                self.input_source_dialog.open = False
            self.page.update()

        def choose_files(_) -> None:
            close_dialog()
            self.open_input_files_picker()

        def choose_folder(_) -> None:
            close_dialog()
            self.open_input_dir_picker()

        self.input_source_dialog = ft.AlertDialog(
            title=ft.Text("选择输入来源"),
            content=ft.Text("请选择 Word 文件（可多选），或选择一个包含 Word 文档的文件夹。"),
            actions=[
                ft.TextButton("选择文件", on_click=choose_files),
                ft.TextButton("选择文件夹", on_click=choose_folder),
                ft.TextButton("取消", on_click=lambda _: close_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(self.input_source_dialog)
        self.input_source_dialog.open = True
        self.page.update()

    def open_input_files_picker(self) -> None:
        """Open native picker for one or more Word files."""
        allowed_extensions = [suffix.lstrip(".") for suffix in sorted(SUPPORTED_WORD_SUFFIXES)]
        selected_paths = select_macos_files(
            "选择一个或多个 Word 文档",
            allowed_extensions=allowed_extensions,
            log=self.log,
        )
        if selected_paths is not None:
            if selected_paths:
                self._apply_selected_file_paths(selected_paths)
            return

        self.picker_mode = "input_files"
        self.file_picker.pick_files(
            allowed_extensions=allowed_extensions,
            allow_multiple=True,
        )

    def open_input_dir_picker(self) -> None:
        """Open native picker for a folder that contains Word files."""
        selected_path = select_macos_directory("选择包含 Word 文档的文件夹", log=self.log)
        if selected_path is not None:
            if selected_path:
                self._apply_input_folder_path(selected_path)
            return

        self.picker_mode = "input_dir"
        self.file_picker.get_directory_path()

    def open_output_dir_picker(self, e) -> None:
        """Open native picker for the output folder."""
        selected_path = select_macos_directory("选择图片输出目录", log=self.log)
        if selected_path is not None:
            if selected_path:
                self._apply_output_folder_path(selected_path)
            return

        self.picker_mode = "output_dir"
        self.file_picker.get_directory_path()

    def on_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        """Dispatch the single FilePicker result by the last requested mode."""
        if self.picker_mode == "input_files":
            self.on_files_selected(e)
        elif self.picker_mode == "input_dir":
            self.on_input_dir_selected(e)
        elif self.picker_mode == "output_dir":
            self.on_output_dir_selected(e)
        self.picker_mode = None

    def on_files_selected(self, e: ft.FilePickerResultEvent) -> None:
        """Called when one or more Word files are selected."""
        if not e.files:
            return

        selected_paths = [getattr(file, "path", "") for file in e.files]
        self._apply_selected_file_paths(selected_paths)

    def _apply_selected_file_paths(self, selected_paths: list[str]) -> None:
        """Apply and validate selected input files from any picker backend."""
        valid_files, invalid_files = self._split_supported_word_files(selected_paths)
        if not valid_files:
            self.show_dialog(
                "文件类型不支持",
                "请选择 .doc 或 .docx 格式的 Word 文档。",
            )
            return

        self.selected_files = valid_files
        self.selected_folder = ""  # Clear folder selection
        if len(self.selected_files) == 1:
            self.file_path_field.value = self.selected_files[0]
        else:
            self.file_path_field.value = f"已选择 {len(self.selected_files)} 个 Word 文件"

        if invalid_files:
            self.show_dialog(
                "已忽略不支持的文件",
                "仅支持 .doc / .docx 文件，以下文件未加入任务：\n"
                + "\n".join(Path(path).name for path in invalid_files[:5]),
            )
        self.page.update()

    def on_input_dir_selected(self, e: ft.FilePickerResultEvent) -> None:
        """Called when an input directory is selected."""
        if e.path:
            self._apply_input_folder_path(e.path)

    def _apply_input_folder_path(self, folder_path: str) -> None:
        """Apply selected input folder from any picker backend."""
        self.selected_folder = folder_path
        self.selected_files = []  # Clear files selection
        self.file_path_field.value = f"已选择文件夹: {self.selected_folder}"
        self.page.update()

    def on_output_dir_selected(self, e: ft.FilePickerResultEvent) -> None:
        """Called when an output directory is selected."""
        if e.path:
            self._apply_output_folder_path(e.path)

    def _apply_output_folder_path(self, folder_path: str) -> None:
        """Apply selected output folder from any picker backend."""
        self.output_dir_field.value = folder_path
        self.page.update()

    def on_start_click(self, e) -> None:
        """Handle run button click."""
        if not self.selected_files and not self.selected_folder:
            self.show_dialog("警告", "请先选择一个或多个 Word 文件，或者选择一个文件夹！")
            return

        invalid_files = [
            file_path for file_path in self.selected_files if not self._is_supported_word_file(Path(file_path))
        ]
        if invalid_files:
            self.show_dialog(
                "文件类型不支持",
                "任务中包含非 Word 文件，请重新选择 .doc 或 .docx 文件：\n"
                + "\n".join(Path(path).name for path in invalid_files[:5]),
            )
            return

        out_dir = self.output_dir_field.value or None
        img_format = self.format_radio.value
        dpi = int(self.dpi_dropdown.value or 150)

        # Run background thread
        self.start_task(self.run_conversion_task, out_dir, img_format, dpi)

    def run_conversion_task(
        self, out_dir: str | None, img_format: str, dpi: int
    ) -> None:
        """Synchronous task executed in the background thread."""
        files_to_convert: list[Path] = []

        if self.selected_folder:
            folder_path = Path(self.selected_folder)
            self.log(f"正在扫描文件夹: {folder_path.name} ...")
            # Scan doc and docx, ignoring temporary files (like ~$report.docx)
            files_to_convert = sorted(
                item
                for item in folder_path.glob("**/*")
                if item.is_file() and self._is_supported_word_file(item)
            )
            
            if not files_to_convert:
                self.log(f"在文件夹中未找到任何支持的 Word 文档 (.doc, .docx)", level="WARNING")
                self.show_dialog("警告", "所选文件夹中未找到任何支持的 Word 文档！")
                return
            self.log(f"扫描完毕，共发现 {len(files_to_convert)} 个 Word 文档待转换。")
        else:
            files_to_convert = [Path(f) for f in self.selected_files]
            self.log(f"已选择 {len(files_to_convert)} 个文件准备转换。")

        total_files = len(files_to_convert)
        self.log(f"开始批量转换 Word 任务，总计 {total_files} 个文件...")

        success_count = 0
        all_generated_images = []

        for index, file_path in enumerate(files_to_convert, 1):
            self.log("-" * 50)
            self.log(f"[{index}/{total_files}] 正在转换: {file_path.name}")
            self.update_progress(
                (index - 1) / total_files,
                f"正在转换 ({index}/{total_files}): {file_path.name} ..."
            )

            try:
                images = convert_word_to_images(
                    input_path=file_path,
                    output_dir=out_dir,
                    image_format=img_format,
                    dpi=dpi,
                )
                self.log(f"[{index}/{total_files}] 转换成功！共生成了 {len(images)} 张图片：")
                for idx, img in enumerate(images, 1):
                    self.log(f"  -> 已保存: {img.name}")
                success_count += 1
                all_generated_images.extend(images)
            except Exception as ex:
                self.log(f"[{index}/{total_files}] 转换失败！原因: {str(ex)}", level="ERROR")

        self.log("=" * 50)
        self.log(f"批量转换任务结束！")
        self.log(f"成功: {success_count} / {total_files}")
        if total_files - success_count > 0:
            self.log(f"失败: {total_files - success_count}", level="WARNING")

        self.update_progress(1.0, f"完成！成功转换 {success_count}/{total_files} 个文档。")
        
        if success_count == total_files:
            self.show_dialog("成功", f"批量 Word 转图片任务全部完成！\n\n共成功转换 {success_count} 个文档，生成了 {len(all_generated_images)} 张图片。")
        else:
            self.show_dialog("完成", f"批量 Word 转图片任务已结束。\n\n成功: {success_count} 个文档\n失败: {total_files - success_count} 个文档\n\n详情请查看日志区。")

    def _split_supported_word_files(self, paths: list[str]) -> tuple[list[str], list[str]]:
        valid_files = []
        invalid_files = []
        for path in paths:
            if self._is_supported_word_file(Path(path)):
                valid_files.append(path)
            else:
                invalid_files.append(path)
        return valid_files, invalid_files

    def _is_supported_word_file(self, path: Path) -> bool:
        return path.suffix.lower() in SUPPORTED_WORD_SUFFIXES and not path.name.startswith("~$")
