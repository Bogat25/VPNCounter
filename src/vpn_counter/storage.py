from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from vpn_counter.cleanup import CleanupOptions
from vpn_counter.settings import data_directory


class StorageDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Storage & cleanup")
        self.setMinimumWidth(510)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        description = QLabel(
            "VPN Counter is portable. Downloaded models and settings are stored here:"
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        location = QLabel(str(data_directory().absolute()))
        location.setTextFormat(Qt.TextFormat.PlainText)
        location.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        location.setWordWrap(True)
        layout.addWidget(location)
        self.open_folder = QPushButton("Open data folder")
        self.open_folder.clicked.connect(self._open_folder)
        layout.addWidget(self.open_folder)
        self.models = QCheckBox("Remove downloaded models")
        self.models.setChecked(True)
        layout.addWidget(self.models)
        self.settings = QCheckBox("Also remove settings and saved counter")
        layout.addWidget(self.settings)
        explanation = QLabel(
            "Cleanup stops recognition, removes the selected data, and exits the app. "
            "Removed models will download again when you next start listening. "
            "To remove the app itself, delete its portable folder after it exits."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.clean_button = buttons.addButton(
            "Clean up and exit", QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.models.toggled.connect(self._selection_changed)
        self.settings.toggled.connect(self._selection_changed)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        self.clean_button.setAutoDefault(False)

    def _selection_changed(self) -> None:
        self.clean_button.setEnabled(self.models.isChecked() or self.settings.isChecked())

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_directory().absolute())))

    def options(self) -> CleanupOptions:
        return CleanupOptions(models=self.models.isChecked(), settings=self.settings.isChecked())
