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
        (vendor_dir / "LibreOffice" / "program").mkdir(parents=True)
        (vendor_dir / "LibreOffice" / "program" / "soffice.exe").write_text("mock soffice")
        (vendor_dir / "poppler" / "bin").mkdir(parents=True)
        (vendor_dir / "poppler" / "bin" / "pdftoppm.exe").write_text("mock pdftoppm")
        (vendor_dir / "marker.txt").write_text("vendor")

    mocker.patch.object(build_app, "bundle_windows_vendor_dependencies", side_effect=fake_bundle)

    archive_name = build_app.create_windows_full_archive(dist_dir, exe_path, "v9.8.7")

    assert archive_name == dist_dir / "OfficeKit_Windows_v9.8.7"
    with zipfile.ZipFile(f"{archive_name}.zip") as archive:
        names = set(archive.namelist())

    assert "OfficeKit_Windows_v9.8.7/OfficeKit.exe" in names
    assert "OfficeKit_Windows_v9.8.7/vendor/marker.txt" in names
    assert "OfficeKit_Windows_v9.8.7/vendor/poppler/bin/pdftoppm.exe" in names


def test_create_windows_full_archive_fails_without_poppler(mocker, tmp_path):
    """Windows release archives should not be created when Poppler is missing."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    exe_path = dist_dir / "OfficeKit.exe"
    exe_path.write_text("mock exe")

    def fake_bundle(vendor_dir):
        (vendor_dir / "LibreOffice" / "program").mkdir(parents=True)
        (vendor_dir / "LibreOffice" / "program" / "soffice.exe").write_text("mock soffice")

    mocker.patch.object(build_app, "bundle_windows_vendor_dependencies", side_effect=fake_bundle)

    try:
        build_app.create_windows_full_archive(dist_dir, exe_path, "v9.8.7")
    except RuntimeError as error:
        assert "pdftoppm.exe" in str(error)
    else:
        raise AssertionError("Expected missing Poppler to fail the Windows archive build")


def test_resolve_build_versions_reads_environment(monkeypatch):
    """Builds should resolve one version pair from the workflow environment."""
    monkeypatch.setenv("OFFICEKIT_VERSION", "v2.3.4")
    monkeypatch.delenv("RELEASE_VERSION", raising=False)

    product_version, release_version = build_app.resolve_build_versions(BUILD_APP_PATH.parent)

    assert product_version == "2.3.4"
    assert release_version == "v2.3.4"


def test_write_generated_version_module_is_temporary(tmp_path):
    """Generated version files should be removable build artifacts."""
    package_dir = tmp_path / "src" / "officekit"
    package_dir.mkdir(parents=True)

    version_module = build_app.write_generated_version_module(tmp_path, "2.3.4")

    assert version_module == package_dir / "_version.py"
    assert '__version__ = "2.3.4"' in version_module.read_text(encoding="utf-8")

    build_app.remove_generated_version_module(version_module)
    assert not version_module.exists()


def test_copy_macos_dylib_dependencies_resolves_rpath_dependencies(mocker, tmp_path):
    """Homebrew Poppler links libpoppler through @rpath and must still be bundled."""
    homebrew_root = tmp_path / "homebrew"
    binary = homebrew_root / "bin" / "pdftoppm"
    poppler_lib = homebrew_root / "lib" / "libpoppler.159.dylib"
    binary.parent.mkdir(parents=True)
    poppler_lib.parent.mkdir(parents=True)
    binary.write_text("mock binary")
    poppler_lib.write_text("mock lib")

    mocker.patch.object(build_app, "MACOS_VENDOR_DEPENDENCY_PREFIXES", (str(homebrew_root),))
    mocker.patch.object(
        build_app,
        "list_macos_dylib_dependencies",
        side_effect=lambda path: ["@rpath/libpoppler.159.dylib"] if Path(path) == binary else [],
    )
    mocker.patch.object(build_app, "list_macos_rpaths", return_value=[str(homebrew_root / "lib")])

    copied_libraries: dict[str, Path] = {}
    vendor_lib_dir = tmp_path / "vendor" / "poppler" / "lib"
    vendor_lib_dir.mkdir(parents=True)

    build_app.copy_macos_dylib_dependencies(binary, vendor_lib_dir, copied_libraries)

    assert (vendor_lib_dir / "libpoppler.159.dylib").exists()


def test_rewrite_macos_dylib_references_rewrites_rpath_dependencies(mocker, tmp_path):
    """install_name_tool should point @rpath Poppler dependencies at the bundled lib dir."""
    homebrew_root = tmp_path / "homebrew"
    binary = homebrew_root / "bin" / "pdftoppm"
    poppler_lib = homebrew_root / "lib" / "libpoppler.159.dylib"
    binary.parent.mkdir(parents=True)
    poppler_lib.parent.mkdir(parents=True)
    binary.write_text("mock binary")
    poppler_lib.write_text("mock lib")

    mocker.patch.object(build_app, "MACOS_VENDOR_DEPENDENCY_PREFIXES", (str(homebrew_root),))
    mocker.patch.object(build_app, "list_macos_dylib_dependencies", return_value=["@rpath/libpoppler.159.dylib"])
    mocker.patch.object(build_app, "list_macos_rpaths", return_value=[str(homebrew_root / "lib")])
    run = mocker.patch.object(build_app.subprocess, "run")

    build_app.rewrite_macos_dylib_references(binary, "@executable_path/../lib")

    run.assert_called_once_with(
        [
            "install_name_tool",
            "-change",
            "@rpath/libpoppler.159.dylib",
            "@executable_path/../lib/libpoppler.159.dylib",
            str(binary),
        ],
        check=True,
    )


def test_bundle_macos_poppler_codesigns_binaries_and_libraries(mocker, tmp_path):
    """Mutated bundled Poppler files should be re-signed before the app is archived."""
    homebrew_root = tmp_path / "homebrew"
    source_bin = homebrew_root / "bin"
    source_lib = homebrew_root / "lib"
    source_bin.mkdir(parents=True)
    source_lib.mkdir(parents=True)
    for binary_name in build_app.MACOS_POPPLER_BINARY_NAMES:
        (source_bin / binary_name).write_text("mock binary")
    (source_lib / "libpoppler.159.dylib").write_text("mock lib")

    mocker.patch.object(build_app, "MACOS_VENDOR_DEPENDENCY_PREFIXES", (str(homebrew_root),))
    mocker.patch.object(
        build_app.shutil,
        "which",
        side_effect=lambda name: str(source_bin / name) if (source_bin / name).exists() else None,
    )
    mocker.patch.object(
        build_app,
        "list_macos_dylib_dependencies",
        side_effect=lambda path: ["@rpath/libpoppler.159.dylib"]
        if Path(path).name in build_app.MACOS_POPPLER_BINARY_NAMES
        else [],
    )
    mocker.patch.object(build_app, "list_macos_rpaths", return_value=[str(source_lib)])
    mocker.patch.object(build_app.subprocess, "run")
    codesign = mocker.patch.object(build_app, "codesign_macos_file")

    result = build_app.bundle_macos_poppler(tmp_path / "vendor")

    assert result is True
    signed_names = {call.args[0].name for call in codesign.call_args_list}
    assert {"pdftoppm", "pdfinfo", "libpoppler.159.dylib"}.issubset(signed_names)
