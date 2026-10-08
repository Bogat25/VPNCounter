from __future__ import annotations

import time
from dataclasses import replace

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from vpn_counter.cleanup import CleanupOptions, CleanupWorker
from vpn_counter.engine import EngineOptions, SpeechWorker, microphones
from vpn_counter.matching import MentionLedger, RecognitionBatch, find_mentions
from vpn_counter.native import GlobalHotkeys
from vpn_counter.overlay import CounterOverlay
from vpn_counter.runtime import gpu_description
from vpn_counter.settings import Settings
from vpn_counter.storage import StorageDialog

STYLE = """
QWidget { color: #eaeaf4; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QWidget#root { background: #0c0d13; }
QDialog { background: #151620; }
QLabel { background: transparent; }
QLabel#title { font-size: 25px; font-weight: 700; letter-spacing: -1px; }
QLabel#subtitle, QLabel#muted { color: #999bb0; }
QLabel#eyebrow { color: #aaa4c6; font-size: 11px; font-weight: 600; letter-spacing: 2px; }
QLabel#brand { background: #28203f; color: #bca4ff; border-radius: 13px;
               font-size: 25px; font-weight: 700; }
QLabel#badge { color: #82dbc1; background: #12241f; border: 1px solid #244237;
              border-radius: 12px; padding: 7px 13px; font-size: 11px; font-weight: 600; }
QFrame#card { background: #151620; border: 1px solid #292b3b; border-radius: 18px; }
QFrame#hero { background: #191625; border: 1px solid #3b3054; border-radius: 18px; }
QLabel#count { font-size: 104px; font-weight: 700; color: #c5afff; letter-spacing: -5px; }
QLabel#section { font-size: 16px; font-weight: 600; }
QLabel#status { font-weight: 600; color: #82dbc1; }
QLabel#transcript { color: #c2c2d3; font-size: 13px; padding: 10px 0; }
QPushButton { background: #222432; border: 1px solid #35384c; border-radius: 9px;
              padding: 9px 15px; font-weight: 600; }
QPushButton:hover { background: #303246; border-color: #64607d; }
QPushButton:pressed { background: #39314f; }
QPushButton:disabled { color: #64667c; background: #1b1d28; border-color: #2c2e40; }
QPushButton#primary { background: #a98aef; color: #17101f; border: 0;
                      font-size: 14px; padding: 13px; }
QPushButton#primary:hover { background: #c1a5ff; }
QPushButton#primary:disabled { background: #56486e; color: #b9abc9; }
QPushButton#quiet { background: transparent; color: #aaaabd; border: 0; padding: 7px; }
QPushButton#quiet:hover { color: #eaeaf4; background: #222432; }
QComboBox, QDoubleSpinBox { background: #0f111a; border: 1px solid #34364b;
                          border-radius: 8px; padding: 8px 10px; min-height: 20px; }
QComboBox:hover, QDoubleSpinBox:hover { border-color: #8d75c1; }
QComboBox:disabled { color: #64667c; }
QComboBox QAbstractItemView { background: #1b1d29; color: #eaeaf4;
                            selection-background-color: #443257; border: 1px solid #44405a; }
QCheckBox { color: #c1c1d3; spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #49445f;
                       border-radius: 5px; background: #0f111a; }
QCheckBox::indicator:checked { background: #a98aef; border-color: #a98aef; }
QSlider::groove:horizontal { height: 5px; background: #303244; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #a98aef; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; margin: -5px 0; border-radius: 7px;
                             background: #d2bfff; }
QProgressBar { border: 0; background: #292b3b; border-radius: 4px;
               min-height: 7px; max-height: 7px; }
QProgressBar::chunk { background: #74d9b3; border-radius: 4px; }
QListWidget { background: transparent; border: 0; outline: 0; }
QListWidget::item { color: #c0c1d2; padding: 9px 4px; border-bottom: 1px solid #282a3a; }
QListWidget::item:selected { background: #2c263b; }
QScrollArea { border: 0; background: #0c0d13; }
QScrollBar:vertical { background: transparent; width: 7px; }
QScrollBar::handle:vertical { background: #38354c; border-radius: 3px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #272334; color: #eaeaf4; border: 1px solid #514368; padding: 6px; }
"""


