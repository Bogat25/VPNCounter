import os
import time
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QObject, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QSystemTrayIcon

from vpn_counter.cleanup import CleanupOptions
from vpn_counter.matching import RecognitionBatch, SpeechWord
from vpn_counter.settings import Settings
from vpn_counter.storage import StorageDialog
from vpn_counter.ui import MainWindow


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(application):
    widget = MainWindow(replace(Settings(), last_count=0), save_settings=False, enable_tray=False)
    widget.show()
    application.processEvents()
    yield widget
    widget.close()
    application.processEvents()


def test_ui_and_overlay_share_counter_and_corrections(window):
    batch = RecognitionBatch(
        (SpeechWord("VPN-t", 1, 1.5), SpeechWord("VPN-en", 2, 2.5)),
        "VPN-t használunk, VPN-en csatlakozunk.",
        0,
        3,
        0.1,
    )
    window.consume_batch(batch)
    assert window.count == window.overlay.count == 2
    window.adjust_count(-1)
    window.consume_batch(batch)
    assert window.count == 1  # An overlapping update must not undo a manual correction.
    window.reset_count()
    assert window.count == window.overlay.count == 0
    assert window.activity.count() == 0


def test_presentation_overlay_lock_and_visibility(window):
    flags = window.overlay.windowFlags()
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert flags & Qt.WindowType.WindowDoesNotAcceptFocus
    assert flags & Qt.WindowType.WindowTransparentForInput
    window.lock_overlay.setChecked(False)
    assert not window.overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput
    window.show_overlay.setChecked(False)
    assert not window.overlay.isVisible()


def test_stale_batch_after_reset_is_discarded(window):
    class Worker:
        generation = 2

    window.worker = Worker()
    window.state = "listening"
    window._batch(RecognitionBatch((SpeechWord("VPN", 1, 2),), "VPN", 1, 3, 0.1))
    assert window.count == 0
    window.worker = None
    window.state = "idle"


@pytest.mark.parametrize("corner", ["top-left", "top-right", "bottom-left", "bottom-right"])
def test_corner_stays_anchored_after_count_and_size_changes(window, monkeypatch, corner):
    class Screen:
        def geometry(self):
            return QRect(-1920, -200, 1920, 1080)

    monkeypatch.setattr(window, "_selected_screen", Screen)
    window.position_combo.setCurrentIndex(window.position_combo.findData(corner))
    for size, count in ((36, 1), (60, 10000)):
        window.size_slider.setValue(size)
        window.adjust_count(count)
        overlay = window.overlay
        if corner.endswith("right"):
            assert -1920 + 1920 - (overlay.x() + overlay.width()) == 24
        else:
            assert overlay.x() - (-1920) == 24
        if corner.startswith("bottom"):
            assert -200 + 1080 - (overlay.y() + overlay.height()) == 24
        else:
            assert overlay.y() - (-200) == 24


def test_drag_switches_to_custom_position_and_keeps_it_when_resized(window, monkeypatch):
    class Screen:
        def geometry(self):
            return QRect(100, 200, 1920, 1080)

    monkeypatch.setattr(window, "_selected_screen", Screen)
    window._overlay_moved(230, 350)
    assert window.position_combo.currentData() == "custom"
    assert (window.settings.overlay_x, window.settings.overlay_y) == (130, 150)
    window.size_slider.setValue(60)
    assert (window.overlay.x(), window.overlay.y()) == (230, 350)


def test_tray_reopens_closed_panel_and_explicit_exit_stops_app(application, monkeypatch):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))
    widget = MainWindow(Settings(), save_settings=False)
    try:
        widget.show()
        application.processEvents()
        assert widget.tray.isVisible()
        widget.close()
        assert not widget.isVisible()
        assert widget.overlay.isVisible()
        assert widget.tray.isVisible()
        widget.tray_open.trigger()
        assert widget.isVisible()
        widget.hide_to_tray()
        widget._tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
        assert widget.isVisible()
        widget.tray_overlay.setChecked(False)
        assert not widget.overlay.isVisible()
        widget.show_overlay.setChecked(True)
        assert widget.tray_overlay.isChecked()
        widget.adjust_count(3)
        assert "3 mentions" in widget.tray.toolTip()
        widget.tray_quit.trigger()
        assert not widget.tray.isVisible()
        assert not widget.overlay.isVisible()
    finally:
        widget.quit_application()


