"""Word-to-PDF backend converters.

Two backends are supported for the Word -> PDF step:

- ``convert_via_word_com``: Windows-only. Drives MS Word through COM
  automation (``pywin32``) so pagination matches what the user sees in Word
  itself. This is the highest-fidelity path.
- ``convert_via_libreoffice``: Cross-platform fallback via ``soffice``.

Both functions accept an absolute source path and an output directory, and
return the produced PDF path. They raise ``RuntimeError`` on failure so the
dispatcher in :mod:`officekit.tools.word2img.core` can decide whether to
fall back.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("officekit")

WD_FORMAT_PDF = 17  # Word.WdSaveFormat.wdFormatPDF


def convert_via_word_com(source: Path, output_dir: Path) -> Path:
    """Convert ``source`` to PDF using MS Word COM automation.

    Only supported on Windows with MS Word installed. Raises ``RuntimeError``
    if the backend is unavailable or the conversion fails, so callers may
    fall back to another backend.
    """
    if sys.platform != "win32":
        raise RuntimeError("Word COM backend is only available on Windows.")

    try:
        import pythoncom  # type: ignore[import-not-found]
        from win32com.client import DispatchEx  # type: ignore[import-not-found]
        from pywintypes import com_error  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError(
            f"pywin32 is not available; cannot use Word COM backend: {error}"
        ) from error

    source_abs = source.expanduser().resolve()
    if not source_abs.exists():
        raise RuntimeError(f"Word document not found: {source_abs}")

    output_dir_abs = output_dir.expanduser().resolve()
    output_dir_abs.mkdir(parents=True, exist_ok=True)
    output_pdf = output_dir_abs / f"{source_abs.stem}.pdf"

    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        try:
            word = DispatchEx("Word.Application")
        except com_error as error:
            raise RuntimeError(
                "Failed to launch Microsoft Word via COM. "
                "Please ensure Microsoft Word is installed and licensed."
            ) from error

        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone
        try:
            word.ScreenUpdating = False
        except Exception:
            pass

        try:
            doc = word.Documents.Open(
                str(source_abs),
                ReadOnly=True,
                ConfirmConversions=False,
                AddToRecentFiles=False,
                Visible=False,
            )
        except com_error as error:
            raise RuntimeError(
                f"Microsoft Word failed to open '{source_abs.name}': {error}"
            ) from error

        try:
            doc.SaveAs2(str(output_pdf), FileFormat=WD_FORMAT_PDF)
        except AttributeError:
            doc.SaveAs(str(output_pdf), FileFormat=WD_FORMAT_PDF)
        except com_error as error:
            raise RuntimeError(
                f"Microsoft Word failed to export '{source_abs.name}' to PDF: {error}"
            ) from error
    finally:
        if doc is not None:
            try:
                doc.Close(SaveChanges=0)
            except Exception as error:
                logger.debug("Word doc.Close failed during cleanup: %s", error)
        if word is not None:
            try:
                word.Quit()
            except Exception as error:
                logger.debug("Word.Quit failed during cleanup: %s", error)
        try:
            pythoncom.CoUninitialize()
        except Exception as error:
            logger.debug("pythoncom.CoUninitialize failed: %s", error)

    if not output_pdf.exists():
        raise RuntimeError(
            "Microsoft Word did not produce a PDF file at the expected location."
        )
    return output_pdf


def convert_via_libreoffice(source: Path, output_dir: Path, soffice: str) -> Path:
    """Convert ``source`` to PDF using LibreOffice's ``soffice --convert-to``.

    ``soffice`` must be an absolute path to the LibreOffice binary; the
    dispatcher is responsible for locating it via :func:`_find_command`.
    """
    source_abs = source.expanduser().resolve()
    if not source_abs.exists():
        raise RuntimeError(f"Word document not found: {source_abs}")

    output_dir_abs = output_dir.expanduser().resolve()
    output_dir_abs.mkdir(parents=True, exist_ok=True)

    command = [
        soffice,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir_abs),
        str(source_abs),
    ]
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or error.stdout.strip() or str(error)
        raise RuntimeError(
            f"LibreOffice conversion failed: {' '.join(command)}\n{details}"
        ) from error
    except FileNotFoundError as error:
        raise RuntimeError(
            f"LibreOffice executable not found at {soffice}: {error}"
        ) from error

    output_pdf = output_dir_abs / f"{source_abs.stem}.pdf"
    if not output_pdf.exists():
        raise RuntimeError(
            "LibreOffice did not produce a PDF file at the expected location."
        )
    return output_pdf


__all__ = [
    "convert_via_word_com",
    "convert_via_libreoffice",
    "WD_FORMAT_PDF",
]
