"""Test-wide fixtures.

Isolates the shared :class:`PreferencesStore` singleton so tests never read
from or write to the user's real ``~/.officekit/preferences.json`` file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make ``tests`` importable so shared helpers under ``tests/support`` can be
# imported as ``from support.fake_page import ...`` regardless of pytest's
# import mode.
_TESTS_DIR = str(Path(__file__).parent)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from support.fake_page import FakePage  # noqa: E402


@pytest.fixture
def fake_page() -> FakePage:
    """Return a fresh lightweight :class:`FakePage` for UI wiring/boot tests."""
    return FakePage()


@pytest.fixture(autouse=True)
def _isolated_preferences_store(tmp_path, monkeypatch):
    """Point the module-level preferences singleton at a temp file per test."""
    from officekit.core import preferences as prefs_module

    isolated_path = tmp_path / "preferences.json"
    monkeypatch.setattr(prefs_module, "DEFAULT_PREFERENCES_FILE", isolated_path)
    prefs_module.reset_default_store_for_tests(None)
    yield
    prefs_module.reset_default_store_for_tests(None)
