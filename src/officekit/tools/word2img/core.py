"""Business logic for converting Word documents to images."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

SUPPORTED_WORD_SUFFIXES = {".doc", ".docx"}
SUPPORTED_IMAGE_FORMATS = {"png", "jpeg"}


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
        command = shutil.which(name)
        if command:
            return command

    raise RuntimeError(f"Missing required command: one of {', '.join(names)}")


def _run(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or error.stdout.strip() or str(error)
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{details}") from error
