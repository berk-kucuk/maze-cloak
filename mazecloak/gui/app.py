"""Application entry point.

No event-loop integration beyond Qt's own: everything this GUI does is a file
read or a short subprocess, so a QTimer is the whole scheduler and there is no
asyncio to bridge.
"""
from __future__ import annotations

import sys

from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from mazecloak.gui.app_state import AppState
from mazecloak.gui.controller import CloakController
from mazecloak.gui.icons import create_app_icon
from mazecloak.gui.theme import get_stylesheet
from mazecloak.gui.window import MainWindow

_BACKGROUND_FLAGS = {"--background", "--tray", "--hidden", "--minimized"}
_SINGLETON_NAME = "maze-cloak-singleton"


def _wants_background(argv: list[str]) -> bool:
    return any(a in _BACKGROUND_FLAGS for a in argv)


def _activate_running_instance() -> bool:
    """Hand over to an instance that is already running, if there is one.

    Autostart means a tray icon is usually already there; without this, opening
    the app from the menu would add a second icon and a second window that
    disagree about state as soon as one of them writes.
    """
    sock = QLocalSocket()
    sock.connectToServer(_SINGLETON_NAME)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Maze Cloak")
    app.setApplicationDisplayName("Maze Cloak")
    app.setOrganizationName("maze")
    # Matches StartupWMClass in maze-cloak.desktop so the window groups under
    # the app's own icon instead of a generic python3 entry.
    app.setDesktopFileName("maze-cloak")
    app.setWindowIcon(create_app_icon(64))
    app.setQuitOnLastWindowClosed(False)

    if _activate_running_instance():
        return 0

    QLocalServer.removeServer(_SINGLETON_NAME)   # clears a socket left by a crash
    singleton = QLocalServer()
    singleton.listen(_SINGLETON_NAME)

    controller = CloakController()
    state = AppState(theme=controller.ui.theme, language=controller.ui.language)

    app.setStyleSheet(get_stylesheet(state.theme))
    state.theme_changed.connect(lambda t: app.setStyleSheet(get_stylesheet(t)))

    window = MainWindow(state, controller)

    def _on_second_instance() -> None:
        conn = singleton.nextPendingConnection()
        if conn is not None:
            conn.disconnectFromServer()
        window.restore()

    singleton.newConnection.connect(_on_second_instance)

    if not (_wants_background(sys.argv) or controller.ui.start_hidden):
        window.show()

    return app.exec()
