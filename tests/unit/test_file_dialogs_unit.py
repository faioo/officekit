"""Unit tests for shared native file dialog helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from officekit.ui import file_dialogs


def test_run_macos_dialog_script_returns_none_outside_macos(mocker):
    """Non-macOS platforms should skip AppleScript and allow Flet fallback."""
    mocker.patch("platform.system", return_value="Linux")

    result = file_dialogs.run_macos_dialog_script("return 1")

    assert result is None


def test_run_macos_dialog_script_returns_stdout_on_success(mocker):
    """Successful osascript execution should return stripped stdout."""
    mocker.patch("platform.system", return_value="Darwin")
    mocker.patch(
        "subprocess.run",
        return_value=MagicMock(returncode=0, stdout="/tmp/example\n", stderr=""),
    )

    result = file_dialogs.run_macos_dialog_script("return 1")

    assert result == "/tmp/example"


def test_run_macos_dialog_script_returns_empty_string_on_cancel(mocker):
    """AppleScript cancel should be treated as an intentional no-op."""
    mocker.patch("platform.system", return_value="Darwin")
    mocker.patch(
        "subprocess.run",
        return_value=MagicMock(returncode=1, stdout="", stderr="User canceled."),
    )

    result = file_dialogs.run_macos_dialog_script("return 1")

    assert result == ""


def test_run_macos_dialog_script_logs_and_falls_back_on_error(mocker):
    """Unexpected osascript errors should log and request fallback."""
    mocker.patch("platform.system", return_value="Darwin")
    mocker.patch(
        "subprocess.run",
        return_value=MagicMock(returncode=1, stdout="", stderr="Not authorized"),
    )
    log = MagicMock()

    result = file_dialogs.run_macos_dialog_script("return 1", log=log)

    assert result is None
    log.assert_called_once()


def test_select_macos_files_splits_multiline_output(mocker):
    """Multiple file picker output should be split into individual paths."""
    mocker.patch(
        "officekit.ui.file_dialogs.run_macos_dialog_script",
        return_value="/tmp/a.docx\n/tmp/b.doc\n",
    )

    result = file_dialogs.select_macos_files("选择文件")

    assert result == ["/tmp/a.docx", "/tmp/b.doc"]


def test_select_macos_files_adds_extension_filter_to_script(mocker):
    """Allowed extensions should be passed to the macOS native picker."""
    mock_run = mocker.patch(
        "officekit.ui.file_dialogs.run_macos_dialog_script",
        return_value="/tmp/a.docx\n",
    )

    result = file_dialogs.select_macos_files("选择文件", allowed_extensions=[".docx", "doc"])

    script = mock_run.call_args.args[0]
    assert 'of type {"docx", "doc"}' in script
    assert result == ["/tmp/a.docx"]


def test_select_macos_file_adds_extension_filter_to_script(mocker):
    """Single file picker should also support extension filtering."""
    mock_run = mocker.patch(
        "officekit.ui.file_dialogs.run_macos_dialog_script",
        return_value="/tmp/table.xlsx\n",
    )

    result = file_dialogs.select_macos_file("选择 Excel", allowed_extensions=["xlsx"])

    script = mock_run.call_args.args[0]
    assert 'of type {"xlsx"}' in script
    assert result == "/tmp/table.xlsx"
