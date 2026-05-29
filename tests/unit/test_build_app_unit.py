"""Unit tests for desktop packaging helpers."""

from __future__ import annotations

import importlib.util
import io
import sys
import zipfile
from pathlib import Path


BUILD_APP_PATH = Path(__file__).resolve().parents[2] / "build_app.py"
SPEC = importlib.util.spec_from_file_location("build_app", BUILD_APP_PATH)
build_app = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(build_app)


def test_log_handles_non_utf8_stdout(mocker):
    """Windows cp1252 consoles should not crash when build logs contain Chinese."""
    output = io.BytesIO()
    stream = io.TextIOWrapper(output, encoding="cp1252", errors="strict")
    mocker.patch.object(sys, "stdout", stream)

    build_app.log("OfficeKit 办公小工具平台")
    stream.flush()

    assert b"OfficeKit" in output.getvalue()
    assert br"\u529e\u516c" in output.getvalue()


def test_find_poppler_root_under_accepts_library_layout(tmp_path):
    """Chocolatey Poppler packages may place binaries under tools/Library/bin."""
    tools_dir = tmp_path / "tools"
    pdftoppm = tools_dir / "Library" / "bin" / "pdftoppm.exe"
    pdftoppm.parent.mkdir(parents=True)
    pdftoppm.write_text("mock")

    result = build_app.find_poppler_root_under(tools_dir)

    assert result == tools_dir / "Library"


def test_bundle_windows_poppler_copies_bin_layout(mocker, tmp_path):
    """Windows full builds should copy Poppler into vendor/poppler."""
    source_root = tmp_path / "source-poppler"
    pdftoppm = source_root / "bin" / "pdftoppm.exe"
    pdftoppm.parent.mkdir(parents=True)
    pdftoppm.write_text("mock")
    mocker.patch.object(build_app, "find_windows_poppler_root", return_value=source_root)

    vendor_dir = tmp_path / "vendor"
    result = build_app.bundle_windows_poppler(vendor_dir)

    assert result is True
    assert (vendor_dir / "poppler" / "bin" / "pdftoppm.exe").exists()


def test_create_windows_full_archive_includes_exe_and_vendor_dir(mocker, tmp_path):
    """Windows release artifact should be a zip containing exe plus vendor folder."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    exe_path = dist_dir / "OfficeKit.exe"
    exe_path.write_text("mock exe")

    def fake_bundle(vendor_dir):
        vendor_dir.mkdir(parents=True)
        (vendor_dir / "marker.txt").write_text("vendor")

    mocker.patch.object(build_app, "bundle_windows_vendor_dependencies", side_effect=fake_bundle)

    archive_name = build_app.create_windows_full_archive(dist_dir, exe_path)

    assert archive_name == dist_dir / "OfficeKit_Windows_v0.1.0"
    with zipfile.ZipFile(f"{archive_name}.zip") as archive:
        names = set(archive.namelist())

    assert "OfficeKit_Windows_v0.1.0/OfficeKit.exe" in names
    assert "OfficeKit_Windows_v0.1.0/vendor/marker.txt" in names
