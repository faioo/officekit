"""Shared native file dialog helpers for OfficeKit GUI tools."""

from __future__ import annotations

import platform
import subprocess
from collections.abc import Callable

LogCallback = Callable[[str, str], None]

MACOS_TYPE_IDENTIFIERS_BY_EXTENSION = {
    "doc": "com.microsoft.word.doc",
    "docx": "org.openxmlformats.wordprocessingml.document",
    "xlsx": "org.openxmlformats.spreadsheetml.sheet",
}


def select_macos_file(
    prompt: str,
    *,
    allowed_extensions: list[str] | None = None,
    log: LogCallback | None = None,
) -> str | None:
    """Return a macOS-selected file path, an empty string on cancel, or None for fallback."""
    type_filter = _build_type_filter_clause(allowed_extensions)
    script = f'return POSIX path of (choose file with prompt "{_escape_applescript(prompt)}"{type_filter})'
    output = run_macos_dialog_script(script, log=log)
    if output is None:
        return None
    return output.strip()


def select_macos_files(
    prompt: str,
    *,
    allowed_extensions: list[str] | None = None,
    log: LogCallback | None = None,
) -> list[str] | None:
    """Return macOS-selected file paths, an empty list on cancel, or None for fallback."""
    escaped_prompt = _escape_applescript(prompt)
    type_filter = _build_type_filter_clause(allowed_extensions)
    script = f"""
set chosenFiles to choose file with prompt "{escaped_prompt}"{type_filter} with multiple selections allowed
set output to ""
repeat with chosenFile in chosenFiles
    set output to output & POSIX path of chosenFile & linefeed
end repeat
return output
"""
    output = run_macos_dialog_script(script, log=log)
    if output is None:
        return None
    return [line for line in output.splitlines() if line.strip()]


def select_macos_directory(prompt: str, *, log: LogCallback | None = None) -> str | None:
    """Return a macOS-selected folder path, an empty string on cancel, or None for fallback."""
    script = f'return POSIX path of (choose folder with prompt "{_escape_applescript(prompt)}")'
    output = run_macos_dialog_script(script, log=log)
    if output is None:
        return None
    return output.strip()


def select_macos_save_file(
    prompt: str,
    *,
    default_name: str,
    log: LogCallback | None = None,
) -> str | None:
    """Return a macOS save-file path, an empty string on cancel, or None for fallback."""
    script = (
        "return POSIX path of "
        f'(choose file name with prompt "{_escape_applescript(prompt)}" '
        f'default name "{_escape_applescript(default_name)}")'
    )
    output = run_macos_dialog_script(script, log=log)
    if output is None:
        return None
    return output.strip()


def run_macos_dialog_script(script: str, *, log: LogCallback | None = None) -> str | None:
    """Run an AppleScript picker and return stdout, or None when fallback is needed."""
    if platform.system() != "Darwin":
        return None

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        _log(log, f"macOS 原生选择器不可用，回退到 Flet 选择器: {error}", "WARNING")
        return None

    if result.returncode == 0:
        return result.stdout.strip()

    stderr = result.stderr.strip()
    if "User canceled" in stderr or "用户已取消" in stderr:
        return ""

    _log(log, f"macOS 原生选择器打开失败，回退到 Flet 选择器: {stderr}", "WARNING")
    return None


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _build_type_filter_clause(allowed_extensions: list[str] | None) -> str:
    if not allowed_extensions:
        return ""

    type_filters = []
    for extension in allowed_extensions:
        normalized = extension.strip().lower().lstrip(".")
        if normalized:
            type_identifier = MACOS_TYPE_IDENTIFIERS_BY_EXTENSION.get(normalized)
            type_filters.append(type_identifier or normalized)

    unique_type_filters = list(dict.fromkeys(type_filters))
    if not unique_type_filters:
        return ""

    type_list = ", ".join(
        f'"{_escape_applescript(type_filter)}"' for type_filter in unique_type_filters
    )
    return f" of type {{{type_list}}}"


def _log(log: LogCallback | None, message: str, level: str) -> None:
    if log:
        log(message, level)