def app_icon() -> QIcon:
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#28203f"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, 128, 128, 30, 30)
    painter.setPen(QColor("#c5afff"))
    painter.setFont(QFont("Segoe UI", 67, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "V")
    painter.end()
    return QIcon(pixmap)


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def card(name: str = "card") -> tuple[QFrame, QVBoxLayout]:
    widget = QFrame()
    widget.setObjectName(name)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(24, 22, 24, 22)
    layout.setSpacing(15)
    return widget, layout


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        save_settings: bool = True,
        enable_tray: bool = True,
    ) -> None:
        super().__init__()
        self.settings = settings or Settings.load()
        self._save_enabled = save_settings
        self.count = self.settings.last_count
        self.ledger = MentionLedger()
        self.worker: SpeechWorker | None = None
        self.cleanup_worker: CleanupWorker | None = None
        self._cleanup_options: CleanupOptions | None = None
        self.cleanup_completed = False
        self.state = "idle"
        self._pending_close = False
        self._quit_requested = False
        self._tray_available = enable_tray and QSystemTrayIcon.isSystemTrayAvailable()
        self._elapsed = 0.0
        self._active_since: float | None = None
        self.overlay = CounterOverlay(self.settings)
        self.overlay.set_count(self.count)
        self.overlay.moved.connect(self._overlay_moved)
        self.setWindowTitle("VPN Counter")
        self.setWindowIcon(app_icon())
        self.resize(1100, 900)
        self.setMinimumSize(900, 700)
        self.setStyleSheet(STYLE)
        self._build()
        self._refresh_microphones()
        self._refresh_screens()
        self._place_overlay()
        self.overlay.configure(self.settings)
        self.overlay.show()
        self._setup_tray()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)
        self._hotkeys = GlobalHotkeys(
            QApplication.instance(),
            {
                0xA101: (ord("P"), self.toggle_listening),
                0xA102: (0x26, lambda: self.adjust_count(1)),
                0xA103: (0x28, lambda: self.adjust_count(-1)),
                0xA104: (ord("R"), self.reset_count),
                0xA105: (ord("O"), lambda: self.show_overlay.toggle()),
            },
        )
        if self._hotkeys.unavailable:
            self._notice("Some global shortcuts are in use by another application.")
        QApplication.instance().screenAdded.connect(lambda _screen: self._screens_changed())
        QApplication.instance().screenRemoved.connect(lambda _screen: self._screens_changed())

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray_menu = QMenu(self)
        self.tray_open = self.tray_menu.addAction("Open VPN Counter", self.open_control_panel)
        self.tray_menu.setDefaultAction(self.tray_open)
        self.tray_listen = self.tray_menu.addAction("Start listening", self.toggle_listening)
        self.tray_overlay = self.tray_menu.addAction("Show overlay")
        self.tray_overlay.setCheckable(True)
        self.tray_overlay.setChecked(self.show_overlay.isChecked())
        self.tray_overlay.toggled.connect(self.show_overlay.setChecked)
        self.show_overlay.toggled.connect(self.tray_overlay.setChecked)
        self.tray_menu.addSeparator()
        self.tray_quit = self.tray_menu.addAction("Exit VPN Counter", self.quit_application)
        self.tray_menu.aboutToShow.connect(self._update_tray)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.messageClicked.connect(self.open_control_panel)
        self.hide_button.setVisible(self._tray_available)
        if self._tray_available:
            QApplication.instance().setQuitOnLastWindowClosed(False)
            self.tray.show()
        self._update_tray()

    def _update_tray(self) -> None:
        if not hasattr(self, "tray"):
            return
        self.tray.setToolTip(f"VPN Counter · {self.count} mentions · {self.status_label.text()}")
        self.tray_listen.setText(self.start_button.text())
        self.tray_listen.setEnabled(
            self.start_button.isEnabled() and not self._quit_requested and not self._cleanup_options
        )

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.open_control_panel()

    def open_control_panel(self) -> None:
        if not self._quit_requested:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def hide_to_tray(self) -> None:
        if self._tray_available:
            self.hide()

    def quit_application(self) -> None:
        self._quit_requested = True
        self.close()

    def _build(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(scroll)
        scroll.setWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(30, 26, 30, 22)
        layout.setSpacing(20)

        header = QHBoxLayout()
        logo = label("V", "brand")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(52, 52)
        header.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(label("VPN Counter", "title"))
        titles.addWidget(label("A little Easter egg. Every mention counts.", "subtitle"))
        header.addLayout(titles)
        header.addStretch()
        header.addWidget(label("LOCAL  /  HUNGARIAN", "badge"))
        self.hide_button = QPushButton("Hide to tray")
        self.hide_button.setObjectName("quiet")
        self.hide_button.setToolTip("Keep the counter running. Reopen it from the Windows tray.")
        self.hide_button.clicked.connect(self.hide_to_tray)
        header.addWidget(self.hide_button)
        help_button = QPushButton("Shortcuts")
        help_button.setObjectName("quiet")
        help_button.clicked.connect(self._help)
        header.addWidget(help_button)
        layout.addLayout(header)

        main = QHBoxLayout()
        main.setSpacing(20)
        hero, hero_layout = card("hero")
        hero.setMinimumWidth(325)
        hero_layout.addWidget(label("THIS SESSION", "eyebrow"))
        self.counter_label = label(str(self.count), "count")
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(self.counter_label)
        mention_label = label("VPN mentions", "muted")
        mention_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(mention_label)
        hero_layout.addSpacing(5)
        corrections = QHBoxLayout()
        subtract = QPushButton("−1")
        subtract.setToolTip("Correct one extra count · Ctrl+Alt+Down")
        subtract.clicked.connect(lambda: self.adjust_count(-1))
        add = QPushButton("+1")
        add.setToolTip("Add one missed mention · Ctrl+Alt+Up")
        add.clicked.connect(lambda: self.adjust_count(1))
        reset = QPushButton("Reset")
        reset.setToolTip("Start the count again · Ctrl+Alt+R")
        reset.clicked.connect(self.reset_count)
        corrections.addWidget(subtract)
        corrections.addWidget(add)
        corrections.addWidget(reset)
        hero_layout.addLayout(corrections)
        hero_layout.addSpacing(5)
        self.start_button = QPushButton("Start listening")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.toggle_listening)
        hero_layout.addWidget(self.start_button)
        self.end_button = QPushButton("End session")
        self.end_button.setObjectName("quiet")
        self.end_button.setEnabled(False)
        self.end_button.clicked.connect(self.end_session)
        hero_layout.addWidget(self.end_button)
        self.status_label = label("Ready to start", "status", True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(self.status_label)
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setTextVisible(False)
        self.busy.hide()
        hero_layout.addWidget(self.busy)
        self.time_label = label("00:00 listening time", "muted")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(self.time_label)
        hero_layout.addStretch()
        main.addWidget(hero, 4)

        setup, setup_layout = card()
        setup_layout.addWidget(label("Recognition", "section"))
        setup_layout.addWidget(label("Listen locally. Count Hungarian VPN word forms.", "muted"))
        mic_header = QHBoxLayout()
        mic_header.addWidget(label("MICROPHONE", "eyebrow"))
        mic_header.addStretch()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("quiet")
        self.refresh_button.clicked.connect(self._refresh_microphones)
        mic_header.addWidget(self.refresh_button)
        setup_layout.addLayout(mic_header)
        self.microphone_combo = QComboBox()
        self.microphone_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.microphone_combo.setMinimumContentsLength(25)
        setup_layout.addWidget(self.microphone_combo)
        meter_row = QHBoxLayout()
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setValue(0)
        self.meter.setTextVisible(False)
        meter_row.addWidget(self.meter, 1)
        meter_row.addWidget(label("input level", "muted"))
        setup_layout.addLayout(meter_row)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.addWidget(label("MODEL", "eyebrow"), 0, 0)
        grid.addWidget(label("PROCESSING", "eyebrow"), 0, 1)
        self.model_combo = QComboBox()
        for text, model in (
            ("Large v3 · best quality", "large-v3"),
            ("Turbo · faster updates", "turbo"),
            ("Small · lightweight", "small"),
        ):
            self.model_combo.addItem(text, model)
        self.model_combo.setCurrentIndex(max(0, self.model_combo.findData(self.settings.model)))
        self.device_combo = QComboBox()
        self.device_combo.addItem("NVIDIA GPU · FP16", "cuda")
        self.device_combo.addItem("CPU · INT8", "cpu")
        self.device_combo.setCurrentIndex(max(0, self.device_combo.findData(self.settings.device)))
        self.model_combo.currentIndexChanged.connect(self._model_changed)
        grid.addWidget(self.model_combo, 1, 0)
        grid.addWidget(self.device_combo, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        setup_layout.addLayout(grid)
        self.hardware_label = label(gpu_description(), "muted", True)
        setup_layout.addWidget(self.hardware_label)
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(label("Minimum match confidence", "muted"))
        threshold_row.addStretch()
        self.confidence = QDoubleSpinBox()
        self.confidence.setRange(0.05, 0.95)
        self.confidence.setSingleStep(0.05)
        self.confidence.setValue(self.settings.confidence)
        self.confidence.setToolTip("Raise this if uncertain words cause false counts.")
        threshold_row.addWidget(self.confidence)
        setup_layout.addLayout(threshold_row)
        self.decode_label = label("Microphone opens when you start listening.", "muted", True)
        setup_layout.addWidget(self.decode_label)
        self.storage_button = QPushButton("Storage && cleanup")
        self.storage_button.setObjectName("storageCleanup")
        self.storage_button.setToolTip(
            "Open the data folder or remove downloaded models and settings."
        )
        self.storage_button.clicked.connect(self.open_storage)
        setup_layout.addWidget(self.storage_button)
        setup_layout.addStretch()
        main.addWidget(setup, 6)
        layout.addLayout(main)

        display, display_layout = card()
        display_header = QHBoxLayout()
        display_header.addWidget(label("Presentation overlay", "section"))
        display_header.addStretch()
        self.show_overlay = QCheckBox("Show overlay")
        self.show_overlay.setChecked(True)
        self.show_overlay.toggled.connect(self.overlay.setVisible)
        display_header.addWidget(self.show_overlay)
        display_layout.addLayout(display_header)
        display_grid = QGridLayout()
        display_grid.setHorizontalSpacing(18)
        display_grid.addWidget(label("DISPLAY", "eyebrow"), 0, 0)
        display_grid.addWidget(label("POSITION", "eyebrow"), 0, 1)
        display_grid.addWidget(label("SIZE", "eyebrow"), 0, 2)
        display_grid.addWidget(label("OPACITY", "eyebrow"), 0, 3)
        self.screen_combo = QComboBox()
        self.screen_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.screen_combo.setMinimumContentsLength(15)
        self.screen_combo.currentIndexChanged.connect(self._screen_selected)
        display_grid.addWidget(self.screen_combo, 1, 0)
        self.position_combo = QComboBox()
        self.position_combo.setObjectName("overlayPosition")
        for text, corner in (
            ("Top left", "top-left"),
            ("Top right", "top-right"),
            ("Bottom left", "bottom-left"),
            ("Bottom right", "bottom-right"),
            ("Custom (drag)", "custom"),
        ):
            self.position_combo.addItem(text, corner)
        self.position_combo.setCurrentIndex(
            max(0, self.position_combo.findData(self.settings.overlay_corner))
        )
        self.position_combo.currentIndexChanged.connect(self._position_selected)
        self.position_combo.setToolTip("Anchor the counter to a corner of the selected display.")
        display_grid.addWidget(self.position_combo, 1, 1)
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(20, 80)
        self.size_slider.setValue(self.settings.overlay_size)
        self.size_slider.valueChanged.connect(self._overlay_style_changed)
        display_grid.addWidget(self.size_slider, 1, 2)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(self.settings.overlay_opacity)
        self.opacity_slider.valueChanged.connect(self._overlay_style_changed)
        display_grid.addWidget(self.opacity_slider, 1, 3)
        display_grid.setColumnStretch(0, 2)
        display_grid.setColumnStretch(1, 2)
        display_grid.setColumnStretch(2, 1)
        display_grid.setColumnStretch(3, 1)
        display_layout.addLayout(display_grid)
        display_options = QHBoxLayout()
        self.lock_overlay = QCheckBox("Lock position · clicks pass through")
        self.lock_overlay.setChecked(True)
        self.lock_overlay.toggled.connect(self.overlay.set_locked)
        display_options.addWidget(self.lock_overlay)
        self.background = QCheckBox("Dark badge")
        self.background.setChecked(self.settings.overlay_background)
        self.background.toggled.connect(self._overlay_style_changed)
        display_options.addWidget(self.background)
        display_options.addStretch()
        for color in ("#a78bfa", "#82dbc1", "#ffffff", "#ffbf78"):
            swatch = QPushButton()
            swatch.setFixedSize(23, 23)
            swatch.setStyleSheet(
                f"background: {color}; border: 2px solid #454154; border-radius: 11px; padding: 0;"
            )
            swatch.setToolTip(f"Overlay color {color}")
            swatch.clicked.connect(lambda _checked=False, selected=color: self._set_color(selected))
            display_options.addWidget(swatch)
        display_layout.addLayout(display_options)
        layout.addWidget(display)

        activity, activity_layout = card()
        activity_header = QHBoxLayout()
        activity_header.addWidget(label("Recent mentions", "section"))
        activity_header.addStretch()
        activity_header.addWidget(label("Audio stays in memory", "muted"))
        activity_layout.addLayout(activity_header)
        self.transcript_label = label(
            "Your last recognized phrase will appear here.", "transcript", True
        )
        self.transcript_label.setTextFormat(Qt.TextFormat.PlainText)
        activity_layout.addWidget(self.transcript_label)
        self.activity = QListWidget()
        self.activity.setMinimumHeight(105)
        self.activity.setMaximumHeight(165)
        self.activity.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        activity_layout.addWidget(self.activity)
        layout.addWidget(activity)
        self.notice_label = label(
            "Ctrl+Alt+P pause/resume    ·    Ctrl+Alt+↑ / ↓ correct    ·    Ctrl+Alt+O overlay"
            + (
                "\nClosing this window hides it to the tray. Use the tray menu to exit."
                if self._tray_available
                else ""
            ),
            "muted",
            True,
        )
        layout.addWidget(self.notice_label)
        layout.addStretch()

    def _refresh_microphones(self) -> None:
        previous = self.microphone_combo.currentText() or self.settings.microphone
        self.microphone_combo.clear()
        try:
            for microphone in microphones():
                self.microphone_combo.addItem(microphone.label, microphone.index)
            found = self.microphone_combo.findText(previous)
            if found >= 0:
                self.microphone_combo.setCurrentIndex(found)
            if self.microphone_combo.count() == 0:
                self._notice("No microphone found. Connect one and click Refresh.")
        except Exception as error:
            self._notice(f"Microphone unavailable: {error}")

    def _refresh_screens(self) -> None:
        self.screen_combo.blockSignals(True)
        self.screen_combo.clear()
        for index, screen in enumerate(QApplication.screens()):
            geometry = screen.geometry()
            self.screen_combo.addItem(
                f"Display {index + 1} · {geometry.width()} × {geometry.height()}", screen.name()
            )
        found = self.screen_combo.findData(self.settings.screen)
        self.screen_combo.setCurrentIndex(max(0, found))
        self.screen_combo.blockSignals(False)

    def _screens_changed(self) -> None:
        self._refresh_screens()
        self._place_overlay()

    def _selected_screen(self):
        name = self.screen_combo.currentData()
        return next(
            (screen for screen in QApplication.screens() if screen.name() == name),
            QApplication.primaryScreen(),
        )

    def _screen_selected(self, _index: int) -> None:
        self.settings = replace(self.settings, screen=self.screen_combo.currentData() or "")
        self._place_overlay()

    def _place_overlay(self) -> None:
        screen = self._selected_screen()
        if screen is None:
            return
        geometry = screen.geometry()
        max_x = max(0, geometry.width() - self.overlay.width())
        max_y = max(0, geometry.height() - self.overlay.height())
        if self.settings.overlay_corner == "custom":
            x = max(0, min(self.settings.overlay_x, max_x))
            y = max(0, min(self.settings.overlay_y, max_y))
        else:
            x = (
                max(0, max_x - 24)
                if self.settings.overlay_corner.endswith("right")
                else min(24, max_x)
            )
            y = (
                max(0, max_y - 24)
                if self.settings.overlay_corner.startswith("bottom")
                else min(24, max_y)
            )
        self.settings = replace(self.settings, overlay_x=x, overlay_y=y)
        self.overlay.move(geometry.x() + x, geometry.y() + y)

    def _overlay_moved(self, x: int, y: int) -> None:
        screen = self._selected_screen()
        geometry = screen.geometry()
        self.settings = replace(
            self.settings,
            overlay_x=x - geometry.x(),
            overlay_y=y - geometry.y(),
            overlay_corner="custom",
        )
        self.position_combo.blockSignals(True)
        self.position_combo.setCurrentIndex(self.position_combo.findData("custom"))
        self.position_combo.blockSignals(False)
        self._place_overlay()

    def _position_selected(self, _index: int) -> None:
        self.settings = replace(self.settings, overlay_corner=self.position_combo.currentData())
        if self.settings.overlay_corner == "custom":
            self.lock_overlay.setChecked(False)
        self._place_overlay()

    def _overlay_style_changed(self, _value=None) -> None:
        self.settings = replace(
            self.settings,
            overlay_size=self.size_slider.value(),
            overlay_opacity=self.opacity_slider.value(),
            overlay_background=self.background.isChecked(),
        )
        self.overlay.configure(self.settings)
        self._place_overlay()

    def _set_color(self, color: str) -> None:
        self.settings = replace(self.settings, overlay_color=color)
        self.overlay.configure(self.settings)

    def _model_changed(self, _index: int) -> None:
        if self.model_combo.currentData() == "small":
            self.device_combo.setCurrentIndex(self.device_combo.findData("cpu"))

    def _notice(self, text: str) -> None:
        self.notice_label.setText(text)

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self._update_tray()

    def _enable_setup(self, enabled: bool) -> None:
        for widget in (
            self.microphone_combo,
            self.refresh_button,
            self.model_combo,
            self.device_combo,
        ):
            widget.setEnabled(enabled)

    def toggle_listening(self) -> None:
        if self._pending_close or self._cleanup_options is not None:
            return
        if self.worker is not None:
            if self.state == "listening":
                self.worker.pause()
                self._pause_clock()
                self.state = "paused"
                self.start_button.setText("Resume listening")
                self._set_status("Paused · microphone stopped")
            elif self.state == "paused":
                self.worker.resume()
                self.state = "listening"
                self._active_since = time.monotonic()
                self.start_button.setText("Pause listening")
                self._set_status("Listening")
            return
        if self.microphone_combo.currentData() is None:
            self._notice("Select a working microphone before starting.")
            return
        self.ledger.clear()
        self.state = "loading"
        self._enable_setup(False)
        self.start_button.setText("Preparing…")
        self.start_button.setEnabled(False)
        self.end_button.setEnabled(True)
        self.busy.show()
        self.worker = SpeechWorker(
            EngineOptions(
                model=self.model_combo.currentData(),
                device=self.device_combo.currentData(),
                microphone_index=self.microphone_combo.currentData(),
            ),
            self,
        )
        self.worker.status.connect(self._set_status)
        self.worker.listening.connect(self._listening)
        self.worker.batch_ready.connect(self._batch)
        self.worker.failed.connect(self._failed)
        self.worker.warning.connect(self._notice)
        self.worker.finished.connect(self._finished)
        self.worker.start()

    def _listening(self) -> None:
        if self.state == "stopping":
            return
        self.state = "listening"
        self._active_since = time.monotonic()
        self.busy.hide()
        self.start_button.setEnabled(True)
        self.start_button.setText("Pause listening")
        self._set_status("Listening")

    def _pause_clock(self) -> None:
        if self._active_since is not None:
            self._elapsed += time.monotonic() - self._active_since
            self._active_since = None

    def end_session(self) -> None:
        if self.worker:
            self.state = "stopping"
            self.worker.stop()
            self._pause_clock()
            self.start_button.setEnabled(False)
            self.end_button.setEnabled(False)
            self._set_status("Stopping after the current model operation…")

    def _failed(self, message: str) -> None:
        self.state = "error"
        self._set_status("Recognition needs attention")
        self._notice(message)

    def _finished(self) -> None:
        self._pause_clock()
        old_worker = self.worker
        self.worker = None
        if old_worker:
            old_worker.deleteLater()
        self.busy.hide()
        self.meter.setValue(0)
        self._enable_setup(True)
        self.start_button.setEnabled(True)
        self.start_button.setText("Start listening")
        self.end_button.setEnabled(False)
        if self.state != "error":
            self.state = "idle"
            self._set_status("Session ended · counter kept")
        if self._cleanup_options is not None:
            self._begin_cleanup()
        elif self._pending_close:
            self.close()

    def open_storage(self) -> None:
        if self._cleanup_options is not None:
            return
        dialog = StorageDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.request_cleanup(dialog.options())

    def request_cleanup(self, options: CleanupOptions) -> None:
        if self._cleanup_options is not None or not (options.models or options.settings):
            return
        self._cleanup_options = options
        self.storage_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self._enable_setup(False)
        if self.worker is not None:
            self.end_session()
            self._set_status("Waiting for recognition to stop before cleanup…")
        else:
            self._begin_cleanup()

    def _begin_cleanup(self) -> None:
        self.state = "cleaning"
        self._enable_setup(False)
        self.start_button.setEnabled(False)
        self.end_button.setEnabled(False)
        self.busy.show()
        self._set_status("Removing selected app data…")
        self.cleanup_worker = CleanupWorker(self._cleanup_options, self)
        self.cleanup_worker.finished.connect(self._cleanup_finished)
        self.cleanup_worker.start()

    def _cleanup_finished(self) -> None:
        worker = self.cleanup_worker
        self.cleanup_worker = None
        error = worker.error
        worker.deleteLater()
        self.busy.hide()
        if error:
            self._cleanup_options = None
            self._pending_close = False
            self._quit_requested = False
            self.state = "idle"
            self._enable_setup(True)
            self.start_button.setEnabled(True)
            self.storage_button.setEnabled(True)
            self._set_status("Cleanup needs attention")
            self.open_control_panel()
            QMessageBox.warning(
                self,
                "Cleanup incomplete",
                "Some selected files could not be removed. Other files may already have been "
                "removed. Close any programs using the data folder and try again.\n\n" + error,
            )
            return
        self.cleanup_completed = True
        if self._cleanup_options.settings:
            self._save_enabled = False  # Do not recreate settings during shutdown.
        self.quit_application()

    def _batch(self, batch: RecognitionBatch) -> None:
        if (
            self.worker is None
            or self.state != "listening"
            or batch.generation != self.worker.generation
        ):
            return
        self.consume_batch(batch)

    def consume_batch(self, batch: RecognitionBatch) -> None:
        """Apply a verified batch; also used by the file benchmark and UI tests."""
        candidates = find_mentions(batch.words, self.confidence.value())
        accepted = self.ledger.accept(candidates, batch.generation, batch.audio_end)
        if batch.text:
            self.transcript_label.setText(batch.text[-450:])
        self.decode_label.setText(f"Last update processed in {batch.processing_seconds:.2f} s")
        for mention in accepted:
            self.adjust_count(1)
            item = QListWidgetItem(
                f"+1    {mention.text}    ·    {mention.start:.1f} s    ·    "
                f"{mention.probability:.0%} confidence"
            )
            self.activity.insertItem(0, item)
        while self.activity.count() > 40:
            self.activity.takeItem(self.activity.count() - 1)

    def adjust_count(self, amount: int) -> None:
        self.count = max(0, self.count + amount)
        self.counter_label.setText(str(self.count))
        self.overlay.set_count(self.count, animate=amount > 0)
        self._place_overlay()
        self._update_tray()

    def reset_count(self) -> None:
        if self.worker:
            self.worker.invalidate()
        self.ledger.clear()
        self.count = 0
        self.counter_label.setText("0")
        self.overlay.set_count(0)
        self._place_overlay()
        self._update_tray()
        self.activity.clear()
        self.transcript_label.setText("Counter reset. Ready for the next mention.")
        self._elapsed = 0
        if self._active_since is not None:
            self._active_since = time.monotonic()

    def _tick(self) -> None:
        if self.worker:
            self.meter.setValue(int(self.worker.level * 100))
        elapsed = self._elapsed
        if self._active_since is not None:
            elapsed += time.monotonic() - self._active_since
        minutes, seconds = divmod(int(elapsed), 60)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d} listening time")

    def _help(self) -> None:
        QMessageBox.information(
            self,
            "Presentation shortcuts",
            "Ctrl+Alt+P     Start / pause / resume\n"
            "Ctrl+Alt+Up    Add one mention\n"
            "Ctrl+Alt+Down  Subtract one mention\n"
            "Ctrl+Alt+R     Reset counter\n"
            "Ctrl+Alt+O     Show / hide overlay\n\n"
            "Choose your presentation display. Unlock the overlay to drag it, "
            "then lock it before starting PowerPoint.\n\n"
            "For remote presentations, share the whole presentation display "
            "so the overlay is included.\n\n"
            "Use Presentation overlay → Position to choose any of the four corners.\n"
            "Click the Windows tray icon to reopen the panel. Right-click it and "
            "choose Exit VPN Counter to stop the app.",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._cleanup_options is not None and not self.cleanup_completed:
            # Keep the event loop and its workers alive until cleanup succeeds
            # or reports an error, even if Exit is selected from the tray.
            event.ignore()
            return
        if self._tray_available and not self._quit_requested:
            self.hide_to_tray()
            event.ignore()
            return
        if self.worker is not None and self.worker.isRunning():
            self._pending_close = True
            self.end_session()
            self.overlay.hide()
            event.ignore()
            return
        self._timer.stop()
        self._hotkeys.close()
        self.tray.hide()
        self.overlay.close()
        self.settings = replace(
            self.settings,
            model=self.model_combo.currentData(),
            device=self.device_combo.currentData(),
            microphone=self.microphone_combo.currentText(),
            screen=self.screen_combo.currentData() or "",
            confidence=self.confidence.value(),
            last_count=self.count,
        )
        if self._save_enabled:
            try:
                self.settings.save()
            except OSError:
                pass  # Closing remains safe if the settings location is read-only.
        event.accept()
        if self._quit_requested:
            QApplication.instance().quit()
