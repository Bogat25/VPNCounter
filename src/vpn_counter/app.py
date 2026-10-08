from __future__ import annotations

import os
import sys
from pathlib import Path


def diagnose(output: Path) -> int:
    """Check the installed runtime without opening a microphone or a window."""
    import json
    import time

    from vpn_counter.runtime import configure_gpu_libraries, gpu_description

    report = {"ok": False, "gpu": gpu_description(), "microphone_opened": False}
    started = time.perf_counter()
    try:
        report["gpu_library_directories"] = [str(path) for path in configure_gpu_libraries()]
        import av
        import ctranslate2
        import numpy as np
        from PySide6.QtCore import qVersion

        from vpn_counter.engine import EngineOptions, load_model, microphones, transcribe_window

        report.update(
            qt_version=qVersion(),
            av_version=av.__version__,
            ctranslate2_version=ctranslate2.__version__,
            cuda_devices=ctranslate2.get_cuda_device_count(),
            microphone_devices=len(microphones()),
        )
        model = load_model(EngineOptions())
        words, _ = transcribe_window(model, np.zeros(3 * 16000, dtype=np.float32))
        report.update(ok=True, model="large-v3", device="cuda", silence_words=len(words))
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    report["seconds"] = round(time.perf_counter() - started, 2)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1


def smoke_test(output: Path) -> int:
    """Exercise the frozen UI and recognition imports without capturing audio."""
    import json

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    report = {"ok": False, "microphone_opened": False, "model_loaded": False}
    window = None
    storage_dialog = None
    try:
        import av
        import faster_whisper  # noqa: F401 -- verify the frozen speech dependencies import
        from PySide6.QtCore import qVersion
        from PySide6.QtWidgets import QApplication

        from vpn_counter import __version__
        from vpn_counter.settings import Settings
        from vpn_counter.storage import StorageDialog
        from vpn_counter.ui import MainWindow

        application = QApplication.instance() or QApplication([])
        application.setStyle("Fusion")
        window = MainWindow(Settings(), save_settings=False, enable_tray=False)
        window.show()
        application.processEvents()
        storage_dialog = StorageDialog(window)
        storage_dialog.show()
        application.processEvents()
        storage_ok = (
            not storage_dialog.grab().isNull()
            and storage_dialog.models.isChecked()
            and not storage_dialog.settings.isChecked()
        )
        report.update(
            ok=not window.grab().isNull() and not window.overlay.grab().isNull() and storage_ok,
            storage_dialog_ok=storage_ok,
            version=__version__,
            qt_version=qVersion(),
            av_version=av.__version__,
        )
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        if storage_dialog is not None:
            storage_dialog.close()
        if window is not None:
            window.quit_application()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1


def main() -> int:
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    from vpn_counter.runtime import configure_model_storage

    configure_model_storage()
    if "--diagnose" in sys.argv or "--smoke-test" in sys.argv:
        import argparse

        parser = argparse.ArgumentParser(description="Verify the installed application runtime")
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--diagnose", type=Path, metavar="REPORT.json")
        mode.add_argument("--smoke-test", type=Path, metavar="REPORT.json")
        arguments = parser.parse_args()
        return (
            diagnose(arguments.diagnose) if arguments.diagnose else smoke_test(arguments.smoke_test)
        )

    from PySide6.QtCore import QLockFile, Qt
    from PySide6.QtWidgets import QApplication, QMessageBox

    from vpn_counter import __version__
    from vpn_counter.cleanup import remove_empty_data_directory
    from vpn_counter.settings import data_directory
    from vpn_counter.ui import MainWindow, app_icon

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    application = QApplication(sys.argv)
    application.setStyle("Fusion")
    application.setApplicationName("VPN Counter")
    application.setApplicationVersion(__version__)
    application.setOrganizationName("VPNCounter")
    application.setWindowIcon(app_icon())
    data_directory().mkdir(parents=True, exist_ok=True)
    instance_lock = QLockFile(str(data_directory() / "application.lock"))
    instance_lock.setStaleLockTime(0)
    if not instance_lock.tryLock(0):
        QMessageBox.information(None, "VPN Counter", "VPN Counter is already running.")
        return 0
    window = MainWindow()
    window.show()
    result = application.exec()
    instance_lock.unlock()
    if window.cleanup_completed:
        remove_empty_data_directory()
    return result
