"""Business logic for converting Word documents to images."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SUPPORTED_WORD_SUFFIXES = {".doc", ".docx"}
SUPPORTED_IMAGE_FORMATS = {"png", "jpeg"}
COMMON_COMMAND_PATHS = {
    "soffice": (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/opt/homebrew/bin/soffice",
        "/usr/local/bin/soffice",
        "C:/Program Files/LibreOffice/program/soffice.exe",
        "C:/Program Files (x86)/LibreOffice/program/soffice.exe",
    ),
    "libreoffice": (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/opt/homebrew/bin/libreoffice",
        "/usr/local/bin/libreoffice",
        "C:/Program Files/LibreOffice/program/soffice.exe",
        "C:/Program Files (x86)/LibreOffice/program/soffice.exe",
    ),
    "pdftoppm": (
        "/opt/homebrew/bin/pdftoppm",
        "/usr/local/bin/pdftoppm",
        "/usr/bin/pdftoppm",
        "C:/ProgramData/chocolatey/lib/poppler/tools/Library/bin/pdftoppm.exe",
        "C:/ProgramData/chocolatey/bin/pdftoppm.exe",
    ),
}


def convert_word_to_images(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    image_format: str = "png",
    dpi: int = 150,
) -> list[Path]:
    """Convert a Word document into one image per page."""
    source = Path(input_path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Word document not found: {source}")

    if source.suffix.lower() not in SUPPORTED_WORD_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_WORD_SUFFIXES))
        raise ValueError(f"Unsupported Word document type: {source.suffix}. Expected {supported}.")

    image_format = image_format.lower()
    if image_format not in SUPPORTED_IMAGE_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_IMAGE_FORMATS))
        raise ValueError(f"Unsupported image format: {image_format}. Expected {supported}.")

    destination = Path(output_dir).expanduser().resolve() if output_dir else source.with_name(f"{source.stem}_images")
    destination.mkdir(parents=True, exist_ok=True)

    soffice = _find_command("soffice", "libreoffice")
    pdftoppm = _find_command("pdftoppm")

    with tempfile.TemporaryDirectory(prefix="officekit-word2img-") as temp_dir:
        temp_path = Path(temp_dir)
        _run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_path),
                str(source),
            ]
        )

        pdf_path = temp_path / f"{source.stem}.pdf"
        if not pdf_path.exists():
            raise RuntimeError("LibreOffice did not produce a PDF file.")

        output_prefix = destination / source.stem
        format_flag = "-png" if image_format == "png" else "-jpeg"
        _run([pdftoppm, format_flag, "-r", str(dpi), str(pdf_path), str(output_prefix)])

    extension = "jpg" if image_format == "jpeg" else image_format
    images = sorted(destination.glob(f"{source.stem}-*.{extension}"))
    if not images:
        raise RuntimeError("No images were generated from the Word document.")

    return images


def _find_command(*names: str) -> str:
    for name in names:
        for command_path in _bundled_command_paths(name):
            if command_path.exists():
                return str(command_path)

        command = shutil.which(name)
        if command:
            return command

        for command_path in COMMON_COMMAND_PATHS.get(name, ()):
            if Path(command_path).exists():
                return command_path

    raise RuntimeError(_missing_command_message(names))


def _bundled_command_paths(name: str) -> tuple[Path, ...]:
    """Return app-bundled command candidates for packaged desktop builds."""
    candidates: list[Path] = []
    for vendor_dir in _candidate_vendor_dirs():
        if name in {"soffice", "libreoffice"}:
            candidates.append(vendor_dir / "LibreOffice.app" / "Contents" / "MacOS" / "soffice")
            candidates.append(vendor_dir / "LibreOffice" / "program" / "soffice.exe")
        elif name == "pdftoppm":
            candidates.append(vendor_dir / "poppler" / "bin" / "pdftoppm")
            candidates.append(vendor_dir / "poppler" / "bin" / "pdftoppm.exe")
            candidates.append(vendor_dir / "poppler" / "Library" / "bin" / "pdftoppm.exe")
    return tuple(candidates)


def _candidate_vendor_dirs() -> tuple[Path, ...]:
    """Find vendor directories in a frozen .app bundle and in local development."""
    candidates: list[Path] = []

    executable_path = Path(sys.executable).resolve()
    candidates.append(executable_path.parent / "vendor")

    for parent in executable_path.parents:
        if parent.name == "Contents":
            candidates.append(parent / "Resources" / "vendor")
            break

    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS).resolve() / "vendor")  # type: ignore[attr-defined]

    project_root = Path(__file__).resolve().parents[4]
    candidates.append(project_root / "vendor")

    unique_candidates = []
    seen = set()
    for candidate in candidates:
        if candidate not in seen:
            unique_candidates.append(candidate)
            seen.add(candidate)
    return tuple(unique_candidates)


def _missing_command_message(names: tuple[str, ...]) -> str:
    missing_commands = ", ".join(names)
    hints = []

    if "soffice" in names or "libreoffice" in names:
        hints.append(
            "未找到 LibreOffice。macOS 可执行：`brew install --cask libreoffice`；"
            "Windows 可执行：`choco install libreoffice-fresh -y`，或从 "
            "https://www.libreoffice.org 下载。"
        )
    if "pdftoppm" in names:
        hints.append(
            "未找到 Poppler/pdftoppm。macOS 可执行：`brew install poppler`；"
            "Windows 可执行：`choco install poppler -y`。"
        )
        bundled_paths = "\n".join(f"- {path}" for path in _bundled_command_paths("pdftoppm"))
        if bundled_paths:
            hints.append(
                "已检查内置 Poppler 路径：\n"
                f"{bundled_paths}\n"
                f"当前 Python 可执行文件：{sys.executable}"
            )

    hint_text = "\n".join(hints) if hints else "请安装对应命令后重试。"
    return f"缺少 Word 转图片依赖: 未找到 {missing_commands}。\n{hint_text}"


def _run(command: list[str]) -> None:
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=_command_env(command[0]),
        )
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or error.stdout.strip() or str(error)
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{details}") from error


def _command_env(command_path: str) -> dict[str, str] | None:
    """Expose bundled Poppler libraries to subprocesses when present."""
    path = Path(command_path).resolve()
    if path.name.lower() not in {"pdftoppm", "pdftoppm.exe"}:
        return None

    env = os.environ.copy()
    if path.parent.name.lower() == "bin":
        existing_path = env.get("PATH")
        env["PATH"] = f"{path.parent}{os.pathsep}{existing_path}" if existing_path else str(path.parent)

    lib_dir = path.parent.parent / "lib"
    if lib_dir.exists():
        existing = env.get("DYLD_LIBRARY_PATH")
        env["DYLD_LIBRARY_PATH"] = f"{lib_dir}{os.pathsep}{existing}" if existing else str(lib_dir)
    return env
