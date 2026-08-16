"""The Settings tab — NetworkManager layers, the daemon, and this window.

The NetworkManager group is the one with consequences beyond this app: the
drop-in it writes is what Maze Control Center reads to report your MAC
randomisation status, so turning it off makes the rest of the suite say
"Disabled" even while the timer here keeps running. The hint under the group
says exactly that, because the alternative is a bug report about two Maze apps
disagreeing.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from mazecloak.core import autostart


class SettingsView(QWidget):
    def __init__(self, state, controller):
        super().__init__()
        self._s = state
        self._c = controller
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        self._body = QVBoxLayout(inner)
        self._body.setContentsMargins(24, 18, 24, 24)
        self._body.setSpacing(18)
        scroll.setWidget(inner)
        root.addWidget(scroll)

        self._nm_group = self._build_nm()
        self._daemon_group = self._build_daemon()
        self._ui_group = self._build_ui()
        self._body.addWidget(self._nm_group)
        self._body.addWidget(self._daemon_group)
        self._body.addWidget(self._ui_group)
        self._body.addStretch()

        state.language_changed.connect(self.retranslate)
        self.load()

    # ── NetworkManager ────────────────────────────────────────────────────

    def _build_nm(self) -> QGroupBox:
        grp = QGroupBox()
        lay = QVBoxLayout(grp)
        lay.setSpacing(10)

        self._cb_nm = QCheckBox()
        self._cb_nm.toggled.connect(self._on_change)
        lay.addWidget(self._cb_nm)

        self._cb_scan = QCheckBox()
        self._cb_scan.toggled.connect(self._on_change)
        self._cb_scan.setContentsMargins(26, 0, 0, 0)
        lay.addWidget(self._cb_scan)
        self._hint_scan = QLabel()
        self._hint_scan.setObjectName("hint")
        self._hint_scan.setWordWrap(True)
        self._hint_scan.setContentsMargins(48, 0, 0, 6)
        lay.addWidget(self._hint_scan)

        row = QHBoxLayout()
        row.addSpacing(26)
        self._lbl_cloned = QLabel()
        self._combo_cloned = QComboBox()
        self._combo_cloned.addItem("", "random")
        self._combo_cloned.addItem("", "stable")
        self._combo_cloned.currentIndexChanged.connect(self._on_change)
        row.addWidget(self._lbl_cloned)
        row.addWidget(self._combo_cloned)
        row.addStretch()
        lay.addLayout(row)

        self._hint_cloned = QLabel()
        self._hint_cloned.setObjectName("hint")
        self._hint_cloned.setWordWrap(True)
        self._hint_cloned.setContentsMargins(48, 0, 0, 0)
        lay.addWidget(self._hint_cloned)

        self._hint_nm = QLabel()
        self._hint_nm.setObjectName("hint")
        self._hint_nm.setWordWrap(True)
        self._hint_nm.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(self._hint_nm)

        return grp

    # ── daemon ────────────────────────────────────────────────────────────

    def _build_daemon(self) -> QGroupBox:
        grp = QGroupBox()
        lay = QVBoxLayout(grp)
        lay.setSpacing(10)

        row = QHBoxLayout()
        self._lbl_daemon = QLabel()
        self._btn_daemon = QPushButton()
        self._btn_daemon.clicked.connect(self._on_daemon_click)
        row.addWidget(self._lbl_daemon)
        row.addStretch()
        row.addWidget(self._btn_daemon)
        lay.addLayout(row)

        self._hint_daemon = QLabel()
        self._hint_daemon.setObjectName("hint")
        self._hint_daemon.setWordWrap(True)
        lay.addWidget(self._hint_daemon)

        return grp

    # ── this window ───────────────────────────────────────────────────────

    def _build_ui(self) -> QGroupBox:
        grp = QGroupBox()
        lay = QVBoxLayout(grp)
        lay.setSpacing(10)

        row = QHBoxLayout()
        self._lbl_theme = QLabel()
        self._combo_theme = QComboBox()
        self._combo_theme.addItem("", "dark")
        self._combo_theme.addItem("", "light")
        self._combo_theme.currentIndexChanged.connect(self._on_ui_change)
        row.addWidget(self._lbl_theme)
        row.addWidget(self._combo_theme)
        row.addSpacing(24)

        self._lbl_lang = QLabel()
        self._combo_lang = QComboBox()
        self._combo_lang.addItem("English", "en")
        self._combo_lang.addItem("Türkçe", "tr")
        self._combo_lang.currentIndexChanged.connect(self._on_ui_change)
        row.addWidget(self._lbl_lang)
        row.addWidget(self._combo_lang)
        row.addStretch()
        lay.addLayout(row)

        self._cb_autostart = QCheckBox()
        self._cb_autostart.toggled.connect(self._on_autostart_change)
        lay.addWidget(self._cb_autostart)
        self._hint_autostart = QLabel()
        self._hint_autostart.setObjectName("hint")
        self._hint_autostart.setWordWrap(True)
        self._hint_autostart.setContentsMargins(26, 0, 0, 6)
        lay.addWidget(self._hint_autostart)

        self._cb_hidden = QCheckBox()
        self._cb_hidden.toggled.connect(self._on_ui_change)
        lay.addWidget(self._cb_hidden)

        self._cb_notify = QCheckBox()
        self._cb_notify.toggled.connect(self._on_ui_change)
        lay.addWidget(self._cb_notify)

        return grp

    def _on_autostart_change(self, enabled: bool) -> None:
        if self._loading:
            return
        ok, err = autostart.set_enabled(enabled)
        if not ok:
            # Put the box back where reality is rather than leaving it showing
            # a state that was never applied.
            self._loading = True
            self._cb_autostart.setChecked(autostart.is_enabled())
            self._loading = False

    # ── binding ───────────────────────────────────────────────────────────

    def load(self) -> None:
        self._loading = True
        cfg, ui = self._c.cfg, self._c.ui
        self._cb_nm.setChecked(cfg.nm_integration)
        self._cb_scan.setChecked(cfg.nm_wifi_scan_rand)
        idx = self._combo_cloned.findData(cfg.nm_cloned_mode)
        self._combo_cloned.setCurrentIndex(max(0, idx))

        self._combo_theme.setCurrentIndex(
            max(0, self._combo_theme.findData(ui.theme)))
        self._combo_lang.setCurrentIndex(
            max(0, self._combo_lang.findData(ui.language)))
        self._cb_hidden.setChecked(ui.start_hidden)
        self._cb_notify.setChecked(ui.notify)
        self._cb_autostart.setChecked(autostart.is_enabled())
        self._cb_autostart.setEnabled(autostart.available())
        self._loading = False
        self.retranslate()
        self._apply_enabled()

    def _on_change(self, *_args) -> None:
        if self._loading:
            return
        cfg = self._c.cfg
        cfg.nm_integration = self._cb_nm.isChecked()
        cfg.nm_wifi_scan_rand = self._cb_scan.isChecked()
        cfg.nm_cloned_mode = self._combo_cloned.currentData() or "random"
        self._c.save()
        self._apply_enabled()

    def _on_ui_change(self, *_args) -> None:
        if self._loading:
            return
        ui = self._c.ui
        ui.theme = self._combo_theme.currentData() or "dark"
        ui.language = self._combo_lang.currentData() or "en"
        ui.start_hidden = self._cb_hidden.isChecked()
        ui.notify = self._cb_notify.isChecked()
        self._c.save_ui_prefs()
        # AppState owns the live switch; these are no-ops when unchanged.
        self._s.set_theme(ui.theme)
        self._s.set_language(ui.language)

    def _on_daemon_click(self) -> None:
        if self._c.daemon_running:
            self._c.stop_daemon()
        else:
            self._c.start_daemon()
        self.refresh()

    def _apply_enabled(self) -> None:
        writable = self._c.writable
        self._cb_nm.setEnabled(writable)
        on = writable and self._cb_nm.isChecked()
        for w in (self._cb_scan, self._combo_cloned, self._lbl_cloned):
            w.setEnabled(on)

    # ── text ──────────────────────────────────────────────────────────────

    def retranslate(self) -> None:
        t = self._s.t
        self._nm_group.setTitle(t("set_nm_group"))
        self._cb_nm.setText(t("set_nm_enable"))
        self._cb_scan.setText(t("set_nm_scan"))
        self._hint_scan.setText(t("set_nm_scan_hint"))
        self._lbl_cloned.setText(t("set_nm_cloned"))
        self._combo_cloned.setItemText(0, t("cloned_random"))
        self._combo_cloned.setItemText(1, t("cloned_stable"))
        self._hint_cloned.setText(t("cloned_stable_hint"))
        self._hint_nm.setText(t("nm_hint"))

        self._daemon_group.setTitle(t("set_daemon_group"))
        self._hint_daemon.setText(t("set_daemon_hint"))

        self._ui_group.setTitle(t("set_ui_group"))
        self._lbl_theme.setText(t("set_theme"))
        self._combo_theme.setItemText(0, t("theme_dark"))
        self._combo_theme.setItemText(1, t("theme_light"))
        self._lbl_lang.setText(t("set_language"))
        self._cb_autostart.setText(t("set_autostart"))
        self._hint_autostart.setText(t("set_autostart_hint"))
        self._cb_hidden.setText(t("set_start_hidden"))
        self._cb_notify.setText(t("set_notify"))

        self._refresh_daemon_row()

    def _refresh_daemon_row(self) -> None:
        t = self._s.t
        if not self._c.daemon_installed:
            self._lbl_daemon.setText(t("daemon_missing"))
            self._btn_daemon.setText(t("btn_daemon_start"))
            self._btn_daemon.setEnabled(False)
            return
        running = self._c.daemon_running
        self._lbl_daemon.setText(
            t("daemon_running") if running else t("daemon_stopped"))
        self._btn_daemon.setText(
            t("btn_daemon_stop") if running else t("btn_daemon_start"))
        self._btn_daemon.setEnabled(True)

    def refresh(self) -> None:
        self._refresh_daemon_row()
