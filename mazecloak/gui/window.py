"""The main window.

Frameless with a custom title bar, matching Maze Guard: same 50px header, same
logo treatment, same window buttons, same close-to-tray behaviour. The banner
strip under the header is the one addition — it carries the two conditions that
make every control below it a lie if left unsaid (no write access to the
config, or no daemon to execute it).
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

from mazecloak.core import paths
from mazecloak.gui.controller import ST_DAEMON_OFF, ST_NO_DAEMON
from mazecloak.gui.icons import create_app_icon
from mazecloak.gui.theme import STATE_COLORS
from mazecloak.gui.tray import SystemTray
from mazecloak.gui.widgets.interfaces_view import InterfacesView
from mazecloak.gui.widgets.overview_view import OverviewView
from mazecloak.gui.widgets.schedule_view import ScheduleView
from mazecloak.gui.widgets.settings_view import SettingsView

# While the window is on screen, a rotation should show up almost as soon as the
# daemon performs it. While it is not — which is most of a session, since the app
# autostarts into the tray — the only thing reading any of this is the tray
# tooltip, so the same cadence would be a timer scanning the machine for an
# answer nobody is looking at.
_REFRESH_MS = 2000
_IDLE_REFRESH_MS = 15000


class _TitleBar(QWidget):
    """Draggable header. startSystemMove() is what makes this work on Wayland."""

    def __init__(self, window: QMainWindow, parent=None):
        super().__init__(parent)
        self._window = window

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._window.windowHandle()
            if handle:
                handle.startSystemMove()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._window.isMaximized():
                self._window.showNormal()
            else:
                self._window.showMaximized()
        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, state, controller):
        super().__init__()
        self._s = state
        self._c = controller

        self.setWindowTitle("Maze Cloak")
        self.setWindowIcon(create_app_icon(64))
        self.setMinimumSize(940, 620)
        self.resize(1120, 740)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        self._build()
        self._setup_tray()

        self._timer = QTimer(self)
        self._timer.setInterval(_REFRESH_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        # _tick() only refreshes the tab in front, so a tab coming forward has
        # to catch up now rather than at the next tick. Connected here, not in
        # _make_tabs, because it reaches the timer the moment it fires.
        self._tabs.currentChanged.connect(lambda _i: self._tick())

        controller.error.connect(self._on_error)
        state.language_changed.connect(self.retranslate)
        # The theme can be changed from Settings too, so the header button
        # tracks AppState instead of only its own click handler.
        state.theme_changed.connect(lambda _t: self._update_theme_btn())
        self._tick()

    # ── build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())
        root.addWidget(self._make_separator())
        root.addWidget(self._make_banner())
        root.addWidget(self._make_tabs(), 1)

    def _make_header(self) -> _TitleBar:
        header = _TitleBar(self)
        header.setObjectName("header")
        header.setFixedHeight(50)

        lay = QHBoxLayout(header)
        lay.setContentsMargins(16, 0, 0, 0)
        lay.setSpacing(10)

        # No mark in the header: the wordmark already says Maze Cloak, and the
        # icon is carried by the window manager and the tray. Repeating it here
        # only crowds the left edge.
        self._logo = QLabel(self._s.t("app_name"))
        self._logo.setObjectName("logo")
        lay.addWidget(self._logo)

        lay.addStretch()

        # A compact repeat of the Overview status, so the answer is visible from
        # any tab without switching back.
        self._pill_dot = QLabel("●")
        self._pill_text = QLabel()
        self._pill_text.setStyleSheet("font-size: 12px; background: transparent;")
        lay.addWidget(self._pill_dot)
        lay.addWidget(self._pill_text)
        lay.addSpacing(14)

        self._lang_combo = QComboBox()
        self._lang_combo.addItem("English", "en")
        self._lang_combo.addItem("Türkçe", "tr")
        self._lang_combo.setFixedWidth(92)
        self._lang_combo.setCurrentIndex(
            max(0, self._lang_combo.findData(self._s.language)))
        self._lang_combo.currentIndexChanged.connect(self._on_lang)
        lay.addWidget(self._lang_combo)

        self._theme_btn = QPushButton()
        self._theme_btn.setFixedWidth(62)
        self._theme_btn.clicked.connect(self._on_theme)
        lay.addWidget(self._theme_btn)

        lay.addSpacing(8)
        self._min_btn = QPushButton("─")
        self._min_btn.setObjectName("win_btn")
        self._min_btn.clicked.connect(self.showMinimized)
        lay.addWidget(self._min_btn)

        self._max_btn = QPushButton("□")
        self._max_btn.setObjectName("win_btn")
        self._max_btn.clicked.connect(self._toggle_max)
        lay.addWidget(self._max_btn)

        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("win_close")
        self._close_btn.clicked.connect(self.hide)
        lay.addWidget(self._close_btn)

        self._update_theme_btn()
        return header

    def _make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        return sep

    def _make_banner(self) -> QWidget:
        self._banner = QLabel()
        self._banner.setWordWrap(True)
        self._banner.setVisible(False)
        self._banner.setStyleSheet(
            "background-color: rgba(255, 171, 0, 0.12);"
            "color: #ffab00; padding: 9px 24px; font-size: 12px;")
        return self._banner

    def _make_tabs(self) -> QTabWidget:
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self.overview = OverviewView(self._s, self._c)
        self.interfaces = InterfacesView(self._s, self._c)
        self.schedule = ScheduleView(self._s, self._c)
        self.settings = SettingsView(self._s, self._c)

        for view in (self.overview, self.interfaces, self.schedule, self.settings):
            self._tabs.addTab(view, "")
        self._retranslate_tabs()
        return self._tabs

    # ── tray ──────────────────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        self.tray = SystemTray(self._s, self._c)
        self.tray.show_requested.connect(self.restore)
        self.tray.toggle_requested.connect(self._on_tray_toggle)
        self.tray.rotate_requested.connect(self._on_tray_rotate)
        self.tray.quit_requested.connect(self._quit)
        self.tray.show()

    def _on_tray_toggle(self) -> None:
        self._c.set_enabled(not self._c.cfg.enabled)
        self._tick()
        if self._c.ui.notify:
            self.tray.notify(
                self._s.t("notify_title"),
                self._s.t("notify_enabled" if self._c.cfg.enabled
                          else "notify_disabled"))

    def _on_tray_rotate(self) -> None:
        self._c.request_rotation()
        self._tick()

    def restore(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:
        # Closing hides; the daemon keeps rotating either way, and quitting is
        # an explicit choice in the tray menu.
        event.ignore()
        self.hide()

    def _quit(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    # ── header actions ────────────────────────────────────────────────────

    def _toggle_max(self) -> None:
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _on_theme(self) -> None:
        self._s.toggle_theme()
        self._c.ui.theme = self._s.theme
        self._c.save_ui_prefs()
        self._update_theme_btn()

    def _update_theme_btn(self) -> None:
        self._theme_btn.setText("Light" if self._s.theme == "dark" else "Dark")

    def _on_lang(self) -> None:
        lang = self._lang_combo.currentData()
        self._s.set_language(lang)
        self._c.ui.language = lang
        self._c.save_ui_prefs()

    # ── refresh ───────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._c.refresh()

        if not self.isVisible():
            # Hidden in the tray. The tooltip is the only consumer and it needs
            # the daemon's state file, not a walk of every interface — and the
            # tabs will be rebuilt by showEvent before anyone sees them.
            self._set_interval(_IDLE_REFRESH_MS)
            self._refresh_pill()
            return

        self._set_interval(_REFRESH_MS)
        # Only the tab in front. The others are rebuilt when they come forward,
        # and rebuilding the Interfaces table every two seconds behind a tab
        # nobody is on is the same work with none of the benefit.
        current = self._tabs.currentWidget()
        if current is self.overview:
            self.overview.refresh()
        elif current is self.interfaces:
            self.interfaces.refresh()
        # These two hold user input, so their refresh() is already a no-op while
        # they are in front; calling them regardless is what re-syncs them after
        # a change made elsewhere.
        self.schedule.refresh()
        self.settings.refresh()
        self._refresh_banner()
        self._refresh_pill()

    def _set_interval(self, ms: int) -> None:
        if self._timer.interval() != ms:
            self._timer.setInterval(ms)

    def showEvent(self, event) -> None:
        # Coming back from the tray, the timer is on its slow cadence and the
        # tabs are up to fifteen seconds stale. Catch up before the first frame.
        super().showEvent(event)
        self._tick()

    def _refresh_banner(self) -> None:
        t = self._s.t
        status = self._c.status()
        if status == ST_NO_DAEMON:
            self._banner.setText(t("warn_no_daemon"))
            self._banner.setVisible(True)
        elif not self._c.writable:
            self._banner.setText(t("warn_readonly").format(
                path=self._c.config_path_str, group=paths.GROUP))
            self._banner.setVisible(True)
        elif status == ST_DAEMON_OFF:
            self._banner.setText(t("warn_daemon_stopped"))
            self._banner.setVisible(True)
        else:
            self._banner.setVisible(False)

    def _refresh_pill(self) -> None:
        from mazecloak.gui.widgets.overview_view import _STATUS_TEXT
        key, colour = _STATUS_TEXT.get(self._c.status(), ("state_off", "off"))
        text = self._s.t(key)
        self._pill_dot.setStyleSheet(
            f"color: {STATE_COLORS[colour]}; font-size: 10px; background: transparent;")
        self._pill_text.setText(text)
        self.tray.set_tooltip(text)

    # ── i18n ──────────────────────────────────────────────────────────────

    def _retranslate_tabs(self) -> None:
        t = self._s.t
        for i, key in enumerate(
                ("tab_overview", "tab_interfaces", "tab_schedule", "tab_settings")):
            self._tabs.setTabText(i, t(key))

    def retranslate(self) -> None:
        # The language can also be changed from the Settings tab, so the header
        # combo follows AppState rather than being the only thing that drives
        # it. Signals are blocked so re-selecting does not loop back.
        if self._lang_combo.currentData() != self._s.language:
            self._lang_combo.blockSignals(True)
            self._lang_combo.setCurrentIndex(
                max(0, self._lang_combo.findData(self._s.language)))
            self._lang_combo.blockSignals(False)

        self._logo.setText(self._s.t("app_name"))
        self._min_btn.setToolTip(self._s.t("tip_minimize"))
        self._max_btn.setToolTip(self._s.t("tip_maximize"))
        self._close_btn.setToolTip(self._s.t("tip_close"))
        self._retranslate_tabs()
        self._tick()

    # ── errors ────────────────────────────────────────────────────────────

    def _on_error(self, err: str) -> None:
        t = self._s.t
        if err == "readonly":
            msg = t("warn_readonly").format(
                path=self._c.config_path_str, group=paths.GROUP)
        else:
            msg = t("err_save").format(err=err)
        self._banner.setText(msg)
        self._banner.setVisible(True)
