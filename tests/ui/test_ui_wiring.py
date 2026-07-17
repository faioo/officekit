"""Wiring / rendering tests that use a real FakePage instead of MagicMock.

These target bugs a mocked ``page`` hides: controls never registered into the
page overlay, ``build_ui`` structure regressions, incomplete ``input_controls``
registration, dialog wiring, and the preference bind round-trip.
"""

from __future__ import annotations

import flet as ft

from support.fake_page import FakePage, iter_controls

from officekit.core.preferences import get_preferences_store
from officekit.tools.doi_query.ui import DOIQueryFrame
from officekit.tools.word2img.ui import Word2ImgFrame


def _overlay_of(page: FakePage, control_type: type) -> list:
    return [control for control in page.overlay if isinstance(control, control_type)]


# --------------------------------------------------------------------------- #
# Overlay registration                                                         #
# --------------------------------------------------------------------------- #

def test_doi_frame_registers_file_picker_in_overlay(fake_page):
    frame = DOIQueryFrame(fake_page)

    pickers = _overlay_of(fake_page, ft.FilePicker)
    assert len(pickers) == 1
    assert pickers[0] is frame.file_picker


def test_word2img_frame_registers_file_picker_in_overlay(fake_page):
    frame = Word2ImgFrame(fake_page)

    pickers = _overlay_of(fake_page, ft.FilePicker)
    assert len(pickers) == 1
    assert pickers[0] is frame.file_picker


# --------------------------------------------------------------------------- #
# build_ui structural invariants                                               #
# --------------------------------------------------------------------------- #

def test_doi_build_ui_exposes_core_controls(fake_page):
    frame = DOIQueryFrame(fake_page)

    for control in (
        frame.run_btn,
        frame.stop_btn,
        frame.progress_bar,
        frame.progress_text,
        frame.log_area,
    ):
        assert control is not None

    # The log area must actually live in the rendered content tree.
    assert frame.log_area in list(iter_controls(frame.content))


def test_word2img_build_ui_exposes_core_controls(fake_page):
    frame = Word2ImgFrame(fake_page)

    for control in (
        frame.run_btn,
        frame.stop_btn,
        frame.progress_bar,
        frame.progress_text,
        frame.log_area,
    ):
        assert control is not None

    assert frame.log_area in list(iter_controls(frame.content))


# --------------------------------------------------------------------------- #
# input_controls completeness + disabled toggling                             #
# --------------------------------------------------------------------------- #

def test_doi_input_controls_registered_and_toggle(fake_page):
    frame = DOIQueryFrame(fake_page)

    for control in (
        frame.file_path_field,
        frame.output_path_field,
        frame.sheet_dropdown,
        frame.timeout_field,
    ):
        assert control in frame.input_controls

    frame._set_controls_state(disabled=True)
    assert all(control.disabled for control in frame.input_controls)
    assert frame.run_btn.disabled is True
    assert frame.stop_btn.disabled is False

    frame._set_controls_state(disabled=False)
    assert all(not control.disabled for control in frame.input_controls)
    assert frame.run_btn.disabled is False
    assert frame.stop_btn.disabled is True


def test_word2img_input_controls_registered_and_toggle(fake_page):
    frame = Word2ImgFrame(fake_page)

    for control in (
        frame.file_path_field,
        frame.output_dir_field,
        frame.format_radio,
        frame.dpi_dropdown,
    ):
        assert control in frame.input_controls

    frame._set_controls_state(disabled=True)
    assert all(control.disabled for control in frame.input_controls)
    assert frame.run_btn.disabled is True
    assert frame.stop_btn.disabled is False


# --------------------------------------------------------------------------- #
# Dialog wiring through the real overlay                                        #
# --------------------------------------------------------------------------- #

def test_show_dialog_registers_alert_and_closes(fake_page):
    frame = DOIQueryFrame(fake_page)

    frame.show_dialog("标题", "内容")

    dialogs = _overlay_of(fake_page, ft.AlertDialog)
    assert len(dialogs) == 1
    dialog = dialogs[0]
    assert dialog.open is True

    # The confirm button's handler must flip the dialog closed.
    dialog.actions[0].on_click(None)
    assert dialog.open is False


def test_word2img_input_source_dialog_offers_file_and_folder(fake_page):
    frame = Word2ImgFrame(fake_page)

    frame.show_input_source_dialog(None)

    dialogs = _overlay_of(fake_page, ft.AlertDialog)
    assert dialogs
    dialog = dialogs[-1]
    assert dialog.open is True

    labels = [action.text for action in dialog.actions]
    assert "选择文件" in labels
    assert "选择文件夹" in labels
    assert "取消" in labels


# --------------------------------------------------------------------------- #
# Preference binding round-trip (restore-on-init + write-back on change)        #
# --------------------------------------------------------------------------- #

def test_doi_timeout_preference_restored_on_init(fake_page):
    store = get_preferences_store()
    store.set("doi_query", "timeout", "45")

    frame = DOIQueryFrame(fake_page)

    assert frame.timeout_field.value == "45"


def test_doi_timeout_preference_written_back_on_change(fake_page):
    frame = DOIQueryFrame(fake_page)

    assert callable(frame.timeout_field.on_change)
    frame.timeout_field.value = "60"
    frame.timeout_field.on_change(None)

    assert frame.prefs.get("doi_query", "timeout") == "60"


def test_word2img_dpi_preference_round_trip(fake_page):
    store = get_preferences_store()
    store.set("word2img", "dpi", "300")

    frame = Word2ImgFrame(fake_page)
    assert frame.dpi_dropdown.value == "300"

    assert callable(frame.dpi_dropdown.on_change)
    frame.dpi_dropdown.value = "96"
    frame.dpi_dropdown.on_change(None)

    assert frame.prefs.get("word2img", "dpi") == "96"
