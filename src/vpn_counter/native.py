from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter


class GlobalHotkeys(QAbstractNativeEventFilter):
    """Windows shortcuts remain available while PowerPoint has focus."""

    def __init__(self, application, callbacks: dict[int, tuple[int, object]]) -> None:
        super().__init__()
        self._app = application
        self._callbacks = callbacks
        self._registered: list[int] = []
        self.unavailable: list[int] = []
        if sys.platform == "win32":
            # MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
            for identifier, (key, _callback) in callbacks.items():
                if ctypes.windll.user32.RegisterHotKey(None, identifier, 0x4003, key):
                    self._registered.append(identifier)
                else:
                    self.unavailable.append(identifier)
            application.installNativeEventFilter(self)

    def nativeEventFilter(self, _event_type, message):
        if sys.platform == "win32":
            native_message = wintypes.MSG.from_address(int(message))
            if native_message.message == 0x0312:  # WM_HOTKEY
                entry = self._callbacks.get(native_message.wParam)
                if entry:
                    entry[1]()
                    return True, 0
        return False, 0

    def close(self) -> None:
        if sys.platform == "win32":
            self._app.removeNativeEventFilter(self)
            for identifier in self._registered:
                ctypes.windll.user32.UnregisterHotKey(None, identifier)
        self._registered.clear()
