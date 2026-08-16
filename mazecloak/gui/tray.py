"""System tray icon.

Maze Cloak is a tray-first app: it autostarts hidden, and for most sessions the
tray menu is the entire interface. So the menu carries the two actions worth
reaching without opening a window — toggle the cloak, rotate now — and both are
rebuilt on every open so their labels match the current state instead of
whatever they said when the icon was created.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from mazecloak.gui.icons import tray_icon


class SystemTray(QObject):
    show_requested = pyqtSignal()
    toggle_requested = pyqtSignal()
    rotate_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, state, controller):
        super().__init__()
        self._s = state
        self._c = controller

        self._tray = QSystemTrayIcon()
        # tray_icon() prefers the installed themed icon so the panel scales it
        # from hicolor at its own size and DPI, and falls back to the trimmed
        # pixmap. Passing a single fixed-size pixmap is what made the mark look
        # undersized next to its neighbours.
        self._tray.setIcon(tray_icon())
        self._menu = QMenu()
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)
        self._menu.aboutToShow.connect(self._rebuild)
        self._rebuild()

    def show(self) -> None:
        self._tray.show()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_requested.emit()

    def _rebuild(self) -> None:
        t = self._s.t
        self._menu.clear()
        self._menu.addAction(t("tray_show")).triggered.connect(
            self.show_requested.emit)
        self._menu.addSeparator()

        enabled = self._c.cfg.enabled
        toggle = self._menu.addAction(
            t("tray_disable") if enabled else t("tray_enable"))
        toggle.setEnabled(self._c.writable and self._c.daemon_installed)
        toggle.triggered.connect(self.toggle_requested.emit)

        rotate = self._menu.addAction(t("tray_rotate"))
        rotate.setEnabled(self._c.writable and enabled and self._c.daemon_running)
        rotate.triggered.connect(self.rotate_requested.emit)

        self._menu.addSeparator()
        self._menu.addAction(t("tray_quit")).triggered.connect(
            self.quit_requested.emit)

    def set_tooltip(self, text: str) -> None:
        self._tray.setToolTip(f"Maze Cloak — {text}")

    def notify(self, title: str, message: str) -> None:
        self._tray.showMessage(
            title, message, QSystemTrayIcon.MessageIcon.Information, 4000)