def test_selecting_custom_position_unlocks_dragging(window):
    window.position_combo.setCurrentIndex(window.position_combo.findData("custom"))
    assert not window.lock_overlay.isChecked()
    assert not window.overlay.locked


def test_model_download_shows_percentage_then_returns_to_loading_indicator(window):
    window.state = "loading"
    window.busy.show()
    window._download_progress(42)
    assert window.busy.maximum() == 100
    assert window.busy.value() == 42
    assert window.status_label.text() == "Downloading model · 42%"
    window._model_status("Loading speech model")
    assert window.busy.maximum() == 0
    assert window.status_label.text() == "Loading speech model"


def test_late_model_progress_cannot_overwrite_shutdown_status(window):
    window.state = "stopping"
    window._set_status("Stopping after the current model operation…")
    window._download_progress(80)
    window._model_status("Loading speech model")
    assert window.status_label.text().startswith("Stopping")


def wait_for_cleanup(application, widget):
    deadline = time.monotonic() + 5
    while widget.cleanup_worker is not None and time.monotonic() < deadline:
        application.processEvents()
        QTest.qWait(10)
    assert widget.cleanup_worker is None


def test_storage_dialog_defaults_and_cancel_preserve_data(window, monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    dialog = StorageDialog(window)
    assert dialog.models.isChecked()
    assert not dialog.settings.isChecked()
    dialog.models.setChecked(False)
    assert not dialog.clean_button.isEnabled()
    dialog.settings.setChecked(True)
    assert dialog.clean_button.isEnabled()
    monkeypatch.setattr(StorageDialog, "exec", lambda _dialog: QDialog.DialogCode.Rejected)
    window.storage_button.click()
    assert window._cleanup_options is None
    assert not (tmp_path / "VPNCounter").exists()


@pytest.mark.parametrize("reset_settings", [False, True])
def test_cleanup_waits_for_recognition_and_does_not_recreate_removed_settings(
    window, application, monkeypatch, tmp_path, reset_settings
):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    data = tmp_path / "VPNCounter"
    model = data / "models/large-v3/model.bin"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"test model")
    Settings().save()

    class Worker(QObject):
        stopped = False

        def stop(self):
            self.stopped = True

    worker = Worker()
    window.worker = worker
    window.state = "listening"
    window._save_enabled = True
    window.adjust_count(7)
    window.request_cleanup(CleanupOptions(models=True, settings=reset_settings))
    assert worker.stopped
    assert model.exists()  # No deletion while the recognition thread is alive.
    assert window.cleanup_worker is None
    assert not window.start_button.isEnabled()
    window.quit_application()
    assert window.isVisible()  # Exit cannot destroy a worker during cleanup.
    window._finished()  # Simulate recognition's finished signal.
    wait_for_cleanup(application, window)
    assert window.cleanup_completed
    assert not model.exists()
    assert not window.isVisible()
    assert (data / "settings.json").exists() is not reset_settings
    if not reset_settings:
        assert Settings.load().last_count == 7


def test_cleanup_failure_keeps_app_open_for_retry(window, application, monkeypatch, tmp_path):
    from vpn_counter import cleanup

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    def fail(_options):
        raise PermissionError("test file is in use")

    warnings = []
    monkeypatch.setattr(cleanup, "remove_app_data", fail)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    window.request_cleanup(CleanupOptions())
    wait_for_cleanup(application, window)
    assert not window.cleanup_completed
    assert window.isVisible()
    assert window.storage_button.isEnabled()
    assert window.start_button.isEnabled()
    assert window._cleanup_options is None
    assert "test file is in use" in warnings[0]
