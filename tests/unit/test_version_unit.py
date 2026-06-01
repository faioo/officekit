"""Unit tests for OfficeKit version resolution."""

from __future__ import annotations

from officekit import version as version_module


def test_normalize_version_strips_git_ref_and_leading_v():
    """Git tag refs should normalize to package version form."""
    assert version_module.normalize_version("refs/tags/v1.2.3") == "1.2.3"
    assert version_module.normalize_version("v1.2.3") == "1.2.3"
    assert version_module.normalize_version("1.2.3") == "1.2.3"


def test_get_version_prefers_generated_module(mocker, monkeypatch):
    """Packaged apps should use the generated offline version module."""
    monkeypatch.setenv("OFFICEKIT_VERSION", "v1.2.3")
    mocker.patch.object(version_module, "_read_generated_version", return_value="9.8.7")
    mocker.patch.object(version_module, "_read_git_tag_version", return_value="v0.1.7")

    assert version_module.get_version() == "9.8.7"
    assert version_module.get_version(include_generated=False) == "1.2.3"


def test_get_version_reads_environment_before_git(mocker, monkeypatch):
    """CI/manual builds should use the version supplied by the workflow."""
    monkeypatch.setenv("OFFICEKIT_VERSION", "v2.3.4")
    mocker.patch.object(version_module, "_read_generated_version", return_value=None)
    mocker.patch.object(version_module, "_read_git_tag_version", return_value="v0.1.7")

    assert version_module.get_version() == "2.3.4"
    assert version_module.get_release_version() == "v2.3.4"


def test_get_version_falls_back_to_git_tag(mocker, monkeypatch):
    """Source checkouts should use the nearest Git tag when env is unset."""
    monkeypatch.delenv("OFFICEKIT_VERSION", raising=False)
    monkeypatch.delenv("RELEASE_VERSION", raising=False)
    mocker.patch.object(version_module, "_read_generated_version", return_value=None)
    mocker.patch.object(version_module, "_read_git_tag_version", return_value="v0.1.7")

    assert version_module.get_version() == "0.1.7"
    assert version_module.get_release_version() == "v0.1.7"


def test_get_version_uses_dev_fallback(mocker, monkeypatch):
    """Non-Git source snapshots should still have a deterministic version."""
    monkeypatch.delenv("OFFICEKIT_VERSION", raising=False)
    monkeypatch.delenv("RELEASE_VERSION", raising=False)
    mocker.patch.object(version_module, "_read_generated_version", return_value=None)
    mocker.patch.object(version_module, "_read_git_tag_version", return_value=None)

    assert version_module.get_version() == "0.0.0+dev"
    assert version_module.get_release_version() == "v0.0.0+dev"
