#!/usr/bin/env python3
"""Cross-platform packaging automation script for OfficeKit."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

MACOS_LIBREOFFICE_APP_PATHS = [
    Path("/Applications/LibreOffice.app"),
    Path.home() / "Applications" / "LibreOffice.app",
]
MACOS_POPPLER_BINARY_NAMES = ["pdftoppm", "pdfinfo"]
MACOS_VENDOR_WARNING = (
    "macOS vendor dependencies were not fully bundled. "
    "Install LibreOffice and Poppler on the build machine for a self-contained app."
)
WINDOWS_LIBREOFFICE_PATHS = [
    *([Path(os.environ["LIBREOFFICE_HOME"])] if os.environ.get("LIBREOFFICE_HOME") else []),
    Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "LibreOffice",
    Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "LibreOffice",
    *([Path(os.environ["LOCALAPPDATA"]) / "Programs" / "LibreOffice"] if os.environ.get("LOCALAPPDATA") else []),
]
WINDOWS_POPPLER_ROOT_PATHS = [
    *([Path(os.environ["POPPLER_HOME"])] if os.environ.get("POPPLER_HOME") else []),
    Path("C:/ProgramData/chocolatey/lib/poppler/tools"),
    Path("C:/Program Files/poppler"),
    Path("C:/Program Files (x86)/poppler"),
]
WINDOWS_VENDOR_WARNING = (
    "Windows vendor dependencies were not fully bundled. "
    "Install LibreOffice and Poppler on the build machine for a self-contained app."
)


def log(message: str) -> None:
    print(f"[BUILD] {message}")


def check_and_install_dependencies() -> None:
    """Ensure packaging requirements are installed."""
    log("Checking development dependencies...")
    try:
        import flet  # noqa: F401
        import pyinstaller_init  # noqa: F401
    except ImportError:
        log("Required packaging tools (flet/pyinstaller) not found in runtime. Installing...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
        )


def build_desktop_app(target_platform: str) -> None:
    """Invokes flet pack with platform-specific optimizations."""
    host_os = platform.system().lower()
    if host_os == "darwin":
        host_platform = "mac"
    elif host_os == "windows":
        host_platform = "win"
    else:
        host_platform = "linux"

    log(f"Detected host build platform: {host_platform}")
    log(f"Requested target packaging platform: {target_platform}")

    # Enforce PyInstaller host-compilation constraints
    if target_platform != host_platform:
        log(f"Warning: PyInstaller cannot cross-compile binaries (cannot build '{target_platform}' on a '{host_platform}' host).")
        log(f"Automatically fallback to package for the current host: '{host_platform}'...")
        log("If you need to compile for the other platform, please push to GitHub to trigger automatic multi-OS CI/CD.")
        target_platform = host_platform

    # Root project pathing
    root_dir = Path(__file__).parent.resolve()
    main_script = root_dir / "src" / "officekit" / "main.py"
    dist_dir = root_dir / "dist"

    # Clean prior builds
    if dist_dir.exists():
        log(f"Cleaning existing build outputs in: {dist_dir}")
        shutil.rmtree(dist_dir, ignore_errors=True)

    build_dir = root_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    # Base packing arguments
    pack_args = [
        "flet",
        "pack",
        str(main_script),
        "--name",
        "OfficeKit",
        "--product-name",
        "OfficeKit 办公小工具平台",
        "--product-version",
        "0.1.0",
        "--file-description",
        "OfficeKit 办公自动化轻量客户端",
        "--copyright",
        "Copyright 2026 OfficeKit",
    ]

    # Platform-specific options
    if target_platform == "mac":
        # macOS: Standard onedir bundle (App directory), packed to preserve Apple sandbox features
        log("Configuring macOS .app directory packaging...")
        # onedir is default on macOS windowed bundles
        pack_args.extend([
            "--bundle-id",
            "com.officekit.app",
        ])
    elif target_platform == "win":
        # Windows: Pack into a clean single executable file
        log("Configuring Windows single file .exe packaging...")
        pack_args.append("-y")  # Answer yes to overwrite
    else:
        log("Configuring Linux standalone packaging...")

    log(f"Executing packaging command: {' '.join(pack_args)}")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root_dir / "src")

    # Run the flet pack command
    try:
        subprocess.run(pack_args, check=True, env=env)
    except subprocess.CalledProcessError as err:
        log(f"Packaging failed with exit code: {err.returncode}")
        sys.exit(err.returncode)

    # Post-build processing
    if target_platform == "mac":
        app_path = dist_dir / "OfficeKit.app"
        if app_path.exists():
            bundle_macos_vendor_dependencies(app_path)
            archive_name = dist_dir / "OfficeKit_macOS_v0.1.0"
            log(f"Compressing macOS .app bundle into: {archive_name}.zip")
            shutil.make_archive(str(archive_name), "zip", root_dir=str(dist_dir), base_dir="OfficeKit.app")
            log(f"macOS zip archive created successfully: {archive_name}.zip")
        else:
            log("Error: macOS .app bundle directory was not found in 'dist/'!")
            sys.exit(1)
    elif target_platform == "win":
        exe_path = dist_dir / "OfficeKit.exe"
        if exe_path.exists():
            archive_name = create_windows_full_archive(dist_dir, exe_path)
            log(f"Windows full zip archive created successfully: {archive_name}.zip")
        else:
            log("Error: Windows .exe was not found in 'dist/'!")
            sys.exit(1)

    log("Packaging workflow completed successfully!")


def bundle_macos_vendor_dependencies(app_path: Path) -> None:
    """Bundle external Word conversion tools into the macOS .app resources."""
    resources_dir = app_path / "Contents" / "Resources"
    vendor_dir = resources_dir / "vendor"
    vendor_dir.mkdir(parents=True, exist_ok=True)

    libreoffice_ok = bundle_macos_libreoffice(vendor_dir)
    poppler_ok = bundle_macos_poppler(vendor_dir)

    if libreoffice_ok and poppler_ok:
        log("Bundled macOS Word conversion vendor dependencies successfully.")
    else:
        log(f"Warning: {MACOS_VENDOR_WARNING}")

    codesign_macos_app(app_path)


def bundle_macos_libreoffice(vendor_dir: Path) -> bool:
    """Copy LibreOffice.app into the vendor directory if available."""
    source_app = next((path for path in MACOS_LIBREOFFICE_APP_PATHS if path.exists()), None)
    if not source_app:
        log("Warning: LibreOffice.app was not found in /Applications or ~/Applications.")
        return False

    destination_app = vendor_dir / "LibreOffice.app"
    if destination_app.exists():
        shutil.rmtree(destination_app, ignore_errors=True)

    log(f"Bundling LibreOffice.app from: {source_app}")
    shutil.copytree(source_app, destination_app, symlinks=True)
    return (destination_app / "Contents" / "MacOS" / "soffice").exists()


def bundle_macos_poppler(vendor_dir: Path) -> bool:
    """Copy Poppler binaries and their Homebrew dylib dependencies."""
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        log("Warning: pdftoppm was not found on PATH. Install Poppler with `brew install poppler`.")
        return False

    poppler_dir = vendor_dir / "poppler"
    bin_dir = poppler_dir / "bin"
    lib_dir = poppler_dir / "lib"
    if poppler_dir.exists():
        shutil.rmtree(poppler_dir, ignore_errors=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    lib_dir.mkdir(parents=True, exist_ok=True)

    copied_binaries = []
    for binary_name in MACOS_POPPLER_BINARY_NAMES:
        binary_path = shutil.which(binary_name)
        if not binary_path:
            continue
        destination = bin_dir / binary_name
        log(f"Bundling Poppler binary: {binary_path}")
        shutil.copy2(binary_path, destination)
        copied_binaries.append(destination)

    if not copied_binaries:
        return False

    copied_libraries: dict[str, Path] = {}
    for binary in copied_binaries:
        copy_macos_dylib_dependencies(binary, lib_dir, copied_libraries)

    for binary in copied_binaries:
        rewrite_macos_dylib_references(binary, "@executable_path/../lib")

    for library in copied_libraries.values():
        set_macos_dylib_id(library)
        rewrite_macos_dylib_references(library, "@loader_path")

    return (bin_dir / "pdftoppm").exists()


def copy_macos_dylib_dependencies(
    binary_path: Path,
    lib_dir: Path,
    copied_libraries: dict[str, Path],
) -> None:
    """Recursively copy non-system dylib dependencies used by a Mach-O file."""
    for dependency in list_macos_dylib_dependencies(binary_path):
        if not should_bundle_macos_dependency(dependency):
            continue
        dependency_path = Path(dependency)
        destination = lib_dir / dependency_path.name
        if dependency not in copied_libraries:
            log(f"Bundling dylib dependency: {dependency_path}")
            shutil.copy2(dependency_path, destination)
            copied_libraries[dependency] = destination
            copy_macos_dylib_dependencies(destination, lib_dir, copied_libraries)


def list_macos_dylib_dependencies(binary_path: Path) -> list[str]:
    """Return linked dynamic libraries from otool -L output."""
    result = subprocess.run(
        ["otool", "-L", str(binary_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    dependencies = []
    for line in result.stdout.splitlines()[1:]:
        dependency = line.strip().split(" ", 1)[0]
        if dependency:
            dependencies.append(dependency)
    return dependencies


def should_bundle_macos_dependency(dependency: str) -> bool:
    """Bundle Homebrew/MacPorts dylibs, but leave system and relative libs alone."""
    if dependency.startswith(("@", "/usr/lib/", "/System/Library/")):
        return False
    return dependency.startswith(("/opt/homebrew/", "/usr/local/", "/opt/local/"))


def rewrite_macos_dylib_references(binary_path: Path, relative_lib_prefix: str) -> None:
    """Rewrite bundled dylib references to point at the app-local vendor lib dir."""
    for dependency in list_macos_dylib_dependencies(binary_path):
        if not should_bundle_macos_dependency(dependency):
            continue
        new_reference = f"{relative_lib_prefix}/{Path(dependency).name}"
        subprocess.run(
            ["install_name_tool", "-change", dependency, new_reference, str(binary_path)],
            check=True,
        )


def set_macos_dylib_id(library_path: Path) -> None:
    """Set a copied dylib's own install name to a relative @loader_path reference."""
    subprocess.run(
        ["install_name_tool", "-id", f"@loader_path/{library_path.name}", str(library_path)],
        check=True,
    )


