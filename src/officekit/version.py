"""Version resolution helpers for OfficeKit."""

from __future__ import annotations

import importlib
import os
import subprocess
from pathlib import Path

DEFAULT_VERSION = "0.0.0+dev"
VERSION_ENV_KEYS = ("OFFICEKIT_VERSION", "RELEASE_VERSION")


def get_version(*, include_generated: bool = True) -> str:
    """Return the app/package version without a leading ``v``."""
    return normalize_version(
        (_read_generated_version() if include_generated else None)
        or _read_environment_version()
        or _read_git_tag_version()
        or DEFAULT_VERSION
    )


def get_release_version(*, include_generated: bool = True) -> str:
    """Return the release version in Git tag form, for example ``v0.1.7``."""
    version = get_version(include_generated=include_generated)
    return version if version.startswith("v") else f"v{version}"


def normalize_version(value: str) -> str:
    """Normalize tag-like version strings to package version form."""
    version = value.strip()
    if version.startswith("refs/tags/"):
        version = version.removeprefix("refs/tags/")
    if len(version) > 1 and version[0] == "v" and version[1].isdigit():
        version = version[1:]
    return version or DEFAULT_VERSION


def _read_generated_version() -> str | None:
    try:
        generated = importlib.import_module("officekit._version")
    except ImportError:
        return None

    version = getattr(generated, "__version__", None)
    return str(version) if version else None


def _read_environment_version() -> str | None:
    for key in VERSION_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            return value
    return None


def _read_git_tag_version() -> str | None:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    version = result.stdout.strip()
    return version or None
