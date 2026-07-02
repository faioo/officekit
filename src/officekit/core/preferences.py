"""Generic per-tool user preference persistence.

Stores lightweight UI state (dropdown selections, numeric inputs, output
directories) in ``~/.officekit/preferences.json`` so tools can restore the
user's last configuration on the next launch. This layer is deliberately
best-effort: any I/O error is swallowed and logged so persistence failures
never break the primary tool workflow.

Only whitelisted, non-sensitive UI values should be stored. Never persist
credentials, tokens, PII, or arbitrary file paths chosen for the current run.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger("officekit")

DEFAULT_PREFERENCES_DIR = Path.home() / ".officekit"
DEFAULT_PREFERENCES_FILE = DEFAULT_PREFERENCES_DIR / "preferences.json"


class PreferencesStore:
    """Thread-safe JSON-backed key/value store scoped by tool id."""

    def __init__(self, file_path: Path | None = None) -> None:
        self._file_path = Path(file_path) if file_path else DEFAULT_PREFERENCES_FILE
        self._lock = threading.RLock()
        self._data: dict[str, dict[str, Any]] = {}
        self._loaded = False

    @property
    def file_path(self) -> Path:
        return self._file_path

    def load(self) -> None:
        """Load preferences from disk into memory. Idempotent and fail-safe."""
        with self._lock:
            self._data = self._read_from_disk()
            self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def _read_from_disk(self) -> dict[str, dict[str, Any]]:
        try:
            if not self._file_path.exists():
                return {}
            with self._file_path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError) as error:
            logger.warning(
                "Failed to read preferences file %s: %s. Falling back to empty preferences.",
                self._file_path,
                error,
            )
            return {}

        if not isinstance(raw, dict):
            logger.warning(
                "Preferences file %s has an unexpected structure; ignoring it.",
                self._file_path,
            )
            return {}

        cleaned: dict[str, dict[str, Any]] = {}
        for tool_id, values in raw.items():
            if isinstance(tool_id, str) and isinstance(values, dict):
                cleaned[tool_id] = dict(values)
        return cleaned

    def get(self, tool_id: str, key: str, default: Any = None) -> Any:
        """Return the stored value for ``tool_id.key`` or ``default``."""
        self._ensure_loaded()
        with self._lock:
            return self._data.get(tool_id, {}).get(key, default)

    def set(self, tool_id: str, key: str, value: Any) -> None:
        """Persist ``value`` under ``tool_id.key``.

        ``None`` and empty strings are treated as "clear this entry" so that
        transient empty UI state does not leak into the on-disk file. Values
        that cannot be JSON-encoded (e.g. mock objects in tests, unexpected
        Flet types) are silently rejected instead of corrupting the store.
        """
        if not tool_id or not key:
            return
        if value is None or (isinstance(value, str) and value == ""):
            self._ensure_loaded()
            with self._lock:
                bucket = self._data.setdefault(tool_id, {})
                bucket.pop(key, None)
                self._flush_to_disk_locked()
            return

        try:
            json.dumps(value)
        except (TypeError, ValueError) as error:
            logger.debug(
                "Skipping non-serializable preference %s.%s (%s): %s",
                tool_id,
                key,
                type(value).__name__,
                error,
            )
            return

        self._ensure_loaded()
        with self._lock:
            bucket = self._data.setdefault(tool_id, {})
            bucket[key] = value
            self._flush_to_disk_locked()

    def snapshot(self, tool_id: str) -> dict[str, Any]:
        """Return a shallow copy of the values recorded for ``tool_id``."""
        self._ensure_loaded()
        with self._lock:
            return dict(self._data.get(tool_id, {}))

    def _flush_to_disk_locked(self) -> None:
        """Atomically write the current state to disk. Never raises."""
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                prefix=".preferences-",
                suffix=".json.tmp",
                dir=str(self._file_path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(self._data, fh, ensure_ascii=False, indent=2)
                os.replace(tmp_name, self._file_path)
            except Exception:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise
        except OSError as error:
            logger.warning(
                "Failed to persist preferences to %s: %s",
                self._file_path,
                error,
            )


_default_store_lock = threading.Lock()
_default_store: PreferencesStore | None = None


def get_preferences_store() -> PreferencesStore:
    """Return the process-wide default :class:`PreferencesStore` singleton."""
    global _default_store
    if _default_store is None:
        with _default_store_lock:
            if _default_store is None:
                store = PreferencesStore()
                store.load()
                _default_store = store
    return _default_store


def reset_default_store_for_tests(store: PreferencesStore | None = None) -> None:
    """Test helper to swap or clear the module-level singleton."""
    global _default_store
    with _default_store_lock:
        _default_store = store
