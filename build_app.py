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
            log(f"Windows single-file executable created successfully: {exe_path}")
        else:
            log("Error: Windows .exe was not found in 'dist/'!")
            sys.exit(1)

    log("Packaging workflow completed successfully!")


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
