import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from vpn_counter.matching import RecognitionBatch, SpeechWord
from vpn_counter.settings import Settings
from vpn_counter.ui import MainWindow


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(application):
    widget = MainWindow(replace(Settings(), last_count=0), save_settings=False)
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
