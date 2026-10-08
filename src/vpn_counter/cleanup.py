from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread

from vpn_counter.settings import data_directory


@dataclass(frozen=True, slots=True)
class CleanupOptions:
    models: bool = True
    settings: bool = False


def _checked_directory() -> Path:
    directory = data_directory().absolute()
    if directory.name != "VPNCounter" or directory.is_symlink() or directory.is_junction():
        raise OSError("The app data folder is a link or has an unexpected location.")
    return directory.resolve()


def remove_app_data(options: CleanupOptions) -> None:
    """Remove only selected app-owned data, after the speech worker has stopped."""
    directory = _checked_directory()
    models = directory / "models"
    if options.models and (models.exists() or models.is_symlink() or models.is_junction()):
        # Validate the absolute target before recursive deletion. rmtree does not
        # follow nested directory links or Windows junctions (Python 3.8+).
        if models.is_symlink() or models.is_junction() or models.resolve().parent != directory:
            raise OSError("The models folder points outside the app data folder.")
        executable = Path(sys.executable).resolve()
        if Path(__file__).resolve().is_relative_to(models) or (
            getattr(sys, "frozen", False) and executable.is_relative_to(models)
        ):
            raise OSError("Move the portable app outside the models folder before cleaning up.")
        shutil.rmtree(models)
    if options.settings:
        for name in ("settings.json", "settings.tmp"):
            (directory / name).unlink(missing_ok=True)


def remove_empty_data_directory() -> None:
    """Called after releasing the instance lock; never recursively deletes the root."""
    try:
        _checked_directory().rmdir()
    except OSError:
        pass  # Keep any models, settings, or other files that were not selected.


class CleanupWorker(QThread):
    def __init__(self, options: CleanupOptions, parent=None) -> None:
        super().__init__(parent)
        self.options = options
        self.error = ""

    def run(self) -> None:
        try:
            remove_app_data(self.options)
        except Exception as error:
            self.error = str(error)