def codesign_macos_app(app_path: Path) -> None:
    """Ad-hoc re-sign the bundle after adding vendor files to avoid stale signatures."""
    try:
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        log("Ad-hoc codesigned macOS app after bundling vendor dependencies.")
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        log(f"Warning: codesign failed or is unavailable: {error}")


def create_windows_full_archive(dist_dir: Path, exe_path: Path) -> Path:
    """Create a Windows full distribution zip with OfficeKit.exe and vendor tools."""
    package_dir = dist_dir / "OfficeKit_Windows_v0.1.0"
    if package_dir.exists():
        shutil.rmtree(package_dir, ignore_errors=True)
    package_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(exe_path, package_dir / exe_path.name)
    bundle_windows_vendor_dependencies(package_dir / "vendor")

    archive_name = dist_dir / "OfficeKit_Windows_v0.1.0"
    shutil.make_archive(str(archive_name), "zip", root_dir=str(dist_dir), base_dir=package_dir.name)
    return archive_name


def bundle_windows_vendor_dependencies(vendor_dir: Path) -> None:
    """Bundle external Word conversion tools beside the Windows executable."""
    vendor_dir.mkdir(parents=True, exist_ok=True)

    libreoffice_ok = bundle_windows_libreoffice(vendor_dir)
    poppler_ok = bundle_windows_poppler(vendor_dir)

    if libreoffice_ok and poppler_ok:
        log("Bundled Windows Word conversion vendor dependencies successfully.")
    else:
        log(f"Warning: {WINDOWS_VENDOR_WARNING}")


