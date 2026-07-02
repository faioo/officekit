"""Test-wide fixtures.

Isolates the shared :class:`PreferencesStore` singleton so tests never read
from or write to the user's real ``~/.officekit/preferences.json`` file.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_preferences_store(tmp_path, monkeypatch):
    """Point the module-level preferences singleton at a temp file per test."""
    from officekit.core import preferences as prefs_module

    isolated_path = tmp_path / "preferences.json"
    monkeypatch.setattr(prefs_module, "DEFAULT_PREFERENCES_FILE", isolated_path)
    prefs_module.reset_default_store_for_tests(None)
    yield
    prefs_module.reset_default_store_for_tests(None)
