import os
from pathlib import Path

import pytest

from vpn_counter import cleanup
from vpn_counter.cleanup import CleanupOptions, remove_app_data, remove_empty_data_directory
from vpn_counter.runtime import configure_model_storage


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    directory = tmp_path / "VPNCounter"
    model = directory / "models/large-v3/model.bin"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"test model")
    (directory / "settings.json").write_text("{}", encoding="utf-8")
    (directory / "settings.tmp").write_text("{}", encoding="utf-8")
    return directory


@pytest.mark.parametrize("models,settings", [(True, False), (False, True), (True, True)])
def test_only_selected_data_is_removed(data, models, settings):
    other = data / "keep.txt"
    other.write_text("unrelated file", encoding="utf-8")
    remove_app_data(CleanupOptions(models=models, settings=settings))
    assert (data / "models/large-v3/model.bin").exists() is not models
    assert (data / "settings.json").exists() is not settings
    assert (data / "settings.tmp").exists() is not settings
    remove_empty_data_directory()
    assert other.read_text(encoding="utf-8") == "unrelated file"


def test_empty_root_is_removed_only_after_the_instance_lock_is_released(data):
    lock = data / "application.lock"
    lock.write_text("test lock", encoding="utf-8")
    remove_app_data(CleanupOptions(models=True, settings=True))
    remove_empty_data_directory()
    assert lock.exists()
    lock.unlink()
    remove_empty_data_directory()
    assert not data.exists()
    remove_app_data(CleanupOptions())  # Cleaning an already empty app is harmless.


@pytest.mark.parametrize("linked_name", ["models", "VPNCounter"])
def test_linked_data_folders_cannot_redirect_deletion(tmp_path, monkeypatch, linked_name):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    outside = tmp_path / "outside"
    outside.mkdir()
    protected = outside / "keep.txt"
    protected.write_text("keep", encoding="utf-8")
    directory = tmp_path / "VPNCounter"
    link = directory if linked_name == "VPNCounter" else directory / "models"
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        import _winapi

        _winapi.CreateJunction(str(outside), str(link))
    else:
        link.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(OSError, match="folder"):
            remove_app_data(CleanupOptions())
        assert protected.read_text(encoding="utf-8") == "keep"
    finally:
        if os.name == "nt":
            link.rmdir()  # Remove only the junction, never its target.
        else:
            link.unlink()


def test_nested_junction_does_not_delete_external_files(data, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    protected = outside / "keep.txt"
    protected.write_text("keep", encoding="utf-8")
    link = data / "models/nested-link"
    if os.name == "nt":
        import _winapi

        _winapi.CreateJunction(str(outside), str(link))
    else:
        link.symlink_to(outside, target_is_directory=True)
    remove_app_data(CleanupOptions())
    assert protected.exists()
    assert not (data / "models").exists()


def test_portable_app_inside_models_folder_is_protected(data, monkeypatch):
    monkeypatch.setattr(cleanup.sys, "frozen", True, raising=False)
    monkeypatch.setattr(cleanup.sys, "executable", str(data / "models/VPNCounter.exe"))
    with pytest.raises(OSError, match="Move the portable app"):
        remove_app_data(CleanupOptions())
    assert (data / "models/large-v3/model.bin").exists()


def test_unexpected_data_root_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(cleanup, "data_directory", lambda: Path(tmp_path))
    with pytest.raises(OSError, match="unexpected location"):
        remove_app_data(CleanupOptions())


def test_download_caches_are_kept_inside_models(data, monkeypatch):
    cache_variables = (
        "HF_HOME",
        "HF_HUB_CACHE",
        "HUGGINGFACE_HUB_CACHE",
        "HF_XET_CACHE",
        "HF_ASSETS_CACHE",
    )
    for name in cache_variables:
        monkeypatch.setenv(name, "unused-test-location")
    configure_model_storage()
    for name in cache_variables:
        assert Path(os.environ[name]).is_relative_to(data / "models")
    assert not (data / "models/.cache").exists()  # No download before listening.