def bundle_windows_libreoffice(vendor_dir: Path) -> bool:
    """Copy a Windows LibreOffice installation into the vendor directory if available."""
    source_dir = next((path for path in WINDOWS_LIBREOFFICE_PATHS if path and (path / "program" / "soffice.exe").exists()), None)
    if not source_dir:
        log("Warning: LibreOffice was not found in common Windows install locations.")
        return False

    destination_dir = vendor_dir / "LibreOffice"
    if destination_dir.exists():
        shutil.rmtree(destination_dir, ignore_errors=True)

    log(f"Bundling Windows LibreOffice from: {source_dir}")
    shutil.copytree(source_dir, destination_dir, symlinks=True)
    return (destination_dir / "program" / "soffice.exe").exists()


def bundle_windows_poppler(vendor_dir: Path) -> bool:
    """Copy a Windows Poppler distribution into the vendor directory if available."""
    source_root = find_windows_poppler_root()
    if not source_root:
        log("Warning: Poppler was not found. Install it with `choco install poppler -y`.")
        return False

    destination_root = vendor_dir / "poppler"
    if destination_root.exists():
        shutil.rmtree(destination_root, ignore_errors=True)

    log(f"Bundling Windows Poppler from: {source_root}")
    shutil.copytree(source_root, destination_root, symlinks=True)
    return (destination_root / "bin" / "pdftoppm.exe").exists()


def find_windows_poppler_root() -> Path | None:
    """Find the Poppler root that contains bin/pdftoppm.exe."""
    for root in WINDOWS_POPPLER_ROOT_PATHS:
        poppler_root = find_poppler_root_under(root)
        if poppler_root:
            return poppler_root

    path_binary = shutil.which("pdftoppm.exe") or shutil.which("pdftoppm")
    if not path_binary:
        return None

    binary_path = Path(path_binary)
    if binary_path.parent.name.lower() == "bin":
        return binary_path.parent.parent
    return None


def find_poppler_root_under(root: Path) -> Path | None:
    """Search a candidate root for a bin/pdftoppm.exe layout."""
    if not root or not root.exists():
        return None

    direct_candidates = [root, root / "Library"]
    for candidate in direct_candidates:
        if (candidate / "bin" / "pdftoppm.exe").exists():
            return candidate

    for binary_path in root.rglob("pdftoppm.exe"):
        if binary_path.parent.name.lower() == "bin":
            return binary_path.parent.parent
    return None


def main() -> None:
    # Set executing directory to workspace root
    os.chdir(Path(__file__).parent.resolve())

    # Argument parsing
    parser = argparse.ArgumentParser(description="Package OfficeKit Desktop application.")
    parser.add_argument(
        "-p", "--platform",
        choices=["win", "mac"],
        default="win",
        help="Target packaging platform (default: win).",
    )
    args = parser.parse_args()

    check_and_install_dependencies()
    build_desktop_app(args.platform)


if __name__ == "__main__":
    main()
