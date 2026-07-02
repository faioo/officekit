"""Unit tests for the PreferencesStore user preference persistence layer."""

from __future__ import annotations

import json

import pytest

from officekit.core.preferences import (
    PreferencesStore,
    get_preferences_store,
    reset_default_store_for_tests,
)


@pytest.fixture
def store(tmp_path):
    return PreferencesStore(file_path=tmp_path / "preferences.json")


def test_get_returns_default_when_key_missing(store):
    assert store.get("word2img", "format", default="png") == "png"


def test_set_then_get_round_trips_value(store):
    store.set("word2img", "format", "jpeg")
    assert store.get("word2img", "format") == "jpeg"


def test_set_persists_to_disk(store, tmp_path):
    store.set("word2img", "dpi", "300")

    with (tmp_path / "preferences.json").open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    assert data == {"word2img": {"dpi": "300"}}


def test_set_empty_value_clears_entry(store):
    store.set("word2img", "output_dir", "/tmp/out")
    assert store.get("word2img", "output_dir") == "/tmp/out"

    store.set("word2img", "output_dir", "")
    assert store.get("word2img", "output_dir") is None


def test_set_none_value_clears_entry(store):
    store.set("word2img", "output_dir", "/tmp/out")
    store.set("word2img", "output_dir", None)
    assert store.get("word2img", "output_dir") is None


def test_corrupted_json_file_does_not_crash(tmp_path):
    pref_file = tmp_path / "preferences.json"
    pref_file.write_text("this is not valid json{{{", encoding="utf-8")

    store = PreferencesStore(file_path=pref_file)
    assert store.get("word2img", "format", default="png") == "png"

    # New writes should still succeed and produce a valid file.
    store.set("word2img", "format", "jpeg")
    assert store.get("word2img", "format") == "jpeg"
    assert json.loads(pref_file.read_text(encoding="utf-8")) == {"word2img": {"format": "jpeg"}}


def test_non_dict_top_level_is_treated_as_empty(tmp_path):
    pref_file = tmp_path / "preferences.json"
    pref_file.write_text('["unexpected", "list"]', encoding="utf-8")

    store = PreferencesStore(file_path=pref_file)
    assert store.get("word2img", "format", default="png") == "png"


def test_snapshot_returns_copy_of_tool_bucket(store):
    store.set("word2img", "format", "png")
    store.set("word2img", "dpi", "150")

    snapshot = store.snapshot("word2img")
    assert snapshot == {"format": "png", "dpi": "150"}

    snapshot["format"] = "jpeg"
    assert store.get("word2img", "format") == "png"


def test_atomic_write_leaves_no_tmp_file_after_success(store, tmp_path):
    store.set("word2img", "format", "png")

    stray = list(tmp_path.glob(".preferences-*.json.tmp"))
    assert stray == []


def test_write_failure_does_not_raise(store, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("officekit.core.preferences.os.replace", boom)

    # Should not raise even though the underlying write fails.
    store.set("word2img", "format", "jpeg")

    # In-memory state is still updated so subsequent gets are consistent.
    assert store.get("word2img", "format") == "jpeg"


def test_get_preferences_store_returns_singleton():
    # The autouse conftest fixture points DEFAULT_PREFERENCES_FILE at a temp path
    # and clears the singleton before/after each test, so this call creates a
    # fresh isolated store.
    reset_default_store_for_tests(None)
    first = get_preferences_store()
    second = get_preferences_store()
    assert first is second


def test_isolated_tool_buckets_do_not_leak(store):
    store.set("word2img", "format", "png")
    store.set("doi_query", "timeout", "30")

    assert store.get("word2img", "timeout") is None
    assert store.get("doi_query", "format") is None
