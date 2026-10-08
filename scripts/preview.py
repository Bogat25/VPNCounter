"""Render the real widgets without opening the microphone or loading Whisper."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from vpn_counter.settings import Settings
from vpn_counter.storage import StorageDialog
from vpn_counter.ui import MainWindow

application = QApplication([])
for filename in ("segoeui.ttf", "segoeuib.ttf"):
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / filename
    if font_path.is_file():
        QFontDatabase.addApplicationFont(str(font_path))
application.setStyle("Fusion")
window = MainWindow(Settings(), save_settings=False, enable_tray=False)
window.resize(1100, 1050)
window.show()
application.processEvents()
output = Path("artifacts")
output.mkdir(exist_ok=True)
window.grab().save(str(output / "control-panel.png"))
window.overlay.grab().save(str(output / "overlay.png"))
window.state = "loading"
window.busy.show()
window._download_progress(42)
application.processEvents()
window.grab().save(str(output / "model-download.png"))
window.state = "idle"
window.busy.hide()
dialog = StorageDialog(window)
dialog.show()
application.processEvents()
dialog.grab().save(str(output / "storage-cleanup.png"))
dialog.close()
window.close()
print("Previews saved to artifacts/: control-panel, overlay, model-download, storage-cleanup")
