from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from vpn_counter.settings import Settings


class CounterOverlay(QWidget):
    moved = Signal(int, int)

    def __init__(self, settings: Settings) -> None:
        super().__init__(None)
        self.settings = settings
        self.count = 0
        self.locked = True
        self._drag: QPoint | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._set_flags()
        self._resize()

    def _set_flags(self) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        if self.locked:
            flags |= Qt.WindowType.WindowTransparentForInput
        self.setWindowFlags(flags)

    def set_locked(self, locked: bool) -> None:
        visible = self.isVisible()
        position = self.pos()
        self.locked = locked
        self._set_flags()
        self.move(position)
        if visible:
            self.show()
        self.update()

    def configure(self, settings: Settings) -> None:
        self.settings = settings
        self.setWindowOpacity(settings.overlay_opacity / 100)
        self._resize()
        self.update()

    def set_count(self, count: int) -> None:
        self.count = count
        self._resize()
        self.update()

    def _resize(self) -> None:
        size = self.settings.overlay_size
        self.setFixedSize(max(size * 5, size * (3 + len(str(self.count)))), int(size * 2.3))

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        if self.settings.overlay_background:
            painter.setPen(QPen(QColor("#353146"), 1))
            painter.setBrush(QColor(19, 19, 29, 235))
            painter.drawRoundedRect(rect, 16, 16)
        if not self.locked:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(self.settings.overlay_color), 2, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(rect, 16, 16)
        font = QFont("Segoe UI", self.settings.overlay_size)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(self.settings.overlay_color))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"VPN: {self.count}")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self.locked and event.button() == Qt.MouseButton.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag is not None:
            self.move(event.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _event: QMouseEvent) -> None:
        if self._drag is not None:
            self._drag = None
            self.moved.emit(self.x(), self.y())
